#!/usr/bin/env python3
"""
Tests for validation utilities
Tests input validation logic comprehensively
"""

import pytest

from sprite_editor.utils.validation import InputSanitizer, ValidationError, Validators


@pytest.mark.unit
class TestValidators:
    """Test Validators utility class"""

    def test_validate_hex_value_valid(self):
        """Test validating valid hex values"""
        # Test with 0x prefix
        valid, value, error = Validators.validate_hex_value("0xFF")
        assert valid is True
        assert value == 255
        assert error == ""

        # Test without prefix
        valid, value, error = Validators.validate_hex_value("FF")
        assert valid is True
        assert value == 255
        assert error == ""

        # Test lowercase
        valid, value, error = Validators.validate_hex_value("0xabcd")
        assert valid is True
        assert value == 0xABCD
        assert error == ""

    def test_validate_hex_value_with_whitespace(self):
        """Test validating hex values with whitespace"""
        valid, value, error = Validators.validate_hex_value("  0xFF  ")
        assert valid is True
        assert value == 255
        assert error == ""

    def test_validate_hex_value_range_check(self):
        """Test hex value range validation"""
        # Test minimum value
        valid, value, error = Validators.validate_hex_value("0x10", min_val=0x20)
        assert valid is False
        assert error == "Value must be at least 0x20"

        # Test maximum value
        valid, value, error = Validators.validate_hex_value("0xFF", max_val=0x80)
        assert valid is False
        assert error == "Value must not exceed 0x80"

        # Test within range
        valid, value, error = Validators.validate_hex_value(
            "0x50", min_val=0x10, max_val=0x80
        )
        assert valid is True
        assert value == 0x50
        assert error == ""

    def test_validate_hex_value_invalid(self):
        """Test validating invalid hex values"""
        # Test invalid characters
        valid, value, error = Validators.validate_hex_value("0xGG")
        assert valid is False
        assert error == "Invalid hexadecimal value"

        # Test empty string
        valid, value, error = Validators.validate_hex_value("")
        assert valid is False
        assert error == "Invalid hexadecimal value"

        # Test non-hex string
        valid, value, error = Validators.validate_hex_value("hello")
        assert valid is False
        assert error == "Invalid hexadecimal value"

    def test_validate_offset(self):
        """Test offset validation"""
        # Valid offset
        valid, error = Validators.validate_offset(100, 1000)
        assert valid is True
        assert error == ""

        # Negative offset
        valid, error = Validators.validate_offset(-1, 1000)
        assert valid is False
        assert error == "Offset cannot be negative"

        # Offset exceeds file size
        valid, error = Validators.validate_offset(1000, 1000)
        assert valid is False
        assert "exceeds file size" in error

        # Offset at boundary
        valid, error = Validators.validate_offset(999, 1000)
        assert valid is True
        assert error == ""

    def test_validate_size(self):
        """Test size validation"""
        # Valid size
        valid, error = Validators.validate_size(100, 1000)
        assert valid is True
        assert error == ""

        # Zero size
        valid, error = Validators.validate_size(0, 1000)
        assert valid is False
        assert error == "Size must be greater than 0"

        # Negative size
        valid, error = Validators.validate_size(-10, 1000)
        assert valid is False
        assert error == "Size must be greater than 0"

        # Size exceeds available
        valid, error = Validators.validate_size(1001, 1000)
        assert valid is False
        assert "exceeds available space" in error

    def test_validate_tile_count(self):
        """Test tile count validation"""
        # Valid count
        valid, error = Validators.validate_tile_count(100)
        assert valid is True
        assert error == ""

        # Zero count
        valid, error = Validators.validate_tile_count(0)
        assert valid is False
        assert error == "Tile count must be greater than 0"

        # Exceeds maximum
        valid, error = Validators.validate_tile_count(70000)
        assert valid is False
        assert "exceeds maximum" in error

        # Custom maximum
        valid, error = Validators.validate_tile_count(50, max_tiles=100)
        assert valid is True
        assert error == ""

        valid, error = Validators.validate_tile_count(101, max_tiles=100)
        assert valid is False
        assert "exceeds maximum (100)" in error

    def test_validate_extraction_params(self):
        """Test extraction parameter validation"""
        # Valid parameters
        errors = Validators.validate_extraction_params(0x1000, 0x800, 0x10000)
        assert len(errors) == 0

        # Invalid offset
        errors = Validators.validate_extraction_params(0x10000, 0x800, 0x10000)
        assert len(errors) > 0
        assert any("exceeds file size" in e for e in errors)

        # Invalid size
        errors = Validators.validate_extraction_params(0xF000, 0x2000, 0x10000)
        assert len(errors) > 0
        assert any("exceeds available space" in e for e in errors)

        # Non-aligned size
        errors = Validators.validate_extraction_params(0x1000, 0x801, 0x10000)
        assert len(errors) > 0
        assert any("multiple of 32 bytes" in e for e in errors)

        # Multiple errors
        errors = Validators.validate_extraction_params(-1, 0x801, 0x10000)
        assert len(errors) >= 2  # Negative offset and non-aligned size

    def test_validate_png_dimensions(self):
        """Test PNG dimension validation"""
        # Valid dimensions
        errors = Validators.validate_png_dimensions(256, 256)
        assert len(errors) == 0

        # Invalid dimensions (zero)
        errors = Validators.validate_png_dimensions(0, 256)
        assert len(errors) == 1
        assert "Invalid image dimensions" in errors[0]

        # Non-aligned width
        errors = Validators.validate_png_dimensions(255, 256)
        assert len(errors) == 1
        assert "Width (255) must be multiple of 8" in errors[0]

        # Non-aligned height
        errors = Validators.validate_png_dimensions(256, 255)
        assert len(errors) == 1
        assert "Height (255) must be multiple of 8" in errors[0]

        # Both non-aligned
        errors = Validators.validate_png_dimensions(255, 255)
        assert len(errors) == 2

        # Exceeds limits
        errors = Validators.validate_png_dimensions(2048, 2048)
        assert len(errors) == 1
        assert "exceed reasonable limits" in errors[0]

    def test_validate_palette_index(self):
        """Test palette index validation"""
        # Valid indices
        for i in range(16):
            valid, error = Validators.validate_palette_index(i)
            assert valid is True
            assert error == ""

        # Negative index
        valid, error = Validators.validate_palette_index(-1)
        assert valid is False
        assert error == "Palette index cannot be negative"

        # Index too high
        valid, error = Validators.validate_palette_index(16)
        assert valid is False
        assert error == "Palette index must be 0-15"


@pytest.mark.unit
class TestInputSanitizer:
    """Test InputSanitizer utility class"""

    def test_sanitize_filename_valid(self):
        """Test sanitizing valid filenames"""
        # Already clean filename
        result = InputSanitizer.sanitize_filename("test_file.txt")
        assert result == "test_file.txt"

        # Filename with spaces
        result = InputSanitizer.sanitize_filename("my file.txt")
        assert result == "my file.txt"

    def test_sanitize_filename_invalid_chars(self):
        """Test sanitizing filenames with invalid characters"""
        # Path separators
        result = InputSanitizer.sanitize_filename("folder/file.txt")
        assert result == "folder_file.txt"

        result = InputSanitizer.sanitize_filename("folder\\file.txt")
        assert result == "folder_file.txt"

        # Other invalid characters
        result = InputSanitizer.sanitize_filename('file<>:"|?*.txt')
        assert result == "file_______.txt"

    def test_sanitize_filename_dots_and_spaces(self):
        """Test sanitizing filenames with leading/trailing dots and spaces"""
        result = InputSanitizer.sanitize_filename("  .file.txt.  ")
        assert result == "file.txt"

        result = InputSanitizer.sanitize_filename("...")
        assert result == "output"  # Falls back to default

    def test_sanitize_filename_empty(self):
        """Test sanitizing empty filename"""
        result = InputSanitizer.sanitize_filename("")
        assert result == "output"

        result = InputSanitizer.sanitize_filename("", "custom_default")
        assert result == "custom_default"

    def test_sanitize_hex_input(self):
        """Test sanitizing hexadecimal input"""
        # Already clean
        result = InputSanitizer.sanitize_hex_input("0xFF")
        assert result == "0xFF"

        # With whitespace
        result = InputSanitizer.sanitize_hex_input("  0xFF  ")
        assert result == "0xFF"

        # With separators
        result = InputSanitizer.sanitize_hex_input("FF:EE:DD")
        assert result == "0xFFEEDD"

        result = InputSanitizer.sanitize_hex_input("FF-EE-DD")
        assert result == "0xFFEEDD"

        result = InputSanitizer.sanitize_hex_input("FF EE DD")
        assert result == "0xFFEEDD"

    def test_sanitize_hex_input_auto_prefix(self):
        """Test auto-adding 0x prefix when hex chars detected"""
        # Contains hex letters
        result = InputSanitizer.sanitize_hex_input("ABCD")
        assert result == "0xABCD"

        result = InputSanitizer.sanitize_hex_input("abcd")
        assert result == "0xabcd"

        # Only decimal digits (no prefix added)
        result = InputSanitizer.sanitize_hex_input("1234")
        assert result == "1234"

        # Mixed case
        result = InputSanitizer.sanitize_hex_input("12ef")
        assert result == "0x12ef"

    def test_sanitize_hex_input_empty(self):
        """Test sanitizing empty hex input"""
        result = InputSanitizer.sanitize_hex_input("")
        assert result == ""

        result = InputSanitizer.sanitize_hex_input("   ")
        assert result == ""


@pytest.mark.unit
class TestValidationError:
    """Test ValidationError exception"""

    def test_validation_error_creation(self):
        """Test creating ValidationError"""
        error = ValidationError("Test error message")
        assert str(error) == "Test error message"
        assert isinstance(error, Exception)
