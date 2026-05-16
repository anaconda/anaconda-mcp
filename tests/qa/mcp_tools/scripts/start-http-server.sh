#!/bin/bash
# Start anaconda-mcp HTTP server (keeps running)
# Usage: ./start-http-server.sh [port] [downstream_port]
# Default ports: 9888 (proxy), 5041 (environments-mcp), 5042 (conda-meta-mcp)
# Avoids conflict with IDE MCP servers (8888, 4041)
#
# Includes all 3 MCP servers:
# - environments-mcp (conda): downstream_port
# - conda-meta-mcp: downstream_port + 1
# - search-mcp: remote (anaconda.com)

PORT=${1:-9888}
DOWNSTREAM_PORT=${2:-5041}
CONDA_META_PORT=$((DOWNSTREAM_PORT + 1))
CONFIG_FILE="/tmp/http-config.toml"
PYTHON_PATH=$(which python)

# Get Anaconda domain (default: anaconda.com)
ANACONDA_DOMAIN=${ANACONDA_MCP_ANACONDA_DOMAIN:-anaconda.com}

# Auth token for search-mcp (optional)
if [ -n "$ANACONDA_AUTH_API_KEY" ]; then
    SEARCH_AUTH_CONFIG="auth_token = \"$ANACONDA_AUTH_API_KEY\"
auth_type = \"bearer\""
else
    SEARCH_AUTH_CONFIG="# No auth token - unauthenticated mode"
fi

echo "=== Cleanup ==="
pkill -9 -f "anaconda-mcp" 2>/dev/null || true
pkill -9 -f "environments_mcp" 2>/dev/null || true
pkill -9 -f "conda_meta_mcp" 2>/dev/null || true
lsof -ti:$PORT | xargs kill -9 2>/dev/null || true
lsof -ti:$DOWNSTREAM_PORT | xargs kill -9 2>/dev/null || true
lsof -ti:$CONDA_META_PORT | xargs kill -9 2>/dev/null || true
sleep 2

echo "=== Creating HTTP config ==="
# Escape backslashes in PYTHON_PATH for Windows compatibility in TOML
PYTHON_PATH_ESCAPED="${PYTHON_PATH//\\/\\\\}"

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
command = ["$PYTHON_PATH_ESCAPED", "-m", "environments_mcp_server", "start", "--transport", "streamable-http", "--port", "$DOWNSTREAM_PORT"]
startup_delay = 5

[[servers.proxied.streamable-http]]
name = "search"
url = "https://$ANACONDA_DOMAIN/api/search/mcp"
$SEARCH_AUTH_CONFIG
timeout = 30
keep_alive = true
reconnect_on_failure = true
max_reconnect_attempts = 10
health_check_enabled = false
mode = "proxy"

[[servers.proxied.streamable-http]]
name = "conda-meta"
url = "http://localhost:$CONDA_META_PORT/mcp"
timeout = 30
keep_alive = true
reconnect_on_failure = true
max_reconnect_attempts = 10
health_check_enabled = false
mode = "proxy"
auto_start = true
command = ["$PYTHON_PATH_ESCAPED", "-m", "conda_meta_mcp.cli", "run", "--transport", "streamable-http", "--port", "$CONDA_META_PORT"]
startup_delay = 5

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
echo "Servers: environments-mcp (:$DOWNSTREAM_PORT), conda-meta-mcp (:$CONDA_META_PORT), search-mcp (remote)"
echo "Press Ctrl+C to stop"
echo ""

python -m anaconda_mcp serve --config "$CONFIG_FILE"
