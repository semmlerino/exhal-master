# Standardized Progress API Documentation

## Overview

The worker progress system has been standardized to provide consistent behavior across all components while maintaining backward compatibility. All workers now emit progress with both a percentage value and an optional descriptive message.

## Signal Format

### New Standard Format
```python
progress = pyqtSignal(int, str)  # Progress percentage (0-100), optional message
```

### Emission Pattern
```python
self.emit_progress(value: int, message: str = "")
```

## Worker Implementation

### BaseWorker Class
All workers inherit from `BaseWorker` which provides:
- Standardized progress signal: `pyqtSignal(int, str)`
- Helper method: `emit_progress(value, message="")`
- Cancellation support
- Error handling

### Example Worker Implementation
```python
class FileLoadWorker(BaseWorker):
    def run(self):
        self.emit_progress(0, f"Loading {self.file_path.name}...")
        # ... perform operations ...
        self.emit_progress(50, "Processing image format...")
        # ... more operations ...
        self.emit_progress(100, "Loading complete!")
```

## Progress Messages by Worker

### FileLoadWorker
- 0%: "Loading {filename}..."
- 20%: "Opening image file..."
- 40%: "Processing image format..."
- 60%: "Extracting image data..."
- 80%: "Preparing metadata..."
- 100%: "Loading complete!"

### FileSaveWorker
- 0%: "Preparing to save..."
- 20%: "Validating image data..."
- 40%: "Creating indexed image..."
- 60%: "Applying color palette..."
- 80%: "Writing {format} to disk..."
- 100%: "Save complete!"

### PaletteLoadWorker
- 0%: "Loading palette from {filename}..."
- 30%: "Reading palette file..."
- 60%: Format-specific messages:
  - JSON: "Parsing JSON palette data..."
  - Binary: "Converting binary palette data..."
  - GIMP: "Parsing GIMP palette format..."
- 90%: "Validating palette colors..."
- 100%: "Palette loaded successfully!"

## ProgressDialog API

### Existing Methods
```python
def update_progress(self, value: int, message: str = ""):
    """Update progress bar value and optionally update message."""
    
def update_message(self, message: str):
    """Update the main message."""
    
def update_status(self, status: str):
    """Update the status label."""
```

### New Utility Methods
```python
def set_value(self, value: int):
    """Set progress value without changing message."""
    
def set_indeterminate(self, show: bool = True):
    """Set progress bar to indeterminate mode."""
    
def reset(self):
    """Reset dialog to initial state."""
```

## Connection Patterns

### Standard Connection
```python
worker.progress.connect(progress_dialog.update_progress)
```

### Custom Handler
```python
def handle_progress(value, message):
    progress_dialog.update_progress(value, message)
    logger.info(f"Progress: {value}% - {message}")
    
worker.progress.connect(handle_progress)
```

### Legacy Single-Parameter Connection (Still Works!)
```python
# Connecting to methods expecting only value
worker.progress.connect(progress_bar.setValue)  # Works!
worker.progress.connect(lambda v: print(f"{v}%"))  # Works!
```

## Backward Compatibility

The new signal format maintains full backward compatibility:

1. **Existing connections continue to work** - Slots expecting only one parameter will receive just the value
2. **No code changes required** - Existing code connecting workers to ProgressDialog works unchanged
3. **Gradual migration** - New code can take advantage of messages while old code continues to function

### Example: Mixed Usage
```python
# Old style - still works
worker.progress.connect(progress_bar.setValue)

# New style - uses messages
worker.progress.connect(progress_dialog.update_progress)

# Both can connect to the same signal!
```

## Best Practices

### 1. Provide Meaningful Messages
```python
# Good
self.emit_progress(50, "Converting image format...")

# Less helpful
self.emit_progress(50, "Working...")
```

### 2. Update Progress Regularly
Emit progress at logical stages of the operation:
- Start of operation (0%)
- Major milestones (20%, 40%, 60%, 80%)
- Completion (100%)

### 3. Use Indeterminate Mode When Appropriate
```python
progress_dialog.set_indeterminate(True)  # For unknown duration
# ... perform operation ...
progress_dialog.set_indeterminate(False)
progress_dialog.set_value(100)
```

### 4. Handle Cancellation
```python
if self.is_cancelled():
    return
```

## Migration Guide

### For New Code
Use the full signal format with meaningful messages:
```python
self.emit_progress(percentage, "Descriptive message...")
```

### For Existing Code
No changes required! Existing connections will continue to work.

### Optional Enhancement
To add messages to existing workers:
```python
# Before
self.emit_progress(50)

# After (enhanced)
self.emit_progress(50, "Processing data...")
```

## Testing

### Test Progress Messages
```python
def test_worker_progress():
    worker = FileLoadWorker("test.png")
    progress_updates = []
    
    worker.progress.connect(lambda v, m: progress_updates.append((v, m)))
    worker.run()
    
    # Verify both value and message
    assert progress_updates[0] == (0, "Loading test.png...")
```

### Test Backward Compatibility
```python
def test_legacy_connection():
    worker = FileLoadWorker("test.png")
    values = []
    
    # Legacy connection expecting only value
    worker.progress.connect(lambda v: values.append(v))
    worker.progress.emit(50, "Message ignored by legacy slot")
    
    assert values[0] == 50  # Still works!
```

## Summary

The standardized progress API provides:
- **Consistency**: All workers use the same signal format
- **Better UX**: Users see descriptive progress messages
- **Backward Compatibility**: Existing code continues to work
- **Flexibility**: New utility methods for special cases
- **Future-Proof**: Easy to extend for new requirements

This standardization improves user experience while maintaining full compatibility with existing code.