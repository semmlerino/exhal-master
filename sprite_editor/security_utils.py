#!/usr/bin/env python3
"""
Security utilities for safe file operations
"""

import pathlib

class SecurityError(Exception):
    """Raised when a security violation is detected"""
    pass

def _check_path_format(file_path_str):
    """Common path format checks for both input and output paths"""
    # Check for URI schemes
    if any(file_path_str.startswith(scheme) for scheme in ["file:", "http:", "https:", "ftp:", "sftp:"]):
        raise SecurityError(f"URI schemes not allowed: {file_path_str}")

    # Check for UNC paths
    if file_path_str.startswith("\\\\") or "\\\\?\\" in file_path_str:
        raise SecurityError(f"UNC paths not allowed: {file_path_str}")

    # Check for Windows-style paths (C:\ etc)
    if len(file_path_str) >= 3 and file_path_str[1:3] == ':\\':
        raise SecurityError(f"Windows-style paths not allowed: {file_path_str}")

    # Check for path traversal attempts
    if ".." in file_path_str or "~" in file_path_str:
        raise SecurityError("Path traversal attempt detected")

def validate_file_path(file_path, base_dir=None, max_size=10 * 1024 * 1024):
    """
    Validate a file path for security issues

    Args:
        file_path: Path to validate
        base_dir: Optional base directory to restrict access to
        max_size: Maximum allowed file size in bytes (default 10MB)

    Returns:
        Absolute path if valid

    Raises:
        SecurityError: If path is invalid or unsafe
    """
    # Perform common path format checks
    file_path_str = str(file_path)
    _check_path_format(file_path_str)

    # Convert to Path object for better handling
    try:
        path = pathlib.Path(file_path).resolve()
    except (ValueError, RuntimeError) as e:
        raise SecurityError(f"Invalid path: {e}")

    # Check for attempts to access system directories
    protected_patterns = [
        "/etc/", "/usr/", "/bin/", "/sbin/", "/lib/", "/sys/", "/proc/",
        "/System/", "C:\\Windows\\", "C:\\Program Files\\", "/dev/"
    ]
    path_str = str(path).replace("\\", "/")
    for pattern in protected_patterns:
        if path_str.startswith(pattern) or pattern in path_str:
            raise SecurityError(f"Access to system directories not allowed: {path}")

    # If base_dir is specified, ensure path is within it
    if base_dir:
        base = pathlib.Path(base_dir).resolve()
        try:
            path.relative_to(base)
        except ValueError:
            raise SecurityError(f"Path outside allowed directory: {path}")

    # Check if path exists and is a file (not directory)
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
    Validate an output file path for security issues

    Args:
        file_path: Path to validate
        base_dir: Optional base directory to restrict access to

    Returns:
        Absolute path if valid

    Raises:
        SecurityError: If path is invalid or unsafe
    """
    # Perform common path format checks
    file_path_str = str(file_path)
    _check_path_format(file_path_str)

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

    # Ensure parent directory exists
    if not path.parent.exists():
        raise SecurityError(f"Parent directory does not exist: {path.parent}")

    # Check if we're trying to overwrite a system file
    if path.exists():
        # List of protected file patterns
        protected_patterns = [
            "/etc/", "/usr/", "/bin/", "/sbin/", "/lib/",
            "/System/", "C:\\Windows\\", "C:\\Program Files\\"
        ]
        path_str = str(path).replace("\\", "/")
        for pattern in protected_patterns:
            if pattern in path_str:
                raise SecurityError(f"Cannot overwrite system file: {path}")

    return str(path)

def safe_file_size(file_path):
    """
    Safely get file size with validation

    Args:
        file_path: Path to check

    Returns:
        File size in bytes

    Raises:
        SecurityError: If file is invalid
    """
    path = pathlib.Path(file_path)
    if not path.exists():
        raise SecurityError(f"File does not exist: {path}")
    if not path.is_file():
        raise SecurityError(f"Not a file: {path}")

    return path.stat().st_size