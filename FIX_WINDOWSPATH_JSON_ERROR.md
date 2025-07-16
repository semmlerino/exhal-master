# Fix for WindowsPath JSON Serialization Error

## Problem
The error "Object of type WindowsPath is not JSON serializable" occurs when PIL's `image.info` dictionary contains Path objects or other non-JSON-serializable objects. This happens in two places:

1. `pixel_editor/core/pixel_editor_workers.py` (line 196): `metadata["info"] = image.info`
2. `pixel_editor/core/pixel_editor_models.py` (line 65): `metadata["info"] = pil_image.info`

## Root Cause
When PIL loads an image, the `image.info` dictionary can contain:
- `WindowsPath` or `PosixPath` objects
- Other non-JSON-serializable objects (like datetime objects, bytes, etc.)
- Various metadata that might not be string-based

When this metadata is later serialized to JSON (for saving project state or during testing), it fails.

## Solution

### Option 1: Create a sanitize helper function (Recommended)

```python
def sanitize_for_json(obj):
    """Convert non-JSON-serializable objects to JSON-safe types."""
    if isinstance(obj, (str, int, float, bool, type(None))):
        return obj
    elif isinstance(obj, (Path, WindowsPath, PosixPath)):
        return str(obj)
    elif isinstance(obj, bytes):
        return obj.decode('utf-8', errors='ignore')
    elif isinstance(obj, dict):
        return {k: sanitize_for_json(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [sanitize_for_json(item) for item in obj]
    elif hasattr(obj, '__dict__'):
        return str(obj)  # Convert objects to string representation
    else:
        return str(obj)  # Fallback to string
```

### Option 2: Quick fix - Convert to strings

Replace the problematic lines with:

```python
# In pixel_editor_workers.py line 196:
if hasattr(image, "info"):
    metadata["info"] = {k: str(v) for k, v in image.info.items()}

# In pixel_editor_models.py line 65:
if hasattr(pil_image, "info"):
    metadata["info"] = {k: str(v) for k, v in pil_image.info.items()}
```

### Option 3: Filter out problematic keys

```python
# Only keep string-valued items
if hasattr(image, "info"):
    metadata["info"] = {
        k: v for k, v in image.info.items() 
        if isinstance(v, (str, int, float, bool, type(None)))
    }
```

## Testing

After applying the fix, test with:
1. Windows paths
2. Linux paths  
3. Images with complex metadata (EXIF data, etc.)
4. Images without metadata

## Additional Considerations

1. **Data Loss**: Converting everything to strings might lose type information
2. **Debugging**: The original type information might be useful for debugging
3. **Compatibility**: Ensure saved projects can still be loaded

## Recommended Implementation

Add the sanitize function to `pixel_editor_utils.py` and use it in both locations:

```python
# In both files:
if hasattr(image, "info"):
    from pixel_editor_utils import sanitize_for_json
    metadata["info"] = sanitize_for_json(image.info)
```