"""
Base worker classes for standardized async operations.

This module provides the foundation for all worker threads in SpritePal,
ensuring consistent interfaces, proper error handling, and type safety.
"""

from abc import ABCMeta, abstractmethod
from typing import Any, Optional, TYPE_CHECKING
from PyQt6.QtCore import QThread, pyqtSignal, QObject, QMetaObject

if TYPE_CHECKING:
    from spritepal.core.managers.factory import ManagerFactory

from core.managers.base_manager import BaseManager
from utils.logging_config import get_logger

logger = get_logger(__name__)


class WorkerMeta(type(QThread), ABCMeta):
    """Metaclass to resolve conflict between QThread and ABC metaclasses."""
    pass


class BaseWorker(QThread, metaclass=WorkerMeta):
    """
    Base class for all worker threads with standard signals and behavior.
    
    Provides:
    - Standard signal interface
    - Cancellation and pause support
    - Consistent error handling
    - Progress reporting utilities
    """
    
    # Standard signals all workers must have
    progress = pyqtSignal(int, str)  # percent (0-100), message
    error = pyqtSignal(str, Exception)  # message, exception
    warning = pyqtSignal(str)  # warning message
    
    # Standard finished signal - use this instead of QThread.finished
    operation_finished = pyqtSignal(bool, str)  # success, message
    
    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._is_cancelled = False
        self._is_paused = False
        self._operation_name = self.__class__.__name__
    
    def cancel(self) -> None:
        """Request cancellation of the operation."""
        logger.debug(f"{self._operation_name}: Cancellation requested")
        self._is_cancelled = True
    
    def pause(self) -> None:
        """Request pause of the operation."""
        logger.debug(f"{self._operation_name}: Pause requested")
        self._is_paused = True
    
    def resume(self) -> None:
        """Resume paused operation."""
        logger.debug(f"{self._operation_name}: Resume requested")
        self._is_paused = False
    
    @property
    def is_cancelled(self) -> bool:
        """Check if cancellation was requested."""
        return self._is_cancelled
    
    @property
    def is_paused(self) -> bool:
        """Check if operation is paused."""
        return self._is_paused
    
    def emit_progress(self, percent: int, message: str = "") -> None:
        """
        Emit progress in a standard format.
        
        Args:
            percent: Progress percentage (0-100)
            message: Optional progress message
        """
        # Clamp percent to valid range
        percent = max(0, min(100, percent))
        self.progress.emit(percent, message)
        
        if message:
            logger.debug(f"{self._operation_name}: {percent}% - {message}")
    
    def emit_error(self, message: str, exception: Optional[Exception] = None) -> None:
        """
        Emit error in a standard format.
        
        Args:
            message: Error message
            exception: Optional exception object
        """
        exc = exception or Exception(message)
        logger.error(f"{self._operation_name}: {message}", exc_info=exc)
        self.error.emit(message, exc)
    
    def emit_warning(self, message: str) -> None:
        """
        Emit warning message.
        
        Args:
            message: Warning message
        """
        logger.warning(f"{self._operation_name}: {message}")
        self.warning.emit(message)
    
    def check_cancellation(self) -> None:
        """
        Check if operation was cancelled and exit if so.
        
        Call this periodically in long-running operations.
        
        Raises:
            InterruptedError: If operation was cancelled
        """
        if self._is_cancelled:
            raise InterruptedError("Operation was cancelled")
    
    def wait_if_paused(self) -> None:
        """
        Wait while operation is paused.
        
        Call this periodically in long-running operations.
        """
        while self._is_paused and not self._is_cancelled:
            self.msleep(100)  # Sleep 100ms
    
    @abstractmethod
    def run(self) -> None:
        """
        Subclasses must implement the actual work.
        
        Should emit operation_finished signal when complete.
        """
        pass


class ManagedWorker(BaseWorker):
    """
    Worker that delegates to a manager for business logic.
    
    This pattern ensures that business logic stays in managers
    while workers only handle Qt threading concerns.
    
    Supports both direct manager injection (legacy) and factory-based
    manager creation (recommended for new code).
    """
    
    def __init__(
        self, 
        manager: Optional[BaseManager] = None,
        manager_factory: Optional["ManagerFactory"] = None,
        parent: Optional[QObject] = None
    ) -> None:
        super().__init__(parent)
        
        # Validate parameters
        if manager is not None and manager_factory is not None:
            raise ValueError("Cannot specify both manager and manager_factory")
        
        # Allow both to be None for delayed manager creation pattern
        # (subclass will create manager after super().__init__ completes)
        
        # Store for subclass use
        self.manager = manager
        self._manager_factory = manager_factory
        self._connections: list[QMetaObject.Connection] = []
        
        # If using factory pattern, manager will be created by subclass
        if manager_factory is not None:
            logger.debug(f"{self._operation_name}: Using factory-based manager creation")
        else:
            logger.debug(f"{self._operation_name}: Using direct manager injection")
    
    def connect_manager_signals(self) -> None:
        """
        Connect manager signals to worker signals.
        
        Subclasses should implement this to wire manager signals
        to the appropriate worker signals.
        """
        pass
    
    def disconnect_manager_signals(self) -> None:
        """Disconnect all manager signals for cleanup."""
        for connection in self._connections:
            QObject.disconnect(connection)
        self._connections.clear()
        logger.debug(f"{self._operation_name}: Disconnected {len(self._connections)} manager signals")
    
    def run(self) -> None:
        """
        Template method for managed operations.
        
        Handles the standard lifecycle:
        1. Connect manager signals
        2. Perform operation via manager
        3. Handle errors and cleanup
        4. Emit completion signal
        """
        try:
            logger.debug(f"{self._operation_name}: Starting managed operation")
            self.connect_manager_signals()
            self.perform_operation()
            
        except InterruptedError:
            logger.info(f"{self._operation_name}: Operation cancelled")
            self.operation_finished.emit(False, "Operation cancelled")
            
        except Exception as e:
            error_msg = f"Operation failed: {e!s}"
            logger.error(f"{self._operation_name}: {error_msg}", exc_info=e)
            self.emit_error(error_msg, e)
            self.operation_finished.emit(False, error_msg)
            
        finally:
            self.disconnect_manager_signals()
    
    @abstractmethod
    def perform_operation(self) -> None:
        """
        Subclasses implement the manager delegation.
        
        Should call manager methods and emit operation_finished
        when complete.
        """
        pass