# SpritePal Development Guidelines

## Quick Reference

- **Qt Framework**: PySide6 (not PyQt6)
- **Python Version**: 3.11+
- **Package Manager**: uv
- **Config Source of Truth**: `pyproject.toml` (ruff, basedpyright, pytest all configured there)

## Documentation Structure

```
spritepal/
├── CLAUDE.md                           # This file - development guidelines
├── README.md                           # Project overview
├── docs/
│   ├── architecture.md                 # Layer structure and import rules
│   ├── REAL_COMPONENT_TESTING_GUIDE.md # Real component testing patterns
│   ├── QT_TESTING_BEST_PRACTICES.md    # pytest-qt patterns
│   ├── dialog_development_guide.md     # Dialog creation patterns
│   └── archive/                        # Historical documentation
├── tests/
│   ├── README.md                       # Test suite overview
│   └── HEADLESS_TESTING.md             # Headless/CI testing
├── TESTING_DEBUG_GUIDE_DO_NOT_DELETE.md    # Critical debug strategies
├── UNIFIED_TESTING_GUIDE_DO_NOT_DELETE.md  # Testing single source of truth
└── SPRITE_LEARNINGS_DO_NOT_DELETE.md       # Sprite extraction knowledge
```

## Development Tools

All tools are run via `uv` from the project root (`exhal-master/`):

```bash
# Sync dependencies
uv sync --extra dev

# Linting
uv run ruff check spritepal
uv run ruff check spritepal --fix

# Type checking (on core modules only)
uv run basedpyright spritepal/core spritepal/ui spritepal/utils

# Tests
uv run pytest spritepal/tests -v
uv run pytest -m "headless and not slow"  # Fast tests
uv run pytest -m "gui" --xvfb              # GUI tests
```

## Qt Testing Best Practices

### Real Component Testing (Preferred)

SpritePal uses real components over mocks. Target mock density: **0.032 or lower**.

```python
from tests.infrastructure.real_component_factory import RealComponentFactory

def test_extraction_workflow():
    with RealComponentFactory() as factory:
        manager = factory.create_extraction_manager(with_test_data=True)
        result = manager.validate_extraction_params(params)
        assert isinstance(result, bool)  # Real behavior
```

### Critical Crash Prevention

**Never inherit from QDialog in mocks** - causes metaclass conflicts:
```python
from PySide6.QtCore import QObject, Signal

# CORRECT
class MockDialog(QObject):
    accepted = Signal()
    rejected = Signal()

# INCORRECT - Causes fatal crashes
class MockDialog(QDialog):  # Don't do this!
    pass
```

**Mock at import location, not definition**:
```python
@patch('ui.rom_extraction_panel.UnifiedManualOffsetDialog')  # Correct
```

### Signal Testing
```python
def test_async_operation(qtbot):
    with qtbot.waitSignal(worker.finished, timeout=5000) as blocker:
        blocker.connect(worker.failed)
        worker.start()
    assert blocker.signal_triggered
```

### Test Markers
- `@pytest.mark.gui` - Real Qt tests (requires display/xvfb)
- `@pytest.mark.headless` - Mock/unit tests (fast, always work)
- `@pytest.mark.serial` - No parallel execution

## Project Architecture

```
spritepal/
├── core/              # Business logic (managers, extractors)
├── ui/                # Qt UI components
│   ├── components/    # Reusable widgets
│   ├── dialogs/       # Dialog windows
│   ├── panels/        # Panel widgets
│   └── windows/       # Main/detached windows
├── tests/
│   ├── infrastructure/  # RealComponentFactory, test contexts
│   └── examples/        # Pattern examples
└── utils/             # Shared utilities
```

### Import Rules (see docs/architecture.md)
- **UI** imports from: core/, managers/, utils/
- **Managers** import from: core/, utils/
- **Core** imports from: utils/
- **Utils** imports from: Python stdlib only

### Circular Import Resolution
```python
def open_detached_gallery(self):
    # Local import to avoid circular dependency
    from ui.windows.detached_gallery_window import DetachedGalleryWindow
    self.detached_window = DetachedGalleryWindow(self)
```

## Key Patterns

### Resource Management
Always use context managers for file/mmap resources:
```python
@contextmanager
def _rom_context(self):
    rom_file = None
    rom_mmap = None
    try:
        rom_file = Path(self.rom_path).open('rb')
        rom_mmap = mmap.mmap(rom_file.fileno(), 0, access=mmap.ACCESS_READ)
        yield rom_mmap
    finally:
        with suppress(Exception):
            if rom_mmap: rom_mmap.close()
        with suppress(Exception):
            if rom_file: rom_file.close()
```

### Thread Safety
- Use `QMutex/QMutexLocker` for shared state
- Use `QThread.currentThread().msleep()` not `QThread.msleep()`
- Test with `qtbot.waitSignal()` for async operations

### Dialog Initialization (DialogBase pattern)
```python
class MyDialog(DialogBase):
    def __init__(self, parent: QWidget | None = None):
        # Step 1: Declare ALL instance variables BEFORE super().__init__
        self.my_widget: QWidget | None = None

        # Step 2: Call super().__init__() - this calls _setup_ui()
        super().__init__(parent)

    def _setup_ui(self):
        # Step 3: Create widgets
        self.my_widget = QPushButton("Click me")
```

## Mesen2/Sprite Finding (Active Work)

Current focus: Finding and extracting SNES sprites using Mesen2 emulator.

Key documentation:
- `NEXT_STEPS_PLAN.md` - Current sprite finding strategy
- `MESEN2_LUA_API_LEARNINGS_DO_NOT_DELETE.md` - Lua scripting knowledge
- `SPRITE_LEARNINGS_DO_NOT_DELETE.md` - ROM extraction patterns

## Historical Documentation

Completed phase reports and one-time fix summaries are archived in:
`docs/archive/` (phase_reports/, migration_reports/, fix_summaries/, analysis_docs/)

---

*Last updated: December 2025*
