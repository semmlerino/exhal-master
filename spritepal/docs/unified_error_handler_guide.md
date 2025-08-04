# Unified Error Handler Guide

## Overview

The Unified Error Handler is a comprehensive error handling service that standardizes error processing, categorization, and recovery across the entire SpritePal application. It builds upon the existing error handling infrastructure while providing enhanced functionality.

## Key Features

- **Automatic Error Categorization**: Intelligently categorizes errors into predefined types
- **Context-Aware Error Messages**: Generates user-friendly messages based on operation context
- **Recovery Suggestions**: Provides actionable suggestions for error resolution
- **Error Chaining Support**: Tracks error history and relationships
- **Integration with Existing Patterns**: Works seamlessly with current error handling
- **Thread-Safe Operation**: Safe for use across worker threads
- **Comprehensive Logging**: Integrated with application logging system

## Architecture

### Core Components

1. **UnifiedErrorHandler**: Main service class
2. **ErrorContext**: Context information for error scenarios
3. **ErrorResult**: Structured result of error processing
4. **ErrorCategory**: Classification system for errors
5. **ErrorSeverity**: Severity levels for prioritization

### Error Categories

- `FILE_IO`: File operation errors
- `VALIDATION`: Input validation errors
- `WORKER_THREAD`: Worker thread operation errors
- `QT_GUI`: Qt GUI-related errors
- `EXTRACTION`: Sprite/ROM extraction errors
- `INJECTION`: Sprite/ROM injection errors
- `CACHE`: Cache operation errors
- `SESSION`: Session/settings errors
- `PREVIEW`: Preview generation errors
- `NETWORK`: Network operation errors
- `SYSTEM`: System-level errors
- `UNKNOWN`: Uncategorized errors

### Error Severity Levels

- `CRITICAL`: App-breaking errors requiring immediate attention
- `HIGH`: Major functionality issues
- `MEDIUM`: Minor functionality issues
- `LOW`: Warnings and notices
- `INFO`: Informational messages

## Usage Examples

### Basic Error Handling

```python
from utils.unified_error_handler import get_unified_error_handler

error_handler = get_unified_error_handler()

try:
    # Risky operation
    with open("config.txt", 'r') as f:
        config = f.read()
except Exception as e:
    # Automatic categorization and handling
    result = error_handler.handle_exception(e)
    print(f"Error handled: {result.message}")
```

### Using Error Context

```python
with error_handler.error_context("loading configuration", file_path="config.txt"):
    # Any exception here will be automatically handled with context
    config = load_config_file("config.txt")
```

### Specific Error Types

```python
# File operation error
try:
    data = read_file("sprite.png")
except OSError as e:
    result = error_handler.handle_file_error(
        e, "sprite.png", "loading sprite data"
    )

# Validation error
try:
    validate_rom_parameters(params)
except ValidationError as e:
    result = error_handler.handle_validation_error(
        e, "validating ROM parameters", user_input=str(params)
    )

# Worker error
try:
    extract_sprites()
except Exception as e:
    result = error_handler.handle_worker_error(
        e, "SpriteExtractor", "extracting sprites from ROM"
    )
```

### Using ErrorHandlerMixin

```python
from utils.error_integration import ErrorHandlerMixin

class MyWidget(QWidget, ErrorHandlerMixin):
    def __init__(self):
        super().__init__()
        self.setup_error_handling()
    
    def risky_operation(self):
        with self.error_context("performing operation"):
            # Code that might fail
            pass
    
    def handle_custom_error(self, error):
        return self.handle_error(error, "custom operation")
```

### Decorators for Common Patterns

```python
from utils.error_integration import (
    enhanced_handle_worker_errors,
    qt_error_handler,
    file_operation_handler,
    validation_handler
)

# Enhanced worker error handling
class MyWorker(BaseWorker):
    @enhanced_handle_worker_errors("sprite extraction")
    def extract_sprites(self):
        # Worker logic here
        pass

# Qt operation error handling
class MyWidget(QWidget):
    @qt_error_handler("updating display", "MyWidget")
    def update_display(self):
        # Qt operations that might fail
        pass

# File operation error handling
class ConfigManager:
    def __init__(self):
        self.config_file = "config.json"
    
    @file_operation_handler("loading configuration", "config_file")
    def load_config(self):
        # File operations that might fail
        pass

# Validation error handling
class DataValidator:
    @validation_handler("validating input data")
    def validate_data(self, data):
        # Validation logic that might fail
        pass
```

## Migration from Existing Patterns

### From Direct QMessageBox Calls

**Before:**
```python
try:
    result = risky_operation()
except Exception as e:
    QMessageBox.critical(self, "Error", str(e))
    logger.error(f"Operation failed: {e}")
```

**After:**
```python
try:
    result = risky_operation()
except Exception as e:
    error_handler.handle_exception(e)
    # Error is automatically displayed and logged
```

### From @handle_worker_errors

**Before:**
```python
@handle_worker_errors("sprite extraction")
def extract_sprites(self):
    # Worker logic
    pass
```

**After:**
```python
@enhanced_handle_worker_errors("sprite extraction")
def extract_sprites(self):
    # Worker logic with enhanced error handling
    pass
```

### From Basic ErrorHandler

**Before:**
```python
error_handler = get_error_handler()
error_handler.handle_critical_error("Error", "Something went wrong")
```

**After:**
```python
error_handler = get_unified_error_handler()
try:
    risky_operation()
except Exception as e:
    error_handler.handle_exception(e)
    # Automatically categorized and processed
```

## Advanced Features

### Error Statistics

```python
# Get error statistics for monitoring
stats = error_handler.get_error_statistics()
print(f"Total errors: {stats['total_errors']}")
print(f"By category: {stats['categories']}")
print(f"By severity: {stats['severities']}")
```

### Custom Error Decorators

```python
# Create custom decorators for specific operations
decorator = error_handler.create_error_decorator(
    "custom operation",
    category=ErrorCategory.VALIDATION,
    component="CustomComponent"
)

@decorator
def custom_function():
    # Function with automatic error handling
    pass
```

### Batch Error Handling

```python
from utils.error_integration import batch_error_handler

operations = [
    (lambda: operation1(), "operation 1"),
    (lambda: operation2(), "operation 2"),
    (lambda: operation3(), "operation 3"),
]

results = batch_error_handler(operations, continue_on_error=True)
for success, result in results:
    if success:
        print(f"Operation succeeded: {result}")
    else:
        print(f"Operation failed: {result.message}")
```

### Safe Method Creation

```python
from utils.error_integration import create_safe_method

# Create a safe version of a risky method
safe_extract = create_safe_method(
    extractor.extract_sprites,
    "extracting sprites",
    default_return=[]
)

sprites = safe_extract(rom_data)  # Won't raise exceptions
```

## Error Recovery

The unified error handler provides context-aware recovery suggestions:

### File Errors
- Verify file path exists and is accessible
- Check file permissions
- Ensure sufficient disk space
- Try selecting a different file

### Validation Errors
- Check input parameters are valid
- Verify data format matches requirements
- Review input constraints in documentation

### Worker Thread Errors
- Try the operation again
- Check if required resources are available
- Restart the application if the issue persists

### Extraction/Injection Errors
- Verify ROM file is valid and not corrupted
- Check if ROM format is supported
- Try different extraction/injection parameters

## Integration with Testing

### Disabling Dialogs for Tests

```python
error_handler = get_unified_error_handler()
error_handler._base_error_handler.set_show_dialogs(False)
```

### Mocking for Unit Tests

```python
from unittest.mock import patch

with patch('utils.unified_error_handler.get_error_handler'):
    # Test code here
    pass
```

### Error Handler Reset

```python
from utils.unified_error_handler import reset_unified_error_handler

# Reset for clean test state
reset_unified_error_handler()
```

## Best Practices

1. **Use Context Managers**: Prefer `error_context()` for operations that might fail
2. **Specific Error Handlers**: Use specialized handlers (file, validation, worker) when possible
3. **Don't Catch and Re-raise**: Let the unified handler process errors completely
4. **Check Recovery Suggestions**: Use `should_retry` and `should_abort` flags
5. **Monitor Error Statistics**: Use statistics for application health monitoring
6. **Integrate with Logging**: Error handler automatically logs with appropriate levels
7. **Test Error Paths**: Use the error handler in test scenarios to verify behavior

## Thread Safety

The unified error handler is thread-safe and can be used across worker threads:

- Global instance creation is protected by locks
- Context stack is per-instance, safe for concurrent use
- Signal emission is thread-safe through Qt's signal system

## Performance Considerations

- Error categorization is fast (simple isinstance checks)
- Context stack operations are O(1)
- Error history is bounded (default 50 entries)
- Recovery suggestion generation is lightweight
- Logging integration uses appropriate levels to avoid spam

## Backward Compatibility

The unified error handler maintains full backward compatibility:

- Existing `ErrorHandler` continues to work
- All existing error patterns are supported
- Gradual migration is possible
- No breaking changes to existing APIs

## Future Enhancements

Potential future improvements:

- Error trend analysis
- Automatic error reporting
- Custom recovery suggestion plugins
- Error correlation across components
- Metrics integration for monitoring systems