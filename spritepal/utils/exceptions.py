"""Custom exceptions for SpritePal"""


class SpritePalError(Exception):
    """Base exception for all SpritePal errors."""
    pass


class VRAMError(SpritePalError):
    """Raised for VRAM-related errors."""
    pass


class CGRAMError(SpritePalError):
    """Raised for CGRAM/palette-related errors."""
    pass


class OAMError(SpritePalError):
    """Raised for OAM-related errors."""
    pass


class ExtractionError(SpritePalError):
    """Raised for sprite extraction errors."""
    pass


class InjectionError(SpritePalError):
    """Raised for sprite injection errors."""
    pass


class ValidationError(SpritePalError):
    """Raised for validation errors."""
    pass


class FileFormatError(SpritePalError):
    """Raised for unsupported or invalid file formats."""
    pass


class TileError(SpritePalError):
    """Raised for tile processing errors."""
    pass