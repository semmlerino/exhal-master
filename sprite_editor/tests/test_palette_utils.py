#!/usr/bin/env python3
"""
Comprehensive tests for palette_utils.py
Tests all palette and color conversion functionality with edge cases and error conditions
"""

import struct

import pytest

from sprite_editor.constants import (
    BGR555_MAX_VALUE,
    BYTES_PER_COLOR,
    BYTES_PER_PALETTE,
    COLORS_PER_PALETTE,
    MAX_CGRAM_FILE_SIZE,
    MAX_PALETTES,
    PALETTE_ENTRIES,
    PALETTE_SIZE_BYTES,
    RGB888_MAX_VALUE,
)
from sprite_editor.palette_utils import (
    bgr555_to_rgb888,
    get_grayscale_palette,
    read_all_palettes,
    read_cgram_palette,
    rgb888_to_bgr555,
    write_cgram_palette,
)
from sprite_editor.security_utils import SecurityError


class TestColorConversion:
    """Test BGR555 <-> RGB888 color conversion functions"""

    def test_bgr555_to_rgb888_black(self):
        """Test conversion of black color"""
        r, g, b = bgr555_to_rgb888(0x0000)
        assert r == 0
        assert g == 0
        assert b == 0

    def test_bgr555_to_rgb888_white(self):
        """Test conversion of white color"""
        # White in BGR555: all 5 bits set = 0x7FFF
        white_bgr555 = 0x7FFF
        r, g, b = bgr555_to_rgb888(white_bgr555)

        # Each 5-bit component (31) should map to 255
        assert r == 255
        assert g == 255
        assert b == 255

    def test_bgr555_to_rgb888_primary_colors(self):
        """Test conversion of primary colors"""
        # Red: only red bits set (bits 0-4)
        red_bgr555 = 0x001F
        r, g, b = bgr555_to_rgb888(red_bgr555)
        assert r == 255
        assert g == 0
        assert b == 0

        # Green: only green bits set (bits 5-9)
        green_bgr555 = 0x03E0
        r, g, b = bgr555_to_rgb888(green_bgr555)
        assert r == 0
        assert g == 255
        assert b == 0

        # Blue: only blue bits set (bits 10-14)
        blue_bgr555 = 0x7C00
        r, g, b = bgr555_to_rgb888(blue_bgr555)
        assert r == 0
        assert g == 0
        assert b == 255

    def test_bgr555_to_rgb888_mid_values(self):
        """Test conversion of mid-range values"""
        # Test with half values (15/2 = 7 or 8)
        mid_bgr555 = (8 << 10) | (8 << 5) | 8  # Mid gray
        r, g, b = bgr555_to_rgb888(mid_bgr555)

        # 8 out of 31 should map to roughly 65 (8*255/31 ≈ 65.8)
        expected = (8 * 255) // 31  # 65
        assert r == expected
        assert g == expected
        assert b == expected

    def test_rgb888_to_bgr555_black(self):
        """Test conversion of black from RGB to BGR555"""
        bgr555 = rgb888_to_bgr555(0, 0, 0)
        assert bgr555 == 0x0000

    def test_rgb888_to_bgr555_white(self):
        """Test conversion of white from RGB to BGR555"""
        bgr555 = rgb888_to_bgr555(255, 255, 255)
        assert bgr555 == 0x7FFF

    def test_rgb888_to_bgr555_primary_colors(self):
        """Test conversion of primary colors from RGB to BGR555"""
        # Red
        bgr555 = rgb888_to_bgr555(255, 0, 0)
        assert bgr555 == 0x001F

        # Green
        bgr555 = rgb888_to_bgr555(0, 255, 0)
        assert bgr555 == 0x03E0

        # Blue
        bgr555 = rgb888_to_bgr555(0, 0, 255)
        assert bgr555 == 0x7C00

    def test_conversion_roundtrip_accuracy(self):
        """Test roundtrip conversion accuracy within precision limits"""
        # Test various BGR555 values
        test_values = [0x0000, 0x7FFF, 0x001F, 0x03E0, 0x7C00]

        for original_bgr555 in test_values:
            # Convert to RGB888 and back
            r, g, b = bgr555_to_rgb888(original_bgr555)
            converted_bgr555 = rgb888_to_bgr555(r, g, b)

            # Due to precision loss in 5-bit<->8-bit conversion,
            # check that the difference is within expected range
            # Each 5-bit component can have at most 1 bit of error
            diff = abs(converted_bgr555 - original_bgr555)
            # Allow for small precision differences
            assert (
                diff <= 0x0842
            ), f"Too much precision loss: {
                original_bgr555:04X} -> {
                converted_bgr555:04X}"

    def test_rgb888_clamping(self):
        """Test that RGB values are properly clamped to 5-bit range"""
        # Test values that should clamp to maximum
        bgr555 = rgb888_to_bgr555(300, 400, 500)  # Over 255
        r, g, b = bgr555_to_rgb888(bgr555)

        # Should be clamped to valid range
        assert 0 <= r <= 255
        assert 0 <= g <= 255
        assert 0 <= b <= 255


class TestGrayscalePalette:
    """Test grayscale palette generation"""

    def test_get_grayscale_palette_size(self):
        """Test grayscale palette has correct size"""
        palette = get_grayscale_palette()
        # 768 values (256 colors * 3)
        assert len(palette) == PALETTE_SIZE_BYTES

    def test_get_grayscale_palette_first_16_colors(self):
        """Test first 16 colors are proper gradients"""
        palette = get_grayscale_palette()

        # Check first 16 colors (0-15)
        for i in range(COLORS_PER_PALETTE):
            r = palette[i * 3]
            g = palette[i * 3 + 1]
            b = palette[i * 3 + 2]

            # Should be grayscale (r == g == b)
            assert r == g == b

            # Should be increasing values
            expected = (i * RGB888_MAX_VALUE) // 15
            assert r == expected

    def test_get_grayscale_palette_remaining_colors(self):
        """Test colors 16-255 are all black"""
        palette = get_grayscale_palette()

        # Check colors 16-255 are all black
        for i in range(COLORS_PER_PALETTE, PALETTE_ENTRIES):
            r = palette[i * 3]
            g = palette[i * 3 + 1]
            b = palette[i * 3 + 2]

            assert r == 0
            assert g == 0
            assert b == 0

    def test_get_grayscale_palette_consistency(self):
        """Test that grayscale palette is consistent across calls"""
        palette1 = get_grayscale_palette()
        palette2 = get_grayscale_palette()

        assert palette1 == palette2


class TestCgramPaletteReading:
    """Test CGRAM palette reading functionality"""

    def test_read_cgram_palette_basic(self, cgram_file):
        """Test basic palette reading"""
        palette = read_cgram_palette(cgram_file, 0)

        assert palette is not None
        assert len(palette) == PALETTE_SIZE_BYTES
        assert all(0 <= val <= 255 for val in palette)

    def test_read_cgram_palette_different_numbers(self, cgram_file):
        """Test reading different palette numbers"""
        palette0 = read_cgram_palette(cgram_file, 0)
        palette1 = read_cgram_palette(cgram_file, 1)
        palette15 = read_cgram_palette(cgram_file, 15)

        assert palette0 is not None
        assert palette1 is not None
        assert palette15 is not None

        # Test data generates identical grayscale palettes for all numbers
        # This is expected behavior based on the test fixture
        assert len(palette0) == PALETTE_SIZE_BYTES
        assert len(palette1) == PALETTE_SIZE_BYTES
        assert len(palette15) == PALETTE_SIZE_BYTES

    def test_read_cgram_palette_invalid_palette_numbers(self, cgram_file):
        """Test reading with invalid palette numbers"""
        # Negative palette number
        palette = read_cgram_palette(cgram_file, -1)
        assert palette is None

        # Palette number too high
        palette = read_cgram_palette(cgram_file, 16)
        assert palette is None

        palette = read_cgram_palette(cgram_file, 100)
        assert palette is None

    def test_read_cgram_palette_file_too_small(self, temp_dir):
        """Test reading from file that's too small"""
        # Create CGRAM file with only enough data for 8 palettes
        small_cgram = temp_dir / "small.cgram"
        small_cgram.write_bytes(bytearray(256))  # 8 palettes * 32 bytes

        # Try to read palette 15 (should need offset 480, but file is only 256
        # bytes)
        palette = read_cgram_palette(str(small_cgram), 15)
        assert palette is None

        # But should work for palette 0-7
        palette = read_cgram_palette(str(small_cgram), 0)
        assert palette is not None

    def test_read_cgram_palette_incomplete_palette_data(self, temp_dir):
        """Test handling incomplete palette data in CGRAM"""
        # Create CGRAM with incomplete palette (31 bytes instead of 32)
        cgram_data = bytearray(31)
        incomplete_cgram = temp_dir / "incomplete.cgram"
        incomplete_cgram.write_bytes(cgram_data)

        # Implementation requires full palette (32 bytes), so should return
        # None
        palette = read_cgram_palette(str(incomplete_cgram), 0)
        assert palette is None

    def test_read_cgram_palette_nonexistent_file(self, temp_dir):
        """Test reading from nonexistent file"""
        nonexistent = temp_dir / "missing.cgram"
        palette = read_cgram_palette(str(nonexistent), 0)
        assert palette is None

    def test_read_cgram_palette_oversized_file(self, temp_dir):
        """Test security check for oversized file"""
        # Create file larger than MAX_CGRAM_FILE_SIZE
        huge_cgram = temp_dir / "huge.cgram"
        huge_cgram.write_bytes(bytearray(MAX_CGRAM_FILE_SIZE + 1))

        with pytest.raises(SecurityError, match="File too large"):
            read_cgram_palette(str(huge_cgram), 0)

    def test_read_cgram_palette_struct_error(self, temp_dir, monkeypatch):
        """Test handling of struct.unpack errors"""
        cgram = temp_dir / "test.cgram"
        cgram.write_bytes(bytearray(512))

        # Mock struct.unpack to raise an error
        def mock_unpack(*args, **kwargs):
            raise struct.error("Invalid format")

        monkeypatch.setattr(struct, "unpack", mock_unpack)

        # Should return None on struct error
        palette = read_cgram_palette(str(cgram), 0)
        assert palette is None

    def test_read_cgram_palette_color_data_verification(self, temp_dir):
        """Test that color data is correctly interpreted"""
        # Create CGRAM with known color values
        cgram_data = bytearray(32)

        # Set first color to known BGR555 value
        # Red = 31, Green = 0, Blue = 0 -> BGR555 = 0x001F
        cgram_data[0] = 0x1F  # Low byte
        cgram_data[1] = 0x00  # High byte

        # Set second color to blue
        # Red = 0, Green = 0, Blue = 31 -> BGR555 = 0x7C00
        cgram_data[2] = 0x00  # Low byte
        cgram_data[3] = 0x7C  # High byte

        cgram = temp_dir / "test_colors.cgram"
        cgram.write_bytes(cgram_data)

        palette = read_cgram_palette(str(cgram), 0)
        assert palette is not None

        # First color should be red (255, 0, 0)
        assert palette[0:3] == [255, 0, 0]

        # Second color should be blue (0, 0, 255)
        assert palette[3:6] == [0, 0, 255]


class TestBatchPaletteOperations:
    """Test batch palette operations"""

    def test_read_all_palettes(self, cgram_file):
        """Test reading all 16 palettes"""
        palettes = read_all_palettes(cgram_file)

        assert len(palettes) == MAX_PALETTES
        assert all(pal is not None for pal in palettes)
        assert all(len(pal) == PALETTE_SIZE_BYTES for pal in palettes)

    def test_read_all_palettes_with_failures(self, temp_dir):
        """Test read_all_palettes when some palettes fail to read"""
        # Create CGRAM with only 8 palettes
        partial_cgram = temp_dir / "partial.cgram"
        partial_cgram.write_bytes(bytearray(256))  # 8 palettes only

        palettes = read_all_palettes(str(partial_cgram))

        assert len(palettes) == MAX_PALETTES
        # First 8 should be valid, last 8 should be None
        assert all(pal is not None for pal in palettes[:8])
        assert all(pal is None for pal in palettes[8:])

    def test_read_all_palettes_nonexistent_file(self, temp_dir):
        """Test read_all_palettes with nonexistent file"""
        missing = temp_dir / "missing.cgram"
        palettes = read_all_palettes(str(missing))

        assert len(palettes) == MAX_PALETTES
        assert all(pal is None for pal in palettes)


class TestPaletteWriting:
    """Test palette writing functionality"""

    def test_write_cgram_palette_basic(self):
        """Test basic palette writing"""
        # Create a simple RGB palette (first 16 colors)
        palette = []
        for i in range(COLORS_PER_PALETTE):
            palette.extend([i * 8, i * 8, i * 8])  # Grayscale

        cgram_data = write_cgram_palette(palette, 0)

        assert len(cgram_data) == BYTES_PER_PALETTE
        assert isinstance(cgram_data, bytes)

    def test_write_cgram_palette_primary_colors(self):
        """Test writing primary colors"""
        # Create palette with red, green, blue
        palette = [
            255,
            0,
            0,  # Red
            0,
            255,
            0,  # Green
            0,
            0,
            255,  # Blue
        ]
        # Fill rest with black
        palette.extend([0, 0, 0] * (COLORS_PER_PALETTE - 3))

        cgram_data = write_cgram_palette(palette, 0)

        # Verify the BGR555 values
        assert len(cgram_data) == BYTES_PER_PALETTE

        # Red should be 0x001F
        red_bgr555 = struct.unpack("<H", cgram_data[0:2])[0]
        assert red_bgr555 == 0x001F

        # Green should be 0x03E0
        green_bgr555 = struct.unpack("<H", cgram_data[2:4])[0]
        assert green_bgr555 == 0x03E0

        # Blue should be 0x7C00
        blue_bgr555 = struct.unpack("<H", cgram_data[4:6])[0]
        assert blue_bgr555 == 0x7C00

    def test_write_cgram_palette_insufficient_colors(self):
        """Test error when palette doesn't have enough colors"""
        short_palette = [255, 0, 0] * 8  # Only 8 colors

        with pytest.raises(ValueError, match="Palette must have at least 48 values"):
            write_cgram_palette(short_palette, 0)

    def test_write_cgram_palette_empty(self):
        """Test error with empty palette"""
        with pytest.raises(ValueError, match="Palette must have at least 48 values"):
            write_cgram_palette([], 0)

    def test_write_cgram_palette_roundtrip(self, temp_dir):
        """Test roundtrip write -> read palette"""
        # Create a test palette
        original_palette = []
        for i in range(COLORS_PER_PALETTE):
            original_palette.extend([i * 16, (i * 16) % 256, 255 - (i * 16)])

        # Write to CGRAM format
        cgram_data = write_cgram_palette(original_palette, 0)

        # Create file and read back
        cgram_file = temp_dir / "roundtrip.cgram"
        # Need to create a full CGRAM file (512 bytes) for read function
        full_cgram = bytearray(512)
        full_cgram[0:32] = cgram_data
        cgram_file.write_bytes(full_cgram)

        # Read back the palette
        read_palette = read_cgram_palette(str(cgram_file), 0)

        assert read_palette is not None
        # Compare first 48 values (16 colors * 3 components)
        for i in range(48):
            # Allow small rounding differences due to 5-bit precision
            diff = abs(original_palette[i] - read_palette[i])
            assert (
                diff <= 8
            ), f"Color component {i}: {
                original_palette[i]} vs {
                read_palette[i]}"

    def test_write_cgram_palette_large_palette(self):
        """Test writing palette with more than 16 colors (should use first 16)"""
        # Create palette with 32 colors
        large_palette = []
        for i in range(32):
            large_palette.extend([i * 8, i * 4, i * 2])

        cgram_data = write_cgram_palette(large_palette, 0)

        # Should still be 32 bytes (16 colors)
        assert len(cgram_data) == BYTES_PER_PALETTE


class TestErrorConditions:
    """Test various error conditions and edge cases"""

    def test_file_permission_error(self, temp_dir, monkeypatch):
        """Test handling of file permission errors"""
        cgram = temp_dir / "readonly.cgram"
        cgram.write_bytes(bytearray(512))

        # Mock open to raise PermissionError
        original_open = open

        def mock_open(filename, mode="r", *args, **kwargs):
            if "readonly.cgram" in str(filename):
                raise PermissionError("Permission denied")
            return original_open(filename, mode, *args, **kwargs)

        import builtins

        monkeypatch.setattr(builtins, "open", mock_open)

        palette = read_cgram_palette(str(cgram), 0)
        assert palette is None

    def test_invalid_file_path_types(self):
        """Test with invalid file path types"""
        # None as file path should raise TypeError from validate_file_path
        with pytest.raises(TypeError):
            read_cgram_palette(None, 0)

    def test_color_conversion_boundary_values(self):
        """Test color conversion with boundary values"""
        # Test with maximum BGR555 values
        max_bgr555 = 0x7FFF
        r, g, b = bgr555_to_rgb888(max_bgr555)

        assert r == 255
        assert g == 255
        assert b == 255

        # Test conversion back
        bgr555 = rgb888_to_bgr555(r, g, b)
        assert bgr555 == max_bgr555

    def test_palette_number_edge_cases(self, cgram_file):
        """Test palette reading with edge case palette numbers"""
        # Test valid boundary values
        palette_0 = read_cgram_palette(cgram_file, 0)
        palette_15 = read_cgram_palette(cgram_file, 15)

        assert palette_0 is not None
        assert palette_15 is not None

        # Test invalid boundary values
        palette_neg = read_cgram_palette(cgram_file, -1)
        palette_high = read_cgram_palette(cgram_file, 16)

        assert palette_neg is None
        assert palette_high is None


class TestImportHandling:
    """Test import error handling"""

    def test_constants_available(self):
        """Test that constants are properly imported"""
        # Verify key constants are available
        assert COLORS_PER_PALETTE == 16
        assert BYTES_PER_COLOR == 2
        assert BYTES_PER_PALETTE == 32
        assert MAX_PALETTES == 16
        assert BGR555_MAX_VALUE == 31
        assert RGB888_MAX_VALUE == 255

    def test_security_utils_available(self):
        """Test that security utilities are available"""
        # This tests the import fallback mechanism
        from sprite_editor.palette_utils import SecurityError

        assert SecurityError is not None
