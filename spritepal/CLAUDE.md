# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Critical Patterns

### Widget Initialization Order
**ALWAYS** follow this order to avoid AttributeError bugs:

```python
def __init__(self):
    # 1. Declare ALL instance variables FIRST
    self.widget: QWidget | None = None
    self.data: list[str] = []
    
    # 2. Call super().__init__() second
    super().__init__()
    
    # 3. Setup methods last
    self._setup_ui()  # Now safe to assign self.widget = QWidget()
```

### Qt Boolean Evaluation Pitfall
Many Qt containers evaluate to `False` when empty. **Always use `is None` checks**:

```python
# ❌ BAD - fails for empty containers
if self._layout:
    self._layout.addWidget(widget)

# ✅ GOOD - works correctly
if self._layout is not None:
    self._layout.addWidget(widget)
```

Affected classes: QTabWidget, QVBoxLayout, QHBoxLayout, QListWidget, QTreeWidget, QStackedWidget, QSplitter

### Worker Thread Pattern
All workers must use the `@handle_worker_errors` decorator:

```python
class MyWorker(BaseWorker):
    # Standard signals
    progress = pyqtSignal(int)
    error = pyqtSignal(str, Exception)
    finished = pyqtSignal(object)
    
    @handle_worker_errors
    def run(self):
        # Decorator handles all exceptions
        result = self._do_work()
        self.finished.emit(result)
```

### Cross-Thread Signal Safety
**Never create GUI objects in worker threads**:

```python
# ❌ DANGER - creates GUI in worker thread
worker.data_ready.connect(lambda: QMessageBox.information(...))

# ✅ SAFE - GUI created in main thread
worker.data_ready.connect(self._show_message_in_main_thread)
```

### Error Handling
Use the exception hierarchy and centralized handler:

```python
from core.managers.exceptions import ValidationError
from ui.common.error_handler import get_error_handler

try:
    self._validate_params(params)
except ValidationError as e:
    self._error_handler.handle_error(e, "Validation Failed")
```

### Type Safety Patterns

#### Manager Type Casting
When accessing managers in workers, use explicit casting:

```python
from typing import cast
from core.managers.extraction_manager import ExtractionManager

# ✅ GOOD - explicit cast for type safety
manager = cast(ExtractionManager, self.manager)
result = manager.extract_sprites(params)

# ❌ BAD - type checker can't verify
result = self.manager.extract_sprites(params)
```

#### Process vs Popen Confusion
Be careful with subprocess types:

```python
import multiprocessing as mp
import subprocess

# ✅ CORRECT - Process for multiprocessing
self._processes: list[mp.Process] = []
process = mp.Process(target=worker_func)

# ❌ WRONG - Popen is for subprocess, not multiprocessing
self._processes: list[subprocess.Popen[bytes]] = []
```

#### Variable Initialization in Try Blocks
Always initialize variables before try blocks:

```python
# ✅ GOOD - variable initialized before try
tile_data = b""
rom_data = None
try:
    rom_data = load_rom()
    tile_data = extract_tiles(rom_data)
except Exception:
    pass
# tile_data and rom_data are always defined here

# ❌ BAD - possibly unbound variable
try:
    tile_data = extract_tiles()  # Might fail
except Exception:
    pass
# tile_data might be unbound here
```

#### Layout Attribute Naming
Avoid conflicting with Qt's built-in layout() method:

```python
# ✅ GOOD - no conflict with layout() method
class MyWidget(QWidget):
    def __init__(self):
        self._layout = QVBoxLayout()  # Private attribute
        super().__init__()
        
# ❌ BAD - conflicts with QWidget.layout()
class MyWidget(QWidget):
    def __init__(self):
        self.layout = QVBoxLayout()  # Shadows built-in method
```

#### Override Decorator Import
Use fallback for Python 3.10 compatibility:

```python
# ✅ GOOD - fallback for older Python
try:
    from typing import override
except ImportError:
    from typing_extensions import override

class MyClass(BaseClass):
    @override
    def method(self):
        pass
```

## Commands

### Setup
```bash
# Virtual environment (from exhal-master/)
python3 -m venv venv
source venv/bin/activate  # Linux/macOS
venv\Scripts\activate     # Windows

# Install dependencies
pip install PyQt6 Pillow pytest pytest-qt pytest-xvfb pytest-benchmark ruff basedpyright coverage typing-extensions

# Run SpritePal
python launch_spritepal.py
```

### Development
```bash
# Testing
pytest tests/ -x                    # Stop on first failure
pytest tests/ -m "unit"             # Unit tests only
pytest tests/ --cov=core --cov=ui   # With coverage

# Code quality (requires activated venv)
ruff check . --fix                  # Lint and fix (305 issues remaining, mostly style)
../venv/bin/basedpyright           # Type check (136 errors, down from 285)

# Type error analysis
python scripts/typecheck_analysis.py --critical
```

## Architecture

### Manager-Based Pattern
```
UI Layer (MainWindow, Dialogs, Panels)
    ↓
Controller (thin coordination)
    ↓
Manager Layer (business logic)
- ExtractionManager: VRAM/ROM extraction
- InjectionManager: VRAM/ROM injection  
- SessionManager: Settings/state
    ↓
Core Layer (algorithms)
- SpriteExtractor, ROMInjector, etc.
```

### Key Managers
- **ExtractionManager**: All extraction workflows, validation, preview generation
- **InjectionManager**: All injection operations with compression support
- **ManagerRegistry**: Singleton providing global manager access
- **WorkerManager**: Thread lifecycle and signal management

### Testing Infrastructure
- **MockFactory**: Centralized mock creation (`tests/infrastructure/mock_factory.py`)
- **Environment detection**: Auto-switches between real Qt and mocks
- **Performance tests**: Use `@pytest.mark.benchmark` 
- **GUI tests**: Use `@pytest.mark.gui` with qtbot

### File Structure
```
spritepal/
├── core/
│   ├── managers/        # Business logic
│   ├── workers/         # Thread workers
│   └── *.py            # Core algorithms
├── ui/
│   ├── common/         # Shared UI utilities
│   ├── dialogs/        # Dialog windows
│   └── *.py           # Main UI components
├── utils/              # Utilities (cache, settings)
└── tests/
    ├── infrastructure/ # Test framework
    └── test_*.py      # Test files
```

## Quick Reference

### Common Issues
- **Qt object is None**: Use `is not None` checks, not truthiness
- **Thread crash**: Ensure `@handle_worker_errors` on all workers
- **Signal not working**: Check thread affinity with `obj.thread()`
- **Type errors**: Run `../venv/bin/basedpyright` (136 errors remaining)
- **Manager type mismatch**: Use `cast(ExtractionManager, self.manager)`
- **Unbound variables**: Initialize before try blocks
- **Layout conflicts**: Use `self._layout` not `self.layout`

### Key Files
- `utils/constants.py`: All magic numbers as named constants
- `core/managers/exceptions.py`: Exception hierarchy
- `ui/common/error_handler.py`: Centralized error handling
- `ui/common/worker_manager.py`: Worker lifecycle management
- `tests/conftest.py`: Test configuration and fixtures
- `tests/infrastructure/mock_factory.py`: Centralized mock creation

### Performance
- ROM cache provides 225x-2400x speedup (see `utils/rom_cache.py`)
- Use `pytest-benchmark` for performance testing
- Profile before optimizing with cProfile/memory_profiler

### Code Quality Status (as of 2025-08-05)
- **Linting (ruff)**: 305 issues (down from 797, 61.7% reduction)
  - 66 PLC0415 (delayed imports) - architecturally necessary
  - 108 PTH violations - pathlib opportunities
  - 48 complexity issues - refactoring candidates
- **Type Checking (basedpyright)**: 136 errors (down from 285, 52% reduction)
  - Remaining issues mostly non-critical (logger params, complex type expressions)
  - All critical runtime safety issues resolved
- **Tests**: Comprehensive test suite with mock infrastructure

### Best Practices
1. Always use virtual environment
2. Follow signal naming conventions (past tense for events)
3. Use MockFactory for consistent test mocks
4. Handle errors at appropriate layers
5. Type hint all new code (Python 3.10+ syntax)
6. Initialize variables before try blocks to avoid unbound errors
7. Use explicit type casting for manager access in workers
8. Avoid shadowing Qt built-in methods (layout, parent, etc.)