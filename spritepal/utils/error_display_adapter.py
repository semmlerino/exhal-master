"""
Adapter to connect UI error handlers to the unified error handler.

This module breaks the circular dependency between unified_error_handler.py
and ui.common.error_handler.py by providing an adapter that implements
the IErrorDisplay protocol.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ui.common.error_handler import ErrorHandler


class ErrorHandlerAdapter:
    """
    Adapter that wraps ui.common.error_handler.ErrorHandler to implement
    the IErrorDisplay protocol for the unified error handler.

    This breaks the circular dependency by allowing the UI layer to
    inject its error handler into the utils layer without direct imports.
    """

    def __init__(self, error_handler: ErrorHandler):
        """Initialize the adapter with a UI error handler"""
        self._error_handler = error_handler

    def handle_critical_error(self, title: str, message: str) -> None:
        """Forward critical errors to the UI error handler"""
        self._error_handler.handle_critical_error(title, message)

    def handle_warning(self, title: str, message: str) -> None:
        """Forward warnings to the UI error handler"""
        self._error_handler.handle_warning(title, message)

    def handle_info(self, title: str, message: str) -> None:
        """Forward info messages to the UI error handler"""
        self._error_handler.handle_info(title, message)
