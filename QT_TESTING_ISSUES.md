# Qt Testing Issues and Solutions

## Problem Summary

When running all tests together, Qt tests can fail with "Fatal Python error: Aborted" due to:

1. **QApplication Singleton**: Qt only allows one QApplication instance per process
2. **Event Loop Conflicts**: Multiple tests trying to manage the Qt event loop
3. **Resource Cleanup**: Widgets not properly cleaned up between tests
4. **Platform Issues**: Qt needs specific configuration for headless testing

## Solutions Implemented

### 1. Updated conftest.py
- Added Qt configuration fixtures
- Set `QT_QPA_PLATFORM=offscreen` for headless testing
- Added automatic widget cleanup between tests
- Made Qt fixtures conditional to avoid import errors

### 2. Test Grouping
Created `run_tests_grouped.py` to run tests in isolated groups:
- Group 1: Unit tests (no Qt)
- Group 2: Integration tests without GUI
- Group 3: GUI tests (isolated)
- Group 4: Other unmarked tests

### 3. Environment Configuration
- Set Qt to use offscreen rendering
- Disabled GPU acceleration
- Configured logging to reduce noise

## How to Run Tests

### Option 1: Run All Tests Safely (Recommended)
```bash
python3 run_tests_grouped.py
```

### Option 2: Run Specific Test Groups
```bash
# Unit tests only
python3 -m pytest -m unit

# GUI tests only (with proper Qt setup)
QT_QPA_PLATFORM=offscreen python3 -m pytest -m gui

# Non-GUI tests
python3 -m pytest -m "not gui"
```

### Option 3: Run Individual Test Files
```bash
# Safe for non-Qt tests
python3 -m pytest sprite_editor/tests/test_validation.py

# For Qt tests, use environment variable
QT_QPA_PLATFORM=offscreen python3 -m pytest sprite_editor/tests/test_main_window.py
```

## Best Practices

1. **Mark your tests**: Use pytest markers
   ```python
   @pytest.mark.unit      # Fast, no dependencies
   @pytest.mark.gui       # Requires Qt
   @pytest.mark.integration  # May need files/resources
   ```

2. **Use qtbot fixture**: For GUI tests
   ```python
   def test_widget(qtbot):
       widget = MyWidget()
       qtbot.addWidget(widget)  # Ensures cleanup
   ```

3. **Avoid QApplication.instance()**: Use qtbot's qapp instead
   ```python
   def test_app(qtbot):
       app = qtbot.qapp  # Use this, not QApplication.instance()
   ```

4. **Clean up resources**: Close windows and delete widgets
   ```python
   def test_window(qtbot):
       window = MainWindow()
       qtbot.addWidget(window)
       # Test...
       window.close()  # Explicit cleanup
   ```

## Troubleshooting

### "Fatal Python error: Aborted"
- Run tests in groups using `run_tests_grouped.py`
- Check for multiple QApplication creations
- Ensure widgets are properly cleaned up

### "QWidget: Must construct a QApplication"
- Test is missing qtbot fixture
- QApplication not initialized properly
- Add `@pytest.mark.gui` to the test

### "Platform plugin could not be initialized"
- Set `QT_QPA_PLATFORM=offscreen` environment variable
- Install Qt platform plugins if missing

### Tests hang or freeze
- Event loop issues - use qtbot.wait() instead of time.sleep()
- Modal dialogs blocking - mock them out
- Infinite loops in signal handlers

## CI/CD Considerations

For CI environments, always:
1. Set `QT_QPA_PLATFORM=offscreen`
2. Use xvfb-run if full rendering needed
3. Run GUI tests separately from other tests
4. Set reasonable timeouts for GUI tests