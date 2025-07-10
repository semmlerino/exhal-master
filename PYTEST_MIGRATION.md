# Pytest Migration Guide

## Overview
The Sprite Editor test suite has been migrated from unittest to pytest for better test organization, fixtures, and tooling support.

## Running Tests

### Basic Test Running
```bash
# Run all tests
./run_tests_pytest.py

# Run specific test file
./run_tests_pytest.py sprite_editor/tests/test_project_management.py

# Run specific test class
./run_tests_pytest.py sprite_editor/tests/test_project_management.py::TestProjectManagement

# Run specific test
./run_tests_pytest.py -k test_new_project_creation
```

### Running with Markers
```bash
# Run only unit tests
./run_tests_pytest.py -m unit

# Run integration tests
./run_tests_pytest.py -m integration

# Run GUI tests
./run_tests_pytest.py -m gui

# Run project management tests
./run_tests_pytest.py -m project
```

### Coverage Reports
```bash
# Run all tests with coverage
./run_all_tests_pytest.sh

# View HTML coverage report
open htmlcov/index.html
```

## Writing Tests

### Test Structure
```python
import pytest
from unittest.mock import patch, MagicMock

@pytest.mark.unit  # Mark test category
class TestFeature:
    """Test feature functionality"""
    
    def test_something(self, fixture_name):
        """Test description"""
        # Test implementation
        assert result == expected
```

### Common Fixtures

#### Qt Application Fixture
```python
@pytest.fixture
def editor(qtbot):
    """Create editor instance with Qt support"""
    editor = UnifiedSpriteEditor()
    qtbot.addWidget(editor)
    yield editor
```

#### Temporary Directory
```python
@pytest.fixture
def temp_dir():
    """Create temporary directory"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir
```

### Mocking
```python
# Mock Qt dialogs
with patch('PyQt6.QtWidgets.QFileDialog.getSaveFileName') as mock_dialog:
    mock_dialog.return_value = ('/path/to/file.ksproj', 'Filter')
    # Test code

# Mock message boxes
with patch.object(QMessageBox, 'critical') as mock_critical:
    # Test code
    mock_critical.assert_called_once()
```

## Test Markers

| Marker | Description | Example |
|--------|-------------|---------|
| `unit` | Fast unit tests | Core algorithms, utilities |
| `integration` | Integration tests | Multi-component workflows |
| `gui` | GUI tests requiring Qt | Widget interactions |
| `project` | Project management | File save/load |
| `backup` | File backup tests | Backup creation |
| `slow` | Slow tests (>1s) | Large file operations |

## Environment Setup

### Headless Testing
Tests automatically run with `QT_QPA_PLATFORM=offscreen` for headless environments.

### Manual Environment Setup
```bash
# For headless testing
export QT_QPA_PLATFORM=offscreen

# For visible GUI testing (debugging)
export QT_QPA_PLATFORM=xcb
./run_tests_pytest.py --headed
```

## Migration Notes

### Key Changes from unittest
1. **No TestCase inheritance** - Use plain classes
2. **Fixtures instead of setUp/tearDown** - More flexible and reusable
3. **Better assertions** - Use plain `assert` statements
4. **Parametrization** - Easy test data variation
5. **Better Qt integration** - pytest-qt plugin

### Example Migration
```python
# Before (unittest)
class TestFeature(unittest.TestCase):
    def setUp(self):
        self.app = QApplication([])
        self.widget = MyWidget()
    
    def tearDown(self):
        self.widget.close()
    
    def test_something(self):
        self.assertEqual(self.widget.value, 42)

# After (pytest)
@pytest.fixture
def widget(qtbot):
    widget = MyWidget()
    qtbot.addWidget(widget)
    yield widget

def test_something(widget):
    assert widget.value == 42
```

## Troubleshooting

### Qt Application Crashes
- Ensure `QT_QPA_PLATFORM=offscreen` is set
- Use `qtbot` fixture for Qt widgets
- Don't create QApplication manually

### Import Errors
- Check `pythonpath = .` in pytest.ini
- Verify test file locations

### Coverage Issues
- Check .coveragerc configuration
- Ensure source paths are correct
- Use `--cov-report=html` for detailed reports