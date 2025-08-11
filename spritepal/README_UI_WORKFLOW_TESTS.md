# SpritePal UI Workflow Integration Tests

This directory contains comprehensive integration tests for SpritePal's complete UI workflows using pytest-qt and real Qt widgets.

## Overview

The integration tests validate end-to-end user workflows rather than isolated components:

1. **App startup → dark theme → ROM loading → extraction panel updates**
2. **Manual offset button → dialog → slider interaction → preview updates**  
3. **Sprite found → signal propagation → main window updates**
4. **Tab switching in dialogs → state preservation → signal functionality**
5. **Window resizing → layout adjustments → theme preservation**

## Files

- `test_complete_ui_workflows_integration.py` - Main integration test suite
- `test_ui_interaction_examples.py` - Advanced qtbot usage patterns
- `run_ui_workflow_tests.py` - Test runner with environment setup
- `README_UI_WORKFLOW_TESTS.md` - This documentation

## Prerequisites

Install required dependencies:

```bash
pip install pytest pytest-qt PySide6
```

For headless testing on Linux:
```bash
sudo apt-get install xvfb
```

## Running Tests

### Quick Start

Run all workflow tests:
```bash
python run_ui_workflow_tests.py
```

### Headless Mode (CI/CD)

For continuous integration:
```bash
python run_ui_workflow_tests.py --headless
```

### Specific Workflows

Run specific workflow tests:
```bash
python run_ui_workflow_tests.py --test=startup
python run_ui_workflow_tests.py --test=manual_offset
python run_ui_workflow_tests.py --test=signals
```

### Interactive Mode

Choose workflows interactively:
```bash
python run_ui_workflow_tests.py --interactive
```

### Direct pytest Execution

You can also run tests directly with pytest:

```bash
# All GUI integration tests
pytest test_complete_ui_workflows_integration.py -m gui -v

# Specific test method
pytest test_complete_ui_workflows_integration.py::TestCompleteUIWorkflowsIntegration::test_app_startup_dark_theme_rom_loading_workflow -v

# With xvfb (headless)
xvfb-run -a pytest test_complete_ui_workflows_integration.py -m gui -v
```

## Test Architecture

### Real Qt Widgets, Not Mocks

These tests use **real Qt widgets** with qtbot for authentic user interactions:

```python
# Real MainWindow instance
main_window = MainWindow()
qtbot.addWidget(main_window)
main_window.show()
qtbot.waitForWindowShown(main_window)

# Real mouse interactions
qtbot.mouseClick(button, Qt.MouseButton.LeftButton)

# Real signal monitoring
spy = QSignalSpy(widget.signal_name)
```

### Key Testing Patterns

#### 1. Dark Theme Verification
```python
def _verify_dark_theme_applied(self, widget: QWidget) -> bool:
    palette = widget.palette()
    bg_color = palette.color(QPalette.ColorRole.Window)
    return bg_color.red() < 128 and bg_color.green() < 128
```

#### 2. Signal Propagation Testing
```python
with qtbot.waitSignal(worker.finished, timeout=5000) as blocker:
    worker.start()
assert blocker.args[0] == expected_result
```

#### 3. User Interaction Simulation
```python
# Slider dragging
qtbot.mousePress(slider, Qt.MouseButton.LeftButton, pos=start_pos)
qtbot.mouseMove(slider, end_pos)
qtbot.mouseRelease(slider, Qt.MouseButton.LeftButton, pos=end_pos)

# Keyboard shortcuts
qtbot.keySequence(dialog, QKeySequence("Ctrl+T"))
```

#### 4. Layout and Resizing Tests
```python
# Test window resizing
original_size = window.size()
window.resize(QSize(800, 600))
qtbot.wait(100)  # Allow layout update

# Verify components still work
assert self._verify_dark_theme_applied(window)
```

## Test Markers

Tests use pytest markers for organization:

- `@pytest.mark.gui` - Requires display/xvfb
- `@pytest.mark.integration` - End-to-end testing  
- `@pytest.mark.serial` - No parallel execution
- `@pytest.mark.slow` - UI tests take time

## Environment Setup

The test runner automatically handles:

- Qt platform configuration (`QT_QPA_PLATFORM=offscreen`)
- Display detection and xvfb setup
- Python path configuration
- Manager initialization/cleanup

## Workflow Test Details

### 1. App Startup & Dark Theme (`test_app_startup_dark_theme_rom_loading_workflow`)

Validates:
- MainWindow creation and display
- Dark theme application and verification
- ROM loading workflow with file dialogs
- UI responsiveness during operations

### 2. Manual Offset Dialog (`test_manual_offset_dialog_interaction_workflow`)

Validates:
- Dialog opening from main window
- Real slider interaction with mouse/keyboard
- Signal emission and handling
- Dark theme in modal dialogs

### 3. Signal Propagation (`test_sprite_found_signal_propagation_workflow`)

Validates:
- Cross-component signal connections
- Main window receiving and handling signals
- UI updates in response to signals
- Multiple signal handling

### 4. Tab State Preservation (`test_manual_offset_tab_switching_state_preservation_workflow`)

Validates:
- Tab widget navigation
- State preservation across tab switches
- Signal functionality after tab changes
- Form input persistence

### 5. Window Resizing (`test_window_resize_layout_theme_preservation_workflow`)

Validates:
- Layout responsiveness to size changes
- Theme preservation during resize
- Component positioning and visibility
- Minimum size constraints

### 6. UI Responsiveness (`test_ui_responsiveness_during_workflows`)

Validates:
- No blocking operations on main thread
- Rapid interaction handling
- Smooth animations and updates
- Performance under load

### 7. Error Recovery (`test_error_recovery_in_ui_workflows`)

Validates:
- Graceful error handling
- UI stability after errors  
- Recovery capabilities
- Error state isolation

## Benefits Over Unit Tests

These integration tests provide:

1. **Real User Experience Validation** - Tests actual workflows users perform
2. **Cross-Component Integration** - Validates components work together
3. **Visual and Behavioral Testing** - Tests appearance and responsiveness
4. **Signal Architecture Validation** - Tests real Qt signal propagation
5. **Theme and Layout Testing** - Validates visual consistency
6. **Error Scenario Coverage** - Tests recovery and stability

## CI/CD Integration

For continuous integration, use headless mode:

```yaml
# GitHub Actions example
- name: Run UI Workflow Tests
  run: |
    sudo apt-get install -y xvfb
    python run_ui_workflow_tests.py --headless --coverage
```

## Troubleshooting

### Common Issues

**"No display" errors:**
- Use `--headless` flag or set `QT_QPA_PLATFORM=offscreen`
- Install xvfb on Linux systems

**Import errors:**
- Ensure project root is in Python path
- Check all dependencies are installed

**Test timeouts:**
- Increase qtbot timeout values for slow systems
- Use `qtbot.wait()` after UI operations

**Qt application conflicts:**
- Tests are marked `serial` to avoid Qt singleton issues
- Each test properly cleans up widgets

### Debug Mode

Run with verbose output for debugging:
```bash
python run_ui_workflow_tests.py --verbose --test=specific_test_name
```

## Contributing

When adding new workflow tests:

1. Use real Qt widgets, not mocks when possible
2. Test complete user workflows, not isolated functions
3. Include proper setup/cleanup fixtures
4. Add appropriate pytest markers
5. Verify dark theme and layout behavior
6. Test both success and error scenarios

## Integration with Existing Tests

These workflow tests complement the existing test suite:

- **Unit tests** - Fast, isolated component testing
- **Integration tests (these)** - End-to-end workflow validation  
- **Performance tests** - Load and stress testing
- **Visual tests** - Screenshot comparison testing

Together they provide comprehensive coverage of SpritePal's functionality.
EOF < /dev/null
