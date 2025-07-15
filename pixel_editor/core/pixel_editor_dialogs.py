#!/usr/bin/env python3
"""
Dialog utilities for the pixel editor.

Provides consistent error and information dialogs using PyQt6.
"""

from typing import Optional

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QMessageBox, QWidget

from .pixel_editor_exceptions import (
    FileOperationError,
    ImageFormatError,
    PaletteError,
    ResourceError,
    ToolError,
    ValidationError,
)


def show_error_dialog(
    parent: Optional[QWidget],
    title: str,
    message: str,
    details: Optional[str] = None,
) -> None:
    """
    Show an error dialog with an optional details section.
    
    Args:
        parent: Parent widget for the dialog
        title: Dialog title
        message: Main error message
        details: Optional detailed error information
    """
    msg_box = QMessageBox(parent)
    msg_box.setIcon(QMessageBox.Icon.Critical)
    msg_box.setWindowTitle(title)
    msg_box.setText(message)
    
    if details:
        msg_box.setDetailedText(details)
    
    msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
    msg_box.exec()


def show_warning_dialog(
    parent: Optional[QWidget],
    title: str,
    message: str,
) -> None:
    """
    Show a warning dialog.
    
    Args:
        parent: Parent widget for the dialog
        title: Dialog title
        message: Warning message
    """
    QMessageBox.warning(parent, title, message)


def show_info_dialog(
    parent: Optional[QWidget],
    title: str,
    message: str,
) -> None:
    """
    Show an information dialog.
    
    Args:
        parent: Parent widget for the dialog
        title: Dialog title
        message: Information message
    """
    QMessageBox.information(parent, title, message)


def show_exception_dialog(
    parent: Optional[QWidget],
    operation: str,
    exception: Exception,
) -> None:
    """
    Show an error dialog for an exception with appropriate formatting.
    
    Args:
        parent: Parent widget for the dialog
        operation: Description of the operation that failed
        exception: The exception that was raised
    """
    # Determine title based on exception type
    if isinstance(exception, FileOperationError):
        title = "File Operation Error"
    elif isinstance(exception, PaletteError):
        title = "Palette Error"
    elif isinstance(exception, ImageFormatError):
        title = "Image Format Error"
    elif isinstance(exception, ValidationError):
        title = "Invalid Input"
    elif isinstance(exception, ResourceError):
        title = "Resource Error"
    elif isinstance(exception, ToolError):
        title = "Tool Error"
    elif isinstance(exception, PermissionError):
        title = "Permission Denied"
    elif isinstance(exception, FileNotFoundError):
        title = "File Not Found"
    elif isinstance(exception, MemoryError):
        title = "Out of Memory"
    else:
        title = "Error"
    
    # Format message
    message = f"Failed to {operation}"
    
    # Get exception details
    details = str(exception)
    if hasattr(exception, '__cause__') and exception.__cause__:
        details += f"\n\nCaused by: {exception.__cause__}"
    
    show_error_dialog(parent, title, message, details)


def ask_yes_no_dialog(
    parent: Optional[QWidget],
    title: str,
    message: str,
) -> bool:
    """
    Show a yes/no question dialog.
    
    Args:
        parent: Parent widget for the dialog
        title: Dialog title
        message: Question message
        
    Returns:
        True if user clicked Yes, False otherwise
    """
    reply = QMessageBox.question(
        parent,
        title,
        message,
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        QMessageBox.StandardButton.No
    )
    return reply == QMessageBox.StandardButton.Yes


def ask_save_changes_dialog(
    parent: Optional[QWidget],
    filename: str = "Untitled",
) -> QMessageBox.StandardButton:
    """
    Show a save changes dialog with Save, Don't Save, and Cancel options.
    
    Args:
        parent: Parent widget for the dialog
        filename: Name of the file with unsaved changes
        
    Returns:
        The button that was clicked
    """
    msg_box = QMessageBox(parent)
    msg_box.setIcon(QMessageBox.Icon.Warning)
    msg_box.setWindowTitle("Unsaved Changes")
    msg_box.setText(f"Do you want to save changes to {filename}?")
    msg_box.setInformativeText("Your changes will be lost if you don't save them.")
    
    msg_box.setStandardButtons(
        QMessageBox.StandardButton.Save |
        QMessageBox.StandardButton.Discard |
        QMessageBox.StandardButton.Cancel
    )
    msg_box.setDefaultButton(QMessageBox.StandardButton.Save)
    
    return msg_box.exec()