# TOCTOU Race Condition Fixes

## Overview
This document describes the Time-of-Check-Time-of-Use (TOCTOU) race condition vulnerabilities that were identified and fixed in the SpritePal codebase, specifically in manager access patterns.

## The Problem

### What is TOCTOU?
TOCTOU is a race condition that occurs when:
1. Code checks if a resource is valid (Time of Check)
2. Releases the lock protecting that resource
3. Uses the resource later (Time of Use)
4. Between steps 2 and 3, another thread could delete/modify the resource

### Example of Vulnerable Code
```python
# BAD: TOCTOU vulnerability
def vulnerable_method(self):
    with self._manager_mutex:
        manager = self._get_manager()  # Check: manager exists
    # Lock released here!
    if manager:  # Manager could be None now!
        manager.do_operation()  # CRASH: AttributeError
```

## The Solution

### Pattern 1: Extend Lock Duration
For short operations, keep the mutex locked during the entire operation:

```python
# GOOD: Extended protection
def safe_method(self):
    with self._manager_mutex:
        manager = self._get_manager()
        if manager:
            manager.do_operation()
        # Lock held until operation complete
```

### Pattern 2: Extract Data Under Lock
For long operations, extract only necessary data under lock:

```python
# GOOD: Extract data safely
def safe_long_operation(self):
    # Extract data under lock
    data = self._with_managers_safely(
        lambda mgr: mgr.get_data() if mgr else None
    )
    
    # Use extracted data outside lock
    if data:
        self._process_data(data)  # Long operation
```

### Pattern 3: Helper Method for Safe Operations
Implement a helper method that ensures operations run under lock:

```python
def _with_managers_safely(self, operation):
    """Execute an operation with manager references under mutex protection."""
    with QMutexLocker(self._manager_mutex):
        if self.extraction_manager is None or self.rom_extractor is None:
            return None
        return operation(self.extraction_manager, self.rom_extractor)
```

## Fixed Files

### 1. manual_offset_dialog_simplified.py
- **_connect_cache_signals**: Fixed to use _with_managers_safely
- **_update_preview**: Refactored to extract data under lock via _extract_preview_data_safely
- **_SimpleROMDataManager.get_rom_extractor**: Added warning about inherent risk

### 2. preview_coordinator.py
- **_execute_preview_update**: Refactored to use _extract_preview_data_safely
- Added _with_managers_safely helper method

### 3. scan_controls_panel.py
- **_scan_range**: Fixed to use _with_managers_safely for existence check
- **_scan_all**: Fixed to use _with_managers_safely for existence check
- **_start_range_scan_worker**: Fixed to extract rom_extractor under lock

## Best Practices

### DO:
1. **Use context managers**: Always use `with QMutexLocker(mutex):` for automatic cleanup
2. **Keep locks short**: Extract data under lock, process outside
3. **Document lock requirements**: Add docstrings explaining thread safety
4. **Test with ThreadSanitizer**: Use tools to detect race conditions

### DON'T:
1. **Don't return references**: Avoid returning manager references that outlive the lock
2. **Don't hold locks during I/O**: Extract data first, then do I/O operations
3. **Don't nest locks**: Avoid deadlock by not acquiring multiple locks
4. **Don't ignore warnings**: If a method warns about TOCTOU, refactor the caller

## Testing Considerations

### Unit Tests
- Mock the mutex to ensure proper locking
- Test concurrent access scenarios
- Verify operations fail gracefully when managers are None

### Integration Tests
- Use pytest-xdist to run tests in parallel
- Monitor for AttributeError exceptions
- Check logs for race condition warnings

## Future Improvements

1. **Consider using Qt's thread-safe patterns**: 
   - QThreadStorage for thread-local data
   - Signal/slot connections with QueuedConnection

2. **Implement manager lifecycle management**:
   - Reference counting for managers
   - Weak references where appropriate
   - Clear ownership hierarchy

3. **Add runtime checks**:
   - Assert thread affinity in critical sections
   - Log mutex contention statistics
   - Detect and warn about potential TOCTOU patterns

## References
- [Qt Thread Safety](https://doc.qt.io/qt-6/threads-qobject.html)
- [Python Threading Best Practices](https://docs.python.org/3/library/threading.html)
- [TOCTOU on Wikipedia](https://en.wikipedia.org/wiki/Time-of-check_to_time-of-use)