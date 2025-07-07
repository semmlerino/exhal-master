#!/usr/bin/env python3
"""
Base worker class for threaded operations
Provides common functionality for all worker threads
"""

from PyQt6.QtCore import QThread, pyqtSignal


class BaseWorker(QThread):
    """Base class for worker threads with common signals and error handling"""
    
    # Common signals
    progress = pyqtSignal(str)  # Progress message
    error = pyqtSignal(str)     # Error message
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._is_cancelled = False
    
    def cancel(self):
        """Request cancellation of the worker thread"""
        self._is_cancelled = True
    
    def is_cancelled(self):
        """Check if cancellation was requested"""
        return self._is_cancelled
    
    def emit_progress(self, message):
        """Emit a progress message if not cancelled"""
        if not self.is_cancelled():
            self.progress.emit(message)
    
    def emit_error(self, error_message):
        """Emit an error message"""
        self.error.emit(error_message)
    
    def handle_exception(self, exception):
        """
        Handle an exception by emitting it as an error
        
        Args:
            exception: The exception to handle
        """
        self.emit_error(str(exception))