# Threading Fixes Required for SpritePal

## Critical Fixes Needed

### 1. Fix BatchThumbnailWorker Cache Access

```python
# In batch_thumbnail_worker.py, add mutex protection:

def get_cache_size(self) -> int:
    """Get the current cache size (THREAD-SAFE)."""
    with QMutexLocker(self._mutex):  # Add mutex protection
        return len(self._cache)

def clear_cache(self):
    """Clear the thumbnail cache (THREAD-SAFE)."""
    with QMutexLocker(self._mutex):  # Add mutex protection
        self._cache.clear()
```

### 2. Fix Gallery Tab Worker Management

```python
# In sprite_gallery_tab.py, improve worker lifecycle:

def _on_thumbnail_request(self, offset: int, priority: int):
    """Handle thumbnail request with proper threading."""
    if not self.rom_path:
        return
    
    # Create worker with proper pattern if needed
    if not self.thumbnail_worker:
        self._setup_thumbnail_worker()
    
    # Queue thumbnail
    self.thumbnail_worker.queue_thumbnail(offset, 128, priority)

def _setup_thumbnail_worker(self):
    """Setup worker with proper moveToThread pattern."""
    # Create thread and worker
    self.thumbnail_thread = QThread()
    self.thumbnail_worker = BatchThumbnailWorker(
        self.rom_path,
        self.rom_extractor
    )
    
    # Move to thread
    self.thumbnail_worker.moveToThread(self.thumbnail_thread)
    
    # Connect signals with proper cleanup
    self.thumbnail_thread.started.connect(self.thumbnail_worker.start_processing)
    self.thumbnail_worker.finished.connect(self.thumbnail_thread.quit)
    self.thumbnail_worker.finished.connect(self.thumbnail_worker.deleteLater)
    self.thumbnail_thread.finished.connect(self.thumbnail_thread.deleteLater)
    
    # Connect result signals
    self.thumbnail_worker.thumbnail_ready.connect(
        self._on_thumbnail_ready,
        Qt.ConnectionType.QueuedConnection
    )
    
    # Start thread
    self.thumbnail_thread.start()

def cleanup(self):
    """Clean up with proper thread termination."""
    if self.thumbnail_worker:
        self.thumbnail_worker.stop()
    
    if hasattr(self, 'thumbnail_thread') and self.thumbnail_thread:
        if self.thumbnail_thread.isRunning():
            self.thumbnail_thread.quit()
            self.thumbnail_thread.wait(3000)
    
    # Close detached window
    if self.detached_window:
        self.detached_window.close()
```

### 3. Fix TypedWorkerBase Pattern

```python
# In typed_worker_base.py, change to composition pattern:

class TypedWorkerBase(QObject, Generic[M, P, R]):
    """Base class using PROPER threading pattern."""
    
    def __init__(self, manager: M, params: P, parent: QObject | None = None):
        super().__init__(parent)  # Don't inherit from QThread!
        self._manager: M = manager
        self._params: P = params
        self._thread: Optional[QThread] = None
    
    def start_in_thread(self):
        """Start worker in separate thread."""
        self._thread = QThread()
        self.moveToThread(self._thread)
        
        # Connect signals
        self._thread.started.connect(self.run)
        self.finished_signal.connect(self._thread.quit)
        self.finished_signal.connect(self.deleteLater)
        self._thread.finished.connect(self._thread.deleteLater)
        
        # Start
        self._thread.start()
    
    @Slot()
    def run(self):
        """Execute work in worker thread."""
        # Implementation remains similar
        pass
```

## Testing Requirements

### Thread Safety Tests
```python
def test_concurrent_cache_access(qtbot):
    """Test thread-safe cache access."""
    worker = BatchThumbnailWorker("test.rom")
    
    # Simulate concurrent access
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = []
        for _ in range(100):
            futures.append(executor.submit(worker.get_cache_size))
            futures.append(executor.submit(worker.clear_cache))
        
        # Should not crash or deadlock
        for future in futures:
            future.result(timeout=1.0)
```

### Signal Delivery Tests
```python
def test_cross_thread_signals(qtbot):
    """Test proper signal delivery across threads."""
    controller = ThumbnailController()
    received = []
    
    controller.worker.thumbnail_ready.connect(
        lambda o, p: received.append((o, p))
    )
    
    # Start worker
    controller.start_worker("test.rom")
    
    # Queue work
    controller.worker.queue_thumbnail(0x1000, 128, 0)
    
    # Wait for signal
    qtbot.wait(1000)
    
    # Verify signal received in main thread
    assert QThread.currentThread() == QApplication.instance().thread()
    assert len(received) > 0
```

## Performance Optimizations

### Use QThreadPool for Scalability
```python
class ThumbnailPoolWorker(QRunnable):
    """Runnable for thread pool execution."""
    
    def __init__(self, request: ThumbnailRequest):
        super().__init__()
        self.request = request
        self.signals = WorkerSignals()
    
    def run(self):
        """Execute in thread pool."""
        try:
            pixmap = self._generate_thumbnail(self.request)
            self.signals.result.emit(self.request.offset, pixmap)
        except Exception as e:
            self.signals.error.emit(str(e))

# Usage
pool = QThreadPool.globalInstance()
worker = ThumbnailPoolWorker(request)
worker.signals.result.connect(self._on_thumbnail_ready)
pool.start(worker)
```

## Monitoring and Debugging

### Add Thread Diagnostics
```python
import threading

def log_thread_info(context: str):
    """Log current thread information."""
    qt_thread = QThread.currentThread()
    py_thread = threading.current_thread()
    
    logger.debug(
        f"{context} - Qt Thread: {qt_thread}, "
        f"Python Thread: {py_thread.name} ({py_thread.ident})"
    )
```

## Priority Order for Implementation

1. **IMMEDIATE**: Fix cache mutex protection in BatchThumbnailWorker
2. **HIGH**: Refactor to moveToThread pattern
3. **HIGH**: Add proper cleanup with deleteLater
4. **MEDIUM**: Switch QPixmap to QImage for thread crossing
5. **LOW**: Consider QThreadPool for better scalability