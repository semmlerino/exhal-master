"""
Tests for sprite_editor_core.py - Core sprite editing functionality
"""

import pytest
from pathlib import Path
from PIL import Image

from sprite_editor.sprite_editor_core import SpriteEditorCore
from sprite_editor.security_utils import SecurityError
from sprite_editor.constants import *

class TestTileEncoding:
    """Test 4bpp tile encoding/decoding"""

    @pytest.mark.unit
    def test_decode_4bpp_tile(self, sample_4bpp_tile):
        """Test decoding a 4bpp tile"""
        core = SpriteEditorCore()
        tile_pixels = core.decode_4bpp_tile(sample_4bpp_tile, 0)

        # Should have 64 pixels
        assert len(tile_pixels) == PIXELS_PER_TILE

        # Check diagonal pattern (from fixture)
        for y in range(TILE_HEIGHT):
            for x in range(TILE_WIDTH):
                pixel = tile_pixels[y * TILE_WIDTH + x]
                if x == y:
                    assert pixel == 1  # Diagonal should be color 1
                else:
                    assert pixel == 0  # Rest should be 0

    @pytest.mark.unit
    def test_encode_decode_roundtrip(self):
        """Test that encoding and decoding are inverse operations"""
        core = SpriteEditorCore()

        # Create a test pattern
        test_pixels = []
        for y in range(TILE_HEIGHT):
            for x in range(TILE_WIDTH):
                # Checkerboard pattern with colors 0-15
                test_pixels.append((x + y) % 16)

        # Encode to 4bpp
        encoded = core.encode_4bpp_tile(test_pixels)
        assert len(encoded) == BYTES_PER_TILE_4BPP

        # Decode back
        decoded = core.decode_4bpp_tile(encoded, 0)

        # Should match original
        assert decoded == test_pixels

    @pytest.mark.unit
    def test_encode_out_of_range_pixels(self):
        """Test encoding handles out of range pixel values"""
        core = SpriteEditorCore()

        # Create pixels with values > 15
        bad_pixels = [20, 30, 255] * 22  # 66 values, truncate to 64
        bad_pixels = bad_pixels[:64]

        # Should encode without error (masked to 4 bits)
        encoded = core.encode_4bpp_tile(bad_pixels)
        decoded = core.decode_4bpp_tile(encoded, 0)

        # Values should be masked to 0-15
        for pixel in decoded:
            assert 0 <= pixel <= 15

class TestPaletteHandling:
    """Test CGRAM palette reading"""

    @pytest.mark.unit
    def test_read_cgram_palette(self, cgram_file):
        """Test reading a palette from CGRAM"""
        palette = SpriteEditorCore.read_cgram_palette(cgram_file, 0)

        # Should have 768 RGB values (256 colors * 3)
        assert len(palette) == 768

        # First 16 colors should be our test pattern
        for i in range(16):
            r = palette[i * 3]
            g = palette[i * 3 + 1]
            b = palette[i * 3 + 2]
            # All channels should have similar values from our test data
            assert abs(r - g) < 10
            assert abs(g - b) < 10

    @pytest.mark.unit
    def test_invalid_palette_number(self, cgram_file):
        """Test handling of invalid palette number"""
        # Palette 16 doesn't exist (0-15 only)
        palette = SpriteEditorCore.read_cgram_palette(cgram_file, 16)

        # Should return None or handle gracefully
        assert palette is None

    @pytest.mark.unit
    def test_grayscale_palette(self):
        """Test generation of default grayscale palette"""
        core = SpriteEditorCore()
        palette = core.get_grayscale_palette()

        assert len(palette) == 768

        # Check first 16 colors are grayscale
        for i in range(16):
            r = palette[i * 3]
            g = palette[i * 3 + 1]
            b = palette[i * 3 + 2]
            assert r == g == b  # Grayscale
            assert r == (i * 255) // 15  # Correct intensity

class TestSpriteExtraction:
    """Test sprite extraction from VRAM"""

    @pytest.mark.unit
    def test_extract_sprites_basic(self, vram_file):
        """Test basic sprite extraction"""
        core = SpriteEditorCore()
        img, tile_count = core.extract_sprites(vram_file, 0, 1024)

        # Check return values
        assert isinstance(img, Image.Image)
        assert img.mode == 'P'  # Indexed color
        assert tile_count == 32  # 1024 bytes / 32 bytes per tile

        # Check dimensions
        assert img.width == DEFAULT_TILES_PER_ROW * TILE_WIDTH
        assert img.height >= TILE_HEIGHT

    @pytest.mark.unit
    def test_extract_sprites_custom_layout(self, vram_file):
        """Test extraction with custom tile layout"""
        core = SpriteEditorCore()
        img, tile_count = core.extract_sprites(vram_file, 0, 512, tiles_per_row=8)

        assert img.width == 8 * TILE_WIDTH  # 64 pixels
        assert tile_count == 16  # 512 bytes / 32 bytes per tile

    @pytest.mark.unit
    def test_extract_sprites_offset(self, vram_file):
        """Test extraction from offset"""
        core = SpriteEditorCore()
        img, tile_count = core.extract_sprites(vram_file, 0x1000, 256)

        assert tile_count == 8  # 256 bytes / 32 bytes per tile

class TestPNGConversion:
    """Test PNG to SNES conversion"""

    @pytest.mark.unit
    def test_png_to_snes_valid(self, temp_dir):
        """Test converting valid indexed PNG to SNES format"""
        # Create a test indexed PNG
        img = Image.new('P', (16, 16))  # 2x2 tiles
        pixels = []
        for y in range(16):
            for x in range(16):
                pixels.append((x + y) % 16)
        img.putdata(pixels)

        # Set a palette
        palette = []
        for i in range(16):
            palette.extend([i * 17, i * 17, i * 17])
        for i in range(16, 256):
            palette.extend([0, 0, 0])
        img.putpalette(palette)

        png_path = temp_dir / "test.png"
        img.save(str(png_path))

        # Convert to SNES
        core = SpriteEditorCore()
        snes_data, tile_count = core.png_to_snes(str(png_path))

        assert len(snes_data) == 4 * BYTES_PER_TILE_4BPP  # 4 tiles
        assert tile_count == 4

    @pytest.mark.unit
    def test_png_to_snes_wrong_mode(self, temp_dir):
        """Test error when PNG is not indexed mode"""
        # Create RGB PNG
        img = Image.new('RGB', (16, 16))
        png_path = temp_dir / "rgb.png"
        img.save(str(png_path))

        core = SpriteEditorCore()
        with pytest.raises(ValueError, match="must be in indexed color mode"):
            core.png_to_snes(str(png_path))

    @pytest.mark.unit
    def test_png_to_snes_wrong_dimensions(self, temp_dir):
        """Test handling of non-tile-aligned dimensions"""
        # Create 15x15 image (not multiple of 8)
        img = Image.new('P', (15, 15))
        png_path = temp_dir / "wrong_size.png"
        img.save(str(png_path))

        core = SpriteEditorCore()
        # Should still work, padding tiles
        snes_data, tile_count = core.png_to_snes(str(png_path))
        assert tile_count == 4  # 2x2 tiles needed

class TestVRAMInjection:
    """Test injecting tile data into VRAM"""

    @pytest.mark.unit
    def test_inject_into_vram_basic(self, vram_file, temp_dir, sample_4bpp_tile):
        """Test basic VRAM injection"""
        core = SpriteEditorCore()
        output_path = str(temp_dir / "modified_vram.dmp")

        # Inject one tile at offset 0x1000
        result = core.inject_into_vram(sample_4bpp_tile, vram_file, 0x1000, output_path)

        assert result == output_path
        assert Path(output_path).exists()

        # Verify the data was injected
        with open(output_path, 'rb') as f:
            f.seek(0x1000)
            injected_data = f.read(32)

        assert injected_data == sample_4bpp_tile

    @pytest.mark.unit
    def test_inject_bounds_checking(self, vram_file, temp_dir):
        """Test bounds checking during injection"""
        core = SpriteEditorCore()

        # Try to inject past end of VRAM
        huge_data = b'\x00' * 10000
        with pytest.raises(ValueError, match="would exceed VRAM size"):
            core.inject_into_vram(huge_data, vram_file, 60000, None)

        # Try negative offset
        with pytest.raises(ValueError, match="Invalid negative offset"):
            core.inject_into_vram(b'\x00' * 32, vram_file, -1, None)

    @pytest.mark.unit
    def test_inject_oversized_data(self, vram_file):
        """Test rejection of oversized tile data"""
        core = SpriteEditorCore()

        # Try to inject more than 64KB of data
        huge_data = b'\x00' * (65 * 1024)
        with pytest.raises(ValueError, match="Tile data too large"):
            core.inject_into_vram(huge_data, vram_file, 0, None)

class TestPNGValidation:
    """Test PNG validation for SNES compatibility"""

    @pytest.mark.unit
    def test_validate_png_valid(self, temp_dir):
        """Test validation of valid PNG"""
        # Create valid indexed PNG
        img = Image.new('P', (16, 16))
        img.putdata([i % 16 for i in range(256)])
        png_path = temp_dir / "valid.png"
        img.save(str(png_path))

        core = SpriteEditorCore()
        valid, issues = core.validate_png_for_snes(str(png_path))

        assert valid is True
        assert len(issues) == 0

    @pytest.mark.unit
    def test_validate_png_wrong_mode(self, temp_dir):
        """Test validation catches wrong color mode"""
        img = Image.new('RGBA', (16, 16))
        png_path = temp_dir / "rgba.png"
        img.save(str(png_path))

        core = SpriteEditorCore()
        valid, issues = core.validate_png_for_snes(str(png_path))

        assert valid is False
        assert any("RGBA mode" in issue for issue in issues)

    @pytest.mark.unit
    def test_validate_png_wrong_dimensions(self, temp_dir):
        """Test validation catches wrong dimensions"""
        img = Image.new('P', (15, 17))  # Not multiples of 8
        png_path = temp_dir / "wrong_dims.png"
        img.save(str(png_path))

        core = SpriteEditorCore()
        valid, issues = core.validate_png_for_snes(str(png_path))

        assert valid is False
        assert any("Width" in issue for issue in issues)
        assert any("Height" in issue for issue in issues)

    @pytest.mark.unit
    def test_validate_png_too_many_colors(self, temp_dir):
        """Test validation catches too many colors"""
        img = Image.new('P', (16, 16))
        # Create a pattern that uses exactly 20 different palette indices
        pixels = []
        for i in range(256):
            pixels.append(i % 20)  # This will use palette indices 0-19
        img.putdata(pixels)

        # Create a palette with 256 colors to ensure indices 0-19 are valid
        palette = []
        for i in range(256):
            palette.extend([i, i, i])  # Grayscale palette
        img.putpalette(palette)

        png_path = temp_dir / "many_colors.png"
        img.save(str(png_path))

        core = SpriteEditorCore()
        valid, issues = core.validate_png_for_snes(str(png_path))

        assert valid is False
        assert any("Too many colors" in issue for issue in issues)

class TestVRAMInfo:
    """Test VRAM file information"""

    @pytest.mark.unit
    def test_get_vram_info_standard(self, vram_file):
        """Test getting info for standard VRAM file"""
        core = SpriteEditorCore()
        info = core.get_vram_info(vram_file)

        assert info is not None
        assert info['size'] == 65536
        assert "64KB" in info['size_text']
        assert info['max_offset'] == 65535

    @pytest.mark.unit
    def test_get_vram_info_nonstandard(self, temp_dir):
        """Test getting info for non-standard size"""
        small_vram = temp_dir / "small_vram.dmp"
        small_vram.write_bytes(b'\x00' * 32768)

        core = SpriteEditorCore()
        info = core.get_vram_info(str(small_vram))

        assert info['size'] == 32768
        assert "32KB" in info['size_text']

class TestOAMIntegration:
    """Test OAM palette mapping integration"""

    @pytest.mark.unit
    def test_load_oam_mapping(self, oam_file):
        """Test loading OAM data into core"""
        core = SpriteEditorCore()
        success = core.load_oam_mapping(oam_file)

        assert success is True
        assert core.oam_mapper is not None

    @pytest.mark.unit
    def test_extract_with_oam_palettes(self, vram_file, cgram_file, oam_file):
        """Test extraction with OAM-based palette assignment"""
        core = SpriteEditorCore()
        core.load_oam_mapping(oam_file)

        # Extract with correct palettes
        img, tile_count = core.extract_sprites_with_correct_palettes(
            vram_file, 0, 512, cgram_file
        )

        assert isinstance(img, Image.Image)
        assert img.mode == 'RGBA'  # Should be RGBA for multi-palette

    @pytest.mark.unit
    def test_multi_palette_extraction(self, vram_file, cgram_file, oam_file):
        """Test multi-palette extraction"""
        core = SpriteEditorCore()
        core.load_oam_mapping(oam_file)

        palette_images, tile_count = core.extract_sprites_multi_palette(
            vram_file, 0, 512, cgram_file
        )

        assert isinstance(palette_images, dict)
        # Should have at least one palette
        assert len(palette_images) >= 1

    @pytest.mark.unit
    def test_palette_grid_preview(self, vram_file, cgram_file):
        """Test creating palette grid preview"""
        core = SpriteEditorCore()

        grid_img, tile_count = core.create_palette_grid_preview(
            vram_file, 0, 512, cgram_file
        )

        assert isinstance(grid_img, Image.Image)
        assert grid_img.mode == 'RGB'
        # Grid should be 4x base image size (4x4 grid)
        assert grid_img.width >= 512  # At least 4 * 128