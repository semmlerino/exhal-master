"""Input validation utilities for SpritePal security"""

import os
from pathlib import Path

# Security constants
from utils.constants import (
    CGRAM_EXPECTED_SIZE as MAX_CGRAM_SIZE,
    MAX_IMAGE_SIZE,
    MAX_JSON_SIZE,
    MAX_TILE_COUNT_DEFAULT,
    OAM_EXPECTED_SIZE as MAX_OAM_SIZE,
    VRAM_MIN_SIZE as MAX_VRAM_SIZE,  # Standard VRAM size is 64KB
)

# Allowed file extensions
VRAM_EXTENSIONS = {".dmp", ".bin", ".vram"}
CGRAM_EXTENSIONS = {".dmp", ".bin", ".cgram", ".pal"}
OAM_EXTENSIONS = {".dmp", ".bin", ".oam"}
IMAGE_EXTENSIONS = {".png"}
JSON_EXTENSIONS = {".json"}


def validate_file_path(
    file_path: str,
    allowed_extensions: set[str] | None = None,
    max_size: int | None = None,
    base_dir: str | None = None,
) -> tuple[bool, str]:
    """
    Validate a file path for security and constraints.

    Args:
        file_path: Path to validate
        allowed_extensions: Set of allowed file extensions (with dots)
        max_size: Maximum allowed file size in bytes
        base_dir: If provided, ensure file is within this directory

    Returns:
        Tuple of (is_valid, error_message)
    """
    try:
        path = Path(file_path).resolve()

        # Check if file exists
        if not path.exists():
            return True, ""  # Non-existent files are OK, will be handled by caller

        # Perform all validation checks
        error_msg = _validate_path_properties(path, file_path, allowed_extensions, max_size, base_dir)
        if error_msg:
            return False, error_msg

    except Exception as e:
        return False, f"Path validation error: {e!s}"

    return True, ""


def _validate_path_properties(
    path: Path,
    file_path: str,
    allowed_extensions: set[str] | None,
    max_size: int | None,
    base_dir: str | None
) -> str:
    """Helper function to validate path properties. Returns error message or empty string."""
    # Check if it's a file (not directory)
    if not path.is_file():
        return f"Path is not a file: {file_path}"

    # Check extension if specified
    if allowed_extensions and path.suffix.lower() not in allowed_extensions:
        return f"Invalid file extension: {path.suffix}. Allowed: {allowed_extensions}"

    # Check file size if specified
    if max_size is not None:
        file_size = path.stat().st_size
        if file_size > max_size:
            return f"File too large: {file_size} bytes (max: {max_size})"

    # Check if within base directory if specified
    if base_dir:
        base = Path(base_dir).resolve()
        try:
            _ = path.relative_to(base)
        except ValueError:
            return f"File is outside allowed directory: {base_dir}"

    return ""


def validate_vram_file(file_path: str) -> tuple[bool, str]:
    """Validate a VRAM dump file."""
    return validate_file_path(file_path, VRAM_EXTENSIONS, MAX_VRAM_SIZE)


def validate_cgram_file(file_path: str) -> tuple[bool, str]:
    """Validate a CGRAM dump file."""
    return validate_file_path(file_path, CGRAM_EXTENSIONS, MAX_CGRAM_SIZE)


def validate_oam_file(file_path: str) -> tuple[bool, str]:
    """Validate an OAM dump file."""
    return validate_file_path(file_path, OAM_EXTENSIONS, MAX_OAM_SIZE)


def validate_image_file(file_path: str) -> tuple[bool, str]:
    """Validate an image file."""
    return validate_file_path(file_path, IMAGE_EXTENSIONS, MAX_IMAGE_SIZE)


def validate_json_file(file_path: str) -> tuple[bool, str]:
    """Validate a JSON file."""
    return validate_file_path(file_path, JSON_EXTENSIONS, MAX_JSON_SIZE)


def validate_offset(offset: int, max_offset: int) -> tuple[bool, str]:
    """Validate an offset value."""
    if offset < 0:
        return False, f"Offset cannot be negative: {offset}"
    if offset >= max_offset:
        return False, f"Offset {offset} exceeds maximum: {max_offset}"
    return True, ""


def validate_tile_count(count: int, max_count: int = MAX_TILE_COUNT_DEFAULT) -> tuple[bool, str]:
    """Validate tile count to prevent excessive memory usage."""
    if count < 0:
        return False, f"Tile count cannot be negative: {count}"
    if count > max_count:
        return False, f"Tile count {count} exceeds maximum: {max_count}"
    return True, ""


def sanitize_filename(filename: str) -> str:
    """
    Sanitize a filename for safe file operations.
    Removes directory traversal attempts and invalid characters.
    """
    # Remove directory separators
    filename = os.path.basename(filename)

    # Remove potentially dangerous characters
    invalid_chars = '<>:"|?*\x00'
    for char in invalid_chars:
        filename = filename.replace(char, "_")

    # Remove leading/trailing dots and spaces
    filename = filename.strip(". ")

    # Ensure filename is not empty
    if not filename:
        filename = "unnamed"

    return filename
