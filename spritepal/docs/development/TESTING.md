# Testing Guide for Ultrathink Sprite Editor

This project uses pytest for testing. The test suite includes unit tests, integration tests, and GUI tests for both the sprite editor and pixel editor components.

## Test Setup

### Prerequisites
- Python 3.x
- pytest and pytest-qt installed (included in requirements.txt)

### Configuration
Tests are configured via:
- `pytest.ini` - Main pytest configuration
- `pyproject.toml` - Additional test settings

## Running Tests

### From spritepal directory:
```bash
# Run all tests
python3 -m pytest .. -v

# Run specific test module
python3 -m pytest ../sprite_editor/tests/test_models.py -v

# Run non-GUI tests only
python3 -m pytest .. -v -k "not gui"

# Run with coverage
python3 -m pytest .. --cov=sprite_editor --cov=pixel_editor --cov-report=html
```

### Using the test runner script:
```bash
# Run all tests
./run_tests.py

# Run specific test suites
./run_tests.py sprite_editor
./run_tests.py pixel_editor
./run_tests.py no_gui
./run_tests.py coverage
```

## Test Organization

- `sprite_editor/tests/` - Sprite editor tests
- `pixel_editor/tests/` - Pixel editor tests
- Tests are marked with:
  - `@pytest.mark.unit` - Fast unit tests
  - `@pytest.mark.integration` - Integration tests
  - `@pytest.mark.gui` - GUI tests requiring Qt

## Test Environment

For headless environments, tests run with:
- `QT_QPA_PLATFORM=offscreen` (configured in pytest.ini)
- GUI tests may be skipped if display is not available