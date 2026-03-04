#!/bin/bash
# Test anaconda-mcp HTTP server
# Usage: ./test-http-server.sh [port]

PORT=${1:-8888}
CONFIG_FILE="/tmp/http-config-$PORT.toml"

echo "=== Creating HTTP config ==="
cat > "$CONFIG_FILE" << EOF
[composer]
name = "anaconda-mcp"
port = $PORT

[transport]
stdio_enabled = false
streamable_http_enabled = true
EOF

echo "=== Starting server on port $PORT ==="
anaconda-mcp serve --config "$CONFIG_FILE" &
SERVER_PID=$!
sleep 10

echo ""
echo "=== Testing API: tools/list ==="
curl -s -X POST "http://localhost:$PORT/mcp" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}'

echo ""
echo ""
echo "=== Stopping server (PID: $SERVER_PID) ==="
kill $SERVER_PID 2>/dev/null

echo "=== Done ==="
