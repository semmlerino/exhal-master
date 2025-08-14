# Mocking Replacement Recommendations

Based on analysis of the SpritePal test suite (2549 mock occurrences across 164 files), here are prioritized recommendations for replacing mocking with better testing approaches:

## High Priority Replacements

### 1. Qt Widget Mocking → Real Widgets with qtbot (HIGH IMPACT)
**Current Issue**: MockQWidget, MockQDialog, MockQLabel etc. in `tests/infrastructure/qt_mocks.py`
**Better Approach**: Use real Qt widgets with pytest-qt's qtbot fixture

```python
# BEFORE - Mock approach
from tests.infrastructure.qt_mocks import MockQDialog
dialog = MockQDialog()  # Fake dialog, doesn't test real Qt behavior

# AFTER - Real Qt with qtbot
def test_dialog_behavior(qtbot):
    from ui.dialogs.my_dialog import MyDialog
    dialog = MyDialog()
    qtbot.addWidget(dialog)  # Proper cleanup
    qtbot.mouseClick(dialog.ok_button, Qt.LeftButton)
    assert dialog.result() == QDialog.Accepted
```

**Benefits**:
- Tests actual Qt signal/slot behavior
- Catches real layout and painting issues
- qtbot provides proper cleanup and event loop handling

### 2. File I/O Mocking → Temp Files (MEDIUM IMPACT)
**Current Pattern**: Extensive use of `@patch('builtins.open')` and mock file operations
**Better Approach**: Use tempfile and actual file operations

```python
# BEFORE - Mock file I/O
with patch('builtins.open', mock_open(read_data=b'data')):
    result = process_file('/fake/path')

# AFTER - Real temp files
import tempfile
with tempfile.NamedTemporaryFile(suffix='.rom') as tmp:
    tmp.write(b'data')
    tmp.flush()
    result = process_file(tmp.name)
```

**Benefits**:
- Tests real file permissions and edge cases
- Catches actual I/O errors
- More realistic testing

### 3. HAL Compression Mocking → Test Mode (HIGH IMPACT)
**Current**: MockHALProcessPool, MockHALCompressor in `tests/infrastructure/mock_hal.py`
**Better Approach**: Use HAL compression in test mode with small test data

```python
# BEFORE - Mock HAL
from tests.infrastructure.mock_hal import MockHALCompressor
compressor = MockHALCompressor()
result = compressor.decompress(data)  # Returns fake data

# AFTER - Real HAL with test data
from core.hal_compression import HALCompressor
compressor = HALCompressor(test_mode=True)
# Use small, known test sprites
test_data = TestDataRepository().get_test_sprite_data('small')
result = compressor.decompress(test_data)
```

**Benefits**:
- Tests actual compression/decompression logic
- Catches format compatibility issues
- Still fast with small test data

## Medium Priority Replacements

### 4. Worker Thread Mocking → Real Workers with Signals
**Current**: Mocking QThread and worker signals
**Better**: Use real workers with qtbot.waitSignal()

```python
# BEFORE - Mock worker
worker = MagicMock()
worker.finished = MagicMock()
worker.progress = MagicMock()

# AFTER - Real worker with signal testing
def test_worker(qtbot):
    worker = RealWorker()
    with qtbot.waitSignal(worker.finished, timeout=1000) as blocker:
        worker.start()
    assert blocker.args[0] == expected_result
```

### 5. Signal/Slot Mocking → Real Qt Signals
**Current**: Using Mock() for signals
**Better**: Use real Qt signals with spy

```python
# BEFORE
mock_signal = Mock()
mock_signal.emit(data)
mock_signal.assert_called_with(data)

# AFTER
from PySide6.QtCore import QObject, Signal
class Emitter(QObject):
    signal = Signal(object)

def test_signal(qtbot):
    emitter = Emitter()
    with qtbot.waitSignal(emitter.signal) as blocker:
        emitter.signal.emit(data)
    assert blocker.args[0] == data
```

## Low Priority (Keep as Mocks)

### Items That Should Remain Mocked:
1. **External APIs** - Network calls, third-party services
2. **System-level operations** - Process spawning for tools
3. **Performance-critical paths** - Where real operations would be too slow
4. **Error simulation** - Testing error handling paths

## Migration Strategy

### Phase 1: High Impact Qt Widgets (Weeks 1-2)
- Replace MockQWidget usage in integration tests
- Update tests to use qtbot fixture
- Verify no test coverage loss

### Phase 2: File I/O (Week 3)
- Replace file mocking with tempfile usage
- Create helper fixtures for common file scenarios
- Update CI to handle temp file cleanup

### Phase 3: HAL Compression (Week 4)
- Implement test mode in HAL compression
- Create small test data sets
- Migrate tests gradually

## Existing Progress

Already migrated:
- ✅ MockFactory → RealComponentFactory (COMPLETED)
- ✅ Many integration tests now use real Qt components
- ✅ TestDataRepository provides consistent test data

## Statistics to Track

Current state:
- 2549 mock occurrences across 164 files
- ~30% could be replaced with real components
- ~40% should remain as mocks (external deps, error cases)
- ~30% are already using hybrid approach

## Expected Benefits

1. **Better bug detection**: Real components catch issues mocks miss
2. **Improved confidence**: Tests verify actual behavior, not mocked behavior  
3. **Easier debugging**: Real stack traces and Qt events
4. **Better integration testing**: Components interact as in production
5. **Type safety**: Real components provide proper type checking

## Tools and Helpers Needed

1. **Fixture factory improvements**:
   ```python
   @pytest.fixture
   def qt_app_with_cleanup(qtbot):
       """Provide QApplication with proper cleanup"""
       app = QApplication.instance() or QApplication([])
       yield app
       # Cleanup handled by qtbot
   ```

2. **Temp file helpers**:
   ```python
   @pytest.fixture
   def temp_rom_file():
       """Create temp ROM file with test data"""
       with tempfile.NamedTemporaryFile(suffix='.sfc') as f:
           f.write(TEST_ROM_DATA)
           f.flush()
           yield f.name
   ```

3. **Signal testing utilities**:
   ```python
   def assert_signal_emitted(qtbot, signal, expected_args):
       """Helper for signal assertions"""
       with qtbot.waitSignal(signal, timeout=1000) as blocker:
           # trigger action
           pass
       assert blocker.args == expected_args
   ```

## Next Steps

1. Review and prioritize specific test files for migration
2. Create migration helper scripts
3. Update testing documentation
4. Train team on real component testing patterns
5. Set up metrics to track migration progress

---

*Note: This migration should be done gradually to avoid disrupting development. Focus on high-value tests first and maintain backward compatibility during transition.*