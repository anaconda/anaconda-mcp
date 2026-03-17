#!/bin/bash
#
# diagnose-hang.sh - Diagnostic script for KI-011 happy-path hang investigation
#
# This script helps determine whether the hang occurs in:
#   1. mcp-compose (proxy layer)
#   2. environments_mcp_server (downstream server)
#
# Usage:
#   ./diagnose-hang.sh [test_type]
#
# test_type:
#   direct   - Test environments_mcp_server directly (bypass proxy)
#   proxy    - Test through mcp-compose proxy (full stack)
#   both     - Run both tests sequentially (default)
#
# Output:
#   All logs written to /tmp/hang-diag-<timestamp>/
#
set -euo pipefail

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
PROXY_PORT=${PROXY_PORT:-9888}
DOWNSTREAM_PORT=${DOWNSTREAM_PORT:-5041}
ITERATIONS=${ITERATIONS:-20}
TIMEOUT_SECS=${TIMEOUT_SECS:-60}
TEST_ENV=${TEST_ENV:-"guard-api-test"}

TIMESTAMP=$(date +%Y%m%d-%H%M%S)
LOG_DIR="/tmp/hang-diag-${TIMESTAMP}"
PYTHON_PATH=$(which python)

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[PASS]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[FAIL]${NC} $1"
}

log_section() {
    echo ""
    echo "============================================================"
    echo " $1"
    echo "============================================================"
}

cleanup_processes() {
    log_info "Cleaning up existing processes..."
    pkill -9 -f "anaconda-mcp" 2>/dev/null || true
    pkill -9 -f "environments_mcp" 2>/dev/null || true
    lsof -ti:$PROXY_PORT 2>/dev/null | xargs kill -9 2>/dev/null || true
    lsof -ti:$DOWNSTREAM_PORT 2>/dev/null | xargs kill -9 2>/dev/null || true
    sleep 2
}

wait_for_port() {
    local port=$1
    local name=$2
    local max_wait=${3:-30}
    local waited=0

    log_info "Waiting for $name on port $port..."
    while ! nc -z localhost $port 2>/dev/null; do
        sleep 1
        waited=$((waited + 1))
        if [ $waited -ge $max_wait ]; then
            log_error "$name did not start within ${max_wait}s"
            return 1
        fi
    done
    log_success "$name is ready on port $port (${waited}s)"
}

capture_system_state() {
    local label=$1
    local state_file="${LOG_DIR}/system-state-${label}.txt"

    {
        echo "=== System State: $label ==="
        echo "Timestamp: $(date -Iseconds)"
        echo ""

        echo "=== Processes ==="
        ps aux | grep -E "(anaconda|environments_mcp|python)" | grep -v grep || true
        echo ""

        echo "=== Port $PROXY_PORT (proxy) ==="
        lsof -i :$PROXY_PORT 2>/dev/null || echo "(no listeners)"
        echo ""

        echo "=== Port $DOWNSTREAM_PORT (downstream) ==="
        lsof -i :$DOWNSTREAM_PORT 2>/dev/null || echo "(no listeners)"
        echo ""

        echo "=== Network connections ==="
        netstat -an 2>/dev/null | grep -E "($PROXY_PORT|$DOWNSTREAM_PORT)" || true
        echo ""

        echo "=== Open files (environments_mcp) ==="
        for pid in $(pgrep -f environments_mcp 2>/dev/null); do
            echo "PID $pid:"
            lsof -p $pid 2>/dev/null | head -50 || true
        done
        echo ""

        echo "=== Open files (anaconda-mcp) ==="
        for pid in $(pgrep -f anaconda-mcp 2>/dev/null); do
            echo "PID $pid:"
            lsof -p $pid 2>/dev/null | head -50 || true
        done
    } > "$state_file" 2>&1

    log_info "System state captured: $state_file"
}

# ---------------------------------------------------------------------------
# Test: Direct calls to environments_mcp_server (bypass proxy)
# ---------------------------------------------------------------------------
test_direct() {
    log_section "TEST: Direct calls to environments_mcp_server"
    log_info "This test bypasses mcp-compose to isolate environments_mcp_server"

    local server_log="${LOG_DIR}/environments-mcp-direct.log"
    local results_log="${LOG_DIR}/direct-test-results.log"

    cleanup_processes

    # Start environments_mcp_server directly
    log_info "Starting environments_mcp_server on port $DOWNSTREAM_PORT..."
    $PYTHON_PATH -m environments_mcp_server start \
        --transport streamable-http \
        --port $DOWNSTREAM_PORT \
        2>&1 | tee "$server_log" &
    local server_pid=$!
    echo $server_pid > "${LOG_DIR}/environments-mcp.pid"

    wait_for_port $DOWNSTREAM_PORT "environments_mcp_server" 30 || {
        log_error "Failed to start environments_mcp_server"
        kill $server_pid 2>/dev/null || true
        return 1
    }

    # Initialize MCP session
    log_info "Initializing MCP session..."
    local init_response
    init_response=$(curl -s -X POST "http://localhost:${DOWNSTREAM_PORT}/mcp" \
        -H "Content-Type: application/json" \
        -H "Accept: application/json, text/event-stream" \
        -d '{
            "jsonrpc": "2.0",
            "id": 0,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "hang-diag", "version": "1.0"}
            }
        }' \
        --max-time 10 2>&1) || true

    local session_id
    session_id=$(echo "$init_response" | grep -o '"mcp-session-id"[[:space:]]*:[[:space:]]*"[^"]*"' | cut -d'"' -f4 || true)
    log_info "Session ID: ${session_id:-none}"

    # Send notifications/initialized
    curl -s -X POST "http://localhost:${DOWNSTREAM_PORT}/mcp" \
        -H "Content-Type: application/json" \
        -H "Accept: application/json" \
        ${session_id:+-H "Mcp-Session-Id: $session_id"} \
        -d '{"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}}' \
        --max-time 5 >/dev/null 2>&1 || true

    # Run iterations
    log_info "Running $ITERATIONS iterations of conda_install_packages..."
    local passed=0
    local failed_at=0

    {
        echo "=== Direct Test Results ==="
        echo "Start time: $(date -Iseconds)"
        echo "Iterations: $ITERATIONS"
        echo "Timeout: ${TIMEOUT_SECS}s"
        echo ""
    } > "$results_log"

    for i in $(seq 1 $ITERATIONS); do
        local start_time=$(date +%s.%N)

        log_info "Iteration $i/$ITERATIONS: conda_install_packages(pyyaml)..."

        local response
        local http_code
        response=$(curl -s -w "\n%{http_code}" -X POST "http://localhost:${DOWNSTREAM_PORT}/mcp" \
            -H "Content-Type: application/json" \
            -H "Accept: application/json, text/event-stream" \
            ${session_id:+-H "Mcp-Session-Id: $session_id"} \
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
            --max-time $TIMEOUT_SECS 2>&1) || {
                local end_time=$(date +%s.%N)
                local elapsed=$(echo "$end_time - $start_time" | bc)
                log_error "Iteration $i TIMEOUT after ${elapsed}s"
                echo "Iteration $i: TIMEOUT after ${elapsed}s" >> "$results_log"
                failed_at=$i
                capture_system_state "direct-hang-iter${i}"
                break
            }

        http_code=$(echo "$response" | tail -1)
        local body=$(echo "$response" | head -n -1)
        local end_time=$(date +%s.%N)
        local elapsed=$(echo "$end_time - $start_time" | bc)

        if [[ "$http_code" =~ ^2 ]]; then
            log_success "Iteration $i completed in ${elapsed}s (HTTP $http_code)"
            echo "Iteration $i: PASS in ${elapsed}s (HTTP $http_code)" >> "$results_log"
            passed=$((passed + 1))
        else
            log_warn "Iteration $i: HTTP $http_code in ${elapsed}s"
            echo "Iteration $i: HTTP $http_code in ${elapsed}s" >> "$results_log"
            passed=$((passed + 1))  # Non-timeout is still a pass for hang detection
        fi

        # Small delay between iterations
        sleep 0.5
    done

    {
        echo ""
        echo "=== Summary ==="
        echo "Passed: $passed/$ITERATIONS"
        echo "Failed at: ${failed_at:-none}"
        echo "End time: $(date -Iseconds)"
    } >> "$results_log"

    # Cleanup
    kill $server_pid 2>/dev/null || true
    wait $server_pid 2>/dev/null || true

    if [ $failed_at -gt 0 ]; then
        log_error "DIRECT TEST FAILED at iteration $failed_at"
        log_error "Root cause likely in: environments_mcp_server"
        return 1
    else
        log_success "DIRECT TEST PASSED: $passed/$ITERATIONS iterations"
        log_info "environments_mcp_server is NOT the root cause"
        return 0
    fi
}

# ---------------------------------------------------------------------------
# Test: Calls through mcp-compose proxy (full stack)
# ---------------------------------------------------------------------------
test_proxy() {
    log_section "TEST: Calls through mcp-compose proxy"
    log_info "This test uses the full stack (mcp-compose -> environments_mcp_server)"

    local proxy_log="${LOG_DIR}/mcp-compose-proxy.log"
    local results_log="${LOG_DIR}/proxy-test-results.log"
    local config_file="${LOG_DIR}/mcp-compose-config.toml"

    cleanup_processes

    # Create config file
    cat > "$config_file" << EOF
[composer]
name = "anaconda-mcp"
conflict_resolution = "prefix"
log_level = "DEBUG"
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

    log_info "Starting mcp-compose proxy on port $PROXY_PORT..."
    log_info "Config: $config_file"

    $PYTHON_PATH -m anaconda_mcp serve --config "$config_file" \
        2>&1 | tee "$proxy_log" &
    local proxy_pid=$!
    echo $proxy_pid > "${LOG_DIR}/mcp-compose.pid"

    wait_for_port $PROXY_PORT "mcp-compose" 60 || {
        log_error "Failed to start mcp-compose"
        kill $proxy_pid 2>/dev/null || true
        return 1
    }

    # Also wait for downstream
    wait_for_port $DOWNSTREAM_PORT "environments_mcp_server" 30 || {
        log_warn "Downstream server may not be ready"
    }

    # Initialize MCP session
    log_info "Initializing MCP session..."
    local init_response
    init_response=$(curl -s -i -X POST "http://localhost:${PROXY_PORT}/mcp" \
        -H "Content-Type: application/json" \
        -H "Accept: application/json, text/event-stream" \
        -d '{
            "jsonrpc": "2.0",
            "id": 0,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "hang-diag-proxy", "version": "1.0"}
            }
        }' \
        --max-time 15 2>&1) || true

    local session_id
    session_id=$(echo "$init_response" | grep -i "mcp-session-id" | head -1 | sed 's/.*: *//' | tr -d '\r\n' || true)
    log_info "Session ID: ${session_id:-none}"

    # Send notifications/initialized
    curl -s -X POST "http://localhost:${PROXY_PORT}/mcp" \
        -H "Content-Type: application/json" \
        -H "Accept: application/json" \
        ${session_id:+-H "Mcp-Session-Id: $session_id"} \
        -d '{"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}}' \
        --max-time 5 >/dev/null 2>&1 || true

    sleep 2  # Allow session to stabilize

    # Run iterations
    log_info "Running $ITERATIONS iterations of conda_install_packages..."
    local passed=0
    local failed_at=0

    {
        echo "=== Proxy Test Results ==="
        echo "Start time: $(date -Iseconds)"
        echo "Iterations: $ITERATIONS"
        echo "Timeout: ${TIMEOUT_SECS}s"
        echo "Session ID: ${session_id:-none}"
        echo ""
    } > "$results_log"

    for i in $(seq 1 $ITERATIONS); do
        local start_time=$(date +%s.%N)

        log_info "Iteration $i/$ITERATIONS: conda_install_packages(pyyaml)..."

        local response
        response=$(curl -s -w "\n%{http_code}" -X POST "http://localhost:${PROXY_PORT}/mcp" \
            -H "Content-Type: application/json" \
            -H "Accept: application/json, text/event-stream" \
            ${session_id:+-H "Mcp-Session-Id: $session_id"} \
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
            --max-time $TIMEOUT_SECS 2>&1) || {
                local end_time=$(date +%s.%N)
                local elapsed=$(echo "$end_time - $start_time" | bc)
                log_error "Iteration $i TIMEOUT after ${elapsed}s"
                echo "Iteration $i: TIMEOUT after ${elapsed}s" >> "$results_log"
                failed_at=$i
                capture_system_state "proxy-hang-iter${i}"

                # Capture detailed logs at hang point
                log_info "Capturing proxy log tail at hang..."
                echo "" >> "$results_log"
                echo "=== Proxy log tail at hang ===" >> "$results_log"
                tail -100 "$proxy_log" >> "$results_log" 2>/dev/null || true
                break
            }

        http_code=$(echo "$response" | tail -1)
        local body=$(echo "$response" | head -n -1)
        local end_time=$(date +%s.%N)
        local elapsed=$(echo "$end_time - $start_time" | bc)

        if [[ "$http_code" =~ ^2 ]]; then
            log_success "Iteration $i completed in ${elapsed}s (HTTP $http_code)"
            echo "Iteration $i: PASS in ${elapsed}s (HTTP $http_code)" >> "$results_log"
            passed=$((passed + 1))
        else
            log_warn "Iteration $i: HTTP $http_code in ${elapsed}s"
            echo "Iteration $i: HTTP $http_code in ${elapsed}s" >> "$results_log"
            passed=$((passed + 1))
        fi

        # Small delay between iterations (configurable)
        sleep ${ITERATION_DELAY:-0.5}
    done

    {
        echo ""
        echo "=== Summary ==="
        echo "Passed: $passed/$ITERATIONS"
        echo "Failed at: ${failed_at:-none}"
        echo "End time: $(date -Iseconds)"
    } >> "$results_log"

    # Cleanup
    kill $proxy_pid 2>/dev/null || true
    pkill -P $proxy_pid 2>/dev/null || true
    wait $proxy_pid 2>/dev/null || true
    cleanup_processes

    if [ $failed_at -gt 0 ]; then
        log_error "PROXY TEST FAILED at iteration $failed_at"
        return 1
    else
        log_success "PROXY TEST PASSED: $passed/$ITERATIONS iterations"
        return 0
    fi
}

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
main() {
    local test_type=${1:-both}

    log_section "Hang Diagnosis Script"
    log_info "Log directory: $LOG_DIR"
    log_info "Test type: $test_type"
    log_info "Iterations: $ITERATIONS"
    log_info "Timeout: ${TIMEOUT_SECS}s"
    log_info "Test environment: $TEST_ENV"

    mkdir -p "$LOG_DIR"

    # Record configuration
    {
        echo "=== Hang Diagnosis Configuration ==="
        echo "Timestamp: $(date -Iseconds)"
        echo "Test type: $test_type"
        echo "Proxy port: $PROXY_PORT"
        echo "Downstream port: $DOWNSTREAM_PORT"
        echo "Iterations: $ITERATIONS"
        echo "Timeout: ${TIMEOUT_SECS}s"
        echo "Test environment: $TEST_ENV"
        echo "Python: $PYTHON_PATH"
        echo ""
        echo "=== Python packages ==="
        $PYTHON_PATH -m pip list 2>/dev/null | grep -E "(mcp|anaconda|environments)" || true
        echo ""
        echo "=== mcp-compose version ==="
        $PYTHON_PATH -c "import mcp_compose; print(mcp_compose.__version__)" 2>/dev/null || echo "unknown"
    } > "${LOG_DIR}/config.txt"

    # Ensure test environment exists
    log_info "Ensuring test environment '$TEST_ENV' exists..."
    conda create -n "$TEST_ENV" python=3.11 -y 2>/dev/null || true

    local direct_result=0
    local proxy_result=0

    case $test_type in
        direct)
            test_direct || direct_result=$?
            ;;
        proxy)
            test_proxy || proxy_result=$?
            ;;
        both)
            test_direct || direct_result=$?
            echo ""
            sleep 3
            test_proxy || proxy_result=$?
            ;;
        *)
            log_error "Unknown test type: $test_type"
            echo "Usage: $0 [direct|proxy|both]"
            exit 1
            ;;
    esac

    # ---------------------------------------------------------------------------
    # Summary and diagnosis
    # ---------------------------------------------------------------------------
    log_section "DIAGNOSIS SUMMARY"

    echo ""
    echo "Log directory: $LOG_DIR"
    echo ""

    if [ "$test_type" = "both" ] || [ "$test_type" = "direct" ]; then
        if [ $direct_result -eq 0 ]; then
            log_success "Direct test: PASSED"
        else
            log_error "Direct test: FAILED"
        fi
    fi

    if [ "$test_type" = "both" ] || [ "$test_type" = "proxy" ]; then
        if [ $proxy_result -eq 0 ]; then
            log_success "Proxy test: PASSED"
        else
            log_error "Proxy test: FAILED"
        fi
    fi

    echo ""

    if [ "$test_type" = "both" ]; then
        if [ $direct_result -eq 0 ] && [ $proxy_result -ne 0 ]; then
            log_section "DIAGNOSIS: Root cause is in mcp-compose (proxy)"
            echo "The direct test passed but proxy test failed."
            echo "This indicates the hang occurs in mcp-compose, not environments_mcp_server."
            echo ""
            echo "Next steps:"
            echo "  1. Check ${LOG_DIR}/mcp-compose-proxy.log for SSE timeout patterns"
            echo "  2. Look for 'GET stream disconnected' without prior 5th POST + DELETE"
            echo "  3. File issue against mcp-compose with the logs"
            echo ""
        elif [ $direct_result -ne 0 ]; then
            log_section "DIAGNOSIS: Root cause is in environments_mcp_server"
            echo "The direct test failed at iteration $direct_result."
            echo "This indicates the hang occurs in environments_mcp_server itself."
            echo ""
            echo "Next steps:"
            echo "  1. Check ${LOG_DIR}/environments-mcp-direct.log for the last processed request"
            echo "  2. Look for logger.exception() patterns (KI-015)"
            echo "  3. Check file descriptor exhaustion in system-state-*.txt"
            echo ""
        else
            log_section "DIAGNOSIS: Both tests passed"
            echo "The hang may be a race condition that requires specific timing."
            echo ""
            echo "Next steps:"
            echo "  1. Try with ITERATION_DELAY=0 to increase pressure"
            echo "  2. Try with ITERATIONS=50 for longer runs"
            echo "  3. Run the actual pytest to compare behavior"
            echo ""
        fi
    fi

    echo "All logs saved to: $LOG_DIR"
    echo ""
    ls -la "$LOG_DIR"

    # Cleanup test environment (optional)
    # conda remove -n "$TEST_ENV" --all -y 2>/dev/null || true

    return $((direct_result + proxy_result))
}

main "$@"
