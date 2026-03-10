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

        echo "The Anaconda MCP Server is now installed. When connected to an MCP-compatible AI assistant, it can:"
        echo "Create, update, and delete conda environments"
        echo "Install, update, and remove packages"
        echo "Read your current environment state"
        echo "These actions occur on your machine based on AI instructions."
        echo "Anaconda is not responsible for changes made to your environments, including unintended modifications or deletions."
        echo "You can revoke access at any time by stopping or uninstalling the MCP server."
    fi

    echo ""
    echo "============================================================"
    echo ""
} >> "${MSG_FILE}"

exit 0
