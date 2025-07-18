#!/usr/bin/env bash
# Test runner using virtual environment with proper headless support
# IMPORTANT: pytest-xvfb plugin hangs in WSL2, so we disable it and use QT_QPA_PLATFORM=offscreen

# Activate virtual environment
source .venv/bin/activate

# Set environment for headless testing
export QT_QPA_PLATFORM=offscreen
export QT_LOGGING_RULES='*.debug=false'

# Common pytest options for headless testing
PYTEST_OPTS="-v -p no:xvfb"

# Run tests with appropriate markers
if [ "$1" == "gui" ]; then
    echo "Running all tests including GUI tests (with offscreen platform)..."
    pytest $PYTEST_OPTS
elif [ "$1" == "unit" ]; then
    echo "Running unit tests only (no GUI)..."
    pytest $PYTEST_OPTS -m "not gui"
elif [ "$1" == "headless" ]; then
    echo "Running headless-safe tests (GUI tests will be skipped)..."
    pytest $PYTEST_OPTS -m "not gui" --tb=short
elif [ "$1" == "controller" ]; then
    echo "Running controller tests specifically..."
    pytest $PYTEST_OPTS pixel_editor/tests/test_pixel_editor_controller_v3.py --tb=short
elif [ "$1" == "all-pixel-editor" ]; then
    echo "Running all pixel editor tests..."
    pytest $PYTEST_OPTS pixel_editor/tests/ -m "not gui" --tb=short
else
    echo "Running tests with offscreen platform (xvfb plugin disabled)..."
    echo "Available options: gui, unit, headless, controller, all-pixel-editor"
    pytest $PYTEST_OPTS "${@}"
fi