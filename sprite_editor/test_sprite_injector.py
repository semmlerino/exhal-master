#!/usr/bin/env python3
"""
Comprehensive test suite for sprite_injector.py CLI utility

Tests sprite injection functionality including:
- PNG to SNES conversion within injector context
- VRAM injection operations 
- Preview generation
- Command-line interface behavior
- Error handling scenarios
"""

import unittest
import tempfile
import os
import sys
import subprocess
import argparse
from unittest.mock import patch, MagicMock, mock_open
from PIL import Image
import sprite_injector


class TestSpriteInjectorPngConversion(unittest.TestCase):
    """Test PNG conversion functionality within sprite injector."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up test fixtures."""
        for file in os.listdir(self.temp_dir):
            os.remove(os.path.join(self.temp_dir, file))
        os.rmdir(self.temp_dir)

    def create_test_png(self, width=8, height=8, pattern='solid'):
        """Create a test PNG file."""
        img = Image.new('P', (width, height))
        
        # Set palette
        palette = []
        for i in range(256):
            r = (i * 17) % 256
            g = (i * 37) % 256  
            b = (i * 73) % 256
            palette.extend([r, g, b])
        img.putpalette(palette)
        
        # Create pattern
        pixels = []
        if pattern == 'solid':
            pixels = [0] * (width * height)
        elif pattern == 'gradient':
            for y in range(height):
                for x in range(width):
                    pixels.append((x + y) % 16)
        elif pattern == 'checkerboard':
            for y in range(height):
                for x in range(width):
                    pixels.append((x + y) % 2)
        
        img.putdata(pixels)
        return img

    def test_png_to_snes_valid_indexed(self):
        """Test PNG to SNES conversion with valid indexed image."""
        png_path = os.path.join(self.temp_dir, 'test.png')
        
        # Create test image
        img = self.create_test_png(16, 16, 'gradient')
        img.save(png_path)
        
        # Convert
        result = sprite_injector.png_to_snes(png_path)
        
        # Should return valid tile data
        self.assertIsInstance(result, bytes)
        self.assertEqual(len(result), 128)  # 4 tiles * 32 bytes each

    def test_png_to_snes_non_indexed_conversion(self):
        """Test PNG to SNES conversion with auto-conversion from RGB."""
        png_path = os.path.join(self.temp_dir, 'test_rgb.png')
        
        # Create RGB image
        img = Image.new('RGB', (8, 8), (255, 0, 0))
        img.save(png_path)
        
        # Convert (should auto-convert)
        with patch('builtins.print'):  # Suppress warning output
            result = sprite_injector.png_to_snes(png_path)
        
        # Should succeed
        self.assertIsInstance(result, bytes)
        self.assertEqual(len(result), 32)  # 1 tile * 32 bytes

    def test_png_to_snes_large_image(self):
        """Test PNG to SNES conversion with larger image."""
        png_path = os.path.join(self.temp_dir, 'test_large.png')
        
        # Create 32x24 image (4x3 = 12 tiles)
        img = self.create_test_png(32, 24, 'checkerboard')
        img.save(png_path)
        
        # Convert
        result = sprite_injector.png_to_snes(png_path)
        
        # Should return correct amount of data
        self.assertEqual(len(result), 384)  # 12 tiles * 32 bytes each

    def test_png_to_snes_nonexistent_file(self):
        """Test PNG to SNES conversion with nonexistent file."""
        png_path = os.path.join(self.temp_dir, 'nonexistent.png')
        
        # Should return None for error
        result = sprite_injector.png_to_snes(png_path)
        self.assertIsNone(result)

    def test_png_to_snes_invalid_file(self):
        """Test PNG to SNES conversion with invalid image file."""
        png_path = os.path.join(self.temp_dir, 'invalid.png')
        
        # Create invalid file
        with open(png_path, 'w') as f:
            f.write("not an image")
        
        # Should return None for error
        result = sprite_injector.png_to_snes(png_path)
        self.assertIsNone(result)

    @patch('sprite_injector.encode_4bpp_tile')
    def test_png_to_snes_encoding_error(self, mock_encode):
        """Test PNG to SNES conversion with encoding error."""
        png_path = os.path.join(self.temp_dir, 'test.png')
        
        # Create valid image
        img = self.create_test_png()
        img.save(png_path)
        
        # Mock encoding failure
        mock_encode.side_effect = Exception("Encoding failed")
        
        # Should return None for error
        result = sprite_injector.png_to_snes(png_path)
        self.assertIsNone(result)


class TestSpriteInjectorVRAMOperations(unittest.TestCase):
    """Test VRAM injection and preview operations."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up test fixtures."""
        for file in os.listdir(self.temp_dir):
            os.remove(os.path.join(self.temp_dir, file))
        os.rmdir(self.temp_dir)

    def test_inject_into_vram_success(self):
        """Test successful VRAM injection."""
        vram_path = os.path.join(self.temp_dir, 'vram.dmp')
        output_path = os.path.join(self.temp_dir, 'vram_out.dmp')
        
        # Create test VRAM file
        vram_data = b'\x00' * 0x10000  # 64KB VRAM
        with open(vram_path, 'wb') as f:
            f.write(vram_data)
        
        # Create test tile data
        tile_data = b'\xFF' * 64  # 2 tiles of test data
        
        # Inject
        result = sprite_injector.inject_into_vram(tile_data, vram_path, 0x1000, output_path)
        
        # Should succeed
        self.assertTrue(result)
        self.assertTrue(os.path.exists(output_path))
        
        # Verify injection
        with open(output_path, 'rb') as f:
            modified_vram = f.read()
        
        # Check that data was injected at correct offset
        self.assertEqual(modified_vram[0x1000:0x1000 + 64], tile_data)
        self.assertEqual(modified_vram[:0x1000], b'\x00' * 0x1000)  # Before injection
        self.assertEqual(len(modified_vram), 0x10000)  # Same total size

    def test_inject_into_vram_offset_overflow(self):
        """Test VRAM injection with offset that would overflow."""
        vram_path = os.path.join(self.temp_dir, 'vram.dmp')
        output_path = os.path.join(self.temp_dir, 'vram_out.dmp')
        
        # Create small VRAM file
        vram_data = b'\x00' * 100
        with open(vram_path, 'wb') as f:
            f.write(vram_data)
        
        # Create tile data that would overflow
        tile_data = b'\xFF' * 64
        
        # Inject at offset that would overflow
        result = sprite_injector.inject_into_vram(tile_data, vram_path, 90, output_path)
        
        # Should fail
        self.assertFalse(result)
        self.assertFalse(os.path.exists(output_path))

    def test_inject_into_vram_nonexistent_input(self):
        """Test VRAM injection with nonexistent input file."""
        vram_path = os.path.join(self.temp_dir, 'nonexistent.dmp')
        output_path = os.path.join(self.temp_dir, 'vram_out.dmp')
        
        tile_data = b'\xFF' * 32
        
        # Should fail gracefully
        result = sprite_injector.inject_into_vram(tile_data, vram_path, 0, output_path)
        self.assertFalse(result)

    def test_inject_into_vram_write_error(self):
        """Test VRAM injection with write error."""
        vram_path = os.path.join(self.temp_dir, 'vram.dmp')
        output_path = '/root/nonexistent/vram_out.dmp'  # Likely non-writable
        
        # Create valid VRAM file
        with open(vram_path, 'wb') as f:
            f.write(b'\x00' * 1000)
        
        tile_data = b'\xFF' * 32
        
        # Should fail due to write error
        result = sprite_injector.inject_into_vram(tile_data, vram_path, 0, output_path)
        self.assertFalse(result)


class TestSpriteInjectorPreview(unittest.TestCase):
    """Test preview generation functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up test fixtures."""
        for file in os.listdir(self.temp_dir):
            os.remove(os.path.join(self.temp_dir, file))
        os.rmdir(self.temp_dir)

    def test_create_preview_success(self):
        """Test successful preview creation."""
        vram_path = os.path.join(self.temp_dir, 'vram.dmp')
        preview_path = os.path.join(self.temp_dir, 'preview.png')
        
        # Create test VRAM with some tile data
        from tile_utils import encode_4bpp_tile
        tile1 = encode_4bpp_tile([i % 16 for i in range(64)])  # Gradient tile
        tile2 = encode_4bpp_tile([(i // 8) % 16 for i in range(64)])  # Different pattern
        
        vram_data = b'\x00' * 0x1000 + tile1 + tile2 + b'\x00' * (0x10000 - 0x1000 - 64)
        with open(vram_path, 'wb') as f:
            f.write(vram_data)
        
        # Create preview
        sprite_injector.create_preview(vram_path, 0x1000, 64, preview_path)
        
        # Should create preview file
        self.assertTrue(os.path.exists(preview_path))
        
        # Verify it's a valid PNG
        try:
            img = Image.open(preview_path)
            self.assertEqual(img.mode, 'P')  # Should be indexed
            self.assertGreater(img.width, 0)
            self.assertGreater(img.height, 0)
        except Exception as e:
            self.fail(f"Preview PNG is invalid: {e}")

    def test_create_preview_empty_data(self):
        """Test preview creation with empty data."""
        vram_path = os.path.join(self.temp_dir, 'vram.dmp')
        preview_path = os.path.join(self.temp_dir, 'preview.png')
        
        # Create VRAM with empty data
        vram_data = b'\x00' * 0x1000
        with open(vram_path, 'wb') as f:
            f.write(vram_data)
        
        # Create preview
        sprite_injector.create_preview(vram_path, 0, 64, preview_path)
        
        # Should still create preview file
        self.assertTrue(os.path.exists(preview_path))

    def test_create_preview_nonexistent_file(self):
        """Test preview creation with nonexistent VRAM file."""
        vram_path = os.path.join(self.temp_dir, 'nonexistent.dmp')
        preview_path = os.path.join(self.temp_dir, 'preview.png')
        
        # Should handle error gracefully
        sprite_injector.create_preview(vram_path, 0, 64, preview_path)
        
        # Should not create preview file
        self.assertFalse(os.path.exists(preview_path))

    def test_create_preview_large_tiles(self):
        """Test preview creation with many tiles."""
        vram_path = os.path.join(self.temp_dir, 'vram.dmp')
        preview_path = os.path.join(self.temp_dir, 'preview.png')
        
        # Create VRAM with multiple tiles
        vram_data = b'\x00' * 0x1000 + b'\xFF' * (32 * 64)  # 64 tiles of data
        with open(vram_path, 'wb') as f:
            f.write(vram_data)
        
        # Create preview for all tiles
        sprite_injector.create_preview(vram_path, 0x1000, 32 * 64, preview_path)
        
        # Should create preview
        self.assertTrue(os.path.exists(preview_path))
        
        # Check dimensions (16 tiles wide layout)
        img = Image.open(preview_path)
        expected_width = 16 * 8  # 16 tiles wide
        expected_height = 4 * 8   # 4 tiles high (64 tiles / 16 per row)
        self.assertEqual(img.width, expected_width)
        self.assertEqual(img.height, expected_height)


class TestSpriteInjectorCommandLine(unittest.TestCase):
    """Test command-line interface behavior."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up test fixtures."""
        for file in os.listdir(self.temp_dir):
            os.remove(os.path.join(self.temp_dir, file))
        os.rmdir(self.temp_dir)

    def create_test_files(self):
        """Create test PNG and VRAM files."""
        png_path = os.path.join(self.temp_dir, 'test.png')
        vram_path = os.path.join(self.temp_dir, 'VRAM.dmp')
        
        # Create test PNG
        img = Image.new('P', (8, 8))
        img.save(png_path)
        
        # Create test VRAM
        with open(vram_path, 'wb') as f:
            f.write(b'\x00' * 0x10000)
        
        return png_path, vram_path

    def test_main_basic_functionality(self):
        """Test main() with basic valid arguments."""
        png_path, vram_path = self.create_test_files()
        output_path = os.path.join(self.temp_dir, 'VRAM_edited.dmp')
        
        # Mock sys.argv
        test_args = ['sprite_injector.py', png_path, '--vram', vram_path, '--output', output_path]
        with patch.object(sys, 'argv', test_args):
            result = sprite_injector.main()
        
        # Should succeed
        self.assertEqual(result, 0)
        self.assertTrue(os.path.exists(output_path))

    def test_main_with_preview(self):
        """Test main() with preview generation."""
        png_path, vram_path = self.create_test_files()
        output_path = os.path.join(self.temp_dir, 'VRAM_edited.dmp')
        
        # Mock sys.argv with preview flag
        test_args = ['sprite_injector.py', png_path, '--vram', vram_path, '--output', output_path, '--preview']
        with patch.object(sys, 'argv', test_args):
            result = sprite_injector.main()
        
        # Should succeed and create preview
        self.assertEqual(result, 0)
        self.assertTrue(os.path.exists(output_path))
        
        # Check for preview file
        preview_path = output_path.replace('.dmp', '_preview.png')
        self.assertTrue(os.path.exists(preview_path))

    def test_main_missing_png_file(self):
        """Test main() with missing PNG file."""
        png_path = os.path.join(self.temp_dir, 'nonexistent.png')
        _, vram_path = self.create_test_files()
        
        test_args = ['sprite_injector.py', png_path, '--vram', vram_path]
        with patch.object(sys, 'argv', test_args):
            result = sprite_injector.main()
        
        # Should fail
        self.assertEqual(result, 1)

    def test_main_missing_vram_file(self):
        """Test main() with missing VRAM file."""
        png_path, _ = self.create_test_files()
        vram_path = os.path.join(self.temp_dir, 'nonexistent.dmp')
        
        test_args = ['sprite_injector.py', png_path, '--vram', vram_path]
        with patch.object(sys, 'argv', test_args):
            result = sprite_injector.main()
        
        # Should fail
        self.assertEqual(result, 1)

    def test_main_png_conversion_failure(self):
        """Test main() with PNG conversion failure."""
        png_path = os.path.join(self.temp_dir, 'invalid.png')
        _, vram_path = self.create_test_files()
        
        # Create invalid PNG
        with open(png_path, 'w') as f:
            f.write("not an image")
        
        test_args = ['sprite_injector.py', png_path, '--vram', vram_path]
        with patch.object(sys, 'argv', test_args):
            result = sprite_injector.main()
        
        # Should fail
        self.assertEqual(result, 1)

    def test_main_injection_failure(self):
        """Test main() with injection failure."""
        png_path, vram_path = self.create_test_files()
        
        # Mock injection failure
        with patch('sprite_injector.inject_into_vram', return_value=False):
            test_args = ['sprite_injector.py', png_path, '--vram', vram_path]
            with patch.object(sys, 'argv', test_args):
                result = sprite_injector.main()
        
        # Should fail
        self.assertEqual(result, 1)

    def test_main_custom_offset(self):
        """Test main() with custom offset."""
        png_path, vram_path = self.create_test_files()
        
        test_args = ['sprite_injector.py', png_path, '--vram', vram_path, '--offset', '0x8000']
        with patch.object(sys, 'argv', test_args):
            result = sprite_injector.main()
        
        # Should succeed
        self.assertEqual(result, 0)


class TestSpriteInjectorIntegration(unittest.TestCase):
    """Integration tests for complete workflow."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up test fixtures."""
        for file in os.listdir(self.temp_dir):
            os.remove(os.path.join(self.temp_dir, file))
        os.rmdir(self.temp_dir)

    def test_complete_workflow(self):
        """Test complete injection workflow."""
        png_path = os.path.join(self.temp_dir, 'sprite.png')
        vram_path = os.path.join(self.temp_dir, 'VRAM.dmp')
        output_path = os.path.join(self.temp_dir, 'VRAM_edited.dmp')
        
        # Create test PNG with distinct pattern
        img = Image.new('P', (16, 8))  # 2 tiles
        palette = []
        for i in range(256):
            palette.extend([i % 256, (i * 2) % 256, (i * 3) % 256])
        img.putpalette(palette)
        
        pixels = []
        for i in range(128):
            pixels.append((i // 8) % 16)  # Create pattern
        img.putdata(pixels)
        img.save(png_path)
        
        # Create initial VRAM
        with open(vram_path, 'wb') as f:
            f.write(b'\x00' * 0x10000)
        
        # Run complete workflow
        test_args = ['sprite_injector.py', png_path, '--vram', vram_path, 
                    '--output', output_path, '--offset', '0x2000', '--preview']
        with patch.object(sys, 'argv', test_args):
            result = sprite_injector.main()
        
        # Should succeed
        self.assertEqual(result, 0)
        
        # Verify output exists
        self.assertTrue(os.path.exists(output_path))
        
        # Verify data was injected
        with open(output_path, 'rb') as f:
            vram_data = f.read()
        
        # Should have data at injection offset
        injected_data = vram_data[0x2000:0x2000 + 64]  # 2 tiles
        self.assertNotEqual(injected_data, b'\x00' * 64)
        
        # Rest should be unchanged
        self.assertEqual(vram_data[:0x2000], b'\x00' * 0x2000)

    def test_subprocess_execution(self):
        """Test executing as subprocess."""
        png_path = os.path.join(self.temp_dir, 'sprite.png')
        vram_path = os.path.join(self.temp_dir, 'VRAM.dmp')
        
        # Create test files
        img = Image.new('P', (8, 8))
        img.save(png_path)
        
        with open(vram_path, 'wb') as f:
            f.write(b'\x00' * 0x10000)  # 64KB to accommodate default offset
        
        # Run as subprocess
        cmd = [sys.executable, 'sprite_injector.py', png_path, '--vram', vram_path]
        result = subprocess.run(cmd, 
                              cwd='/mnt/c/CustomScripts/KirbyMax/workshop/exhal-master/sprite_editor',
                              capture_output=True, text=True)
        
        # Debug output if failed
        if result.returncode != 0:
            print(f"STDOUT: {result.stdout}")
            print(f"STDERR: {result.stderr}")
        
        # Should succeed
        self.assertEqual(result.returncode, 0)


if __name__ == '__main__':
    unittest.main()