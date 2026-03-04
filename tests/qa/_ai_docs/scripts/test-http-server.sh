#!/bin/bash
# Test anaconda-mcp HTTP server
# Usage: ./test-http-server.sh [port]

PORT=${1:-8888}
DOWNSTREAM_PORT=4041
CONFIG_FILE="/tmp/http-config-$PORT.toml"
PYTHON_PATH=$(which python)

echo "=== Creating HTTP config ==="
cat > "$CONFIG_FILE" << EOF
[composer]
name = "anaconda-mcp"
port = $PORT

[transport]
stdio_enabled = false
streamable_http_enabled = true

[[servers.proxied.streamable-http]]
name = "conda"
url = "http://localhost:$DOWNSTREAM_PORT/mcp"
auto_start = true
command = ["$PYTHON_PATH", "-m", "environments_mcp_server", "start", "--transport", "streamable-http", "--port", "$DOWNSTREAM_PORT"]
startup_delay = 3
EOF

echo "Config file: $CONFIG_FILE"
cat "$CONFIG_FILE"
echo ""

echo "=== Starting server on port $PORT ==="
anaconda-mcp serve --config "$CONFIG_FILE" &
SERVER_PID=$!
sleep 10

echo ""
echo "=== Testing API: tools/list ==="
curl -s -X POST "http://localhost:$PORT/mcp" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}'

echo ""
echo ""
echo "=== Stopping server (PID: $SERVER_PID) ==="
kill $SERVER_PID 2>/dev/null
sleep 2

echo "=== Done ==="
