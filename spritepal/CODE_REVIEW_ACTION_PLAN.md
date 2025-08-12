# SpritePal Code Review Action Plan

## Executive Summary
Comprehensive code review identified 734 type errors, 623 linting violations, critical thread safety issues, and complete accessibility failure. This plan prioritizes fixes by severity and impact.

## 🔴 Critical Issues - Week 1 (Prevent Crashes & Errors)

### 1. Thread Safety Violations
**Impact**: Application crashes, data corruption  
**Effort**: 2-3 days  
**Files**: `ui/workers/batch_thumbnail_worker.py`, all worker classes

#### Actions:
```python
# Fix 1: Add mutex protection to cache access
from PySide6.QtCore import QMutex, QMutexLocker

class BatchThumbnailWorker(QObject):  # Changed from QThread
    def __init__(self):
        super().__init__()
        self._cache_mutex = QMutex()
        self._cache = {}
    
    def get_cached_thumbnail(self, offset: int) -> Optional[QImage]:
        with QMutexLocker(self._cache_mutex):
            return self._cache.get(offset)

# Fix 2: Use moveToThread pattern
worker = BatchThumbnailWorker()
thread = QThread()
worker.moveToThread(thread)
thread.started.connect(worker.run)
worker.finished.connect(thread.quit)
worker.finished.connect(worker.deleteLater)
thread.finished.connect(thread.deleteLater)
thread.start()

# Fix 3: Verify thread before UI updates
def safe_ui_update(func):
    def wrapper(self, *args, **kwargs):
        if QThread.currentThread() != QApplication.instance().thread():
            QMetaObject.invokeMethod(
                self, func.__name__, 
                Qt.ConnectionType.QueuedConnection,
                *args, **kwargs
            )
            return
        return func(self, *args, **kwargs)
    return wrapper
```

### 2. Type Safety Failures  
**Impact**: Runtime AttributeErrors, crashes  
**Effort**: 2-3 days  
**Files**: `core/controller.py`, `core/hal_compression.py`, protocol implementations

#### Actions:
```python
# Fix 1: Add None checks for optional members
# Before (crashes):
gallery_tab.set_sprites(sprites)

# After (safe):
if gallery_tab is not None:
    gallery_tab.set_sprites(sprites)

# Fix 2: Fix protocol conformance
from PySide6.QtWidgets import QWidget

@runtime_checkable
class MainWindowProtocol(QWidget, Protocol):  # Add QWidget base
    """Protocol for main window functionality."""
    extract_requested: Signal
    
    def as_qwidget(self) -> QWidget:
        """Bridge method for Qt compatibility."""
        return self

# Fix 3: Replace Any with specific types
# Before:
def process_data(data: Any) -> Any:

# After:
T = TypeVar('T')
def process_data(data: T) -> T:
```

### 3. Accessibility Non-Compliance
**Impact**: Application unusable for keyboard/screen reader users  
**Effort**: 3-4 days  
**Files**: All UI components, especially dialogs

#### Actions:
```python
# Fix 1: Add keyboard navigation
size_label = QLabel("&Size:")  # Add mnemonic
size_label.setBuddy(self.size_slider)  # Link to control
size_label.setAccessibleDescription("Adjusts thumbnail size from 128 to 768 pixels")
self.size_slider.setAccessibleName("Thumbnail Size Slider")

# Fix 2: Add standard shortcuts
self.scan_action = QAction("&Scan for Sprites", self)
self.scan_action.setShortcut("Ctrl+Shift+S")
self.scan_action.setToolTip("Scan ROM for sprite data (Ctrl+Shift+S)")

# Fix 3: Implement focus indicators
self.setStyleSheet("""
    QWidget:focus {
        border: 2px solid #0078d4;
        outline: none;
    }
""")

# Fix 4: Tab order management
self.setTabOrder(self.rom_input, self.offset_input)
self.setTabOrder(self.offset_input, self.scan_button)
```

## 🟠 High Priority - Week 2 (Performance & Stability)

### 4. Configuration Cleanup
**Effort**: 1 day
```bash
# Consolidate configurations
rm ruff.toml  # Remove duplicate
# Update pyproject.toml with consolidated settings

# Fix imports
source ../venv/bin/activate
python3 -m ruff check . --fix  # Auto-fix 41 issues
python3 -m ruff check --select PLC0415 --fix  # Fix import-outside-top-level
```

### 5. Performance Optimizations
**Effort**: 3-4 days

#### Tile Rendering (5-10x speedup):
```python
import numpy as np

def render_tiles_vectorized(self, tile_data: bytes, width_tiles: int, height_tiles: int) -> Image:
    """Vectorized tile rendering using NumPy."""
    # Pre-allocate output array
    image_array = np.zeros((height_tiles * 8, width_tiles * 8, 4), dtype=np.uint8)
    
    # Process tiles in batches using NumPy operations
    # See full implementation in performance review
    
    return Image.fromarray(image_array, 'RGBA')
```

#### Memory Management (50-90% reduction):
```python
import mmap

class BatchThumbnailWorker:
    def _load_rom_data(self):
        """Memory-map ROM file instead of loading into RAM."""
        self._rom_file = open(self.rom_path, 'rb')
        self._rom_mmap = mmap.mmap(self._rom_file.fileno(), 0, access=mmap.ACCESS_READ)
    
    def _read_rom_chunk(self, offset: int, size: int) -> bytes:
        """Read efficiently from memory-mapped file."""
        return self._rom_mmap[offset:offset + size]
```

## 🟡 Medium Priority - Week 3 (Quality & Maintenance)

### 6. Automated Fixes
```bash
# Run comprehensive automated fixes
python3 -m ruff check . --fix --unsafe-fixes
python3 -m basedpyright . --createstub PySide6  # Generate stubs
```

### 7. Test Coverage Improvements
```python
# Add error scenario testing
@pytest.mark.parametrize("error_type", [
    "disk_full", "permission_denied", "corrupted_data"
])
def test_error_resilience(error_type, error_injector):
    error_injector.inject(error_type)
    # Test graceful handling

# Add property-based testing
from hypothesis import given, strategies as st

@given(st.binary(min_size=1024, max_size=0x400000))
def test_sprite_finder_robustness(rom_data):
    # Test with random data
```

## Testing Requirements

### Thread Safety Testing:
```python
# Add to all worker tests
def test_thread_safety_with_concurrent_access():
    worker = BatchThumbnailWorker()
    
    # Launch multiple threads accessing cache
    import concurrent.futures
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(worker.get_cached_thumbnail, i) for i in range(100)]
        results = [f.result() for f in futures]
    
    # Should not crash or corrupt data
```

### Accessibility Testing:
```bash
# Manual testing checklist
1. Navigate entire app with Tab/Shift+Tab only
2. Test all functionality with keyboard only
3. Run with screen reader (NVDA/JAWS)
4. Test at 150% and 200% display scaling
5. Verify focus indicators visible
```

## Success Metrics

### Week 1 Targets:
- [ ] Zero crashes from thread safety issues
- [ ] Type errors < 100 (from 734)
- [ ] Basic keyboard navigation working
- [ ] All critical None-check issues fixed

### Week 2 Targets:
- [ ] Tile rendering 5x faster
- [ ] Memory usage reduced by 50%
- [ ] Linting violations < 200 (from 623)
- [ ] Configuration consolidated

### Week 3 Targets:
- [ ] Full WCAG 2.1 AA compliance
- [ ] Test coverage > 80%
- [ ] All automated fixes applied
- [ ] Performance benchmarks established

## Implementation Order

1. **Day 1-2**: Thread safety fixes (prevent crashes)
2. **Day 3-4**: Type safety critical fixes (prevent errors)
3. **Day 5-7**: Basic accessibility (keyboard nav, shortcuts)
4. **Week 2**: Performance optimizations and config cleanup
5. **Week 3**: Test improvements and remaining fixes

## Verification Commands

```bash
# After each phase, verify improvements:
source ../venv/bin/activate

# Check type safety
python3 -m basedpyright . --stats

# Check linting
python3 -m ruff check . --statistics

# Run tests
python3 -m pytest tests/ -x --tb=short

# Memory profiling
python3 -m memory_profiler launch_spritepal.py

# Performance profiling  
python3 -m cProfile -o profile.stats launch_spritepal.py
python3 -m pstats profile.stats
```

## Notes

- Fix critical thread safety FIRST to prevent production crashes
- Each fix should include tests to prevent regression
- Consider feature freeze during Week 1 critical fixes
- Document patterns in CLAUDE.md as they're established
- Set up CI/CD checks for type safety and linting

This plan addresses the most severe issues first while establishing patterns and infrastructure for long-term code quality improvement.