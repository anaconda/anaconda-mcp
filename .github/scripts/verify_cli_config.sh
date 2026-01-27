#!/usr/bin/env bash
set -e

CONFIG_PATH="$1"

if [ -z "$CONFIG_PATH" ]; then
    echo "Usage: $0 <config_path>"
    exit 1
fi

echo "Verifying config was created at: $CONFIG_PATH"

python << EOF
import json
import sys

config_path = '$CONFIG_PATH'
with open(config_path) as f:
    config = json.load(f)

assert 'mcpServers' in config, 'mcpServers not in config'
assert 'anaconda-mcp' in config['mcpServers'], 'anaconda-mcp not in config'

server_config = config['mcpServers']['anaconda-mcp']
assert 'command' in server_config, 'command not in server config'
assert 'args' in server_config, 'args not in server config'
assert 'env' in server_config, 'env not in server config'
assert 'MCP_COMPOSE_CONFIG_DIR' in server_config['env'], 'MCP_COMPOSE_CONFIG_DIR not in env'

print('[PASS] CLI install test passed!')
EOF
