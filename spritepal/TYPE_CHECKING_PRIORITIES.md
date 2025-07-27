# Type Checking Error Priority List

## Summary
- **Total Errors**: 1,630 errors
- **Total Warnings**: 35,130 warnings
- **Critical Issues**: ~50 high-impact errors that break functionality

## Priority 1: Critical Errors (Breaking Issues)

### 1.1 Import Cycles (2 cycles)
**Impact**: Prevents module loading, breaks application startup
- `core/controller.py` ↔ `ui/main_window.py`
- `core/managers/__init__.py` (self-referential cycle)

### 1.2 QThread Signal Conflicts (5 instances)
**Impact**: Runtime errors, signal handling failures
- `core/controller.py:49` - ExtractorWorker.finished
- `core/controller.py:531` - ROMExtractorWorker.finished  
- `core/injector.py:263` - InjectorWorker.finished
- `core/rom_injector.py:658` - ROMInjectorWorker.finished

### 1.3 Missing Critical Methods (2 methods)
**Impact**: AttributeError at runtime
- `core/controller.py:248` - PreviewPanel.clear_preview()
- `core/controller.py:411` - PreviewPanel.get_tile_info()

### 1.4 Missing Attributes (3 instances)
**Impact**: AttributeError during extraction
- `core/managers/extraction_manager.py:419,422,425` - ExtractionManager._extractor

## Priority 2: Type Safety Issues

### 2.1 Return Type Mismatches
- `extraction_manager.py:483` - Returns ROMHeader instead of dict[str, Any]
- `injection_manager.py:203` - Returns bool|None instead of bool

### 2.2 Method Parameter Issues
- `extraction_manager.py:192` - QImage constructor wrong parameters
- `injection_manager.py:211,216,218` - Accessing non-existent QThread attributes

### 2.3 Abstract Class Issues
- `base_manager.py:21` - BaseManager not properly abstract
- `base_manager.py:17` - Cannot create consistent method ordering

## Priority 3: Import and Dependency Issues

### 3.1 Missing Optional Dependencies
- `sprite_visual_validator.py:13` - cv2 import (opencv)
- `find_real_sprites.py:10` - cv2 import

### 3.2 Relative Import Issues (7 files)
- Test files using relative imports that break when run as modules
- Development scripts with improper imports

## Priority 4: Type Annotation Issues

### 4.1 Missing Type Arguments
- Generic types without parameters (list, tuple, dict)
- ~10 instances in various files

### 4.2 Unknown Types
- External library types (PIL, numpy)
- PyQt6 signal types

## Recommended Fix Order

1. **Fix import cycles first** - These prevent the app from starting
2. **Fix QThread signal conflicts** - Use different signal names
3. **Add missing methods** - Implement or remove calls
4. **Fix missing attributes** - Ensure proper initialization
5. **Fix return type mismatches** - Update type hints or implementations
6. **Handle optional dependencies** - Add try/except for cv2
7. **Fix remaining type issues** - Lower priority, non-breaking

## Quick Wins
- Rename QThread signals to avoid conflicts (e.g., `finished` → `extraction_finished`)
- Add missing methods as stubs with proper types
- Break import cycles by moving shared types to separate modules
- Add `TYPE_CHECKING` guards for circular type imports