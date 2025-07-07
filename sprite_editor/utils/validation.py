#!/usr/bin/env python3
"""
Input validation utilities
Provides common validation functions for user input
"""

from typing import Tuple, List, Optional


class ValidationError(Exception):
    """Custom exception for validation errors"""
    pass


class Validators:
    """Common validation functions"""
    
    @staticmethod
    def validate_hex_value(value_str: str, min_val: int = 0, 
                          max_val: Optional[int] = None) -> Tuple[bool, int, str]:
        """
        Validate a hexadecimal string value
        
        Args:
            value_str: String to validate
            min_val: Minimum allowed value
            max_val: Maximum allowed value (optional)
            
        Returns:
            Tuple of (is_valid, parsed_value, error_message)
        """
        try:
            # Remove whitespace
            value_str = value_str.strip()
            
            # Parse hex value
            if value_str.startswith('0x') or value_str.startswith('0X'):
                value = int(value_str, 16)
            else:
                # Try to parse as hex even without prefix
                value = int(value_str, 16)
            
            # Check range
            if value < min_val:
                return False, 0, f"Value must be at least 0x{min_val:X}"
            
            if max_val is not None and value > max_val:
                return False, 0, f"Value must not exceed 0x{max_val:X}"
            
            return True, value, ""
            
        except ValueError:
            return False, 0, "Invalid hexadecimal value"
    
    @staticmethod
    def validate_offset(offset: int, file_size: int) -> Tuple[bool, str]:
        """
        Validate an offset within a file
        
        Args:
            offset: Offset to validate
            file_size: Size of the file
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if offset < 0:
            return False, "Offset cannot be negative"
        
        if offset >= file_size:
            return False, f"Offset 0x{offset:X} exceeds file size (0x{file_size:X})"
        
        return True, ""
    
    @staticmethod
    def validate_size(size: int, available: int) -> Tuple[bool, str]:
        """
        Validate a size value
        
        Args:
            size: Size to validate
            available: Available space
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if size <= 0:
            return False, "Size must be greater than 0"
        
        if size > available:
            return False, f"Size 0x{size:X} exceeds available space (0x{available:X})"
        
        return True, ""
    
    @staticmethod
    def validate_tile_count(count: int, max_tiles: int = 65536) -> Tuple[bool, str]:
        """
        Validate tile count
        
        Args:
            count: Number of tiles
            max_tiles: Maximum allowed tiles
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if count <= 0:
            return False, "Tile count must be greater than 0"
        
        if count > max_tiles:
            return False, f"Tile count {count} exceeds maximum ({max_tiles})"
        
        return True, ""
    
    @staticmethod
    def validate_extraction_params(offset: int, size: int, 
                                 file_size: int) -> List[str]:
        """
        Validate extraction parameters
        
        Args:
            offset: Extraction offset
            size: Extraction size
            file_size: Total file size
            
        Returns:
            List of validation errors (empty if valid)
        """
        errors = []
        
        # Validate offset
        valid, error = Validators.validate_offset(offset, file_size)
        if not valid:
            errors.append(error)
        
        # Validate size
        available = file_size - offset if offset < file_size else 0
        valid, error = Validators.validate_size(size, available)
        if not valid:
            errors.append(error)
        
        # Check tile alignment
        if size % 32 != 0:
            errors.append(f"Size must be multiple of 32 bytes (tile size)")
        
        return errors
    
    @staticmethod
    def validate_png_dimensions(width: int, height: int) -> List[str]:
        """
        Validate PNG dimensions for SNES compatibility
        
        Args:
            width: Image width
            height: Image height
            
        Returns:
            List of validation errors (empty if valid)
        """
        errors = []
        
        if width <= 0 or height <= 0:
            errors.append("Invalid image dimensions")
            return errors
        
        if width % 8 != 0:
            errors.append(f"Width ({width}) must be multiple of 8")
        
        if height % 8 != 0:
            errors.append(f"Height ({height}) must be multiple of 8")
        
        # Check reasonable limits
        if width > 1024 or height > 1024:
            errors.append("Image dimensions exceed reasonable limits (1024x1024)")
        
        return errors
    
    @staticmethod
    def validate_palette_index(index: int) -> Tuple[bool, str]:
        """
        Validate a palette index
        
        Args:
            index: Palette index
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if index < 0:
            return False, "Palette index cannot be negative"
        
        if index >= 16:
            return False, "Palette index must be 0-15"
        
        return True, ""


class InputSanitizer:
    """Sanitize user input"""
    
    @staticmethod
    def sanitize_filename(filename: str, default: str = "output") -> str:
        """
        Sanitize a filename for safe file operations
        
        Args:
            filename: Filename to sanitize
            default: Default name if invalid
            
        Returns:
            Sanitized filename
        """
        if not filename:
            return default
        
        # Remove path separators
        filename = filename.replace('/', '_').replace('\\', '_')
        
        # Remove other problematic characters
        invalid_chars = '<>:"|?*'
        for char in invalid_chars:
            filename = filename.replace(char, '_')
        
        # Remove leading/trailing dots and spaces
        filename = filename.strip('. ')
        
        # Ensure not empty
        if not filename:
            return default
        
        return filename
    
    @staticmethod
    def sanitize_hex_input(hex_str: str) -> str:
        """
        Sanitize hexadecimal input
        
        Args:
            hex_str: Hex string to sanitize
            
        Returns:
            Sanitized hex string
        """
        # Remove whitespace
        hex_str = hex_str.strip()
        
        # Remove common separators
        hex_str = hex_str.replace(' ', '').replace('-', '').replace(':', '')
        
        # Ensure 0x prefix if hex chars present
        if hex_str and not hex_str.startswith('0x'):
            # Check if it contains hex chars
            if any(c in hex_str.upper() for c in 'ABCDEF'):
                hex_str = '0x' + hex_str
        
        return hex_str