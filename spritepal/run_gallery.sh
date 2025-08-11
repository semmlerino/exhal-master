#!/bin/bash
# Simple launcher for the standalone gallery

echo "🚀 Launching SpritePal Detached Gallery..."
echo "================================================"

# Navigate to the correct directory
cd "$(dirname "$0")"

# Check if venv exists
if [ -f "../venv/bin/python" ]; then
    echo "📦 Using virtual environment..."
    ../venv/bin/python launch_detached_gallery.py
else
    echo "❌ Virtual environment not found"
    echo "Please run: cd .. && python -m venv venv && source venv/bin/activate && pip install -r requirements.txt"
    exit 1
fi

echo "👋 Gallery closed"