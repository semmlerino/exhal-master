# Type Safety Improvements for SpritePal Tests

## Overview

This document outlines the type safety improvements made to the SpritePal test suite, focusing on proper typing, better mock usage, and basedpyright-specific configurations.

## Key Improvements Made

### 1. Basedpyright Configuration for Tests

Added per-file basedpyright configuration to test files:

```python
# pyright: basic  # Less strict for test files
# pyright: reportPrivateUsage=false  # Allow testing private methods
# pyright: reportUnknownMemberType=warning  # Mock attributes are dynamic
# pyright: reportUnknownArgumentType=warning  # Test data may be dynamic
# pyright: reportUntypedFunctionDecorator=error  # Type all decorators
# pyright: reportUnnecessaryTypeIgnoreComment=error  # Clean up unused ignores
```

### 2. Improved conftest.py Typing

**Before:**
```python
@pytest.fixture
def mock_main_window() -> Any:  # MockMainWindowProtocol but avoid import issues
    """Provide a fully configured mock main window."""
    return MockFactory.create_main_window()
```

**After:**
```python
@pytest.fixture
def mock_main_window() -> "MockMainWindowProtocol":
    """Provide a fully configured mock main window."""
    return MockFactory.create_main_window()
```

### 3. Protocol-Based Mock Typing

Leveraged existing protocol infrastructure for type-safe mocks:

```python
if TYPE_CHECKING:
    from tests.infrastructure.test_protocols import (
        MockExtractionManagerProtocol,
        MockInjectionManagerProtocol,
        MockMainWindowProtocol,
        MockQtBotProtocol,
        MockSessionManagerProtocol,
    )
```

### 4. Proper Function Signatures

**Before:**
```python
def test_worker_initialization(self, qtbot):
    """Test worker initialization with proper default values."""
```

**After:**
```python
def test_worker_initialization(self, qtbot: "MockQtBotProtocol") -> None:
    """Test worker initialization with proper default values."""
```

### 5. Better Import Organization

Organized imports to use TYPE_CHECKING for test-specific protocols:

```python
from typing import TYPE_CHECKING
from unittest.mock import Mock, patch

if TYPE_CHECKING:
    from tests.infrastructure.test_protocols import MockQtBotProtocol
```

### 6. Strategic pyright: ignore Usage

Replaced generic `type: ignore` with specific basedpyright rules:

**Before:**
```python
WorkerManager.cleanup_all()  # type: ignore[attr-defined]
```

**After:**
```python
WorkerManager.cleanup_all()  # pyright: ignore[reportUnknownMemberType]  # WorkerManager may have different interface
```

## Type Safety Patterns Demonstrated

### 1. Real Objects Over Mocks

```python
def test_real_object_preference(self) -> None:
    """Demonstrate using real objects over mocks when possible."""
    # PREFER: Real objects for better type safety
    test_data = {
        "vram_path": "test.dmp",
        "create_grayscale": True,
    }
    
    # Type checker knows these are correct types
    vram_path: str = test_data["vram_path"]
    create_grayscale: bool = test_data["create_grayscale"]
```

### 2. Type-Safe Mock Creation

```python
def test_typed_mock_usage(
    self, 
    mock_main_window: "MockMainWindowProtocol"
) -> None:
    """Demonstrate type-safe mock usage with protocols."""
    # Mock is properly typed via protocol
    mock_main_window.get_extraction_params.return_value = {  # pyright: ignore[reportUnknownMemberType]
        "vram_path": "test.dmp",
        "output_base": "sprites"
    }
    
    # Type checker knows the interface
    result = mock_main_window.get_extraction_params()
    assert isinstance(result, dict)
```

### 3. Proper Parametrized Test Typing

```python
@pytest.mark.parametrize(
    "input_value,expected_type,expected_result",
    [
        ("valid_string", str, True),
        (42, int, True),
        (None, type(None), False),
    ]
)
def test_parametrized_with_types(
    self, 
    input_value: str | int | None,
    expected_type: type[str] | type[int] | type[None],
    expected_result: bool
) -> None:
    """Demonstrate type-safe parametrized testing."""
    assert isinstance(input_value, expected_type) == expected_result
```

### 4. Type-Safe Fixture Creation

```python
@pytest.fixture
def typed_test_data(self) -> dict[str, str | bool]:
    """Provide properly typed test data."""
    return {
        "rom_path": "test.sfc",
        "output_dir": "/tmp/output", 
        "create_metadata": True,
    }
```

## Benefits Achieved

### 1. Better IDE Support
- Accurate autocompletion for mock objects
- Proper error highlighting for type mismatches
- Better refactoring support

### 2. Catch Type Errors Early
- basedpyright can catch type errors before runtime
- Prevents common mock-related bugs
- Ensures mock interfaces match real objects

### 3. Improved Test Maintainability
- Clear documentation of expected types
- Easier to understand test dependencies
- Better error messages when tests fail

### 4. Enhanced Code Quality
- Consistent typing patterns across test files
- Proper use of pyright ignore comments
- Strategic use of real objects vs mocks

## Configuration Recommendations

### For pytest.ini
```ini
[pytest]
# Enable type checking in tests
addopts = 
    -v
    --tb=short
    --strict-markers

# Qt-specific settings
qt_api = pyside6
qt_default_raise = true
```

### For pyproject.toml (basedpyright configuration)
```toml
[tool.basedpyright]
typeCheckingMode = "basic"  # Relaxed for tests
testPatterns = ["**/test_*.py", "**/*_test.py", "**/tests/**/*.py"]

# Test-specific relaxations
reportPrivateUsage = "warning"  # Tests may access private members
reportUnknownMemberType = "warning"  # Mock attributes are dynamic
reportUnknownArgumentType = "warning"  # Test data may be dynamic

# Enforce good practices
reportUnnecessaryTypeIgnoreComment = "error"  # Clean up unused ignores
reportUntypedFunctionDecorator = "error"  # Type all decorators
```

## Migration Guide

### Step 1: Add basedpyright Configuration
Add the pyright configuration comments to the top of test files.

### Step 2: Update Fixture Types
Replace `Any` return types with proper protocol types or specific types.

### Step 3: Add Function Return Types
Add `-> None` to test functions that don't return anything.

### Step 4: Improve Mock Typing
Use protocol types for mock fixtures and proper pyright ignore comments.

### Step 5: Prefer Real Objects
Replace mocks with real objects where possible for better type safety.

## Files Modified

1. `/tests/conftest.py` - Main fixture improvements
2. `/tests/test_type_safety_example.py` - Comprehensive example patterns
3. `/tests/test_worker_base.py` - Example of test file improvements
4. `/tests/infrastructure/test_protocols.py` - Protocol documentation

## Next Steps

1. **Apply patterns to more test files**: Use the examples in `test_type_safety_example.py` as templates
2. **Run basedpyright on tests**: `basedpyright tests/ --stats` to find more type issues
3. **Create migration script**: Automate conversion of existing test files
4. **Add CI integration**: Include type checking in CI/CD pipeline
5. **Review mock usage**: Identify more opportunities to use real objects

## Benefits vs Maintenance

### Benefits
- ✅ Catches type errors at development time
- ✅ Better IDE support and autocompletion
- ✅ More maintainable and self-documenting tests
- ✅ Prevents runtime errors from type mismatches
- ✅ Better refactoring support

### Maintenance Considerations
- ⚠️ Slightly more verbose test code
- ⚠️ Need to maintain protocol definitions
- ⚠️ Learning curve for team members
- ⚠️ Some edge cases may require type: ignore

The benefits significantly outweigh the maintenance overhead, especially for a large test suite like SpritePal's.