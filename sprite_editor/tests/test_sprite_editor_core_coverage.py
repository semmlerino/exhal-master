"""
Additional tests to improve coverage for sprite_editor_core.py
Focus on error conditions, edge cases, and fallback scenarios
"""

import pytest
import tempfile
from pathlib import Path
from PIL import Image

from sprite_editor.sprite_editor_core import SpriteEditorCore
from sprite_editor.constants import *
from sprite_editor.security_utils import SecurityError


class TestEdgeCases:
    """Test edge cases and error conditions"""
    
    def test_read_cgram_palette_file_too_small(self, temp_dir):
        """Test reading palette when CGRAM file is too small"""
        core = SpriteEditorCore()
        
        # Create CGRAM file that's too small for palette 15
        small_cgram = temp_dir / "small.cgram"
        # Only enough data for 8 palettes, not 16
        small_cgram.write_bytes(bytearray(256))  # 8 palettes * 32 bytes
        
        # Try to read palette 15 (needs offset 480, but file is only 256 bytes)
        palette = core.read_cgram_palette(str(small_cgram), 15)
        assert palette is None
    
    def test_read_cgram_palette_incomplete_color(self, temp_dir):
        """Test handling of incomplete color data in CGRAM"""
        core = SpriteEditorCore()
        
        # Create CGRAM with incomplete last color
        cgram_data = bytearray(33)  # 1 palette + 1 extra byte
        cgram = temp_dir / "incomplete.cgram"
        cgram.write_bytes(cgram_data)
        
        # This should handle the incomplete color gracefully
        palette = core.read_cgram_palette(str(cgram), 0)
        assert palette is not None
        # Last color should be black due to incomplete data
        assert palette[-3:] == [0, 0, 0]
    
    def test_read_cgram_palette_generic_exception(self, temp_dir, monkeypatch):
        """Test generic exception handling in read_cgram_palette"""
        core = SpriteEditorCore()
        
        cgram = temp_dir / "test.cgram"
        cgram.write_bytes(bytearray(512))
        
        # Mock struct.unpack_from to raise an unexpected exception
        def mock_unpack(*args, **kwargs):
            raise RuntimeError("Unexpected error")
        
        import struct
        monkeypatch.setattr(struct, 'unpack_from', mock_unpack)
        
        # When struct.unpack_from fails, it fills with zeros
        palette = core.read_cgram_palette(str(cgram), 0)
        assert palette is not None
        # Should be all zeros due to error handling
        assert all(c == 0 for c in palette)
    
    def test_extract_sprites_generic_exception(self, temp_dir, monkeypatch):
        """Test generic exception handling in extract_sprites"""
        core = SpriteEditorCore()
        
        vram = temp_dir / "test.vram"
        vram.write_bytes(bytearray(0x10000))
        
        # Mock Image.new to raise an exception
        def mock_new(*args, **kwargs):
            raise MemoryError("Out of memory")
        
        monkeypatch.setattr(Image, 'new', mock_new)
        
        # Should raise with descriptive message
        with pytest.raises(RuntimeError, match="Error extracting sprites.*Out of memory"):
            core.extract_sprites(str(vram), 0, 1024)
    
    def test_inject_into_vram_oversized_file(self, temp_dir):
        """Test handling of oversized VRAM files"""
        core = SpriteEditorCore()
        
        # Create VRAM file larger than 128KB
        huge_vram = temp_dir / "huge.vram"
        huge_vram.write_bytes(bytearray(0x20001))  # 128KB + 1 byte
        
        sprite_data = bytearray(32)
        
        # Security check happens first and raises SecurityError
        with pytest.raises(SecurityError, match="File too large"):
            core.inject_into_vram(sprite_data, str(huge_vram), 0)
    
    def test_inject_into_vram_offset_exceeds_size(self, temp_dir):
        """Test injection with offset beyond file size"""
        core = SpriteEditorCore()
        
        vram = temp_dir / "test.vram"
        vram.write_bytes(bytearray(0x10000))
        
        sprite_data = bytearray(32)
        
        # Try to inject at offset beyond file size
        with pytest.raises(ValueError, match="Offset.*exceeds VRAM size"):
            core.inject_into_vram(sprite_data, str(vram), 0x10001)
    
    def test_inject_into_vram_no_output_file(self, vram_file):
        """Test injection that returns data instead of writing file"""
        core = SpriteEditorCore()
        
        sprite_data = bytearray(32)
        sprite_data[0] = 0xFF  # Mark first byte
        
        # Call without output file parameter
        result = core.inject_into_vram(sprite_data, vram_file, 0x1000)
        
        # Should return modified VRAM data as bytearray
        assert isinstance(result, bytearray)
        assert len(result) == 0x10000  # 64KB
        assert result[0x1000] == 0xFF  # Check our modification
    
    def test_inject_into_vram_generic_exception(self, temp_dir, monkeypatch):
        """Test generic exception handling in inject_into_vram"""
        core = SpriteEditorCore()
        
        vram = temp_dir / "test.vram"
        vram.write_bytes(bytearray(0x10000))
        
        sprite_data = bytearray(32)
        output = temp_dir / "output.vram"
        
        # Mock the builtin open to raise an exception when writing
        original_open = open
        
        def mock_open(filename, mode='r', *args, **kwargs):
            if 'output.vram' in str(filename) and 'w' in mode:
                raise IOError("Disk full")
            return original_open(filename, mode, *args, **kwargs)
        
        import builtins
        monkeypatch.setattr(builtins, 'open', mock_open)
        
        with pytest.raises(RuntimeError, match="Error injecting into VRAM.*Disk full"):
            core.inject_into_vram(sprite_data, str(vram), 0, str(output))
    
    def test_validate_png_generic_exception(self, temp_dir, monkeypatch):
        """Test generic exception handling in validate_png_for_snes"""
        core = SpriteEditorCore()
        
        # Create a valid PNG
        img = Image.new('P', (128, 128))
        png_path = temp_dir / "test.png"
        img.save(str(png_path))
        
        # Mock Image.open to raise unexpected exception
        def mock_open(path):
            raise RuntimeError("Unexpected error")
        
        monkeypatch.setattr(Image, 'open', mock_open)
        
        # Should return validation failure with error
        valid, issues = core.validate_png_for_snes(str(png_path))
        assert valid is False
        assert any("Unexpected error" in issue for issue in issues)
    
    def test_get_vram_info_non_standard_size(self, temp_dir):
        """Test VRAM info for non-standard file size"""
        core = SpriteEditorCore()
        
        # Create VRAM with non-standard size (48KB)
        vram = temp_dir / "odd.vram"
        vram.write_bytes(bytearray(0xC000))  # 48KB
        
        info = core.get_vram_info(str(vram))
        assert info is not None
        assert info['size'] == 0xC000
        assert info['size_text'] == '49152 bytes'  # Raw byte count
    
    def test_get_vram_info_generic_exception(self, temp_dir, monkeypatch):
        """Test generic exception handling in get_vram_info"""
        core = SpriteEditorCore()
        
        vram = temp_dir / "test.vram"
        vram.write_bytes(bytearray(0x10000))
        
        # Mock file size to raise exception
        import os
        def mock_getsize(path):
            raise OSError("Permission denied")
        
        monkeypatch.setattr(os.path, 'getsize', mock_getsize)
        
        # Should return None on error
        info = core.get_vram_info(str(vram))
        assert info is None
    
    def test_load_oam_mapping_generic_exception(self, temp_dir, monkeypatch):
        """Test generic exception handling in load_oam_mapping"""
        core = SpriteEditorCore()
        
        oam = temp_dir / "test.oam"
        oam.write_bytes(bytearray(544))
        
        # Mock OAMPaletteMapper to raise exception
        def mock_parse(*args):
            raise RuntimeError("Parser error")
        
        from sprite_editor.oam_palette_mapper import OAMPaletteMapper
        monkeypatch.setattr(OAMPaletteMapper, 'parse_oam_dump', mock_parse)
        
        # Should return False and print error
        result = core.load_oam_mapping(str(oam))
        assert result is False


class TestFallbackBehavior:
    """Test fallback behavior when resources are missing"""
    
    def test_extract_sprites_multi_palette_no_oam(self, vram_file, cgram_file):
        """Test multi-palette extraction without OAM mapper"""
        core = SpriteEditorCore()
        # Don't load OAM mapper
        
        palette_images, tile_count = core.extract_sprites_multi_palette(
            vram_file, 0xC000, 512, cgram_file
        )
        
        # Should return single image with default palette
        assert 'palette_0' in palette_images
        assert len(palette_images) == 1
        assert tile_count == 16
    
    def test_extract_sprites_with_correct_palettes_no_cgram(self, vram_file, oam_file, temp_dir):
        """Test extraction when CGRAM file doesn't exist"""
        core = SpriteEditorCore()
        core.load_oam_mapping(oam_file)
        
        # Use non-existent CGRAM file
        fake_cgram = temp_dir / "missing.cgram"
        
        img, tile_count = core.extract_sprites_with_correct_palettes(
            vram_file, 0xC000, 512, str(fake_cgram)
        )
        
        # Should work with grayscale palettes
        assert img is not None
        assert img.mode == 'RGBA'
        assert tile_count > 0
    
    def test_extract_sprites_with_correct_palettes_no_oam_data(self, vram_file, cgram_file):
        """Test when OAM mapper returns None for palette"""
        core = SpriteEditorCore()
        # Create a mock OAM mapper that returns None
        from sprite_editor.oam_palette_mapper import OAMPaletteMapper
        
        class MockMapper(OAMPaletteMapper):
            def get_palette_for_vram_offset(self, offset):
                return None  # No palette mapping found
        
        core.oam_mapper = MockMapper()
        
        img, tile_count = core.extract_sprites_with_correct_palettes(
            vram_file, 0xC000, 512, cgram_file
        )
        
        # Should use palette 0 as default
        assert img is not None
        assert tile_count > 0


class TestModuleExecution:
    """Test running the module directly"""
    
    def test_module_direct_imports(self):
        """Test that fallback imports work"""
        # This tests lines 14-17 (ImportError handling)
        # We can't easily test this in isolation, but we can verify
        # the module loads correctly
        import sprite_editor.sprite_editor_core
        assert hasattr(sprite_editor.sprite_editor_core, 'SpriteEditorCore')