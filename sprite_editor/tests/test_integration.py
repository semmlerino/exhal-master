"""
Integration tests for sprite editor - testing complete workflows
"""

import pytest
from pathlib import Path
from PIL import Image

from sprite_editor.sprite_editor_core import SpriteEditorCore
from sprite_editor.oam_palette_mapper import OAMPaletteMapper
from sprite_editor.security_utils import SecurityError
from sprite_editor.constants import *

class TestFullExtractionWorkflow:
    """Test complete sprite extraction workflow"""

    @pytest.mark.integration
    def test_extract_view_edit_inject_workflow(self, vram_file, cgram_file, temp_dir):
        """Test full workflow: extract -> edit -> inject"""
        core = SpriteEditorCore()

        # Step 1: Extract sprites
        extracted_img, tile_count = core.extract_sprites(vram_file, 0xC000, 512)
        assert extracted_img.mode == 'P'
        assert tile_count == 16

        # Step 2: Apply palette
        palette = core.read_cgram_palette(cgram_file, 8)  # Kirby's palette
        assert palette is not None
        extracted_img.putpalette(palette)

        # Step 3: Save as PNG
        edit_path = temp_dir / "edit.png"
        extracted_img.save(str(edit_path))

        # Step 4: Validate PNG
        valid, issues = core.validate_png_for_snes(str(edit_path))
        assert valid is True

        # Step 5: Modify the image (simple color shift)
        edit_img = Image.open(str(edit_path))
        pixels = list(edit_img.getdata())
        # Shift all non-zero pixels by 1
        modified_pixels = [(p + 1) % 16 if p > 0 else 0 for p in pixels]
        edit_img.putdata(modified_pixels)

        modified_path = temp_dir / "modified.png"
        edit_img.save(str(modified_path))

        # Step 6: Convert back to SNES format
        snes_data, new_tile_count = core.png_to_snes(str(modified_path))
        assert new_tile_count == tile_count

        # Step 7: Inject back into VRAM
        output_vram = temp_dir / "output_vram.dmp"
        result = core.inject_into_vram(snes_data, vram_file, 0xC000, str(output_vram))
        assert Path(result).exists()

        # Step 8: Verify injection by re-extracting
        verify_img, _ = core.extract_sprites(result, 0xC000, 512)
        verify_img.putpalette(palette)

        # Compare with modified image
        verify_pixels = list(verify_img.getdata())
        assert verify_pixels == modified_pixels

    @pytest.mark.integration
    @pytest.mark.slow
    def test_multi_palette_workflow(self, vram_file, cgram_file, oam_file, temp_dir):
        """Test workflow with OAM-based palette mapping"""
        core = SpriteEditorCore()

        # Step 1: Load OAM data
        success = core.load_oam_mapping(oam_file)
        assert success is True

        # Step 2: Extract with multiple palettes
        palette_images, tile_count = core.extract_sprites_multi_palette(
            vram_file, 0, 1024, cgram_file
        )

        # Should have images for active palettes
        assert len(palette_images) >= 1

        # Step 3: Save each palette version
        for pal_name, img in palette_images.items():
            save_path = temp_dir / f"{pal_name}.png"
            img.save(str(save_path))
            assert save_path.exists()

        # Step 4: Create palette grid
        grid_img, _ = core.create_palette_grid_preview(
            vram_file, 0, 1024, cgram_file
        )

        grid_path = temp_dir / "palette_grid.png"
        grid_img.save(str(grid_path))
        assert grid_path.exists()

        # Grid should be larger than individual images
        first_img = list(palette_images.values())[0]
        assert grid_img.width > first_img.width
        assert grid_img.height > first_img.height

class TestSecurityIntegration:
    """Test security features across components"""

    @pytest.mark.integration
    def test_malicious_path_blocked_everywhere(self, temp_dir):
        """Test that malicious paths are blocked at all entry points"""
        core = SpriteEditorCore()
        mapper = OAMPaletteMapper()

        evil_path = "../../../etc/passwd"

        # Should be blocked in core
        with pytest.raises(SecurityError):
            core.extract_sprites(evil_path, 0, 100)

        with pytest.raises(SecurityError):
            core.png_to_snes(evil_path)

        with pytest.raises(SecurityError):
            core.inject_into_vram(b'data', evil_path, 0)

        with pytest.raises(SecurityError):
            core.get_vram_info(evil_path)

        # Should be blocked in OAM mapper
        with pytest.raises(SecurityError):
            mapper.parse_oam_dump(evil_path)

        # Should be blocked in palette reading
        with pytest.raises(SecurityError):
            core.read_cgram_palette(evil_path, 0)

    @pytest.mark.integration
    def test_size_limits_enforced(self, temp_dir):
        """Test that file size limits are enforced consistently"""
        # Create files of various sizes
        files = {
            'huge_vram.dmp': 200 * 1024,      # 200KB (exceeds VRAM limit)
            'huge_png.png': 10 * 1024 * 1024,  # 10MB (exceeds PNG limit)
            'huge_oam.dmp': 10 * 1024,         # 10KB (exceeds OAM limit)
            'huge_cgram.dmp': 10 * 1024,       # 10KB (exceeds CGRAM limit)
        }

        for filename, size in files.items():
            path = temp_dir / filename
            path.write_bytes(b'\x00' * size)

        core = SpriteEditorCore()

        # All should raise SecurityError for size
        with pytest.raises(SecurityError, match="File too large"):
            core.extract_sprites(str(temp_dir / 'huge_vram.dmp'), 0, 100)

        with pytest.raises(SecurityError, match="File too large"):
            core.png_to_snes(str(temp_dir / 'huge_png.png'))

        with pytest.raises(SecurityError, match="File too large"):
            core.load_oam_mapping(str(temp_dir / 'huge_oam.dmp'))

        with pytest.raises(SecurityError, match="File too large"):
            core.read_cgram_palette(str(temp_dir / 'huge_cgram.dmp'), 0)

class TestComplexDataIntegration:
    """Test integration with complex/realistic data"""

    @pytest.mark.integration
    def test_kirby_sprite_extraction(self, temp_dir):
        """Test extraction of Kirby-like sprite data"""
        # Create VRAM with Kirby-like tiles
        vram_data = bytearray(65536)

        # Create some recognizable patterns at Kirby offset
        kirby_offset = 0xC000
        for tile_idx in range(16):  # 16 tiles
            tile_offset = kirby_offset + (tile_idx * BYTES_PER_TILE_4BPP)

            # Create a pattern for each tile
            for y in range(TILE_HEIGHT):
                for bp in range(4):  # 4 bitplanes
                    offset = tile_offset + (bp * 16) + (y * 2)
                    if offset < len(vram_data):
                        # Create different patterns per tile
                        if tile_idx < 4:  # Head tiles
                            vram_data[offset] = 0xFF if bp == 0 else 0x00
                        elif tile_idx < 8:  # Body tiles
                            vram_data[offset] = 0xAA if bp < 2 else 0x55
                        else:  # Feet tiles
                            vram_data[offset] = (0xFF >> bp) & 0xFF

        # Create CGRAM with Kirby palette
        cgram_data = bytearray(512)
        # Palette 8 - Kirby's colors
        kirby_colors = [
            (0, 0, 0),        # Transparent
            (255, 192, 203),  # Pink
            (255, 20, 147),   # Deep pink
            (139, 0, 139),    # Dark magenta
            (255, 255, 255),  # White
            (0, 0, 0),        # Black
            (255, 0, 0),      # Red
            (128, 0, 0),      # Dark red
        ]

        for i, (r, g, b) in enumerate(kirby_colors[:16]):
            # Convert to BGR555
            r5 = (r * 31) // 255
            g5 = (g * 31) // 255
            b5 = (b * 31) // 255
            bgr555 = (b5 << 10) | (g5 << 5) | r5

            offset = 8 * 32 + i * 2  # Palette 8
            cgram_data[offset] = bgr555 & 0xFF
            cgram_data[offset + 1] = (bgr555 >> 8) & 0xFF

        # Create OAM data with Kirby sprites
        oam_data = bytearray(544)
        for i in range(4):  # 4 Kirby sprites
            offset = i * 4
            oam_data[offset] = 100 + i * 16      # X
            oam_data[offset + 1] = 100           # Y
            oam_data[offset + 2] = 0x80 + i * 4  # Tile (in Kirby range)
            oam_data[offset + 3] = 0x08 | 0x80    # Palette 8, table 1

        # Save test files
        vram_path = temp_dir / "kirby_vram.dmp"
        cgram_path = temp_dir / "kirby_cgram.dmp"
        oam_path = temp_dir / "kirby_oam.dmp"

        vram_path.write_bytes(vram_data)
        cgram_path.write_bytes(cgram_data)
        oam_path.write_bytes(oam_data)

        # Test extraction
        core = SpriteEditorCore()
        core.load_oam_mapping(str(oam_path))

        # Extract with correct palettes
        img, tile_count = core.extract_sprites_with_correct_palettes(
            str(vram_path), kirby_offset, 512, str(cgram_path)
        )

        assert img.mode == 'RGBA'
        assert tile_count == 16

        # Save result
        output_path = temp_dir / "kirby_sprites.png"
        img.save(str(output_path))
        assert output_path.exists()

class TestErrorRecovery:
    """Test error handling and recovery in workflows"""

    @pytest.mark.integration
    def test_partial_data_handling(self, temp_dir):
        """Test handling of partial/corrupted data"""
        # Create VRAM with some corrupted tiles
        vram_data = bytearray(65536)

        # Fill with pattern but corrupt some tiles
        for i in range(0, 65536, BYTES_PER_TILE_4BPP):
            if i % 256 == 0:  # Every 8th tile
                # Corrupt tile - fill with 0xFF
                vram_data[i:i+BYTES_PER_TILE_4BPP] = b'\xFF' * BYTES_PER_TILE_4BPP
            else:
                # Normal tile pattern
                for j in range(BYTES_PER_TILE_4BPP):
                    vram_data[i + j] = (i + j) % 256

        vram_path = temp_dir / "partial_vram.dmp"
        vram_path.write_bytes(vram_data)

        # Should still extract successfully
        core = SpriteEditorCore()
        img, tile_count = core.extract_sprites(str(vram_path), 0, 1024)

        assert img is not None
        assert tile_count == 32

    @pytest.mark.integration
    def test_missing_files_graceful_handling(self, vram_file, temp_dir):
        """Test graceful handling when optional files are missing"""
        core = SpriteEditorCore()

        # Extract without CGRAM - should use grayscale
        img, _ = core.extract_sprites(vram_file, 0, 512)
        assert img.mode == 'P'

        # Try to load non-existent OAM - should return False
        fake_oam = temp_dir / "fake_oam.dmp"
        success = core.load_oam_mapping(str(fake_oam))
        assert success is False

        # Extract with OAM palettes but no OAM loaded - should work
        fake_cgram = temp_dir / "fake_cgram.dmp"
        img, _ = core.extract_sprites_with_correct_palettes(
            vram_file, 0, 512, str(fake_cgram)
        )
        assert img is not None

class TestPerformanceIntegration:
    """Test performance aspects of integrated workflows"""

    @pytest.mark.integration
    @pytest.mark.slow
    def test_large_extraction_performance(self, temp_dir):
        """Test performance with large sprite extractions"""
        # Create large VRAM file
        large_vram = bytearray(65536)
        for i in range(0, 65536, 32):
            # Simple pattern for each tile
            for j in range(32):
                large_vram[i + j] = (i // 32) % 256

        vram_path = temp_dir / "large_vram.dmp"
        vram_path.write_bytes(large_vram)

        core = SpriteEditorCore()

        # Extract entire VRAM
        import time
        start_time = time.time()
        img, tile_count = core.extract_sprites(str(vram_path), 0, 65536)
        extraction_time = time.time() - start_time

        assert tile_count == 2048  # 64KB / 32 bytes
        assert extraction_time < 2.0  # Should complete in under 2 seconds

        # Test binary search performance with many ranges
        mapper = OAMPaletteMapper()

        # Create many palette ranges
        for i in range(0, 60000, 64):
            mapper.vram_palette_ranges.append((i, i + 32, i % 8))

        # Sort for binary search
        mapper.vram_palette_ranges.sort(key=lambda x: x[0])

        # Test lookup performance
        start_time = time.time()
        for i in range(1000):
            # Random lookups
            offset = (i * 137) % 65536
            palette = mapper.get_palette_for_vram_offset(offset)
        lookup_time = time.time() - start_time

        assert lookup_time < 0.1  # 1000 lookups in under 100ms

class TestRealWorldScenarios:
    """Test scenarios that mirror real usage"""

    @pytest.mark.integration
    def test_sprite_sheet_workflow(self, temp_dir):
        """Test creating and editing a sprite sheet"""
        # Create a sprite sheet with multiple characters
        sheet_width = 128  # 16 tiles wide
        sheet_height = 64  # 8 tiles high

        # Create VRAM with different character sprites
        vram_data = bytearray(65536)

        # Character 1 at offset 0x6000
        # Character 2 at offset 0x6200
        # Character 3 at offset 0x6400

        for char_idx, offset in enumerate([0x6000, 0x6200, 0x6400]):
            for tile_idx in range(16):  # 16 tiles per character
                tile_offset = offset + (tile_idx * 32)
                # Create unique pattern per character
                for i in range(32):
                    vram_data[tile_offset + i] = (char_idx * 64 + tile_idx * 4 + i) % 256

        vram_path = temp_dir / "characters_vram.dmp"
        vram_path.write_bytes(vram_data)

        # Create CGRAM with different palettes per character
        cgram_data = bytearray(512)

        # Palette 0 - Character 1 (red tones)
        # Palette 1 - Character 2 (blue tones)
        # Palette 2 - Character 3 (green tones)

        base_colors = [
            [(255, 0, 0), (200, 0, 0), (150, 0, 0)],    # Red
            [(0, 0, 255), (0, 0, 200), (0, 0, 150)],    # Blue
            [(0, 255, 0), (0, 200, 0), (0, 150, 0)],    # Green
        ]

        for pal_idx, colors in enumerate(base_colors):
            for color_idx, (r, g, b) in enumerate(colors):
                # Convert to BGR555
                r5 = (r * 31) // 255
                g5 = (g * 31) // 255
                b5 = (b * 31) // 255
                bgr555 = (b5 << 10) | (g5 << 5) | r5

                offset = pal_idx * 32 + color_idx * 2
                cgram_data[offset] = bgr555 & 0xFF
                cgram_data[offset + 1] = (bgr555 >> 8) & 0xFF

        cgram_path = temp_dir / "characters_cgram.dmp"
        cgram_path.write_bytes(cgram_data)

        # Extract all characters into a sprite sheet
        core = SpriteEditorCore()
        sheet_parts = []

        for char_idx, (offset, pal) in enumerate([(0x6000, 0), (0x6200, 1), (0x6400, 2)]):
            img, _ = core.extract_sprites(str(vram_path), offset, 512, tiles_per_row=4)
            palette = core.read_cgram_palette(str(cgram_path), pal)
            img.putpalette(palette)
            sheet_parts.append(img)

        # Combine into single sheet
        sheet = Image.new('P', (sheet_width, sheet_height))
        sheet.putpalette(palette)  # Use last palette for now

        y_offset = 0
        for part in sheet_parts:
            sheet.paste(part, (0, y_offset))
            y_offset += part.height

        sheet_path = temp_dir / "sprite_sheet.png"
        sheet.save(str(sheet_path))
        assert sheet_path.exists()

        # Validate the sprite sheet
        valid, issues = core.validate_png_for_snes(str(sheet_path))
        assert valid is True