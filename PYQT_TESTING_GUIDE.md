# PyQt Testing Guide for pytest in WSL

## Quick Start

### Setup
```bash
# Install required packages
pip install pytest pytest-qt pytest-cov

# Run tests headless (no display required)
QT_QPA_PLATFORM=offscreen pytest

# Or add to pytest.ini
[pytest]
qt_qpa_platform = offscreen
```

### Basic Test Structure
```python
import pytest
from PyQt6.QtWidgets import QPushButton
from PyQt6.QtCore import Qt

@pytest.fixture
def widget(qtbot):
    """Create widget with qtbot fixture"""
    button = QPushButton("Click Me")
    qtbot.addWidget(button)
    button.show()
    qtbot.waitExposed(button)
    return button

def test_button_click(widget, qtbot):
    """Test button interaction"""
    with qtbot.waitSignal(widget.clicked):
        qtbot.mouseClick(widget, Qt.MouseButton.LeftButton)
```

## Key Features of pytest-qt

### 1. Widget Interaction
```python
# Mouse clicks
qtbot.mouseClick(widget, Qt.MouseButton.LeftButton)
qtbot.mouseClick(widget, Qt.MouseButton.RightButton, pos=QPoint(10, 10))

# Keyboard input
qtbot.keyClicks(line_edit, "Hello World")
qtbot.keyClick(widget, Qt.Key.Key_Enter)
qtbot.keyClick(widget, Qt.Key.Key_A, Qt.KeyboardModifier.ControlModifier)

# Mouse drag
qtbot.mousePress(widget, Qt.MouseButton.LeftButton, pos=start)
qtbot.mouseMove(widget, pos=end)
qtbot.mouseRelease(widget, Qt.MouseButton.LeftButton, pos=end)
```

### 2. Signal Testing
```python
# Wait for signal
with qtbot.waitSignal(widget.textChanged, timeout=1000) as blocker:
    widget.setText("new text")
assert blocker.args == ["new text"]

# Assert signal NOT emitted
with qtbot.assertNotEmitted(widget.clicked):
    widget.setEnabled(False)

# Wait for multiple signals
with qtbot.waitSignals([signal1, signal2]):
    trigger_both_signals()
```

### 3. Timing and Conditions
```python
# Wait for condition
qtbot.waitUntil(lambda: widget.text() == "Ready", timeout=5000)

# Simple delay
qtbot.wait(500)  # milliseconds

# Wait for widget to be visible
qtbot.waitExposed(widget)
```

## Running Tests in WSL

### Option 1: Headless (Recommended)
```bash
# Set environment variable
export QT_QPA_PLATFORM=offscreen

# Or run directly
QT_QPA_PLATFORM=offscreen pytest

# In pytest.ini
[pytest]
env = 
    QT_QPA_PLATFORM=offscreen
```

### Option 2: With xvfb (for OpenGL/full rendering)
```bash
# Install xvfb
sudo apt-get install xvfb

# Run tests
xvfb-run -a pytest

# With specific display
xvfb-run --server-args="-screen 0 1024x768x24" pytest
```

## Best Practices

### 1. Fixture Organization
```python
@pytest.fixture
def app(qtbot):
    """Application-level fixture"""
    widget = MyApplication()
    qtbot.addWidget(widget)
    widget.show()
    qtbot.waitExposed(widget)
    yield widget
    widget.close()

@pytest.fixture
def logged_in_app(app):
    """Composed fixture with setup"""
    app.login("testuser", "testpass")
    return app
```

### 2. Testing Complex Workflows
```python
def test_complete_workflow(app, qtbot):
    """Test multi-step workflow"""
    # Step 1: Open dialog
    qtbot.mouseClick(app.open_button, Qt.MouseButton.LeftButton)
    
    # Step 2: Wait for dialog
    qtbot.waitUntil(lambda: app.dialog.isVisible())
    
    # Step 3: Fill form
    qtbot.keyClicks(app.dialog.name_input, "Test Name")
    
    # Step 4: Submit
    with qtbot.waitSignal(app.dialog.accepted):
        qtbot.mouseClick(app.dialog.ok_button, Qt.MouseButton.LeftButton)
    
    # Verify results
    assert app.current_name == "Test Name"
```

### 3. Handling Dialogs
```python
def test_dialog_interaction(app, qtbot):
    """Test dialog handling"""
    def handle_dialog():
        # Wait for dialog to appear
        qtbot.waitUntil(lambda: isinstance(app.activeWindow(), QMessageBox))
        dialog = app.activeWindow()
        # Click OK
        qtbot.mouseClick(dialog.button(QMessageBox.StandardButton.Ok), 
                        Qt.MouseButton.LeftButton)
    
    # Schedule dialog handler
    QTimer.singleShot(100, handle_dialog)
    
    # Trigger dialog
    app.show_message()
```

### 4. Testing Async Operations
```python
def test_async_operation(app, qtbot):
    """Test async operations with signals"""
    with qtbot.waitSignal(app.operation_complete, timeout=5000) as blocker:
        app.start_async_operation()
    
    # Check signal arguments
    success, result = blocker.args
    assert success is True
    assert result == "Expected result"
```

## Common Issues and Solutions

### 1. "Could not connect to display"
```bash
# Solution: Use offscreen platform
QT_QPA_PLATFORM=offscreen pytest
```

### 2. Widget not found/not visible
```python
# Solution: Ensure widget is shown and exposed
widget.show()
qtbot.waitExposed(widget)
```

### 3. Signal timeout
```python
# Solution: Increase timeout or check signal is actually emitted
with qtbot.waitSignal(signal, timeout=5000):  # 5 seconds
    trigger_action()
```

### 4. Focus issues
```python
# Solution: Explicitly set focus
widget.setFocus()
qtbot.waitUntil(lambda: widget.hasFocus())
```

## Advanced Patterns

### Custom Assertions
```python
def assert_widget_state(widget, enabled=True, visible=True, text=None):
    """Custom assertion helper"""
    assert widget.isEnabled() == enabled
    assert widget.isVisible() == visible
    if text is not None:
        assert widget.text() == text
```

### Testing Drag and Drop
```python
def test_drag_drop(source, target, qtbot):
    """Test drag and drop operation"""
    # Start drag
    qtbot.mousePress(source, Qt.MouseButton.LeftButton)
    
    # Move to target
    source_pos = source.mapToGlobal(source.rect().center())
    target_pos = target.mapToGlobal(target.rect().center())
    
    # Simulate drag
    qtbot.mouseMove(source, pos=source_pos)
    qtbot.mouseMove(target, pos=target_pos)
    
    # Drop
    qtbot.mouseRelease(target, Qt.MouseButton.LeftButton)
```

### Parameterized GUI Tests
```python
@pytest.mark.parametrize("input_text,expected", [
    ("123", 123),
    ("abc", 0),  # Invalid input
    ("", 0),     # Empty input
])
def test_numeric_input(qtbot, input_text, expected):
    """Test various inputs"""
    spinbox = QSpinBox()
    qtbot.addWidget(spinbox)
    
    qtbot.keyClicks(spinbox, input_text)
    assert spinbox.value() == expected
```

## Performance Tips

1. **Reuse fixtures** when possible to avoid recreating widgets
2. **Use class-based tests** to share setup between related tests  
3. **Mock heavy operations** (file I/O, network) in GUI tests
4. **Set smaller timeouts** in CI to fail fast
5. **Run GUI tests in parallel** with pytest-xdist (if tests are independent)

```bash
# Parallel execution
pytest -n auto
```