# SpritePal Parallel Testing Guide

## Overview

SpritePal's test suite has been configured for parallel execution using `pytest-xdist` to significantly improve test execution speed. The suite automatically separates tests into:

- **Parallel-safe tests**: Can run simultaneously across multiple workers
- **Serial tests**: Must run sequentially due to thread-unsafe operations

## Quick Start

### Automatic Parallel + Serial Execution
```bash
# Best option: Run all tests optimally
source venv/bin/activate && python scripts/run_parallel_tests.py

# With custom worker count (default: 4)
python scripts/run_parallel_tests.py --workers 8

# Verbose output
python scripts/run_parallel_tests.py -v
```

### Manual Execution
```bash
# Parallel tests only (fast, safe for CI)
pytest -c pytest_parallel.ini -m "not serial" -n 8

# Serial tests only (thread-unsafe tests)
pytest -c pytest_serial.ini -m "serial"

# Traditional single-threaded (all tests)
pytest tests/
```

## Configuration Files

### `pytest_parallel.ini`
- Optimized for parallel execution with 8 workers
- Uses `worksteal` distribution for load balancing
- Forces offscreen Qt platform for GUI tests
- Reduced timeouts for faster feedback

### `pytest_serial.ini`
- Sequential execution for thread-unsafe tests
- Longer timeouts for complex operations
- Allows real Qt for debugging when needed

### `pytest.ini` (default)
- Maintains backward compatibility
- Single-threaded execution
- Comprehensive markers and configuration

## Test Markers

### Parallel Execution Markers
- `@pytest.mark.serial`: Forces serial execution
- `@pytest.mark.process_pool`: HAL process pool tests
- `@pytest.mark.singleton`: Tests manipulating singletons
- `@pytest.mark.qt_application`: Tests managing QApplication
- `@pytest.mark.thread_safety`: Thread safety tests

### Usage Examples
```python
# Entire test file needs serial execution
pytestmark = [
    pytest.mark.serial,
    pytest.mark.qt_application
]

# Individual test needs serial execution
@pytest.mark.serial
def test_singleton_behavior():
    pass
```

## Test Categories

### Parallel-Safe Tests ✅
- Constants and validation tests
- Unit tests with mocked dependencies
- Stateless operations
- File format tests
- Exception hierarchy tests

### Serial Tests ⚠️
- HAL process pool tests (singleton management)
- QApplication instance management
- Manager registry manipulation
- Thread safety tests
- Real Qt component tests
- Async ROM cache tests

## Performance Impact

### Before Parallel Testing
- **2,131 tests** running sequentially
- Estimated execution time: 45-90 minutes
- Resource utilization: Single CPU core

### After Parallel Testing
- **~1,700 parallel tests** on 8 workers
- **~400 serial tests** running sequentially
- Estimated execution time: 10-20 minutes
- Resource utilization: Multi-core efficiency

### Expected Speedup
- **Parallel tests**: 6-8x faster (depending on CPU cores)
- **Serial tests**: No change (must run sequentially)
- **Overall suite**: 3-5x faster total execution time

## Best Practices

### For Test Authors
1. **Write parallel-safe tests by default**
   - Use mocked dependencies
   - Avoid global state manipulation
   - Use proper test isolation

2. **Mark thread-unsafe tests explicitly**
   ```python
   @pytest.mark.serial
   def test_singleton_reset():
       SometonClass.reset_singleton()
   ```

3. **Avoid QApplication() in parallel tests**
   ```python
   # ❌ Bad - creates conflicts
   app = QApplication([])
   
   # ✅ Good - use fixtures
   def test_gui_component(qtbot):
       # qtbot handles QApplication properly
   ```

### For CI/CD
```yaml
# Recommended CI configuration
- name: Run parallel tests
  run: |
    source venv/bin/activate
    python scripts/run_parallel_tests.py --workers 4 --maxfail 10

# Alternative: Separate parallel and serial phases
- name: Run parallel tests
  run: pytest -c pytest_parallel.ini -m "not serial" -n auto
- name: Run serial tests  
  run: pytest -c pytest_serial.ini -m "serial"
```

## Troubleshooting

### Common Issues

1. **"InvalidSpecError: Cannot spec a Mock object"**
   - Caused by Mock conflicts in parallel execution
   - Marked tests as `@pytest.mark.serial` if needed

2. **QApplication conflicts**
   - Multiple workers creating QApplication instances
   - Use `pytest.mark.qt_application` marker

3. **Singleton state conflicts**
   - Tests modifying global singletons simultaneously
   - Use `pytest.mark.singleton` marker

4. **Process pool deadlocks**
   - HAL compression tests interfering
   - Use `pytest.mark.process_pool` marker

### Debug Commands
```bash
# Test collection verification
pytest --collect-only -m "serial" tests/

# Run specific problematic test in isolation
pytest tests/test_specific.py::TestClass::test_method -v

# Check marker coverage
pytest --markers | grep -E "(serial|parallel|qt_application)"
```

## Performance Monitoring

### Execution Time Analysis
```bash
# Measure parallel performance
time pytest -c pytest_parallel.ini -m "not serial" -n 8 --durations=10

# Compare with serial execution
time pytest -c pytest_serial.ini -m "not serial" --durations=10

# Full suite analysis
python scripts/run_parallel_tests.py --verbose
```

### Test Distribution Analysis
```bash
# Count tests by category
pytest --collect-only -q -m "not serial" tests/ | grep "tests collected"
pytest --collect-only -q -m "serial" tests/ | grep "tests collected"
```

## Future Optimizations

1. **Worker count tuning**: Adjust based on CPU cores and I/O patterns
2. **Test grouping**: Group related tests to minimize worker overhead
3. **Fixture optimization**: Shared fixtures across worker processes
4. **Mock reduction**: Convert more tests to use real components safely

## Configuration Summary

| Configuration | Purpose | Workers | Markers | Use Case |
|---------------|---------|---------|---------|----------|
| `pytest.ini` | Default | 1 | All | Development, debugging |
| `pytest_parallel.ini` | Fast parallel | 8 | `not serial` | CI, fast feedback |
| `pytest_serial.ini` | Thread-unsafe | 1 | `serial` | Thread-unsafe tests |
| `run_parallel_tests.py` | Optimal | 4-8 | Auto | Best performance |

The parallel testing setup provides significant performance improvements while maintaining test reliability and comprehensive coverage.