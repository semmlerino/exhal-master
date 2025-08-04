"""
Integration utilities for unified error handling.

This module provides decorators and utilities that integrate the UnifiedErrorHandler
with existing error handling patterns, maintaining backward compatibility while
providing enhanced error processing capabilities.
"""

from __future__ import annotations

from functools import wraps
from typing import TYPE_CHECKING, Any, Callable, Optional

if TYPE_CHECKING:
    from PyQt6.QtWidgets import QWidget

from utils.unified_error_handler import (
    ErrorCategory,
    ErrorContext,
    UnifiedErrorHandler,
    get_unified_error_handler,
)


def enhanced_handle_worker_errors(
    operation_context: str = "operation",
    handle_interruption: bool = False,
    include_runtime_error: bool = False,
    error_handler: Optional[UnifiedErrorHandler] = None
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """
    Enhanced version of @handle_worker_errors that uses UnifiedErrorHandler.
    
    This decorator provides the same interface as the original but adds
    comprehensive error categorization, recovery suggestions, and standardized
    error processing through the UnifiedErrorHandler.
    
    Args:
        operation_context: Context string for error messages
        handle_interruption: If True, handles InterruptedError instead of re-raising
        include_runtime_error: If True, adds RuntimeError to the handled exceptions
        error_handler: Custom error handler instance (uses global if None)
        
    Returns:
        Decorated function with enhanced error handling
    """
    if error_handler is None:
        error_handler = get_unified_error_handler()
    
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        def wrapper(self: Any, *args: Any, **kwargs: Any) -> Any:
            worker_name = getattr(self, '_operation_name', self.__class__.__name__)
            
            with error_handler.error_context(
                operation_context,
                component=worker_name,
                recovery_possible=True
            ) as context:
                try:
                    return func(self, *args, **kwargs)
                    
                except InterruptedError as e:
                    if handle_interruption:
                        result = error_handler.handle_worker_error(
                            e, worker_name, operation_context
                        )
                        # Emit operation finished signal if available
                        if hasattr(self, 'operation_finished'):
                            self.operation_finished.emit(False, "Operation cancelled")
                        return None
                    else:
                        # Re-raise for base class handling
                        raise
                        
                except (OSError, IOError, PermissionError) as e:
                    # Handle file I/O errors
                    context.file_path = getattr(self, '_current_file', None)
                    error_handler.handle_file_error(
                        e, context.file_path or "unknown", operation_context,
                        component=worker_name
                    )
                    # Don't emit signals for specific errors - just log
                    
                except (ValueError, TypeError) as e:
                    # Handle validation errors - these will be converted to ValidationError
                    # automatically by handle_validation_error
                    error_handler.handle_validation_error(
                        e, operation_context, component=worker_name
                    )
                    # Don't emit signals for specific errors - just log
                    
                except RuntimeError as e:
                    if include_runtime_error:
                        error_handler.handle_worker_error(
                            e, worker_name, operation_context
                        )
                        # Don't emit signals for specific errors - just log
                    else:
                        raise
                        
                except Exception as e:
                    # Handle all other exceptions with full error processing
                    result = error_handler.handle_worker_error(
                        e, worker_name, operation_context
                    )
                    
                    # Emit error signal if available
                    if hasattr(self, 'error'):
                        self.error.emit(result.message, e)
                    
                    # Don't re-raise - let the worker handle the error state
                    
        return wrapper
    return decorator


def qt_error_handler(
    operation: str,
    component: Optional[str] = None,
    error_handler: Optional[UnifiedErrorHandler] = None
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """
    Decorator for Qt GUI operations with enhanced error handling.
    
    Usage:
        @qt_error_handler("updating UI", "MainWindow")
        def update_display(self):
            # Qt operations that might fail
            pass
    """
    if error_handler is None:
        error_handler = get_unified_error_handler()
    
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        def wrapper(self: Any, *args: Any, **kwargs: Any) -> Any:
            comp_name = component or getattr(self, '__class__', {}).get('__name__', 'Unknown')
            
            try:
                return func(self, *args, **kwargs)
            except Exception as e:
                error_handler.handle_qt_error(
                    e, comp_name, operation
                )
                # For Qt errors, we typically want to continue execution
                return None
                
        return wrapper
    return decorator


def file_operation_handler(
    operation: str,
    file_path_attr: str = "file_path",
    error_handler: Optional[UnifiedErrorHandler] = None
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """
    Decorator for file operations with enhanced error handling.
    
    Args:
        operation: Description of the file operation
        file_path_attr: Attribute name or method to get file path from self
        error_handler: Custom error handler instance
        
    Usage:
        @file_operation_handler("loading configuration", "config_file")
        def load_config(self):
            # File operations that might fail
            pass
    """
    if error_handler is None:
        error_handler = get_unified_error_handler()
    
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        def wrapper(self: Any, *args: Any, **kwargs: Any) -> Any:
            # Get file path from object
            file_path = "unknown"
            if hasattr(self, file_path_attr):
                path_value = getattr(self, file_path_attr)
                file_path = str(path_value) if path_value else "unknown"
            
            try:
                return func(self, *args, **kwargs)
            except Exception as e:
                result = error_handler.handle_file_error(
                    e, file_path, operation
                )
                
                # Re-raise critical errors
                if result.should_abort:
                    raise
                    
                return None
                
        return wrapper
    return decorator


def validation_handler(
    operation: str,
    input_attr: Optional[str] = None,
    error_handler: Optional[UnifiedErrorHandler] = None
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """
    Decorator for input validation with enhanced error handling.
    
    This decorator automatically converts any exception to ValidationError
    through the UnifiedErrorHandler.handle_validation_error method,
    ensuring type safety and consistent error handling.
    
    Args:
        operation: Description of the validation operation
        input_attr: Attribute name to get user input from self
        error_handler: Custom error handler instance
        
    Usage:
        @validation_handler("validating ROM parameters", "rom_params")
        def validate_rom(self):
            # Validation logic that might fail
            pass
    """
    if error_handler is None:
        error_handler = get_unified_error_handler()
    
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        def wrapper(self: Any, *args: Any, **kwargs: Any) -> Any:
            # Get user input if available
            user_input = None
            if input_attr and hasattr(self, input_attr):
                input_value = getattr(self, input_attr)
                user_input = str(input_value) if input_value else None
            
            try:
                return func(self, *args, **kwargs)
            except Exception as e:
                error_handler.handle_validation_error(
                    e, operation, user_input
                )
                # Validation errors typically shouldn't continue
                return False
                
        return wrapper
    return decorator


class ErrorHandlerMixin:
    """
    Mixin class that provides error handling capabilities to any class.
    
    Usage:
        class MyWidget(QWidget, ErrorHandlerMixin):
            def __init__(self):
                super().__init__()
                self.setup_error_handling()
                
            def risky_operation(self):
                with self.error_context("performing risky operation"):
                    # Code that might fail
                    pass
    """
    
    def setup_error_handling(self, parent: Optional[QWidget] = None) -> None:
        """Setup error handling for this instance"""
        self._error_handler = get_unified_error_handler(parent)
    
    def error_context(self, operation: str, **kwargs: Any):
        """Convenient access to error context manager"""
        if not hasattr(self, '_error_handler'):
            self.setup_error_handling()
        return self._error_handler.error_context(operation, **kwargs)
    
    def handle_error(self, error: Exception, operation: str, **kwargs: Any):
        """Convenient error handling method"""
        if not hasattr(self, '_error_handler'):
            self.setup_error_handling()
        
        context = ErrorContext(operation=operation, **kwargs)
        return self._error_handler.handle_exception(error, context)
    
    def get_error_statistics(self) -> dict[str, Any]:
        """Get error statistics for this component"""
        if not hasattr(self, '_error_handler'):
            return {}
        return self._error_handler.get_error_statistics()


# Utility functions for common patterns

def create_safe_method(
    method: Callable,
    operation: str,
    default_return: Any = None,
    error_handler: Optional[UnifiedErrorHandler] = None
) -> Callable:
    """
    Create a safe version of a method that handles all errors.
    
    Usage:
        safe_extract = create_safe_method(
            extractor.extract_sprites,
            "extracting sprites",
            default_return=[]
        )
        sprites = safe_extract(rom_data)
    """
    if error_handler is None:
        error_handler = get_unified_error_handler()
    
    @wraps(method)
    def safe_wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            return method(*args, **kwargs)
        except Exception as e:
            context = ErrorContext(
                operation=operation,
                component=method.__name__
            )
            result = error_handler.handle_exception(e, context)
            
            if result.should_abort:
                raise
                
            return default_return
    
    return safe_wrapper


def batch_error_handler(
    operations: list[tuple[Callable, str]],
    continue_on_error: bool = True,
    error_handler: Optional[UnifiedErrorHandler] = None
) -> list[tuple[bool, Any]]:
    """
    Execute multiple operations with unified error handling.
    
    Args:
        operations: List of (function, operation_name) tuples
        continue_on_error: Whether to continue after errors
        error_handler: Custom error handler
        
    Returns:
        List of (success, result) tuples
    """
    if error_handler is None:
        error_handler = get_unified_error_handler()
    
    results = []
    
    for func, operation_name in operations:
        try:
            result = func()
            results.append((True, result))
        except Exception as e:
            context = ErrorContext(
                operation=operation_name,
                component=func.__name__
            )
            error_result = error_handler.handle_exception(e, context)
            
            results.append((False, error_result))
            
            if not continue_on_error or error_result.should_abort:
                break
    
    return results