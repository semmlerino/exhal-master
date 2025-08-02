"""
Worker Manager for consistent QThread worker lifecycle management.

This module provides simplified worker management that matches the patterns
used throughout the SpritePal codebase:
- Simple cleanup with quit() and wait()
- Optional timeouts for termination
- Consistent logging
"""

from typing import Optional

from PyQt6.QtCore import QThread
from utils.logging_config import get_logger

logger = get_logger(__name__)


class WorkerManager:
    """
    Simple helper for managing QThread worker lifecycle.

    This class provides:
    - Consistent worker cleanup patterns
    - Optional timeout handling
    - Debug logging for worker operations
    """

    @staticmethod
    def cleanup_worker(
        worker: Optional[QThread],
        timeout: int = 3000,
        force_terminate: bool = True
    ) -> None:
        """
        Clean up a worker thread using the standard pattern.

        Args:
            worker: The worker thread to clean up (can be None)
            timeout: Milliseconds to wait for graceful shutdown (default: 3000)
            force_terminate: Whether to force terminate if quit fails
        """
        if not worker:
            return

        worker_name = worker.__class__.__name__

        if worker.isRunning():
            logger.debug(f"Stopping {worker_name}")
            worker.quit()

            if not worker.wait(timeout):
                if force_terminate:
                    logger.warning(f"{worker_name} did not stop gracefully, terminating")
                    worker.terminate()
                    worker.wait(1000)  # Wait up to 1 second for termination
                else:
                    logger.warning(f"{worker_name} did not stop within {timeout}ms")

        # Schedule for deletion
        worker.deleteLater()
        logger.debug(f"{worker_name} cleaned up")

    @staticmethod
    def start_worker(
        worker: QThread,
        cleanup_existing: Optional[QThread] = None,
        cleanup_timeout: int = 3000
    ) -> None:
        """
        Start a new worker, optionally cleaning up an existing one first.

        Args:
            worker: The new worker to start
            cleanup_existing: Existing worker to clean up first (optional)
            cleanup_timeout: Timeout for cleaning up existing worker
        """
        # Clean up existing worker if provided
        if cleanup_existing:
            WorkerManager.cleanup_worker(cleanup_existing, cleanup_timeout)

        # Start the new worker
        worker_name = worker.__class__.__name__
        logger.debug(f"Starting {worker_name}")
        worker.start()

    @staticmethod
    def create_and_start(
        worker_class: type,
        *args,
        cleanup_existing: Optional[QThread] = None,
        **kwargs
    ) -> QThread:
        """
        Create and start a worker in one call.

        Args:
            worker_class: The worker class to instantiate
            *args: Arguments for worker constructor
            cleanup_existing: Existing worker to clean up first
            **kwargs: Keyword arguments for worker constructor

        Returns:
            The newly created and started worker
        """
        # Clean up existing worker if provided
        if cleanup_existing:
            WorkerManager.cleanup_worker(cleanup_existing)

        # Create and start new worker
        worker = worker_class(*args, **kwargs)
        WorkerManager.start_worker(worker)
        return worker
