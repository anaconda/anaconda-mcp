#!/bin/bash
# Capture diagnostics during MCP hang
# Run this WHILE Claude Desktop is hanging (before closing it)

OUTPUT_DIR="/Users/iiliukhina/projects/anaconda-mcp/tests/qa/_ai_docs/bug_details/proxy_hang"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
OUTPUT_FILE="$OUTPUT_DIR/diagnostics_$TIMESTAMP.txt"

echo "=== MCP Hang Diagnostics - $TIMESTAMP ===" > "$OUTPUT_FILE"

echo -e "\n=== Port 4041 connections ===" >> "$OUTPUT_FILE"
lsof -i :4041 >> "$OUTPUT_FILE" 2>&1

echo -e "\n=== Netstat port 4041 ===" >> "$OUTPUT_FILE"
netstat -an | grep 4041 >> "$OUTPUT_FILE" 2>&1

echo -e "\n=== All anaconda-mcp processes ===" >> "$OUTPUT_FILE"
ps aux | grep -E "anaconda_mcp|mcp_compose|environments_mcp" | grep -v grep >> "$OUTPUT_FILE" 2>&1

echo -e "\n=== Process tree ===" >> "$OUTPUT_FILE"
pstree -p $(pgrep -f "anaconda_mcp serve" | head -1) >> "$OUTPUT_FILE" 2>&1

echo -e "\n=== Open files for anaconda_mcp serve ===" >> "$OUTPUT_FILE"
for pid in $(pgrep -f "anaconda_mcp serve"); do
    echo "--- PID $pid ---" >> "$OUTPUT_FILE"
    lsof -p $pid 2>/dev/null | head -50 >> "$OUTPUT_FILE"
done

echo -e "\n=== Open files for environments_mcp_server ===" >> "$OUTPUT_FILE"
for pid in $(pgrep -f "environments_mcp_server"); do
    echo "--- PID $pid ---" >> "$OUTPUT_FILE"
    lsof -p $pid 2>/dev/null | head -50 >> "$OUTPUT_FILE"
done

echo -e "\n=== Network connections summary ===" >> "$OUTPUT_FILE"
lsof -i -P | grep -E "anaconda|mcp|python" | grep -v grep >> "$OUTPUT_FILE" 2>&1

echo -e "\n=== Copying current MCP log ===" >> "$OUTPUT_FILE"
cp ~/Library/Logs/Claude/mcp-server-anaconda-mcp.log "$OUTPUT_DIR/mcp_log_$TIMESTAMP.log"

echo "Diagnostics saved to: $OUTPUT_FILE"
echo "MCP log saved to: $OUTPUT_DIR/mcp_log_$TIMESTAMP.log"
