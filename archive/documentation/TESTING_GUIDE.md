# Testing Guide for Kirby Super Star Sprite Editor

## Overview

This project includes comprehensive unit and integration tests to ensure the sprite editing tools work correctly. Tests are written using Python's built-in `unittest` framework with minimal mocking to test real behavior.

## Test Structure

```
test_sprite_edit_helpers.py     # Unit tests for core utility functions
test_sprite_workflows.py        # Unit tests for workflow classes
test_integration_workflows.py   # Integration tests for complete workflows
run_all_tests.py               # Test runner with colored output
```

## Running Tests

### Run All Tests
```bash
python3 run_all_tests.py
```

### Run Specific Test Module
```bash
python3 test_sprite_edit_helpers.py
python3 test_sprite_workflows.py
python3 test_integration_workflows.py
```

### Run Specific Test Class or Method
```bash
# Run all tests in a class
python3 run_all_tests.py test_sprite_workflows.TestSpriteEditWorkflow

# Run specific test method
python3 run_all_tests.py test_sprite_workflows.TestSpriteEditWorkflow.test_extract_for_editing
```

### Command Line Options
```bash
# Verbose output
python3 run_all_tests.py -v

# Stop on first failure
python3 run_all_tests.py -f

# Quiet mode
python3 run_all_tests.py -q
```

## Test Coverage

### Unit Tests

#### test_sprite_edit_helpers.py
- **Color Conversions**
  - BGR555 to RGB conversion
  - RGB to BGR555 conversion
  - Round-trip conversion accuracy
  - Edge cases (black, white, pure colors)

- **CGRAM Parsing**
  - Parse all-black CGRAM
  - Parse specific test colors
  - Handle partial/incomplete files

- **Tile Encoding/Decoding**
  - Decode 4bpp SNES tiles
  - Encode pixels to 4bpp format
  - Round-trip preservation
  - Value clipping (0-15 range)

#### test_sprite_workflows.py
- **SpriteEditWorkflow**
  - Load palette mappings
  - Extract sprites for editing
  - Validate edited sprites (dimensions, color mode, palette)
  - Reinsert sprites to VRAM

- **SpriteSheetEditor**
  - Extract sprite sheets
  - Validate edited sheets
  - Reinsert sheets
  - Create editing guides

### Integration Tests

#### test_integration_workflows.py
- **Complete Workflows**
  - Extract → Edit → Validate → Reinsert (tiles)
  - Extract → Edit → Validate → Reinsert (sheets)
  - Workflow without palette mappings
  - Error handling scenarios

- **Data Integrity**
  - CGRAM palette application
  - Round-trip data preservation
  - Modified data verification

## Test Data

Tests create realistic test data including:
- VRAM with recognizable patterns (gradients, stripes, checkerboards)
- CGRAM with game-like palettes (Kirby pink, enemy green, etc.)
- Palette mappings matching test sprites

## Writing New Tests

### Guidelines
1. **Minimal Mocking**: Use real files and data where possible
2. **Test Real Behavior**: Don't just test what you expect, test what actually happens
3. **Clean Up**: Always clean up temporary files in `tearDown()`
4. **Descriptive Names**: Use clear test method names that describe what's being tested

### Example Test Structure
```python
class TestNewFeature(unittest.TestCase):
    def setUp(self):
        """Create test environment"""
        self.test_dir = tempfile.mkdtemp()
        # Create test files...
    
    def tearDown(self):
        """Clean up test environment"""
        shutil.rmtree(self.test_dir)
    
    def test_specific_behavior(self):
        """Test description"""
        # Arrange
        input_data = self._create_test_data()
        
        # Act
        result = function_under_test(input_data)
        
        # Assert
        self.assertEqual(result, expected_value)
```

## Continuous Integration

The project includes GitHub Actions configuration for:
- Running tests on multiple Python versions (3.8-3.12)
- Testing on multiple platforms (Linux, Windows, macOS)
- Code coverage reporting
- Linting with flake8
- Format checking with black
- Type checking with mypy

## Troubleshooting

### Common Issues

#### ResourceWarning: unclosed file
These warnings indicate files aren't being properly closed. While not test failures, they should be fixed in the code.

#### Import Errors
Ensure all required packages are installed:
```bash
pip install -r test_requirements.txt
```

#### Temporary File Issues
Tests use `tempfile.mkdtemp()` for isolation. If tests fail with file errors, check:
- File permissions
- Disk space
- Antivirus software interference

### Debug Mode
To see more detailed output during test failures:
```python
# Add to test method
import pdb; pdb.set_trace()

# Or use verbose asserts
self.assertEqual(actual, expected, f"Expected {expected} but got {actual}")
```

## Test Metrics

Current test suite includes:
- **36 test methods** across 3 modules
- **100% pass rate** (all tests passing)
- Tests cover:
  - Core utility functions
  - Workflow operations
  - Error handling
  - Data integrity
  - File I/O operations

## Future Improvements

1. **Add GUI Tests**: Test PyQt6 interface components
2. **Performance Tests**: Benchmark large sprite sheet operations  
3. **Stress Tests**: Test with very large files
4. **Compatibility Tests**: Test with various SNES game dumps
5. **Mock External Dependencies**: Add mocks for file system when needed

---

Remember: Good tests make refactoring safe and catch bugs early!