#!/bin/bash
# post-link.sh — placed next to meta.yaml, conda-build renames it automatically.
# Output goes to $PREFIX/.messages.txt per conda conventions.

EULA_FILE="${PREFIX}/share/anaconda-mcp/EULA.txt"
ACCEPTANCE_FLAG="${PREFIX}/share/anaconda-mcp/.eula_accepted"
MSG_FILE="${PREFIX}/.messages.txt"

# Skip if already accepted (e.g. reinstall/update)
if [ -f "${ACCEPTANCE_FLAG}" ]; then
    exit 0
fi

{
    echo ""
    echo "============================================================"
    echo "  ANACONDA MCP — END USER LICENSE AGREEMENT"
    echo "============================================================"
    echo ""

    if [ -f "${EULA_FILE}" ]; then
        cat "${EULA_FILE}"
    else

        echo "The Anaconda MCP Server connects your conda environments to MCP-compatible AI assistants, enabling them to create, modify, and delete environments and packages on your machine. Install only if you trust the AI assistant you intend to connect and understand it can take real actions on your machine."
        echo "By installing you acknowledge:"
        echo "The AI assistant you connect to this MCP server is an independent third-party model, not a product or service of Anaconda."
        echo "Anaconda is NOT responsible for the actions the AI assistant directs within your environment, including unintended changes or deletions."
    fi

    echo ""
    echo "============================================================"
    echo ""
} >> "${MSG_FILE}"

exit 0
