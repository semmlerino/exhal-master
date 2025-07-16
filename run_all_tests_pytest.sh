#!/bin/bash
# Run all tests with pytest and generate coverage report

echo "🧪 Running Sprite Editor Test Suite with pytest"
echo "=============================================="
echo

# Set up environment for headless Qt testing
export QT_QPA_PLATFORM=offscreen

# Run tests with coverage
echo "Running tests with coverage..."
python3 -m pytest \
    --cov=sprite_editor \
    --cov=sprite_editor_unified \
    --cov=pixel_editor \
    --cov-report=html \
    --cov-report=term-missing \
    --cov-branch \
    -v

# Check exit code
if [ $? -eq 0 ]; then
    echo
    echo "✅ All tests passed!"
    echo
    echo "📊 Coverage report generated in htmlcov/index.html"
else
    echo
    echo "❌ Some tests failed!"
    exit 1
fi