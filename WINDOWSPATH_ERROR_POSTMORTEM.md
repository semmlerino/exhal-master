# WindowsPath JSON Serialization Error - Postmortem

## Why This Error Was Missed

### 1. Cross-Platform Testing Gap
- **Development Environment**: The tests were run on Linux (WSL)
- **Production Environment**: The error occurred on Windows
- **Key Difference**: PIL's `image.info` dictionary can contain platform-specific Path objects (`WindowsPath` on Windows, `PosixPath` on Linux)

### 2. Test Coverage Blind Spot
The original test in `test_load_non_image_file` had this assertion:
```python
# Should emit error about invalid image
assert len(error_messages) > 0
```

This test was **too generic** - it only checked that "some error occurred" rather than validating the specific error type. When the AttributeError occurred, it was caught and emitted as an error message, so the test passed despite the unexpected error.

### 3. Misdiagnosis
When I saw the error during testing:
```
[ERROR] Load error: Unexpected error loading file: 'str' object has no attribute 'name'
AttributeError: 'str' object has no attribute 'name'
```

I investigated and found that `Path(file_path)` was being used correctly in the `__init__` method. I concluded the code was correct without realizing there was a **different issue** - the JSON serialization of Path objects.

### 4. The Real Issue
The actual problem was **not** with the Path conversion in `FileLoadWorker.__init__`. Instead:

1. PIL's `image.info` dictionary can contain non-JSON-serializable objects
2. The code directly assigned `image.info` to metadata dictionaries:
   ```python
   metadata["info"] = image.info  # Can contain WindowsPath objects!
   ```
3. When this metadata was later serialized to JSON, it failed

## The Fix

### Solution Implemented
1. Created a `sanitize_for_json()` function that recursively converts non-serializable objects to strings
2. Applied it to both locations where `image.info` is stored:
   - `pixel_editor_workers.py` line 198
   - `pixel_editor_models.py` line 67

### Code Changes
```python
# Before:
metadata["info"] = image.info

# After:
metadata["info"] = sanitize_for_json(image.info)
```

## Lessons Learned

### 1. Test Specificity
**Bad Test**:
```python
assert len(error_messages) > 0  # Any error passes!
```

**Good Test**:
```python
assert len(error_messages) > 0
assert "Failed to open image" in error_messages[0]
assert "AttributeError" not in str(error_messages)  # No unexpected errors
```

### 2. Cross-Platform Considerations
- Always consider platform-specific behavior, especially with file paths
- PIL's behavior can differ between Windows and Linux
- Test on multiple platforms when dealing with file I/O

### 3. Error Investigation
- **Always investigate unexpected errors**, even if tests pass
- A passing test doesn't mean the code is correct
- Check the **full error message** and stack trace

### 4. Data Serialization
- When accepting external data (like PIL's `image.info`), always sanitize before storing
- Never assume third-party data structures are JSON-serializable
- Create explicit sanitization functions for complex data

## Prevention Strategies

1. **Defensive Programming**: Always sanitize external data before storage
2. **Explicit Testing**: Test for specific expected behaviors, not just "no crash"
3. **Cross-Platform CI**: Run tests on both Windows and Linux
4. **Error Message Validation**: Tests should validate error messages match expectations
5. **Type Checking**: Use type hints and runtime validation for data structures

## Impact

This bug would have caused:
- Crashes when loading images with certain metadata on Windows
- Failed project saves when images contain Path objects in metadata
- Poor user experience with cryptic error messages

The fix ensures robust handling of all image metadata across platforms.