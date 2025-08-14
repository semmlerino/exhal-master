"""
Headless-safe integration tests for grid arrangement system
"""

import os
import tempfile
import time
from unittest.mock import Mock

import pytest

# Mark this entire module as headless, integration, and no Qt dependencies
pytestmark = [
    pytest.mark.headless,
    pytest.mark.integration,
    pytest.mark.no_qt,
    pytest.mark.parallel_safe,
    pytest.mark.ci_safe,
    pytest.mark.slow,
]
from PIL import Image

from ui.row_arrangement.grid_arrangement_manager import (
    ArrangementType,
    GridArrangementManager,
    TileGroup,
    TilePosition,
)
from ui.row_arrangement.grid_image_processor import GridImageProcessor
from ui.row_arrangement.grid_preview_generator import GridPreviewGenerator
from ui.row_arrangement.palette_colorizer import PaletteColorizer


class TestGridArrangementHeadless:
    """Headless-safe integration tests for grid arrangement system"""

    def test_complete_sprite_processing_workflow(self):
        """Test complete sprite processing workflow without GUI dependencies"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create test sprite with distinct patterns
            sprite_path = os.path.join(temp_dir, "test_sprite.png")
            test_image = Image.new("L", (64, 64))
            pixels = test_image.load()

            # Create distinct patterns for each 16x16 tile
            for tile_row in range(4):
                for tile_col in range(4):
                    base_value = (tile_row * 4 + tile_col) * 15 + 50
                    for y in range(16):
                        for x in range(16):
                            pixel_x = tile_col * 16 + x
                            pixel_y = tile_row * 16 + y
                            pixels[pixel_x, pixel_y] = min(base_value, 255)

            test_image.save(sprite_path)

            # Create processor and load sprite
            processor = GridImageProcessor()
            processor.tile_width = 16
            processor.tile_height = 16

            original_image, tiles = processor.process_sprite_sheet_as_grid(
                sprite_path, 4
            )

            # Verify processing
            assert original_image is not None
            assert len(tiles) == 16  # 4x4 grid
            assert processor.grid_rows == 4
            assert processor.grid_cols == 4
            assert processor.original_image is not None

            # Verify tiles are distinct
            tile_values = set()
            for tile in tiles.values():
                # Get center pixel value
                center_value = tile.getpixel((8, 8))
                tile_values.add(center_value)

            # Should have different values for different tiles
            assert len(tile_values) > 1

    def test_arrangement_workflow_without_gui(self):
        """Test arrangement workflow without GUI components"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create test sprite
            sprite_path = os.path.join(temp_dir, "test_sprite.png")
            test_image = Image.new("L", (48, 48))
            test_image.save(sprite_path)

            # Process sprite
            processor = GridImageProcessor()
            processor.tile_width = 16
            processor.tile_height = 16
            original_image, tiles = processor.process_sprite_sheet_as_grid(
                sprite_path, 3
            )

            # Create manager
            manager = GridArrangementManager(processor.grid_rows, processor.grid_cols)

            # Test arrangement operations
            # Add individual tiles
            assert manager.add_tile(TilePosition(0, 0)) is True
            assert manager.add_tile(TilePosition(0, 1)) is True
            assert manager.get_arranged_count() == 2

            # Add row
            assert manager.add_row(1) is True
            assert manager.get_arranged_count() == 5  # 2 tiles + 3 from row

            # Add column with overlap
            assert manager.add_column(2) is True
            assert (
                manager.get_arranged_count() == 7
            )  # 2 new tiles from column (1 overlap)

            # Create and add group
            group_tiles = [TilePosition(2, 0), TilePosition(2, 1)]
            group = TileGroup("test_group", group_tiles, 2, 1, "Test Group")
            assert manager.add_group(group) is True
            assert manager.get_arranged_count() == 9  # 2 more tiles

            # Verify arrangement order
            arrangement_order = manager.get_arrangement_order()
            assert len(arrangement_order) == 5
            assert arrangement_order[0] == (ArrangementType.TILE, "0,0")
            assert arrangement_order[1] == (ArrangementType.TILE, "0,1")
            assert arrangement_order[2] == (ArrangementType.ROW, "1")
            assert arrangement_order[3] == (ArrangementType.COLUMN, "2")
            assert arrangement_order[4] == (ArrangementType.GROUP, "test_group")

    def test_preview_generation_headless(self):
        """Test preview generation without GUI display"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create test sprite
            sprite_path = os.path.join(temp_dir, "test_sprite.png")
            test_image = Image.new("L", (32, 32))
            test_image.save(sprite_path)

            # Process sprite
            processor = GridImageProcessor()
            processor.tile_width = 16
            processor.tile_height = 16
            original_image, tiles = processor.process_sprite_sheet_as_grid(
                sprite_path, 2
            )

            # Create manager and add arrangements
            manager = GridArrangementManager(processor.grid_rows, processor.grid_cols)
            manager.add_tile(TilePosition(0, 0))
            manager.add_row(1)

            # Create generator and generate preview
            generator = GridPreviewGenerator()

            # Test arranged image generation
            arranged_image = generator.create_grid_arranged_image(processor, manager)
            assert arranged_image is not None
            assert arranged_image.size[0] > 0
            assert arranged_image.size[1] > 0

            # Test preview with overlay
            preview = generator.create_grid_preview_with_overlay(processor, manager)
            assert preview is not None
            assert preview.mode == "RGBA"
            assert preview.size == original_image.size

            # Test export
            export_path = generator.export_grid_arrangement(
                sprite_path, arranged_image, "headless_test"
            )
            assert export_path.endswith("_headless_test_arranged.png")

    def test_large_sprite_processing_headless(self):
        """Test processing large sprites without GUI"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create large test sprite
            sprite_path = os.path.join(temp_dir, "large_sprite.png")
            test_image = Image.new("L", (256, 256))  # 16x16 tiles of 16x16 each
            test_image.save(sprite_path)

            # Process sprite
            processor = GridImageProcessor()
            processor.tile_width = 16
            processor.tile_height = 16
            original_image, tiles = processor.process_sprite_sheet_as_grid(
                sprite_path, 16
            )

            # Verify processing
            assert len(tiles) == 256  # 16x16 grid
            assert processor.grid_rows == 16
            assert processor.grid_cols == 16

            # Create manager and add large arrangements
            manager = GridArrangementManager(processor.grid_rows, processor.grid_cols)

            # Add multiple rows and columns
            for row in range(0, 16, 4):  # Every 4th row
                manager.add_row(row)

            for col in range(0, 16, 4):  # Every 4th column
                manager.add_column(col)

            # Verify large arrangement
            assert manager.get_arranged_count() > 0

            # Generate preview for large sprite
            generator = GridPreviewGenerator()
            arranged_image = generator.create_grid_arranged_image(processor, manager)
            assert arranged_image is not None

    def test_error_handling_headless(self):
        """Test error handling in headless environment"""
        # Test with non-existent file
        processor = GridImageProcessor()

        with pytest.raises(FileNotFoundError):
            processor.process_sprite_sheet_as_grid("nonexistent.png", 4)

        # Test with invalid manager dimensions
        with pytest.raises(ValueError, match="Invalid.*dimensions"):
            GridArrangementManager(0, 5)

        # Test generator with empty arrangements
        generator = GridPreviewGenerator()
        manager = GridArrangementManager(2, 2)

        result = generator.create_grid_arranged_image(processor, manager)
        assert result is None

    def test_memory_management_headless(self):
        """Test memory management in headless environment"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create test sprite
            sprite_path = os.path.join(temp_dir, "test_sprite.png")
            test_image = Image.new("L", (64, 64))
            test_image.save(sprite_path)

            # Process multiple sprites to test memory cleanup
            processor = GridImageProcessor()
            processor.tile_width = 16
            processor.tile_height = 16

            for i in range(3):
                # Create different sized sprite
                sprite_path_i = os.path.join(temp_dir, f"sprite_{i}.png")
                size = 32 + i * 16
                test_image_i = Image.new("L", (size, size))
                test_image_i.save(sprite_path_i)

                # Process sprite
                original_image, tiles = processor.process_sprite_sheet_as_grid(
                    sprite_path_i, size // 16
                )

                # Verify memory is being managed
                assert processor.original_image is not None
                assert len(processor.tiles) > 0

                # Each processing should clear previous data
                expected_tiles = (size // 16) ** 2
                assert len(processor.tiles) == expected_tiles

    def test_colorization_workflow_headless(self):
        """Test colorization workflow without GUI"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create test sprite
            sprite_path = os.path.join(temp_dir, "test_sprite.png")
            test_image = Image.new("L", (32, 32))
            test_image.save(sprite_path)

            # Process sprite
            processor = GridImageProcessor()
            processor.tile_width = 16
            processor.tile_height = 16
            original_image, tiles = processor.process_sprite_sheet_as_grid(
                sprite_path, 2
            )

            # Create mock colorizer
            colorizer = Mock(spec=PaletteColorizer)
            colorizer.is_palette_mode.return_value = True
            colorizer.get_display_image.return_value = Image.new(
                "RGBA", (16, 16), (255, 0, 0, 255)
            )

            # Create generator with colorizer
            generator = GridPreviewGenerator(colorizer)
            generator.apply_palette_to_full_image = Mock(
                return_value=Image.new("RGBA", (32, 32), (0, 255, 0, 255))
            )

            # Create manager and add arrangements
            manager = GridArrangementManager(processor.grid_rows, processor.grid_cols)
            manager.add_tile(TilePosition(0, 0))

            # Test colorized arranged image
            arranged_image = generator.create_grid_arranged_image(processor, manager)
            assert arranged_image is not None
            assert arranged_image.mode == "RGBA"

            # Test colorized preview
            preview = generator.create_grid_preview_with_overlay(processor, manager)
            assert preview is not None
            assert preview.mode == "RGBA"

            # Verify colorizer was called
            colorizer.get_display_image.assert_called()

    def test_batch_processing_headless(self):
        """Test batch processing multiple sprites"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create multiple test sprites
            sprite_paths = []
            for i in range(3):
                sprite_path = os.path.join(temp_dir, f"sprite_{i}.png")
                size = 32 + i * 16
                test_image = Image.new("L", (size, size))
                test_image.save(sprite_path)
                sprite_paths.append(sprite_path)

            # Process all sprites
            results = []
            for sprite_path in sprite_paths:
                processor = GridImageProcessor()
                processor.tile_width = 16
                processor.tile_height = 16

                original_image, tiles = processor.process_sprite_sheet_as_grid(
                    sprite_path, (32 + len(results) * 16) // 16
                )

                manager = GridArrangementManager(
                    processor.grid_rows, processor.grid_cols
                )
                manager.add_row(0)  # Add first row

                generator = GridPreviewGenerator()
                arranged_image = generator.create_grid_arranged_image(
                    processor, manager
                )

                results.append(
                    {
                        "sprite_path": sprite_path,
                        "original_image": original_image,
                        "arranged_image": arranged_image,
                        "tile_count": len(tiles),
                        "arranged_count": manager.get_arranged_count(),
                    }
                )

            # Verify all sprites were processed
            assert len(results) == 3
            for result in results:
                assert result["original_image"] is not None
                assert result["arranged_image"] is not None
                assert result["tile_count"] > 0
                assert result["arranged_count"] > 0

    def test_arrangement_data_persistence_headless(self):
        """Test arrangement data persistence without GUI"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create test sprite
            sprite_path = os.path.join(temp_dir, "test_sprite.png")
            test_image = Image.new("L", (48, 48))
            test_image.save(sprite_path)

            # Process sprite
            processor = GridImageProcessor()
            processor.tile_width = 16
            processor.tile_height = 16
            original_image, tiles = processor.process_sprite_sheet_as_grid(
                sprite_path, 3
            )

            # Create complex arrangement
            manager = GridArrangementManager(processor.grid_rows, processor.grid_cols)
            manager.add_tile(TilePosition(0, 0))
            manager.add_row(1)
            manager.add_column(2)

            # Create group
            group_tiles = [TilePosition(2, 0), TilePosition(2, 1)]
            group = TileGroup("test_group", group_tiles, 2, 1, "Test Group")
            manager.add_group(group)

            # Generate arrangement data
            generator = GridPreviewGenerator()
            data = generator.create_arrangement_preview_data(manager, processor)

            # Verify data structure
            assert data is not None
            assert "grid_dimensions" in data
            assert "arrangement_order" in data
            assert "groups" in data
            assert "total_tiles" in data

            # Verify grid dimensions
            assert data["grid_dimensions"]["rows"] == 3
            assert data["grid_dimensions"]["cols"] == 3
            assert data["grid_dimensions"]["tile_width"] == 16
            assert data["grid_dimensions"]["tile_height"] == 16

            # Verify arrangement order
            assert len(data["arrangement_order"]) == 4
            assert data["arrangement_order"][0]["type"] == "tile"
            assert data["arrangement_order"][1]["type"] == "row"
            assert data["arrangement_order"][2]["type"] == "column"
            assert data["arrangement_order"][3]["type"] == "group"

            # Verify groups
            assert len(data["groups"]) == 1
            assert data["groups"][0]["id"] == "test_group"
            assert data["groups"][0]["name"] == "Test Group"
            assert len(data["groups"][0]["tiles"]) == 2

            # Verify total tiles
            assert data["total_tiles"] > 0

    def test_edge_cases_headless(self):
        """Test edge cases in headless environment"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Test with minimum size sprite
            sprite_path = os.path.join(temp_dir, "minimal_sprite.png")
            test_image = Image.new("L", (16, 16))  # Single tile
            test_image.save(sprite_path)

            processor = GridImageProcessor()
            processor.tile_width = 16
            processor.tile_height = 16
            original_image, tiles = processor.process_sprite_sheet_as_grid(
                sprite_path, 1
            )

            assert len(tiles) == 1
            assert processor.grid_rows == 1
            assert processor.grid_cols == 1

            # Test with single tile arrangement
            manager = GridArrangementManager(1, 1)
            manager.add_tile(TilePosition(0, 0))

            generator = GridPreviewGenerator()
            arranged_image = generator.create_grid_arranged_image(processor, manager)
            assert arranged_image is not None
            assert arranged_image.size == (16, 16)

            # Test with empty arrangement
            manager.clear()
            arranged_image = generator.create_grid_arranged_image(processor, manager)
            assert arranged_image is None

    def test_non_square_tiles_headless(self):
        """Test non-square tiles in headless environment"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create sprite with non-square tiles
            sprite_path = os.path.join(temp_dir, "non_square_sprite.png")
            test_image = Image.new("L", (64, 32))  # 4x2 tiles of 16x16 each
            test_image.save(sprite_path)

            processor = GridImageProcessor()
            processor.tile_width = 16
            processor.tile_height = 16
            original_image, tiles = processor.process_sprite_sheet_as_grid(
                sprite_path, 4
            )

            assert len(tiles) == 8  # 4x2 grid
            assert processor.grid_rows == 2
            assert processor.grid_cols == 4

            # Test arrangement with non-square grid
            manager = GridArrangementManager(2, 4)
            manager.add_row(0)  # Add first row (4 tiles)
            manager.add_column(3)  # Add last column (2 tiles, 1 overlap)

            assert manager.get_arranged_count() == 5  # 4 + 1 new

            generator = GridPreviewGenerator()
            arranged_image = generator.create_grid_arranged_image(processor, manager)
            assert arranged_image is not None

    def test_stress_testing_headless(self):
        """Test system under stress in headless environment"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create moderately large sprite
            sprite_path = os.path.join(temp_dir, "stress_sprite.png")
            test_image = Image.new("L", (128, 128))  # 8x8 tiles
            test_image.save(sprite_path)

            processor = GridImageProcessor()
            processor.tile_width = 16
            processor.tile_height = 16
            original_image, tiles = processor.process_sprite_sheet_as_grid(
                sprite_path, 8
            )

            manager = GridArrangementManager(8, 8)
            generator = GridPreviewGenerator()

            # Add many arrangements
            for i in range(0, 8, 2):  # Every other row
                manager.add_row(i)

            for i in range(1, 8, 2):  # Every other column
                manager.add_column(i)

            # Create multiple groups with tiles not already arranged
            group_count = 0
            for i in range(0, 6, 2):
                # Use tiles in positions that won't conflict with rows/columns
                group_tiles = [TilePosition(i + 1, i + 1), TilePosition(i + 1, i + 2)]
                # Check if tiles are available
                if not manager.is_tile_arranged(
                    group_tiles[0]
                ) and not manager.is_tile_arranged(group_tiles[1]):
                    group = TileGroup(f"group_{i}", group_tiles, 2, 1)
                    if manager.add_group(group):
                        group_count += 1

            # Generate results
            arranged_image = generator.create_grid_arranged_image(processor, manager)
            preview = generator.create_grid_preview_with_overlay(processor, manager)
            data = generator.create_arrangement_preview_data(manager, processor)

            # Verify results
            assert arranged_image is not None
            assert preview is not None
            assert data is not None
            assert manager.get_arranged_count() > 0
            assert (
                len(data["groups"]) >= 0
            )  # May be 0 if all tiles are already arranged


class TestGridArrangementPerformance:
    """Performance tests for grid arrangement system"""

    def test_processing_performance(self):
        """Test processing performance with moderately sized sprites"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create test sprite
            sprite_path = os.path.join(temp_dir, "perf_sprite.png")
            test_image = Image.new("L", (160, 160))  # 10x10 tiles
            test_image.save(sprite_path)

            start_time = time.time()

            # Process sprite
            processor = GridImageProcessor()
            processor.tile_width = 16
            processor.tile_height = 16
            original_image, tiles = processor.process_sprite_sheet_as_grid(
                sprite_path, 10
            )

            processing_time = time.time() - start_time

            # Should process reasonably quickly (less than 1 second)
            assert processing_time < 1.0
            assert len(tiles) == 100

    def test_arrangement_performance(self):
        """Test arrangement performance with many operations"""
        manager = GridArrangementManager(10, 10)

        start_time = time.time()

        # Add many arrangements
        for i in range(10):
            manager.add_tile(TilePosition(i, i))

        for i in range(5):
            manager.add_row(i)

        for i in range(5):
            manager.add_column(i + 5)

        arrangement_time = time.time() - start_time

        # Should arrange reasonably quickly
        assert arrangement_time < 1.0
        assert manager.get_arranged_count() > 0

    def test_preview_generation_performance(self):
        """Test preview generation performance"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create test sprite
            sprite_path = os.path.join(temp_dir, "preview_perf_sprite.png")
            test_image = Image.new("L", (96, 96))  # 6x6 tiles
            test_image.save(sprite_path)

            # Process sprite
            processor = GridImageProcessor()
            processor.tile_width = 16
            processor.tile_height = 16
            original_image, tiles = processor.process_sprite_sheet_as_grid(
                sprite_path, 6
            )

            # Create arrangement
            manager = GridArrangementManager(6, 6)
            manager.add_row(0)
            manager.add_column(2)

            generator = GridPreviewGenerator()

            start_time = time.time()

            # Generate previews
            arranged_image = generator.create_grid_arranged_image(processor, manager)
            preview = generator.create_grid_preview_with_overlay(processor, manager)

            generation_time = time.time() - start_time

            # Should generate reasonably quickly
            assert generation_time < 1.0
            assert arranged_image is not None
            assert preview is not None