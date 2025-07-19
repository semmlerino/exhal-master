#!/usr/bin/env python3
"""
Unit tests for pixel editor manager classes
Tests FileManager, ToolManager, and PaletteManager
"""

import os
import tempfile
from unittest.mock import MagicMock

import numpy as np
import pytest

from pixel_editor.core.pixel_editor_managers import (
    ColorPickerTool,
    FileManager,
    FillTool,
    PaletteManager,
    PencilTool,
    ToolManager,
    ToolType,
)
from pixel_editor.core.pixel_editor_models import ImageModel, PaletteModel
from pixel_editor.core.pixel_editor_workers import (
    FileLoadWorker,
    FileSaveWorker,
    PaletteLoadWorker,
)


class TestToolClasses:
    """Test individual tool implementations"""

    @pytest.fixture
    def image_model(self):
        """Create test image model"""
        return ImageModel(width=8, height=8)

    def test_pencil_tool_press(self, image_model):
        """Test pencil tool on press"""
        tool = PencilTool()

        # Draw pixel
        changed = tool.on_press(3, 4, 5, image_model)

        assert changed is True
        assert image_model.data[4, 3] == 5
        assert image_model.modified

    def test_pencil_tool_move(self, image_model):
        """Test pencil tool on move (continuous drawing with line interpolation)"""
        tool = PencilTool()

        # Start drawing at position (0, 2)
        tool.on_press(0, 2, 7, image_model)

        # Draw line by moving to position (3, 2) - should interpolate between
        line_points = tool.on_move(3, 2, 7, image_model)
        
        # Apply the line points to the image model
        for x, y in line_points:
            image_model.set_pixel(x, y, 7)

        # Check line drawn (all points from 0 to 3 should be filled)
        for x in range(4):
            assert image_model.data[2, x] == 7

    def test_pencil_tool_release(self, image_model):
        """Test pencil tool on release (no-op)"""
        tool = PencilTool()
        result = tool.on_release(0, 0, 0, image_model)
        assert result is None

    def test_fill_tool_press(self, image_model):
        """Test fill tool on press"""
        tool = FillTool()

        # Fill from corner
        changed_pixels = tool.on_press(0, 0, 9, image_model)

        # Should fill entire image (all pixels were 0)
        assert len(changed_pixels) == 64
        assert np.all(image_model.data == 9)

    def test_fill_tool_bounded(self, image_model):
        """Test fill tool respects boundaries"""
        tool = FillTool()

        # Create boundary
        image_model.data[2, :] = 1  # Horizontal line

        # Fill above line
        tool.on_press(0, 0, 5, image_model)

        # Check only top part filled
        assert np.all(image_model.data[:2, :] == 5)
        assert np.all(image_model.data[2, :] == 1)  # Boundary unchanged
        assert np.all(image_model.data[3:, :] == 0)  # Below unchanged

    def test_fill_tool_no_change(self, image_model):
        """Test fill tool when target same as replacement"""
        tool = FillTool()

        # Fill with same color
        changed = tool.on_press(0, 0, 0, image_model)

        assert len(changed) == 0
        assert not image_model.modified

    def test_color_picker_tool(self, image_model):
        """Test color picker tool"""
        tool = ColorPickerTool()

        # Set test color
        image_model.data[3, 2] = 12

        # Mock callback
        picked_colors = []
        tool.picked_callback = lambda c: picked_colors.append(c)

        # Pick color
        color = tool.on_press(2, 3, 0, image_model)

        assert color == 12
        assert picked_colors == [12]

    def test_color_picker_no_callback(self, image_model):
        """Test color picker without callback"""
        tool = ColorPickerTool()
        image_model.data[0, 0] = 8

        # Should work without callback
        color = tool.on_press(0, 0, 0, image_model)
        assert color == 8


class TestToolManager:
    """Test the tool manager"""

    @pytest.fixture
    def tool_manager(self):
        """Create tool manager instance"""
        return ToolManager()

    def test_initial_state(self, tool_manager):
        """Test initial tool manager state"""
        assert tool_manager.current_tool == ToolType.PENCIL
        assert tool_manager.current_color == 0
        assert len(tool_manager.tools) == 3

    def test_set_tool_enum(self, tool_manager):
        """Test setting tool with enum"""
        tool_manager.set_tool(ToolType.FILL)
        assert tool_manager.current_tool == ToolType.FILL

    def test_set_tool_string(self, tool_manager):
        """Test setting tool with string"""
        tool_manager.set_tool("fill")
        assert tool_manager.current_tool == ToolType.FILL

        tool_manager.set_tool("PICKER")  # Case insensitive
        assert tool_manager.current_tool == ToolType.PICKER

    def test_set_tool_invalid(self, tool_manager):
        """Test setting invalid tool"""
        original_tool = tool_manager.current_tool
        tool_manager.set_tool("invalid_tool")
        assert tool_manager.current_tool == original_tool  # Unchanged

    def test_current_tool_name(self, tool_manager):
        """Test getting current tool name"""
        tool_manager.set_tool(ToolType.FILL)
        assert tool_manager.current_tool_name == "fill"

        tool_manager.set_tool(ToolType.PICKER)
        assert tool_manager.current_tool_name == "picker"

    def test_get_tool_current(self, tool_manager):
        """Test getting current tool"""
        tool = tool_manager.get_tool()
        assert isinstance(tool, PencilTool)

        tool_manager.set_tool(ToolType.FILL)
        tool = tool_manager.get_tool()
        assert isinstance(tool, FillTool)

    def test_get_tool_specific(self, tool_manager):
        """Test getting specific tool"""
        # By enum
        tool = tool_manager.get_tool(ToolType.FILL)
        assert isinstance(tool, FillTool)

        # By string
        tool = tool_manager.get_tool("picker")
        assert isinstance(tool, ColorPickerTool)

    def test_get_tool_invalid(self, tool_manager):
        """Test getting invalid tool"""
        with pytest.raises(ValueError):
            tool_manager.get_tool("invalid_tool")

    def test_set_color(self, tool_manager):
        """Test setting drawing color"""
        tool_manager.set_color(7)
        assert tool_manager.current_color == 7

        # Test clamping
        tool_manager.set_color(20)
        assert tool_manager.current_color == 15

        tool_manager.set_color(-5)
        assert tool_manager.current_color == 0

    def test_set_color_picker_callback(self, tool_manager):
        """Test setting color picker callback"""
        callback = MagicMock()
        tool_manager.set_color_picked_callback(callback)

        # Get picker tool and check callback set
        picker = tool_manager.tools[ToolType.PICKER]
        assert picker.picked_callback == callback


class TestFileManager:
    """Test the file manager"""

    @pytest.fixture
    def file_manager(self):
        """Create file manager instance"""
        return FileManager()

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    def test_new_file(self, file_manager):
        """Test creating new file"""
        image_model = file_manager.new_file(16, 24)

        assert isinstance(image_model, ImageModel)
        assert image_model.width == 16
        assert image_model.height == 24
        assert image_model.data.shape == (24, 16)
        assert file_manager.project_model.image_path is None

    def test_load_file_not_found(self, file_manager):
        """Test loading non-existent file"""
        error_called = False

        def error_callback(msg):
            nonlocal error_called
            error_called = True
            assert "File not found" in msg

        file_manager.error_callback = error_callback
        worker = file_manager.load_file("/does/not/exist.png")

        assert worker is None
        assert error_called

    def test_load_file_success(self, file_manager, temp_dir):
        """Test loading existing file"""
        # Create test file
        test_path = os.path.join(temp_dir, "test.png")
        with open(test_path, "wb") as f:
            f.write(b"dummy")

        worker = file_manager.load_file(test_path)

        assert isinstance(worker, FileLoadWorker)
        assert str(worker.file_path) == test_path
        assert file_manager.project_model.image_path == test_path

    def test_save_file(self, file_manager, temp_dir):
        """Test saving file"""
        # Create test data
        image_model = ImageModel(width=4, height=4)
        image_model.data[0, 0] = 5
        palette_model = PaletteModel()

        save_path = os.path.join(temp_dir, "output.png")

        worker = file_manager.save_file(image_model, palette_model, save_path)

        assert isinstance(worker, FileSaveWorker)
        assert file_manager.project_model.image_path == save_path
        assert image_model.file_path == save_path
        assert not image_model.modified

    def test_get_metadata_path(self, file_manager):
        """Test getting metadata path"""
        image_path = "/path/to/image.png"
        metadata_path = file_manager.get_metadata_path(image_path)

        assert metadata_path == "/path/to/image.metadata.json"


class TestPaletteManager:
    """Test the palette manager"""

    @pytest.fixture
    def palette_manager(self):
        """Create palette manager instance"""
        return PaletteManager()

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory"""
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    def test_initial_state(self, palette_manager):
        """Test initial palette manager state"""
        assert palette_manager.current_palette_index == 8
        assert len(palette_manager.palettes) == 0

    def test_add_palette(self, palette_manager):
        """Test adding palette"""
        palette = PaletteModel(name="Test Palette")
        palette_manager.add_palette(10, palette)

        assert 10 in palette_manager.palettes
        assert palette_manager.palettes[10] == palette
        assert palette.index == 10

    def test_get_palette(self, palette_manager):
        """Test getting palette by index"""
        palette = PaletteModel(name="Test")
        palette_manager.add_palette(8, palette)

        retrieved = palette_manager.get_palette(8)
        assert retrieved == palette

        # Non-existent palette
        assert palette_manager.get_palette(99) is None

    def test_get_current_palette(self, palette_manager):
        """Test getting current palette"""
        # No palette at current index
        assert palette_manager.get_current_palette() is None

        # Add palette at current index
        palette = PaletteModel()
        palette_manager.add_palette(8, palette)

        assert palette_manager.get_current_palette() == palette

    def test_set_current_palette(self, palette_manager):
        """Test setting current palette"""
        # Add palettes
        pal1 = PaletteModel(name="Palette 1")
        pal2 = PaletteModel(name="Palette 2")
        palette_manager.add_palette(8, pal1)
        palette_manager.add_palette(12, pal2)

        # Switch to existing palette
        result = palette_manager.set_current_palette(12)
        assert result is True
        assert palette_manager.current_palette_index == 12
        assert palette_manager.get_current_palette() == pal2

        # Try to switch to non-existent palette
        result = palette_manager.set_current_palette(99)
        assert result is False
        assert palette_manager.current_palette_index == 12  # Unchanged

    def test_load_palette_file_not_found(self, palette_manager):
        """Test loading non-existent palette file"""
        error_called = False

        def error_callback(msg):
            nonlocal error_called
            error_called = True
            assert "File not found during load palette" in msg

        palette_manager.error_callback = error_callback
        worker = palette_manager.load_palette_file("/does/not/exist.pal")

        assert worker is None
        assert error_called

    def test_load_palette_file_success(self, palette_manager, temp_dir):
        """Test loading palette file"""
        # Create test file
        test_path = os.path.join(temp_dir, "test.pal")
        with open(test_path, "wb") as f:
            f.write(b"dummy")

        worker = palette_manager.load_palette_file(test_path)

        assert isinstance(worker, PaletteLoadWorker)
        assert str(worker.file_path) == test_path

    def test_load_from_metadata_multiple(self, palette_manager):
        """Test loading multiple palettes from metadata"""
        metadata = {
            "palettes": {
                "8": {
                    "name": "Sprite Palette",
                    "colors": [[255, 0, 0]] + [[0, 0, 0]] * 15,
                },
                "12": {
                    "name": "Background Palette",
                    "colors": [[0, 255, 0]] + [[0, 0, 0]] * 15,
                },
            }
        }

        result = palette_manager.load_from_metadata(metadata)

        assert result is True
        assert palette_manager.get_palette_count() == 2

        pal8 = palette_manager.get_palette(8)
        assert pal8.name == "Sprite Palette"
        assert pal8.colors[0] == (255, 0, 0)

        pal12 = palette_manager.get_palette(12)
        assert pal12.name == "Background Palette"
        assert pal12.colors[0] == (0, 255, 0)

    def test_load_from_metadata_single(self, palette_manager):
        """Test loading single palette from metadata"""
        metadata = {"palette": [255, 128, 64] + [0] * 765}  # Flat palette data

        result = palette_manager.load_from_metadata(metadata)

        assert result is True
        assert palette_manager.get_palette_count() == 1

        palette = palette_manager.get_current_palette()
        assert palette.name == "Loaded Palette"
        assert palette.colors[0] == (255, 128, 64)

    def test_load_from_metadata_invalid(self, palette_manager):
        """Test loading from invalid metadata"""
        metadata = {"no_palette_data": True}

        result = palette_manager.load_from_metadata(metadata)

        assert result is False
        assert palette_manager.get_palette_count() == 0

    def test_clear_palettes(self, palette_manager):
        """Test clearing all palettes"""
        # Add some palettes
        palette_manager.add_palette(8, PaletteModel())
        palette_manager.add_palette(12, PaletteModel())

        palette_manager.clear_palettes()

        # Should have default palette only
        assert palette_manager.get_palette_count() == 1
        assert palette_manager.get_palette(8) is not None


class TestManagerIntegration:
    """Integration tests for managers working together"""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory"""
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    def test_file_and_palette_integration(self):
        """Test file manager and palette manager working together"""
        file_manager = FileManager()
        palette_manager = PaletteManager()

        # Create new file
        image_model = file_manager.new_file(8, 8)

        # Add palette
        palette = PaletteModel(name="Custom Palette")
        palette.colors[0] = (255, 0, 0)
        palette_manager.add_palette(8, palette)

        # Save file would use both managers
        assert image_model is not None
        assert palette_manager.get_current_palette() == palette

    def test_tool_and_image_integration(self):
        """Test tool manager working with image model"""
        tool_manager = ToolManager()
        image_model = ImageModel(width=8, height=8)

        # Set tool and color
        tool_manager.set_tool("pencil")
        tool_manager.set_color(5)

        # Use tool
        tool = tool_manager.get_tool()
        changed = tool.on_press(3, 3, tool_manager.current_color, image_model)

        assert changed is True
        assert image_model.data[3, 3] == 5

    def test_complete_workflow(self, temp_dir):
        """Test complete workflow with all managers"""
        # Setup managers
        file_manager = FileManager()
        palette_manager = PaletteManager()
        tool_manager = ToolManager()

        # Create new image
        image_model = file_manager.new_file(4, 4)

        # Create custom palette
        palette = PaletteModel(name="Test Palette")
        palette.colors[0] = (255, 255, 255)  # White
        palette.colors[1] = (255, 0, 0)  # Red
        palette.colors[2] = (0, 255, 0)  # Green
        palette_manager.add_palette(8, palette)

        # Draw with tools
        tool_manager.set_tool("pencil")
        tool_manager.set_color(1)
        pencil = tool_manager.get_tool()
        pencil.on_press(0, 0, 1, image_model)
        pencil.on_press(1, 1, 1, image_model)

        tool_manager.set_tool("fill")
        tool_manager.set_color(2)
        fill = tool_manager.get_tool()
        fill.on_press(3, 3, 2, image_model)

        # Verify drawing
        assert image_model.data[0, 0] == 1  # Red pixel
        assert image_model.data[1, 1] == 1  # Red pixel
        assert image_model.data[3, 3] == 2  # Green from fill

        # Would save with file_manager.save_file()
        assert image_model.modified is True
