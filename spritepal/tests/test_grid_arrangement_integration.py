"""
Integration tests for the grid arrangement system
"""

import os
import tempfile
from unittest.mock import Mock

import pytest
from PIL import Image

from ui.row_arrangement.grid_arrangement_manager import (
# Systematic pytest markers applied based on test content analysis
pytestmark = [
    pytest.mark.file_io,
    pytest.mark.headless,
    pytest.mark.integration,
    pytest.mark.mock_only,
    pytest.mark.no_qt,
    pytest.mark.parallel_safe,
    pytest.mark.rom_data,
]


    ArrangementType,
    GridArrangementManager,
    TileGroup,
    TilePosition,
)
from ui.row_arrangement.grid_image_processor import GridImageProcessor
from ui.row_arrangement.grid_preview_generator import GridPreviewGenerator
from ui.row_arrangement.palette_colorizer import PaletteColorizer


class TestGridArrangementIntegration:
    """Integration tests for the complete grid arrangement workflow"""

    def test_complete_workflow_basic(self):
        """Test complete workflow from image loading to arrangement generation"""
        # Create a test sprite sheet
        sprite_sheet = Image.new("L", (32, 32))

        # Add some pattern to make tiles distinct
        pixels = sprite_sheet.load()
        for y in range(32):
            for x in range(32):
                # Create a pattern based on tile position
                tile_x = x // 16
                tile_y = y // 16
                value = (tile_x * 2 + tile_y) * 50 + 50
                pixels[x, y] = min(value, 255)

        # Create components
        processor = GridImageProcessor()
        manager = GridArrangementManager(2, 2)
        generator = GridPreviewGenerator()

        # Process sprite sheet
        processor.tile_width = 16
        processor.tile_height = 16
        processor.original_image = sprite_sheet
        tiles = processor.extract_tiles_as_grid(sprite_sheet, 2)

        # Verify tiles were extracted correctly
        assert len(tiles) == 4
        assert processor.grid_rows == 2
        assert processor.grid_cols == 2

        # Add arrangements
        manager.add_tile(TilePosition(0, 0))
        manager.add_row(1)
        manager.add_column(1)

        # Generate arranged image
        arranged_image = generator.create_grid_arranged_image(processor, manager)

        # Verify arranged image was created
        assert arranged_image is not None
        assert arranged_image.size[0] > 0
        assert arranged_image.size[1] > 0

        # Verify preview with overlay
        preview = generator.create_grid_preview_with_overlay(processor, manager)
        assert preview is not None
        assert preview.mode == "RGBA"
        assert preview.size == (32, 32)

    def test_complete_workflow_with_groups(self):
        """Test workflow with group creation and management"""
        # Create a larger test sprite sheet
        sprite_sheet = Image.new("L", (48, 32))

        # Create components
        processor = GridImageProcessor()
        manager = GridArrangementManager(2, 3)
        generator = GridPreviewGenerator()

        # Process sprite sheet
        processor.tile_width = 16
        processor.tile_height = 16
        processor.original_image = sprite_sheet
        processor.extract_tiles_as_grid(sprite_sheet, 3)

        # Create and add a group
        group_tiles = [TilePosition(0, 0), TilePosition(0, 1), TilePosition(1, 0)]
        group = TileGroup("character_group", group_tiles, 2, 2, "Character Tiles")

        # Add group and individual tile
        manager.add_group(group)
        manager.add_tile(TilePosition(1, 2))

        # Generate arranged image
        arranged_image = generator.create_grid_arranged_image(processor, manager)

        # Verify arranged image includes group and individual tile
        assert arranged_image is not None

        # Check arrangement data
        preview_data = generator.create_arrangement_preview_data(manager, processor)
        assert preview_data["total_tiles"] == 4
        assert len(preview_data["groups"]) == 1
        assert preview_data["groups"][0]["id"] == "character_group"
        assert preview_data["groups"][0]["name"] == "Character Tiles"

    def test_complete_workflow_with_colorization(self):
        """Test workflow with palette colorization"""
        # Create test sprite sheet
        sprite_sheet = Image.new("L", (32, 32))

        # Create colorizer mock
        colorizer = Mock(spec=PaletteColorizer)
        colorizer.is_palette_mode.return_value = True

        # Mock colorizer methods
        colorized_tile = Image.new("RGBA", (16, 16), (255, 0, 0, 255))
        colorizer.get_display_image.return_value = colorized_tile

        colorized_sheet = Image.new("RGBA", (32, 32), (0, 255, 0, 255))

        # Create components
        processor = GridImageProcessor()
        manager = GridArrangementManager(2, 2)
        generator = GridPreviewGenerator(colorizer)

        # Mock the inherited method
        generator.apply_palette_to_full_image = Mock(return_value=colorized_sheet)

        # Process sprite sheet
        processor.tile_width = 16
        processor.tile_height = 16
        processor.original_image = sprite_sheet
        processor.extract_tiles_as_grid(sprite_sheet, 2)

        # Add arrangements
        manager.add_tile(TilePosition(0, 0))
        manager.add_tile(TilePosition(1, 1))

        # Generate arranged image with colorization
        arranged_image = generator.create_grid_arranged_image(processor, manager)

        # Verify colorized arranged image
        assert arranged_image is not None
        assert arranged_image.mode == "RGBA"

        # Verify colorizer was called
        colorizer.get_display_image.assert_called()

        # Generate preview with colorization
        preview = generator.create_grid_preview_with_overlay(processor, manager)
        assert preview is not None
        assert preview.mode == "RGBA"

        # Verify colorizer methods were called
        generator.apply_palette_to_full_image.assert_called_once_with(sprite_sheet)

    def test_workflow_with_file_operations(self):
        """Test workflow with actual file I/O operations"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create test sprite file
            sprite_path = os.path.join(temp_dir, "test_sprite.png")
            test_image = Image.new("L", (32, 32))
            test_image.save(sprite_path)

            # Create components
            processor = GridImageProcessor()
            manager = GridArrangementManager(2, 2)
            generator = GridPreviewGenerator()

            # Process sprite file
            original_image, tiles = processor.process_sprite_sheet_as_grid(
                sprite_path, 2
            )

            # Verify file was processed
            assert original_image is not None
            assert len(tiles) == 4
            assert processor.original_image is not None

            # Add arrangements
            manager.add_row(0)
            manager.add_column(1)

            # Generate and export arranged image
            arranged_image = generator.create_grid_arranged_image(processor, manager)
            assert arranged_image is not None

            # Export arranged image
            exported_path = generator.export_grid_arrangement(
                sprite_path, arranged_image, "test_arrangement"
            )

            # Verify export
            expected_path = os.path.join(
                temp_dir, "test_sprite_test_arrangement_arranged.png"
            )
            assert exported_path == expected_path

    def test_workflow_error_handling(self):
        """Test error handling throughout the workflow"""
        # Create components
        processor = GridImageProcessor()
        manager = GridArrangementManager(2, 2)
        generator = GridPreviewGenerator()

        # Test processing non-existent file
        with pytest.raises(FileNotFoundError):
            processor.process_sprite_sheet_as_grid("nonexistent.png", 2)

        # Test creating arranged image with no processor data
        arranged_image = generator.create_grid_arranged_image(processor, manager)
        assert arranged_image is None

        # Test creating preview with no original image
        preview = generator.create_grid_preview_with_overlay(processor, manager)
        assert preview is not None
        assert preview.size == (1, 1)

        # Test invalid grid dimensions
        with pytest.raises(ValueError, match="Invalid.*dimensions"):
            GridArrangementManager(0, 2)

    def test_workflow_arrangement_order_consistency(self):
        """Test that arrangement order is consistent across components"""
        # Create test sprite sheet
        sprite_sheet = Image.new("L", (48, 32))

        # Create components
        processor = GridImageProcessor()
        manager = GridArrangementManager(2, 3)
        generator = GridPreviewGenerator()

        # Process sprite sheet
        processor.tile_width = 16
        processor.tile_height = 16
        processor.original_image = sprite_sheet
        processor.extract_tiles_as_grid(sprite_sheet, 3)

        # Add arrangements in specific order
        manager.add_tile(TilePosition(0, 0))
        manager.add_row(1)
        manager.add_column(2)

        # Create group with tiles that aren't already arranged
        group_tiles = [TilePosition(0, 1)]  # Only use tiles not already arranged
        group = TileGroup("test_group", group_tiles, 1, 1)
        result = manager.add_group(group)
        assert result is True  # Make sure group was added successfully

        # Get arrangement order
        arrangement_order = manager.get_arrangement_order()

        # Verify order is preserved
        assert len(arrangement_order) == 4
        assert arrangement_order[0] == (ArrangementType.TILE, "0,0")
        assert arrangement_order[1] == (ArrangementType.ROW, "1")
        assert arrangement_order[2] == (ArrangementType.COLUMN, "2")
        assert arrangement_order[3] == (ArrangementType.GROUP, "test_group")

        # Generate arranged image - should respect order
        arranged_image = generator.create_grid_arranged_image(processor, manager)
        assert arranged_image is not None

        # Create preview data - should match arrangement order
        preview_data = generator.create_arrangement_preview_data(manager, processor)
        assert len(preview_data["arrangement_order"]) == 4
        assert preview_data["arrangement_order"][0]["type"] == "tile"
        assert preview_data["arrangement_order"][0]["key"] == "0,0"

    def test_workflow_with_overlapping_arrangements(self):
        """Test workflow with overlapping row/column arrangements"""
        # Create test sprite sheet
        sprite_sheet = Image.new("L", (48, 48))

        # Create components
        processor = GridImageProcessor()
        manager = GridArrangementManager(3, 3)
        generator = GridPreviewGenerator()

        # Process sprite sheet
        processor.tile_width = 16
        processor.tile_height = 16
        processor.original_image = sprite_sheet
        processor.extract_tiles_as_grid(sprite_sheet, 3)

        # Add overlapping arrangements
        manager.add_row(1)  # Row 1: (1,0), (1,1), (1,2)
        manager.add_column(1)  # Column 1: (0,1), (1,1), (2,1) - overlaps at (1,1)

        # Verify overlapping arrangement
        assert manager.get_arranged_count() == 5  # 3 from row + 2 new from column
        assert manager.is_tile_arranged(TilePosition(1, 1))  # Overlap point

        # Generate arranged image with overlaps
        arranged_image = generator.create_grid_arranged_image(processor, manager)
        assert arranged_image is not None

        # Verify arrangement order includes both operations
        arrangement_order = manager.get_arrangement_order()
        assert len(arrangement_order) == 2
        assert arrangement_order[0] == (ArrangementType.ROW, "1")
        assert arrangement_order[1] == (ArrangementType.COLUMN, "1")

    def test_workflow_large_grid_handling(self):
        """Test workflow with large grid dimensions"""
        # Create large test sprite sheet
        sprite_sheet = Image.new("L", (160, 160))  # 10x10 tiles of 16x16

        # Create components
        processor = GridImageProcessor()
        manager = GridArrangementManager(10, 10)
        generator = GridPreviewGenerator()

        # Process sprite sheet
        processor.tile_width = 16
        processor.tile_height = 16
        processor.original_image = sprite_sheet
        tiles = processor.extract_tiles_as_grid(sprite_sheet, 10)

        # Verify large grid was processed
        assert len(tiles) == 100
        assert processor.grid_rows == 10
        assert processor.grid_cols == 10

        # Add multiple arrangements
        manager.add_row(0)
        manager.add_row(9)
        manager.add_column(0)
        manager.add_column(9)

        # Create large group
        group_tiles = [
            TilePosition(4, 4),
            TilePosition(4, 5),
            TilePosition(5, 4),
            TilePosition(5, 5),
        ]
        group = TileGroup("center_group", group_tiles, 2, 2)
        manager.add_group(group)

        # Generate arranged image
        arranged_image = generator.create_grid_arranged_image(processor, manager)
        assert arranged_image is not None

        # Verify arrangement count
        # Row 0: 10 tiles
        # Row 9: 10 tiles
        # Column 0: 8 new tiles (excluding overlaps with rows 0 and 9)
        # Column 9: 8 new tiles (excluding overlaps with rows 0 and 9)
        # Group: 4 tiles at center
        expected_count = 10 + 10 + 8 + 8 + 4  # 40 total
        assert manager.get_arranged_count() == expected_count

    def test_workflow_memory_cleanup(self):
        """Test that components properly clean up memory"""
        # Create test sprite sheet
        sprite_sheet = Image.new("L", (32, 32))

        # Create components
        processor = GridImageProcessor()
        manager = GridArrangementManager(2, 2)
        GridPreviewGenerator()

        # Process sprite sheet
        processor.tile_width = 16
        processor.tile_height = 16
        processor.original_image = sprite_sheet
        processor.extract_tiles_as_grid(sprite_sheet, 2)

        # Add arrangements
        manager.add_tile(TilePosition(0, 0))
        manager.add_row(1)

        # Verify data is present
        assert len(processor.tiles) == 4
        assert processor.original_image is not None
        assert manager.get_arranged_count() == 3

        # Clear arrangements
        manager.clear()
        assert manager.get_arranged_count() == 0
        assert len(manager.get_groups()) == 0

        # Process new sprite sheet (should clear old data)
        new_sprite_sheet = Image.new("L", (16, 16))
        processor.tile_width = 16
        processor.tile_height = 16
        processor.original_image = new_sprite_sheet
        processor.extract_tiles_as_grid(new_sprite_sheet, 1)

        # Verify old data was cleared
        assert len(processor.tiles) == 1
        assert processor.grid_rows == 1
        assert processor.grid_cols == 1

    def test_workflow_edge_cases(self):
        """Test workflow with edge cases and boundary conditions"""
        # Create minimal sprite sheet
        sprite_sheet = Image.new("L", (16, 16))  # Single tile

        # Create components
        processor = GridImageProcessor()
        manager = GridArrangementManager(1, 1)
        generator = GridPreviewGenerator()

        # Process single tile
        processor.tile_width = 16
        processor.tile_height = 16
        processor.original_image = sprite_sheet
        tiles = processor.extract_tiles_as_grid(sprite_sheet, 1)

        # Add single tile
        manager.add_tile(TilePosition(0, 0))

        # Generate arranged image
        arranged_image = generator.create_grid_arranged_image(processor, manager)
        assert arranged_image is not None
        assert arranged_image.size == (16, 16)

        # Test with empty arrangement
        manager.clear()
        arranged_image = generator.create_grid_arranged_image(processor, manager)
        assert arranged_image is None

        # Test with non-square tiles
        non_square_sheet = Image.new("L", (32, 16))
        processor.tile_width = 16
        processor.tile_height = 8
        processor.original_image = non_square_sheet
        tiles = processor.extract_tiles_as_grid(non_square_sheet, 2)

        assert len(tiles) == 4
        assert processor.grid_rows == 2
        assert processor.grid_cols == 2

        # Verify tile sizes
        for tile in tiles.values():
            assert tile.size == (16, 8)

    def test_workflow_signal_integration(self):
        """Test that signals are properly emitted throughout the workflow"""
        # Create components
        GridImageProcessor()
        manager = GridArrangementManager(2, 2)
        GridPreviewGenerator()

        # Mock all signals
        manager.tile_added = Mock()
        manager.tile_removed = Mock()
        manager.group_added = Mock()
        manager.group_removed = Mock()
        manager.arrangement_changed = Mock()
        manager.arrangement_cleared = Mock()

        # Add arrangements and verify signals
        manager.add_tile(TilePosition(0, 0))
        manager.tile_added.emit.assert_called_once_with(TilePosition(0, 0))
        manager.arrangement_changed.emit.assert_called()

        # Add row
        manager.add_row(1)
        assert manager.arrangement_changed.emit.call_count >= 2

        # Add group with tiles not already arranged
        group_tiles = [TilePosition(0, 1)]  # Only use tiles not already arranged
        group = TileGroup("test_group", group_tiles, 1, 1)
        result = manager.add_group(group)
        assert result is True  # Verify group was added successfully
        manager.group_added.emit.assert_called_once_with("test_group")

        # Remove group
        manager.remove_group("test_group")
        manager.group_removed.emit.assert_called_once_with("test_group")

        # Clear all
        manager.clear()
        manager.arrangement_cleared.emit.assert_called_once()

    def test_workflow_state_consistency(self):
        """Test that component states remain consistent throughout workflow"""
        # Create test sprite sheet
        sprite_sheet = Image.new("L", (48, 32))

        # Create components
        processor = GridImageProcessor()
        manager = GridArrangementManager(2, 3)
        generator = GridPreviewGenerator()

        # Process sprite sheet
        processor.tile_width = 16
        processor.tile_height = 16
        processor.original_image = sprite_sheet
        processor.extract_tiles_as_grid(sprite_sheet, 3)

        # Add various arrangements
        manager.add_tile(TilePosition(0, 0))
        manager.add_row(1)
        manager.add_column(2)

        # Verify state consistency
        assert len(processor.tiles) == 6  # 2 rows * 3 cols
        assert processor.grid_rows == 2
        assert processor.grid_cols == 3
        assert processor.original_image is not None

        # Manager state
        assert manager.get_arranged_count() == 5  # 1 + 3 + 2 (with overlap)
        assert len(manager.get_arrangement_order()) == 3

        # Generate products and verify consistency
        arranged_image = generator.create_grid_arranged_image(processor, manager)
        preview = generator.create_grid_preview_with_overlay(processor, manager)
        preview_data = generator.create_arrangement_preview_data(manager, processor)

        # All should be consistent
        assert arranged_image is not None
        assert preview is not None
        assert preview_data["total_tiles"] == 5
        assert preview_data["grid_dimensions"]["rows"] == 2
        assert preview_data["grid_dimensions"]["cols"] == 3

        # Modify state and verify consistency maintained
        manager.add_tile(TilePosition(1, 1))  # This tile should already be arranged
        assert manager.get_arranged_count() == 5  # Should not change

        # Clear and verify clean state
        manager.clear()
        assert manager.get_arranged_count() == 0
        assert len(manager.get_arrangement_order()) == 0
        assert len(manager.get_groups()) == 0
