#!/usr/bin/env python3
"""
Comprehensive tests for tile_utils.py
Tests all tile encoding/decoding functionality with edge cases and error conditions
"""

from unittest import mock

import pytest

from sprite_editor.constants import (BYTES_PER_TILE_4BPP, PIXELS_PER_TILE,
                                     TILE_BITPLANE_OFFSET, TILE_HEIGHT,
                                     TILE_WIDTH)
from sprite_editor.tile_utils import (decode_4bpp_tile, decode_tiles,
                                      encode_4bpp_tile, encode_tiles)


class TestTileDecoding:
    """Test 4bpp tile decoding functionality"""

    def test_decode_4bpp_tile_basic(self, sample_4bpp_tile):
        """Test basic tile decoding with sample data"""
        tile_pixels = decode_4bpp_tile(sample_4bpp_tile, 0)

        assert len(tile_pixels) == PIXELS_PER_TILE
        assert all(0 <= pixel <= 15 for pixel in tile_pixels)

        # Check diagonal pattern from fixture
        for y in range(TILE_HEIGHT):
            for x in range(TILE_WIDTH):
                pixel_idx = y * TILE_WIDTH + x
                if x == y:
                    # Diagonal should be color 1
                    assert tile_pixels[pixel_idx] == 1
                else:
                    assert tile_pixels[pixel_idx] == 0  # Rest should be 0

    def test_decode_4bpp_tile_offset(self):
        """Test decoding with non-zero offset"""
        # Create data with multiple tiles
        tile1_data = b'\x01' + b'\x00' * 31  # Simple pattern
        tile2_data = b'\x02' + b'\x00' * 31  # Different pattern
        combined_data = tile1_data + tile2_data

        # Decode second tile
        tile_pixels = decode_4bpp_tile(combined_data, BYTES_PER_TILE_4BPP)

        # Should get pattern from second tile
        assert tile_pixels[0] != 1  # Should be different from first tile

    def test_decode_4bpp_tile_bounds_error(self):
        """Test error when offset exceeds data bounds"""
        small_data = b'\x00' * 16  # Only 16 bytes, need 32

        with pytest.raises(IndexError, match="Tile data out of bounds at offset 0"):
            decode_4bpp_tile(small_data, 0)

        # Test with offset that would exceed bounds
        data_31_bytes = b'\x00' * 31
        with pytest.raises(IndexError, match="Tile data out of bounds at offset 0"):
            decode_4bpp_tile(data_31_bytes, 0)

    def test_decode_4bpp_tile_complex_pattern(self):
        """Test decoding of complex 4bpp pattern"""
        # Create a tile with all 4 bitplanes having data
        tile_data = bytearray(32)

        # Set specific patterns in each bitplane
        for y in range(8):
            # bp0: alternating rows
            tile_data[y * 2] = 0xFF if y % 2 == 0 else 0x00
            # bp1: top/bottom half
            tile_data[y * 2 + 1] = 0x0F if y < 4 else 0xF0
            # bp2: checkerboard
            tile_data[16 + y * 2] = 0xAA
            # bp3: inverse checkerboard
            tile_data[16 + y * 2 + 1] = 0x55

        pixels = decode_4bpp_tile(bytes(tile_data), 0)

        # Verify we get values using all 4 bits
        unique_values = set(pixels)
        assert len(unique_values) > 1  # Should have multiple colors
        assert all(0 <= val <= 15 for val in unique_values)


class TestTileEncoding:
    """Test 4bpp tile encoding functionality"""

    def test_encode_4bpp_tile_basic(self):
        """Test basic tile encoding"""
        # Create a simple test pattern
        test_pixels = [0] * PIXELS_PER_TILE
        test_pixels[0] = 1  # First pixel = color 1
        test_pixels[9] = 15  # Pixel at (1,1) = color 15

        encoded = encode_4bpp_tile(test_pixels)

        assert len(encoded) == BYTES_PER_TILE_4BPP
        assert isinstance(encoded, bytes)

    def test_encode_4bpp_tile_wrong_size_error(self):
        """Test error when pixel list has wrong size"""
        # Test with too few pixels
        with pytest.raises(ValueError, match="Expected 64 pixels, got 32"):
            encode_4bpp_tile([0] * 32)

        # Test with too many pixels
        with pytest.raises(ValueError, match="Expected 64 pixels, got 128"):
            encode_4bpp_tile([0] * 128)

        # Test with empty list
        with pytest.raises(ValueError, match="Expected 64 pixels, got 0"):
            encode_4bpp_tile([])

    def test_encode_decode_roundtrip(self):
        """Test that encoding and decoding are inverse operations"""
        # Create a complex test pattern using all colors
        test_pixels = []
        for y in range(TILE_HEIGHT):
            for x in range(TILE_WIDTH):
                # Create a pattern that uses all 16 colors
                test_pixels.append((x + y * 2) % 16)

        # Encode then decode
        encoded = encode_4bpp_tile(test_pixels)
        decoded = decode_4bpp_tile(encoded, 0)

        assert decoded == test_pixels

    def test_encode_4bpp_tile_pixel_clamping(self):
        """Test that pixel values are properly clamped to 4 bits"""
        # Create pixels with values > 15 (should be masked to 4 bits)
        test_pixels = [16, 17, 255, 31] + [0] * 60

        encoded = encode_4bpp_tile(test_pixels)
        decoded = decode_4bpp_tile(encoded, 0)

        # Values should be masked to 4 bits
        assert decoded[0] == 0   # 16 & 0x0F = 0
        assert decoded[1] == 1   # 17 & 0x0F = 1
        assert decoded[2] == 15  # 255 & 0x0F = 15
        assert decoded[3] == 15  # 31 & 0x0F = 15


class TestBatchOperations:
    """Test batch tile operations (decode_tiles, encode_tiles)"""

    def test_decode_tiles_multiple(self):
        """Test decoding multiple tiles"""
        # Create data for 3 tiles with different patterns
        tile1 = bytearray(32)
        tile1[0] = 0x01  # First tile marker

        tile2 = bytearray(32)
        tile2[0] = 0x02  # Second tile marker

        tile3 = bytearray(32)
        tile3[0] = 0x04  # Third tile marker

        combined_data = bytes(tile1 + tile2 + tile3)

        tiles = decode_tiles(combined_data, 3)

        assert len(tiles) == 3
        assert len(tiles[0]) == PIXELS_PER_TILE
        assert len(tiles[1]) == PIXELS_PER_TILE
        assert len(tiles[2]) == PIXELS_PER_TILE

        # Each tile should have different patterns
        assert tiles[0] != tiles[1]
        assert tiles[1] != tiles[2]

    def test_decode_tiles_with_offset(self):
        """Test decoding tiles with start offset"""
        # Create data with padding + 2 tiles with distinct patterns
        padding = b'\xFF' * 64  # 64 bytes of padding

        # Create distinct tile patterns
        tile1 = bytearray(32)
        tile1[0] = 0x80  # Set a bit in first byte to create pattern

        tile2 = bytearray(32)
        tile2[0] = 0x40  # Set different bit in first byte

        combined_data = padding + bytes(tile1) + bytes(tile2)

        # Decode starting after padding
        tiles = decode_tiles(combined_data, 2, start_offset=64)

        assert len(tiles) == 2
        # Verify we got the tiles after the padding with different patterns
        # Should be 1 vs 0 due to different bit patterns
        assert tiles[0][0] != tiles[1][0]

    def test_decode_tiles_insufficient_data(self):
        """Test decode_tiles when there's insufficient data"""
        # Create data for only 1.5 tiles
        partial_data = b'\x00' * 48  # 32 + 16 bytes

        # Request 2 tiles, should only get 1
        tiles = decode_tiles(partial_data, 2)

        assert len(tiles) == 1
        assert len(tiles[0]) == PIXELS_PER_TILE

    def test_decode_tiles_exact_boundary(self):
        """Test decode_tiles at exact data boundary"""
        # Create data for exactly 2 tiles
        data = b'\x00' * (BYTES_PER_TILE_4BPP * 2)

        tiles = decode_tiles(data, 2)
        assert len(tiles) == 2

        # Try to decode 3 tiles from 2 tiles worth of data
        tiles = decode_tiles(data, 3)
        assert len(tiles) == 2  # Should only get 2

    def test_encode_tiles_multiple(self):
        """Test encoding multiple tiles"""
        # Create 3 different tile patterns
        tile1 = [1] * PIXELS_PER_TILE
        tile2 = [2] * PIXELS_PER_TILE
        tile3 = [3] * PIXELS_PER_TILE

        tiles = [tile1, tile2, tile3]
        encoded = encode_tiles(tiles)

        assert len(encoded) == BYTES_PER_TILE_4BPP * 3
        assert isinstance(encoded, bytes)

    def test_encode_tiles_empty_list(self):
        """Test encoding empty tile list"""
        encoded = encode_tiles([])

        assert encoded == b''
        assert isinstance(encoded, bytes)

    def test_encode_decode_tiles_roundtrip(self):
        """Test roundtrip encoding/decoding of multiple tiles"""
        # Create varied tile patterns
        tiles = []
        for i in range(3):
            tile = [(x + i) % 16 for x in range(PIXELS_PER_TILE)]
            tiles.append(tile)

        # Encode then decode
        encoded = encode_tiles(tiles)
        decoded = decode_tiles(encoded, 3)

        assert len(decoded) == 3
        for i in range(3):
            assert decoded[i] == tiles[i]


class TestErrorConditions:
    """Test various error conditions and edge cases"""

    def test_decode_with_zero_offset(self):
        """Test decoding at zero offset"""
        data = b'\x00' * BYTES_PER_TILE_4BPP
        pixels = decode_4bpp_tile(data, 0)

        assert len(pixels) == PIXELS_PER_TILE
        assert all(pixel == 0 for pixel in pixels)

    def test_decode_tiles_zero_count(self):
        """Test decode_tiles with zero tile count"""
        data = b'\x00' * BYTES_PER_TILE_4BPP
        tiles = decode_tiles(data, 0)

        assert tiles == []

    def test_encode_tiles_with_invalid_tile(self):
        """Test encode_tiles when one tile has wrong size"""
        good_tile = [0] * PIXELS_PER_TILE
        bad_tile = [0] * 32  # Wrong size

        with pytest.raises(ValueError, match="Expected 64 pixels, got 32"):
            encode_tiles([good_tile, bad_tile])


class TestImportHandling:
    """Test import error handling"""

    def test_import_fallback(self):
        """Test that the module can handle import errors"""
        # This is tricky to test directly, but we can verify the constants are available
        # regardless of which import path was taken
        assert TILE_WIDTH == 8
        assert TILE_HEIGHT == 8
        assert BYTES_PER_TILE_4BPP == 32
        assert PIXELS_PER_TILE == 64
        assert TILE_BITPLANE_OFFSET == 16

    @mock.patch('sprite_editor.tile_utils.TILE_WIDTH', 8)
    def test_constants_available_after_import(self):
        """Test that constants are properly imported and usable"""
        # Create a simple test to verify constants work
        test_pixels = [0] * PIXELS_PER_TILE
        encoded = encode_4bpp_tile(test_pixels)

        assert len(encoded) == BYTES_PER_TILE_4BPP


class TestBoundaryConditions:
    """Test boundary conditions and edge cases"""

    def test_maximum_color_values(self):
        """Test encoding/decoding with maximum color values"""
        # Test with all pixels set to maximum value (15)
        max_pixels = [15] * PIXELS_PER_TILE

        encoded = encode_4bpp_tile(max_pixels)
        decoded = decode_4bpp_tile(encoded, 0)

        assert decoded == max_pixels

    def test_alternating_pattern(self):
        """Test encoding/decoding with alternating pattern"""
        # Create checkerboard pattern
        pattern = []
        for y in range(TILE_HEIGHT):
            for x in range(TILE_WIDTH):
                pattern.append((x + y) % 2)

        encoded = encode_4bpp_tile(pattern)
        decoded = decode_4bpp_tile(encoded, 0)

        assert decoded == pattern

    def test_large_offset_decode_tiles(self):
        """Test decode_tiles with large start offset"""
        # Create large data buffer
        large_data = b'\x00' * 1000
        tiles = decode_tiles(large_data, 1, start_offset=500)

        assert len(tiles) == 1

    def test_decode_tiles_negative_offset_implicit(self):
        """Test that decode_tiles handles offsets properly"""
        data = b'\x00' * BYTES_PER_TILE_4BPP

        # Should work with valid offset
        tiles = decode_tiles(data, 1, start_offset=0)
        assert len(tiles) == 1

        # Should fail gracefully with offset that makes insufficient data
        tiles = decode_tiles(data, 1, start_offset=16)  # Only 16 bytes left
        assert len(tiles) == 0  # Not enough data for a full tile
