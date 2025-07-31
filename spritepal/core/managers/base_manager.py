"""
Base manager class providing common functionality for all managers
"""

import os
import threading
from typing import Any, Callable

from PyQt6.QtCore import QObject, pyqtSignal

from spritepal.core.managers.exceptions import ValidationError
from spritepal.utils.logging_config import get_logger


class BaseManager(QObject):
    """Abstract base class for all manager classes"""

    # Common signals that all managers can emit
    error_occurred: pyqtSignal = pyqtSignal(str)  # Error message
    warning_occurred: pyqtSignal = pyqtSignal(str)  # Warning message
    operation_started: pyqtSignal = pyqtSignal(str)  # Operation name
    operation_finished: pyqtSignal = pyqtSignal(str)  # Operation name
    progress_updated: pyqtSignal = pyqtSignal(str, int, int)  # Operation name, current, total

    def __init__(self, name: str | None = None) -> None:
        """
        Initialize base manager

        Args:
            name: manager name for logging
        """
        super().__init__()

        # Set up logger with module-specific naming
        self._name = name or self.__class__.__name__
        self._logger = get_logger(f"managers.{self._name}")

        # Thread safety
        self._lock = threading.RLock()
        self._operation_locks: dict[str, threading.Lock] = {}

        # State tracking
        self._is_initialized = False
        self._active_operations: set[str] = set()

        # Initialize the manager
        self._initialize()

    def _initialize(self) -> None:
        """Initialize the manager - must be implemented by subclasses"""
        raise NotImplementedError("Subclasses must implement _initialize()")

    def cleanup(self) -> None:
        """Cleanup resources - must be implemented by subclasses"""
        raise NotImplementedError("Subclasses must implement cleanup()")

    def get_name(self) -> str:
        """Get the manager name"""
        return self._name

    def is_initialized(self) -> bool:
        """Check if manager is initialized"""
        return self._is_initialized

    def is_operation_active(self, operation: str) -> bool:
        """Check if a specific operation is currently active"""
        with self._lock:
            return operation in self._active_operations

    def has_active_operations(self) -> bool:
        """Check if any operations are currently active"""
        with self._lock:
            return len(self._active_operations) > 0

    def _start_operation(self, operation: str) -> bool:
        """
        Mark an operation as started

        Args:
            operation: Operation name

        Returns:
            True if operation started, False if already running
        """
        with self._lock:
            if operation in self._active_operations:
                self._logger.warning(f"Operation '{operation}' is already active")
                return False

            self._active_operations.add(operation)
            self.operation_started.emit(operation)
            self._logger.debug(f"Started operation: {operation}")
            return True

    def _finish_operation(self, operation: str) -> None:
        """
        Mark an operation as finished

        Args:
            operation: Operation name
        """
        with self._lock:
            if operation in self._active_operations:
                self._active_operations.remove(operation)
                self.operation_finished.emit(operation)
                self._logger.debug(f"Finished operation: {operation}")

    def _with_operation_lock(self, operation: str, func: Callable[[], Any]) -> Any:
        """
        Execute a function with operation-specific locking

        Args:
            operation: Operation name for the lock
            func: Function to execute

        Returns:
            Result from the function
        """
        if operation not in self._operation_locks:
            self._operation_locks[operation] = threading.Lock()

        with self._operation_locks[operation]:
            return func()

    def _handle_error(self, error: Exception, operation: str | None = None) -> None:
        """
        Handle an error with logging and signal emission

        Args:
            error: The exception that occurred
            operation: operation name for context
        """
        error_msg = str(error)
        if operation:
            error_msg = f"{operation}: {error_msg}"

        self._logger.error(error_msg, exc_info=True)
        self.error_occurred.emit(error_msg)

        # Finish the operation if it was active
        if operation:
            self._finish_operation(operation)

    def _handle_warning(self, message: str) -> None:
        """
        Handle a warning with logging and signal emission

        Args:
            message: Warning message
        """
        self._logger.warning(message)
        self.warning_occurred.emit(message)

    def _update_progress(self, operation: str, current: int, total: int) -> None:
        """
        Update operation progress

        Args:
            operation: Operation name
            current: Current progress value
            total: Total progress value
        """
        self.progress_updated.emit(operation, current, total)

    def _validate_required(self, params: dict[str, Any], required: list[str]) -> None:
        """
        Validate that required parameters are present

        Args:
            params: Parameters to validate
            required: List of required parameter names

        Raises:
            ValidationError: If required parameters are missing
        """
        missing = [key for key in required if key not in params or not params[key]]
        if missing:
            raise ValidationError(f"Missing required parameters: {', '.join(missing)}")

    def _validate_type(self, value: Any, name: str, expected_type: type) -> None:
        """
        Validate parameter type

        Args:
            value: Value to validate
            name: Parameter name for error messages
            expected_type: Expected type

        Raises:
            ValidationError: If type doesn't match
        """
        if not isinstance(value, expected_type):
            raise ValidationError(
                f"Invalid type for '{name}': expected {expected_type.__name__}, "
                f"got {type(value).__name__}"
            )

    def _validate_file_exists(self, path: str, name: str) -> None:
        """
        Validate that a file exists

        Args:
            path: File path to check
            name: Parameter name for error messages

        Raises:
            ValidationError: If file doesn't exist
        """
        if not os.path.exists(path):
            raise ValidationError(f"{name} does not exist: {path}")

    def _validate_range(self, value: int | float, name: str,
                       min_val: int | float | None = None,
                       max_val: int | float | None = None) -> None:
        """
        Validate that a numeric value is within range

        Args:
            value: Value to validate
            name: Parameter name for error messages
            min_val: Minimum allowed value (inclusive)
            max_val: Maximum allowed value (inclusive)

        Raises:
            ValidationError: If value is out of range
        """
        if min_val is not None and value < min_val:
            raise ValidationError(f"{name} must be >= {min_val}, got {value}")
        if max_val is not None and value > max_val:
            raise ValidationError(f"{name} must be <= {max_val}, got {value}")
