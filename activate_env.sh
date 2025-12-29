#!/bin/bash
# UV doesn't require traditional venv activation
# UV automatically manages the virtual environment when you run commands with 'uv run'
echo "ℹ️  This project now uses UV for package management!"
echo ""
echo "UV automatically manages the virtual environment."
echo "No activation needed - just use 'uv run' or 'make' commands."
echo ""
echo "Examples:"
echo "  uv run whoop-start    # Start the CLI"
echo "  make run              # Start the CLI (via Makefile)"
echo "  make server           # Start FastAPI server"
echo "  make help             # See all available commands"
echo ""
echo "To use the old venv (if needed):"
echo "  source venv/bin/activate"
