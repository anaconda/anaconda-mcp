#!/usr/bin/env bash
# Copyright (c) Anaconda, Inc.
#
# Apache-2.0 License

# Wrapper script to launch anaconda-mcp server from Claude Desktop.
#
# Claude Desktop is a GUI app and does not inherit terminal environment
# variables (like CONDA_PREFIX). This script sources the user's shell
# profiles to initialize conda, then launches the Python server from
# the anaconda-mcp conda environment.

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Source shell profiles to get conda initialized.
# Try multiple files to handle both macOS (zsh default) and Linux (bash default).
for rc in "$HOME/.zshrc" "$HOME/.bashrc" "$HOME/.bash_profile" "$HOME/.profile"; do
    if [ -f "$rc" ]; then
        source "$rc" 2>/dev/null
        if [ -n "$CONDA_PREFIX" ]; then
            break
        fi
    fi
done

if [ -z "$CONDA_PREFIX" ]; then
    echo "Error: Could not find conda installation. Please ensure conda is initialized in your shell (run 'conda init')." >&2
    exit 1
fi

PYTHON="${CONDA_PREFIX}/envs/anaconda-mcp/bin/python"

if [ ! -x "$PYTHON" ]; then
    echo "Error: Python not found at ${PYTHON}" >&2
    echo "Please create the anaconda-mcp conda environment:" >&2
    echo "  conda create -n anaconda-mcp anaconda-mcp" >&2
    exit 1
fi

exec "$PYTHON" "${SCRIPT_DIR}/server.py"
