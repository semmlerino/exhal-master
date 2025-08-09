"""
Safe logging utilities for test cleanup.

Prevents I/O errors during test teardown when logging handlers are closed.
"""

import logging
import sys


class SafeCleanupHandler(logging.Handler):
    """
    Logging handler that doesn't raise exceptions during cleanup.
    
    This handler silently ignores I/O errors that occur when
    logging after file handles have been closed.
    """

    def emit(self, record: logging.LogRecord) -> None:
        """Emit a log record, ignoring I/O errors."""
        try:
            # Try to format the message
            msg = self.format(record)

            # Try to write to stderr
            sys.stderr.write(msg + "\n")
            sys.stderr.flush()
        except (ValueError, OSError, AttributeError):
            # Silently ignore I/O errors during cleanup
            pass


class NullCleanupHandler(logging.Handler):
    """Handler that discards all messages during cleanup."""

    def emit(self, record: logging.LogRecord) -> None:
        """Discard the log record."""
        pass


def install_safe_cleanup_logging() -> None:
    """
    Replace all logging handlers with safe cleanup handlers.
    
    Call this at the start of test cleanup to prevent I/O errors.
    """
    root_logger = logging.getLogger()

    # Remove all existing handlers
    for handler in root_logger.handlers[:]:
        try:
            handler.close()
        except Exception:
            pass
        root_logger.removeHandler(handler)

    # Add safe cleanup handler
    root_logger.addHandler(SafeCleanupHandler())
    root_logger.setLevel(logging.WARNING)  # Only log warnings during cleanup


def install_null_logging() -> None:
    """
    Completely disable logging during cleanup.
    
    Use this for maximum safety during teardown.
    """
    root_logger = logging.getLogger()

    # Remove all existing handlers
    for handler in root_logger.handlers[:]:
        try:
            handler.close()
        except Exception:
            pass
        root_logger.removeHandler(handler)

    # Add null handler
    root_logger.addHandler(NullCleanupHandler())
