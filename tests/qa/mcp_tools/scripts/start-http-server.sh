#!/bin/bash
# Start anaconda-mcp HTTP server (keeps running)
# Usage: ./start-http-server.sh [port]
# Default port: 9888 (proxy) - avoids conflict with IDE MCP servers (8888)

PORT=${1:-9888}
CONFIG_FILE="/tmp/http-config.toml"
PYTHON_PATH=$(which python)

export ANACONDA_MCP_ACCEPTED_TERMS=true
export ANACONDA_MCP_ACCEPTED_TERMS_VERSION="2026-05-27"

echo "=== Cleanup ==="
pkill -9 -f "anaconda-mcp" 2>/dev/null || true
pkill -9 -f "conda_mcp_lite" 2>/dev/null || true
lsof -ti:$PORT | xargs kill -9 2>/dev/null || true
sleep 2

echo "=== Creating HTTP config ==="
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

[[servers.proxied.stdio]]
name = "conda"
command = ["$PYTHON_PATH", "-m", "anaconda_mcp.conda_mcp_lite"]
restart_policy = "on-failure"
max_restarts = 3

[tool_manager]
conflict_resolution = "prefix"

[api]
enabled = true
path_prefix = "/api/v1"
host = "0.0.0.0"
port = $PORT
EOF

echo "=== Starting HTTP server on port $PORT ==="
echo "Config: $CONFIG_FILE"
echo "Press Ctrl+C to stop"
echo ""

python -m anaconda_mcp serve --config "$CONFIG_FILE"
