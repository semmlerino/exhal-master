#!/usr/bin/env python3
"""
Tests for png_to_snes module
Tests PNG to SNES conversion functionality with comprehensive coverage
"""

import os
from unittest.mock import patch

import pytest
from PIL import Image

from sprite_editor.png_to_snes import main, png_to_snes


@pytest.fixture
def temp_files(tmp_path):
    """Create temporary test files with various image types"""
    # Create indexed PNG (2x2 tiles = 16x16 pixels)
    indexed_file = tmp_path / "indexed.png"
    img = Image.new("P", (16, 16))

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
    img.save(indexed_file)

    # Create RGB PNG
    rgb_file = tmp_path / "rgb.png"
    rgb_img = Image.new("RGB", (16, 16))
    rgb_pixels = []
    for y in range(16):
        for x in range(16):
            rgb_pixels.append((x * 16, y * 16, 0))
    rgb_img.putdata(rgb_pixels)
    rgb_img.save(rgb_file)

    # Create single tile PNG (8x8)
    single_tile_file = tmp_path / "single_tile.png"
    single_img = Image.new("P", (8, 8))
    single_img.putdata([i % 16 for i in range(64)])
    single_img.putpalette(palette)
    single_img.save(single_tile_file)

    # Create large PNG (4x4 tiles = 32x32 pixels)
    large_file = tmp_path / "large.png"
    large_img = Image.new("P", (32, 32))
    large_img.putdata([i % 16 for i in range(32 * 32)])
    large_img.putpalette(palette)
    large_img.save(large_file)

    # Create non-tile-aligned PNG (15x15 pixels)
    unaligned_file = tmp_path / "unaligned.png"
    unaligned_img = Image.new("P", (15, 15))
    unaligned_img.putdata([0] * (15 * 15))
    unaligned_img.putpalette(palette)
    unaligned_img.save(unaligned_file)

    return {
        "indexed": str(indexed_file),
        "rgb": str(rgb_file),
        "single_tile": str(single_tile_file),
        "large": str(large_file),
        "unaligned": str(unaligned_file),
        "dir": str(tmp_path),
    }


@pytest.mark.unit
class TestPngToSnes:
    """Test PNG to SNES conversion functionality"""

    def test_png_to_snes_indexed_basic(self, temp_files):
        """Test basic conversion of indexed PNG"""
        output_file = os.path.join(temp_files["dir"], "output.bin")

        with patch("builtins.print") as mock_print:
            result = png_to_snes(temp_files["indexed"], output_file)

        # 2x2 tiles = 4 tiles * 32 bytes per tile = 128 bytes
        assert result == 128
        assert os.path.exists(output_file)

        # Check file size
        with open(output_file, "rb") as f:
            data = f.read()
        assert len(data) == 128

        # Check print messages
        print_calls = [call[0][0] for call in mock_print.call_args_list]
        assert any("Converting 2x2 tiles (4 total)" in call for call in print_calls)
        assert any(f"Wrote 128 bytes to {output_file}" in call for call in print_calls)

    def test_png_to_snes_rgb_mode(self, temp_files):
        """Test conversion of RGB PNG (should convert to indexed)"""
        output_file = os.path.join(temp_files["dir"], "rgb_output.bin")

        with patch("builtins.print") as mock_print:
            result = png_to_snes(temp_files["rgb"], output_file)

        # Should convert and produce data
        assert result == 128  # 2x2 tiles
        assert os.path.exists(output_file)

        # Check conversion message was printed
        print_calls = [call[0][0] for call in mock_print.call_args_list]
        assert any(
            "Converting to indexed color mode..." in call for call in print_calls
        )

    def test_png_to_snes_single_tile(self, temp_files):
        """Test conversion of single tile"""
        output_file = os.path.join(temp_files["dir"], "single_output.bin")

        with patch("builtins.print") as mock_print:
            result = png_to_snes(temp_files["single_tile"], output_file)

        # 1 tile = 32 bytes
        assert result == 32

        # Check tile count in output
        print_calls = [call[0][0] for call in mock_print.call_args_list]
        assert any("Converting 1x1 tiles (1 total)" in call for call in print_calls)

    def test_png_to_snes_large_image(self, temp_files):
        """Test conversion of larger image"""
        output_file = os.path.join(temp_files["dir"], "large_output.bin")

        with patch("builtins.print") as mock_print:
            result = png_to_snes(temp_files["large"], output_file)

        # 4x4 tiles = 16 tiles * 32 bytes = 512 bytes
        assert result == 512

        print_calls = [call[0][0] for call in mock_print.call_args_list]
        assert any("Converting 4x4 tiles (16 total)" in call for call in print_calls)

    def test_png_to_snes_non_tile_aligned(self, temp_files):
        """Test conversion of non-tile-aligned image"""
        output_file = os.path.join(temp_files["dir"], "unaligned_output.bin")

        with patch("builtins.print") as mock_print:
            result = png_to_snes(temp_files["unaligned"], output_file)

        # 15x15 pixels = 1x1 complete tiles (since 15//8 = 1)
        assert result == 32  # 1 tile

        print_calls = [call[0][0] for call in mock_print.call_args_list]
        assert any("Converting 1x1 tiles (1 total)" in call for call in print_calls)

    def test_png_to_snes_file_not_found(self):
        """Test with non-existent input file"""
        with pytest.raises(FileNotFoundError):
            png_to_snes("/nonexistent/file.png", "output.bin")

    def test_png_to_snes_invalid_image(self, tmp_path):
        """Test with invalid image file"""
        bad_file = tmp_path / "bad.png"
        bad_file.write_text("not a png file")

        output_file = tmp_path / "output.bin"

        with pytest.raises(Exception):  # PIL will raise an exception
            png_to_snes(str(bad_file), str(output_file))

    def test_png_to_snes_write_error(self, temp_files):
        """Test handling write errors"""
        # Try to write to invalid path
        invalid_output = "/invalid/path/output.bin"

        with pytest.raises(FileNotFoundError):
            png_to_snes(temp_files["indexed"], invalid_output)

    def test_png_to_snes_pixel_value_clamping(self, tmp_path):
        """Test that pixel values are clamped to 4-bit"""
        # Create image with high pixel values
        test_file = tmp_path / "high_values.png"
        img = Image.new("P", (8, 8))

        # Create pixels with values > 15
        high_pixels = [i % 256 for i in range(64)]  # Some values > 15
        img.putdata(high_pixels)

        # Set palette
        palette = []
        for i in range(256):
            palette.extend([i, i, i])
        img.putpalette(palette)
        img.save(test_file)

        output_file = tmp_path / "clamped_output.bin"

        # Should not raise error and should clamp values
        result = png_to_snes(str(test_file), str(output_file))
        assert result == 32  # 1 tile

        # Verify output file exists and has correct size
        assert os.path.exists(output_file)
        with open(output_file, "rb") as f:
            data = f.read()
        assert len(data) == 32

    def test_png_to_snes_tile_data_integrity(self, temp_files):
        """Test that tile data is encoded correctly"""
        output_file = os.path.join(temp_files["dir"], "integrity_test.bin")

        # Mock encode_4bpp_tile to verify it's called correctly
        with patch("sprite_editor.png_to_snes.encode_4bpp_tile") as mock_encode:
            mock_encode.return_value = b"\\x00" * 32  # Mock tile data

            png_to_snes(temp_files["single_tile"], output_file)

        # Should call encode_4bpp_tile once for single tile
        mock_encode.assert_called_once()

        # Check the tile pixels passed to encoder
        call_args = mock_encode.call_args[0][0]
        assert len(call_args) == 64  # 8x8 pixels
        assert all(0 <= pixel <= 15 for pixel in call_args)  # All 4-bit values

    def test_png_to_snes_tile_ordering(self, temp_files):
        """Test that tiles are processed in correct order"""
        # Use 2x2 tile image to test ordering
        output_file = os.path.join(temp_files["dir"], "ordering_test.bin")

        with patch("sprite_editor.png_to_snes.encode_4bpp_tile") as mock_encode:
            mock_encode.return_value = b"\\x00" * 32

            png_to_snes(temp_files["indexed"], output_file)

        # Should be called 4 times for 2x2 tiles
        assert mock_encode.call_count == 4

        # Verify all calls have 64 pixels each
        for call in mock_encode.call_args_list:
            pixels = call[0][0]
            assert len(pixels) == 64


@pytest.mark.unit
class TestMainFunction:
    """Test main entry point"""

    def test_main_success(self, temp_files, monkeypatch):
        """Test successful main execution"""
        output_file = os.path.join(temp_files["dir"], "main_output.bin")

        test_args = ["png_to_snes.py", temp_files["indexed"], output_file]
        monkeypatch.setattr("sys.argv", test_args)

        with patch("builtins.print"):
            main()

        assert os.path.exists(output_file)

    def test_main_insufficient_arguments(self, monkeypatch):
        """Test main with insufficient arguments"""
        test_args = ["png_to_snes.py"]
        monkeypatch.setattr("sys.argv", test_args)

        with patch("builtins.print") as mock_print:
            with pytest.raises(SystemExit) as exc_info:
                main()

        assert exc_info.value.code == 1
        mock_print.assert_called_with(
            "Usage: python png_to_snes.py input.png output.bin"
        )

    def test_main_one_argument(self, monkeypatch):
        """Test main with only one argument"""
        test_args = ["png_to_snes.py", "input.png"]
        monkeypatch.setattr("sys.argv", test_args)

        with patch("builtins.print") as mock_print:
            with pytest.raises(SystemExit) as exc_info:
                main()

        assert exc_info.value.code == 1
        mock_print.assert_called_with(
            "Usage: python png_to_snes.py input.png output.bin"
        )

    def test_main_file_not_found(self, monkeypatch, tmp_path):
        """Test main with non-existent input file"""
        output_file = tmp_path / "output.bin"

        test_args = ["png_to_snes.py", "/nonexistent/file.png", str(output_file)]
        monkeypatch.setattr("sys.argv", test_args)

        with pytest.raises(FileNotFoundError):
            main()

    def test_main_calls_png_to_snes(self, temp_files, monkeypatch):
        """Test that main properly calls png_to_snes function"""
        output_file = os.path.join(temp_files["dir"], "main_call_test.bin")

        test_args = ["png_to_snes.py", temp_files["indexed"], output_file]
        monkeypatch.setattr("sys.argv", test_args)

        with patch("sprite_editor.png_to_snes.png_to_snes") as mock_convert:
            main()

        mock_convert.assert_called_once_with(temp_files["indexed"], output_file)


@pytest.mark.integration
class TestPngToSnesIntegration:
    """Integration tests for PNG to SNES conversion"""

    def test_full_conversion_workflow(self, temp_files):
        """Test complete conversion workflow"""
        output_file = os.path.join(temp_files["dir"], "workflow_output.bin")

        # Convert PNG to SNES
        result = png_to_snes(temp_files["indexed"], output_file)

        # Verify output
        assert result > 0
        assert os.path.exists(output_file)

        # Read and verify output data
        with open(output_file, "rb") as f:
            data = f.read()

        assert len(data) == result
        assert len(data) % 32 == 0  # Should be multiple of tile size

    def test_round_trip_compatibility(self, temp_files):
        """Test that output is compatible with tile decoder"""
        from sprite_editor.tile_utils import decode_4bpp_tile

        output_file = os.path.join(temp_files["dir"], "roundtrip_test.bin")

        # Convert PNG to SNES format
        png_to_snes(temp_files["single_tile"], output_file)

        # Read output and decode first tile
        with open(output_file, "rb") as f:
            tile_data = f.read(32)  # Read first tile

        # Should be able to decode without error
        pixels = decode_4bpp_tile(tile_data, 0)
        assert len(pixels) == 64  # 8x8 pixels
        assert all(0 <= pixel <= 15 for pixel in pixels)

    def test_batch_conversion_simulation(self, temp_files):
        """Test converting multiple files in sequence"""
        test_files = [
            temp_files["indexed"],
            temp_files["single_tile"],
            temp_files["large"],
        ]
        expected_sizes = [128, 32, 512]  # Expected output sizes

        for i, (input_file, expected_size) in enumerate(
            zip(test_files, expected_sizes)
        ):
            output_file = os.path.join(temp_files["dir"], f"batch_{i}.bin")

            result = png_to_snes(input_file, output_file)

            assert result == expected_size
            assert os.path.exists(output_file)

    def test_different_image_modes_workflow(self, temp_files):
        """Test workflow with different image modes"""
        # Test indexed mode (should work directly)
        indexed_output = os.path.join(temp_files["dir"], "indexed_workflow.bin")
        indexed_result = png_to_snes(temp_files["indexed"], indexed_output)

        # Test RGB mode (should convert then work)
        rgb_output = os.path.join(temp_files["dir"], "rgb_workflow.bin")
        rgb_result = png_to_snes(temp_files["rgb"], rgb_output)

        # Both should produce same size output (same dimensions)
        assert indexed_result == rgb_result
        assert os.path.exists(indexed_output)
        assert os.path.exists(rgb_output)

    def test_error_handling_workflow(self, tmp_path):
        """Test error handling in real workflow scenarios"""
        # Test with completely invalid file
        bad_file = tmp_path / "bad.txt"
        bad_file.write_text("This is not an image")
        output_file = tmp_path / "error_output.bin"

        with pytest.raises(Exception):
            png_to_snes(str(bad_file), str(output_file))

        # Output file should not be created on error
        assert not os.path.exists(output_file)

    def test_large_image_performance(self, tmp_path):
        """Test performance with larger images"""
        # Create larger test image (8x8 tiles = 64x64 pixels)
        large_file = tmp_path / "performance_test.png"
        img = Image.new("P", (64, 64))

        # Create pattern
        pixels = [i % 16 for i in range(64 * 64)]
        img.putdata(pixels)

        # Set palette
        palette = []
        for i in range(16):
            palette.extend([i * 16, i * 16, i * 16])
        for i in range(240):
            palette.extend([0, 0, 0])
        img.putpalette(palette)
        img.save(large_file)

        output_file = tmp_path / "performance_output.bin"

        # Should handle without issues
        result = png_to_snes(str(large_file), str(output_file))

        # 8x8 tiles = 64 tiles * 32 bytes = 2048 bytes
        assert result == 2048
        assert os.path.exists(output_file)
