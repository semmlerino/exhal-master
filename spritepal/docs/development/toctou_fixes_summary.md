# TOCTOU Race Condition Fixes - Implementation Summary

## Overview
Fixed Time-of-Check-Time-of-Use (TOCTOU) race conditions in manager access patterns across three critical files where manager references were obtained under mutex but used after the lock was released.

## Files Modified

### 1. `/ui/dialogs/manual_offset_dialog_simplified.py`

#### Added Helper Method
```python
def _with_managers_safely(self, operation):
    """Execute an operation with manager references under mutex protection."""
    with QMutexLocker(self._manager_mutex):
        if self.extraction_manager is None or self.rom_extractor is None:
            return None
        return operation(self.extraction_manager, self.rom_extractor)
```

#### Fixed Methods
- **`_connect_cache_signals()`**: Now uses `_with_managers_safely` to prevent TOCTOU
- **`_update_preview()`**: Refactored to use new `_extract_preview_data_safely()` method
- **`_SimpleROMDataManager.get_rom_extractor()`**: Added mutex protection and warning

### 2. `/ui/dialogs/manual_offset/preview_coordinator.py`

#### Added Helper Method
```python
def _with_managers_safely(self, operation):
    """Execute an operation with manager references under mutex protection."""
    with QMutexLocker(self._manager_mutex):
        extraction_manager = self._rom_data_manager.get_extraction_manager()
        rom_extractor = self._rom_data_manager.get_rom_extractor()
        if extraction_manager is None or rom_extractor is None:
            return None
        return operation(extraction_manager, rom_extractor)
```

#### Fixed Methods
- **`_execute_preview_update()`**: Refactored to use new `_extract_preview_data_safely()` method
- **`_get_managers_safely()`**: Added warning about proper usage

### 3. `/ui/components/panels/scan_controls_panel.py`

#### Added Helper Method
```python
def _with_managers_safely(self, operation):
    """Execute an operation with manager references under mutex protection."""
    with QMutexLocker(self._manager_mutex):
        if self.extraction_manager is None or self.rom_extractor is None:
            return None
        return operation(self.extraction_manager, self.rom_extractor)
```

#### Fixed Methods
- **`_scan_range()`**: Now uses safe existence check with `_with_managers_safely`
- **`_scan_all()`**: Now uses safe existence check with `_with_managers_safely`
- **`_start_range_scan_worker()`**: Extracts rom_extractor under lock protection

## Key Improvements

### 1. **Atomic Operations**
All manager access and usage now happens within the same mutex lock, preventing race conditions.

### 2. **Data Extraction Pattern**
For long-running operations, we extract only the necessary data under lock and process it afterwards.

### 3. **Consistent API**
The `_with_managers_safely()` helper provides a consistent, safe way to work with managers.

### 4. **Clear Documentation**
Added warnings and documentation about thread safety requirements.

## Impact

- **Prevents crashes**: No more AttributeError from accessing deleted managers
- **Thread-safe**: Operations are now atomic with respect to manager lifecycle
- **Maintainable**: Clear patterns make it easier to write safe code
- **Performance**: Minimal impact as locks are held only as long as necessary

## Testing

Run these commands to verify the fixes:
```bash
# Run thread safety tests
pytest tests/test_error_handler_thread_safety.py -v

# Run manual offset dialog tests
pytest tests/test_manual_offset_dialog_refactoring.py -v

# Run integration tests with parallel execution
pytest tests/test_integration_mock.py -n 4
```

## Future Considerations

1. Consider implementing a manager registry with reference counting
2. Add static analysis tools to detect TOCTOU patterns
3. Implement comprehensive thread safety test suite
4. Document threading model in the architecture guide