# Pytest Pattern Fixes

## PT017: Use pytest.raises() instead of except blocks with assertions

### The Issue
Ruff's PT017 rule flags code that catches exceptions and then asserts on them. This pattern is considered less Pythonic than using `pytest.raises()`.

### Current Pattern (Flagged by PT017)
```python
try:
    some_operation()
    assert False, "Should have raised an exception"
except Exception as e:
    assert "expected message" in str(e)
```

### Recommended Pattern
```python
with pytest.raises(Exception, match="expected message"):
    some_operation()
```

### More Complex Example
```python
# Current
try:
    controller.validate_extraction_params({})
except Exception as e:
    assert "parameter" in str(e).lower() or "validation" in str(e).lower()

# Recommended
with pytest.raises(Exception, match=r"(?i)(parameter|validation)"):
    controller.validate_extraction_params({})
```

### When to Fix
- Fix when writing new tests
- Fix when modifying existing tests
- Don't mass-refactor unless the warnings become annoying

### Current Status
- 59 PT017 warnings in test files
- 0 PT011 warnings

For a solo developer, these are low priority style issues that don't affect functionality.