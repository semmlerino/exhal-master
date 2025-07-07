"""
Simplified security utilities for personal project
Minimal validation to prevent obvious issues
"""

import pathlib
from pathlib import Path

class SecurityError(Exception):
    """Security-related errors"""
    pass

def validate_file_path(file_path, base_dir=None, max_size=10 * 1024 * 1024):
    """
    Basic file path validation for personal project
    
    Args:
        file_path: Path to validate
        base_dir: Optional base directory to restrict access to
        max_size: Maximum allowed file size in bytes (default 10MB)
        
    Returns:
        Absolute path if valid
        
    Raises:
        SecurityError: If path has obvious issues
    """
    file_path_str = str(file_path)
    
    # Check for null bytes
    if '\0' in file_path_str:
        raise SecurityError("Null bytes in path")
    
    # Convert to Path object
    try:
        path = pathlib.Path(file_path).resolve()
    except (ValueError, RuntimeError) as e:
        raise SecurityError(f"Invalid path: {e}")
    
    # If base_dir is specified, ensure path is within it
    if base_dir:
        base = pathlib.Path(base_dir).resolve()
        try:
            path.relative_to(base)
        except ValueError:
            raise SecurityError(f"Path outside allowed directory: {path}")
    
    # Check if path exists and is a file
    if path.exists():
        if not path.is_file():
            raise SecurityError(f"Path is not a file: {path}")
        
        # Check file size
        file_size = path.stat().st_size
        if file_size > max_size:
            raise SecurityError(f"File too large: {file_size} bytes (max {max_size})")
    
    return str(path)

def validate_output_path(file_path, base_dir=None):
    """
    Basic output path validation for personal project
    
    Args:
        file_path: Path to validate
        base_dir: Optional base directory to restrict access to
        
    Returns:
        Absolute path if valid
        
    Raises:
        SecurityError: If path has obvious issues
    """
    file_path_str = str(file_path)
    
    # Check for null bytes
    if '\0' in file_path_str:
        raise SecurityError("Null bytes in path")
    
    # Convert to Path object
    try:
        path = pathlib.Path(file_path).resolve()
    except (ValueError, RuntimeError) as e:
        raise SecurityError(f"Invalid path: {e}")
    
    # Ensure parent directory exists
    parent = path.parent
    if not parent.exists():
        raise SecurityError(f"Parent directory does not exist: {parent}")
    
    # If base_dir is specified, ensure path is within it
    if base_dir:
        base = pathlib.Path(base_dir).resolve()
        try:
            path.relative_to(base)
        except ValueError:
            raise SecurityError(f"Path outside allowed directory: {path}")
    
    # Check if path already exists and is a directory
    if path.exists() and path.is_dir():
        raise SecurityError(f"Path is a directory: {path}")
    
    return str(path)