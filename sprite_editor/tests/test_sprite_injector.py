#!/usr/bin/env python3
"""
Tests for sprite_injector module
Tests core injection functionality with comprehensive coverage
"""

import os
from unittest.mock import patch

import pytest
from PIL import Image

from sprite_editor.sprite_injector import (
    create_preview,
    inject_into_vram,
    main,
    png_to_snes,
)
from sprite_editor.tile_utils import decode_4bpp_tile


@pytest.fixture
def temp_files(tmp_path):
    """Create temporary test files"""
    # Create test PNG (8x8 indexed image)
    png_file = tmp_path / "test.png"
    img = Image.new("P", (16, 16))  # 2x2 tiles

    # Create test pattern
    pixels = []
    for y in range(16):
        for x in range(16):
            pixels.append((x + y) % 16)
    img.putdata(pixels)

    # Set palette
    palette = []
    for i in range(16):
        palette.extend([i * 16, i * 16, i * 16])  # Grayscale
    for i in range(240):  # Fill rest of palette
        palette.extend([0, 0, 0])
    img.putpalette(palette)

    img.save(png_file)

    # Create test VRAM file (64KB)
    vram_file = tmp_path / "test.vram"
    vram_data = bytearray(0x10000)
    # Add some pattern
    for i in range(0, 0x10000, 2):
        vram_data[i] = i % 256
        vram_data[i + 1] = (i >> 8) % 256
    vram_file.write_bytes(vram_data)

    return {"png": str(png_file), "vram": str(vram_file), "dir": str(tmp_path)}


@pytest.mark.unit
class TestPngToSnes:
    """Test PNG to SNES conversion"""

    def test_png_to_snes_indexed(self, temp_files):
        """Test converting indexed PNG to SNES format"""
        result = png_to_snes(temp_files["png"])

        assert result is not None
        # 2x2 tiles = 4 tiles * 32 bytes per tile = 128 bytes
        assert len(result) == 128

        # Verify it's valid 4bpp data by decoding first tile
        first_tile = decode_4bpp_tile(result, 0)
        assert len(first_tile) == 64  # 8x8 pixels
        assert all(0 <= pixel <= 15 for pixel in first_tile)

    def test_png_to_snes_rgb_mode(self, tmp_path):
        """Test converting RGB PNG (should convert to indexed)"""
        # Create RGB image
        png_file = tmp_path / "rgb.png"
        img = Image.new("RGB", (8, 8))
        # Fill with colors
        pixels = []
        for y in range(8):
            for x in range(8):
                pixels.append((x * 32, y * 32, 0))
        img.putdata(pixels)
        img.save(png_file)

        # Capture print output
        with patch("builtins.print") as mock_print:
            result = png_to_snes(str(png_file))

        assert result is not None
        assert len(result) == 32  # 1 tile

        # Check warning was printed
        mock_print.assert_any_call(
            "Warning: Image is in RGB mode, converting to indexed..."
        )

    def test_png_to_snes_large_image(self, tmp_path):
        """Test converting larger image"""
        png_file = tmp_path / "large.png"
        img = Image.new("P", (128, 64))  # 16x8 tiles
        img.putdata([i % 16 for i in range(128 * 64)])
        img.save(png_file)

        result = png_to_snes(str(png_file))

        assert result is not None
        assert len(result) == 16 * 8 * 32  # 128 tiles * 32 bytes

    def test_png_to_snes_non_tile_aligned(self, tmp_path):
        """Test image not aligned to 8x8 tiles"""
        png_file = tmp_path / "unaligned.png"
        img = Image.new("P", (15, 15))  # Not tile-aligned
        img.putdata([0] * (15 * 15))
        img.save(png_file)

        result = png_to_snes(str(png_file))

        assert result is not None
        # Only gets tiles that fully fit: 1x1 tile in this case
        # since 15/8 = 1 with remainder
        assert len(result) == 1 * 32

    def test_png_to_snes_file_not_found(self):
        """Test with non-existent file"""
        with patch("builtins.print") as mock_print:
            result = png_to_snes("/nonexistent/file.png")

        assert result is None
        mock_print.assert_called_with(
            "Error converting PNG: [Errno 2] No such file or directory: '/nonexistent/file.png'"
        )

    def test_png_to_snes_invalid_image(self, tmp_path):
        """Test with invalid image file"""
        bad_file = tmp_path / "bad.png"
        bad_file.write_text("not a png")

        with patch("builtins.print") as mock_print:
            result = png_to_snes(str(bad_file))

        assert result is None
        assert mock_print.call_count > 0
        assert "Error converting PNG:" in mock_print.call_args[0][0]


@pytest.mark.unit
class TestInjectIntoVram:
    """Test VRAM injection"""

    def test_inject_into_vram_success(self, temp_files):
        """Test successful injection"""
        # Create test tile data
        tile_data = b"\x00" * 64  # 2 tiles
        output_file = os.path.join(temp_files["dir"], "output.vram")

        result = inject_into_vram(tile_data, temp_files["vram"], 0xC000, output_file)

        assert result is True
        assert os.path.exists(output_file)

        # Verify injection
        with open(output_file, "rb") as f:
            f.seek(0xC000)
            injected = f.read(64)
        assert injected == tile_data

    def test_inject_into_vram_boundary_check(self, temp_files):
        """Test injection at VRAM boundary"""
        # Try to inject past end of VRAM
        tile_data = b"\xff" * 0x2000  # 8KB
        output_file = os.path.join(temp_files["dir"], "output.vram")

        with patch("builtins.print") as mock_print:
            result = inject_into_vram(
                tile_data, temp_files["vram"], 0xF000, output_file  # Only 4KB left
            )

        assert result is False
        mock_print.assert_called_with(
            "Error: Tile data (8192 bytes) would exceed VRAM size at offset 0xf000"
        )

    def test_inject_into_vram_exact_boundary(self, temp_files):
        """Test injection exactly at boundary"""
        # Inject exactly to end of VRAM
        tile_data = b"\xaa" * 0x1000  # 4KB
        output_file = os.path.join(temp_files["dir"], "output.vram")

        result = inject_into_vram(
            tile_data, temp_files["vram"], 0xF000, output_file  # Exactly 4KB left
        )

        assert result is True

        # Verify last bytes
        with open(output_file, "rb") as f:
            f.seek(-1, 2)  # Seek to last byte
            last_byte = f.read(1)
        assert last_byte == b"\xaa"

    def test_inject_into_vram_file_not_found(self):
        """Test with non-existent VRAM file"""
        with patch("builtins.print") as mock_print:
            result = inject_into_vram(
                b"\x00" * 32, "/nonexistent/vram.dmp", 0, "output.vram"
            )

        assert result is False
        assert "Error injecting into VRAM:" in mock_print.call_args[0][0]

    def test_inject_into_vram_write_error(self, temp_files):
        """Test handling write errors"""
        tile_data = b"\x00" * 32
        output_file = "/invalid/path/output.vram"

        with patch("builtins.print") as mock_print:
            result = inject_into_vram(tile_data, temp_files["vram"], 0, output_file)

        assert result is False
        assert "Error injecting into VRAM:" in mock_print.call_args[0][0]


@pytest.mark.unit
class TestCreatePreview:
    """Test preview generation"""

    def test_create_preview_success(self, temp_files):
        """Test successful preview creation"""
        # First inject some data
        tile_data = bytes([i % 16 for i in range(32 * 4)])  # 4 tiles
        vram_file = temp_files["vram"]

        # Inject tiles
        with open(vram_file, "r+b") as f:
            f.seek(0x1000)
            f.write(tile_data)

        preview_file = os.path.join(temp_files["dir"], "preview.png")

        with patch("builtins.print") as mock_print:
            create_preview(vram_file, 0x1000, 128, preview_file)

        assert os.path.exists(preview_file)
        mock_print.assert_called_with(f"Created preview: {preview_file}")

        # Verify image
        img = Image.open(preview_file)
        assert img.size == (128, 8)  # 16 tiles wide, 1 row
        assert img.mode == "P"

    def test_create_preview_empty_data(self, temp_files):
        """Test preview with zero data area"""
        # First, ensure we have zeros at a specific offset
        vram_file = temp_files["vram"]
        with open(vram_file, "r+b") as f:
            f.seek(0x2000)
            f.write(b"\x00" * 128)  # Write zeros

        preview_file = os.path.join(temp_files["dir"], "preview.png")

        create_preview(vram_file, 0x2000, 128, preview_file)

        assert os.path.exists(preview_file)

        # Verify image is all zeros
        img = Image.open(preview_file)
        pixels = list(img.getdata())
        assert all(p == 0 for p in pixels)

    def test_create_preview_error_handling(self):
        """Test preview error handling"""
        with patch("builtins.print") as mock_print:
            create_preview("/nonexistent/vram.dmp", 0, 128, "preview.png")

        assert "Error creating preview:" in mock_print.call_args[0][0]


@pytest.mark.unit
class TestMainFunction:
    """Test main entry point"""

    def test_main_success(self, temp_files, monkeypatch):
        """Test successful main execution"""
        output_file = os.path.join(temp_files["dir"], "output.vram")

        # Mock command line arguments
        test_args = [
            "sprite_injector.py",
            temp_files["png"],
            "--vram",
            temp_files["vram"],
            "--offset",
            "0xC000",
            "--output",
            output_file,
            "--preview",
        ]
        monkeypatch.setattr("sys.argv", test_args)

        result = main()

        assert result == 0
        assert os.path.exists(output_file)
        assert os.path.exists(output_file.replace(".vram", "_preview.png"))

    def test_main_input_not_found(self, monkeypatch):
        """Test with missing input file"""
        test_args = ["sprite_injector.py", "/nonexistent/input.png"]
        monkeypatch.setattr("sys.argv", test_args)

        with patch("builtins.print") as mock_print:
            result = main()

        assert result == 1
        mock_print.assert_any_call(
            "Error: Input file '/nonexistent/input.png' not found"
        )

    def test_main_vram_not_found(self, temp_files, monkeypatch):
        """Test with missing VRAM file"""
        test_args = [
            "sprite_injector.py",
            temp_files["png"],
            "--vram",
            "/nonexistent/vram.dmp",
        ]
        monkeypatch.setattr("sys.argv", test_args)

        with patch("builtins.print") as mock_print:
            result = main()

        assert result == 1
        mock_print.assert_any_call("Error: VRAM file '/nonexistent/vram.dmp' not found")

    def test_main_conversion_failure(self, temp_files, monkeypatch):
        """Test handling conversion failure"""
        test_args = [
            "sprite_injector.py",
            temp_files["png"],
            "--vram",
            temp_files["vram"],
        ]
        monkeypatch.setattr("sys.argv", test_args)

        # Mock png_to_snes to fail
        with patch("sprite_editor.sprite_injector.png_to_snes", return_value=None):
            result = main()

        assert result == 1

    def test_main_injection_failure(self, temp_files, monkeypatch):
        """Test handling injection failure"""
        test_args = [
            "sprite_injector.py",
            temp_files["png"],
            "--vram",
            temp_files["vram"],
        ]
        monkeypatch.setattr("sys.argv", test_args)

        # Mock inject_into_vram to fail
        with patch(
            "sprite_editor.sprite_injector.inject_into_vram", return_value=False
        ):
            result = main()

        assert result == 1


@pytest.mark.integration
class TestSpriteInjectorIntegration:
    """Integration tests for sprite injector"""

    def test_full_injection_workflow(self, temp_files):
        """Test complete PNG to VRAM injection workflow"""
        # Create a specific test pattern PNG
        png_file = temp_files["png"]
        Image.open(png_file)

        # Convert to SNES
        tile_data = png_to_snes(png_file)
        assert tile_data is not None

        # Inject into VRAM
        output_vram = os.path.join(temp_files["dir"], "injected.vram")
        result = inject_into_vram(tile_data, temp_files["vram"], 0x8000, output_vram)
        assert result is True

        # Create preview
        preview_file = os.path.join(temp_files["dir"], "preview.png")
        create_preview(output_vram, 0x8000, len(tile_data), preview_file)
        assert os.path.exists(preview_file)

        # Verify round-trip by decoding tiles
        with open(output_vram, "rb") as f:
            f.seek(0x8000)
            injected_data = f.read(len(tile_data))

        assert injected_data == tile_data
