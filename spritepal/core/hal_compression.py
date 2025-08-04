"""
HAL compression/decompression module for SpritePal.
Interfaces with exhal/inhal C tools for ROM sprite injection.
"""

import atexit
import builtins
import contextlib
import multiprocessing as mp
import os
import platform
import queue
import re
import shutil
import signal
import subprocess
import tempfile
import threading
import time
from typing import Any, NamedTuple

try:
    from PyQt6.QtWidgets import QApplication
    QT_AVAILABLE = True
except ImportError:
    QT_AVAILABLE = False

from utils.constants import (
    DATA_SIZE,
    HAL_POOL_SHUTDOWN_TIMEOUT,
    HAL_POOL_SIZE_DEFAULT,
    HAL_POOL_SIZE_MAX,
    HAL_POOL_SIZE_MIN,
    HAL_POOL_TIMEOUT_SECONDS,
)
from utils.logging_config import get_logger

logger = get_logger(__name__)


class HALCompressionError(Exception):
    """Raised when HAL compression/decompression fails"""


class HALPoolError(HALCompressionError):
    """Raised when HAL process pool operations fail"""


class HALRequest(NamedTuple):
    """Request structure for HAL process pool operations"""
    operation: str  # 'decompress' or 'compress'
    rom_path: str
    offset: int
    data: bytes | None = None
    output_path: str | None = None
    fast: bool = False
    request_id: str | None = None


class HALResult(NamedTuple):
    """Result structure for HAL process pool operations"""
    success: bool
    data: bytes | None = None
    size: int | None = None
    error_message: str | None = None
    request_id: str | None = None


def _hal_worker_process(exhal_path: str, inhal_path: str, request_queue: mp.Queue, result_queue: mp.Queue) -> None:
    """Worker process function for HAL operations.

    Runs in a separate process and handles HAL compression/decompression requests.
    """
    import os  # noqa: PLC0415
    import signal  # noqa: PLC0415

    # Ignore interrupt signals in worker processes
    signal.signal(signal.SIGINT, signal.SIG_IGN)

    while True:
        try:
            # Get request from queue (blocking) with error handling for closed pipes
            try:
                request = request_queue.get(timeout=1.0)
            except (BrokenPipeError, EOFError, OSError) as e:
                # Queue closed, main process has shut down
                logger.debug(f"Worker process {os.getpid()}: Request queue closed, exiting: {e}")
                break

            if request is None:  # Shutdown signal
                break

            # Process the request
            if request.operation == "decompress":
                result = _process_decompress(exhal_path, request)
            elif request.operation == "compress":
                result = _process_compress(inhal_path, request)
            else:
                result = HALResult(
                    success=False,
                    error_message=f"Unknown operation: {request.operation}",
                    request_id=request.request_id
                )

            # Put result in queue with error handling for closed pipes
            try:
                result_queue.put(result)
            except (BrokenPipeError, EOFError, OSError) as e:
                # Queue closed, main process has shut down
                logger.debug(f"Worker process {os.getpid()}: Queue closed, exiting gracefully: {e}")
                break

        except queue.Empty:
            continue  # Keep waiting for requests
        except (BrokenPipeError, EOFError, OSError) as e:
            # Pipe/queue closed, exit gracefully
            logger.debug(f"Worker process {os.getpid()}: Connection closed during request handling: {e}")
            break
        except Exception as e:
            # Send error result if queue is still open
            try:
                result = HALResult(
                    success=False,
                    error_message=f"Worker process error: {e!s}",
                    request_id=getattr(request, "request_id", None) if "request" in locals() else None
                )
                result_queue.put(result)
            except (BrokenPipeError, EOFError, OSError):
                # Queue closed, exit gracefully
                logger.debug(f"Worker process {os.getpid()}: Cannot send error result, queue closed")
                break


def _process_decompress(exhal_path: str, request: HALRequest) -> HALResult:
    """Process decompression request in worker process."""
    try:
        # Create temporary output file
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            output_path = tmp.name

        try:
            # Run exhal: exhal romfile offset outfile
            cmd = [exhal_path, request.rom_path, f"0x{request.offset:X}", output_path]

            result = subprocess.run(cmd, check=False, capture_output=True, text=True)

            if result.returncode != 0:
                return HALResult(
                    success=False,
                    error_message=f"Decompression failed: {result.stderr}",
                    request_id=request.request_id
                )

            # Read decompressed data
            with open(output_path, "rb") as f:
                data = f.read()

            return HALResult(
                success=True,
                data=data,
                size=len(data),
                request_id=request.request_id
            )

        finally:
            # Clean up temp file
            with contextlib.suppress(Exception):
                os.unlink(output_path)

    except Exception as e:
        return HALResult(
            success=False,
            error_message=f"Decompression error: {e!s}",
            request_id=request.request_id
        )


def _process_compress(inhal_path: str, request: HALRequest) -> HALResult:
    """Process compression request in worker process."""
    try:
        if not request.data:
            return HALResult(
                success=False,
                error_message="No data provided for compression",
                request_id=request.request_id
            )

        # Write input to temp file
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp.write(request.data)
            tmp_path = tmp.name

        try:
            if request.output_path:
                # Compress to file
                cmd = [inhal_path]
                if request.fast:
                    cmd.append("-fast")
                cmd.extend(["-n", tmp_path, request.output_path])

                result = subprocess.run(cmd, check=False, capture_output=True, text=True)

                if result.returncode != 0:
                    return HALResult(
                        success=False,
                        error_message=f"Compression failed: {result.stderr}",
                        request_id=request.request_id
                    )

                # Get compressed size
                compressed_size = os.path.getsize(request.output_path)

                return HALResult(
                    success=True,
                    size=compressed_size,
                    request_id=request.request_id
                )
            # ROM injection - not supported in pool mode for safety
            return HALResult(
                success=False,
                error_message="ROM injection not supported in pool mode",
                request_id=request.request_id
            )

        finally:
            # Clean up temp file
            with contextlib.suppress(Exception):
                os.unlink(tmp_path)

    except Exception as e:
        return HALResult(
            success=False,
            error_message=f"Compression error: {e!s}",
            request_id=request.request_id
        )


class HALProcessPool:
    """Singleton HAL process pool for efficient compression/decompression operations."""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        # Only initialize once
        if hasattr(self, "_initialized"):
            return

        self._initialized = True
        self._pool_lock = threading.RLock()
        self._pool = None
        self._manager = None
        self._request_queue = None
        self._result_queue = None
        self._processes = []
        self._process_pids = []  # Track PIDs for debugging
        self._shutdown = False
        self._pool_size = HAL_POOL_SIZE_DEFAULT
        self._exhal_path = None
        self._inhal_path = None
        self._qt_cleanup_connected = False

        # Register cleanup on exit
        atexit.register(self.shutdown)

        logger.info("HALProcessPool singleton initialized")

    def initialize(self, exhal_path: str, inhal_path: str, pool_size: int = HAL_POOL_SIZE_DEFAULT) -> bool:
        """Initialize the process pool with HAL tool paths.

        Returns:
            True if initialization successful, False otherwise
        """
        with self._pool_lock:
            if self._pool is not None:
                logger.debug("Pool already initialized")
                return True

            try:
                # Validate pool size
                pool_size = max(HAL_POOL_SIZE_MIN, min(pool_size, HAL_POOL_SIZE_MAX))
                self._pool_size = pool_size
                self._exhal_path = exhal_path
                self._inhal_path = inhal_path

                # Create multiprocessing manager for queues
                self._manager = mp.Manager()
                self._request_queue = self._manager.Queue()
                self._result_queue = self._manager.Queue()

                # Start worker processes (daemon=False to prevent zombie processes)
                logger.info(f"Starting HAL process pool with {pool_size} workers")
                for i in range(pool_size):
                    p = mp.Process(
                        target=_hal_worker_process,
                        args=(exhal_path, inhal_path, self._request_queue, self._result_queue),
                        daemon=False  # Changed from True to prevent zombie processes
                    )
                    p.start()
                    self._processes.append(p)
                    self._process_pids.append(p.pid)
                    logger.debug(f"Started worker process {i+1}/{pool_size}: PID {p.pid}")

                # Connect to Qt application aboutToQuit signal if available
                self._connect_qt_cleanup()

                # Test pool with a simple operation
                test_request = HALRequest(
                    operation="decompress",
                    rom_path="",  # Will fail but tests communication
                    offset=0,
                    request_id="test"
                )
                self._request_queue.put(test_request)

                try:
                    self._result_queue.get(timeout=2.0)
                    logger.debug("Pool communication test successful")
                except queue.Empty:
                    raise HALPoolError("Pool communication test failed - no response from workers") from None

                self._pool = True  # Mark as initialized
                logger.info("HAL process pool initialized successfully")
                return True

            except Exception as e:
                logger.exception(f"Failed to initialize HAL process pool: {e}")
                self.shutdown()
                return False

    def _connect_qt_cleanup(self):
        """Connect cleanup to QApplication.aboutToQuit signal if Qt is available."""
        if not QT_AVAILABLE or self._qt_cleanup_connected:
            return

        try:
            app = QApplication.instance()
            if app is not None:
                app.aboutToQuit.connect(self.shutdown)
                self._qt_cleanup_connected = True
                logger.debug("Connected HAL pool cleanup to QApplication.aboutToQuit signal")
        except Exception as e:
            logger.debug(f"Could not connect to QApplication.aboutToQuit: {e}")

    def submit_request(self, request: HALRequest) -> HALResult:
        """Submit a single request to the pool and wait for result.

        Args:
            request: HAL operation request

        Returns:
            HAL operation result
        """
        if self._pool is None or self._shutdown:
            return HALResult(
                success=False,
                error_message="Pool not initialized or shutting down",
                request_id=request.request_id
            )

        try:
            # Put request in queue
            self._request_queue.put(request)

            # Wait for result with timeout
            timeout = HAL_POOL_TIMEOUT_SECONDS
            return self._result_queue.get(timeout=timeout)


        except queue.Empty:
            return HALResult(
                success=False,
                error_message=f"Operation timed out after {timeout} seconds",
                request_id=request.request_id
            )
        except Exception as e:
            return HALResult(
                success=False,
                error_message=f"Pool error: {e!s}",
                request_id=request.request_id
            )

    def submit_batch(self, requests: list[HALRequest]) -> list[HALResult]:
        """Submit multiple requests to the pool for parallel processing.

        Args:
            requests: List of HAL operation requests

        Returns:
            List of HAL operation results in same order as requests
        """
        if self._pool is None or self._shutdown:
            return [
                HALResult(
                    success=False,
                    error_message="Pool not initialized or shutting down",
                    request_id=req.request_id
                )
                for req in requests
            ]

        try:
            # Submit all requests
            for req in requests:
                self._request_queue.put(req)

            # Collect results
            results = {}
            timeout = HAL_POOL_TIMEOUT_SECONDS
            deadline = time.time() + timeout

            for _ in requests:
                remaining = deadline - time.time()
                if remaining <= 0:
                    break

                try:
                    result = self._result_queue.get(timeout=remaining)
                    if result.request_id:
                        results[result.request_id] = result
                except queue.Empty:
                    break

            # Return results in same order as requests
            return [
                results.get(
                    req.request_id,
                    HALResult(
                        success=False,
                        error_message="No result received",
                        request_id=req.request_id
                    )
                )
                for req in requests
            ]

        except Exception as e:
            logger.exception(f"Batch processing error: {e}")
            return [
                HALResult(
                    success=False,
                    error_message=f"Batch error: {e!s}",
                    request_id=req.request_id
                )
                for req in requests
            ]

    def shutdown(self):
        """Shutdown the process pool gracefully with robust error handling."""
        with self._pool_lock:
            if self._pool is None or self._shutdown:
                return

            self._shutdown = True
            logger.info(f"Shutting down HAL process pool (PIDs: {self._process_pids})")

            # Phase 1: Send shutdown signals to workers
            try:
                if self._request_queue is not None:
                    for _ in self._processes:
                        try:
                            self._request_queue.put(None, timeout=1.0)
                        except Exception as e:
                            logger.debug(f"Error sending shutdown signal: {e}")
            except Exception as e:
                logger.warning(f"Error sending shutdown signals: {e}")

            # Phase 2: Graceful shutdown with timeouts
            alive_processes = []
            deadline = time.time() + HAL_POOL_SHUTDOWN_TIMEOUT

            for p in self._processes:
                if not p.is_alive():
                    logger.debug(f"Process {p.pid} already terminated")
                    continue

                remaining = max(0, deadline - time.time())
                if remaining > 0:
                    try:
                        p.join(timeout=remaining)
                        if not p.is_alive():
                            logger.debug(f"Process {p.pid} gracefully terminated")
                        else:
                            alive_processes.append(p)
                    except Exception as e:
                        logger.debug(f"Error during graceful join for PID {p.pid}: {e}")
                        alive_processes.append(p)
                else:
                    alive_processes.append(p)

            # Phase 3: Forceful termination for stuck processes
            for p in alive_processes:
                if p.is_alive():
                    logger.warning(f"Force terminating stuck worker process {p.pid}")
                    try:
                        p.terminate()
                        p.join(timeout=1.0)
                        if p.is_alive():
                            logger.error(f"Process {p.pid} still alive after terminate(), attempting kill()")
                            try:
                                p.kill()
                                p.join(timeout=1.0)
                                if p.is_alive():
                                    logger.error(f"Process {p.pid} survived kill() - potential zombie")
                                else:
                                    logger.debug(f"Process {p.pid} killed successfully")
                            except Exception as e:
                                logger.error(f"Failed to kill process {p.pid}: {e}")
                        else:
                            logger.debug(f"Process {p.pid} terminated successfully")
                    except Exception as e:
                        logger.error(f"Error terminating process {p.pid}: {e}")

            # Phase 4: Manager shutdown with comprehensive error handling
            if self._manager is not None:
                try:
                    logger.debug("Shutting down multiprocessing manager")
                    self._manager.shutdown()
                    logger.debug("Manager shutdown completed successfully")
                except (OSError, EOFError, BrokenPipeError) as e:
                    # These are expected during shutdown when processes are terminated
                    logger.debug(f"Expected manager shutdown error: {e}")
                except Exception as e:
                    logger.warning(f"Unexpected error during manager shutdown: {e}")

            # Phase 5: Final cleanup
            try:
                self._processes.clear()
                self._process_pids.clear()
                self._pool = None
                self._manager = None
                self._request_queue = None
                self._result_queue = None
                logger.info("HAL process pool shutdown complete")
            except Exception as e:
                logger.error(f"Error during final cleanup: {e}")

    def _force_cleanup_zombies(self):
        """Emergency cleanup for zombie processes."""
        for pid in self._process_pids:
            try:
                # Check if process still exists
                os.kill(pid, 0)  # Doesn't actually send signal, just checks existence
                logger.warning(f"Zombie process detected: PID {pid}")
                try:
                    os.kill(pid, signal.SIGTERM)
                    time.sleep(0.1)
                    os.kill(pid, signal.SIGKILL)
                    logger.debug(f"Forcefully cleaned up zombie process {pid}")
                except (OSError, ProcessLookupError):
                    pass  # Process already gone
            except (OSError, ProcessLookupError):
                # Process doesn't exist anymore
                pass
            except Exception as e:
                logger.debug(f"Error checking process {pid}: {e}")

    def __del__(self):
        """Destructor to ensure cleanup happens even if shutdown is not called explicitly."""
        try:
            if hasattr(self, "_pool") and self._pool is not None and not self._shutdown:
                logger.debug("HALProcessPool destructor triggered - cleaning up resources")
                self.shutdown()
        except Exception:
            # Ignore errors in destructor to prevent issues during interpreter shutdown
            pass

    @property
    def is_initialized(self) -> bool:
        """Check if pool is initialized and ready."""
        return self._pool is not None and not self._shutdown


class HALCompressor:
    """Handles HAL compression/decompression for ROM injection"""

    def __init__(
        self, exhal_path: str | None = None, inhal_path: str | None = None, use_pool: bool = True
    ):
        """
        Initialize HAL compressor.

        Args:
            exhal_path: Path to exhal executable (decompressor)
            inhal_path: Path to inhal executable (compressor)
            use_pool: Whether to use process pool for performance
        """
        logger.info("Initializing HAL compressor")
        # Try to find tools in various locations
        self.exhal_path: str = self._find_tool("exhal", exhal_path)
        self.inhal_path: str = self._find_tool("inhal", inhal_path)
        logger.info(f"HAL compressor initialized with exhal={self.exhal_path}, inhal={self.inhal_path}")

        # Initialize process pool if requested
        self._use_pool = use_pool
        self._pool = None
        self._pool_failed = False

        if use_pool:
            try:
                self._pool = HALProcessPool()
                if self._pool.initialize(self.exhal_path, self.inhal_path):
                    logger.info("HAL process pool enabled for enhanced performance")
                else:
                    logger.warning("HAL process pool initialization failed - falling back to subprocess mode")
                    self._pool = None
                    self._pool_failed = True
            except Exception as e:
                logger.warning(f"Could not enable HAL process pool: {e} - falling back to subprocess mode")
                self._pool = None
                self._pool_failed = True

    def _find_tool(self, tool_name: str, provided_path: str | None = None) -> str:
        """Find HAL compression tool executable"""
        logger.info(f"Searching for {tool_name} tool")

        if provided_path:
            logger.debug(f"Checking provided path: {provided_path}")
            if os.path.isfile(provided_path):
                logger.info(f"Using provided {tool_name} at: {provided_path}")
                return provided_path
            logger.warning(f"Provided path does not exist: {provided_path}")

        # Platform-specific executable suffix
        exe_suffix = ".exe" if platform.system() == "Windows" else ""
        tool_with_suffix = f"{tool_name}{exe_suffix}"

        # Search locations
        search_paths = [
            # Compiled tools directory (preferred)
            f"tools/{tool_with_suffix}",
            f"./tools/{tool_with_suffix}",
            # Current directory
            tool_with_suffix,
            f"./{tool_with_suffix}",
            # Archive directory (from codebase structure)
            f"../archive/obsolete_test_images/ultrathink/{tool_name}",
            f"../archive/obsolete_test_images/ultrathink/{tool_with_suffix}",
            # Parent directories
            f"../{tool_name}",
            f"../../{tool_name}",
            # System PATH
            tool_name,
        ]

        logger.debug(f"Searching {len(search_paths)} locations for {tool_name}")
        for i, path in enumerate(search_paths, 1):
            full_path = os.path.abspath(path)
            if os.path.isfile(full_path):
                logger.info(f"Found {tool_name} at location {i}/{len(search_paths)}: {full_path}")
                # Check if file is executable
                if not os.access(full_path, os.X_OK):
                    logger.warning(f"Found {tool_name} but it may not be executable: {full_path}")
                return full_path
            logger.debug(f"Location {i}/{len(search_paths)}: Not found at {full_path}")

        logger.error(f"Could not find {tool_name} executable in any search path")
        raise HALCompressionError(
            f"Could not find {tool_name} executable. "
            f"Please run 'python compile_hal_tools.py' to build for your platform."
        )

    def decompress_from_rom(
        self, rom_path: str, offset: int, output_path: str | None = None
    ) -> bytes:
        """
        Decompress data from ROM at specified offset.

        Args:
            rom_path: Path to ROM file
            offset: Offset in ROM where compressed data starts
            output_path: path to save decompressed data

        Returns:
            Decompressed data as bytes
        """
        logger.info(f"Decompressing from ROM: {rom_path} at offset 0x{offset:X}")

        # Try to use pool if available
        if self._pool and self._pool.is_initialized:
            request = HALRequest(
                operation="decompress",
                rom_path=rom_path,
                offset=offset,
                output_path=output_path,
                request_id=f"decompress_{offset}"
            )

            result = self._pool.submit_request(request)

            if result.success and result.data:
                logger.info(f"Successfully decompressed {len(result.data)} bytes using pool")
                # Save to output file if specified
                if output_path:
                    with open(output_path, "wb") as f:
                        f.write(result.data)
                return result.data
            if not self._pool_failed:
                # Pool operation failed, fall back to subprocess
                logger.warning(f"Pool decompression failed: {result.error_message}, falling back to subprocess")

        # Subprocess fallback (original implementation)
        # Create temporary output file if not specified
        if output_path is None:
            with tempfile.NamedTemporaryFile(delete=False) as tmp:
                output_path = tmp.name

        try:
            # Run exhal: exhal romfile offset outfile
            cmd = [self.exhal_path, rom_path, f"0x{offset:X}", output_path]
            logger.debug(f"Running command: {' '.join(cmd)}")

            result = subprocess.run(cmd, check=False, capture_output=True, text=True)
            logger.debug(f"Command completed with return code: {result.returncode}")

            if result.stdout:
                logger.debug(f"stdout: {result.stdout.strip()}")
            if result.stderr:
                logger.debug(f"stderr: {result.stderr.strip()}")

            if result.returncode != 0:
                logger.error(f"Decompression failed with return code {result.returncode}")
                raise HALCompressionError(f"Decompression failed: {result.stderr}")

            # Read decompressed data
            with open(output_path, "rb") as f:
                data = f.read()

            logger.info(f"Successfully decompressed {len(data)} bytes from ROM offset 0x{offset:X}")
            return data

        finally:
            # Clean up temp file if we created one
            if output_path and output_path.startswith(tempfile.gettempdir()):
                with contextlib.suppress(builtins.BaseException):
                    os.unlink(output_path)

    def compress_to_file(
        self, input_data: bytes, output_path: str, fast: bool = False
    ) -> int:
        """
        Compress data to a file.

        Args:
            input_data: Data to compress
            output_path: Path to save compressed data
            fast: Use fast compression mode

        Returns:
            Size of compressed data
        """
        logger.info(f"Compressing {len(input_data)} bytes to file: {output_path}")

        # Check size limit
        if len(input_data) > DATA_SIZE:
            logger.error(f"Input data too large: {len(input_data)} bytes (max {DATA_SIZE})")
            raise HALCompressionError(
                f"Input data too large: {len(input_data)} bytes (max {DATA_SIZE})"
            )

        # Write input to temp file
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp.write(input_data)
            tmp_path = tmp.name

        try:
            # Run inhal: inhal [-fast] -n infile outfile
            cmd = [self.inhal_path]
            if fast:
                cmd.append("-fast")
                logger.debug("Using fast compression mode")
            cmd.extend(["-n", tmp_path, output_path])

            logger.debug(f"Running command: {' '.join(cmd)}")
            result = subprocess.run(cmd, check=False, capture_output=True, text=True)
            logger.debug(f"Command completed with return code: {result.returncode}")

            if result.stdout:
                logger.debug(f"stdout: {result.stdout.strip()}")
            if result.stderr:
                logger.debug(f"stderr: {result.stderr.strip()}")

            if result.returncode != 0:
                logger.error(f"Compression failed with return code {result.returncode}: {result.stderr}")
                raise HALCompressionError(f"Compression failed: {result.stderr}")

            # Get compressed size
            compressed_size = os.path.getsize(output_path)
            compression_ratio = (len(input_data) - compressed_size) / len(input_data) * 100
            logger.info(f"Compressed to {compressed_size} bytes ({compression_ratio:.1f}% reduction)")
            return compressed_size

        finally:
            # Clean up temp file
            with contextlib.suppress(builtins.BaseException):
                os.unlink(tmp_path)

    def compress_to_rom(
        self,
        input_data: bytes,
        rom_path: str,
        offset: int,
        output_rom_path: str | None = None,
        fast: bool = False
    ) -> tuple[bool, str]:
        """
        Compress data and inject into ROM at specified offset.

        Args:
            input_data: Data to compress and inject
            rom_path: Path to input ROM file
            offset: Offset in ROM to inject compressed data
            output_rom_path: Path for output ROM (if None, modifies in place)
            fast: Use fast compression mode

        Returns:
            Tuple of (success, message)
        """
        logger.info(f"Compressing {len(input_data)} bytes to ROM: {rom_path} at offset 0x{offset:X}")

        # Check size limit
        if len(input_data) > DATA_SIZE:
            logger.error(f"Input data too large: {len(input_data)} bytes (max {DATA_SIZE})")
            return (
                False,
                f"Input data too large: {len(input_data)} bytes (max {DATA_SIZE})"
            )

        # If no output path, modify in place
        if output_rom_path is None:
            output_rom_path = rom_path
            logger.debug("Modifying ROM in place")
        else:
            # Copy ROM to output path first
            logger.debug(f"Copying ROM to output path: {output_rom_path}")
            shutil.copy2(rom_path, output_rom_path)

        # Write input to temp file
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp.write(input_data)
            tmp_path = tmp.name

        try:
            # Run inhal: inhal [-fast] infile romfile offset
            cmd = [self.inhal_path]
            if fast:
                cmd.append("-fast")
                logger.debug("Using fast compression mode")
            cmd.extend([tmp_path, output_rom_path, f"0x{offset:X}"])

            logger.debug(f"Running command: {' '.join(cmd)}")
            result = subprocess.run(cmd, check=False, capture_output=True, text=True)
            logger.debug(f"Command completed with return code: {result.returncode}")

            if result.stdout:
                logger.debug(f"stdout: {result.stdout.strip()}")
            if result.stderr:
                logger.debug(f"stderr: {result.stderr.strip()}")

            if result.returncode != 0:
                logger.error(f"ROM injection failed with return code {result.returncode}")
                return False, f"ROM injection failed: {result.stderr}"

            # Extract size info from output if available
            compressed_size = "unknown"
            if "bytes" in result.stdout:
                # Try to parse compressed size from output
                match = re.search(r"(\d+)\s+bytes", result.stdout)
                if match:
                    compressed_size = match.group(1)

            logger.info(f"Successfully injected compressed data ({compressed_size} bytes) at offset 0x{offset:X}")
            return (
                True,
                f"Successfully injected compressed data ({compressed_size} bytes) at offset 0x{offset:X}"
            )

        finally:
            # Clean up temp file
            with contextlib.suppress(builtins.BaseException):
                os.unlink(tmp_path)

    def test_tools(self) -> tuple[bool, str]:
        """Test if HAL compression tools are available and working"""
        logger.info("Testing HAL compression tools")

        def _test_tool(tool_path: str, tool_name: str) -> str | None:
            """Helper to test a single HAL tool. Returns error message or None if success."""
            logger.debug(f"Testing {tool_name} at: {tool_path}")
            result = subprocess.run(
                [tool_path], check=False, capture_output=True, text=True
            )
            # Check both stdout and stderr for tool output
            output = (result.stdout + result.stderr).lower()
            if tool_name.lower() not in output and "usage" not in output:
                logger.error(f"{tool_name} tool not working correctly. Output: {output[:100]}")
                return f"{tool_name} tool not working correctly"
            return None

        try:
            # Test both tools
            error_msg = _test_tool(self.exhal_path, "exhal")
            if error_msg:
                return False, error_msg

            error_msg = _test_tool(self.inhal_path, "inhal")
            if error_msg:
                return False, error_msg

        except FileNotFoundError:
            logger.exception("HAL tools not found")
            error_msg = f"HAL tools not found. Please run 'python compile_hal_tools.py' to build for {platform.system()}"
        except OSError as e:
            logger.exception("OS error testing tools")
            if platform.system() == "Windows" and hasattr(e, "winerror") and getattr(e, "winerror", None) == 193:
                error_msg = "Wrong platform binaries. Please run 'python compile_hal_tools.py' to build for Windows"
            else:
                error_msg = f"Error testing tools: {e!s}"
        except subprocess.SubprocessError as e:
            logger.exception("Subprocess error testing tools")
            error_msg = f"Error running tools: {e!s}"
        except ValueError as e:
            logger.exception("Value error testing tools")
            error_msg = f"Invalid tool configuration: {e!s}"
        else:
            logger.info("HAL compression tools are working correctly")
            return True, "HAL compression tools are working correctly"

        return False, error_msg

    def decompress_batch(self, requests: list[tuple[str, int]]) -> list[tuple[bool, bytes | str]]:
        """
        Decompress multiple ROM offsets in parallel for improved performance.

        Args:
            requests: List of (rom_path, offset) tuples

        Returns:
            List of (success, data_or_error) tuples in same order as requests
        """
        if not self._pool or not self._pool.is_initialized:
            # Fall back to sequential processing
            logger.debug("Pool not available, using sequential batch processing")
            results = []
            for rom_path, offset in requests:
                try:
                    data = self.decompress_from_rom(rom_path, offset)
                    results.append((True, data))
                except Exception as e:
                    results.append((False, str(e)))
            return results

        # Convert to HALRequest objects
        hal_requests = [
            HALRequest(
                operation="decompress",
                rom_path=rom_path,
                offset=offset,
                request_id=f"batch_{i}"
            )
            for i, (rom_path, offset) in enumerate(requests)
        ]

        # Submit batch to pool
        logger.info(f"Processing batch of {len(requests)} decompression requests using pool")
        hal_results = self._pool.submit_batch(hal_requests)

        # Convert results
        results = []
        for result in hal_results:
            if result.success and result.data:
                results.append((True, result.data))
            else:
                results.append((False, result.error_message or "Unknown error"))

        return results

    def compress_batch(self, requests: list[tuple[bytes, str, bool]]) -> list[tuple[bool, int | str]]:
        """
        Compress multiple data blocks in parallel for improved performance.

        Args:
            requests: List of (data, output_path, fast) tuples

        Returns:
            List of (success, size_or_error) tuples in same order as requests
        """
        if not self._pool or not self._pool.is_initialized:
            # Fall back to sequential processing
            logger.debug("Pool not available, using sequential batch processing")
            results = []
            for data, output_path, fast in requests:
                try:
                    size = self.compress_to_file(data, output_path, fast)
                    results.append((True, size))
                except Exception as e:
                    results.append((False, str(e)))
            return results

        # Convert to HALRequest objects
        hal_requests = [
            HALRequest(
                operation="compress",
                rom_path="",  # Not used for compression
                offset=0,  # Not used for compression
                data=data,
                output_path=output_path,
                fast=fast,
                request_id=f"batch_compress_{i}"
            )
            for i, (data, output_path, fast) in enumerate(requests)
        ]

        # Submit batch to pool
        logger.info(f"Processing batch of {len(requests)} compression requests using pool")
        hal_results = self._pool.submit_batch(hal_requests)

        # Convert results
        results = []
        for result in hal_results:
            if result.success and result.size is not None:
                results.append((True, result.size))
            else:
                results.append((False, result.error_message or "Unknown error"))

        return results

    @property
    def pool_status(self) -> dict[str, Any]:
        """Get status information about the HAL process pool."""
        if not self._pool:
            return {
                "enabled": False,
                "reason": "Pool not configured" if not self._use_pool else "Pool initialization failed"
            }

        return {
            "enabled": True,
            "initialized": self._pool.is_initialized,
            "pool_size": getattr(self._pool, "_pool_size", 0),
            "mode": "pool" if self._pool.is_initialized else "subprocess"
        }
