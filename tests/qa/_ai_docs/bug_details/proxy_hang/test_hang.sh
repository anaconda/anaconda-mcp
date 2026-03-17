#!/bin/bash
#
# Reproduction script for mcp-compose proxy hang bug.
#
# This script demonstrates that mcp-compose hangs after ~17-18
# rapid sequential tool calls, even though the downstream server
# processes all requests successfully.
#
# Usage:
#   cd /path/to/anaconda-mcp
#   ./tests/qa/_ai_docs/bug_details/proxy_hang/test_hang.sh
#
# Prerequisites:
#   - mcp-compose running: python -m mcp_compose serve --config tests/qa/_ai_docs/bug_details/proxy_hang/proxy.toml
#
set -uo pipefail

PORT=${PORT:-7000}
ITERATIONS=${ITERATIONS:-25}
TIMEOUT=${TIMEOUT:-10}

RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m'

echo "============================================================"
echo " mcp-compose Proxy Hang Reproduction"
echo "============================================================"
echo ""
echo "Config:"
echo "  Proxy port: $PORT"
echo "  Iterations: $ITERATIONS"
echo "  Timeout per call: ${TIMEOUT}s"
echo ""

# Check if proxy is running
if ! nc -z localhost $PORT 2>/dev/null; then
    echo "ERROR: mcp-compose not running on port $PORT"
    echo ""
    echo "Start it first:"
    echo "  python -m mcp_compose serve --config tests/qa/_ai_docs/bug_details/proxy_hang/proxy.toml"
    exit 1
fi

# Initialize session
echo "Initializing MCP session..."
INIT_RESPONSE=$(curl -s -i -X POST "http://localhost:${PORT}/mcp" \
    -H "Accept: application/json, text/event-stream" \
    -H "Content-Type: application/json" \
    -d '{
        "jsonrpc": "2.0",
        "id": 0,
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "hang-repro", "version": "1.0"}
        }
    }' 2>&1)

SID=$(echo "$INIT_RESPONSE" | grep -i "mcp-session-id" | head -1 | sed 's/.*: *//' | tr -d '\r\n')
echo "Session ID: ${SID:-none}"
echo ""

# Send initialized notification
curl -s -X POST "http://localhost:${PORT}/mcp" \
    -H "Content-Type: application/json" \
    -H "Accept: application/json" \
    ${SID:+-H "Mcp-Session-Id: $SID"} \
    -d '{"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}}' \
    >/dev/null 2>&1 || true

sleep 1

# Run rapid calls
echo "Sending $ITERATIONS rapid tool calls..."
echo ""

PASSED=0
FAILED=0

for i in $(seq 1 $ITERATIONS); do
    printf "[%2d/%d] echo_ping... " "$i" "$ITERATIONS"

    RESPONSE=$(curl -s -X POST "http://localhost:${PORT}/mcp" \
        -H "Accept: application/json, text/event-stream" \
        -H "Content-Type: application/json" \
        ${SID:+-H "Mcp-Session-Id: $SID"} \
        -d "{
            \"jsonrpc\": \"2.0\",
            \"id\": $i,
            \"method\": \"tools/call\",
            \"params\": {
                \"name\": \"echo_ping\",
                \"arguments\": {\"message\": \"test-$i\"}
            }
        }" \
        --max-time $TIMEOUT 2>&1)

    if [ $? -eq 0 ]; then
        echo -e "${GREEN}OK${NC}"
        PASSED=$((PASSED + 1))
    else
        echo -e "${RED}TIMEOUT${NC}"
        FAILED=$((FAILED + 1))
    fi
done

# Summary
echo ""
echo "============================================================"
echo " Results"
echo "============================================================"
echo ""
echo "Passed: $PASSED / $ITERATIONS"
echo "Failed: $FAILED / $ITERATIONS"
echo ""

if [ $FAILED -gt 0 ]; then
    echo -e "${RED}BUG REPRODUCED${NC}: Proxy hung after $PASSED successful calls"
    echo ""
    echo "The downstream server (echo_server.py) processes all requests."
    echo "The hang is in mcp-compose proxy response forwarding."
    exit 1
else
    echo -e "${GREEN}All calls succeeded${NC}"
    exit 0
fi
