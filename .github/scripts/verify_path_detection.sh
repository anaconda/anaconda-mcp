#!/usr/bin/env bash
set -e

echo "Testing Claude Desktop config path detection..."

python << 'EOF'
import platform
from anaconda_mcp.claude_desktop import get_claude_desktop_config_path

path = get_claude_desktop_config_path()
system = platform.system()

print(f'OS: {system}')
print(f'Config path: {path}')

# Verify path structure
assert path.name == 'claude_desktop_config.json', f'Unexpected filename: {path.name}'
assert 'Claude' in str(path), f'Claude not in path: {path}'

if system == 'Linux':
    assert '.config' in str(path), f'Expected .config in Linux path: {path}'
elif system == 'Darwin':
    assert 'Library' in str(path), f'Expected Library in macOS path: {path}'
    assert 'Application Support' in str(path), f'Expected Application Support in macOS path: {path}'
elif system == 'Windows':
    path_str = str(path).lower()
    assert 'appdata' in path_str or 'roaming' in path_str, f'Expected AppData in Windows path: {path}'

print('[PASS] Path detection test passed!')
EOF
