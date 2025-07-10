#!/usr/bin/env python3
"""
Unit tests for sprite workflow classes
Tests SpriteEditWorkflow and SpriteSheetEditor
"""

import json
import os
import shutil
import struct
import tempfile
import unittest

from PIL import Image

from sprite_edit_workflow import SpriteEditWorkflow
from sprite_sheet_editor import SpriteSheetEditor


class TestSpriteEditWorkflow(unittest.TestCase):
    """Test the SpriteEditWorkflow class"""

    def setUp(self):
        """Set up test environment"""
        self.test_dir = tempfile.mkdtemp()

        # Create test VRAM file (minimal sprite data)
        self.vram_file = os.path.join(self.test_dir, "test.vram")
        with open(self.vram_file, "wb") as f:
            # Write 64KB of data with some test patterns
            # First tile: gradient pattern
            tile_data = bytearray(32)
            for i in range(8):
                tile_data[i*2] = i * 32
                tile_data[i*2 + 1] = i * 32

            f.write(tile_data)
            # Fill rest with zeros
            f.write(b"\x00" * (65536 - 32))

        # Create test CGRAM file
        self.cgram_file = os.path.join(self.test_dir, "test.cgram")
        with open(self.cgram_file, "wb") as f:
            # Create distinctive palettes
            for pal_idx in range(16):
                for color_idx in range(16):
                    if pal_idx == 8:  # Sprite palette 0
                        # Pink palette for Kirby
                        if color_idx == 0:
                            bgr = 0x0000  # Transparent
                        elif color_idx < 8:
                            bgr = 0x7C1F  # Pink shades
                        else:
                            bgr = 0x7FFF  # White
                    else:
                        # Generic palette
                        bgr = (pal_idx << 10) | (color_idx << 5) | color_idx
                    f.write(struct.pack("<H", bgr))

        # Create test palette mappings
        self.mappings_file = os.path.join(self.test_dir, "mappings.json")
        mappings = {
            "tile_mappings": {
                "0": {"palette": 0, "confidence": 5},
                "1": {"palette": 1, "confidence": 3},
                "2": {"palette": 0, "confidence": 10}
            }
        }
        with open(self.mappings_file, "w") as f:
            json.dump(mappings, f)

        self.workflow = SpriteEditWorkflow(self.mappings_file)

    def tearDown(self):
        """Clean up test environment"""
        shutil.rmtree(self.test_dir)

    def test_load_palette_mappings(self):
        """Test loading palette mappings from file"""
        # Should have loaded 3 mappings
        assert len(self.workflow.tile_to_palette) == 3
        assert self.workflow.tile_to_palette[0] == 0
        assert self.workflow.tile_to_palette[1] == 1
        assert self.workflow.tile_to_palette[2] == 0

    def test_extract_for_editing(self):
        """Test extracting sprites for editing"""
        output_dir = os.path.join(self.test_dir, "extracted")

        metadata = self.workflow.extract_for_editing(
            self.vram_file,
            self.cgram_file,
            offset=0,
            size=64,  # 2 tiles
            output_dir=output_dir,
            tiles_per_row=2
        )

        # Check metadata structure
        assert "vram_file" in metadata
        assert "cgram_file" in metadata
        assert "offset" in metadata
        assert "size" in metadata
        assert "tile_palette_mappings" in metadata

        # Check files were created
        assert os.path.exists(output_dir)
        assert os.path.exists(os.path.join(output_dir, "extraction_metadata.json"))
        assert os.path.exists(os.path.join(output_dir, "reference_sheet.png"))

        # Check tile files
        tile_files = [f for f in os.listdir(output_dir) if f.startswith("tile_")]
        assert len(tile_files) > 0

        # Verify palette assignment in filename
        assert any("_pal0.png" in f for f in tile_files)

    def test_validate_edited_sprites_valid(self):
        """Test validating correctly edited sprites"""
        # Create a test workspace with valid tiles
        workspace = os.path.join(self.test_dir, "workspace")
        os.makedirs(workspace)

        # Create metadata
        metadata = {
            "vram_file": self.vram_file,
            "cgram_file": self.cgram_file,
            "offset": 0,
            "size": 32,
            "tile_palette_mappings": {
                "0": {
                    "filename": "tile_0000_pal0.png",
                    "palette": 0,
                    "cgram_palette": 8,
                    "offset_in_vram": 0
                }
            }
        }

        with open(os.path.join(workspace, "extraction_metadata.json"), "w") as f:
            json.dump(metadata, f)

        # Create a valid 8x8 indexed PNG
        img = Image.new("P", (8, 8))
        pixels = list(range(64))
        # Ensure all pixels are 0-15
        pixels = [p % 16 for p in pixels]
        img.putdata(pixels)

        # Set a palette
        palette = []
        for i in range(256):
            palette.extend([i, i, i])
        img.putpalette(palette)

        img.save(os.path.join(workspace, "tile_0000_pal0.png"))

        # Validate
        results = self.workflow.validate_edited_sprites(workspace)

        assert "valid_tiles" in results
        assert "invalid_tiles" in results
        assert "warnings" in results

        assert len(results["valid_tiles"]) == 1
        assert len(results["invalid_tiles"]) == 0

    def test_validate_edited_sprites_invalid_dimensions(self):
        """Test validating sprites with wrong dimensions"""
        workspace = os.path.join(self.test_dir, "workspace")
        os.makedirs(workspace)

        # Create metadata
        metadata = {
            "cgram_file": self.cgram_file,
            "tile_palette_mappings": {
                "0": {
                    "filename": "tile_0000_pal0.png",
                    "palette": 0,
                    "cgram_palette": 8
                }
            }
        }

        with open(os.path.join(workspace, "extraction_metadata.json"), "w") as f:
            json.dump(metadata, f)

        # Create an invalid 16x16 PNG
        img = Image.new("P", (16, 16))
        img.save(os.path.join(workspace, "tile_0000_pal0.png"))

        # Validate
        results = self.workflow.validate_edited_sprites(workspace)

        assert len(results["valid_tiles"]) == 0
        assert len(results["invalid_tiles"]) == 1

        # Check error message
        error = results["invalid_tiles"][0]
        assert error["tile"] == "tile_0000_pal0.png"
        assert "(16, 16)" in error["error"]
        assert "(8, 8)" in error["error"]

    def test_validate_edited_sprites_invalid_color_mode(self):
        """Test validating sprites with wrong color mode"""
        workspace = os.path.join(self.test_dir, "workspace")
        os.makedirs(workspace)

        # Create metadata
        metadata = {
            "cgram_file": self.cgram_file,
            "tile_palette_mappings": {
                "0": {
                    "filename": "tile_0000_pal0.png",
                    "palette": 0,
                    "cgram_palette": 8
                }
            }
        }

        with open(os.path.join(workspace, "extraction_metadata.json"), "w") as f:
            json.dump(metadata, f)

        # Create an RGB image instead of indexed
        img = Image.new("RGB", (8, 8))
        img.save(os.path.join(workspace, "tile_0000_pal0.png"))

        # Validate
        results = self.workflow.validate_edited_sprites(workspace)

        assert len(results["valid_tiles"]) == 0
        assert len(results["invalid_tiles"]) == 1

        error = results["invalid_tiles"][0]
        assert "RGB" in error["error"]
        assert "P" in error["error"]

    def test_reinsert_sprites(self):
        """Test reinserting edited sprites"""
        # First extract sprites
        workspace = os.path.join(self.test_dir, "workspace")

        self.workflow.extract_for_editing(
            self.vram_file,
            self.cgram_file,
            offset=0,
            size=32,
            output_dir=workspace
        )

        # Modify a tile slightly
        tile_file = os.path.join(workspace, "tile_0000_pal0.png")
        if os.path.exists(tile_file):
            img = Image.open(tile_file)
            pixels = list(img.getdata())
            # Change first pixel
            pixels[0] = 1 if pixels[0] == 0 else 0
            img.putdata(pixels)
            img.save(tile_file)

        # Reinsert
        output_vram = os.path.join(self.test_dir, "modified.vram")
        result = self.workflow.reinsert_sprites(
            workspace,
            output_vram=output_vram,
            backup=False  # No backup for test
        )

        # Check result
        assert result == output_vram
        assert os.path.exists(output_vram)

        # Verify file size matches original
        assert os.path.getsize(output_vram) == os.path.getsize(self.vram_file)


class TestSpriteSheetEditor(unittest.TestCase):
    """Test the SpriteSheetEditor class"""

    def setUp(self):
        """Set up test environment"""
        self.test_dir = tempfile.mkdtemp()

        # Create test files (reuse from workflow tests)
        self.vram_file = os.path.join(self.test_dir, "test.vram")
        with open(self.vram_file, "wb") as f:
            # Create some test tiles
            for tile_idx in range(4):
                tile_data = bytearray(32)
                # Simple pattern based on tile index
                for i in range(32):
                    tile_data[i] = (tile_idx * 64 + i) & 0xFF
                f.write(tile_data)
            # Fill rest
            f.write(b"\x00" * (65536 - 128))

        self.cgram_file = os.path.join(self.test_dir, "test.cgram")
        with open(self.cgram_file, "wb") as f:
            # Create test palettes
            for pal_idx in range(16):
                for color_idx in range(16):
                    bgr = (pal_idx << 10) | (color_idx << 5) | color_idx
                    f.write(struct.pack("<H", bgr))

        self.sheet_editor = SpriteSheetEditor()

    def tearDown(self):
        """Clean up test environment"""
        shutil.rmtree(self.test_dir)

    def test_extract_sheet_for_editing(self):
        """Test extracting sprite sheet"""
        output_png = os.path.join(self.test_dir, "sheet.png")

        metadata = self.sheet_editor.extract_sheet_for_editing(
            self.vram_file,
            self.cgram_file,
            offset=0,
            size=128,  # 4 tiles
            output_png=output_png
        )

        # Check files created
        assert os.path.exists(output_png)
        assert os.path.exists(output_png.replace(".png", "_palettes.png"))
        assert os.path.exists(output_png.replace(".png", "_metadata.json"))
        assert os.path.exists(output_png.replace(".png", "_palette_ref.png"))

        # Check metadata
        assert "source_vram" in metadata
        assert "source_cgram" in metadata
        assert "tile_info" in metadata
        assert "palette_colors" in metadata

        # Verify image dimensions
        img = Image.open(output_png)
        # Sheet editor uses fixed 16 tiles per row
        assert img.size == (128, 8)  # 16 tiles per row * 8 pixels, 1 row

    def test_validate_edited_sheet_valid(self):
        """Test validating a valid edited sheet"""
        # First extract a sheet
        output_png = os.path.join(self.test_dir, "sheet.png")

        self.sheet_editor.extract_sheet_for_editing(
            self.vram_file,
            self.cgram_file,
            offset=0,
            size=64,  # 2 tiles
            output_png=output_png
        )

        # Validate without modifications
        results = self.sheet_editor.validate_edited_sheet(output_png)

        assert results["valid"]
        assert len(results["errors"]) == 0

    def test_validate_edited_sheet_too_many_colors(self):
        """Test validating sheet with too many colors per tile"""
        # Create a sheet with metadata
        output_png = os.path.join(self.test_dir, "sheet.png")

        # Create metadata
        metadata = {
            "tile_info": {
                "0": {"x": 0, "y": 0, "palette": 0, "cgram_palette": 8}
            },
            "palette_colors": {}
        }

        metadata_file = output_png.replace(".png", "_metadata.json")
        with open(metadata_file, "w") as f:
            json.dump(metadata, f)

        # Create image with too many colors
        img = Image.new("RGBA", (8, 8))
        # Draw 17 different colors (more than 15 + transparent)
        for i in range(8):
            for j in range(8):
                color_idx = i * 8 + j
                if color_idx < 17:
                    # Create unique colors
                    img.putpixel((j, i), (color_idx * 15, 0, 0, 255))

        img.save(output_png)

        # Validate
        results = self.sheet_editor.validate_edited_sheet(output_png)

        assert not results["valid"]
        assert len(results["errors"]) > 0
        assert "too many colors" in results["errors"][0]

    def test_reinsert_sheet(self):
        """Test reinserting edited sheet"""
        # Extract a sheet first
        sheet_png = os.path.join(self.test_dir, "sheet.png")

        self.sheet_editor.extract_sheet_for_editing(
            self.vram_file,
            self.cgram_file,
            offset=0,
            size=64,
            output_png=sheet_png
        )

        # Make a small edit
        img = Image.open(sheet_png)
        # Change one pixel
        img.putpixel((0, 0), (255, 0, 0, 255))
        img.save(sheet_png)

        # Reinsert
        output_vram = os.path.join(self.test_dir, "modified.vram")
        result = self.sheet_editor.reinsert_sheet(sheet_png, output_vram)

        assert result == output_vram
        assert os.path.exists(output_vram)

        # Verify file size
        assert os.path.getsize(output_vram) == os.path.getsize(self.vram_file)

    def test_create_editing_guide(self):
        """Test creating editing guide"""
        # Extract a sheet
        sheet_png = os.path.join(self.test_dir, "sheet.png")

        self.sheet_editor.extract_sheet_for_editing(
            self.vram_file,
            self.cgram_file,
            offset=0,
            size=64,
            output_png=sheet_png
        )

        # Create guide
        self.sheet_editor.create_editing_guide(sheet_png)

        guide_file = sheet_png.replace(".png", "_editing_guide.png")
        assert os.path.exists(guide_file)

        # Verify guide is larger than original
        original_img = Image.open(sheet_png)
        guide_img = Image.open(guide_file)
        assert guide_img.width > original_img.width


if __name__ == "__main__":
    unittest.main()
