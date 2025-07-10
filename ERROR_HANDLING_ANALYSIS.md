# Error Handling and Edge Cases Analysis - Pixel Editor

## Executive Summary

After reviewing the indexed pixel editor codebase (`indexed_pixel_editor.py`, `pixel_editor_widgets.py`, and test files), I've identified several areas where error handling could be improved and edge cases that need attention. While the code has some error handling in place, there are potential crashes, data loss scenarios, and unhandled exceptions that should be addressed.

## Critical Issues Found

### 1. Insufficient Input Validation

**Issue**: Several methods don't validate input parameters before use.

**Location**: `pixel_editor_widgets.py:273-290`
```python
# In ColorPaletteWidget.paintEvent()
if i < len(self.colors):
    try:
        r, g, b = self.colors[i]
        r = int(r) if r is not None else 0
        g = int(g) if g is not None else 0
        b = int(b) if b is not None else 0
        color = QColor(r, g, b)
    except (ValueError, TypeError, IndexError) as e:
        debug_log("PALETTE", f"Error with color {i}: {self.colors[i]} - {e}", "ERROR")
        color = QColor(0, 0, 0)
```
**Problem**: The code catches exceptions but doesn't prevent invalid data from being set in the first place.

### 2. Array Boundary Issues

**Location**: `pixel_editor_widgets.py:820-854`
```python
def draw_pixel(self, x: int, y: int):
    if self.image_data is None:
        debug_log("CANVAS", "Cannot draw pixel - no image data", "ERROR")
        return
    
    height, width = self.image_data.shape
    if 0 <= x < width and 0 <= y < height:
        # ... drawing code
    else:
        debug_log("CANVAS", f"Draw pixel out of bounds: ({x},{y}) for {width}x{height} image", "WARNING")
```
**Good**: Boundary checking is present, but only logs warnings instead of preventing the operation.

### 3. File I/O Error Handling

**Location**: `indexed_pixel_editor.py:893-909`
```python
def save_to_file(self, file_path: str):
    try:
        img = self.canvas.get_pil_image()
        if img:
            img.save(file_path)
            # ... success handling
    except Exception as e:
        QMessageBox.critical(self, "Error", f"Failed to save file: {e!s}")
```
**Issues**:
- Generic Exception catching masks specific errors
- No handling for disk full, permissions, or invalid path scenarios
- No validation of file path before attempting save

### 4. Null/None Reference Errors

**Location**: Multiple places check for None but not consistently
```python
# indexed_pixel_editor.py:1454
if self.canvas.image_data is None:
    return

# But other places access without checking:
# indexed_pixel_editor.py:1461
height, width = self.canvas.image_data.shape  # Could crash if None
```

### 5. Resource Cleanup

**Issue**: No proper cleanup in error paths
```python
# indexed_pixel_editor.py:119-134
def load_settings(self):
    try:
        if self.settings_file.exists():
            with open(self.settings_file) as f:  # File handle cleaned up by context manager
                loaded = json.load(f)
                self.settings.update(loaded)
    except Exception as e:
        debug_exception("SETTINGS", e)
        # No fallback or recovery mechanism
```

## Specific Edge Cases Not Handled

### 1. Empty/Corrupted Images
- Loading a 0x0 image could cause issues
- Corrupted PNG files might pass initial checks but fail later

### 2. Invalid Color Indices
**Location**: `pixel_editor_widgets.py:822-825`
```python
color = max(0, min(15, int(self.current_color)))  # Good clamping
old_value = self.image_data[y, x]
self.image_data[y, x] = np.uint8(color)
```
While color clamping is done, there's no validation that the input is numeric.

### 3. Large Image Handling
- No maximum size limits for images
- Could cause memory issues with very large images
- No progress indication for slow operations

### 4. Concurrent Access
- No handling for file being modified externally while editing
- Settings file could be corrupted by concurrent access

### 5. Palette File Validation
**Location**: `indexed_pixel_editor.py:1321-1331`
```python
def _validate_palette_file(self, data: dict) -> bool:
    try:
        if "palette" in data and "colors" in data["palette"]:
            colors = data["palette"]["colors"]
            return len(colors) >= 16 and all(len(color) >= 3 for color in colors)
    except (KeyError, TypeError, AttributeError):
        return False
```
**Issues**:
- Doesn't validate color value ranges (0-255)
- Doesn't check for non-numeric values in colors
- Silently returns False without logging specific error

### 6. Undo/Redo Stack Overflow
**Location**: `pixel_editor_widgets.py:388-389`
```python
self.undo_stack = deque(maxlen=50)
self.redo_stack = deque(maxlen=50)
```
**Good**: Uses maxlen to prevent unbounded growth
**Missing**: No handling for very large images where 50 copies could exhaust memory

### 7. Event Handler Errors
- Mouse/keyboard event handlers don't have try/except blocks
- A crash in event handler could freeze the UI

## Recommendations

### 1. Input Validation Layer
Add validation methods for all user inputs:
```python
def validate_color_index(self, index: Any) -> int:
    """Validate and return a valid color index"""
    try:
        index = int(index)
        return max(0, min(15, index))
    except (ValueError, TypeError):
        return 0  # Default to transparent
```

### 2. Comprehensive File Error Handling
```python
def save_to_file(self, file_path: str):
    try:
        # Validate path first
        if not file_path:
            raise ValueError("File path cannot be empty")
        
        dir_path = os.path.dirname(file_path)
        if dir_path and not os.path.exists(dir_path):
            raise FileNotFoundError(f"Directory does not exist: {dir_path}")
        
        if os.path.exists(file_path) and not os.access(file_path, os.W_OK):
            raise PermissionError(f"No write permission for file: {file_path}")
        
        img = self.canvas.get_pil_image()
        if img is None:
            raise ValueError("No image data to save")
            
        img.save(file_path)
        
    except PermissionError as e:
        QMessageBox.critical(self, "Permission Error", f"Cannot write to file: {e}")
    except OSError as e:
        if e.errno == 28:  # ENOSPC
            QMessageBox.critical(self, "Disk Full", "Not enough disk space to save file")
        else:
            QMessageBox.critical(self, "File Error", f"Failed to save file: {e}")
    except Exception as e:
        QMessageBox.critical(self, "Unexpected Error", f"An unexpected error occurred: {e}")
```

### 3. Add Image Size Limits
```python
MAX_IMAGE_DIMENSION = 1024  # Reasonable limit for sprite editing

def load_image(self, pil_image: Image.Image):
    if pil_image.mode != "P":
        raise ValueError("Image must be in indexed color mode (P)")
    
    width, height = pil_image.size
    if width > MAX_IMAGE_DIMENSION or height > MAX_IMAGE_DIMENSION:
        raise ValueError(f"Image too large: {width}x{height}. Maximum dimension is {MAX_IMAGE_DIMENSION}")
    
    if width == 0 or height == 0:
        raise ValueError("Image has zero dimension")
```

### 4. Protect Event Handlers
```python
def mousePressEvent(self, event: QMouseEvent):
    try:
        # ... existing code ...
    except Exception as e:
        debug_exception("CANVAS", e)
        # Ensure UI remains responsive
```

### 5. Add Null Checks Consistently
Create helper methods:
```python
def ensure_image_loaded(self) -> bool:
    """Ensure image is loaded, show error if not"""
    if self.canvas.image_data is None:
        QMessageBox.warning(self, "No Image", "Please create or load an image first")
        return False
    return True
```

### 6. Memory-Aware Undo System
```python
def save_undo(self):
    if self.image_data is not None:
        # Check memory usage before saving
        image_size = self.image_data.nbytes
        if len(self.undo_stack) * image_size > 100 * 1024 * 1024:  # 100MB limit
            # Clear oldest entries
            while len(self.undo_stack) > 10:
                self.undo_stack.popleft()
        
        self.undo_stack.append(self.image_data.copy())
        self.redo_stack.clear()
```

### 7. Add Progress Indicators
For potentially slow operations:
```python
def flood_fill(self, x: int, y: int):
    # Show progress for large fills
    if self.image_data.size > 10000:  # Large image
        progress = QProgressDialog("Filling...", "Cancel", 0, 100, self)
        progress.setWindowModality(Qt.WindowModal)
        # ... implement fill with progress updates
```

## Testing Recommendations

1. **Boundary Testing**: Test with 1x1, 0x0 (should fail), and maximum size images
2. **Invalid Input Testing**: Test with corrupted files, wrong formats, invalid color values
3. **Resource Testing**: Test with low memory, full disk, read-only files
4. **Concurrency Testing**: Test opening same file in multiple instances
5. **Error Recovery Testing**: Ensure UI remains responsive after errors

## Conclusion

While the pixel editor has basic error handling, it needs improvements in:
- Input validation
- Specific exception handling instead of generic catches
- Consistent null/boundary checking
- Resource management
- User feedback for errors
- Recovery mechanisms

Implementing these improvements will make the application more robust and prevent data loss scenarios.