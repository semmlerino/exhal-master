#!/usr/bin/env python3
"""
Tests for sprite_disassembler module
Tests sprite disassembly functionality with comprehensive coverage
"""

import os
from pathlib import Path
from unittest.mock import patch

import pytest
from PIL import Image

from sprite_editor.sprite_disassembler import (
    main,
    process_edit_sheet,
    rebuild_tileset,
    split_sprite_to_tiles,
)


@pytest.fixture
def temp_files(tmp_path):
    """Create temporary test files with tile patterns"""
    # Create original tileset (4x4 tiles = 32x32 pixels)
    tileset_file = tmp_path / "original_tileset.png"
    img = Image.new("P", (32, 32))

    # Create distinct patterns for each tile
    pixels = []
    for y in range(32):
        for x in range(32):
            tile_x = x // 8
            tile_y = y // 8
            tile_idx = tile_y * 4 + tile_x
            pattern_value = (tile_idx + (x % 8) + (y % 8)) % 16
            pixels.append(pattern_value)

    img.putdata(pixels)

    # Set palette
    palette = []
    for i in range(16):
        palette.extend([i * 16, i * 16, i * 16])
    for i in range(240):
        palette.extend([0, 0, 0])
    img.putpalette(palette)
    img.save(tileset_file)

    # Create test sprite (2x2 tiles = 16x16 pixels)
    sprite_file = tmp_path / "assembled_test_sprite.png"
    sprite_img = Image.new("P", (16, 16))
    sprite_pixels = []
    for y in range(16):
        for x in range(16):
            # Create modified pattern for edited sprite
            pattern_value = ((x + y) * 2) % 16
            sprite_pixels.append(pattern_value)
    sprite_img.putdata(sprite_pixels)
    sprite_img.putpalette(palette)
    sprite_img.save(sprite_file)

    # Create arrangements file
    arrangements_file = tmp_path / "assembled_arrangements.txt"
    arrangements_content = """test_sprite|2,2|0,1,4,5
other_sprite|3,2|2,3,6,7,8,9
single_tile|1,1|15"""
    arrangements_file.write_text(arrangements_content)

    # Create edit sheet (left=original, right=edited)
    edit_sheet_file = tmp_path / "assembled_edit_sheet.png"
    sheet = Image.new(
        "RGBA", (64, 40), (0, 0, 0, 0)
    )  # 32*2 wide, space for 2 sprites + padding

    # Left side: original sprites
    original_sprite1 = Image.new("P", (16, 16))
    original_sprite1.putdata([i % 16 for i in range(256)])
    original_sprite1.putpalette(palette)
    sheet.paste(original_sprite1, (0, 0))

    # Right side: edited sprites
    edited_sprite1 = Image.new("P", (16, 16))
    edited_sprite1.putdata([(i * 2) % 16 for i in range(256)])
    edited_sprite1.putpalette(palette)
    sheet.paste(edited_sprite1, (32, 0))

    sheet.save(edit_sheet_file)

    return {
        "tileset": str(tileset_file),
        "sprite": str(sprite_file),
        "arrangements": str(arrangements_file),
        "edit_sheet": str(edit_sheet_file),
        "dir": str(tmp_path),
    }


@pytest.mark.unit
class TestSplitSpriteToTiles:
    """Test sprite splitting functionality"""

    def test_split_sprite_2x2(self, temp_files):
        """Test splitting 2x2 sprite"""
        sprite = Image.open(temp_files["sprite"])

        tiles = split_sprite_to_tiles(sprite, (2, 2))

        assert len(tiles) == 4
        for tile in tiles:
            assert tile.size == (8, 8)

    def test_split_sprite_3x2(self):
        """Test splitting 3x2 sprite"""
        # Create 3x2 sprite (24x16 pixels)
        sprite = Image.new("P", (24, 16))
        sprite.putdata([i % 16 for i in range(24 * 16)])

        tiles = split_sprite_to_tiles(sprite, (3, 2))

        assert len(tiles) == 6
        for tile in tiles:
            assert tile.size == (8, 8)

    def test_split_sprite_1x1(self):
        """Test splitting single tile sprite"""
        sprite = Image.new("P", (8, 8))
        sprite.putdata([5] * 64)

        tiles = split_sprite_to_tiles(sprite, (1, 1))

        assert len(tiles) == 1
        assert tiles[0].size == (8, 8)
        assert all(p == 5 for p in tiles[0].getdata())

    def test_split_sprite_custom_tile_size(self):
        """Test splitting with custom tile size"""
        sprite = Image.new("P", (32, 16))  # 2x1 tiles at 16x16 each
        sprite.putdata([i % 16 for i in range(32 * 16)])

        tiles = split_sprite_to_tiles(sprite, (2, 1), tile_size=16)

        assert len(tiles) == 2
        for tile in tiles:
            assert tile.size == (16, 16)

    def test_split_sprite_empty_arrangement(self):
        """Test with empty arrangement"""
        sprite = Image.new("P", (8, 8))

        tiles = split_sprite_to_tiles(sprite, (0, 0))

        assert len(tiles) == 0


@pytest.mark.unit
class TestRebuildTileset:
    """Test tileset rebuilding functionality"""

    def test_rebuild_tileset_success(self, temp_files):
        """Test successful tileset rebuilding"""
        edited_sprites = [temp_files["sprite"]]

        new_tileset = rebuild_tileset(
            temp_files["tileset"], edited_sprites, temp_files["arrangements"]
        )

        assert new_tileset.size == (32, 32)  # Same as original
        assert new_tileset.mode == "P"

        # Verify some tiles were modified
        original = Image.open(temp_files["tileset"])
        original_data = list(original.getdata())
        new_data = list(new_tileset.getdata())

        # Should be different due to edited sprite
        assert original_data != new_data

    def test_rebuild_tileset_multiple_sprites(self, temp_files):
        """Test with multiple edited sprites"""
        # Create second sprite
        sprite2_file = Path(temp_files["dir"]) / "assembled_other_sprite.png"
        sprite2 = Image.new("P", (24, 16))  # 3x2 tiles
        sprite2.putdata([15] * (24 * 16))  # All white
        sprite2.save(sprite2_file)

        edited_sprites = [temp_files["sprite"], str(sprite2_file)]

        with patch("builtins.print") as mock_print:
            new_tileset = rebuild_tileset(
                temp_files["tileset"], edited_sprites, temp_files["arrangements"]
            )

        assert new_tileset.size == (32, 32)

        # Check both sprites were processed
        mock_print.assert_any_call("Processed test_sprite: replaced 4 tiles")
        mock_print.assert_any_call("Processed other_sprite: replaced 6 tiles")

    def test_rebuild_tileset_file_not_found(self, temp_files):
        """Test with non-existent original tileset"""
        with pytest.raises(FileNotFoundError):
            rebuild_tileset(
                "/nonexistent/tileset.png",
                [temp_files["sprite"]],
                temp_files["arrangements"],
            )

    def test_rebuild_tileset_invalid_arrangements(self, temp_files, tmp_path):
        """Test with invalid arrangements file"""
        # Create invalid arrangements file
        bad_arrangements = tmp_path / "bad_arrangements.txt"
        bad_arrangements.write_text("invalid|format\ntest_sprite|2,2|0,1,4,5")

        # Should skip invalid lines but process valid ones
        new_tileset = rebuild_tileset(
            temp_files["tileset"], [temp_files["sprite"]], str(bad_arrangements)
        )

        assert new_tileset.size == (32, 32)

    def test_rebuild_tileset_missing_arrangements(self, temp_files, tmp_path):
        """Test with missing arrangements file"""
        with pytest.raises(FileNotFoundError):
            rebuild_tileset(
                temp_files["tileset"],
                [temp_files["sprite"]],
                "/nonexistent/arrangements.txt",
            )

    def test_rebuild_tileset_sprite_not_in_arrangements(self, temp_files, tmp_path):
        """Test with sprite not listed in arrangements"""
        # Create sprite with name not in arrangements
        unknown_sprite = tmp_path / "assembled_unknown_sprite.png"
        sprite = Image.new("P", (8, 8))
        sprite.save(unknown_sprite)

        # Should skip unknown sprite
        new_tileset = rebuild_tileset(
            temp_files["tileset"], [str(unknown_sprite)], temp_files["arrangements"]
        )

        # Should be identical to original since no valid sprites processed
        original = Image.open(temp_files["tileset"])
        assert list(new_tileset.getdata()) == list(original.getdata())

    def test_rebuild_tileset_out_of_bounds_index(self, temp_files, tmp_path):
        """Test with tile index out of bounds"""
        # Create arrangements with out-of-bounds tile index
        bad_arrangements = tmp_path / "oob_arrangements.txt"
        bad_arrangements.write_text("test_sprite|1,1|999")  # Index too high

        # Should handle gracefully
        new_tileset = rebuild_tileset(
            temp_files["tileset"], [temp_files["sprite"]], str(bad_arrangements)
        )

        assert new_tileset.size == (32, 32)


@pytest.mark.unit
class TestProcessEditSheet:
    """Test edit sheet processing functionality"""

    def test_process_edit_sheet_success(self, temp_files):
        """Test successful edit sheet processing"""
        with patch("builtins.print") as mock_print:
            new_tileset = process_edit_sheet(
                temp_files["edit_sheet"],
                temp_files["arrangements"],
                temp_files["tileset"],
            )

        assert new_tileset.size == (32, 32)
        assert new_tileset.mode == "P"

        # Should process at least one sprite
        print_calls = [call[0][0] for call in mock_print.call_args_list]
        assert any("Processed" in call for call in print_calls)

    def test_process_edit_sheet_file_not_found(self, temp_files):
        """Test with non-existent edit sheet"""
        with pytest.raises(FileNotFoundError):
            process_edit_sheet(
                "/nonexistent/sheet.png",
                temp_files["arrangements"],
                temp_files["tileset"],
            )

    def test_process_edit_sheet_empty_arrangements(self, temp_files, tmp_path):
        """Test with empty arrangements file"""
        empty_arrangements = tmp_path / "empty_arrangements.txt"
        empty_arrangements.write_text("")

        new_tileset = process_edit_sheet(
            temp_files["edit_sheet"], str(empty_arrangements), temp_files["tileset"]
        )

        # Should return unchanged tileset
        original = Image.open(temp_files["tileset"])
        assert list(new_tileset.getdata()) == list(original.getdata())

    def test_process_edit_sheet_malformed_sheet(self, temp_files, tmp_path):
        """Test with malformed edit sheet"""
        # Create sheet that's too small
        small_sheet = tmp_path / "small_sheet.png"
        small_img = Image.new("RGBA", (8, 8))
        small_img.save(small_sheet)

        # Should handle gracefully
        new_tileset = process_edit_sheet(
            str(small_sheet), temp_files["arrangements"], temp_files["tileset"]
        )

        assert new_tileset.size == (32, 32)


@pytest.mark.unit
class TestMainFunction:
    """Test main entry point"""

    def test_main_no_arguments(self, monkeypatch):
        """Test with no command line arguments"""
        test_args = ["sprite_disassembler.py"]
        monkeypatch.setattr("sys.argv", test_args)

        with patch("builtins.print") as mock_print:
            with pytest.raises(SystemExit) as exc_info:
                main()

        assert exc_info.value.code == 1
        mock_print.assert_any_call(
            "Usage: python sprite_disassembler.py <original_tileset> <edited_sprite(s)> [output_tileset]"
        )

    def test_main_individual_sprites(self, temp_files, monkeypatch):
        """Test processing individual sprites"""
        output_file = os.path.join(temp_files["dir"], "output_tileset.png")

        test_args = [
            "sprite_disassembler.py",
            temp_files["tileset"],
            temp_files["sprite"],
            output_file,
        ]
        monkeypatch.setattr("sys.argv", test_args)

        with patch("builtins.print") as mock_print:
            main()

        assert os.path.exists(output_file)
        mock_print.assert_any_call(
            f"Using arrangements from: {temp_files['arrangements']}"
        )
        mock_print.assert_any_call(f"\nSaved updated tileset to: {output_file}")

    def test_main_individual_sprites_default_output(self, temp_files, monkeypatch):
        """Test with default output filename"""
        test_args = [
            "sprite_disassembler.py",
            temp_files["tileset"],
            temp_files["sprite"],
        ]
        monkeypatch.setattr("sys.argv", test_args)

        # Change to temp directory so default file is created there
        original_cwd = os.getcwd()
        try:
            os.chdir(temp_files["dir"])

            with patch("builtins.print"):
                main()

            assert os.path.exists("updated_tileset.png")

        finally:
            os.chdir(original_cwd)

    def test_main_edit_sheet_mode(self, temp_files, monkeypatch):
        """Test processing edit sheet"""
        output_file = os.path.join(temp_files["dir"], "sheet_output.png")

        test_args = [
            "sprite_disassembler.py",
            temp_files["tileset"],
            temp_files["edit_sheet"],
            "--sheet",
            output_file,
        ]
        monkeypatch.setattr("sys.argv", test_args)

        with patch("builtins.print") as mock_print:
            main()

        assert os.path.exists(output_file)
        mock_print.assert_any_call(f"Processing edit sheet: {temp_files['edit_sheet']}")
        mock_print.assert_any_call(f"\nSaved updated tileset to: {output_file}")

    def test_main_edit_sheet_default_output(self, temp_files, monkeypatch):
        """Test edit sheet with default output"""
        test_args = [
            "sprite_disassembler.py",
            temp_files["tileset"],
            temp_files["edit_sheet"],
            "--sheet",
        ]
        monkeypatch.setattr("sys.argv", test_args)

        original_cwd = os.getcwd()
        try:
            os.chdir(temp_files["dir"])

            with patch("builtins.print"):
                main()

            assert os.path.exists("updated_tileset.png")

        finally:
            os.chdir(original_cwd)

    def test_main_multiple_sprites(self, temp_files, monkeypatch, tmp_path):
        """Test with multiple sprite files"""
        # Create second sprite
        sprite2 = tmp_path / "assembled_other_sprite.png"
        Image.new("P", (8, 8)).save(sprite2)

        output_file = os.path.join(temp_files["dir"], "multi_output.png")

        test_args = [
            "sprite_disassembler.py",
            temp_files["tileset"],
            temp_files["sprite"],
            str(sprite2),
            output_file,
        ]
        monkeypatch.setattr("sys.argv", test_args)

        with patch("builtins.print"):
            main()

        assert os.path.exists(output_file)

    def test_main_missing_arrangements_file(self, temp_files, monkeypatch, tmp_path):
        """Test when arrangements file cannot be found"""
        # Create sprite in location without arrangements file
        isolated_sprite = tmp_path / "isolated" / "assembled_test.png"
        isolated_sprite.parent.mkdir()
        Image.new("P", (8, 8)).save(isolated_sprite)

        test_args = [
            "sprite_disassembler.py",
            temp_files["tileset"],
            str(isolated_sprite),
        ]
        monkeypatch.setattr("sys.argv", test_args)

        with patch("builtins.print") as mock_print:
            with pytest.raises(SystemExit) as exc_info:
                main()

        assert exc_info.value.code == 1
        mock_print.assert_any_call("Error: Could not find arrangements file")

    def test_main_indexed_mode_notice(self, temp_files, monkeypatch):
        """Test notice for indexed mode conversion"""
        output_file = os.path.join(temp_files["dir"], "indexed_output.png")

        test_args = [
            "sprite_disassembler.py",
            temp_files["tileset"],
            temp_files["sprite"],
            output_file,
        ]
        monkeypatch.setattr("sys.argv", test_args)

        with patch("builtins.print") as mock_print:
            main()

        # Should suggest SNES conversion for indexed images
        print_calls = [call[0][0] for call in mock_print.call_args_list]
        snes_notice = next(
            (call for call in print_calls if "png_to_snes.py" in call), None
        )
        assert snes_notice is not None


@pytest.mark.integration
class TestSpriteDisassemblerIntegration:
    """Integration tests for sprite disassembler"""

    def test_full_disassembly_workflow(self, temp_files):
        """Test complete disassembly workflow"""
        # Split sprite into tiles
        sprite = Image.open(temp_files["sprite"])
        tiles = split_sprite_to_tiles(sprite, (2, 2))

        assert len(tiles) == 4

        # Rebuild tileset
        new_tileset = rebuild_tileset(
            temp_files["tileset"], [temp_files["sprite"]], temp_files["arrangements"]
        )

        # Verify tileset was modified
        original = Image.open(temp_files["tileset"])
        assert list(new_tileset.getdata()) != list(original.getdata())

    def test_round_trip_assembly_disassembly(self, temp_files):
        """Test assembly followed by disassembly"""
        from sprite_editor.sprite_assembler import (
            assemble_sprite,
            load_tiles_from_image,
        )

        # Start with original tileset
        original_tiles, _, _ = load_tiles_from_image(temp_files["tileset"])

        # Assemble a sprite
        assembled = assemble_sprite(original_tiles, [0, 1, 4, 5], (2, 2))

        # Save assembled sprite
        assembled_file = os.path.join(temp_files["dir"], "assembled_round_trip.png")
        assembled.save(assembled_file)

        # Split it back to tiles
        split_tiles = split_sprite_to_tiles(assembled, (2, 2))

        # Verify we got back the same number of tiles
        assert len(split_tiles) == 4

        # Verify dimensions are preserved
        for tile in split_tiles:
            assert tile.size == (8, 8)

    def test_edit_sheet_workflow(self, temp_files):
        """Test complete edit sheet workflow"""
        # Process edit sheet
        new_tileset = process_edit_sheet(
            temp_files["edit_sheet"], temp_files["arrangements"], temp_files["tileset"]
        )

        # Verify modifications were applied
        original = Image.open(temp_files["tileset"])
        assert list(new_tileset.getdata()) != list(original.getdata())

        # Save and verify can be reloaded
        output_file = os.path.join(temp_files["dir"], "processed_tileset.png")
        new_tileset.save(output_file)

        reloaded = Image.open(output_file)
        assert reloaded.size == new_tileset.size
        assert list(reloaded.getdata()) == list(new_tileset.getdata())
