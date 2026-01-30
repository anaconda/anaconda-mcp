#!/usr/bin/env bash
set -e

CONFIG_PATH="$1"

if [ -z "$CONFIG_PATH" ]; then
    echo "Usage: $0 <config_path>"
    exit 1
fi

echo "Verifying streamable-http config at: $CONFIG_PATH"

CONFIG_PATH="$CONFIG_PATH" python << 'EOF'
import json
import os

config_path = os.environ['CONFIG_PATH']
with open(config_path) as f:
    config = json.load(f)

server_config = config['mcpServers']['anaconda-mcp']
assert server_config['transport'] == 'streamable-http', 'Wrong transport'
assert '127.0.0.1' in server_config['url'], 'Wrong host in URL'
assert '9999' in server_config['url'], 'Wrong port in URL'

print('[PASS] Streamable HTTP transport test passed!')
EOF
