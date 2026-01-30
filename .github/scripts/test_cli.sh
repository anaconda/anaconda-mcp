#!/usr/bin/env bash
set -e

echo "Testing CLI commands..."

# Test help
anaconda-mcp claude-desktop --help

# Test path command
anaconda-mcp claude-desktop path

# Test install command (to temp file)
if [ "$(uname)" == "MINGW"* ] || [ "$(uname)" == "MSYS"* ]; then
    # Windows
    TEMP_CONFIG=$(python -c "import tempfile, os; print(os.path.join(tempfile.gettempdir(), 'test_claude_config.json'))")
else
    # Linux/macOS
    TEMP_CONFIG=$(python -c "import tempfile, os; print(os.path.join(tempfile.gettempdir(), 'test_claude_config.json'))")
fi

anaconda-mcp claude-desktop setup-config --config "$TEMP_CONFIG" --no-backup

# Verify config was created
chmod +x .github/scripts/verify_cli_config.sh
.github/scripts/verify_cli_config.sh "$TEMP_CONFIG"

# Test show command
anaconda-mcp claude-desktop show --config "$TEMP_CONFIG"

# Test remove-config command
anaconda-mcp claude-desktop remove-config --config "$TEMP_CONFIG" --no-backup

echo "[PASS] All CLI tests passed!"
