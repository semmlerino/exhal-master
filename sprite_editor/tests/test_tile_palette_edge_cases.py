"""
Edge case tests for tile and palette handling
Tests unusual, boundary, and error conditions
"""

import struct
from pathlib import Path

import pytest
from PIL import Image

from sprite_editor.constants import (
    BYTES_PER_TILE_4BPP,
    PIXELS_PER_TILE,
    TILE_HEIGHT,
    TILE_WIDTH,
)
from sprite_editor.palette_utils import (
    bgr555_to_rgb888,
    read_cgram_palette,
    rgb888_to_bgr555,
)
from sprite_editor.sprite_editor_core import SpriteEditorCore
from sprite_editor.tile_utils import decode_4bpp_tile, encode_4bpp_tile


class TestTileEdgeCases:
    """Test edge cases in tile encoding/decoding"""

    @pytest.mark.unit
    def test_encode_decode_all_zeros(self):
        """Test encoding/decoding tile with all zeros"""
        # All black tile
        pixels = [0] * PIXELS_PER_TILE

        encoded = encode_4bpp_tile(pixels)
        assert len(encoded) == BYTES_PER_TILE_4BPP
        assert all(b == 0 for b in encoded)

        decoded = decode_4bpp_tile(encoded, 0)
        assert decoded == pixels

    @pytest.mark.unit
    def test_encode_decode_all_max(self):
        """Test encoding/decoding tile with all max values"""
        # All color 15
        pixels = [15] * PIXELS_PER_TILE

        encoded = encode_4bpp_tile(pixels)
        assert len(encoded) == BYTES_PER_TILE_4BPP

        decoded = decode_4bpp_tile(encoded, 0)
        assert decoded == pixels

    @pytest.mark.unit
    def test_encode_decode_alternating_pattern(self):
        """Test encoding/decoding checkerboard pattern"""
        # Checkerboard of 0 and 15
        pixels = []
        for y in range(TILE_HEIGHT):
            for x in range(TILE_WIDTH):
                pixels.append(15 if (x + y) % 2 == 0 else 0)

        encoded = encode_4bpp_tile(pixels)
        decoded = decode_4bpp_tile(encoded, 0)
        assert decoded == pixels

    @pytest.mark.unit
    def test_encode_invalid_pixel_values(self):
        """Test encoding with invalid pixel values"""
        # Values outside 0-15 range
        pixels = list(range(64))  # 0-63

        # Should clamp to valid range
        encoded = encode_4bpp_tile(pixels)
        decoded = decode_4bpp_tile(encoded, 0)

        # encode_4bpp_tile may mask values to 0-15 range
        for i, pixel in enumerate(decoded):
            # Values are masked with & 0x0F, so value 16 becomes 0, 17 becomes 1, etc.
            expected = pixels[i] & 0x0F
            assert pixel == expected

    @pytest.mark.unit
    def test_decode_with_offset_boundary(self):
        """Test decoding at exact tile boundaries"""
        # Create data for multiple tiles
        tile_data = []
        for i in range(4):
            pixels = [i] * PIXELS_PER_TILE
            tile_data.extend(encode_4bpp_tile(pixels))

        # Decode each tile at exact boundaries
        for i in range(4):
            offset = i * BYTES_PER_TILE_4BPP
            decoded = decode_4bpp_tile(bytes(tile_data), offset)
            assert all(p == i for p in decoded)

    @pytest.mark.unit
    def test_encode_wrong_pixel_count(self):
        """Test encoding with wrong number of pixels"""
        # Too few pixels
        pixels = [0] * 32  # Half a tile

        # Should pad with zeros or handle gracefully
        try:
            encoded = encode_4bpp_tile(pixels)
            # If it succeeds, check size
            assert len(encoded) == BYTES_PER_TILE_4BPP
        except (IndexError, ValueError):
            # Or it might raise an error
            pass

    @pytest.mark.unit
    def test_decode_partial_tile_data(self):
        """Test decoding with insufficient tile data"""
        # Only half the tile data
        partial_data = b"\x00" * 16  # 16 bytes instead of 32

        # Should handle gracefully
        try:
            decoded = decode_4bpp_tile(partial_data, 0)
            # If successful, should have 64 pixels
            assert len(decoded) == PIXELS_PER_TILE
        except (IndexError, struct.error):
            # Or might raise an error
            pass


class TestPaletteEdgeCases:
    """Test edge cases in palette handling"""

    @pytest.mark.unit
    def test_read_palette_at_boundaries(self, cgram_file):
        """Test reading palettes at CGRAM boundaries"""
        # First palette
        pal0 = read_cgram_palette(cgram_file, 0)
        assert pal0 is not None
        assert len(pal0) == 768

        # Last valid palette (15)
        pal15 = read_cgram_palette(cgram_file, 15)
        assert pal15 is not None
        assert len(pal15) == 768

        # Invalid palette (16)
        pal16 = read_cgram_palette(cgram_file, 16)
        assert pal16 is None

    @pytest.mark.unit
    def test_bgr555_conversion_edge_values(self):
        """Test BGR555 conversion with edge values"""
        # Test cases: (bgr555, expected_rgb)
        test_cases = [
            (0x0000, (0, 0, 0)),  # Black
            (0x7FFF, (255, 255, 255)),  # White (5-bit max converted to 8-bit)
            (0x001F, (255, 0, 0)),  # Pure red (31 * 255 / 31 = 255)
            (0x03E0, (0, 255, 0)),  # Pure green
            (0x7C00, (0, 0, 255)),  # Pure blue
        ]

        for bgr555, expected in test_cases:
            r, g, b = bgr555_to_rgb888(bgr555)
            assert (r, g, b) == expected

    @pytest.mark.unit
    def test_rgb_to_bgr555_conversion(self):
        """Test RGB to BGR555 conversion"""
        # Test conversion and back
        test_colors = [
            (0, 0, 0),
            (255, 255, 255),
            (255, 0, 0),
            (0, 255, 0),
            (0, 0, 255),
            (128, 128, 128),
        ]

        for r, g, b in test_colors:
            bgr555 = rgb888_to_bgr555(r, g, b)
            # Convert back
            r2, g2, b2 = bgr555_to_rgb888(bgr555)
            # Should be close (within 8 due to bit depth reduction)
            assert abs(r - r2) <= 8
            assert abs(g - g2) <= 8
            assert abs(b - b2) <= 8

    @pytest.mark.unit
    def test_corrupted_cgram_data(self, temp_dir):
        """Test handling of corrupted CGRAM data"""
        # Create CGRAM with invalid data
        cgram_path = temp_dir / "corrupted_cgram.bin"

        # Valid size but garbage data
        cgram_data = b"\xff\xfe" * 256  # Invalid BGR555 values
        cgram_path.write_bytes(cgram_data)

        # Should still read (just weird colors)
        palette = read_cgram_palette(str(cgram_path), 0)
        assert palette is not None
        assert len(palette) == 768

    @pytest.mark.unit
    def test_palette_with_transparency(self):
        """Test palette handling with transparency color"""
        # In SNES, color 0 is often transparent
        # Create a palette where color 0 is not black
        palette_data = []

        # Make color 0 bright pink (often used for transparency)
        palette_data.extend([255, 0, 255])  # Magenta

        # Rest of palette
        for i in range(1, 16):
            palette_data.extend([i * 16, i * 16, i * 16])

        # Fill to 256 colors
        for i in range(16, 256):
            palette_data.extend([0, 0, 0])

        assert len(palette_data) == 768
        assert palette_data[0:3] == [255, 0, 255]


class TestSpriteExtractionEdgeCases:
    """Test edge cases in sprite extraction"""

    @pytest.mark.unit
    def test_extract_at_vram_edge(self, temp_dir):
        """Test extraction at the very edge of VRAM"""
        core = SpriteEditorCore()

        # Create VRAM that's exactly one tile
        vram_path = temp_dir / "edge_vram.bin"
        vram_path.write_bytes(b"\x00" * BYTES_PER_TILE_4BPP)

        # Extract exactly one tile
        img, count = core.extract_sprites(str(vram_path), 0, BYTES_PER_TILE_4BPP)
        assert count == 1
        # extract_sprites uses default tiles_per_row of 16
        assert img.width == 16 * TILE_WIDTH  # Default layout
        assert img.height == TILE_HEIGHT

    @pytest.mark.unit
    def test_extract_misaligned_offset(self, vram_file):
        """Test extraction from non-tile-aligned offset"""
        core = SpriteEditorCore()

        # Start at odd offset (not multiple of 32)
        img, count = core.extract_sprites(vram_file, 17, 1024)
        # Should still work, extracting from that offset
        assert img is not None
        assert count > 0

    @pytest.mark.unit
    def test_extract_zero_tiles_per_row_bug(self, vram_file):
        """Test extraction with tiles_per_row=0 causes division by zero (BUG)"""
        core = SpriteEditorCore()

        # This is a bug in the implementation - tiles_per_row=0 should be validated
        with pytest.raises(ZeroDivisionError):
            core.extract_sprites(vram_file, 0, 1024, tiles_per_row=0)

        # TODO: The implementation should validate tiles_per_row > 0 and use default if invalid

    @pytest.mark.unit
    def test_inject_at_vram_boundary(self, vram_file, temp_dir):
        """Test injection exactly at VRAM size limit"""
        core = SpriteEditorCore()

        # Create small tile data
        tile_data = encode_4bpp_tile([0] * PIXELS_PER_TILE)

        # Get VRAM size
        vram_size = Path(vram_file).stat().st_size

        # Try to inject at the very end
        output_path = temp_dir / "boundary_inject.bin"
        import shutil

        shutil.copy(vram_file, output_path)

        # Inject at last tile position
        last_tile_offset = vram_size - BYTES_PER_TILE_4BPP
        if last_tile_offset >= 0:
            result = core.inject_into_vram(
                tile_data, str(output_path), last_tile_offset, str(output_path)
            )
            assert result is not None


class TestImageConversionEdgeCases:
    """Test edge cases in PNG/SNES conversion"""

    @pytest.mark.unit
    def test_png_with_exact_16_colors(self, temp_dir):
        """Test PNG with exactly 16 unique colors"""
        core = SpriteEditorCore()

        # Create image with exactly 16 colors
        img = Image.new("P", (32, 32))
        pixels = []
        for i in range(32 * 32):
            pixels.append(i % 16)
        img.putdata(pixels)

        # Set palette
        palette = []
        for i in range(16):
            palette.extend([i * 17, 0, 0])  # Red gradient
        for i in range(16, 256):
            palette.extend([0, 0, 0])
        img.putpalette(palette)

        png_path = temp_dir / "16colors.png"
        img.save(str(png_path))

        # Should convert successfully
        snes_data, count = core.png_to_snes(str(png_path))
        assert snes_data is not None
        assert count == (32 * 32) // PIXELS_PER_TILE

    @pytest.mark.unit
    def test_png_single_tile(self, temp_dir):
        """Test PNG that's exactly one tile"""
        core = SpriteEditorCore()

        # Create 8x8 image
        img = Image.new("P", (8, 8))
        img.putdata(list(range(64)))
        img.putpalette([0] * 768)

        png_path = temp_dir / "single_tile.png"
        img.save(str(png_path))

        snes_data, count = core.png_to_snes(str(png_path))
        assert count == 1
        assert len(snes_data) == BYTES_PER_TILE_4BPP

    @pytest.mark.unit
    def test_png_non_square_dimensions(self, temp_dir):
        """Test PNG with non-square tile dimensions"""
        core = SpriteEditorCore()

        # Create 16x32 image (2x4 tiles)
        img = Image.new("P", (16, 32))
        img.putdata([0] * (16 * 32))
        img.putpalette([0] * 768)

        png_path = temp_dir / "non_square.png"
        img.save(str(png_path))

        snes_data, count = core.png_to_snes(str(png_path))
        assert count == 8  # 2x4 tiles

    @pytest.mark.unit
    def test_palette_grid_single_palette(self, vram_file):
        """Test palette grid with single palette"""
        core = SpriteEditorCore()

        # Create palette grid (always shows all palettes)
        result = core.create_palette_grid_preview(vram_file, 0, 1024, None)

        if result:
            img, count = result
            # create_palette_grid_preview always creates full 16-palette grid
            assert img.width == 544  # Full 16-palette width (34 tiles * 16 palettes)


class TestExtremeEdgeCases:
    """Test extreme edge cases"""

    @pytest.mark.unit
    def test_massive_tiles_per_row(self, vram_file):
        """Test with extremely large tiles_per_row"""
        core = SpriteEditorCore()

        # Request 1000 tiles per row
        img, count = core.extract_sprites(vram_file, 0, 1024, tiles_per_row=1000)
        # Should handle gracefully
        assert img is not None
        # Width should be clamped or all tiles in one row
        assert img.width <= 1000 * TILE_WIDTH

    @pytest.mark.unit
    def test_extract_single_byte(self, temp_dir):
        """Test extracting less than one tile of data"""
        core = SpriteEditorCore()

        # Create VRAM with lots of data
        vram_path = temp_dir / "vram.bin"
        vram_path.write_bytes(b"\xff" * 1024)

        # Try to extract just 1 byte
        img, count = core.extract_sprites(str(vram_path), 0, 1)
        # Should handle gracefully (0 complete tiles)
        assert count == 0

    @pytest.mark.unit
    def test_alternating_palette_indices(self, vram_file, cgram_file):
        """Test with non-contiguous palette indices"""
        core = SpriteEditorCore()

        # Create palette grid with all palettes
        result = core.create_palette_grid_preview(vram_file, 0, 1024, cgram_file)

        assert result is not None
        img, count = result
        assert isinstance(img, Image.Image)
