#!/bin/bash
# Run the FastAPI backend server

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"

# Use the venv's Python directly (no need to activate)
PYTHON_BIN="$PROJECT_ROOT/.venv/bin/python"

if [ ! -f "$PYTHON_BIN" ]; then
    echo "❌ Virtual environment not found at $PROJECT_ROOT/.venv"
    echo "Please run: python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt"
    exit 1
fi

echo "✅ Using Python: $PYTHON_BIN"
echo "✅ Starting FastAPI server..."
echo ""

# Change to backend directory and run uvicorn using venv's Python
cd "$SCRIPT_DIR"
"$PYTHON_BIN" -m uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
