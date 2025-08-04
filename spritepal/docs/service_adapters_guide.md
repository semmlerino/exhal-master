# Service Adapters Implementation Guide

## Overview

The service adapters in `/ui/dialogs/manual_offset/services/service_adapters.py` provide thread-safe, fallback-enabled access to core SpritePal services. They work around Phase 2 service issues by implementing adapter patterns that isolate the manual offset dialog from direct service dependencies.

## Architecture

### Service Adapter Pattern

Each adapter follows the same pattern:
1. **Thread Safety**: All operations protected by QMutex/threading.Lock
2. **Fallback Chain**: Multiple fallback strategies for service failures
3. **Graceful Degradation**: Continue operation even when services fail
4. **Resource Management**: Proper cleanup and weak references
5. **Error Recovery**: Automatic retry and recovery mechanisms

### Service Adapters

#### 1. PreviewServiceAdapter

**Purpose**: Thread-safe wrapper around PreviewGenerator singleton

**Features**:
- QMutex protection for thread safety
- Request queuing with conflict resolution
- Debounced preview generation (150ms)
- Weak references to prevent memory leaks
- Automatic service recovery

**Usage**:
```python
from ui.dialogs.manual_offset.services.service_adapters import PreviewServiceAdapter

# Initialize
preview_service = PreviewServiceAdapter(parent_widget)

# Set up signal connections
preview_service.preview_ready.connect(self._on_preview_ready)
preview_service.preview_error.connect(self._on_preview_error)

# Generate preview with thread safety
request = create_preview_request(...)
success = preview_service.generate_preview_safely(request, use_debounce=True)

# Set manager references
preview_service.set_managers(extraction_manager, rom_extractor)

# Cleanup
preview_service.cleanup()
```

**Signals**:
- `preview_ready(PreviewResult)`: Preview generation completed
- `preview_error(str, PreviewRequest)`: Preview generation failed
- `service_unavailable(str)`: Service is not available

#### 2. ValidationServiceAdapter

**Purpose**: Focused interface to FileValidator avoiding God Class complexity

**Features**:
- Fast file validation with LRU caching
- Focused interface using only specific validation methods
- Comprehensive error handling with fallbacks
- Thread-safe operations
- Cache invalidation based on file modification time

**Usage**:
```python
from ui.dialogs.manual_offset.services.service_adapters import ValidationServiceAdapter

# Initialize
validator = ValidationServiceAdapter()

# Validate files
is_valid, error_msg = validator.validate_rom_file("/path/to/rom.smc")
is_valid, error_msg = validator.validate_vram_file("/path/to/vram.dump")
is_valid, error_msg = validator.validate_palette_file("/path/to/palette.pal")

# Cache management
cache_stats = validator.get_cache_stats()
validator.clear_cache()
```

**Returns**: `tuple[bool, str]` - (is_valid, error_message)

#### 3. ErrorServiceAdapter

**Purpose**: Error handling with fallback to existing patterns

**Features**:
- Graceful fallback to existing error handler
- Context-aware error handling
- Thread-safe error processing
- Error categorization and routing
- Emergency fallback for critical situations

**Usage**:
```python
from ui.dialogs.manual_offset.services.service_adapters import ErrorServiceAdapter

# Initialize
error_service = ErrorServiceAdapter(parent_widget)

# Handle different types of errors
error_service.handle_error(exception, "Context description")
error_service.handle_validation_error(error, "/path/to/file")
error_service.handle_preview_error(error, offset=0x1000)
error_service.handle_service_error(error, "PreviewGenerator")
error_service.handle_thread_error(error, "WorkerThread")

# Get statistics
stats = error_service.get_error_stats()
```

## Integration Example

### Manual Offset Dialog Integration

```python
class ManualOffsetDialog(DialogBase):
    def __init__(self, parent=None):
        # Initialize instance variables first
        self.preview_service = None
        self.validation_service = None
        self.error_service = None
        
        # Call parent init
        super().__init__(parent)
        
        # Setup services
        self._setup_services()
    
    def _setup_services(self):
        """Setup service adapters with error handling."""
        try:
            # Preview service adapter
            self.preview_service = PreviewServiceAdapter(self)
            self._connect_preview_signals()
            
            # Validation service adapter
            self.validation_service = ValidationServiceAdapter()
            
            # Error service adapter
            self.error_service = ErrorServiceAdapter(self)
            
        except Exception as e:
            # Graceful degradation - continue without services
            if self.error_service:
                self.error_service.handle_error(e, "Service setup failed")
    
    def _connect_preview_signals(self):
        """Connect preview service signals with thread safety."""
        if self.preview_service:
            self.preview_service.preview_ready.connect(
                self._on_preview_ready,
                type=Qt.ConnectionType.QueuedConnection
            )
            self.preview_service.preview_error.connect(
                self._on_preview_error_safe
            )
    
    def _on_preview_error_safe(self, error_msg, request):
        """Safe preview error handler."""
        try:
            self._on_preview_error(error_msg, request)
        except Exception as e:
            if self.error_service:
                self.error_service.handle_error(e, "Preview error handler")
    
    def validate_file(self, file_path):
        """Validate file using service adapter."""
        if not self.validation_service:
            return False, "Validation service not available"
        
        is_valid, error_msg = self.validation_service.validate_rom_file(file_path)
        
        if not is_valid and self.error_service:
            self.error_service.handle_validation_error(error_msg, file_path)
        
        return is_valid, error_msg
    
    def cleanup(self):
        """Clean up service adapters."""
        if self.preview_service:
            self.preview_service.cleanup()
```

## Thread Safety Considerations

### QMutex vs threading.Lock

**Use QMutex for**:
- Qt object access
- Signal/slot operations
- Qt-specific resource management

**Use threading.Lock for**:
- Pure Python operations
- Non-Qt data structures
- Cross-platform compatibility

### Signal Connections

Always use `QueuedConnection` for cross-thread signals:

```python
self.service.signal.connect(
    self.slot,
    type=Qt.ConnectionType.QueuedConnection
)
```

## Error Handling Strategy

### Fallback Chain

1. **Primary Service**: Try unified/specialized service
2. **Fallback Service**: Use existing reliable service
3. **Basic Fallback**: Minimal functionality fallback
4. **Emergency Fallback**: Print/log only (prevents crashes)

### Error Categories

- **Validation Errors**: File validation failures
- **Preview Errors**: Preview generation failures
- **Service Errors**: Service initialization/operation failures
- **Thread Errors**: Threading and concurrency issues

## Performance Optimizations

### Caching

- **Validation Results**: Cached with file modification time
- **Preview Requests**: Debounced and deduplicated
- **Error Stats**: Lightweight counters

### Request Management

- **Preview Requests**: Conflict resolution and cancellation
- **Validation Requests**: LRU cache with size limits
- **Error Handling**: Minimal overhead tracking

## Debugging

### Service Status

```python
# Check service availability
preview_status = preview_service.get_service_status()
cache_stats = validation_service.get_cache_stats()
error_stats = error_service.get_error_stats()

print(f"Preview: {preview_status}")
print(f"Cache: {cache_stats}")
print(f"Errors: {error_stats}")
```

### Common Issues

1. **Service Unavailable**: Check service initialization
2. **Preview Not Working**: Verify manager references
3. **Validation Slow**: Check cache hit rate
4. **Memory Leaks**: Ensure proper cleanup

## Testing

Run the service adapter tests:

```bash
# Simple pattern tests (no Qt dependencies)
python3 test_service_adapters_simple.py

# Full integration tests (requires Qt environment)
python3 test_service_adapters_integration.py
```

## Best Practices

1. **Always Check Service Availability**: Services may not be available
2. **Use Weak References**: Prevent memory leaks with manager references
3. **Implement Cleanup**: Always cleanup resources in close/destruction
4. **Handle Exceptions**: Wrap all service calls in try-catch
5. **Use Appropriate Mutexes**: QMutex for Qt, threading.Lock for Python
6. **Connect Signals Safely**: Use QueuedConnection for cross-thread
7. **Test Fallbacks**: Ensure fallback paths work correctly

This implementation provides robust service access that works around Phase 2 issues while maintaining full functionality and thread safety.