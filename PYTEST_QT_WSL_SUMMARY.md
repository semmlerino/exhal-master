# PyQt Testing in WSL - Quick Reference

## ✅ Setup Complete
```bash
pip install pytest-qt
export QT_QPA_PLATFORM=offscreen  # For headless testing
```

## 🎯 Key Testing Patterns Implemented

### 1. Widget Interaction
```python
# Mouse clicks
qtbot.mouseClick(button, Qt.MouseButton.LeftButton)

# Keyboard input
qtbot.keyClicks(line_edit, "Hello")
qtbot.keyClick(widget, Qt.Key.Key_Enter)

# Drag operations
qtbot.mousePress(widget, Qt.MouseButton.LeftButton, pos=start)
qtbot.mouseMove(widget, pos=end)
qtbot.mouseRelease(widget, Qt.MouseButton.LeftButton, pos=end)
```

### 2. Signal Testing
```python
# Wait for signal
with qtbot.waitSignal(widget.clicked):
    qtbot.mouseClick(widget, Qt.MouseButton.LeftButton)

# Capture signal arguments
with qtbot.waitSignal(widget.textChanged) as blocker:
    widget.setText("new text")
assert blocker.args == ["new text"]

# Assert NOT emitted
with qtbot.assertNotEmitted(widget.clicked):
    widget.setEnabled(False)
```

### 3. Async Conditions
```python
# Wait for condition
qtbot.waitUntil(lambda: widget.isVisible())

# Wait for widget exposure
qtbot.waitExposed(widget)

# Simple delay
qtbot.wait(100)  # milliseconds
```

## 📊 Coverage Results
- **Total Coverage**: 51% (up from 34%)
- **Controllers**: 55-100% coverage
- **Workers**: 93% coverage  
- **Utilities**: 98% coverage

## 🚀 Running Tests
```bash
# Headless (recommended for WSL)
QT_QPA_PLATFORM=offscreen pytest

# With xvfb (for OpenGL/rendering)
xvfb-run -a pytest

# Run specific GUI tests
pytest -m gui

# With coverage
pytest --cov=sprite_editor --cov-report=html
```

## 💡 WSL-Specific Tips
1. **Always use `QT_QPA_PLATFORM=offscreen`** for CI/headless
2. **Use `qtbot.wait()` or `qtbot.waitUntil()`** for timing issues
3. **Mock file dialogs** to avoid display dependencies
4. **Test widget states**, not implementation details

## 🔧 Common Issues & Solutions

| Issue | Solution |
|-------|----------|
| "Could not connect to display" | Set `QT_QPA_PLATFORM=offscreen` |
| Widget not visible | Use `qtbot.waitExposed(widget)` |
| Signal timeout | Increase timeout: `waitSignal(..., timeout=5000)` |
| Focus issues | Use `qtbot.waitUntil(lambda: widget.hasFocus())` |

## 📝 Test Files Created
- `test_enhanced_gui_interaction.py` - Advanced qtbot examples
- `PYQT_TESTING_GUIDE.md` - Comprehensive guide
- Enhanced existing tests with proper GUI interaction patterns

All tests run successfully in WSL without requiring an X server! 🎉