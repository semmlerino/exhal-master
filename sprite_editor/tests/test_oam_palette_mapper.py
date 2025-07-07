"""
Tests for oam_palette_mapper.py - OAM parsing with bounds checking
"""

import pytest

from sprite_editor.constants import KIRBY_TILE_START, KIRBY_VRAM_BASE
from sprite_editor.oam_palette_mapper import (OAMPaletteMapper,
                                              create_tile_palette_map)


class TestOAMParsing:
    """Test OAM file parsing with various edge cases"""

    @pytest.mark.unit
    def test_valid_oam_parsing(self, oam_file):
        """Test parsing of valid OAM data"""
        mapper = OAMPaletteMapper()
        mapper.parse_oam_dump(oam_file)

        # Should have parsed 10 sprites from our fixture
        assert len(mapper.oam_entries) >= 10

        # Check first sprite
        first_sprite = mapper.oam_entries[0]
        assert first_sprite['x'] == 100
        assert first_sprite['y'] == 50
        assert first_sprite['tile'] == 0x80
        assert first_sprite['palette'] == 0

    @pytest.mark.unit
    def test_small_oam_file(self, temp_dir):
        """Test handling of OAM file that's too small"""
        small_oam = temp_dir / "small_oam.dmp"
        # Less than 4 bytes (minimum for one entry)
        small_oam.write_bytes(b'\x00' * 3)

        mapper = OAMPaletteMapper()
        with pytest.raises(ValueError, match="OAM dump too small.*need at least 4"):
            mapper.parse_oam_dump(str(small_oam))

    @pytest.mark.unit
    def test_truncated_oam_data(self, temp_dir):
        """Test graceful handling of truncated OAM data"""
        # Create OAM data that's exactly 544 bytes but truncated sprite entries
        truncated_data = bytearray(544)
        # Fill with partial sprite data
        for i in range(50):  # Only 50 complete entries
            offset = i * 4
            truncated_data[offset] = i
            truncated_data[offset + 1] = i
            truncated_data[offset + 2] = i
            truncated_data[offset + 3] = i % 8

        truncated_oam = temp_dir / "truncated_oam.dmp"
        truncated_oam.write_bytes(truncated_data)

        mapper = OAMPaletteMapper()
        mapper.parse_oam_dump(str(truncated_oam))

        # Should successfully parse available entries
        assert len(mapper.oam_entries) >= 50

    @pytest.mark.unit
    def test_large_oam_file(self, temp_dir):
        """Test handling of OAM file larger than expected"""
        large_data = bytearray(1024)  # Larger than normal
        # Fill with valid sprite data
        for i in range(128):
            offset = i * 4
            if offset + 3 < 512:
                large_data[offset] = i
                large_data[offset + 1] = i
                large_data[offset + 2] = i
                large_data[offset + 3] = i % 8

        large_oam = temp_dir / "large_oam.dmp"
        large_oam.write_bytes(large_data)

        mapper = OAMPaletteMapper()
        mapper.parse_oam_dump(str(large_oam))

        # Should parse exactly 128 sprites
        assert len(mapper.oam_entries) == 128

    @pytest.mark.unit
    def test_missing_high_table(self, temp_dir):
        """Test handling when high table data is missing"""
        # Create OAM data with only main table (512 bytes)
        partial_data = bytearray(512)
        for i in range(10):
            offset = i * 4
            partial_data[offset] = 100 + i
            partial_data[offset + 1] = 50 + i
            partial_data[offset + 2] = 0x80 + i
            partial_data[offset + 3] = i % 8

        partial_oam = temp_dir / "partial_oam.dmp"
        partial_oam.write_bytes(partial_data)

        mapper = OAMPaletteMapper()
        # This should now work with a warning
        import warnings
        with warnings.catch_warnings(record=True) as w:
            mapper.parse_oam_dump(str(partial_oam))
            # Should have warning about partial data
            assert len(w) == 1
            assert "Partial OAM data" in str(w[0].message)

        # Should have parsed all 128 entries (OAM always has 128 entries)
        assert len(mapper.oam_entries) == 128


class TestPaletteMapping:
    """Test palette mapping functionality"""

    @pytest.mark.unit
    def test_tile_palette_mapping(self, oam_file):
        """Test basic tile to palette mapping"""
        mapper = OAMPaletteMapper()
        mapper.parse_oam_dump(oam_file)

        # Check palette assignments
        assert mapper.get_palette_for_tile(0x80) == 0
        assert mapper.get_palette_for_tile(0x81) == 1
        assert mapper.get_palette_for_tile(0x89) == 1  # Wraps at 8

    @pytest.mark.unit
    def test_vram_palette_mapping(self, oam_file):
        """Test VRAM offset to palette mapping"""
        mapper = OAMPaletteMapper()
        mapper.parse_oam_dump(oam_file)
        mapper.build_vram_palette_map(KIRBY_VRAM_BASE)

        # Our test data doesn't have Kirby tiles, so map should be empty
        assert len(mapper.vram_palette_map) == 0

    @pytest.mark.unit
    def test_vram_offset_bounds(self):
        """Test VRAM offset calculation bounds checking"""
        mapper = OAMPaletteMapper()

        # Test with invalid base offset
        with pytest.raises(ValueError, match="Invalid base VRAM offset"):
            mapper.build_vram_palette_map(-1)

        with pytest.raises(ValueError, match="Invalid base VRAM offset"):
            mapper.build_vram_palette_map(0x20000)

    @pytest.mark.unit
    def test_kirby_tile_mapping(self, temp_dir):
        """Test mapping of Kirby-specific tiles"""
        # Create OAM data with Kirby tiles
        kirby_data = bytearray(544)

        # Add sprites using Kirby tiles
        for i in range(5):
            offset = i * 4
            kirby_data[offset] = 100 + i * 10
            kirby_data[offset + 1] = 100
            kirby_data[offset + 2] = (KIRBY_TILE_START + i) & 0xFF
            kirby_data[offset + 3] = i | 0x80  # High bit for tile table

        kirby_oam = temp_dir / "kirby_oam.dmp"
        kirby_oam.write_bytes(kirby_data)

        mapper = OAMPaletteMapper()
        mapper.parse_oam_dump(str(kirby_oam))
        mapper.build_vram_palette_map(KIRBY_VRAM_BASE)

        # Should have mapped some VRAM offsets
        assert len(mapper.vram_palette_ranges) > 0


class TestBinarySearchOptimization:
    """Test the optimized binary search for palette lookup"""

    @pytest.mark.unit
    def test_empty_ranges(self):
        """Test lookup with no ranges"""
        mapper = OAMPaletteMapper()
        assert mapper.get_palette_for_vram_offset(0x1000) is None

    @pytest.mark.unit
    def test_single_range(self):
        """Test lookup with single range"""
        mapper = OAMPaletteMapper()
        mapper.vram_palette_ranges = [(0x1000, 0x1020, 5)]

        assert mapper.get_palette_for_vram_offset(0x1000) == 5
        assert mapper.get_palette_for_vram_offset(0x1010) == 5
        assert mapper.get_palette_for_vram_offset(0x101F) == 5
        assert mapper.get_palette_for_vram_offset(0x1020) is None
        assert mapper.get_palette_for_vram_offset(0x0FFF) is None

    @pytest.mark.unit
    def test_multiple_ranges(self):
        """Test lookup with multiple ranges"""
        mapper = OAMPaletteMapper()
        mapper.vram_palette_ranges = [
            (0x1000, 0x1020, 1),
            (0x2000, 0x2020, 2),
            (0x3000, 0x3020, 3),
            (0x4000, 0x4020, 4),
        ]

        assert mapper.get_palette_for_vram_offset(0x1010) == 1
        assert mapper.get_palette_for_vram_offset(0x2010) == 2
        assert mapper.get_palette_for_vram_offset(0x3010) == 3
        assert mapper.get_palette_for_vram_offset(0x4010) == 4
        assert mapper.get_palette_for_vram_offset(0x1500) is None

    @pytest.mark.unit
    def test_overlapping_ranges(self):
        """Test handling of overlapping ranges (shouldn't happen but test anyway)"""
        mapper = OAMPaletteMapper()
        # Later ranges should take precedence due to sort order
        mapper.vram_palette_ranges = [
            (0x1000, 0x1030, 1),
            (0x1010, 0x1040, 2),  # Overlaps with first
            (0x1020, 0x1050, 3),  # Overlaps with both
        ]

        # Binary search should find the rightmost matching range
        assert mapper.get_palette_for_vram_offset(0x1025) == 3


class TestPaletteStatistics:
    """Test palette usage statistics"""

    @pytest.mark.unit
    def test_palette_usage_stats(self, oam_file):
        """Test calculation of palette usage statistics"""
        mapper = OAMPaletteMapper()
        mapper.parse_oam_dump(oam_file)

        stats = mapper.get_palette_usage_stats()

        assert 'palette_counts' in stats
        assert 'active_palettes' in stats
        assert 'total_sprites' in stats
        assert 'visible_sprites' in stats

        # Our test data has 10 sprites with palettes 0-7 (wrapping)
        assert stats['total_sprites'] >= 10
        assert len(stats['active_palettes']) >= 2

    @pytest.mark.unit
    def test_find_sprites_by_palette(self, oam_file):
        """Test finding sprites using specific palette"""
        mapper = OAMPaletteMapper()
        mapper.parse_oam_dump(oam_file)

        # Find sprites using palette 0
        palette_0_sprites = mapper.find_sprites_using_palette(0)
        assert len(palette_0_sprites) >= 1
        assert palette_0_sprites[0]['palette'] == 0

    @pytest.mark.unit
    def test_find_sprites_in_region(self, oam_file):
        """Test finding sprites within screen region"""
        mapper = OAMPaletteMapper()
        mapper.parse_oam_dump(oam_file)

        # Find sprites in region
        sprites_in_region = mapper.find_sprites_in_region(90, 40, 120, 60)
        assert len(sprites_in_region) >= 1

        for sprite in sprites_in_region:
            assert 90 <= sprite['x'] <= 120
            assert 40 <= sprite['y'] <= 60


class TestConvenienceFunctions:
    """Test convenience functions"""

    @pytest.mark.unit
    def test_create_tile_palette_map(self, oam_file):
        """Test the convenience function"""
        mapper = create_tile_palette_map(oam_file)

        assert isinstance(mapper, OAMPaletteMapper)
        assert len(mapper.oam_entries) >= 10
        # Should have called build_vram_palette_map
        assert mapper.vram_palette_ranges is not None
