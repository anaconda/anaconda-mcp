#!/bin/bash
# Test anaconda-mcp HTTP server
# Usage: ./test-http-server.sh [port]

PORT=${1:-8888}
DOWNSTREAM_PORT=4041
CONFIG_FILE="/tmp/http-config-$PORT.toml"
PYTHON_PATH=$(which python)

echo "=== Killing any existing processes ==="
pkill -9 -f "anaconda-mcp" 2>/dev/null || true
pkill -9 -f "environments_mcp" 2>/dev/null || true
lsof -ti:$PORT | xargs kill -9 2>/dev/null || true
lsof -ti:$DOWNSTREAM_PORT | xargs kill -9 2>/dev/null || true
sleep 3

echo "=== Creating HTTP config (based on default template) ==="
cat > "$CONFIG_FILE" << EOF
[composer]
name = "anaconda-mcp"
conflict_resolution = "prefix"
log_level = "INFO"
port = $PORT

[transport]
stdio_enabled = false
streamable_http_enabled = true
sse_enabled = false

[[servers.proxied.streamable-http]]
name = "conda"
url = "http://localhost:$DOWNSTREAM_PORT/mcp"
timeout = 30
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
port = $PORT
EOF

echo "Config written to: $CONFIG_FILE"
echo ""

echo "=== Starting server on port $PORT ==="
anaconda-mcp serve --config "$CONFIG_FILE" 2>&1 &
SERVER_PID=$!
echo "Server PID: $SERVER_PID"
echo ""

echo "=== Waiting for server to be ready ==="
for i in {1..90}; do
  sleep 1
  HEALTH=$(curl -s "http://localhost:$PORT/api/v1/health" 2>/dev/null)
  if [ -n "$HEALTH" ]; then
    echo "Health check passed after ${i}s: $HEALTH"
    break
  fi
  if [ $((i % 10)) -eq 0 ]; then
    echo "Still waiting... ${i}s"
  fi
done

sleep 5

echo ""
echo "=== Step 1: Initialize session ==="
INIT_RESPONSE=$(curl -s -X POST "http://localhost:$PORT/mcp" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","id":0,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}}}')
echo "Init: $INIT_RESPONSE"

echo ""
echo "=== Step 2: List tools ==="
RESPONSE=$(curl -s -X POST "http://localhost:$PORT/mcp" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}')
echo "Tools response:"
echo "$RESPONSE" | head -c 2000

TOOL_COUNT=$(echo "$RESPONSE" | grep -o '"name":' | wc -l)
echo ""
echo "Tools found: $TOOL_COUNT"

echo ""
echo "=== Cleanup ==="
kill $SERVER_PID 2>/dev/null
pkill -f "environments_mcp_server" 2>/dev/null || true
echo "=== Done ==="
