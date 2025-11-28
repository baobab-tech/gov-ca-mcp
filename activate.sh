#!/bin/bash
# Quick activation script for the Government MCP Server environment

# Get the directory where this script is located
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

echo "🚀 Activating Government MCP Server environment..."
echo "   Directory: $DIR"

# Activate the virtual environment
if [ -f "$DIR/venv/bin/activate" ]; then
    source "$DIR/venv/bin/activate"
    echo "✓ Virtual environment activated"
    echo "✓ Python: $(python --version)"
    echo ""
    echo "Next steps:"
    echo "  - Start server: python -m gov_mcp.server"
    echo "  - Run examples: python examples.py"
    echo "  - Run tests:    python test_server.py"
else
    echo "❌ Virtual environment not found at $DIR/venv"
    echo "Please run: pip install -e ."
    exit 1
fi
