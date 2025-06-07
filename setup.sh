#!/bin/sh
#
# setup.sh — PeerCache Session Setup Script
#
# Description:
#   Prepares the current terminal session by defining a command `peercache`
#   that runs your peer-to-peer simulation script (`main.py`).
#   This works on macOS, Linux, and Windows (via Git Bash or WSL),
#   and supports POSIX-compliant shells like Bash, Zsh, and Dash.
#
# Usage:
#   source setup.sh
#
# Notes:
#   - Do NOT run with `bash setup.sh`; instead, use `source setup.sh` to persist the function.
#   - This script is shell-agnostic but assumes Python 3 is installed and accessible.
#
# Author: Priyanshu Mehta
# Date: June 2025
# Version: 1.0.1

MAIN_PY_PATH="$PWD/main.py"

if ! command -v python3 >/dev/null 2>&1; then
    echo "Error: Python 3 is not installed or not in PATH"
    return 1 2>/dev/null || exit 1
fi

if [ ! -f "$MAIN_PY_PATH" ]; then
    echo "Error: main.py not found at: $MAIN_PY_PATH"
    return 1 2>/dev/null || exit 1
fi

if alias peercache >/dev/null 2>&1; then
    unalias peercache
    echo "Previous alias 'peercache' was found and removed to avoid conflict."
fi

peercache() {
    python3 "$MAIN_PY_PATH" "$@"
}

if [ -n "$BASH_VERSION" ]; then
    export -f peercache
fi

echo "You can run it in this terminal using: peercache (Example: peercache --help)"
