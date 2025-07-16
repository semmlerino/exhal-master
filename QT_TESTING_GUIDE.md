# Comprehensive Guide to PyQt6 GUI Testing

This guide synthesizes best practices, tools, and real-world solutions for testing PyQt6 applications based on extensive research and industry standards.

## Table of Contents
1. [Core Principles](#core-principles)
2. [Testing Framework Setup](#testing-framework-setup)
3. [Virtual Display Solutions](#virtual-display-solutions)
4. [Test Organization](#test-organization)
5. [Common Patterns](#common-patterns)
6. [CI/CD Configuration](#cicd-configuration)
7. [Troubleshooting](#troubleshooting)
8. [Platform-Specific Considerations](#platform-specific-considerations)

## Core Principles

### 1. **Use pytest-qt**
The de facto standard for PyQt/PySide testing. Used by virtually all successful PyQt projects.

### 2. **Prefer Real Components Over Mocks**
Test with actual Qt widgets when possible. Use virtual displays (Xvfb) rather than mocking.

### 3. **Proper Test Isolation**
Each test should be independent. Use fixtures and proper cleanup.

### 4. **Platform Testing**
Test on Linux, Windows, and macOS in CI/CD.

## Testing Framework Setup

### Essential Dependencies
```bash
# Core testing libraries
pip install pytest pytest-qt pytest-xvfb pytest-cov

# System dependencies (Ubuntu/Debian)
sudo apt-get install -y \
    xvfb \
    libxkbcommon-x11-0 \
    libxcb-icccm4 \
    libxcb-image0 \
    libxcb-keysyms1 \
    libxcb-randr0 \
    libxcb-render-util0 \
    libxcb-xinerama0 \
    libxcb-xfixes0 \
    x11-utils
```

### pytest.ini Configuration
```ini
[tool:pytest]
testpaths = tests
qt_api = pyqt6

# Xvfb configuration (when using pytest-xvfb)
xvfb_width = 1280
xvfb_height = 1024
xvfb_colordepth = 24

markers =
    unit: Unit tests (no GUI required)
    integration: Integration tests
    gui: GUI tests requiring display
    slow: Slow running tests

addopts = 
    -v
    --strict-markers
    --tb=short
```

## Virtual Display Solutions

### 1. **pytest-xvfb (Recommended)**
Automatically manages Xvfb lifecycle.

```python
# Just install and run - no code changes needed
pip install pytest-xvfb
pytest  # Xvfb starts automatically
```

**Benefits:**
- Zero configuration
- Automatic cleanup
- Works in CI/CD
- Platform detection

### 2. **Manual Xvfb**
For more control or specific requirements.

```bash
# Start Xvfb
Xvfb :99 -screen 0 1280x1024x24 &
export DISPLAY=:99
pytest
```

### 3. **Alternative Backends**

| Backend | Use Case | Setup |
|---------|----------|-------|
| Xvfb | Standard CI/CD | `pytest-xvfb` |
| Xdummy | RANDR support needed | Manual setup |
| Xvnc | Visual debugging | `Xvnc :1` |
| Offscreen | Fallback only | `QT_QPA_PLATFORM=offscreen` |

## Test Organization

### Recommended Structure
```
project/
├── src/
│   └── myapp/
├── tests/
│   ├── conftest.py      # Shared fixtures
│   ├── unit/            # No GUI required
│   ├── integration/     # Component integration
│   └── gui/             # Full GUI tests
└── pytest.ini
```

### Fixture Best Practices
```python
# conftest.py
import pytest
from PyQt6.QtCore import Qt

@pytest.fixture
def main_window(qtbot):
    """Create main window for testing."""
    from myapp.main_window import MainWindow
    window = MainWindow()
    qtbot.addWidget(window)  # Ensures cleanup
    window.show()
    qtbot.waitExposed(window)  # Wait for window
    return window

@pytest.fixture
def click_button(qtbot):
    """Helper to click buttons."""
    def _click(button):
        qtbot.mouseClick(button, Qt.MouseButton.LeftButton)
    return _click
```

## Common Patterns

### Testing Signals
```python
def test_signal_emission(qtbot, main_window):
    """Test signal emission with timeout."""
    with qtbot.waitSignal(main_window.data_loaded, timeout=1000) as blocker:
        main_window.load_data()
    
    # Check signal arguments
    assert blocker.args == [expected_data]
```

### Testing Async Operations
```python
def test_async_operation(qtbot, main_window):
    """Test async operations."""
    def check_result():
        return main_window.result is not None
    
    main_window.start_async_operation()
    qtbot.waitUntil(check_result, timeout=5000)
    assert main_window.result == expected_value
```

### Testing Dialogs
```python
def test_dialog(qtbot, monkeypatch, main_window):
    """Test dialog interaction."""
    # Mock dialog exec
    monkeypatch.setattr(QMessageBox, "exec", lambda *args: QMessageBox.StandardButton.Ok)
    
    main_window.show_dialog()
    assert main_window.dialog_result == "ok"
```

### Testing Worker Threads
```python
def test_worker_thread(qtbot, main_window):
    """Test QThread worker."""
    with qtbot.waitSignal(main_window.worker.finished, timeout=2000):
        main_window.start_worker()
    
    assert main_window.worker_result is not None
```

## CI/CD Configuration

### GitHub Actions (Complete Example)
```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ${{ matrix.os }}
    strategy:
      matrix:
        python-version: ['3.8', '3.9', '3.10', '3.11']
        os: [ubuntu-latest, windows-latest, macos-latest]
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: ${{ matrix.python-version }}
    
    - name: Install system dependencies (Linux)
      if: runner.os == 'Linux'
      run: |
        sudo apt-get update
        sudo apt-get install -y xvfb libxkbcommon-x11-0 libxcb-icccm4 \
          libxcb-image0 libxcb-keysyms1 libxcb-randr0 libxcb-render-util0 \
          libxcb-xinerama0 libxcb-xfixes0 x11-utils
    
    - name: Install Python dependencies
      run: |
        pip install --upgrade pip
        pip install pytest pytest-qt pytest-xvfb pytest-cov
        pip install -r requirements.txt
    
    - name: Run tests (Linux/macOS)
      if: runner.os != 'Windows'
      run: pytest --cov=src --cov-report=xml
    
    - name: Run tests (Windows)
      if: runner.os == 'Windows'
      env:
        QT_QPA_PLATFORM: offscreen
      run: pytest --cov=src --cov-report=xml -m "not gui"
    
    - name: Upload coverage
      uses: codecov/codecov-action@v3
```

### Docker Configuration
```dockerfile
FROM python:3.11

# Install system dependencies
RUN apt-get update && apt-get install -y \
    xvfb \
    libxkbcommon-x11-0 \
    libxcb-icccm4 \
    libxcb-image0 \
    libxcb-keysyms1 \
    libxcb-randr0 \
    libxcb-render-util0 \
    libxcb-xinerama0 \
    libxcb-xfixes0 \
    x11-utils \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install -r requirements.txt
RUN pip install pytest pytest-qt pytest-xvfb

# Copy application
COPY . /app
WORKDIR /app

# Run tests with Xvfb
CMD ["pytest"]
```

## Troubleshooting

### Common Issues and Solutions

#### 1. **"could not connect to display"**
```bash
# Solution: Install and use pytest-xvfb
pip install pytest-xvfb
# Or manually start Xvfb
Xvfb :99 &
export DISPLAY=:99
```

#### 2. **"QThread tests hanging"**
```python
# Use proper timeout
with qtbot.waitSignal(worker.finished, timeout=2000, raising=True):
    worker.start()
```

#### 3. **"Platform plugin not found"**
```bash
# Install Qt platform plugins
sudo apt-get install qt6-qpa-plugins
# Or use offscreen as fallback
export QT_QPA_PLATFORM=offscreen
```

#### 4. **Tests pass locally but fail in CI**
- Check system dependencies installation
- Verify DISPLAY environment variable
- Use pytest-xvfb for consistency
- Add debugging output:
```python
import os
print(f"DISPLAY={os.environ.get('DISPLAY', 'not set')}")
print(f"QT_QPA_PLATFORM={os.environ.get('QT_QPA_PLATFORM', 'not set')}")
```

## Platform-Specific Considerations

### Linux
- Use Xvfb or pytest-xvfb
- Install all X11 dependencies
- Works well in Docker

### Windows
- Limited virtual display options
- Use `QT_QPA_PLATFORM=offscreen` for CI
- Consider Windows-specific test suite

### macOS
- No native Xvfb support
- Use `QT_QPA_PLATFORM=offscreen`
- Or use Docker with X11 forwarding

### WSL2
```bash
# With WSLg (GUI support)
export DISPLAY=:0
pytest

# Without WSLg
pip install pytest-xvfb
pytest
```

## Best Practices Summary

1. **Start Simple**: Use pytest-xvfb for automatic setup
2. **Organize Tests**: Separate unit, integration, and GUI tests
3. **Use Fixtures**: Leverage pytest-qt fixtures extensively
4. **Clean Up**: Always use qtbot.addWidget() for proper cleanup
5. **Test Signals**: Use waitSignal() for reliable signal testing
6. **Handle Async**: Use waitUntil() for async operations
7. **Platform Aware**: Test on all target platforms
8. **Performance**: Run fast tests frequently, full suite on main branches
9. **Debug Visually**: Use Xvnc when you need to see tests running
10. **Document Issues**: Keep notes on platform-specific quirks

## Example Test Suite

```python
# test_example.py
import pytest
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QPushButton

class TestMainWindow:
    """Example test class following best practices."""
    
    @pytest.fixture
    def window(self, qtbot):
        """Create window fixture."""
        from myapp import MainWindow
        window = MainWindow()
        qtbot.addWidget(window)
        window.show()
        qtbot.waitExposed(window)
        return window
    
    def test_button_click(self, qtbot, window):
        """Test button interaction."""
        button = window.findChild(QPushButton, "submit_button")
        qtbot.mouseClick(button, Qt.MouseButton.LeftButton)
        assert window.status_label.text() == "Submitted"
    
    def test_async_load(self, qtbot, window):
        """Test async data loading."""
        with qtbot.waitSignal(window.load_complete, timeout=1000):
            window.load_data()
        assert window.data is not None
```

This guide represents the current best practices for PyQt6 testing as of 2025, based on successful open-source projects and industry standards.