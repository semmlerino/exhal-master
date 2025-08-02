# Import Location Warnings (PLC0415)

## Overview
Ruff's PLC0415 rule flags imports that are not at the top level of a file. While this is generally good practice, there are legitimate reasons to have imports inside functions.

## Why These Warnings Exist

### 1. Circular Dependencies
The most common reason for imports inside functions is to avoid circular import errors.

Example from `core/managers/factory.py`:
```python
def create_extraction_manager(self, parent: Optional[QObject] = None) -> ExtractionManager:
    from . import get_extraction_manager  # Avoid circular import
    return get_extraction_manager()
```

This happens because:
- `factory.py` is imported by `__init__.py`
- `__init__.py` imports from `registry.py`
- `registry.py` might need `factory.py`
- Creating a circular dependency

### 2. Optional Dependencies
Some imports are only needed in specific code paths and importing them at the top level would create unnecessary dependencies.

Example from `tests/conftest.py`:
```python
def create_test_app():
    from PyQt6.QtWidgets import QApplication  # Only needed when creating app
    return QApplication([])
```

### 3. Performance Optimization
Heavy imports that are only needed in rare code paths can be deferred to improve startup time.

## Current Status
- **core/managers/**: 4 instances (circular dependency avoidance)
- **tests/**: 15+ instances (test isolation and optional dependencies)
- **ui/**: Several instances (lazy loading of dialogs)

## Recommendations for Solo Developer

### Do NOT Fix These
These warnings are intentional design decisions to avoid real problems:
1. Circular dependency avoidance in managers
2. Test isolation in conftest and fixtures
3. Lazy loading of heavy UI components

### When to Fix
Only fix if:
1. The import is truly unnecessary inside the function
2. Moving it to top-level doesn't create circular imports
3. It doesn't impact performance or create unwanted dependencies

### How to Suppress
If the warnings become annoying, you can:
1. Add `# noqa: PLC0415` to specific lines
2. Add to `ruff.toml`:
```toml
[tool.ruff.lint]
ignore = ["PLC0415"]  # Allow imports inside functions
```

## Conclusion
For a solo developer, these warnings are noise. The imports are inside functions for good architectural reasons. Don't waste time "fixing" them unless they're actually causing problems.