#!/bin/bash
#
# test-env-mcp-direct.sh - Test environments_mcp_server directly (bypass mcp-compose)
#
# This script calls environments_mcp_server with UNPREFIXED tool names
# (install_packages, list_environments) to isolate whether hangs occur
# in environments_mcp_server itself or in mcp-compose proxy.
#
# Usage:
#   ./test-env-mcp-direct.sh [iterations] [port]
#
# Examples:
#   ./test-env-mcp-direct.sh           # 20 iterations on port 5041
#   ./test-env-mcp-direct.sh 50        # 50 iterations
#   ./test-env-mcp-direct.sh 20 6041   # custom port
#
set -uo pipefail

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
ITERATIONS=${1:-20}
PORT=${2:-5041}
TIMEOUT_SECS=${TIMEOUT_SECS:-60}
TEST_ENV=${TEST_ENV:-"guard-api-test"}
DELAY=${DELAY:-0.5}

TIMESTAMP=$(date +%Y%m%d-%H%M%S)
LOG_DIR="/tmp/env-mcp-direct-${TIMESTAMP}"
RESULTS_LOG="${LOG_DIR}/results.log"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------
log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[PASS]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[FAIL]${NC} $1"; }

cleanup() {
    log_info "Cleaning up..."
    if [ -n "${SERVER_PID:-}" ]; then
        kill $SERVER_PID 2>/dev/null || true
        wait $SERVER_PID 2>/dev/null || true
    fi
    pkill -9 -f "environments_mcp_server.*--port.*$PORT" 2>/dev/null || true
    lsof -ti:$PORT 2>/dev/null | xargs kill -9 2>/dev/null || true
}

trap cleanup EXIT

wait_for_port() {
    local port=$1
    local max_wait=${2:-30}
    local waited=0
    while ! nc -z localhost $port 2>/dev/null; do
        sleep 1
        waited=$((waited + 1))
        if [ $waited -ge $max_wait ]; then
            return 1
        fi
    done
    return 0
}

capture_state() {
    local label=$1
    {
        echo "=== System State: $label ==="
        echo "Time: $(date -Iseconds)"
        echo ""
        echo "=== Port $PORT ==="
        lsof -i :$PORT 2>/dev/null || echo "(none)"
        echo ""
        echo "=== Network ==="
        netstat -an 2>/dev/null | grep $PORT || true
        echo ""
        echo "=== Process FDs ==="
        for pid in $(pgrep -f "environments_mcp" 2>/dev/null); do
            echo "PID $pid:"
            lsof -p $pid 2>/dev/null | wc -l
        done
    } > "${LOG_DIR}/state-${label}.txt" 2>&1
}

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
echo ""
echo "============================================================"
echo " Direct Test: environments_mcp_server (no proxy)"
echo "============================================================"
echo ""

mkdir -p "$LOG_DIR"

log_info "Configuration:"
log_info "  Port: $PORT"
log_info "  Iterations: $ITERATIONS"
log_info "  Timeout: ${TIMEOUT_SECS}s"
log_info "  Test env: $TEST_ENV"
log_info "  Delay: ${DELAY}s"
log_info "  Log dir: $LOG_DIR"
echo ""

# Cleanup any existing processes
cleanup 2>/dev/null || true
sleep 1

# Ensure test environment exists
log_info "Ensuring conda environment '$TEST_ENV' exists..."
if ! conda env list | grep -q "^${TEST_ENV} "; then
    conda create -n "$TEST_ENV" python=3.11 -y >/dev/null 2>&1 || true
fi

# Start environments_mcp_server
log_info "Starting environments_mcp_server on port $PORT..."
python -m environments_mcp_server start \
    --transport streamable-http \
    --port $PORT \
    > "${LOG_DIR}/server.log" 2>&1 &
SERVER_PID=$!
echo $SERVER_PID > "${LOG_DIR}/server.pid"

if ! wait_for_port $PORT 30; then
    log_error "Server failed to start within 30s"
    cat "${LOG_DIR}/server.log"
    exit 1
fi
log_success "Server ready (PID: $SERVER_PID)"

# Initialize session
log_info "Initializing MCP session..."
INIT_RESPONSE=$(curl -s -i -X POST "http://localhost:${PORT}/mcp" \
    -H "Content-Type: application/json" \
    -H "Accept: application/json, text/event-stream" \
    -d '{
        "jsonrpc": "2.0",
        "id": 0,
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "direct-test", "version": "1.0"}
        }
    }' \
    --max-time 10 2>&1)

SESSION_ID=$(echo "$INIT_RESPONSE" | grep -i "mcp-session-id" | head -1 | sed 's/.*: *//' | tr -d '\r\n')
log_info "Session ID: ${SESSION_ID:-none}"

# Send initialized notification
curl -s -X POST "http://localhost:${PORT}/mcp" \
    -H "Content-Type: application/json" \
    -H "Accept: application/json" \
    ${SESSION_ID:+-H "Mcp-Session-Id: $SESSION_ID"} \
    -d '{"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}}' \
    --max-time 5 >/dev/null 2>&1 || true

sleep 1

# ---------------------------------------------------------------------------
# Run test iterations
# ---------------------------------------------------------------------------
echo ""
log_info "Running $ITERATIONS iterations of install_packages (unprefixed)..."
echo ""

{
    echo "=== Direct Test Results ==="
    echo "Start: $(date -Iseconds)"
    echo "Port: $PORT"
    echo "Iterations: $ITERATIONS"
    echo "Session: ${SESSION_ID:-none}"
    echo ""
} > "$RESULTS_LOG"

PASSED=0
FAILED_AT=0

for i in $(seq 1 $ITERATIONS); do
    START_TIME=$(python3 -c "import time; print(time.time())")

    log_info "[$i/$ITERATIONS] install_packages(environment=$TEST_ENV, packages=[pyyaml])..."

    # Call with UNPREFIXED tool name (as environments_mcp_server exposes it)
    RESPONSE=$(curl -s -w "\nHTTP_CODE:%{http_code}\nTIME:%{time_total}" \
        -X POST "http://localhost:${PORT}/mcp" \
        -H "Content-Type: application/json" \
        -H "Accept: application/json, text/event-stream" \
        ${SESSION_ID:+-H "Mcp-Session-Id: $SESSION_ID"} \
        -d "{
            \"jsonrpc\": \"2.0\",
            \"id\": $i,
            \"method\": \"tools/call\",
            \"params\": {
                \"name\": \"install_packages\",
                \"arguments\": {
                    \"environment\": \"$TEST_ENV\",
                    \"packages\": [\"pyyaml\"]
                }
            }
        }" \
        --max-time $TIMEOUT_SECS 2>&1)

    CURL_EXIT=$?
    END_TIME=$(python3 -c "import time; print(time.time())")
    ELAPSED=$(python3 -c "print(f'{$END_TIME - $START_TIME:.2f}')")

    HTTP_CODE=$(echo "$RESPONSE" | grep "HTTP_CODE:" | cut -d: -f2)
    CURL_TIME=$(echo "$RESPONSE" | grep "TIME:" | cut -d: -f2)
    BODY=$(echo "$RESPONSE" | grep -v "HTTP_CODE:\|TIME:")

    if [ $CURL_EXIT -eq 28 ]; then
        # Timeout
        log_error "[$i/$ITERATIONS] TIMEOUT after ${ELAPSED}s"
        echo "[$i] TIMEOUT after ${ELAPSED}s" >> "$RESULTS_LOG"
        FAILED_AT=$i
        capture_state "hang-iter${i}"

        # Capture server log tail
        echo "" >> "$RESULTS_LOG"
        echo "=== Server log tail at hang ===" >> "$RESULTS_LOG"
        tail -50 "${LOG_DIR}/server.log" >> "$RESULTS_LOG" 2>/dev/null
        break

    elif [ $CURL_EXIT -ne 0 ]; then
        log_error "[$i/$ITERATIONS] curl error $CURL_EXIT after ${ELAPSED}s"
        echo "[$i] curl error $CURL_EXIT after ${ELAPSED}s" >> "$RESULTS_LOG"
        FAILED_AT=$i
        capture_state "error-iter${i}"
        break

    elif [[ "$HTTP_CODE" =~ ^2 ]]; then
        # Check if response contains error
        if echo "$BODY" | grep -q '"is_error"[[:space:]]*:[[:space:]]*true'; then
            log_warn "[$i/$ITERATIONS] HTTP $HTTP_CODE in ${ELAPSED}s (tool returned error)"
            echo "[$i] HTTP $HTTP_CODE in ${ELAPSED}s (tool error)" >> "$RESULTS_LOG"
        else
            log_success "[$i/$ITERATIONS] HTTP $HTTP_CODE in ${ELAPSED}s"
            echo "[$i] PASS HTTP $HTTP_CODE in ${ELAPSED}s" >> "$RESULTS_LOG"
        fi
        PASSED=$((PASSED + 1))

    else
        log_warn "[$i/$ITERATIONS] HTTP $HTTP_CODE in ${ELAPSED}s"
        echo "[$i] HTTP $HTTP_CODE in ${ELAPSED}s" >> "$RESULTS_LOG"
        PASSED=$((PASSED + 1))
    fi

    # Delay between iterations
    if [ $i -lt $ITERATIONS ] && [ "$(echo "$DELAY > 0" | bc)" -eq 1 ]; then
        sleep $DELAY
    fi
done

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
echo ""
echo "============================================================"
echo " RESULTS"
echo "============================================================"
echo ""

{
    echo ""
    echo "=== Summary ==="
    echo "Passed: $PASSED/$ITERATIONS"
    echo "Failed at: ${FAILED_AT:-none}"
    echo "End: $(date -Iseconds)"
} >> "$RESULTS_LOG"

if [ $FAILED_AT -gt 0 ]; then
    log_error "TEST FAILED at iteration $FAILED_AT"
    echo ""
    log_error "DIAGNOSIS: Hang occurs in environments_mcp_server (not mcp-compose)"
    echo ""
    echo "Check logs:"
    echo "  Server log: ${LOG_DIR}/server.log"
    echo "  Results:    ${RESULTS_LOG}"
    echo "  State:      ${LOG_DIR}/state-hang-iter${FAILED_AT}.txt"
    exit 1
else
    log_success "TEST PASSED: $PASSED/$ITERATIONS iterations completed"
    echo ""
    log_success "DIAGNOSIS: environments_mcp_server does NOT hang"
    log_info "If proxy test hangs, root cause is in mcp-compose"
    echo ""
    echo "Logs: ${LOG_DIR}/"
    exit 0
fi
