"""
Preview Worker Pool for efficient thread reuse during preview generation.

This module provides a pool of reusable worker threads to prevent the overhead
of creating/destroying threads for each preview request. Features:
- Thread reuse with automatic scaling
- Request priority queuing
- Cancellation support for stale requests
- Automatic cleanup of idle workers
"""

import queue
import threading
import time
import weakref

from PyQt6.QtCore import QMutex, QMutexLocker, QObject, QTimer, pyqtSignal

from ui.common.timing_constants import WORKER_TIMEOUT_SHORT
from ui.common.worker_manager import WorkerManager
from ui.rom_extraction.workers.preview_worker import SpritePreviewWorker
from utils.logging_config import get_logger

logger = get_logger(__name__)


class PooledPreviewWorker(SpritePreviewWorker):
    """
    Enhanced preview worker that supports cancellation and reuse.

    This worker extends the base SpritePreviewWorker with:
    - Request ID tracking for cancellation
    - Periodic cancellation checks during processing
    - Proper cleanup for pool reuse
    """

    # Enhanced signals with request ID
    preview_ready = pyqtSignal(int, bytes, int, int, str)  # request_id, tile_data, width, height, name
    preview_error = pyqtSignal(int, str)  # request_id, error_msg

    def __init__(self, pool_ref: weakref.ReferenceType):
        # Initialize with dummy values - actual values set per request
        super().__init__("", 0, "", None, None)
        self._pool_ref = pool_ref
        self._current_request_id = 0
        self._cancel_requested = threading.Event()
        self._is_processing = False

    def setup_request(self, request, extractor, rom_cache=None) -> None:
        """Setup worker for new request with optional ROM cache."""
        self.rom_path = request.rom_path
        self.offset = request.offset
        self.sprite_name = f"manual_0x{request.offset:X}"
        self.extractor = extractor
        self.rom_cache = rom_cache  # Store ROM cache for potential use
        self.sprite_config = None
        self._current_request_id = request.request_id
        self._cancel_requested.clear()
        self._is_processing = True

    def cancel_current_request(self) -> None:
        """Cancel the current request."""
        self._cancel_requested.set()
        logger.debug(f"Cancellation requested for worker processing request {self._current_request_id}")

    def run(self) -> None:
        """Enhanced run method with cancellation support."""
        if not self._is_processing:
            return

        try:
            # Check for cancellation before starting
            if self._cancel_requested.is_set():
                logger.debug(f"Request {self._current_request_id} cancelled before processing")
                return

            # Call parent run method with cancellation checks
            self._run_with_cancellation_checks()

        except Exception as e:
            if not self._cancel_requested.is_set():
                logger.exception(f"Error in pooled preview worker for request {self._current_request_id}")
                self.preview_error.emit(self._current_request_id, str(e))
        finally:
            self._is_processing = False
            # Return worker to pool
            pool = self._pool_ref()
            if pool:
                pool._return_worker(self)

    def _run_with_cancellation_checks(self) -> None:
        """Run preview generation with periodic cancellation checks."""
        # Import validation functions from parent class

        # Check cancellation before file operations
        if self._cancel_requested.is_set():
            return

        # Validate ROM path
        if not self.rom_path or not self.rom_path.strip():
            raise FileNotFoundError("No ROM path provided")

        # Read ROM data
        try:
            with open(self.rom_path, "rb") as f:
                rom_data = f.read()
        except Exception as e:
            raise OSError(f"Error reading ROM file: {e}") from e

        # Check cancellation after file read
        if self._cancel_requested.is_set():
            return

        # Validate ROM size and offset
        rom_size = len(rom_data)
        if rom_size < 0x8000:
            raise ValueError(f"ROM file too small: {rom_size} bytes")
        if self.offset >= rom_size:
            raise ValueError(f"Offset 0x{self.offset:X} beyond ROM size 0x{rom_size:X}")

        # Check cancellation before decompression
        if self._cancel_requested.is_set():
            return

        # Use conservative size for manual offsets during dragging
        expected_size = 4096  # 4KB for fast preview during dragging

        try:
            # Extract sprite data with size limit
            compressed_size, tile_data = (
                self.extractor.rom_injector.find_compressed_sprite(
                    rom_data, self.offset, expected_size
                )
            )
        except Exception as e:
            raise ValueError(f"Failed to extract sprite at 0x{self.offset:X}: {e}") from e

        # Check cancellation after decompression
        if self._cancel_requested.is_set():
            return

        # Validate extracted data
        if not tile_data:
            raise ValueError(f"No sprite data found at offset 0x{self.offset:X}")

        # Calculate dimensions
        num_tiles = len(tile_data) // 32
        if num_tiles == 0:
            raise ValueError("No complete tiles found in sprite data")

        tiles_per_row = 16
        tile_rows = (num_tiles + tiles_per_row - 1) // tiles_per_row
        width = min(tiles_per_row * 8, 128)
        height = min(tile_rows * 8, 128)

        # Final cancellation check before emitting
        if self._cancel_requested.is_set():
            return

        # Emit success
        self.preview_ready.emit(self._current_request_id, tile_data, width, height, self.sprite_name)


class PreviewWorkerPool(QObject):
    """
    Pool of reusable preview workers for efficient thread management.

    Features:
    - Maintains pool of 1-2 workers to prevent thread churn
    - Priority queue for request handling
    - Automatic cancellation of stale requests
    - Worker cleanup after idle period
    - Thread-safe request submission
    """

    # Signals for completed previews
    preview_ready = pyqtSignal(int, bytes, int, int, str)  # request_id, tile_data, width, height, name
    preview_error = pyqtSignal(int, str)  # request_id, error_msg

    def __init__(self, max_workers: int = 4, idle_timeout: int = 30000):
        super().__init__()

        self._max_workers = max_workers
        self._idle_timeout = idle_timeout

        # Thread-safe collections
        self._available_workers = queue.Queue()
        self._active_workers = set()
        self._request_queue = queue.PriorityQueue()

        # Synchronization
        self._mutex = QMutex()
        self._shutdown_requested = threading.Event()

        # Pool management
        self._worker_count = 0
        self._last_activity = time.time()

        # Cleanup timer
        self._cleanup_timer = QTimer(self)
        self._cleanup_timer.timeout.connect(self._cleanup_idle_workers)
        self._cleanup_timer.start(10000)  # Check every 10 seconds

        logger.debug(f"PreviewWorkerPool initialized with max_workers={max_workers}")

    def submit_request(self, request, extractor, rom_cache=None) -> None:
        """
        Submit a preview request to the worker pool.

        Args:
            request: PreviewRequest object
            extractor: ROM extractor for sprite processing
            rom_cache: Optional ROM cache for performance optimization
        """
        if self._shutdown_requested.is_set():
            logger.warning("Cannot submit request - pool is shutting down")
            return

        with QMutexLocker(self._mutex):
            # Cancel any existing requests with lower priority
            self._cancel_lower_priority_requests(request.priority)

            # Get or create a worker
            worker = self._get_available_worker()
            if worker is None:
                logger.warning("No workers available for request")
                self.preview_error.emit(request.request_id, "No workers available")
                return

            # Setup worker for this request with ROM cache
            worker.setup_request(request, extractor, rom_cache)

            # Connect signals for this request
            worker.preview_ready.connect(self._on_worker_ready)
            worker.preview_error.connect(self._on_worker_error)

            # Move to active set
            self._active_workers.add(worker)
            self._last_activity = time.time()

            # Start processing
            worker.start()

        logger.debug(f"Submitted request {request.request_id} to worker pool")

    def _get_available_worker(self) -> PooledPreviewWorker | None:
        """Get an available worker, creating one if needed."""
        # Try to get existing worker
        try:
            worker = self._available_workers.get_nowait()
            logger.debug("Reusing existing worker")
        except queue.Empty:
            pass
        else:
            return worker

        # Create new worker if under limit
        if self._worker_count < self._max_workers:
            worker = PooledPreviewWorker(weakref.ref(self))
            self._worker_count += 1
            logger.debug(f"Created new worker (count: {self._worker_count})")
            return worker

        logger.warning("Worker pool at capacity")
        return None

    def _return_worker(self, worker: PooledPreviewWorker) -> None:
        """Return a worker to the available pool."""
        with QMutexLocker(self._mutex):
            # Remove from active set
            self._active_workers.discard(worker)

            # Disconnect signals
            worker.preview_ready.disconnect()
            worker.preview_error.disconnect()

            # Return to available pool if not shutting down
            if not self._shutdown_requested.is_set():
                try:
                    self._available_workers.put_nowait(worker)
                    logger.debug("Worker returned to pool")
                except queue.Full:
                    # Pool full, clean up worker
                    logger.debug("Available worker pool full, cleaning up worker")
                    self._cleanup_worker(worker)
            else:
                self._cleanup_worker(worker)

    def _cancel_lower_priority_requests(self, priority: int) -> None:
        """Cancel active requests with lower priority."""
        cancelled_count = 0
        for worker in list(self._active_workers):
            # Cancel workers processing lower priority requests
            if hasattr(worker, "_current_request_id"):
                worker.cancel_current_request()
                cancelled_count += 1

        if cancelled_count > 0:
            logger.debug(f"Cancelled {cancelled_count} lower priority requests")

    def _on_worker_ready(self, request_id: int, tile_data: bytes,
                        width: int, height: int, sprite_name: str) -> None:
        """Handle worker preview ready."""
        self.preview_ready.emit(request_id, tile_data, width, height, sprite_name)

    def _on_worker_error(self, request_id: int, error_msg: str) -> None:
        """Handle worker preview error."""
        self.preview_error.emit(request_id, error_msg)

    def _cleanup_idle_workers(self) -> None:
        """Clean up idle workers after timeout."""
        if self._shutdown_requested.is_set():
            return

        current_time = time.time()
        idle_time = current_time - self._last_activity

        if idle_time > (self._idle_timeout / 1000.0):  # Convert to seconds
            with QMutexLocker(self._mutex):
                # Clean up some idle workers
                workers_to_cleanup = []
                try:
                    while not self._available_workers.empty() and len(workers_to_cleanup) < 1:
                        worker = self._available_workers.get_nowait()
                        workers_to_cleanup.append(worker)
                except queue.Empty:
                    pass

                for worker in workers_to_cleanup:
                    self._cleanup_worker(worker)
                    self._worker_count -= 1

                if workers_to_cleanup:
                    logger.debug(f"Cleaned up {len(workers_to_cleanup)} idle workers")

    def _cleanup_worker(self, worker: PooledPreviewWorker) -> None:
        """Clean up a single worker."""
        try:
            # Cancel any current operation
            worker.cancel_current_request()

            # Use WorkerManager for safe cleanup with longer timeout for preview workers
            # Preview workers may be doing file I/O and decompression, so need more time
            WorkerManager.cleanup_worker(worker, timeout=2000)  # 2 seconds for preview workers

        except Exception as e:
            logger.warning(f"Error cleaning up worker: {e}")

    def cleanup(self) -> None:
        """Clean up the entire worker pool."""
        logger.debug("Cleaning up PreviewWorkerPool")

        self._shutdown_requested.set()
        self._cleanup_timer.stop()

        with QMutexLocker(self._mutex):
            # Cancel all active workers
            for worker in list(self._active_workers):
                worker.cancel_current_request()

            # Clean up all workers
            workers_to_cleanup = []

            # Collect active workers
            workers_to_cleanup.extend(self._active_workers)

            # Collect available workers
            try:
                while not self._available_workers.empty():
                    worker = self._available_workers.get_nowait()
                    workers_to_cleanup.append(worker)
            except queue.Empty:
                pass

            # Clean up all workers with proper termination
            for worker in workers_to_cleanup:
                try:
                    # First cancel the request
                    worker.cancel_current_request()
                    
                    # Request interruption
                    worker.requestInterruption()
                    
                    # Give worker a chance to finish gracefully
                    if worker.isRunning():
                        if not worker.wait(1000):  # Wait up to 1 second
                            logger.warning(f"Worker still running after 1s, forcing quit")
                            worker.quit()
                            if not worker.wait(500):  # Additional 500ms after quit
                                logger.error(f"Worker failed to stop after quit, may cause QThread warning")
                    
                    # Schedule for deletion
                    worker.deleteLater()
                except Exception as e:
                    logger.warning(f"Error during worker cleanup: {e}")

            self._active_workers.clear()
            self._worker_count = 0

        logger.debug("PreviewWorkerPool cleanup complete")
