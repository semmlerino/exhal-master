"""
Custom exceptions for manager classes
"""
# No imports needed for basic exceptions


class ManagerError(Exception):
    """Base exception for all manager-related errors"""


class ExtractionError(ManagerError):
    """Exception raised during extraction operations"""


class SessionError(ManagerError):
    """Exception raised during session/settings operations"""


class ValidationError(ManagerError):
    """Exception raised when parameter validation fails"""


class InjectionError(ManagerError):
    """Exception raised during injection operations"""


class PreviewError(ManagerError):
    """Exception raised during preview generation"""


class FileOperationError(ManagerError):
    """Exception raised during file operations"""


class CacheError(ManagerError):
    """Exception raised during cache operations"""

    def __init__(self, message: str, cache_path: str | None = None):
        super().__init__(message)
        self.cache_path = cache_path


class CacheCorruptionError(CacheError):
    """Exception raised when cache database is corrupted"""


class CachePermissionError(CacheError):
    """Exception raised when cache access is denied due to permissions"""


class NavigationError(ManagerError):
    """Exception raised during navigation operations"""
