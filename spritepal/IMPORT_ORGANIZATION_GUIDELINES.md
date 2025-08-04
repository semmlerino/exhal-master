# Import Organization Guidelines for SpritePal

## Overview
This document provides guidelines for import organization in the SpritePal codebase, specifically addressing E402 and PLC0415 violations found by ruff.

## E402 Violations (Module imports not at top of file)
**Status**: ✅ Fixed (37 instances resolved)

All E402 violations have been fixed by moving imports to the top of files, with the following exceptions:
- `debug_duplicate_slider.py`: Imports remain after monkey patching code with `# noqa: E402` comments, as this is intentional for debugging purposes.

## PLC0415 Violations (Imports inside functions/methods)
**Status**: 📊 Analyzed (226 instances categorized)

### Analysis Results
- **Test imports**: 185 violations (82%)
- **Circular import prevention**: 11 violations (5%)
- **Lazy loading**: 9 violations (4%)
- **Multiprocessing**: 5 violations (2%)
- **Uncategorized**: 16 violations (7%)

### Guidelines for PLC0415 Violations

#### 1. **KEEP** - Circular Import Prevention (11 instances)
These imports MUST remain inside functions to prevent circular dependencies:

**Pattern**: Manager singletons and registry access
```python
def some_method(self):
    from utils.settings_manager import get_settings_manager
    from core.managers.registry import ManagerRegistry
```

**Files affected**:
- `core/navigation/manager.py`
- `ui/managers/status_bar_manager.py`
- `ui/managers/session_coordinator.py`
- Various test files accessing managers

**Rationale**: These modules have interdependencies that would create import cycles if imported at the top level.

#### 2. **KEEP** - Multiprocessing Worker Functions (5 instances)
These imports MUST remain inside worker functions:

**Pattern**: Signal handling in worker processes
```python
def worker_process(request_queue, result_queue):
    import signal
    signal.signal(signal.SIGINT, signal.SIG_IGN)
```

**Files affected**:
- `core/hal_compression.py` (line 74)

**Rationale**: Worker processes need their own signal handling setup, independent of the parent process.

#### 3. **KEEP** - Heavy/Optional Dependencies (9 instances)
These imports should remain inside functions for performance:

**Pattern**: Heavy libraries loaded on-demand
```python
def analyze_memory(self):
    import psutil  # Only loaded when memory analysis is needed
```

**Files affected**:
- PIL/Pillow imports in test files
- psutil in performance tests
- matplotlib in visualization code (if any)

**Rationale**: These libraries are heavy and only needed in specific scenarios. Loading them at module level would slow down imports.

#### 4. **FIX** - Test File Imports (185 instances)
Most test file imports can be moved to the top level:

**Current pattern** (can be fixed):
```python
def test_something(self):
    from spritepal.some.module import SomeClass  # Unnecessary
```

**Fixed pattern**:
```python
from spritepal.some.module import SomeClass

def test_something(self):
    # Use SomeClass directly
```

**Exception**: Keep inside functions if:
- Testing import errors or module availability
- Mocking needs to happen before import
- Testing circular import scenarios

#### 5. **REVIEW** - Uncategorized (16 instances)
These need case-by-case review:

**Navigation module imports**: May be for plugin system flexibility
- `core/navigation/caching.py`
- `core/navigation/plugins.py`

**UI component imports**: May be for lazy loading of heavy widgets
- `ui/components/navigation/sprite_navigator.py`
- `ui/components/panels/scan_controls_panel.py`

## Recommended Actions

### Phase 1: Quick Wins (Test Files)
1. Create a script to automatically move test imports to top-level
2. Exclude imports that are testing import behavior itself
3. Run tests to ensure no breakage

### Phase 2: Document Intentional Cases
1. Add `# noqa: PLC0415` comments with explanations for:
   - Circular import prevention cases
   - Multiprocessing worker functions
   - Heavy dependency lazy loading

### Phase 3: Review Uncategorized
1. Analyze each uncategorized case
2. Either fix or document with `# noqa` comment

## Example Documentation Comments

```python
# Circular import prevention
def get_current_settings(self):
    from utils.settings_manager import get_settings_manager  # noqa: PLC0415 - circular import
    
# Lazy loading for performance
def generate_preview_image(self):
    from PIL import Image  # noqa: PLC0415 - lazy load heavy dependency
    
# Worker process isolation
def worker_func():
    import signal  # noqa: PLC0415 - worker process needs own signal handling
```

## Summary

- **E402**: All 37 violations fixed (except intentional debug case)
- **PLC0415**: 226 violations categorized:
  - 11 must keep (circular imports)
  - 5 must keep (multiprocessing)
  - 9 should keep (performance)
  - 185 can fix (test imports)
  - 16 need review

This approach balances code quality with practical considerations like circular import prevention and performance optimization.