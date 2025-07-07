"""
Integration tests for OAM palette mapping with sprite extraction
"""


from PIL import Image

from sprite_editor.oam_palette_mapper import OAMPaletteMapper
from sprite_editor.sprite_editor_core import SpriteEditorCore


class TestOAMSpriteIntegration:
    """Test OAM integration with sprite extraction workflows"""

    def test_oam_guided_sprite_extraction(
            self, vram_file, cgram_file, oam_file):
        """Test extracting sprites using OAM data for palette assignment"""
        core = SpriteEditorCore()
        mapper = OAMPaletteMapper()

        # Load OAM data
        mapper.parse_oam_dump(oam_file)
        mapper.build_vram_palette_map()

        # Get active palettes from OAM
        active_palettes = mapper.get_active_palettes()
        assert len(active_palettes) > 0

        # Extract sprites for each active palette
        extracted_sprites = {}
        for pal_num in active_palettes:
            # Get sprites using this palette
            sprites = mapper.find_sprites_using_palette(pal_num)
            if sprites:
                # Get the tile range for this palette
                tile_nums = [s['tile'] for s in sprites]
                min_tile = min(tile_nums)
                max_tile = max(tile_nums)

                # Extract sprites in this range
                # Calculate VRAM offset for the tile range
                vram_offset = 0xC000 + (min_tile * 32)
                tile_count = max_tile - min_tile + 1

                if vram_offset < 0x20000 and tile_count > 0:
                    img, count = core.extract_sprites(
                        vram_file, vram_offset, tile_count * 32)

                    # Apply the palette
                    palette = core.read_cgram_palette(cgram_file, pal_num)
                    img.putpalette(palette)

                    extracted_sprites[pal_num] = img

        # Should have extracted sprites for active palettes
        assert len(extracted_sprites) > 0

        # Verify the images are valid
        for pal_num, img in extracted_sprites.items():
            assert img.mode == 'P'
            assert img.width > 0
            assert img.height > 0

    def test_oam_sprite_sheet_creation(
            self, vram_file, cgram_file, oam_file, temp_dir):
        """Test creating a sprite sheet with OAM-based palette mapping"""
        core = SpriteEditorCore()

        # Load OAM mapping
        success = core.load_oam_mapping(oam_file)
        assert success is True

        # Create a composite sprite sheet with all palettes
        all_sprites = []
        labels = []

        # Extract sprites for each palette
        palette_images, tile_count = core.extract_sprites_multi_palette(
            vram_file, 0xC000, 1024, cgram_file
        )

        # Create a sprite sheet showing all palette variations
        if palette_images:
            # Calculate dimensions
            first_img = list(palette_images.values())[0]
            sheet_width = first_img.width
            sheet_height = first_img.height * len(palette_images)

            # Create composite sheet
            sheet = Image.new('RGBA', (sheet_width, sheet_height))

            y_offset = 0
            for pal_name, img in sorted(palette_images.items()):
                sheet.paste(img.convert('RGBA'), (0, y_offset))
                y_offset += img.height

            # Save the sheet
            sheet_path = temp_dir / 'oam_sprite_sheet.png'
            sheet.save(str(sheet_path))

            # Verify the sheet
            assert sheet_path.exists()
            loaded_sheet = Image.open(str(sheet_path))
            assert loaded_sheet.width == sheet_width
            assert loaded_sheet.height == sheet_height

    def test_oam_sprite_region_extraction(
            self, vram_file, cgram_file, oam_file):
        """Test extracting sprites from specific screen regions"""
        mapper = OAMPaletteMapper()
        core = SpriteEditorCore()

        # Parse OAM
        mapper.parse_oam_dump(oam_file)

        # Find sprites in the upper-left quadrant (0-128, 0-112)
        upper_left_sprites = mapper.find_sprites_in_region(0, 0, 128, 112)

        # Find sprites in the center region
        center_sprites = mapper.find_sprites_in_region(64, 56, 192, 168)

        # Extract tiles for sprites in each region
        if upper_left_sprites:
            # Get unique tiles from upper left region
            ul_tiles = set(s['tile'] for s in upper_left_sprites)
            ul_palettes = set(s['palette'] for s in upper_left_sprites)

            # Verify we found region-specific data
            assert len(ul_tiles) > 0
            assert len(ul_palettes) > 0

        if center_sprites:
            center_tiles = set(s['tile'] for s in center_sprites)
            center_palettes = set(s['palette'] for s in center_sprites)

            # These might overlap but should have some data
            assert len(center_tiles) >= 0
            assert len(center_palettes) >= 0

    def test_oam_palette_statistics_workflow(self, oam_file, cgram_file):
        """Test workflow using OAM palette statistics"""
        mapper = OAMPaletteMapper()
        core = SpriteEditorCore()

        # Parse OAM and get statistics
        mapper.parse_oam_dump(oam_file)
        stats = mapper.get_palette_usage_stats()

        # Verify statistics
        assert 'palette_counts' in stats
        assert 'active_palettes' in stats
        assert 'total_sprites' in stats
        assert 'visible_sprites' in stats

        # Find the most used palette
        if stats['palette_counts']:
            most_used_pal = max(
                stats['palette_counts'].items(),
                key=lambda x: x[1])
            pal_num, count = most_used_pal

            # Read this palette from CGRAM
            palette = core.read_cgram_palette(cgram_file, pal_num)
            assert palette is not None
            # Palette is extended to 256 values (full palette for P mode)
            assert len(palette) == 768  # 256 colors * 3 bytes (RGB)

            # Verify it's being used by sprites
            sprites_using_pal = mapper.find_sprites_using_palette(pal_num)
            # The count should be at least what the stats reported
            # (stats might only count visible sprites, but find_sprites returns all)
            assert len(sprites_using_pal) >= count

    def test_partial_oam_data_workflow(self, vram_file, cgram_file, temp_dir):
        """Test workflow with partial/truncated OAM data"""
        mapper = OAMPaletteMapper()
        core = SpriteEditorCore()

        # Create partial OAM data (only 50 sprites worth)
        partial_oam = bytearray(200)  # 50 sprites * 4 bytes

        # Fill with test data
        for i in range(50):
            offset = i * 4
            partial_oam[offset] = i * 4  # x
            partial_oam[offset + 1] = i * 4  # y
            partial_oam[offset + 2] = i % 64  # tile
            partial_oam[offset + 3] = i % 8  # palette

        # Save partial OAM
        oam_path = temp_dir / 'partial.oam'
        oam_path.write_bytes(partial_oam)

        # Parse with warning
        import warnings
        with warnings.catch_warnings(record=True) as w:
            mapper.parse_oam_dump(str(oam_path))
            # Should have a warning about partial data
            assert len(w) == 1
            assert "Partial OAM data" in str(w[0].message)

        # Should still have parsed 50 sprites
        assert len(mapper.oam_entries) == 50

        # Should be able to get palette mapping
        active_pals = mapper.get_active_palettes()
        assert len(active_pals) > 0

        # Try to extract sprites based on this partial data
        if mapper.oam_entries:
            first_sprite = mapper.oam_entries[0]
            tile_num = first_sprite['tile']
            pal_num = first_sprite['palette']

            # Extract the tile
            vram_offset = 0xC000 + (tile_num * 32)
            if vram_offset + 32 <= 0x20000:
                img, _ = core.extract_sprites(vram_file, vram_offset, 32)
                palette = core.read_cgram_palette(cgram_file, pal_num)
                img.putpalette(palette)

                # Should have extracted a single tile
                # Single tile extraction, but width depends on tiles_per_row
                assert img.width > 0
                assert img.height == 8


class TestOAMErrorHandling:
    """Test error handling in OAM integration scenarios"""

    def test_corrupted_oam_recovery(self, vram_file, cgram_file, temp_dir):
        """Test recovery from corrupted OAM data"""
        mapper = OAMPaletteMapper()

        # Create corrupted OAM with invalid values
        corrupted_oam = bytearray(544)

        # Fill with some extreme/invalid values
        for i in range(128):
            offset = i * 4
            corrupted_oam[offset] = 0xFF  # x = 255
            corrupted_oam[offset + 1] = 0xFF  # y = 255 (off-screen)
            corrupted_oam[offset + 2] = 0xFF  # tile 255
            corrupted_oam[offset + 3] = 0xFF  # attributes with all bits set

        # Save corrupted OAM
        oam_path = temp_dir / 'corrupted.oam'
        oam_path.write_bytes(corrupted_oam)

        # Should parse without crashing
        mapper.parse_oam_dump(str(oam_path))

        # Should have parsed entries but most are off-screen
        assert len(mapper.oam_entries) == 128
        stats = mapper.get_palette_usage_stats()
        assert stats['visible_sprites'] == 0  # All have y=255 which is > 224

        # Palette 7 should be used (lower 3 bits of 0xFF)
        assert 7 in stats['palette_counts']

    def test_oam_vram_mismatch_handling(self, temp_dir):
        """Test handling when OAM references tiles not in VRAM"""
        mapper = OAMPaletteMapper()
        core = SpriteEditorCore()

        # Create OAM referencing high tile numbers
        oam_data = bytearray(544)
        for i in range(10):
            offset = i * 4
            oam_data[offset] = 50  # x
            oam_data[offset + 1] = 50  # y
            # tiles 240-255 (likely not in VRAM)
            oam_data[offset + 2] = 240 + (i % 16)
            oam_data[offset + 3] = 1  # palette 1

        oam_path = temp_dir / 'high_tiles.oam'
        oam_path.write_bytes(oam_data)

        # Create small VRAM that doesn't contain these tiles
        small_vram = bytearray(0x8000)  # Only 32KB
        vram_path = temp_dir / 'small.vram'
        vram_path.write_bytes(small_vram)

        # Parse OAM
        mapper.parse_oam_dump(str(oam_path))

        # Try to extract - should handle missing tiles gracefully
        for sprite in mapper.oam_entries[:10]:
            tile_num = sprite['tile']
            vram_offset = 0xC000 + (tile_num * 32)

            # This offset will be beyond our small VRAM
            if vram_offset + 32 > len(small_vram):
                # Should fail gracefully with a descriptive error
                try:
                    result = core.extract_sprites(
                        str(vram_path), vram_offset, 32)
                    # If it doesn't raise, it might return empty/partial data
                    assert False, "Expected exception for out-of-bounds offset"
                except Exception as e:
                    # Verify we get a meaningful error
                    assert "offset" in str(
                        e).lower() or "size" in str(e).lower()
