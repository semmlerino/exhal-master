#!/usr/bin/env python3
"""
Comprehensive test suite for png_to_snes.py CLI utility

Tests PNG to SNES 4bpp tile conversion functionality including:
- Valid PNG conversion scenarios
- Error handling for invalid inputs
- Command-line interface behavior
- File I/O operations
"""

import os
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import png_to_snes
import pytest
from PIL import Image


class TestPngToSnesFunction(unittest.TestCase):
    """Test the core png_to_snes() conversion function."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up test fixtures."""
        # Clean up temp files
        for file in os.listdir(self.temp_dir):
            os.remove(os.path.join(self.temp_dir, file))
        os.rmdir(self.temp_dir)

    def create_test_image(self, width=16, height=16, mode="P", colors=None):
        """Create a test PNG image for conversion."""
        if colors is None:
            colors = list(range(16))  # Default 16-color palette

        img = Image.new(mode, (width, height))

        if mode == "P":
            # Set up indexed palette
            palette = []
            for i in range(256):
                if i < len(colors):
                    # Create distinct colors for each palette entry
                    r = (i * 17) % 256
                    g = (i * 37) % 256
                    b = (i * 73) % 256
                else:
                    r = g = b = 0
                palette.extend([r, g, b])
            img.putpalette(palette)

            # Fill with test pattern
            pixels = []
            for y in range(height):
                for x in range(width):
                    pixel_val = (x + y) % len(colors)
                    pixels.append(pixel_val)
            img.putdata(pixels)

        return img

    def test_valid_png_conversion_16x16(self):
        """Test conversion of valid 16x16 indexed PNG."""
        input_path = os.path.join(self.temp_dir, "test_16x16.png")
        output_path = os.path.join(self.temp_dir, "test_output.bin")

        # Create 16x16 test image (2x2 tiles)
        img = self.create_test_image(16, 16)
        img.save(input_path)

        # Convert
        result = png_to_snes.png_to_snes(input_path, output_path)

        # Verify output
        assert isinstance(result, int)
        assert result == 128  # 4 tiles * 32 bytes each
        assert os.path.exists(output_path)

        # Check file size
        with open(output_path, "rb") as f:
            data = f.read()
        assert len(data) == 128

    def test_valid_png_conversion_8x8(self):
        """Test conversion of valid 8x8 indexed PNG (single tile)."""
        input_path = os.path.join(self.temp_dir, "test_8x8.png")
        output_path = os.path.join(self.temp_dir, "test_output.bin")

        # Create 8x8 test image (1 tile)
        img = self.create_test_image(8, 8)
        img.save(input_path)

        # Convert
        result = png_to_snes.png_to_snes(input_path, output_path)

        # Verify output
        assert result == 32  # 1 tile * 32 bytes

        # Check file contents are valid 4bpp data
        with open(output_path, "rb") as f:
            data = f.read()
        assert len(data) == 32

    def test_non_indexed_png_auto_conversion(self):
        """Test that non-indexed PNGs are automatically converted."""
        input_path = os.path.join(self.temp_dir, "test_rgb.png")
        output_path = os.path.join(self.temp_dir, "test_output.bin")

        # Create RGB image
        img = Image.new("RGB", (8, 8), (255, 0, 0))  # Red image
        img.save(input_path)

        # Convert (should auto-convert to indexed)
        with patch("builtins.print"):  # Suppress conversion message
            result = png_to_snes.png_to_snes(input_path, output_path)

        # Should succeed
        assert result == 32
        assert os.path.exists(output_path)

    def test_large_image_multiple_tiles(self):
        """Test conversion of larger image with multiple tiles."""
        input_path = os.path.join(self.temp_dir, "test_large.png")
        output_path = os.path.join(self.temp_dir, "test_output.bin")

        # Create 32x24 image (4x3 = 12 tiles)
        img = self.create_test_image(32, 24)
        img.save(input_path)

        # Convert
        result = png_to_snes.png_to_snes(input_path, output_path)

        # Verify output
        expected_bytes = 12 * 32  # 12 tiles * 32 bytes each
        assert result == expected_bytes

    def test_4bit_pixel_masking(self):
        """Test that pixel values are properly masked to 4-bit."""
        input_path = os.path.join(self.temp_dir, "test_mask.png")
        output_path = os.path.join(self.temp_dir, "test_output.bin")

        # Create image with palette indices that need masking
        img = self.create_test_image(
            8, 8, colors=list(range(32))
        )  # Use more than 16 colors
        img.save(input_path)

        # Convert
        result = png_to_snes.png_to_snes(input_path, output_path)

        # Should succeed (values should be masked to 4-bit)
        assert result == 32


class TestPngToSnesErrorHandling(unittest.TestCase):
    """Test error handling scenarios."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up test fixtures."""
        for file in os.listdir(self.temp_dir):
            os.remove(os.path.join(self.temp_dir, file))
        os.rmdir(self.temp_dir)

    def test_nonexistent_input_file(self):
        """Test handling of non-existent input file."""
        input_path = os.path.join(self.temp_dir, "nonexistent.png")
        output_path = os.path.join(self.temp_dir, "output.bin")

        # Should handle file not found gracefully
        with pytest.raises(FileNotFoundError):
            png_to_snes.png_to_snes(input_path, output_path)

    def test_invalid_image_file(self):
        """Test handling of invalid image file."""
        input_path = os.path.join(self.temp_dir, "invalid.png")
        output_path = os.path.join(self.temp_dir, "output.bin")

        # Create invalid file
        with open(input_path, "w") as f:
            f.write("not an image")

        # Should handle invalid image gracefully
        with pytest.raises(Exception):
            png_to_snes.png_to_snes(input_path, output_path)

    def test_output_directory_not_writable(self):
        """Test handling of non-writable output directory."""
        input_path = os.path.join(self.temp_dir, "test.png")
        output_path = "/root/nonexistent/output.bin"  # Likely non-writable

        # Create valid input
        img = Image.new("P", (8, 8))
        img.save(input_path)

        # Should handle write failure gracefully
        with pytest.raises(Exception):
            png_to_snes.png_to_snes(input_path, output_path)

    @patch("png_to_snes.encode_4bpp_tile")
    def test_encoding_failure(self, mock_encode):
        """Test handling of tile encoding failure."""
        input_path = os.path.join(self.temp_dir, "test.png")
        output_path = os.path.join(self.temp_dir, "output.bin")

        # Create valid input
        img = Image.new("P", (8, 8))
        img.save(input_path)

        # Mock encoding failure
        mock_encode.side_effect = Exception("Encoding failed")

        # Should propagate encoding error
        with pytest.raises(Exception):
            png_to_snes.png_to_snes(input_path, output_path)


class TestPngToSnesCommandLine(unittest.TestCase):
    """Test command-line interface behavior."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up test fixtures."""
        for file in os.listdir(self.temp_dir):
            os.remove(os.path.join(self.temp_dir, file))
        os.rmdir(self.temp_dir)

    def test_main_with_valid_args(self):
        """Test main() function with valid arguments."""
        input_path = os.path.join(self.temp_dir, "test.png")
        output_path = os.path.join(self.temp_dir, "output.bin")

        # Create test image
        img = Image.new("P", (8, 8))
        img.save(input_path)

        # Mock sys.argv
        with patch.object(sys, "argv", ["png_to_snes.py", input_path, output_path]):
            # Should run without error
            png_to_snes.main()

        # Check output was created
        assert os.path.exists(output_path)

    def test_main_insufficient_args(self):
        """Test main() function with insufficient arguments."""
        with patch.object(sys, "argv", ["png_to_snes.py"]):
            with patch("builtins.print") as mock_print:
                with patch.object(sys, "exit") as mock_exit:
                    # Mock sys.exit to raise SystemExit so we can catch it
                    mock_exit.side_effect = SystemExit(1)

                    with pytest.raises(SystemExit):
                        png_to_snes.main()

                    # Should print usage and exit
                    mock_print.assert_called_with(
                        "Usage: python png_to_snes.py input.png output.bin"
                    )
                    mock_exit.assert_called_with(1)

    def test_main_with_missing_input(self):
        """Test main() function with missing input file."""
        input_path = os.path.join(self.temp_dir, "nonexistent.png")
        output_path = os.path.join(self.temp_dir, "output.bin")

        with patch.object(sys, "argv", ["png_to_snes.py", input_path, output_path]):
            # Should raise FileNotFoundError (main doesn't handle this)
            with pytest.raises(FileNotFoundError):
                png_to_snes.main()


class TestPngToSnesIntegration(unittest.TestCase):
    """Integration tests for the complete workflow."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up test fixtures."""
        for file in os.listdir(self.temp_dir):
            os.remove(os.path.join(self.temp_dir, file))
        os.rmdir(self.temp_dir)

    def test_roundtrip_compatibility(self):
        """Test that converted data can be decoded back properly."""
        input_path = os.path.join(self.temp_dir, "test.png")
        output_path = os.path.join(self.temp_dir, "output.bin")

        # Create test image with known single tile pattern
        img = Image.new("P", (8, 8))  # Single tile

        # Set palette
        palette = []
        for i in range(256):
            r = (i * 17) % 256
            g = (i * 37) % 256
            b = (i * 73) % 256
            palette.extend([r, g, b])
        img.putpalette(palette)

        # Create known pattern: simple gradient
        pixels = []
        for _y in range(8):
            for x in range(8):
                # Gradient from 0-7, clamped to 4-bit
                pixels.append(min(x, 15))

        img.putdata(pixels)
        img.save(input_path)

        # Convert
        result = png_to_snes.png_to_snes(input_path, output_path)

        # Verify structure
        assert result == 32  # 1 tile * 32 bytes

        with open(output_path, "rb") as f:
            data = f.read()

        # Verify we have the expected data size
        assert len(data) == 32

        # Test that the conversion can be decoded back
        from tile_utils import decode_4bpp_tile

        # Decode the tile
        decoded = decode_4bpp_tile(data, 0)

        # Verify we got 64 pixels back
        assert len(decoded) == 64

        # Verify all pixels are in valid 4-bit range
        for pixel in decoded:
            assert pixel >= 0
            assert pixel <= 15

        # Verify the pattern has some variation (not all the same)
        unique_values = set(decoded)
        assert len(unique_values) > 1

    def test_subprocess_execution(self):
        """Test executing as subprocess."""
        input_path = os.path.join(self.temp_dir, "test.png")
        output_path = os.path.join(self.temp_dir, "output.bin")

        # Create test image
        img = Image.new("P", (8, 8))
        img.save(input_path)

        # Run as subprocess
        cmd = [sys.executable, "png_to_snes.py", input_path, output_path]
        result = subprocess.run(
            cmd,
            check=False,
            cwd="/mnt/c/CustomScripts/KirbyMax/workshop/exhal-master/sprite_editor",
            capture_output=True,
            text=True,
        )

        # Should succeed
        assert result.returncode == 0
        assert os.path.exists(output_path)


if __name__ == "__main__":
    unittest.main()
