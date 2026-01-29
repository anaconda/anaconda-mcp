#!/usr/bin/env bash
set -e

echo "Testing CLI commands..."

# Test help
anaconda-mcp claude --help

# Test path command
anaconda-mcp claude path

# Test install command (to temp file)
if [ "$(uname)" == "MINGW"* ] || [ "$(uname)" == "MSYS"* ]; then
    # Windows
    TEMP_CONFIG=$(python -c "import tempfile, os; print(os.path.join(tempfile.gettempdir(), 'test_claude_config.json'))")
else
    # Linux/macOS
    TEMP_CONFIG=$(python -c "import tempfile, os; print(os.path.join(tempfile.gettempdir(), 'test_claude_config.json'))")
fi

anaconda-mcp claude configure --config "$TEMP_CONFIG" --no-backup

# Verify config was created
chmod +x .github/scripts/verify_cli_config.sh
.github/scripts/verify_cli_config.sh "$TEMP_CONFIG"

# Test show command
anaconda-mcp claude show --config "$TEMP_CONFIG"

# Test uninstall command
anaconda-mcp claude uninstall --config "$TEMP_CONFIG" --no-backup

echo "[PASS] All CLI tests passed!"
