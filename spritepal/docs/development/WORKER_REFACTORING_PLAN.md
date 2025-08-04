# Worker/Thread Architecture Refactoring Plan

## Executive Summary
Refactor the Worker/Thread architecture in SpritePal to establish a consistent, type-safe, and maintainable async operation framework. This addresses 539 type errors and architectural inconsistencies across 12+ worker classes.

## Current State Analysis

### Problems Identified
1. **No Common Base Class**
   - Each worker defines its own signals
   - No interface contract
   - Managers use `hasattr()` to check for signals

2. **Scattered Organization**
   - Workers in `core/` (3 classes)
   - Workers in `ui/rom_extraction/workers/` (4 classes)
   - Test workers inline (4+ classes)
   - No clear organizational principle

3. **Business Logic Mixing**
   - Some workers delegate to managers (ExtractionWorker)
   - Others contain business logic (InjectionWorker, SpriteScanWorker)
   - Unclear separation of concerns

4. **Type Safety Issues**
   - 539 type errors in codebase
   - QThread signal/method conflicts
   - Missing `@override` decorators
   - Incorrect signal attribute access

5. **Inconsistent Patterns**
   - No standard progress reporting
   - No unified error handling
   - No cancellation mechanism
   - Different signal naming conventions

## Proposed Architecture

### Phase 1: Create Base Worker Classes (Week 1)

#### 1.1 Create `core/workers/base.py`
```python
from abc import ABC, abstractmethod
from typing import Any, Optional
from PyQt6.QtCore import QThread, pyqtSignal, QObject

class BaseWorker(QThread):
    """Base class for all worker threads with standard signals"""
    
    # Standard signals all workers must have
    progress = pyqtSignal(int, str)  # percent (0-100), message
    error = pyqtSignal(str, Exception)  # message, exception
    warning = pyqtSignal(str)  # warning message
    
    # Standard finished signal (override QThread.finished)
    operation_finished = pyqtSignal(bool, str)  # success, message
    
    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        self._is_cancelled = False
        self._is_paused = False
    
    def cancel(self) -> None:
        """Request cancellation of the operation"""
        self._is_cancelled = True
    
    def pause(self) -> None:
        """Request pause of the operation"""
        self._is_paused = True
    
    def resume(self) -> None:
        """Resume paused operation"""
        self._is_paused = False
    
    @property
    def is_cancelled(self) -> bool:
        return self._is_cancelled
    
    @property
    def is_paused(self) -> bool:
        return self._is_paused
    
    def emit_progress(self, percent: int, message: str = "") -> None:
        """Emit progress in a standard format"""
        self.progress.emit(max(0, min(100, percent)), message)
    
    def emit_error(self, message: str, exception: Optional[Exception] = None) -> None:
        """Emit error in a standard format"""
        self.error.emit(message, exception or Exception(message))
    
    @abstractmethod
    def run(self) -> None:
        """Subclasses must implement the actual work"""
        pass
```

#### 1.2 Create `core/workers/managed_worker.py`
```python
class ManagedWorker(BaseWorker):
    """Worker that delegates to a manager for business logic"""
    
    def __init__(self, manager: BaseManager, parent: Optional[QObject] = None):
        super().__init__(parent)
        self.manager = manager
        self._connections: list[QMetaObject.Connection] = []
    
    def connect_manager_signals(self) -> None:
        """Connect manager signals to worker signals"""
        # To be implemented by subclasses
        pass
    
    def disconnect_manager_signals(self) -> None:
        """Disconnect all manager signals"""
        for connection in self._connections:
            QObject.disconnect(connection)
        self._connections.clear()
    
    @override
    def run(self) -> None:
        """Template method for managed operations"""
        try:
            self.connect_manager_signals()
            self.perform_operation()
        except Exception as e:
            self.emit_error(str(e), e)
            self.operation_finished.emit(False, str(e))
        finally:
            self.disconnect_manager_signals()
    
    @abstractmethod
    def perform_operation(self) -> None:
        """Subclasses implement the manager delegation"""
        pass
```

#### 1.3 Create Specialized Base Classes
```python
class ExtractionWorkerBase(ManagedWorker):
    """Base for extraction workers with extraction-specific signals"""
    preview_ready = pyqtSignal(object, int)  # image, tile_count
    palettes_ready = pyqtSignal(dict)  # palette data
    
class InjectionWorkerBase(ManagedWorker):
    """Base for injection workers with injection-specific signals"""
    compression_info = pyqtSignal(dict)  # compression stats
    
class ScanWorkerBase(BaseWorker):
    """Base for scanning workers with scan-specific signals"""
    item_found = pyqtSignal(dict)  # found item info
    scan_stats = pyqtSignal(dict)  # scan statistics
```

### Phase 2: Migrate Existing Workers (Week 2-3)

#### 2.1 Create Migration Map
- `ExtractionWorker` → `VRAMExtractionWorker(ExtractionWorkerBase)`
- `ROMExtractionWorker` → `ROMExtractionWorker(ExtractionWorkerBase)`
- `InjectionWorker` → `VRAMInjectionWorker(InjectionWorkerBase)`
- `ROMInjectionWorker` → `ROMInjectionWorker(InjectionWorkerBase)`
- `SpriteScanWorker` → `SpriteScanWorker(ScanWorkerBase)`
- `SpriteSearchWorker` → `SpriteSearchWorker(ScanWorkerBase)`
- `SpritePreviewWorker` → `PreviewWorker(BaseWorker)`
- `RangeScanWorker` → `RangeScanWorker(ScanWorkerBase)`

#### 2.2 Migration Strategy
1. Create new worker alongside old one
2. Implement using base class pattern
3. Add tests for new worker
4. Update manager to use new worker
5. Remove old worker
6. Update imports

#### 2.3 Example Migration: ExtractionWorker
```python
# core/workers/extraction.py
class VRAMExtractionWorker(ExtractionWorkerBase):
    """Worker for VRAM extraction operations"""
    
    def __init__(self, params: ExtractionParams, parent: Optional[QObject] = None):
        manager = get_extraction_manager()
        super().__init__(manager, parent)
        self.params = params
    
    @override
    def connect_manager_signals(self) -> None:
        """Connect extraction manager signals"""
        self._connections.extend([
            self.manager.extraction_progress.connect(
                lambda msg: self.emit_progress(50, msg)
            ),
            self.manager.palettes_extracted.connect(self.palettes_ready.emit),
            self.manager.preview_generated.connect(self._on_preview_generated),
        ])
    
    def _on_preview_generated(self, img: Image.Image, count: int) -> None:
        """Convert PIL image to QPixmap and emit"""
        pixmap = pil_to_qpixmap(img)
        self.preview_ready.emit(pixmap, count)
    
    @override
    def perform_operation(self) -> None:
        """Perform the extraction via manager"""
        files = self.manager.extract_sprites(self.params)
        self.operation_finished.emit(True, f"Extracted {len(files)} files")
```

### Phase 3: Reorganize Worker Structure (Week 4)

#### 3.1 New Directory Structure
```
core/
  workers/
    __init__.py
    base.py              # Base classes
    extraction.py        # All extraction workers
    injection.py         # All injection workers
    scanning.py          # All scanning workers
    preview.py          # Preview generation workers
```

#### 3.2 Remove UI Workers
- Move all workers from `ui/rom_extraction/workers/` to `core/workers/`
- UI should only create workers, not contain them

### Phase 4: Update Managers (Week 5)

#### 4.1 Remove hasattr Checks
Replace dynamic attribute checking with interface contracts:

```python
# Before
if hasattr(worker, "progress"):
    worker.progress.connect(self._on_worker_progress)

# After
worker.progress.connect(self._on_worker_progress)  # Guaranteed by base class
```

#### 4.2 Standardize Worker Creation
```python
def create_extraction_worker(self, params: ExtractionParams) -> ExtractionWorkerBase:
    """Factory method for creating extraction workers"""
    if "vram_path" in params:
        return VRAMExtractionWorker(params)
    elif "rom_path" in params:
        return ROMExtractionWorker(params)
    else:
        raise ValueError("Invalid extraction parameters")
```

### Phase 5: Improve Type Safety (Week 6)

#### 5.1 Add Type Annotations
- Add proper type hints to all worker methods
- Use `@override` decorator for overridden methods
- Fix QThread signal conflicts

#### 5.2 Create Worker Protocols
```python
from typing import Protocol

class WorkerProtocol(Protocol):
    """Protocol defining worker interface"""
    progress: pyqtSignal
    error: pyqtSignal
    operation_finished: pyqtSignal
    
    def start(self) -> None: ...
    def cancel(self) -> None: ...
    def wait(self, msecs: int = -1) -> bool: ...
```

### Phase 6: Testing Strategy (Ongoing)

#### 6.1 Unit Tests for Base Classes
- Test signal emission
- Test cancellation/pause mechanisms
- Test error handling

#### 6.2 Integration Tests
- Test manager-worker communication
- Test worker lifecycle
- Test concurrent operations

#### 6.3 Migration Tests
- Parallel testing of old vs new workers
- Ensure identical behavior
- Performance comparison

## Implementation Checklist

### Phase 1: Base Classes
- [ ] Create `core/workers/` directory
- [ ] Implement `BaseWorker` class
- [ ] Implement `ManagedWorker` class
- [ ] Implement specialized base classes
- [ ] Write unit tests for base classes
- [ ] Document worker patterns

### Phase 2: Worker Migration
- [ ] Migrate `ExtractionWorker`
- [ ] Migrate `ROMExtractionWorker`
- [ ] Migrate `InjectionWorker`
- [ ] Migrate `ROMInjectionWorker`
- [ ] Migrate `SpriteScanWorker`
- [ ] Migrate `SpriteSearchWorker`
- [ ] Migrate `SpritePreviewWorker`
- [ ] Migrate `RangeScanWorker`

### Phase 3: Reorganization
- [ ] Move workers to `core/workers/`
- [ ] Update all imports
- [ ] Remove old worker files
- [ ] Update documentation

### Phase 4: Manager Updates
- [ ] Remove `hasattr` checks
- [ ] Implement worker factories
- [ ] Update signal connections
- [ ] Test manager-worker integration

### Phase 5: Type Safety
- [ ] Add comprehensive type hints
- [ ] Add `@override` decorators
- [ ] Fix QThread conflicts
- [ ] Run type checker and fix errors

### Phase 6: Testing
- [ ] Create worker test suite
- [ ] Add lifecycle tests
- [ ] Add concurrency tests
- [ ] Performance benchmarks

## Success Metrics

1. **Type Errors**: Reduce from 539 to <100
2. **Code Duplication**: Eliminate duplicate signal definitions
3. **Test Coverage**: >90% coverage for worker code
4. **Performance**: No regression in async operations
5. **Maintainability**: Clear separation of concerns

## Risk Mitigation

1. **Backwards Compatibility**
   - Keep old workers during migration
   - Use feature flags if needed
   - Extensive testing before removal

2. **Performance Impact**
   - Benchmark before/after
   - Profile critical paths
   - Optimize if needed

3. **UI Breakage**
   - Test all UI workflows
   - Update UI code incrementally
   - Have rollback plan

## Estimated Timeline

- **Phase 1**: 1 week (Base classes and tests)
- **Phase 2**: 2 weeks (Worker migration)
- **Phase 3**: 1 week (Reorganization)
- **Phase 4**: 1 week (Manager updates)
- **Phase 5**: 1 week (Type safety)
- **Phase 6**: Ongoing (Testing throughout)

**Total**: 6 weeks for complete refactoring

## Next Steps

1. Review and approve this plan
2. Create tracking issues for each phase
3. Begin Phase 1 implementation
4. Set up parallel testing infrastructure
5. Schedule regular progress reviews