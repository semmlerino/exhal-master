#!/bin/bash
# Run tests in headless environment (WSL/Docker/CI)

echo "Running tests with Qt offscreen platform for headless environment..."

# Set the Qt platform to offscreen to avoid display connection issues
export QT_QPA_PLATFORM=offscreen

# Run pytest with all arguments passed to this script
python3 -m pytest "$@"