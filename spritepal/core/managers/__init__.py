"""
Manager classes for SpritePal business logic
"""

from .base_manager import BaseManager
from .exceptions import (
    ExtractionError,
    FileOperationError,
    InjectionError,
    ManagerError,
    PreviewError,
    SessionError,
    ValidationError,
)
from .extraction_manager import ExtractionManager
from .injection_manager import InjectionManager
from .registry import (
    are_managers_initialized,
    cleanup_managers,
    get_extraction_manager,
    get_injection_manager,
    get_registry,
    get_session_manager,
    initialize_managers,
    validate_manager_dependencies,
)
from .session_manager import SessionManager

__all__ = [
    # Base classes
    "BaseManager",
    "ExtractionError",
    # Managers
    "ExtractionManager",
    "FileOperationError",
    "InjectionError",
    "InjectionManager",
    # Exceptions
    "ManagerError",
    "PreviewError",
    "SessionError",
    "SessionManager",
    "ValidationError",
    "are_managers_initialized",
    "cleanup_managers",
    "get_extraction_manager",
    "get_injection_manager",
    # Registry functions
    "get_registry",
    "get_session_manager",
    "initialize_managers",
    "validate_manager_dependencies",
]
