# Qt Integration Test Segmentation Fault Fix

## Issue Summary
Segmentation fault occurring in Qt integration tests at `test_integration_preview_system.py::test_worker_generates_preview` during `qtbot.wait()` call in `wait_signal.py`.

## Root Cause Analysis

### Primary Issues Identified:

1. **Improper Qt Event Loop Handling in `wait_for_condition()`**
   - Mixed QTimer with manual `qtbot.wait()` polling
   - Created unnecessary QTimer without proper usage
   - Manual event loop polling caused conflicts with Qt's internal event processing

2. **Thread Lifecycle Management**
   - QThread workers created without proper parent-child relationships
   - Workers potentially deleted while signals still pending
   - No proper cleanup mechanism for finished workers

3. **Signal/Slot Safety Issues**
   - Signals potentially delivered to deleted objects
   - Race conditions between worker deletion and signal delivery

## Solutions Implemented

### 1. Fixed `conftest.py` - Proper Event Loop Handling

**Before (Problematic):**
```python
def wait_for_condition(qtbot, condition_func, timeout=5000, message="Condition not met"):
    timer = QTimer()
    timer.timeout.connect(lambda: None)  # Useless connection
    timer.start(100)
    
    elapsed = 0
    while elapsed < timeout:
        if condition_func():
            timer.stop()
            return True
        qtbot.wait(100)  # Manual polling - causes segfault
        elapsed += 100
```

**After (Fixed):**
```python
def wait_for_condition(qtbot, condition_func, timeout=5000, message="Condition not met"):
    """Use qtbot's built-in waitUntil for proper event loop handling."""
    try:
        qtbot.waitUntil(condition_func, timeout=timeout)
        return True
    except AssertionError:
        raise TimeoutError(f"Timeout waiting for condition: {message}")
```

### 2. Fixed Thread Management with WorkerContainer

**Created a proper container widget for thread lifecycle:**
```python
class WorkerContainer(QWidget):
    """Container widget to manage worker lifecycle properly."""
    
    def set_worker(self, worker):
        # Ensure worker has parent for proper Qt lifecycle
        if worker.parent() is None:
            worker.setParent(self)
        
        # Schedule cleanup after worker finishes
        worker.finished.connect(lambda: self.cleanup_timer.start(100))
    
    def cleanup_worker(self):
        """Clean up the worker safely."""
        if self.worker:
            if self.worker.isRunning():
                self.worker.quit()
                self.worker.wait(500)
            self.worker.deleteLater()
            self.worker = None
```

### 3. Updated Test Implementation

**Key changes:**
- Use `qtbot.waitSignal()` for proper signal waiting
- Use `qtbot.waitUntil()` for condition waiting
- Proper parent-child relationships for all Qt objects
- Explicit cleanup of workers after tests

## Technical Details

### Qt Event Loop Considerations
- `qtbot.wait()` processes events but can cause issues when used in tight loops
- `qtbot.waitUntil()` properly integrates with Qt's event loop
- `qtbot.waitSignal()` is the correct way to wait for Qt signals

### Thread Safety Patterns
- Always set parent for QThread objects
- Connect to `finished` signal for cleanup
- Use `deleteLater()` instead of direct deletion
- Ensure proper cleanup order (quit → wait → deleteLater)

## Results

- **Before:** Segmentation fault at line 177 in conftest.py
- **After:** All tests pass successfully without crashes
- **Performance:** No degradation in test execution time
- **Reliability:** Consistent test execution without random failures

## Prevention Guidelines

1. **Always use pytest-qt's built-in waiting mechanisms:**
   - `qtbot.waitSignal()` for signals
   - `qtbot.waitUntil()` for conditions
   - `qtbot.wait()` only for simple delays

2. **Proper Qt object lifecycle:**
   - Set parent-child relationships
   - Use `deleteLater()` for cleanup
   - Connect to `finished` signals

3. **Thread management:**
   - Create container objects for thread lifecycle
   - Ensure proper cleanup order
   - Wait for threads to finish before cleanup

## Files Modified

1. `/mnt/c/CustomScripts/KirbyMax/workshop/exhal-master/spritepal/tests/integration/conftest.py`
   - Replaced `wait_for_condition()` implementation
   - Added `ConditionWaiter` helper class (optional)

2. `/mnt/c/CustomScripts/KirbyMax/workshop/exhal-master/spritepal/tests/integration/test_integration_preview_system.py`
   - Added `WorkerContainer` class for thread management
   - Updated all worker tests to use container
   - Replaced custom wait_for with qtbot methods

## Testing Confirmation

```bash
# Test command that previously caused segfault
xvfb-run -a python -m pytest tests/integration/test_integration_preview_system.py::TestSimplePreviewWorker::test_worker_generates_preview -xvs

# Result: PASSED - No segfault
```

## Lessons Learned

1. **Qt event loop is delicate** - Improper manipulation causes crashes
2. **pytest-qt provides the right tools** - Use them instead of custom solutions
3. **Parent-child relationships matter** - Qt's automatic cleanup requires proper hierarchy
4. **Signal/slot lifecycle** - Must be carefully managed in threaded contexts

---

*This fix ensures robust Qt integration testing without segmentation faults while maintaining full test coverage and functionality.*
