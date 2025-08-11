# Qt Signal/Slot Integration Tests

## Overview

Comprehensive integration tests for Qt signal/slot connections in SpritePal, focusing on the critical communication between `UnifiedManualOffsetDialog` and `ROMExtractionPanel`.

## Test Files Created

### 1. `/tests/integration/test_qt_signal_slot_integration.py`
**Purpose**: Test core signal/slot connections between dialog and panel

**Key Test Classes**:
- `TestDialogSignalConnections`: Verifies dialog signals exist and emit correctly
- `TestPanelSignalReception`: Tests panel properly receives and handles signals
- `TestSignalConnectionLifecycle`: Ensures no duplicate connections and proper cleanup
- `TestCrossWidgetCoordination`: Tests multi-widget signal coordination
- `TestThreadSafetyAndTiming`: Validates thread safety and timing
- `TestSignalBlockingAndError`: Tests error conditions and signal blocking

**Critical Tests**:
- Dialog emits `offset_changed(int)` when offset changes
- Dialog emits `sprite_found(int, str)` when sprite is selected
- Panel receives signals and updates state correctly
- Multiple rapid emissions are handled in order
- Signals work after dialog hide/show cycles
- No duplicate connections when dialog opened multiple times

### 2. `/tests/integration/test_qt_threading_signals.py`
**Purpose**: Advanced threading and cross-thread signal testing

**Key Test Classes**:
- `TestCrossThreadSignals`: QueuedConnection vs DirectConnection behavior
- `TestSignalParameterMarshalling`: Parameter type safety across threads
- `TestThreadAffinity`: Qt object thread affinity rules
- `TestSignalSynchronization`: QWaitCondition and QEventLoop patterns
- `TestDeadlockPrevention`: Patterns to prevent deadlocks
- `TestHighConcurrency`: Multiple threads signaling to single receiver

**Threading Patterns Tested**:
- Worker thread emitting to main thread (QueuedConnection)
- DirectConnection for same-thread performance
- BlockingQueuedConnection behavior and risks
- Signal emission outside mutex locks
- Thread-safe counter with proper locking
- Signal storm handling (1000+ rapid emissions)

### 3. `/tests/integration/test_dialog_singleton_signals.py`
**Purpose**: Test singleton pattern impact on signals

**Key Test Classes**:
- `TestSingletonBehavior`: Singleton returns same instance
- `TestSingletonSignalConnections`: Signal connections through singleton
- `TestSingletonLifecycle`: Dialog survives panel deletion
- `TestSingletonSignalIntegrity`: Signals intact through lifecycle

**Singleton-Specific Tests**:
- Thread-safe singleton access from multiple threads
- Single connection despite multiple panel access
- Each panel's handlers properly connected
- Signals work after singleton reset
- Rapid hide/show maintains signal integrity

### 4. `/tests/integration/test_signal_basics.py`
**Purpose**: Basic signal/slot tests that run in headless environments

**Key Test Classes**:
- `TestBasicSignalSlot`: Core signal/slot functionality
- `TestDialogSignalPatterns`: Dialog-specific patterns
- `TestSignalThreadSafety`: Basic thread safety

**Headless-Compatible Tests**:
- Signal emission and reception
- Multiple connections to same signal
- Disconnection behavior
- Qt.UniqueConnection prevents duplicates
- Parameter type marshalling
- Singleton pattern simulation
- Deferred connection pattern

## Signal Architecture Validated

### Core Signals
```python
class UnifiedManualOffsetDialog(DialogBase):
    offset_changed = Signal(int)      # Emitted when offset changes
    sprite_found = Signal(int, str)   # Emitted when sprite is found
```

### Panel Signal Handlers
```python
class ROMExtractionPanel:
    def _on_dialog_offset_changed(self, offset: int):
        """Update panel state when offset changes"""
        self._manual_offset = offset
        self.manual_offset_status.setText(f"Current offset: 0x{offset:06X}")
    
    def _on_dialog_sprite_found(self, offset: int, sprite_name: str):
        """Handle sprite selection"""
        self._manual_offset = offset
        self.manual_offset_status.setText(f"Selected sprite at 0x{offset:06X}")
```

## Thread Safety Patterns

### Safe Signal Emission
```python
# Emit signal OUTSIDE mutex lock to prevent deadlock
self._mutex.lock()
self._value += 1
new_value = self._value
self._mutex.unlock()
self.value_changed.emit(new_value)  # Outside lock
```

### Cross-Thread Signals
```python
# Automatic QueuedConnection for cross-thread
worker.moveToThread(thread)
worker.progress.connect(handler)  # Auto-queued
```

### Thread Affinity Rules
- Parent and child QObjects must be in same thread
- Create QObjects AFTER moveToThread()
- Cannot move object with parent to another thread

## Connection Types Tested

1. **Qt.AutoConnection** (default)
   - DirectConnection if same thread
   - QueuedConnection if different threads

2. **Qt.DirectConnection**
   - Slot invoked immediately in signaling thread
   - Use only when guaranteed same thread

3. **Qt.QueuedConnection**
   - Slot invoked when control returns to receiver's event loop
   - Safe for cross-thread communication

4. **Qt.BlockingQueuedConnection**
   - Like QueuedConnection but blocks until slot returns
   - Risk of deadlock - use carefully

5. **Qt.UniqueConnection**
   - Prevents duplicate connections
   - Can be combined with other types

## Test Execution

### Run All Signal Tests
```bash
./run_signal_integration_tests.sh
```

### Run Specific Test Files
```bash
# Basic tests (headless-compatible)
pytest tests/integration/test_signal_basics.py -v

# GUI tests with xvfb
xvfb-run -a pytest tests/integration/test_qt_signal_slot_integration.py -v

# Threading tests
pytest tests/integration/test_qt_threading_signals.py -v

# Singleton tests
pytest tests/integration/test_dialog_singleton_signals.py -v
```

## Key Findings

### Verified Working
- ✅ Signal emission and reception across threads
- ✅ Parameter marshalling for all Qt types
- ✅ Singleton pattern maintains single instance
- ✅ Signals survive dialog hide/show cycles
- ✅ No duplicate connections with proper patterns
- ✅ Thread-safe signal emission with proper locking

### Best Practices Enforced
- Always emit signals outside mutex locks
- Use @Slot decorators with type hints
- Let Qt.AutoConnection handle thread detection
- Create QObjects after moveToThread()
- Use Qt.UniqueConnection to prevent duplicates
- Clean up connections when objects deleted

## Coverage Statistics

- **Signal Types**: 15+ different signal signatures tested
- **Connection Types**: All 5 Qt connection types validated
- **Thread Scenarios**: 10+ threading patterns tested
- **Error Cases**: 8+ error conditions handled
- **Concurrency**: Up to 1000 concurrent signal emissions

## Integration Points

These tests validate the critical signal/slot connections between:
- `UnifiedManualOffsetDialog` ↔ `ROMExtractionPanel`
- Worker threads ↔ Main GUI thread
- Multiple panels ↔ Singleton dialog
- Preview coordinator ↔ UI components

## Future Enhancements

1. **Performance Benchmarking**
   - Signal emission overhead measurement
   - Connection type performance comparison
   - Thread pool optimization testing

2. **Memory Leak Detection**
   - Signal connection leak testing
   - Deleted object reference detection
   - Circular reference prevention

3. **Complex Scenarios**
   - Nested signal emissions
   - Signal forwarding chains
   - Dynamic connection management