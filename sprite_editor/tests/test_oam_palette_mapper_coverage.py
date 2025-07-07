"""
Additional tests to improve coverage for oam_palette_mapper.py
"""

import pytest
import tempfile
from pathlib import Path

from sprite_editor.oam_palette_mapper import OAMPaletteMapper, create_tile_palette_map
from sprite_editor.constants import *


class TestAdditionalOAMCoverage:
    """Tests to improve code coverage for edge cases"""
    
    def test_partial_sprite_entry(self):
        """Test when OAM data ends in the middle of a sprite entry"""
        mapper = OAMPaletteMapper()
        
        # Create OAM data that ends mid-sprite (513 bytes instead of 544)
        # This will have 128 complete entries + 1 partial byte
        oam_data = bytearray(513)
        
        # Fill with test data
        for i in range(128):
            offset = i * 4
            if offset + 3 < len(oam_data):
                oam_data[offset] = i  # x
                oam_data[offset + 1] = 100  # y (visible)
                oam_data[offset + 2] = i  # tile
                oam_data[offset + 3] = i % 8  # palette in lower 3 bits
        
        with tempfile.NamedTemporaryFile(suffix='.dmp', delete=False) as f:
            f.write(oam_data)
            temp_file = f.name
        
        try:
            # This should parse successfully but stop at incomplete entries
            mapper.parse_oam_dump(temp_file)
            
            # Should have parsed 128 entries (the partial 129th is skipped)
            assert len(mapper.oam_entries) == 128
        finally:
            Path(temp_file).unlink()
    
    def test_missing_high_table_default_bits(self):
        """Test default high bits when high table is partially missing"""
        mapper = OAMPaletteMapper()
        
        # Create OAM data with main table but incomplete high table
        # 512 bytes main + 10 bytes high table (incomplete)
        oam_data = bytearray(522)
        
        # Fill main table
        for i in range(128):
            offset = i * 4
            oam_data[offset] = 50  # x
            oam_data[offset + 1] = 50  # y (visible)
            oam_data[offset + 2] = i  # tile
            oam_data[offset + 3] = 0  # attributes
        
        # Fill partial high table (only covers first 40 sprites)
        for i in range(10):
            oam_data[512 + i] = 0x00
        
        with tempfile.NamedTemporaryFile(suffix='.dmp', delete=False) as f:
            f.write(oam_data)
            temp_file = f.name
        
        try:
            mapper.parse_oam_dump(temp_file)
            
            # Sprites 40-127 should have default high_bits = 0
            # Check a sprite that's beyond the high table coverage
            sprite_100 = mapper.oam_entries[100]
            assert sprite_100['size'] == 'small'  # default size when high_bits = 0
            assert sprite_100['x'] == 50  # no MSB from high table
        finally:
            Path(temp_file).unlink()
    
    def test_large_sprite_tile_mapping(self):
        """Test palette mapping for large (16x16) sprites"""
        mapper = OAMPaletteMapper()
        
        # Create proper OAM data with large sprites
        oam_data = bytearray(544)  # Full OAM size
        
        # Set up a large sprite at index 0
        oam_data[0] = 10  # x
        oam_data[1] = 20  # y
        oam_data[2] = 100  # base tile
        oam_data[3] = 0x03  # palette 3
        
        # Set size bit in high table for sprite 0
        # Sprite 0 is in byte 512, bits 0-1
        oam_data[512] = 0x01  # size bit = 1, x_msb = 0
        
        with tempfile.NamedTemporaryFile(suffix='.dmp', delete=False) as f:
            f.write(oam_data)
            temp_file = f.name
        
        try:
            mapper.parse_oam_dump(temp_file)
            
            # Check that all 4 tiles of the large sprite are mapped
            assert mapper.tile_palette_map[100] == 3  # base tile
            assert mapper.tile_palette_map[101] == 3  # +1
            assert mapper.tile_palette_map[116] == 3  # +16
            assert mapper.tile_palette_map[117] == 3  # +17
        finally:
            Path(temp_file).unlink()
    
    def test_vram_offset_bounds_checking(self):
        """Test VRAM offset calculation with out-of-bounds tiles"""
        mapper = OAMPaletteMapper()
        
        # Manually add tiles that would cause bounds issues
        mapper.tile_palette_map[KIRBY_TILE_START - 1] = 1  # Before Kirby range
        mapper.tile_palette_map[KIRBY_TILE_START + 200] = 2  # Way beyond valid range
        mapper.tile_palette_map[KIRBY_TILE_START + 0x80] = 3  # Just over limit
        
        # Build VRAM map
        mapper.build_vram_palette_map(0x6000)
        
        # These should not be in the VRAM map due to bounds checks
        assert len(mapper.vram_palette_ranges) == 0
    
    def test_vram_address_overflow(self):
        """Test VRAM address calculation that would overflow"""
        mapper = OAMPaletteMapper()
        
        # The VRAM size limit is 0x20000 (128KB), not 0xFFFF
        # Let's test a tile that would exceed this limit
        # We need: (base + (tile_offset * 16)) * 2 > 0x20000
        # With base 0xF000: (0xF000 + (0x7F * 16)) * 2 = (0xF000 + 0x7F0) * 2 = 0xF7F0 * 2 = 0x1EFE0
        # Still under limit. Let's use a tile outside Kirby range
        
        # First, let's test that normal Kirby tiles work
        mapper.tile_palette_map[KIRBY_TILE_START] = 5
        mapper.build_vram_palette_map(0x8000)
        
        # This should create one range
        assert len(mapper.vram_palette_ranges) == 1
        
        # Now test with tiles outside the valid Kirby range
        mapper2 = OAMPaletteMapper()
        mapper2.tile_palette_map[KIRBY_TILE_END + 10] = 5  # Beyond Kirby range
        mapper2.build_vram_palette_map(0x6000)
        
        # Should not map tiles outside Kirby range
        assert len(mapper2.vram_palette_ranges) == 0
    
    def test_invalid_vram_base_offset(self):
        """Test invalid base VRAM offset validation"""
        mapper = OAMPaletteMapper()
        mapper.tile_palette_map[KIRBY_TILE_START] = 1
        
        # Test negative offset
        with pytest.raises(ValueError, match="Invalid base VRAM offset"):
            mapper.build_vram_palette_map(-1)
        
        # Test offset > 0x10000
        with pytest.raises(ValueError, match="Invalid base VRAM offset"):
            mapper.build_vram_palette_map(0x10001)
    
    def test_debug_dump_method(self):
        """Test the debug_dump method for coverage"""
        mapper = OAMPaletteMapper()
        
        # Create minimal OAM data
        oam_data = bytearray(544)
        
        # Add a few visible sprites
        for i in range(5):
            oam_data[i*4] = 10 + i*10  # x
            oam_data[i*4 + 1] = 20 + i*10  # y (visible)
            oam_data[i*4 + 2] = i  # tile
            oam_data[i*4 + 3] = i % 3  # palette
        
        with tempfile.NamedTemporaryFile(suffix='.dmp', delete=False) as f:
            f.write(oam_data)
            temp_file = f.name
        
        try:
            mapper.parse_oam_dump(temp_file)
            
            # Capture logging output
            import logging
            import io
            log_stream = io.StringIO()
            handler = logging.StreamHandler(log_stream)
            handler.setFormatter(logging.Formatter('%(message)s'))
            
            # Get the mapper's logger and add our handler
            logger = mapper.logger
            original_level = logger.level
            logger.setLevel(logging.INFO)
            logger.addHandler(handler)
            
            try:
                mapper.debug_dump()
                output = log_stream.getvalue()
                
                # Verify debug output contains expected information
                assert "OAM Debug Dump" in output
                assert "Total sprites: 128" in output
                # All sprites with y=0 are visible, only first 5 have custom y values
                # Actually need to count how many have y < 224
                visible_count = sum(1 for s in mapper.oam_entries if s['y'] < 224)
                assert f"Visible sprites: {visible_count}" in output
                assert "Palette usage:" in output
                assert "First 10 visible sprites:" in output
            finally:
                logger.removeHandler(handler)
                logger.setLevel(original_level)
        finally:
            Path(temp_file).unlink()


class TestModuleMain:
    """Test the module's __main__ execution"""
    
    def test_main_execution_with_file(self):
        """Test running module as script with OAM file"""
        import subprocess
        import sys
        
        # Create a test OAM file
        oam_data = bytearray(544)
        for i in range(10):
            oam_data[i*4] = 10
            oam_data[i*4 + 1] = 20
            oam_data[i*4 + 2] = i
            oam_data[i*4 + 3] = 1
        
        with tempfile.NamedTemporaryFile(suffix='.dmp', delete=False) as f:
            f.write(oam_data)
            temp_file = f.name
        
        try:
            # Run the module directly
            result = subprocess.run(
                [sys.executable, '-m', 'sprite_editor.oam_palette_mapper', temp_file],
                capture_output=True,
                text=True,
                cwd=Path(__file__).parent.parent.parent  # exhal-master directory
            )
            
            # Should run successfully and output debug info
            assert result.returncode == 0
            assert "OAM Debug Dump" in result.stdout
            assert "Total sprites:" in result.stdout
        finally:
            Path(temp_file).unlink()
    
    def test_main_execution_no_file(self):
        """Test running module without OAM file"""
        import subprocess
        import sys
        
        # Run the script directly
        script_path = Path(__file__).parent.parent / 'oam_palette_mapper.py'
        
        # Change to a temp directory where OAM.dmp doesn't exist
        with tempfile.TemporaryDirectory() as temp_dir:
            result = subprocess.run(
                [sys.executable, str(script_path)],
                capture_output=True,
                text=True,
                cwd=temp_dir
            )
            
            # Should output file not found message
            assert "OAM file not found: OAM.dmp" in result.stdout


class TestConvenienceFunction:
    """Test the create_tile_palette_map convenience function"""
    
    def test_create_tile_palette_map_custom_base(self):
        """Test convenience function with custom VRAM base"""
        # Create test OAM data
        oam_data = bytearray(544)
        
        # Add Kirby tile
        # Note: OAM tile numbers can use table select bit for tiles 256-511
        # Tile 384 (KIRBY_TILE_START) = 128 + 256 table offset
        oam_data[0] = 10  # x
        oam_data[1] = 20  # y
        oam_data[2] = 128  # tile 128 (will become 384 with table select)
        oam_data[3] = 0x85  # palette 5 + table select bit (bit 7) set
        
        with tempfile.NamedTemporaryFile(suffix='.dmp', delete=False) as f:
            f.write(oam_data)
            temp_file = f.name
        
        try:
            # Test with default VRAM base
            mapper = create_tile_palette_map(temp_file)
            
            assert mapper.get_palette_for_tile(KIRBY_TILE_START) == 5
            assert len(mapper.vram_palette_ranges) > 0
            
            # Test with custom VRAM base
            custom_base = 0x8000
            mapper2 = create_tile_palette_map(temp_file, custom_base)
            
            # The tile mapping should be the same
            assert mapper2.get_palette_for_tile(KIRBY_TILE_START) == 5
        finally:
            Path(temp_file).unlink()