#!/usr/bin/env python3
"""
Custom exceptions and error handling utilities for the pixel editor.

This module defines domain-specific exceptions and provides utilities
for consistent error handling across the application.
"""


class PixelEditorError(Exception):
    """Base exception for all pixel editor errors"""
    pass


class FileOperationError(PixelEditorError):
    """Raised when file operations fail"""
    pass


class PaletteError(PixelEditorError):
    """Raised when palette operations fail"""
    pass


class ImageFormatError(FileOperationError):
    """Raised when image format is invalid or unsupported"""
    pass


class ToolError(PixelEditorError):
    """Raised when tool operations fail"""
    pass


class ValidationError(PixelEditorError):
    """Raised when input validation fails"""
    pass


class ResourceError(PixelEditorError):
    """Raised when system resources are exhausted"""
    pass


def format_error_message(operation: str, error: Exception) -> str:
    """
    Format an error message for user display.
    
    Args:
        operation: Description of the operation that failed
        error: The exception that was raised
        
    Returns:
        User-friendly error message
    """
    error_type = type(error).__name__
    
    # Map specific error types to user-friendly messages
    if isinstance(error, FileNotFoundError):
        return f"File not found during {operation}"
    elif isinstance(error, PermissionError):
        return f"Permission denied during {operation}"
    elif isinstance(error, MemoryError):
        return f"Out of memory during {operation}"
    elif isinstance(error, OSError) and error.errno == 28:  # No space left
        return f"Disk full - cannot complete {operation}"
    elif isinstance(error, ImageFormatError):
        return f"Invalid image format: {error}"
    elif isinstance(error, PaletteError):
        return f"Palette error: {error}"
    elif isinstance(error, ValidationError):
        return f"Invalid input: {error}"
    else:
        # Generic message for unexpected errors
        return f"Failed to {operation}: {error}"