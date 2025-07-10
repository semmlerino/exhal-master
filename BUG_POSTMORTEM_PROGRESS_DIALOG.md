# Bug Postmortem: ProgressDialog.update_progress() Argument Mismatch

## Summary
A TypeError occurred because `ProgressDialog.update_progress()` was implemented to accept only 1 argument (value) but was called with 2 arguments (value, message) throughout the codebase.

## Timeline
1. Created `ProgressDialog` with `update_progress(value: int)`
2. Created worker integration that connected signals correctly
3. Added manual calls with `update_progress(value, message)` pattern
4. Never ran the code to test integration
5. Bug discovered post-commit by user

## Root Causes

### 1. **Inconsistent Mental Model**
During implementation, I had two different mental models:
- **Widget implementation**: Simple progress bar update
- **Usage pattern**: Progress with status messages

This led to implementing one interface but using another.

### 2. **PyQt Signal Masking**
```python
# This worked (signal passes only value):
worker.progress.connect(dialog.update_progress)

# This failed (manual call with 2 args):
dialog.update_progress(30, "Loading...")
```

The signal connections worked fine, creating false confidence.

### 3. **No Integration Testing**
- Unit tests wouldn't catch this (different components)
- Integration tests timed out and were skipped
- Manual testing wasn't performed

### 4. **Copy-Paste Pattern**
Once the first `update_progress(value, message)` call was written, it was copied throughout the file without verification.

## The Fix

Changed the method signature to accept an optional message:

```python
def update_progress(self, value: int, message: str = ""):
    """Update progress bar value and optionally update message."""
    self.progress_bar.setValue(value)
    if message:
        self.message_label.setText(message)
```

This maintains backward compatibility while supporting the intended usage.

## Lessons Learned

### 1. **Design API Before Usage**
Write the interface documentation/signature before writing code that uses it.

### 2. **Test at Integration Points**
The bugs hide where components connect. Always test:
- Signal connections
- Direct method calls
- Mixed usage patterns

### 3. **Run the Code**
No amount of code review replaces actually running the application.

### 4. **Watch for Pattern Mismatches**
When you see repeated calls with the same "wrong" signature, the signature might be what's wrong, not the calls.

### 5. **Type Checking Isn't Enough**
Even with type hints, PyQt signals bypass normal checks. Need runtime verification.

## Prevention Strategies

### 1. **Consistent API Design**
```python
# Option 1: Single responsibility
def update_progress(self, value: int): ...
def update_message(self, message: str): ...

# Option 2: Combined (what we chose)
def update_progress(self, value: int, message: str = ""): ...
```

### 2. **Integration Test Template**
```python
def test_progress_dialog_integration():
    dialog = ProgressDialog()
    
    # Test direct calls
    dialog.update_progress(50, "Half way")
    
    # Test signal connections
    worker = Worker()
    worker.progress.connect(dialog.update_progress)
    worker.progress.emit(75)
    
    # Verify both work
    assert dialog.progress_bar.value() == 75
```

### 3. **API Documentation**
Always document expected usage:
```python
"""
Example usage:
    # With message
    dialog.update_progress(30, "Loading file...")
    
    # Without message (signal connection)
    worker.progress.connect(dialog.update_progress)
"""
```

## Impact
- **Severity**: Medium (feature broken but app doesn't crash)
- **Scope**: All palette loading operations
- **User Experience**: Error dialogs instead of progress
- **Fix Complexity**: Trivial (one line change)

## Conclusion
This bug represents a common integration issue where components work in isolation but fail when connected. The fix was simple, but the lesson is valuable: **always test the integration points**, especially with framework-specific patterns like PyQt signals.