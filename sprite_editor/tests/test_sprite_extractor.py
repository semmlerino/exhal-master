#!/usr/bin/env python3
"""
Tests for sprite_extractor module
Tests core extraction functionality with comprehensive coverage
"""

import os
from unittest.mock import patch

import pytest
from PIL import Image

from sprite_editor.palette_utils import write_cgram_palette
from sprite_editor.sprite_extractor import extract_sprites, main
from sprite_editor.tile_utils import encode_4bpp_tile


@pytest.fixture
def temp_files(tmp_path):
    """Create temporary test files with known tile patterns"""
    # Create test VRAM file with pattern tiles
    vram_file = tmp_path / "test.vram"
    vram_data = bytearray(0x10000)  # 64KB

    # Create recognizable tile patterns at different offsets
    # Pattern 1: Gradient tile at 0xC000
    gradient_tile = []
    for y in range(8):
        for x in range(8):
            gradient_tile.append((x + y) % 16)
    gradient_data = encode_4bpp_tile(gradient_tile)

    # Pattern 2: Checkerboard at 0xC020
    checker_tile = []
    for y in range(8):
        for x in range(8):
            checker_tile.append(0 if (x + y) % 2 == 0 else 15)
    checker_data = encode_4bpp_tile(checker_tile)

    # Pattern 3: Solid colors
    for color in range(16):
        solid_tile = [color] * 64
        solid_data = encode_4bpp_tile(solid_tile)
        vram_data[0xC000 + 0x40 + color * 32 : 0xC000 + 0x40 + (color + 1) * 32] = (
            solid_data
        )

    # Write patterns
    vram_data[0xC000:0xC020] = gradient_data
    vram_data[0xC020:0xC040] = checker_data

    vram_file.write_bytes(vram_data)

    # Create test CGRAM file with palettes
    cgram_file = tmp_path / "test.cgram"
    cgram_data = bytearray(512)

    # Create test palette (grayscale gradient)
    test_palette = []
    for i in range(16):
        gray = i * 17  # 0-255 in 16 steps
        test_palette.extend([gray, gray, gray])

    # Write palette 0
    palette_data = write_cgram_palette(test_palette, 0)
    cgram_data[0:32] = palette_data

    cgram_file.write_bytes(cgram_data)

    return {"vram": str(vram_file), "cgram": str(cgram_file), "dir": str(tmp_path)}


@pytest.mark.unit
class TestExtractSprites:
    """Test sprite extraction functionality"""

    def test_extract_sprites_basic(self, temp_files):
        """Test basic sprite extraction"""
        img = extract_sprites(
            temp_files["vram"], 0xC000, 128, tiles_per_row=2  # 4 tiles
        )

        assert img is not None
        assert img.size == (16, 16)  # 2x2 tiles
        assert img.mode == "P"

        # Check that we have pixel data
        pixels = list(img.getdata())
        assert len(pixels) == 256
        assert not all(p == 0 for p in pixels)  # Should have non-zero data

    def test_extract_sprites_large_area(self, temp_files):
        """Test extracting larger sprite area"""
        img = extract_sprites(
            temp_files["vram"], 0xC000, 0x1000, tiles_per_row=16  # 128 tiles
        )

        assert img is not None
        assert img.size == (128, 64)  # 16x8 tiles

        # Verify dimensions calculation
        with patch("builtins.print") as mock_print:
            extract_sprites(temp_files["vram"], 0xC000, 0x1000, 16)

        mock_print.assert_any_call("Extracting 128 tiles (16x8)")
        mock_print.assert_any_call("Image size: 128x64 pixels")

    def test_extract_sprites_custom_width(self, temp_files):
        """Test extraction with custom tiles per row"""
        img = extract_sprites(
            temp_files["vram"], 0xC000, 256, tiles_per_row=4  # 8 tiles
        )

        assert img is not None
        assert img.size == (32, 16)  # 4x2 tiles

    def test_extract_sprites_partial_tile(self, temp_files):
        """Test extraction with incomplete last tile"""
        # Request size that's not tile-aligned
        img = extract_sprites(
            temp_files["vram"], 0xC000, 100, tiles_per_row=8  # 3.125 tiles
        )

        assert img is not None
        # Should still create space for 4 tiles (rounds up)
        assert img.size == (64, 8)  # 8x1 tiles

    def test_extract_sprites_at_boundary(self, temp_files):
        """Test extraction at VRAM boundary"""
        # Extract from near end of VRAM
        img = extract_sprites(
            temp_files["vram"], 0xFF00, 256, tiles_per_row=8  # 8 tiles
        )

        assert img is not None
        assert img.size == (64, 8)

    def test_extract_sprites_file_not_found(self):
        """Test with non-existent VRAM file"""
        with patch("builtins.print") as mock_print:
            img = extract_sprites("/nonexistent/vram.dmp", 0, 128, 16)

        assert img is None
        assert "Error extracting sprites:" in mock_print.call_args[0][0]

    def test_extract_sprites_read_error(self, temp_files):
        """Test handling read errors"""
        # Mock file read to raise exception
        with patch("builtins.open", side_effect=OSError("Read error")):
            with patch("builtins.print") as mock_print:
                img = extract_sprites(temp_files["vram"], 0, 128, 16)

        assert img is None
        assert "Error extracting sprites: Read error" in mock_print.call_args[0][0]

    def test_extract_sprites_palette_preservation(self, temp_files):
        """Test that palette is set correctly"""
        img = extract_sprites(temp_files["vram"], 0xC000, 32, tiles_per_row=1)  # 1 tile

        assert img is not None

        # Check palette
        palette = img.getpalette()
        assert palette is not None

        # Verify grayscale palette (default)
        for i in range(16):
            expected_gray = (i * 255) // 15
            r, g, b = palette[i * 3], palette[i * 3 + 1], palette[i * 3 + 2]
            assert r == g == b == expected_gray


@pytest.mark.unit
class TestMainFunction:
    """Test main entry point"""

    def test_main_success(self, temp_files, monkeypatch):
        """Test successful main execution"""
        output_file = os.path.join(temp_files["dir"], "output.png")

        # Mock command line arguments
        test_args = [
            "sprite_extractor.py",
            "--vram",
            temp_files["vram"],
            "--offset",
            "0xC000",
            "--size",
            "0x400",
            "--output",
            output_file,
            "--width",
            "8",
        ]
        monkeypatch.setattr("sys.argv", test_args)

        result = main()

        assert result == 0
        assert os.path.exists(output_file)

        # Verify output image
        img = Image.open(output_file)
        assert img.size == (64, 32)  # 8x4 tiles
        assert img.mode == "P"

    def test_main_with_palette(self, temp_files, monkeypatch):
        """Test extraction with palette application"""
        output_file = os.path.join(temp_files["dir"], "output_pal.png")

        # Create CGRAM.dmp in same directory as VRAM
        cgram_path = os.path.join(os.path.dirname(temp_files["vram"]), "CGRAM.dmp")
        with open(temp_files["cgram"], "rb") as src:
            cgram_data = src.read()
        with open(cgram_path, "wb") as dst:
            dst.write(cgram_data)

        test_args = [
            "sprite_extractor.py",
            "--vram",
            temp_files["vram"],
            "--offset",
            "0xC000",
            "--size",
            "0x100",
            "--output",
            output_file,
            "--palette",
            "0",
        ]
        monkeypatch.setattr("sys.argv", test_args)

        # Change working directory to VRAM directory
        original_cwd = os.getcwd()
        try:
            os.chdir(os.path.dirname(temp_files["vram"]))

            with patch("builtins.print") as mock_print:
                result = main()

            assert result == 0
            mock_print.assert_any_call("Applying palette 0...")

        finally:
            os.chdir(original_cwd)

    def test_main_vram_not_found(self, monkeypatch):
        """Test with missing VRAM file"""
        test_args = ["sprite_extractor.py", "--vram", "/nonexistent/vram.dmp"]
        monkeypatch.setattr("sys.argv", test_args)

        with patch("builtins.print") as mock_print:
            result = main()

        assert result == 1
        mock_print.assert_any_call("Error: VRAM file '/nonexistent/vram.dmp' not found")

    def test_main_extraction_failure(self, temp_files, monkeypatch):
        """Test handling extraction failure"""
        test_args = ["sprite_extractor.py", "--vram", temp_files["vram"]]
        monkeypatch.setattr("sys.argv", test_args)

        # Mock extract_sprites to fail
        with patch("sprite_editor.sprite_extractor.extract_sprites", return_value=None):
            result = main()

        assert result == 1

    def test_main_hex_parsing(self, temp_files, monkeypatch):
        """Test hex value parsing"""
        output_file = os.path.join(temp_files["dir"], "hex_test.png")

        test_args = [
            "sprite_extractor.py",
            "--vram",
            temp_files["vram"],
            "--offset",
            "0xc000",  # lowercase hex
            "--size",
            "0X200",  # uppercase X
            "--output",
            output_file,
        ]
        monkeypatch.setattr("sys.argv", test_args)

        with patch("builtins.print") as mock_print:
            result = main()

        assert result == 0
        # Verify values were parsed correctly
        mock_print.assert_any_call("Offset: 0xc000 (VRAM $0x6000)")
        mock_print.assert_any_call("Size: 0x200 (512 bytes)")

    def test_main_default_values(self, temp_files, monkeypatch):
        """Test with default argument values"""
        # Change to VRAM directory so default filenames work
        original_cwd = os.getcwd()
        vram_dir = os.path.dirname(temp_files["vram"])

        # Copy test VRAM to default name
        default_vram = os.path.join(vram_dir, "VRAM.dmp")
        with open(temp_files["vram"], "rb") as src:
            vram_data = src.read()
        with open(default_vram, "wb") as dst:
            dst.write(vram_data)

        try:
            os.chdir(vram_dir)

            test_args = ["sprite_extractor.py"]
            monkeypatch.setattr("sys.argv", test_args)

            result = main()

            assert result == 0
            assert os.path.exists("sprites_to_edit.png")

            # Check default values were used
            img = Image.open("sprites_to_edit.png")
            # Default: offset=0xC000, size=0x4000, width=16
            assert img.size == (128, 256)  # 16x32 tiles

        finally:
            os.chdir(original_cwd)


@pytest.mark.integration
class TestSpriteExtractorIntegration:
    """Integration tests for sprite extractor"""

    def test_extract_inject_roundtrip(self, temp_files):
        """Test extracting sprites and verifying data integrity"""
        # Extract sprites
        img = extract_sprites(
            temp_files["vram"], 0xC000, 0x400, tiles_per_row=8  # 32 tiles
        )
        assert img is not None

        # Save and reload
        output_png = os.path.join(temp_files["dir"], "extracted.png")
        img.save(output_png)

        # Reload and verify
        reloaded = Image.open(output_png)
        assert reloaded.size == img.size
        assert reloaded.mode == img.mode

        # Verify pixel data matches
        orig_pixels = list(img.getdata())
        reloaded_pixels = list(reloaded.getdata())
        assert orig_pixels == reloaded_pixels

    def test_extract_known_patterns(self, temp_files):
        """Test extraction of known tile patterns"""
        # Extract the gradient and checkerboard tiles we created
        img = extract_sprites(
            temp_files["vram"], 0xC000, 64, tiles_per_row=2  # 2 tiles
        )

        pixels = list(img.getdata())

        # First tile should be gradient
        first_tile = []
        for y in range(8):
            for x in range(8):
                pixel_idx = y * 16 + x  # 2 tiles per row
                first_tile.append(pixels[pixel_idx])

        # Verify gradient pattern
        expected_gradient = []
        for y in range(8):
            for x in range(8):
                expected_gradient.append((x + y) % 16)

        assert first_tile == expected_gradient
