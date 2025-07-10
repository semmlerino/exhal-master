# Bugs Found and Fixed During Testing

## Critical Bugs

### 1. PaletteController Attribute Error
**File**: `sprite_editor/controllers/palette_controller.py`
**Issue**: Used `self.palette_model` instead of `self.model`
**Impact**: Would cause AttributeError when any palette operations were performed
**Fix**: Changed 4 occurrences:
- Line 74: `self.model.load_palettes_from_cgram()`
- Line 84: `self.model.get_palette(index)`
- Line 93: `self.model.export_palette(index, filename)`
- Line 105: `self.model.import_palette(index, filename)`

### 2. Duplicate Signal Connections in Controllers
**Files**: All controller tests
**Issue**: Tests were manually calling `connect_signals()` after controller creation, but `BaseController.__init__` already calls it automatically
**Impact**: Signals were connected twice, causing callbacks to fire multiple times
**Fix**: Removed manual `connect_signals()` calls from all controller tests

## Test Infrastructure Issues

### 3. Qt Test Timeout Issues
**File**: `sprite_editor/tests/test_gui_workflows.py`
**Issue**: Tests were hanging due to:
- Unmocked QFileDialog blocking operations
- WorkflowWorker threads not properly mocked
- Editor fixture showing GUI and waiting for exposure
**Fix**: 
- Properly mocked all QFileDialog methods before triggering actions
- Created mock WorkflowWorker that doesn't actually start threads
- Removed `show()` and `waitExposed()` from fixture

### 4. Test Environment Qt Errors
**Issue**: "Fatal Python error: Aborted" in Qt tests
**Fix**: Added proper Qt test configuration in conftest.py:
- Set `QT_QPA_PLATFORM=offscreen`
- Added proper cleanup fixtures
- Configured Qt for headless testing

## Design Issues Found

### 5. Signal Connection Pattern
**Observation**: BaseController automatically connects signals in __init__, which is good for consistency but can surprise developers
**Recommendation**: Document this behavior clearly in BaseController docstring

### 6. Model Naming Consistency
**Observation**: PaletteController receives a `palette_model` parameter but stores it as `self.model`
**Recommendation**: Consider renaming parameter to `model` for consistency with other controllers

## Test Coverage Gaps Identified

### 7. Error Handling Paths
Many modules have untested error handling code:
- File not found scenarios
- Invalid data handling
- Network/permission errors
**Recommendation**: Add dedicated error handling test suite

### 8. View Module Testing
View modules have low coverage (18-31%) due to:
- Heavy Qt widget interaction
- Complex UI setup
- Event handling complexity
**Recommendation**: Create focused view tests with proper Qt mocking

## Performance Issues

### 9. Test Suite Timeouts
**Issue**: Full test suite was timing out when running with coverage
**Fix**: Simplified GUI workflow tests and removed unnecessary waits
**Impact**: Test suite now completes in ~12 seconds instead of timing out

## Recommendations

1. **Add type hints** to catch attribute errors at development time
2. **Document signal flow** in controllers to prevent confusion
3. **Create error injection fixtures** for systematic error testing
4. **Add integration test suite** separate from unit tests
5. **Consider using pytest-xdist** for parallel test execution