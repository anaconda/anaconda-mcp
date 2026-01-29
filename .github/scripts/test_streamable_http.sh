#!/usr/bin/env bash
set -e

echo "Testing streamable-http transport..."

# Create temp config
if [ "$(uname)" == "MINGW"* ] || [ "$(uname)" == "MSYS"* ]; then
    # Windows
    TEMP_CONFIG=$(python -c "import tempfile, os; print(os.path.join(tempfile.gettempdir(), 'test_http_config.json'))")
else
    # Linux/macOS
    TEMP_CONFIG=$(python -c "import tempfile, os; print(os.path.join(tempfile.gettempdir(), 'test_http_config.json'))")
fi

anaconda-mcp claude configure \
  --config "$TEMP_CONFIG" \
  --transport streamable-http \
  --host 127.0.0.1 \
  --port 9999 \
  --no-backup

chmod +x .github/scripts/verify_streamable_http.sh
.github/scripts/verify_streamable_http.sh "$TEMP_CONFIG"
