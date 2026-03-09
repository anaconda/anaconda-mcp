#!/bin/bash
# post-link.sh — runs automatically after `conda install anaconda-mcp`
# Displays the EULA and requires user acceptance.

EULA_FILE="${PREFIX}/share/anaconda-mcp/EULA.txt"
ACCEPTANCE_FLAG="${PREFIX}/share/anaconda-mcp/.eula_accepted"

# Skip if already accepted (e.g. reinstall/update)
if [ -f "${ACCEPTANCE_FLAG}" ]; then
    exit 0
fi

echo ""
echo "============================================================"
echo "  ANACONDA MCP — END USER LICENSE AGREEMENT"
echo "============================================================"
echo ""

if [ -f "${EULA_FILE}" ]; then
    cat "${EULA_FILE}"
else
    echo "IMPORTANT NOTICE:"
    echo ""
    echo "Anaconda MCP connects an AI assistant (Claude, by Anthropic)"
    echo "to your computing environment. By using this software, you"
    echo "acknowledge that:"
    echo ""
    echo "  - Claude is developed by Anthropic, not Anaconda."
    echo "  - You are solely responsible for the permissions you grant."
    echo "  - Anaconda is NOT liable for any actions Claude takes in"
    echo "    your environment, including unintended changes or deletions."
    echo ""
    echo "Full EULA: https://docs.anaconda.com/anaconda-mcp/eula"
fi

echo ""
echo "============================================================"

# Non-interactive installs (e.g. --yes flag, CI): warn but continue
if [ ! -t 0 ]; then
    echo ""
    echo "[WARNING] Non-interactive install detected."
    echo "By proceeding, you are deemed to have accepted the EULA above."
    echo "Full EULA: https://docs.anaconda.com/anaconda-mcp/eula"
    echo ""
    mkdir -p "$(dirname "${ACCEPTANCE_FLAG}")"
    echo "accepted-non-interactive-$(date -u +%Y-%m-%dT%H:%M:%SZ)" > "${ACCEPTANCE_FLAG}"
    exit 0
fi

echo ""
printf "Do you accept the terms of this End User License Agreement? [yes/no]: "
read -r REPLY </dev/tty

echo ""
if [ "${REPLY}" = "yes" ] || [ "${REPLY}" = "YES" ] || [ "${REPLY}" = "y" ] || [ "${REPLY}" = "Y" ]; then
    mkdir -p "$(dirname "${ACCEPTANCE_FLAG}")"
    echo "accepted-$(date -u +%Y-%m-%dT%H:%M:%SZ)" > "${ACCEPTANCE_FLAG}"
    echo "[OK] EULA accepted. Anaconda MCP installation complete."
    echo ""
else
    echo "[ABORTED] You must accept the EULA to use Anaconda MCP."
    echo "To uninstall: conda remove anaconda-mcp"
    echo ""
    # Exit non-zero to signal to the user, but conda won't rollback at this stage.
    # The flag file is simply not created, and the check above will re-prompt on next install.
    exit 1
fi