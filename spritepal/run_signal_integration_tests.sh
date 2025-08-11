#!/bin/bash
# Run Qt signal/slot integration tests with proper environment setup

# Activate virtual environment
source venv/bin/activate

# Set environment to enable GUI tests
export DISPLAY=:99
export CI=""
export QT_QPA_PLATFORM=""
export SPRITEPAL_HEADLESS_OVERRIDE=false

echo "==================================================================================="
echo "Running Qt Signal/Slot Integration Tests"
echo "==================================================================================="
echo ""
echo "Environment:"
echo "  DISPLAY=$DISPLAY"
echo "  Python: $(which python)"
echo "  PySide6: $(python -c 'import PySide6; print(PySide6.__version__)' 2>/dev/null || echo 'Not installed')"
echo ""

# Run tests with xvfb for GUI support
echo "Running signal/slot connection tests..."
xvfb-run -a python -m pytest \
    tests/integration/test_qt_signal_slot_integration.py \
    tests/integration/test_qt_threading_signals.py \
    tests/integration/test_dialog_singleton_signals.py \
    -v \
    --tb=short \
    --color=yes \
    -m "gui or not gui" \
    2>&1 | tee signal_test_results.txt

# Check results
if [ ${PIPESTATUS[0]} -eq 0 ]; then
    echo ""
    echo "==================================================================================="
    echo "✓ All signal/slot integration tests passed!"
    echo "==================================================================================="
    exit 0
else
    echo ""
    echo "==================================================================================="
    echo "✗ Some tests failed. See signal_test_results.txt for details."
    echo "==================================================================================="
    exit 1
fi