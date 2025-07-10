#!/usr/bin/env python3
"""
Unit tests for sprite_edit_helpers.py
Tests the core utility functions for sprite editing
"""

import os
import struct
import tempfile
import unittest

from sprite_edit_helpers import (
    bgr555_to_rgb,
    decode_4bpp_tile,
    encode_4bpp_tile,
    parse_cgram,
    rgb_to_bgr555,
)


class TestColorConversions(unittest.TestCase):
    """Test color conversion functions"""

    def test_bgr555_to_rgb_black(self):
        """Test converting black"""
        r, g, b = bgr555_to_rgb(0x0000)
        assert (r, g, b) == (0, 0, 0)

    def test_bgr555_to_rgb_white(self):
        """Test converting white (all 5 bits set)"""
        # BGR555: 0111 1111 1111 1111 = 0x7FFF
        r, g, b = bgr555_to_rgb(0x7FFF)
        assert (r, g, b) == (248, 248, 248)  # 31 * 8 = 248

    def test_bgr555_to_rgb_pure_red(self):
        """Test converting pure red"""
        # BGR555: red in bits 0-4
        r, g, b = bgr555_to_rgb(0x001F)  # 31 in red channel
        assert (r, g, b) == (248, 0, 0)

    def test_bgr555_to_rgb_pure_green(self):
        """Test converting pure green"""
        # BGR555: green in bits 5-9
        r, g, b = bgr555_to_rgb(0x03E0)  # 31 << 5
        assert (r, g, b) == (0, 248, 0)

    def test_bgr555_to_rgb_pure_blue(self):
        """Test converting pure blue"""
        # BGR555: blue in bits 10-14
        r, g, b = bgr555_to_rgb(0x7C00)  # 31 << 10
        assert (r, g, b) == (0, 0, 248)

    def test_rgb_to_bgr555_black(self):
        """Test converting black to BGR555"""
        bgr = rgb_to_bgr555(0, 0, 0)
        assert bgr == 0

    def test_rgb_to_bgr555_white(self):
        """Test converting white to BGR555"""
        bgr = rgb_to_bgr555(255, 255, 255)
        assert bgr == 32767  # All 5-bit channels maxed

    def test_rgb_to_bgr555_rounding(self):
        """Test rounding behavior"""
        # 248 / 8 = 31 exactly
        bgr = rgb_to_bgr555(248, 248, 248)
        assert bgr == 32767

        # 247 / 8 = 30.875, should round down to 30
        bgr = rgb_to_bgr555(247, 247, 247)
        expected = (30 << 10) | (30 << 5) | 30
        assert bgr == expected

    def test_color_conversion_round_trip(self):
        """Test converting back and forth maintains values"""
        # Test some common SNES colors
        test_colors = [
            0x0000,  # Black
            0x7FFF,  # White
            0x001F,  # Red
            0x03E0,  # Green
            0x7C00,  # Blue
            0x7C1F,  # Magenta
            0x7FE0,  # Yellow
            0x03FF,  # Cyan
        ]

        for original_bgr in test_colors:
            r, g, b = bgr555_to_rgb(original_bgr)
            converted_bgr = rgb_to_bgr555(r, g, b)
            assert original_bgr == converted_bgr, f"Round trip failed for 0x{original_bgr:04X}"


class TestCGRAMParsing(unittest.TestCase):
    """Test CGRAM file parsing"""

    def setUp(self):
        """Create test CGRAM data"""
        self.test_dir = tempfile.mkdtemp()
        self.cgram_file = os.path.join(self.test_dir, "test.cgram")

    def tearDown(self):
        """Clean up test files"""
        if os.path.exists(self.cgram_file):
            os.unlink(self.cgram_file)
        os.rmdir(self.test_dir)

    def test_parse_cgram_all_black(self):
        """Test parsing CGRAM with all black colors"""
        # Create 512 bytes of zeros (16 palettes * 16 colors * 2 bytes)
        with open(self.cgram_file, "wb") as f:
            f.write(b"\x00" * 512)

        palettes = parse_cgram(self.cgram_file)

        # Should have 16 palettes
        assert len(palettes) == 16

        # Each palette should have 16 colors
        for pal in palettes:
            assert len(pal) == 16

            # All colors should be black (0, 0, 0)
            for color in pal:
                assert color == (0, 0, 0)

    def test_parse_cgram_specific_colors(self):
        """Test parsing CGRAM with specific test colors"""
        # Create test data with known colors
        test_data = bytearray(512)

        # Palette 0, Color 0: Black (0x0000)
        test_data[0:2] = struct.pack("<H", 0x0000)

        # Palette 0, Color 1: White (0x7FFF)
        test_data[2:4] = struct.pack("<H", 0x7FFF)

        # Palette 0, Color 2: Red (0x001F)
        test_data[4:6] = struct.pack("<H", 0x001F)

        # Palette 8, Color 0: Green (0x03E0)
        offset = 8 * 32  # Palette 8 offset
        test_data[offset:offset+2] = struct.pack("<H", 0x03E0)

        with open(self.cgram_file, "wb") as f:
            f.write(test_data)

        palettes = parse_cgram(self.cgram_file)

        # Check specific colors
        assert palettes[0][0] == (0, 0, 0)      # Black
        assert palettes[0][1] == (248, 248, 248)  # White
        assert palettes[0][2] == (248, 0, 0)      # Red
        assert palettes[8][0] == (0, 248, 0)      # Green

    def test_parse_cgram_partial_file(self):
        """Test parsing incomplete CGRAM file"""
        # Create file with only 256 bytes (half size)
        with open(self.cgram_file, "wb") as f:
            f.write(b"\xFF" * 256)

        palettes = parse_cgram(self.cgram_file)

        # Should still return 16 palettes
        assert len(palettes) == 16

        # First 8 palettes should have white colors
        for i in range(8):
            assert palettes[i][0] == (248, 248, 248)

        # Last 8 palettes should have black (missing data)
        for i in range(8, 16):
            assert palettes[i][0] == (0, 0, 0)


class TestTileEncoding(unittest.TestCase):
    """Test 4bpp tile encoding/decoding"""

    def test_decode_4bpp_tile_all_zeros(self):
        """Test decoding a blank tile"""
        tile_data = bytes(32)  # 32 bytes of zeros
        pixels = decode_4bpp_tile(tile_data)

        # Should have 64 pixels
        assert len(pixels) == 64

        # All pixels should be 0
        assert all(p == 0 for p in pixels)

    def test_decode_4bpp_tile_pattern(self):
        """Test decoding a tile with a specific pattern"""
        # Create a simple pattern: first row has pixels 0-7
        tile_data = bytearray(32)

        # For row 0, set different values for each pixel
        # SNES 4bpp format uses planar encoding
        for col in range(8):
            bit = 7 - col
            # Set bit in each bitplane for this pixel
            if col & 1:  # Bit 0
                tile_data[0] |= (1 << bit)
            if col & 2:  # Bit 1
                tile_data[1] |= (1 << bit)
            if col & 4:  # Bit 2
                tile_data[16] |= (1 << bit)
            if col & 8:  # Bit 3
                tile_data[17] |= (1 << bit)

        pixels = decode_4bpp_tile(bytes(tile_data))

        # Check first row has correct values
        for col in range(8):
            assert pixels[col] == col

    def test_encode_4bpp_tile_all_zeros(self):
        """Test encoding a blank tile"""
        pixels = [0] * 64
        tile_data = encode_4bpp_tile(pixels)

        # Should produce 32 bytes
        assert len(tile_data) == 32

        # All bytes should be 0
        assert tile_data == bytes(32)

    def test_encode_4bpp_tile_all_15s(self):
        """Test encoding a tile with all pixels set to 15"""
        pixels = [15] * 64
        tile_data = encode_4bpp_tile(pixels)

        # Should produce 32 bytes
        assert len(tile_data) == 32

        # Check the pattern
        # All bitplanes should be 0xFF for rows where they're active
        for row in range(8):
            # Bitplanes 0 and 1
            assert tile_data[row * 2] == 255
            assert tile_data[row * 2 + 1] == 255
            # Bitplanes 2 and 3
            assert tile_data[row * 2 + 16] == 255
            assert tile_data[row * 2 + 17] == 255

    def test_encode_decode_round_trip(self):
        """Test encoding and decoding maintains data"""
        # Test various patterns
        test_patterns = [
            [i % 16 for i in range(64)],  # Sequential
            [15 - (i % 16) for i in range(64)],  # Reverse sequential
            [0, 15] * 32,  # Alternating
            [i // 8 for i in range(64)],  # Row-based
        ]

        for pattern in test_patterns:
            encoded = encode_4bpp_tile(pattern)
            decoded = decode_4bpp_tile(encoded)
            assert pattern == decoded

    def test_encode_clips_values(self):
        """Test that encoding clips values to 0-15 range"""
        # Create pixels with out-of-range values
        pixels = list(range(64))  # 0-63

        tile_data = encode_4bpp_tile(pixels)
        decoded = decode_4bpp_tile(tile_data)

        # Values should be masked to 0-15
        expected = [i & 0xF for i in range(64)]
        assert decoded == expected


class TestIntegrationHelpers(unittest.TestCase):
    """Integration tests for helper functions working together"""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()

    def tearDown(self):
        # Clean up any test files
        for file in os.listdir(self.test_dir):
            os.unlink(os.path.join(self.test_dir, file))
        os.rmdir(self.test_dir)

    def test_cgram_parse_and_color_conversion(self):
        """Test parsing CGRAM and using the colors"""
        # Create a CGRAM file with gradient palette
        cgram_file = os.path.join(self.test_dir, "gradient.cgram")

        with open(cgram_file, "wb") as f:
            for pal_idx in range(16):
                for color_idx in range(16):
                    # Create gradient in each palette
                    intensity = color_idx * 2  # 0-30
                    bgr555 = (intensity << 10) | (intensity << 5) | intensity
                    f.write(struct.pack("<H", bgr555))

        # Parse the file
        palettes = parse_cgram(cgram_file)

        # Verify gradients
        for pal_idx in range(16):
            for color_idx in range(16):
                r, g, b = palettes[pal_idx][color_idx]
                expected = (color_idx * 2) * 8  # 5-bit to 8-bit conversion
                if color_idx == 15:
                    expected = 240  # 30 * 8
                assert r == expected
                assert g == expected
                assert b == expected


if __name__ == "__main__":
    unittest.main()
