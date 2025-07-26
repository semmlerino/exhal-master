"""
Custom exceptions for manager classes
"""


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
