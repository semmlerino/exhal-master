# Error Handler Migration Guide

## Overview
The new error handler uses Qt signals instead of direct QMessageBox calls. This improves testability and separation of concerns.

## Migration Pattern

### Before (Direct QMessageBox):
```python
try:
    # some operation
    do_something()
except Exception as e:
    QMessageBox.critical(
        self,
        "Error", 
        f"Operation failed: {e}"
    )
```

### After (Signal-based):
```python
from spritepal.ui.common import get_error_handler

class MyWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.error_handler = get_error_handler(self)
    
    def some_method(self):
        try:
            # some operation
            do_something()
        except Exception as e:
            self.error_handler.handle_exception(e, "Operation failed")
```

## Benefits

1. **Testability**: Tests can spy on error signals without dealing with actual dialogs
2. **Flexibility**: Different UI components can handle errors differently
3. **Consistency**: All errors go through the same handler
4. **Logging**: Automatic logging of all errors

## Usage Examples

### Critical Error
```python
self.error_handler.handle_critical_error("Database Error", "Failed to save data")
```

### Warning
```python
self.error_handler.handle_warning("Low Memory", "System memory is running low")
```

### Info Message
```python
self.error_handler.handle_info("Success", "Operation completed successfully")
```

### Exception Handling
```python
try:
    risky_operation()
except Exception as e:
    self.error_handler.handle_exception(e, "Failed to perform risky operation")
```

## Testing

In tests, disable dialogs and spy on signals:

```python
def test_error_handling(qtbot):
    widget = MyWidget()
    widget.error_handler.set_show_dialogs(False)
    
    # Spy on error signal
    spy = QSignalSpy(widget.error_handler.critical_error)
    
    # Trigger an error
    widget.trigger_error()
    
    # Verify signal was emitted
    assert len(spy) == 1
    assert "Expected error" in spy[0][1]
```

## Implementation Status

### Completed:
- ✅ ExtractionController - replaced QMessageBox.critical with error handler

### Todo (only if needed):
- [ ] MainWindow - has 5 QMessageBox calls
- [ ] InjectionDialog - has 14 QMessageBox calls  
- [ ] Other dialogs - various QMessageBox calls

For a solo developer, it's recommended to only migrate components as you work on them or when they cause test issues.