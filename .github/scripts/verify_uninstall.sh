#!/usr/bin/env bash
set -e

CONFIG_PATH="$1"

if [ -z "$CONFIG_PATH" ]; then
    echo "Usage: $0 <config_path>"
    exit 1
fi

echo "Verifying uninstall at: $CONFIG_PATH"

python << EOF
import json
import sys

config_path = '$CONFIG_PATH'
with open(config_path) as f:
    config = json.load(f)

assert 'anaconda-mcp' not in config.get('mcpServers', {}), 'Server not removed'
print('[PASS] Uninstall successful')
EOF
