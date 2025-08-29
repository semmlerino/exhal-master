# SpritePal Type Safety Implementation Guide

## Quick Start Commands

```bash
# Ensure you're in the spritepal directory with venv activated
source venv/bin/activate

# Check current type status
python3 -m basedpyright core/workers/base.py core/workers/specialized.py
# Should show: 0 errors, 0 warnings, 0 notes

# Check annotation progress
python3 -m ruff check --select ANN core/ | wc -l
# Current: 920 issues (down from 953)

# Check type checking imports
python3 -m ruff check --select TCH core/ | wc -l  
# Current: 242 issues
```

## Phase 2 Continuation: Core Module Annotations

### 1. Auto-fix Safe Annotations (5 minutes)

```bash
# Fix missing __init__ return types automatically
python3 -m ruff check --select ANN204 core/ --fix-only

# Fix TYPE_CHECKING imports automatically  
python3 -m ruff check --select TCH core/ --fix-only

# Check improvement
python3 -m ruff check --select ANN core/ | wc -l
```

### 2. Manual Method Return Types (15-30 minutes)

Focus on public API methods first:

```bash
# Find missing return type annotations for public methods
python3 -m ruff check --select ANN201 core/managers/ | head -10
python3 -m ruff check --select ANN201 core/protocols/ | head -10
```

**Pattern to apply:**
```python
# Before
def cleanup(self):
    """Clean up resources"""
    pass

# After  
def cleanup(self) -> None:
    """Clean up resources"""
    pass
```

### 3. Parameter Type Annotations (30-45 minutes)

```bash
# Find missing parameter annotations
python3 -m ruff check --select ANN001 core/managers/ | head -10
```

**Common patterns:**
```python
# Before
def process_data(self, data, options=None):

# After
def process_data(self, data: bytes, options: dict[str, Any] | None = None) -> bool:
```

## Phase 3: Advanced Type Features

### 1. Expand TypedDict Usage

Look for `dict[str, Any]` patterns and replace:

```bash
grep -r "dict\[str, Any\]" core/ | head -5
```

**Example replacement:**
```python
# Before
def configure(self, settings: dict[str, Any]) -> None:

# After  
class CacheSettings(TypedDict):
    size_limit: int
    ttl_seconds: int
    persist_to_disk: NotRequired[bool]

def configure(self, settings: CacheSettings) -> None:
```

### 2. Apply Literal Types

Use the constants from `core/type_constants.py`:

```python
from core.type_constants import LogLevel, CompressionType

def set_log_level(self, level: LogLevel) -> None:
    """Set logging level with type safety."""
    
def compress_data(self, data: bytes, method: CompressionType) -> bytes:
    """Compress data using specified method."""
```

### 3. Add TypeGuard Usage

Use guards from `core/type_guards.py`:

```python
from core.type_guards import is_valid_rom_path, is_manager_instance

def load_rom(self, path: str) -> None:
    if not is_valid_rom_path(path):
        raise ValueError(f"Invalid ROM path: {path}")
    # Type checker knows path is valid here

def register_manager(self, obj: object) -> None:
    if is_manager_instance(obj, ExtractionManager):
        # Type checker knows obj is ExtractionManager here
        self._managers.append(obj)
```

## Testing and Verification

### After Each Change Session

```bash
# 1. Run type checker on modified files
python3 -m basedpyright core/modified_file.py

# 2. Run all core type checking (may take time)
timeout 30s python3 -m basedpyright core/

# 3. Check annotation progress
python3 -m ruff check --select ANN core/ | wc -l

# 4. Verify runtime behavior (run a simple test)
python3 -c "from core.async_rom_cache import ROMCacheWorker; print('Import successful')"
```

### Full Verification (End of Session)

```bash
# Complete type check (if time permits)
python3 -m basedpyright .

# Check all linting improvements
python3 -m ruff check --select UP,TCH,ANN core/ | wc -l

# Runtime verification
python3 -m pytest tests/test_minimal.py -v
```

## Progress Tracking

### Current Baselines (Starting Point)
- **Core ANN issues**: 920 (target: <500)
- **Core TCH issues**: 242 (target: <50) 
- **UI ANN issues**: 10,653 (future target: <5000)
- **Critical type errors**: 0 ✅

### Session Goals
- **15-minute session**: -50 to -100 ANN issues
- **30-minute session**: -100 to -200 ANN issues  
- **45-minute session**: -200 to -300 ANN issues

### Milestone Targets
1. **Core Module Complete**: <100 ANN issues remaining
2. **Modern Features Applied**: TypedDict, Literal, TypeGuard usage throughout
3. **Protocol Enhancement**: All manager protocols fully typed
4. **UI Migration Ready**: Core patterns established for UI application

## Common Patterns and Solutions

### Missing `__init__` Return Type
```python
# Ruff will suggest: ANN204 Missing return type annotation for special method `__init__`
def __init__(self, param: str) -> None:  # Add -> None
```

### Missing Parameter Types  
```python
# Ruff will suggest: ANN001 Missing type annotation for function argument
def process(self, data: bytes, count: int = 10) -> bool:  # Add types
```

### TYPE_CHECKING Imports
```python
# Ruff will suggest: TCH001 Move application import into a type-checking block
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.managers.extraction_manager import ExtractionManager
```

### Generic Type Parameters
```python
# Use modern syntax
from collections.abc import Sequence

def process_items[T](items: Sequence[T]) -> list[T]:  # Python 3.12+
    return list(items)

# Or for compatibility
T = TypeVar('T')
def process_items(items: Sequence[T]) -> list[T]:
    return list(items)
```

## Expected Outcomes by Phase

### After 1 Hour of Implementation
- **Core ANN issues**: 920 → ~700 (-25%)
- **Core TCH issues**: 242 → ~50 (-80%)
- **Enhanced protocols**: 3-5 TypedDict definitions added
- **Type guards**: Active usage in validation functions

### After 2 Hours of Implementation  
- **Core ANN issues**: 700 → ~400 (-60% total)
- **Manager protocols**: Fully typed with no `Any` usage
- **Modern features**: Literal types and TypeGuards throughout
- **Documentation**: Updated with type-safe examples

### After Full Core Migration (4-6 Hours)
- **Core ANN issues**: <100 (-90% total)
- **Basedpyright strict mode**: Ready for adoption
- **UI migration**: Patterns established and documented
- **Developer experience**: Full IDE type support

This guide provides a structured approach to systematically improve SpritePal's type safety while maintaining development momentum and code quality.