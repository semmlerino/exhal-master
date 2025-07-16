# Headless Testing Guide for SpritePal

This guide explains how to run SpritePal tests in headless environments (CI/CD, servers without display).

## Setup

Tests are configured to run in headless mode using Qt's offscreen platform:
- `pytest.ini` sets `qt_qpa_platform = offscreen`
- GUI tests are marked with `@pytest.mark.gui`
- Problematic QThread tests skip in headless mode

## Running Tests

### All tests (headless safe)
```bash
QT_QPA_PLATFORM=offscreen python3 -m pytest tests/ -v
```

### Non-GUI tests only
```bash
python3 -m pytest tests/ -v -k "not gui"
```

### Headless integration tests
```bash
python3 -m pytest tests/test_integration_headless.py -v
```

## Test Organization

1. **Unit Tests** (always headless safe):
   - `test_extractor.py` - Core extraction logic
   - `test_palette_manager.py` - Palette management
   - `test_constants.py` - Configuration validation

2. **Integration Tests**:
   - `test_integration.py` - Standard integration tests
     - GUI tests marked and skip in headless
   - `test_integration_headless.py` - Headless-specific tests
     - Mock Qt dependencies
     - Test business logic without threading

## Implementation Details

### Handling Qt Dependencies
- QThread tests are mocked or skipped in headless
- Business logic extracted and tested separately
- QPixmap creation mocked for headless environments

### Test Adaptations
- 35 tests run successfully in headless mode
- 2 GUI tests automatically skip when `QT_QPA_PLATFORM=offscreen`
- Worker thread logic tested without actual threading

## CI/CD Integration

For GitHub Actions or similar:
```yaml
- name: Run tests
  env:
    QT_QPA_PLATFORM: offscreen
  run: |
    python -m pytest tests/ -v --tb=short
```