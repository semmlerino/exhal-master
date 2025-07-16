"""Input validation utilities for SpritePal security"""

import os
from pathlib import Path
from typing import Optional, Set

# Security constants
MAX_VRAM_SIZE = 65536  # 64KB - standard SNES VRAM size
MAX_CGRAM_SIZE = 512   # 512 bytes - standard SNES CGRAM size
MAX_OAM_SIZE = 544     # 544 bytes - standard SNES OAM size
MAX_IMAGE_SIZE = 10 * 1024 * 1024  # 10MB for PNG files
MAX_JSON_SIZE = 1 * 1024 * 1024    # 1MB for JSON files

# Allowed file extensions
VRAM_EXTENSIONS = {'.dmp', '.bin', '.vram'}
CGRAM_EXTENSIONS = {'.dmp', '.bin', '.cgram', '.pal'}
OAM_EXTENSIONS = {'.dmp', '.bin', '.oam'}
IMAGE_EXTENSIONS = {'.png'}
JSON_EXTENSIONS = {'.json'}


def validate_file_path(file_path: str, allowed_extensions: Optional[Set[str]] = None,
                      max_size: Optional[int] = None, base_dir: Optional[str] = None) -> tuple[bool, str]:
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
            
        # Check if it's a file (not directory)
        if not path.is_file():
            return False, f"Path is not a file: {file_path}"
        
        # Check extension if specified
        if allowed_extensions and path.suffix.lower() not in allowed_extensions:
            return False, f"Invalid file extension: {path.suffix}. Allowed: {allowed_extensions}"
        
        # Check file size if specified
        if max_size is not None:
            file_size = path.stat().st_size
            if file_size > max_size:
                return False, f"File too large: {file_size} bytes (max: {max_size})"
        
        # Check if within base directory if specified
        if base_dir:
            base = Path(base_dir).resolve()
            try:
                path.relative_to(base)
            except ValueError:
                return False, f"File is outside allowed directory: {base_dir}"
        
        return True, ""
        
    except Exception as e:
        return False, f"Path validation error: {str(e)}"


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


def validate_tile_count(count: int, max_count: int = 8192) -> tuple[bool, str]:
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
        filename = filename.replace(char, '_')
    
    # Remove leading/trailing dots and spaces
    filename = filename.strip('. ')
    
    # Ensure filename is not empty
    if not filename:
        filename = 'unnamed'
    
    return filename