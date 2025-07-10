#!/usr/bin/env python3
"""
Tests for sprite_assembler module
Tests sprite assembly functionality with comprehensive coverage
"""

import os
from pathlib import Path
from unittest.mock import patch

import pytest
from PIL import Image

from sprite_editor.sprite_assembler import (
    assemble_sprite,
    create_sprite_sheet,
    load_tiles_from_image,
    main,
)


@pytest.fixture
def temp_files(tmp_path):
    """Create temporary test files with tile patterns"""
    # Create test tileset (4x4 tiles = 32x32 pixels)
    tileset_file = tmp_path / "test_tileset.png"
    img = Image.new("P", (32, 32))

    # Create distinct patterns for each tile
    pixels = []
    for y in range(32):
        for x in range(32):
            # Create 4x4 distinct 8x8 tile patterns
            tile_x = x // 8
            tile_y = y // 8
            tile_idx = tile_y * 4 + tile_x

            # Simple pattern: each tile has unique base color
            pattern_value = (tile_idx + (x % 8) + (y % 8)) % 16
            pixels.append(pattern_value)

    img.putdata(pixels)

    # Set palette
    palette = []
    for i in range(16):
        palette.extend([i * 16, i * 16, i * 16])  # Grayscale
    for i in range(240):  # Fill rest of palette
        palette.extend([0, 0, 0])
    img.putpalette(palette)

    img.save(tileset_file)

    # Create RGB test image
    rgb_file = tmp_path / "test_rgb.png"
    rgb_img = Image.new("RGB", (16, 16))
    rgb_pixels = []
    for y in range(16):
        for x in range(16):
            rgb_pixels.append((x * 16, y * 16, 0))
    rgb_img.putdata(rgb_pixels)
    rgb_img.save(rgb_file)

    return {"tileset": str(tileset_file), "rgb": str(rgb_file), "dir": str(tmp_path)}


@pytest.mark.unit
class TestLoadTilesFromImage:
    """Test tile loading functionality"""

    def test_load_tiles_indexed(self, temp_files):
        """Test loading tiles from indexed image"""
        tiles, mode, palette = load_tiles_from_image(temp_files["tileset"])

        assert len(tiles) == 16  # 4x4 tiles
        assert mode == "P"
        assert palette is not None

        # Check tile dimensions
        for tile in tiles:
            assert tile.size == (8, 8)
            assert tile.mode == "P"

    def test_load_tiles_rgb(self, temp_files):
        """Test loading tiles from RGB image"""
        tiles, mode, palette = load_tiles_from_image(temp_files["rgb"])

        assert len(tiles) == 4  # 2x2 tiles
        assert mode == "RGB"
        assert palette is None

        # Check tile dimensions
        for tile in tiles:
            assert tile.size == (8, 8)
            assert tile.mode == "RGB"

    def test_load_tiles_custom_size(self, temp_files):
        """Test loading with custom tile size"""
        tiles, mode, palette = load_tiles_from_image(
            temp_files["tileset"], tile_size=16
        )

        assert len(tiles) == 4  # 2x2 tiles at 16x16 each

        # Check tile dimensions
        for tile in tiles:
            assert tile.size == (16, 16)

    def test_load_tiles_file_not_found(self):
        """Test with non-existent file"""
        with pytest.raises(FileNotFoundError):
            load_tiles_from_image("/nonexistent/file.png")

    def test_load_tiles_partial_tiles(self, tmp_path):
        """Test with image not perfectly divisible by tile size"""
        # Create 15x15 image (not divisible by 8)
        img_file = tmp_path / "partial.png"
        img = Image.new("P", (15, 15))
        img.putdata([0] * (15 * 15))
        img.save(img_file)

        tiles, mode, palette = load_tiles_from_image(str(img_file))

        # Should only get tiles that fully fit: 1x1 tile
        assert len(tiles) == 1
        assert tiles[0].size == (8, 8)


@pytest.mark.unit
class TestAssembleSprite:
    """Test sprite assembly functionality"""

    def test_assemble_sprite_2x2(self, temp_files):
        """Test assembling 2x2 sprite"""
        tiles, mode, palette = load_tiles_from_image(temp_files["tileset"])

        sprite = assemble_sprite(tiles, [0, 1, 4, 5], (2, 2))

        assert sprite.size == (16, 16)  # 2x2 tiles
        assert sprite.mode == "P"

        # Verify tiles are placed correctly
        top_left = sprite.crop((0, 0, 8, 8))
        top_right = sprite.crop((8, 0, 16, 8))
        assert list(top_left.getdata()) == list(tiles[0].getdata())
        assert list(top_right.getdata()) == list(tiles[1].getdata())

    def test_assemble_sprite_3x3(self, temp_files):
        """Test assembling 3x3 sprite"""
        tiles, mode, palette = load_tiles_from_image(temp_files["tileset"])

        sprite = assemble_sprite(tiles, [0, 1, 2, 4, 5, 6, 8, 9, 10], (3, 3))

        assert sprite.size == (24, 24)  # 3x3 tiles
        assert sprite.mode == "P"

    def test_assemble_sprite_rgb_mode(self, temp_files):
        """Test assembling from RGB tiles"""
        tiles, mode, palette = load_tiles_from_image(temp_files["rgb"])

        sprite = assemble_sprite(tiles, [0, 1, 2, 3], (2, 2))

        assert sprite.size == (16, 16)
        assert sprite.mode == "RGB"

    def test_assemble_sprite_invalid_indices(self, temp_files):
        """Test with invalid tile indices"""
        tiles, mode, palette = load_tiles_from_image(temp_files["tileset"])

        # Include index beyond available tiles
        sprite = assemble_sprite(tiles, [0, 1, 999, 3], (2, 2))

        assert sprite.size == (16, 16)
        # Should skip invalid index 999

    def test_assemble_sprite_custom_size(self, temp_files):
        """Test with custom tile size"""
        tiles, mode, palette = load_tiles_from_image(
            temp_files["tileset"], tile_size=16
        )

        sprite = assemble_sprite(tiles, [0, 1], (2, 1), tile_size=16)

        assert sprite.size == (32, 16)  # 2x1 tiles at 16x16 each


@pytest.mark.unit
class TestCreateSpriteSheet:
    """Test sprite sheet creation"""

    def test_create_sprite_sheet_basic(self, temp_files):
        """Test creating basic sprite sheet"""
        tiles, mode, palette = load_tiles_from_image(temp_files["tileset"])

        arrangements = [
            ("sprite1", (2, 2), [0, 1, 4, 5]),
            ("sprite2", (2, 2), [2, 3, 6, 7]),
        ]

        sheet, sprites = create_sprite_sheet(tiles, arrangements)

        assert len(sprites) == 2
        assert sheet.mode == "RGBA"
        assert sheet.width >= 32  # At least as wide as largest sprite * 2

        # Check sprites were created
        for name, sprite in sprites:
            assert name in ["sprite1", "sprite2"]
            assert sprite.size == (16, 16)

    def test_create_sprite_sheet_different_sizes(self, temp_files):
        """Test with sprites of different sizes"""
        tiles, mode, palette = load_tiles_from_image(temp_files["tileset"])

        arrangements = [
            ("small", (1, 1), [0]),
            ("medium", (2, 2), [0, 1, 4, 5]),
            ("large", (3, 2), [0, 1, 2, 4, 5, 6]),
        ]

        sheet, sprites = create_sprite_sheet(tiles, arrangements)

        assert len(sprites) == 3
        # Sheet should be wide enough for largest sprite * 2
        max_sprite_width = max(s[1].width for s in sprites)
        assert sheet.width >= max_sprite_width * 2

    def test_create_sprite_sheet_empty_arrangements(self, temp_files):
        """Test with empty arrangements"""
        tiles, mode, palette = load_tiles_from_image(temp_files["tileset"])

        sheet, sprites = create_sprite_sheet(tiles, [])

        assert len(sprites) == 0
        # Should still create a sheet
        assert sheet.mode == "RGBA"


@pytest.mark.unit
class TestMainFunction:
    """Test main entry point"""

    def test_main_success(self, temp_files, monkeypatch):
        """Test successful main execution"""
        # Mock command line arguments
        test_args = [
            "sprite_assembler.py",
            temp_files["tileset"],
            os.path.join(temp_files["dir"], "test_output"),
        ]
        monkeypatch.setattr("sys.argv", test_args)

        with patch("builtins.print") as mock_print:
            main()

        # Check files were created
        output_dir = temp_files["dir"]
        assert any(f.endswith("_edit_sheet.png") for f in os.listdir(output_dir))
        assert any(f.endswith("_arrangements.txt") for f in os.listdir(output_dir))

        # Check print statements
        mock_print.assert_any_call("Loaded 16 tiles from " + temp_files["tileset"])

    def test_main_no_arguments(self, monkeypatch):
        """Test with no command line arguments"""
        test_args = ["sprite_assembler.py"]
        monkeypatch.setattr("sys.argv", test_args)

        with patch("builtins.print") as mock_print:
            with pytest.raises(SystemExit) as exc_info:
                main()

        assert exc_info.value.code == 1
        mock_print.assert_called_with(
            "Usage: python sprite_assembler.py <tileset_image> [output_prefix]"
        )

    def test_main_default_output_prefix(self, temp_files, monkeypatch):
        """Test with default output prefix"""
        test_args = ["sprite_assembler.py", temp_files["tileset"]]
        monkeypatch.setattr("sys.argv", test_args)

        # Change to temp directory so files are created there
        original_cwd = os.getcwd()
        try:
            os.chdir(temp_files["dir"])

            with patch("builtins.print"):
                main()

            # Check default prefix was used
            files = os.listdir(".")
            assert any(f.startswith("assembled_") for f in files)

        finally:
            os.chdir(original_cwd)

    def test_main_file_not_found(self, monkeypatch):
        """Test with non-existent input file"""
        test_args = ["sprite_assembler.py", "/nonexistent/file.png"]
        monkeypatch.setattr("sys.argv", test_args)

        with pytest.raises(FileNotFoundError):
            main()

    def test_main_auto_detection(self, temp_files, monkeypatch):
        """Test automatic Kirby tile detection"""
        # Create tileset with some non-zero tiles for auto-detection
        tileset_file = Path(temp_files["dir"]) / "kirby_tiles.png"
        img = Image.new("P", (32, 32))

        # Create pattern where some tiles have non-zero pixels
        pixels = []
        for y in range(32):
            for x in range(32):
                tile_x = x // 8
                tile_y = y // 8
                tile_idx = tile_y * 4 + tile_x

                # Make first few tiles have non-zero pixels
                pattern_value = (tile_idx + 1) % 16 if tile_idx < 8 else 0
                pixels.append(pattern_value)

        img.putdata(pixels)

        palette = []
        for i in range(16):
            palette.extend([i * 16, i * 16, i * 16])
        for i in range(240):
            palette.extend([0, 0, 0])
        img.putpalette(palette)
        img.save(tileset_file)

        test_args = [
            "sprite_assembler.py",
            str(tileset_file),
            os.path.join(temp_files["dir"], "kirby_test"),
        ]
        monkeypatch.setattr("sys.argv", test_args)

        with patch("builtins.print") as mock_print:
            main()

        # Should detect Kirby tiles and print them
        print_calls = [call[0][0] for call in mock_print.call_args_list]
        kirby_detection_call = next(
            (call for call in print_calls if "Found potential Kirby tiles" in call),
            None,
        )
        assert kirby_detection_call is not None


@pytest.mark.integration
class TestSpriteAssemblerIntegration:
    """Integration tests for sprite assembler"""

    def test_full_assembly_workflow(self, temp_files):
        """Test complete assembly workflow"""
        # Load tiles
        tiles, mode, palette = load_tiles_from_image(temp_files["tileset"])

        # Create arrangements
        arrangements = [
            ("test_sprite_16x16", (2, 2), [0, 1, 4, 5]),
            ("test_sprite_24x16", (3, 2), [0, 1, 2, 4, 5, 6]),
        ]

        # Assemble individual sprites
        sprites = []
        for name, (w, h), indices in arrangements:
            sprite = assemble_sprite(tiles, indices, (w, h))
            assert sprite.size == (w * 8, h * 8)
            sprites.append((name, sprite))

        # Create sprite sheet
        sheet, sheet_sprites = create_sprite_sheet(tiles, arrangements)

        assert len(sheet_sprites) == 2
        assert sheet.width >= 24 * 2  # Width of largest sprite * 2

        # Verify sprite data integrity
        for (name1, sprite1), (name2, sprite2) in zip(sprites, sheet_sprites):
            assert name1 == name2
            assert sprite1.size == sprite2.size

    def test_round_trip_assembly_disassembly(self, temp_files):
        """Test that assembled sprites can be properly identified"""
        tiles, mode, palette = load_tiles_from_image(temp_files["tileset"])

        # Assemble a sprite
        original_indices = [0, 1, 4, 5]
        sprite = assemble_sprite(tiles, original_indices, (2, 2))

        # Save and reload sprite
        sprite_file = os.path.join(temp_files["dir"], "test_sprite.png")
        sprite.save(sprite_file)
        reloaded = Image.open(sprite_file)

        # Verify integrity
        assert reloaded.size == sprite.size
        assert list(reloaded.getdata()) == list(sprite.getdata())

        # Verify can be split back to tiles
        from sprite_editor.sprite_disassembler import split_sprite_to_tiles

        split_tiles = split_sprite_to_tiles(reloaded, (2, 2))

        assert len(split_tiles) == 4
        for i, split_tile in enumerate(split_tiles):
            original_tile = tiles[original_indices[i]]
            # Verify tile data matches (allowing for format differences)
            assert split_tile.size == original_tile.size
