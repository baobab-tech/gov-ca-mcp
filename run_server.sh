#!/usr/bin/env bash
# MCP Server runner script
# This script can be used directly with MCP Inspector

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Use the virtual environment's Python
exec "$SCRIPT_DIR/venv/bin/python" -m gov_mcp.server "$@"
