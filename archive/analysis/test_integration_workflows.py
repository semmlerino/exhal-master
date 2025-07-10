#!/usr/bin/env python3
"""
Integration tests for complete sprite editing workflows
Tests the full pipeline from extraction to reinsertion
"""

import json
import os
import shutil
import struct
import tempfile
import unittest

import pytest
from PIL import Image

from sprite_edit_helpers import encode_4bpp_tile, parse_cgram
from sprite_edit_workflow import SpriteEditWorkflow
from sprite_sheet_editor import SpriteSheetEditor


class TestCompleteWorkflow(unittest.TestCase):
    """Test complete sprite editing workflows end-to-end"""

    def setUp(self):
        """Create realistic test environment"""
        self.test_dir = tempfile.mkdtemp()

        # Create realistic VRAM with multiple sprites
        self.vram_file = os.path.join(self.test_dir, "test.vram")
        self._create_test_vram()

        # Create realistic CGRAM with game-like palettes
        self.cgram_file = os.path.join(self.test_dir, "test.cgram")
        self._create_test_cgram()

        # Create palette mappings that match our test data
        self.mappings_file = os.path.join(self.test_dir, "mappings.json")
        self._create_test_mappings()

    def tearDown(self):
        """Clean up test environment"""
        shutil.rmtree(self.test_dir)

    def _create_test_vram(self):
        """Create VRAM with recognizable sprite patterns"""
        with open(self.vram_file, "wb") as f:
            # Sprite area starts at 0xC000
            f.write(b"\x00" * 0xC000)

            # Create 8 test sprites with different patterns
            patterns = [
                # Tile 0: Diagonal gradient
                self._create_gradient_tile(0),
                # Tile 1: Horizontal stripes
                self._create_stripe_tile(horizontal=True),
                # Tile 2: Vertical stripes
                self._create_stripe_tile(horizontal=False),
                # Tile 3: Checkerboard
                self._create_checkerboard_tile(),
                # Tile 4: Solid color
                self._create_solid_tile(15),
                # Tile 5: Border pattern
                self._create_border_tile(),
                # Tile 6: Cross pattern
                self._create_cross_tile(),
                # Tile 7: Random pattern
                self._create_random_tile(seed=42),
            ]

            for pattern in patterns:
                f.write(pattern)

            # Fill rest with zeros
            remaining = 65536 - 0xC000 - (8 * 32)
            f.write(b"\x00" * remaining)

    def _create_gradient_tile(self, offset):
        """Create a diagonal gradient tile"""
        pixels = []
        for y in range(8):
            for x in range(8):
                # Diagonal gradient
                value = ((x + y + offset) % 16)
                pixels.append(value)
        return encode_4bpp_tile(pixels)

    def _create_stripe_tile(self, horizontal=True):
        """Create a striped tile"""
        pixels = []
        for y in range(8):
            for x in range(8):
                if horizontal:
                    value = 15 if y % 2 == 0 else 1
                else:
                    value = 15 if x % 2 == 0 else 1
                pixels.append(value)
        return encode_4bpp_tile(pixels)

    def _create_checkerboard_tile(self):
        """Create a checkerboard pattern"""
        pixels = []
        for y in range(8):
            for x in range(8):
                value = 15 if (x + y) % 2 == 0 else 1
                pixels.append(value)
        return encode_4bpp_tile(pixels)

    def _create_solid_tile(self, color):
        """Create a solid color tile"""
        pixels = [color] * 64
        return encode_4bpp_tile(pixels)

    def _create_border_tile(self):
        """Create a tile with border"""
        pixels = []
        for y in range(8):
            for x in range(8):
                value = 15 if x in {0, 7} or y in {0, 7} else 0
                pixels.append(value)
        return encode_4bpp_tile(pixels)

    def _create_cross_tile(self):
        """Create a cross pattern"""
        pixels = []
        for y in range(8):
            for x in range(8):
                value = 15 if x in {3, 4} or y in {3, 4} else 0
                pixels.append(value)
        return encode_4bpp_tile(pixels)

    def _create_random_tile(self, seed):
        """Create a random pattern tile"""
        import random
        random.seed(seed)
        pixels = [random.randint(0, 15) for _ in range(64)]
        return encode_4bpp_tile(pixels)

    def _create_test_cgram(self):
        """Create CGRAM with distinct palettes"""
        with open(self.cgram_file, "wb") as f:
            palettes = [
                # Palette 0-7: Background palettes
                self._create_grayscale_palette(),      # 0
                self._create_red_palette(),            # 1
                self._create_green_palette(),          # 2
                self._create_blue_palette(),           # 3
                self._create_yellow_palette(),         # 4
                self._create_cyan_palette(),           # 5
                self._create_magenta_palette(),        # 6
                self._create_rainbow_palette(),        # 7
                # Palette 8-15: Sprite palettes
                self._create_pink_palette(),           # 8 (Kirby)
                self._create_orange_palette(),         # 9
                self._create_purple_palette(),         # 10
                self._create_brown_palette(),          # 11
                self._create_enemy_palette(),          # 12
                self._create_metallic_palette(),       # 13
                self._create_fire_palette(),           # 14
                self._create_ice_palette(),            # 15
            ]

            for palette in palettes:
                f.write(palette)

    def _create_grayscale_palette(self):
        """Create a grayscale palette"""
        data = bytearray()
        for i in range(16):
            intensity = i * 2  # 0-30
            bgr = (intensity << 10) | (intensity << 5) | intensity
            data.extend(struct.pack("<H", bgr))
        return data

    def _create_pink_palette(self):
        """Create Kirby's pink palette"""
        colors = [
            0x0000,  # Transparent
            0x7C1F,  # Pink
            0x6C1B,  # Darker pink
            0x5817,  # Even darker
            0x001F,  # Red (cheeks)
            0x7FFF,  # White (eyes)
            0x0000,  # Black (pupils)
            0x3DEF,  # Light gray
        ]
        # Fill rest with variations
        while len(colors) < 16:
            colors.append(0x7C1F)

        data = bytearray()
        for color in colors:
            data.extend(struct.pack("<H", color))
        return data

    def _create_red_palette(self):
        """Create red gradient palette"""
        data = bytearray()
        for i in range(16):
            r = min(31, i * 2)
            bgr = r  # Red only
            data.extend(struct.pack("<H", bgr))
        return data

    def _create_green_palette(self):
        """Create green gradient palette"""
        data = bytearray()
        for i in range(16):
            g = min(31, i * 2)
            bgr = g << 5  # Green only
            data.extend(struct.pack("<H", bgr))
        return data

    def _create_blue_palette(self):
        """Create blue gradient palette"""
        data = bytearray()
        for i in range(16):
            b = min(31, i * 2)
            bgr = b << 10  # Blue only
            data.extend(struct.pack("<H", bgr))
        return data

    def _create_yellow_palette(self):
        """Create yellow gradient palette"""
        data = bytearray()
        for i in range(16):
            rg = min(31, i * 2)
            bgr = rg | (rg << 5)  # Red + Green = Yellow
            data.extend(struct.pack("<H", bgr))
        return data

    def _create_cyan_palette(self):
        """Create cyan gradient palette"""
        data = bytearray()
        for i in range(16):
            gb = min(31, i * 2)
            bgr = (gb << 5) | (gb << 10)  # Green + Blue = Cyan
            data.extend(struct.pack("<H", bgr))
        return data

    def _create_magenta_palette(self):
        """Create magenta gradient palette"""
        data = bytearray()
        for i in range(16):
            rb = min(31, i * 2)
            bgr = rb | (rb << 10)  # Red + Blue = Magenta
            data.extend(struct.pack("<H", bgr))
        return data

    def _create_rainbow_palette(self):
        """Create rainbow palette"""
        colors = [
            0x0000,  # Black
            0x001F,  # Red
            0x03E0,  # Green
            0x7C00,  # Blue
            0x03FF,  # Yellow
            0x7FE0,  # Cyan
            0x7C1F,  # Magenta
            0x7FFF,  # White
        ]
        # Repeat pattern
        while len(colors) < 16:
            colors.extend(colors[1:8])

        data = bytearray()
        for color in colors[:16]:
            data.extend(struct.pack("<H", color))
        return data

    def _create_orange_palette(self):
        """Create orange palette"""
        data = bytearray()
        for i in range(16):
            r = min(31, i * 2)
            g = min(31, i)  # Half green
            bgr = r | (g << 5)
            data.extend(struct.pack("<H", bgr))
        return data

    def _create_purple_palette(self):
        """Create purple palette"""
        data = bytearray()
        for i in range(16):
            r = min(31, i)
            b = min(31, i * 2)
            bgr = r | (b << 10)
            data.extend(struct.pack("<H", bgr))
        return data

    def _create_brown_palette(self):
        """Create brown palette"""
        data = bytearray()
        for i in range(16):
            r = min(31, i + 8)
            g = min(31, i // 2 + 4)
            b = min(31, i // 4)
            bgr = r | (g << 5) | (b << 10)
            data.extend(struct.pack("<H", bgr))
        return data

    def _create_enemy_palette(self):
        """Create typical enemy palette"""
        colors = [
            0x0000,  # Transparent
            0x03E0,  # Green (body)
            0x02A0,  # Dark green
            0x0140,  # Darker green
            0x7FFF,  # White (eyes)
            0x0000,  # Black
            0x001F,  # Red (details)
            0x03FF,  # Yellow
        ]
        while len(colors) < 16:
            colors.append(0x03E0)

        data = bytearray()
        for color in colors:
            data.extend(struct.pack("<H", color))
        return data

    def _create_metallic_palette(self):
        """Create metallic/silver palette"""
        data = bytearray()
        for i in range(16):
            # Silver gradient
            intensity = min(31, 15 + i)
            bgr = (intensity << 10) | (intensity << 5) | intensity
            data.extend(struct.pack("<H", bgr))
        return data

    def _create_fire_palette(self):
        """Create fire-themed palette"""
        colors = [
            0x0000,  # Transparent
            0x001F,  # Red
            0x00FF,  # Orange-red
            0x03FF,  # Yellow
            0x07FF,  # Bright yellow
            0x0FFF,  # White-yellow
            0x7FFF,  # White
            0x0000,  # Black (smoke)
        ]
        while len(colors) < 16:
            colors.append(0x001F)

        data = bytearray()
        for color in colors:
            data.extend(struct.pack("<H", color))
        return data

    def _create_ice_palette(self):
        """Create ice-themed palette"""
        data = bytearray()
        for i in range(16):
            # Blue-white gradient
            b = 31
            g = min(31, 20 + i // 2)
            r = min(31, 15 + i)
            bgr = r | (g << 5) | (b << 10)
            data.extend(struct.pack("<H", bgr))
        return data

    def _create_test_mappings(self):
        """Create palette mappings for our test sprites"""
        mappings = {
            "tile_mappings": {
                "0": {"palette": 0, "confidence": 10},  # Kirby
                "1": {"palette": 1, "confidence": 8},   # Enemy type 1
                "2": {"palette": 1, "confidence": 8},   # Enemy type 1
                "3": {"palette": 4, "confidence": 5},   # Enemy type 2
                "4": {"palette": 2, "confidence": 7},   # UI element
                "5": {"palette": 0, "confidence": 9},   # Kirby
                "6": {"palette": 3, "confidence": 6},   # Effect
                "7": {"palette": 5, "confidence": 4},   # Random
            }
        }

        with open(self.mappings_file, "w") as f:
            json.dump(mappings, f)

    def test_complete_tile_workflow(self):
        """Test complete workflow with individual tiles"""
        # Step 1: Extract
        workflow = SpriteEditWorkflow(self.mappings_file)
        extract_dir = os.path.join(self.test_dir, "extracted")

        metadata = workflow.extract_for_editing(
            self.vram_file,
            self.cgram_file,
            offset=0xC000,
            size=256,  # 8 tiles
            output_dir=extract_dir,
            tiles_per_row=4
        )

        # Verify extraction
        assert len(metadata["tile_palette_mappings"]) == 8

        # Check that tiles use correct palettes from mappings
        for i in range(8):
            tile_file = f"tile_{i:04d}_pal{workflow.tile_to_palette.get(i, 0)}.png"
            assert tile_file in os.listdir(extract_dir)

        # Step 2: Edit a tile
        tile_to_edit = os.path.join(extract_dir, "tile_0000_pal0.png")
        assert os.path.exists(tile_to_edit)

        # Load and modify
        img = Image.open(tile_to_edit)
        assert img.size == (8, 8)
        assert img.mode == "P"

        # Make a valid edit - invert colors (keeping within palette)
        pixels = list(img.getdata())
        edited_pixels = []
        for p in pixels:
            if p > 0 and p < 15:  # Don't change transparent or max
                edited_pixels.append(15 - p)
            else:
                edited_pixels.append(p)

        img.putdata(edited_pixels)
        img.save(tile_to_edit)

        # Step 3: Validate
        validation = workflow.validate_edited_sprites(extract_dir)
        assert len(validation["valid_tiles"]) == 8
        assert len(validation["invalid_tiles"]) == 0

        # Step 4: Reinsert
        output_vram = os.path.join(self.test_dir, "modified.vram")
        result = workflow.reinsert_sprites(extract_dir, output_vram, backup=False)

        assert result == output_vram
        assert os.path.exists(output_vram)

        # Verify the edit was applied
        with open(output_vram, "rb") as f:
            f.seek(0xC000)
            modified_tile_data = f.read(32)

        # The modified tile should be different from original
        with open(self.vram_file, "rb") as f:
            f.seek(0xC000)
            original_tile_data = f.read(32)

        assert modified_tile_data != original_tile_data

        # But file sizes should match
        assert os.path.getsize(output_vram) == os.path.getsize(self.vram_file)

    def test_complete_sheet_workflow(self):
        """Test complete workflow with sprite sheet"""
        # Step 1: Extract sheet
        editor = SpriteSheetEditor(self.mappings_file)
        sheet_png = os.path.join(self.test_dir, "sprites.png")

        editor.extract_sheet_for_editing(
            self.vram_file,
            self.cgram_file,
            offset=0xC000,
            size=256,  # 8 tiles
            output_png=sheet_png
        )

        # Verify files created
        assert os.path.exists(sheet_png)
        assert os.path.exists(sheet_png.replace(".png", "_metadata.json"))
        assert os.path.exists(sheet_png.replace(".png", "_palettes.png"))

        # Load and check sheet
        img = Image.open(sheet_png)
        # Sheet editor uses fixed 16 tiles per row
        assert img.size == (128, 8)  # 16 tiles per row * 8 pixels, 1 row
        assert img.mode == "RGBA"

        # Step 2: Make edits
        # Add a red dot to first tile
        img.putpixel((3, 3), (255, 0, 0, 255))
        img.putpixel((4, 3), (255, 0, 0, 255))
        img.putpixel((3, 4), (255, 0, 0, 255))
        img.putpixel((4, 4), (255, 0, 0, 255))

        img.save(sheet_png)

        # Also create editing guide
        editor.create_editing_guide(sheet_png)
        guide_file = sheet_png.replace(".png", "_editing_guide.png")
        assert os.path.exists(guide_file)

        # Step 3: Validate
        validation = editor.validate_edited_sheet(sheet_png)
        # The red pixels should map to closest palette color
        # This may generate warnings but should still be valid
        assert validation["valid"]

        # Step 4: Reinsert
        output_vram = os.path.join(self.test_dir, "sheet_modified.vram")
        result = editor.reinsert_sheet(sheet_png, output_vram)

        assert result == output_vram
        assert os.path.exists(output_vram)

        # Verify modification
        with open(output_vram, "rb") as f:
            f.seek(0xC000)
            modified_data = f.read(256)

        with open(self.vram_file, "rb") as f:
            f.seek(0xC000)
            original_data = f.read(256)

        # Should be different due to edit
        assert modified_data != original_data

    def test_workflow_with_missing_mappings(self):
        """Test workflow without palette mappings file"""
        # Should work with default palette assignments
        workflow = SpriteEditWorkflow()  # No mappings file

        extract_dir = os.path.join(self.test_dir, "no_mappings")

        workflow.extract_for_editing(
            self.vram_file,
            self.cgram_file,
            offset=0xC000,
            size=64,  # 2 tiles
            output_dir=extract_dir
        )

        # Should extract with default palette 0
        tiles = [f for f in os.listdir(extract_dir) if f.startswith("tile_")]
        assert len(tiles) == 2

        # All should use palette 0 by default
        for tile in tiles:
            assert "_pal0.png" in tile

    def test_workflow_error_handling(self):
        """Test error handling in workflows"""
        workflow = SpriteEditWorkflow()

        # Test with non-existent files
        with pytest.raises(Exception):
            workflow.extract_for_editing(
                "nonexistent.vram",
                "nonexistent.cgram",
                0, 32, "output"
            )

        # Test validation with missing metadata
        empty_dir = os.path.join(self.test_dir, "empty")
        os.makedirs(empty_dir)

        with pytest.raises(FileNotFoundError):
            workflow.validate_edited_sprites(empty_dir)

        # Test reinsertion with no valid tiles
        workspace = os.path.join(self.test_dir, "invalid_workspace")
        os.makedirs(workspace)

        # Create metadata but no valid tiles
        metadata = {
            "vram_file": self.vram_file,
            "cgram_file": self.cgram_file,  # Need this for validation
            "tile_palette_mappings": {}
        }

        with open(os.path.join(workspace, "extraction_metadata.json"), "w") as f:
            json.dump(metadata, f)

        # Should handle gracefully
        workflow.reinsert_sprites(workspace, backup=False)
        # Result could be None or empty file depending on implementation

    def test_cgram_palette_application(self):
        """Test that palettes are correctly applied from CGRAM"""
        # Extract with known palette mappings
        workflow = SpriteEditWorkflow(self.mappings_file)
        extract_dir = os.path.join(self.test_dir, "palette_test")

        workflow.extract_for_editing(
            self.vram_file,
            self.cgram_file,
            offset=0xC000,
            size=32,  # 1 tile
            output_dir=extract_dir
        )

        # Load the extracted tile
        tile_img = Image.open(os.path.join(extract_dir, "tile_0000_pal0.png"))

        # Get the palette
        palette_data = tile_img.getpalette()
        assert palette_data is not None

        # Parse CGRAM to verify palette matches
        palettes = parse_cgram(self.cgram_file)

        # Tile 0 uses palette 0, which maps to CGRAM palette 8
        expected_palette = palettes[8]

        # Check first few colors match
        for i in range(16):
            r_expected, g_expected, b_expected = expected_palette[i]
            r_actual = palette_data[i * 3]
            g_actual = palette_data[i * 3 + 1]
            b_actual = palette_data[i * 3 + 2]

            # Should match exactly
            assert r_actual == r_expected
            assert g_actual == g_expected
            assert b_actual == b_expected

    def test_round_trip_preservation(self):
        """Test that extract->reinsert preserves data exactly"""
        workflow = SpriteEditWorkflow(self.mappings_file)

        # Extract
        extract_dir = os.path.join(self.test_dir, "round_trip")
        workflow.extract_for_editing(
            self.vram_file,
            self.cgram_file,
            offset=0xC000,
            size=256,  # 8 tiles
            output_dir=extract_dir
        )

        # Don't edit anything, just reinsert
        output_vram = os.path.join(self.test_dir, "round_trip.vram")
        workflow.reinsert_sprites(extract_dir, output_vram, backup=False)

        # Compare sprite data
        with open(self.vram_file, "rb") as f:
            f.seek(0xC000)
            original_sprites = f.read(256)

        with open(output_vram, "rb") as f:
            f.seek(0xC000)
            round_trip_sprites = f.read(256)

        # Should be identical
        assert original_sprites == round_trip_sprites


if __name__ == "__main__":
    unittest.main()
