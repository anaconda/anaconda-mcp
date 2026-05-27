#!/bin/bash
# Start anaconda-mcp HTTP server (keeps running)
# Usage: ./start-http-server.sh [port] [downstream_port]
# Default ports: 9888 (proxy), 5041 (downstream) - avoids conflict with IDE MCP servers (8888, 4041)

PORT=${1:-9888}
DOWNSTREAM_PORT=${2:-5041}
CONFIG_FILE="/tmp/http-config.toml"
PYTHON_PATH=$(which python)

export ANACONDA_MCP_ACCEPTED_TERMS=true
export ANACONDA_MCP_ACCEPTED_TERMS_VERSION="2026-05-27"

echo "=== Cleanup ==="
pkill -9 -f "anaconda-mcp" 2>/dev/null || true
pkill -9 -f "environments_mcp" 2>/dev/null || true
lsof -ti:$PORT | xargs kill -9 2>/dev/null || true
lsof -ti:$DOWNSTREAM_PORT | xargs kill -9 2>/dev/null || true
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
# Give downstream time to bind and complete MCP setup before compose registers tools.
startup_delay = 15

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
