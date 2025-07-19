"""Custom exceptions for SpritePal"""


class SpritePalError(Exception):
    """Base exception for all SpritePal errors."""


class VRAMError(SpritePalError):
    """Raised for VRAM-related errors."""


class CGRAMError(SpritePalError):
    """Raised for CGRAM/palette-related errors."""


class OAMError(SpritePalError):
    """Raised for OAM-related errors."""


class ExtractionError(SpritePalError):
    """Raised for sprite extraction errors."""


class InjectionError(SpritePalError):
    """Raised for sprite injection errors."""


class ValidationError(SpritePalError):
    """Raised for validation errors."""


class FileFormatError(SpritePalError):
    """Raised for unsupported or invalid file formats."""


class TileError(SpritePalError):
    """Raised for tile processing errors."""
