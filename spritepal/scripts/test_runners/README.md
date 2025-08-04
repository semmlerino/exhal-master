# Test Runner Scripts

This directory contains specialized test execution scripts for different testing scenarios and environments.

## Test Execution Scripts

### Virtual Display Testing
- `run_tests_xvfb.py` - Runs GUI tests with automatic Xvfb virtual display setup
- `run_tests_safe.py` - Safe test execution with error handling and cleanup
- `run_tests.py` - Standard test runner with enhanced reporting

### Manual Testing
- `test_rom_cache_manual.py` - Manual testing script for ROM cache functionality
- `test_simple_real_integration.py` - Simple real-world integration test scenarios

## Features

### Automatic Virtual Display Setup
The `run_tests_xvfb.py` script automatically:
- Detects if running in a headless environment
- Starts Xvfb virtual display server if needed
- Configures appropriate display settings for GUI tests
- Handles cleanup and error recovery

### Enhanced Error Handling
- Captures and reports test failures with context
- Provides detailed logging for debugging test issues
- Handles Qt application lifecycle properly

## Usage

```bash
# Run all tests with virtual display (recommended for headless environments)
python scripts/test_runners/run_tests_xvfb.py

# Run tests with enhanced safety checks
python scripts/test_runners/run_tests_safe.py

# Run specific manual tests
python scripts/test_runners/test_rom_cache_manual.py
```

## Environment Requirements

Some scripts require:
- Xvfb (for virtual display testing on Linux)
- Qt6 libraries
- pytest and pytest-qt
- Appropriate test data files

See the main project documentation for complete setup instructions.