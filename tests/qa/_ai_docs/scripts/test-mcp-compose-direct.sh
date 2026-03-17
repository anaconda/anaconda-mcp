#!/bin/bash
#
# test-mcp-compose-direct.sh - Test mcp-compose directly (without anaconda-mcp wrapper)
#
# This script uses mcp-compose CLI directly to isolate whether the hang is in:
#   1. mcp-compose itself
#   2. anaconda-mcp's wrapper/configuration
#
# Usage:
#   ./test-mcp-compose-direct.sh [iterations] [proxy_port] [downstream_port]
#
set -uo pipefail

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
ITERATIONS=${1:-20}
PROXY_PORT=${2:-9999}
DOWNSTREAM_PORT=${3:-6041}
TIMEOUT_SECS=${TIMEOUT_SECS:-60}
TEST_ENV=${TEST_ENV:-"guard-api-test"}
DELAY=${DELAY:-0}

TIMESTAMP=$(date +%Y%m%d-%H%M%S)
LOG_DIR="/tmp/mcp-compose-direct-${TIMESTAMP}"
RESULTS_LOG="${LOG_DIR}/results.log"
CONFIG_FILE="${LOG_DIR}/mcp-compose-minimal.toml"
PYTHON_PATH=$(which python)

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[PASS]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[FAIL]${NC} $1"; }

cleanup() {
    log_info "Cleaning up..."
    if [ -n "${COMPOSE_PID:-}" ]; then
        kill $COMPOSE_PID 2>/dev/null || true
        wait $COMPOSE_PID 2>/dev/null || true
    fi
    pkill -9 -f "mcp-compose.*$PROXY_PORT" 2>/dev/null || true
    pkill -9 -f "environments_mcp_server.*$DOWNSTREAM_PORT" 2>/dev/null || true
    lsof -ti:$PROXY_PORT 2>/dev/null | xargs kill -9 2>/dev/null || true
    lsof -ti:$DOWNSTREAM_PORT 2>/dev/null | xargs kill -9 2>/dev/null || true
}

trap cleanup EXIT

wait_for_port() {
    local port=$1
    local max_wait=${2:-60}
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

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
echo ""
echo "============================================================"
echo " Direct Test: mcp-compose (without anaconda-mcp wrapper)"
echo "============================================================"
echo ""

mkdir -p "$LOG_DIR"

log_info "Configuration:"
log_info "  Proxy port: $PROXY_PORT"
log_info "  Downstream port: $DOWNSTREAM_PORT"
log_info "  Iterations: $ITERATIONS"
log_info "  Timeout: ${TIMEOUT_SECS}s"
log_info "  Test env: $TEST_ENV"
log_info "  Log dir: $LOG_DIR"
echo ""

# Cleanup
cleanup 2>/dev/null || true
sleep 1

# Check mcp-compose is available
if ! python -c "import mcp_compose" 2>/dev/null; then
    log_error "mcp-compose not installed"
    exit 1
fi

MCP_COMPOSE_VERSION=$(python -c "import mcp_compose; print(mcp_compose.__version__)" 2>/dev/null || echo "unknown")
log_info "mcp-compose version: $MCP_COMPOSE_VERSION"

# Create minimal mcp-compose config (no anaconda-mcp involved)
log_info "Creating minimal mcp-compose config..."
cat > "$CONFIG_FILE" << EOF
# Minimal mcp-compose config - NO anaconda-mcp wrapper
# Tests mcp-compose proxy directly

[composer]
name = "mcp-compose-direct-test"
conflict_resolution = "prefix"
log_level = "INFO"
port = $PROXY_PORT

[transport]
stdio_enabled = false
streamable_http_enabled = true
sse_enabled = false

[[servers.proxied.streamable-http]]
name = "conda"
url = "http://localhost:$DOWNSTREAM_PORT/mcp"
timeout = 60
keep_alive = true
reconnect_on_failure = true
max_reconnect_attempts = 10
health_check_enabled = false
mode = "proxy"
auto_start = true
command = ["$PYTHON_PATH", "-m", "environments_mcp_server", "start", "--transport", "streamable-http", "--port", "$DOWNSTREAM_PORT"]
startup_delay = 5

[tool_manager]
conflict_resolution = "prefix"

[api]
enabled = true
path_prefix = "/api/v1"
host = "0.0.0.0"
port = $PROXY_PORT
EOF

log_info "Config file: $CONFIG_FILE"

# Ensure test environment exists
log_info "Ensuring conda environment '$TEST_ENV' exists..."
if ! conda env list | grep -q "^${TEST_ENV} "; then
    conda create -n "$TEST_ENV" python=3.11 -y >/dev/null 2>&1 || true
fi

# Start mcp-compose directly (NOT via anaconda-mcp)
log_info "Starting mcp-compose directly on port $PROXY_PORT..."
python -m mcp_compose serve --config "$CONFIG_FILE" \
    > "${LOG_DIR}/mcp-compose.log" 2>&1 &
COMPOSE_PID=$!
echo $COMPOSE_PID > "${LOG_DIR}/mcp-compose.pid"

if ! wait_for_port $PROXY_PORT 60; then
    log_error "mcp-compose failed to start within 60s"
    cat "${LOG_DIR}/mcp-compose.log"
    exit 1
fi

# Also wait for downstream
if ! wait_for_port $DOWNSTREAM_PORT 30; then
    log_warn "Downstream server may not be ready"
fi

log_success "mcp-compose ready (PID: $COMPOSE_PID)"
sleep 2

# Initialize session
log_info "Initializing MCP session..."
INIT_RESPONSE=$(curl -s -i -X POST "http://localhost:${PROXY_PORT}/mcp" \
    -H "Content-Type: application/json" \
    -H "Accept: application/json, text/event-stream" \
    -d '{
        "jsonrpc": "2.0",
        "id": 0,
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "mcp-compose-direct-test", "version": "1.0"}
        }
    }' \
    --max-time 15 2>&1)

SESSION_ID=$(echo "$INIT_RESPONSE" | grep -i "mcp-session-id" | head -1 | sed 's/.*: *//' | tr -d '\r\n')
log_info "Session ID: ${SESSION_ID:-none}"

# Send initialized notification
curl -s -X POST "http://localhost:${PROXY_PORT}/mcp" \
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
log_info "Running $ITERATIONS iterations of conda_install_packages (PREFIXED - through mcp-compose)..."
echo ""

{
    echo "=== mcp-compose Direct Test Results ==="
    echo "Start: $(date -Iseconds)"
    echo "Proxy port: $PROXY_PORT"
    echo "Downstream port: $DOWNSTREAM_PORT"
    echo "mcp-compose version: $MCP_COMPOSE_VERSION"
    echo "Iterations: $ITERATIONS"
    echo "Session: ${SESSION_ID:-none}"
    echo ""
} > "$RESULTS_LOG"

PASSED=0
FAILED_AT=0

for i in $(seq 1 $ITERATIONS); do
    START_TIME=$(python3 -c "import time; print(time.time())")

    log_info "[$i/$ITERATIONS] conda_install_packages(environment=$TEST_ENV, packages=[pyyaml])..."

    # Call with PREFIXED tool name (as mcp-compose exposes it)
    RESPONSE=$(curl -s -w "\nHTTP_CODE:%{http_code}\nTIME:%{time_total}" \
        -X POST "http://localhost:${PROXY_PORT}/mcp" \
        -H "Content-Type: application/json" \
        -H "Accept: application/json, text/event-stream" \
        ${SESSION_ID:+-H "Mcp-Session-Id: $SESSION_ID"} \
        -d "{
            \"jsonrpc\": \"2.0\",
            \"id\": $i,
            \"method\": \"tools/call\",
            \"params\": {
                \"name\": \"conda_install_packages\",
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
    BODY=$(echo "$RESPONSE" | grep -v "HTTP_CODE:\|TIME:")

    if [ $CURL_EXIT -eq 28 ]; then
        log_error "[$i/$ITERATIONS] TIMEOUT after ${ELAPSED}s"
        echo "[$i] TIMEOUT after ${ELAPSED}s" >> "$RESULTS_LOG"
        FAILED_AT=$i

        echo "" >> "$RESULTS_LOG"
        echo "=== mcp-compose log tail at hang ===" >> "$RESULTS_LOG"
        tail -100 "${LOG_DIR}/mcp-compose.log" >> "$RESULTS_LOG" 2>/dev/null
        break

    elif [ $CURL_EXIT -ne 0 ]; then
        log_error "[$i/$ITERATIONS] curl error $CURL_EXIT after ${ELAPSED}s"
        echo "[$i] curl error $CURL_EXIT after ${ELAPSED}s" >> "$RESULTS_LOG"
        FAILED_AT=$i
        break

    elif [[ "$HTTP_CODE" =~ ^2 ]]; then
        if echo "$BODY" | grep -q '"is_error"[[:space:]]*:[[:space:]]*true'; then
            log_warn "[$i/$ITERATIONS] HTTP $HTTP_CODE in ${ELAPSED}s (tool returned error)"
        else
            log_success "[$i/$ITERATIONS] HTTP $HTTP_CODE in ${ELAPSED}s"
        fi
        echo "[$i] PASS HTTP $HTTP_CODE in ${ELAPSED}s" >> "$RESULTS_LOG"
        PASSED=$((PASSED + 1))
    else
        log_warn "[$i/$ITERATIONS] HTTP $HTTP_CODE in ${ELAPSED}s"
        echo "[$i] HTTP $HTTP_CODE in ${ELAPSED}s" >> "$RESULTS_LOG"
        PASSED=$((PASSED + 1))
    fi

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
    log_error "DIAGNOSIS: Bug is in mcp-compose library (NOT anaconda-mcp wrapper)"
    echo ""
    echo "Evidence:"
    echo "  - Used mcp-compose directly via 'python -m mcp_compose serve'"
    echo "  - No anaconda-mcp code involved"
    echo "  - Same hang at iteration ~$FAILED_AT"
    echo ""
    echo "Report to: https://github.com/datalayer/mcp-compose"
    echo ""
    echo "Logs: ${LOG_DIR}/"
    exit 1
else
    log_success "TEST PASSED: $PASSED/$ITERATIONS iterations completed"
    echo ""
    log_info "mcp-compose does NOT hang when used directly"
    log_info "If anaconda-mcp hangs, the bug may be in anaconda-mcp's configuration"
    echo ""
    echo "Logs: ${LOG_DIR}/"
    exit 0
fi
