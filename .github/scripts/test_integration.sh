#!/usr/bin/env bash
set -e

echo "Testing full integration workflow..."

# Create a temporary directory for testing
TEMP_DIR=$(mktemp -d)
CONFIG_PATH="$TEMP_DIR/claude_desktop_config.json"

echo "=== Test 1: Fresh install ==="
anaconda-mcp claude configure --config "$CONFIG_PATH"
cat "$CONFIG_PATH"

echo ""
echo "=== Test 2: Show configuration ==="
anaconda-mcp claude show --config "$CONFIG_PATH"

echo ""
echo "=== Test 3: Verify backup was created ==="
anaconda-mcp claude configure --config "$CONFIG_PATH" --force
ls -la "$TEMP_DIR"

BACKUP_COUNT=$(ls "$TEMP_DIR"/*.backup.json 2>/dev/null | wc -l)
if [ "$BACKUP_COUNT" -ge 1 ]; then
  echo "[PASS] Backup file created"
else
  echo "[FAIL] No backup file found"
  exit 1
fi

echo ""
echo "=== Test 4: Uninstall ==="
anaconda-mcp claude uninstall --config "$CONFIG_PATH" --no-backup

chmod +x .github/scripts/verify_uninstall.sh
.github/scripts/verify_uninstall.sh "$CONFIG_PATH"

echo ""
echo "=== Test 5: JSON output ==="
anaconda-mcp claude configure --config "$CONFIG_PATH" --no-backup
anaconda-mcp claude show --config "$CONFIG_PATH" --json | python -m json.tool

# Cleanup
rm -rf "$TEMP_DIR"

echo ""
echo "[PASS] All integration tests passed!"
