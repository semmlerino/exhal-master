"""
Centralized error handling service that uses signals instead of direct dialogs.
This allows for proper testing and separation of concerns.
"""

from __future__ import annotations

import threading
from typing import TYPE_CHECKING

from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtWidgets import QMessageBox

if TYPE_CHECKING:
    from PyQt6.QtWidgets import QWidget

from utils.logging_config import get_logger

logger = get_logger(__name__)


class ErrorHandler(QObject):
    """
    Centralized error handler that emits signals for errors instead of showing dialogs directly.
    This allows UI components to handle errors appropriately and makes testing easier.
    """

    # Signals for different error types
    critical_error = pyqtSignal(str, str)  # title, message
    warning_error = pyqtSignal(str, str)   # title, message
    info_message = pyqtSignal(str, str)    # title, message

    def __init__(self, parent: QWidget | None = None):
        """Initialize the error handler"""
        super().__init__(parent)
        self._parent_widget = parent
        self._show_dialogs = True  # Can be disabled for testing

        # Connect signals to default handlers
        self.critical_error.connect(self._show_critical_dialog)
        self.warning_error.connect(self._show_warning_dialog)
        self.info_message.connect(self._show_info_dialog)

    def set_show_dialogs(self, show: bool) -> None:
        """Enable or disable showing dialogs (useful for testing)"""
        self._show_dialogs = show

    def handle_critical_error(self, title: str, message: str) -> None:
        """Handle a critical error by emitting signal"""
        logger.error(f"Critical error - {title}: {message}")
        self.critical_error.emit(title, message)

    def handle_warning(self, title: str, message: str) -> None:
        """Handle a warning by emitting signal"""
        logger.warning(f"Warning - {title}: {message}")
        self.warning_error.emit(title, message)

    def handle_info(self, title: str, message: str) -> None:
        """Handle an info message by emitting signal"""
        logger.info(f"Info - {title}: {message}")
        self.info_message.emit(title, message)

    def handle_exception(self, exception: Exception, context: str = "") -> None:
        """Handle an exception by emitting appropriate signal"""
        error_msg = str(exception)
        if context:
            error_msg = f"{context}: {error_msg}"

        logger.exception(f"Exception in {context}")
        self.critical_error.emit("Error", error_msg)

    def _show_critical_dialog(self, title: str, message: str) -> None:
        """Default handler for critical errors - shows QMessageBox"""
        if self._show_dialogs and self._parent_widget is not None:
            QMessageBox.critical(self._parent_widget, title, message)

    def _show_warning_dialog(self, title: str, message: str) -> None:
        """Default handler for warnings - shows QMessageBox"""
        if self._show_dialogs and self._parent_widget is not None:
            QMessageBox.warning(self._parent_widget, title, message)

    def _show_info_dialog(self, title: str, message: str) -> None:
        """Default handler for info messages - shows QMessageBox"""
        if self._show_dialogs and self._parent_widget is not None:
            QMessageBox.information(self._parent_widget, title, message)


class _ErrorHandlerSingleton:
    """Thread-safe singleton holder for ErrorHandler."""
    _instance: ErrorHandler | None = None
    _lock = threading.Lock()

    @classmethod
    def get(cls, parent: QWidget | None = None) -> ErrorHandler:
        """Get or create the global error handler instance (thread-safe)"""
        # Fast path - check without lock
        if cls._instance is not None:
            if parent is not None and cls._instance._parent_widget is None:
                with cls._lock:
                    if cls._instance._parent_widget is None:
                        cls._instance._parent_widget = parent
                        cls._instance.setParent(parent)
            return cls._instance

        # Slow path - create with lock
        with cls._lock:
            # Double-check pattern
            if cls._instance is None:
                cls._instance = ErrorHandler(parent)
            return cls._instance

    @classmethod
    def reset(cls) -> None:
        """Reset the global error handler (useful for testing)"""
        with cls._lock:
            cls._instance = None


def get_error_handler(parent: QWidget | None = None) -> ErrorHandler:
    """Get or create the global error handler instance (thread-safe)"""
    return _ErrorHandlerSingleton.get(parent)


def reset_error_handler() -> None:
    """Reset the global error handler (useful for testing)"""
    _ErrorHandlerSingleton.reset()
