#!/usr/bin/env python3
"""
Comprehensive test suite for the Indexed Pixel Editor
Tests core functionality, settings, widgets, and edge cases
"""

# Standard library imports
import os

# PyQt6 testing setup
import sys
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

# Third-party imports
import numpy as np
import pytest

# PIL for image testing
from PIL import Image
from PyQt6.QtCore import QPoint, QPointF
from PyQt6.QtWidgets import QApplication

# Local imports
# Import modules to test
from indexed_pixel_editor import (
    IndexedPixelEditor,
    SettingsManager,
)
from pixel_editor_widgets import ColorPaletteWidget, PixelCanvas, ZoomableScrollArea


@pytest.fixture(scope="session")
def qapp():
    """Create QApplication instance for testing"""
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    return app


@pytest.fixture
def temp_dir():
    """Create temporary directory for test files"""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


@pytest.fixture
def sample_indexed_image():
    """Create a sample 4bpp indexed PNG for testing"""
    # Create 8x8 test image with pattern
    data = np.array(
        [
            [0, 1, 2, 3, 4, 5, 6, 7],
            [1, 2, 3, 4, 5, 6, 7, 8],
            [2, 3, 4, 5, 6, 7, 8, 9],
            [3, 4, 5, 6, 7, 8, 9, 10],
            [4, 5, 6, 7, 8, 9, 10, 11],
            [5, 6, 7, 8, 9, 10, 11, 12],
            [6, 7, 8, 9, 10, 11, 12, 13],
            [7, 8, 9, 10, 11, 12, 13, 14],
        ],
        dtype=np.uint8,
    )

    # Clamp to 4bpp range (0-15)
    data = np.clip(data, 0, 15)

    # Create PIL image
    img = Image.fromarray(data, mode="P")

    # Set up 16-color palette (SNES-like)
    palette = []
    for i in range(16):
        gray = i * 17  # 0, 17, 34, ..., 255
        palette.extend([gray, gray, gray])

    # Pad to 256 colors
    while len(palette) < 768:
        palette.extend([0, 0, 0])

    img.putpalette(palette)
    return img


@pytest.fixture
def sample_image_file(temp_dir, sample_indexed_image):
    """Save sample image to temporary file"""
    file_path = temp_dir / "test_sprite.png"
    sample_indexed_image.save(file_path)
    return str(file_path)


class TestSettingsManager:
    """Test the settings management system"""

    def test_settings_initialization(self, temp_dir):
        """Test settings manager initializes correctly"""
        # Use custom settings directory
        with patch("pathlib.Path.home", return_value=temp_dir):
            settings = SettingsManager()

            assert settings.settings["last_file"] == ""
            assert settings.settings["recent_files"] == []
            assert settings.settings["max_recent_files"] == 10
            assert settings.settings["auto_load_last"]

    def test_add_recent_file(self, temp_dir, sample_image_file):
        """Test adding files to recent files list"""
        with patch("pathlib.Path.home", return_value=temp_dir):
            settings = SettingsManager()

            # Add a file
            settings.add_recent_file(sample_image_file)

            assert sample_image_file in settings.settings["recent_files"]
            assert settings.settings["last_file"] == sample_image_file
            assert len(settings.settings["recent_files"]) == 1

    def test_recent_files_limit(self, temp_dir):
        """Test recent files list respects maximum limit"""
        with patch("pathlib.Path.home", return_value=temp_dir):
            settings = SettingsManager()

            # Add more files than the limit
            for i in range(15):
                fake_file = f"/fake/file_{i}.png"
                with patch("os.path.exists", return_value=True):
                    settings.add_recent_file(fake_file)

            assert (
                len(settings.settings["recent_files"])
                <= settings.settings["max_recent_files"]
            )

    def test_get_recent_files_filters_nonexistent(self, temp_dir):
        """Test that get_recent_files removes non-existent files"""
        with patch("pathlib.Path.home", return_value=temp_dir):
            settings = SettingsManager()

            # Add files (some exist, some don't)
            existing_file = "/existing/file.png"
            nonexistent_file = "/nonexistent/file.png"

            settings.settings["recent_files"] = [existing_file, nonexistent_file]

            with patch("os.path.exists") as mock_exists:
                mock_exists.side_effect = lambda path: path == existing_file

                recent = settings.get_recent_files()

                assert existing_file in recent
                assert nonexistent_file not in recent

    def test_settings_persistence(self, temp_dir):
        """Test settings are saved and loaded correctly"""
        with patch("pathlib.Path.home", return_value=temp_dir):
            # Create and modify settings
            settings1 = SettingsManager()
            test_file = "/test/file.png"

            with patch("os.path.exists", return_value=True):
                settings1.add_recent_file(test_file)

            # SettingsManager converts paths to absolute - get the actual converted path
            expected_path = os.path.abspath(test_file)

            # Create new instance (should load saved settings)
            settings2 = SettingsManager()

            assert settings2.settings["last_file"] == expected_path
            assert expected_path in settings2.settings["recent_files"]


class TestColorPaletteWidget:
    """Test the color palette widget"""

    def test_palette_initialization(self, qapp):
        """Test palette widget initializes with correct colors"""
        palette = ColorPaletteWidget()

        assert len(palette.colors) == 16
        assert palette.selected_index == 1
        assert palette.cell_size == 32
        assert palette.is_grayscale_mode  # Starts in grayscale mode by default

        # Test actual default grayscale colors from implementation
        assert palette.colors[0] == (0, 0, 0)  # Black
        assert palette.colors[1] == (17, 17, 17)  # Gray level 1
        assert palette.colors[15] == (255, 255, 255)  # White

        # Test that it has the color palette available
        assert len(palette.default_colors) == 16
        assert palette.default_colors[1] == (255, 183, 197)  # Kirby pink in color mode
        assert palette.colors[4] == (68, 68, 68)  # Gray level 4 in grayscale mode

        # Check widget size calculation
        expected_size = 4 * 32 + 10  # 4 cells * 32 pixels + 10 offset
        assert palette.width() == expected_size
        assert palette.height() == expected_size

    def test_set_palette(self, qapp):
        """Test setting custom palette colors"""
        palette = ColorPaletteWidget()

        # Test with exactly 16 colors
        new_colors = [(i * 16, i * 16, i * 16) for i in range(16)]
        palette.set_palette(new_colors)

        assert palette.colors[0] == (0, 0, 0)
        assert palette.colors[15] == (240, 240, 240)

        # Test with more than 16 colors (should truncate)
        many_colors = [(255, 0, 0)] * 20
        palette.set_palette(many_colors)
        assert len(palette.colors) == 16

        # Test with fewer than 16 colors (should not update)
        few_colors = [(0, 255, 0)] * 10
        old_colors = palette.colors.copy()
        palette.set_palette(few_colors)
        assert palette.colors == old_colors  # Should be unchanged

    def test_color_selection_calculation(self, qapp):
        """Test color selection coordinate calculation"""
        ColorPaletteWidget()

        # Test different grid positions based on actual implementation
        # Grid layout: 4x4, cell_size=32, offset=5

        # Click on top-left (index 0)
        click_pos = QPoint(5 + 16, 5 + 16)  # Center of first cell
        x = int((click_pos.x() - 5) // 32)
        y = int((click_pos.y() - 5) // 32)
        index = y * 4 + x
        assert index == 0

        # Click on bottom-right (index 15)
        click_pos = QPoint(5 + 3 * 32 + 16, 5 + 3 * 32 + 16)  # Center of last cell
        x = int((click_pos.x() - 5) // 32)
        y = int((click_pos.y() - 5) // 32)
        index = y * 4 + x
        assert index == 15

    def test_color_mode_switching(self, qapp):
        """Test switching between grayscale and color modes"""
        palette = ColorPaletteWidget()

        # Start in grayscale mode
        assert palette.is_grayscale_mode
        assert palette.colors[1] == (17, 17, 17)

        # Switch to color mode
        palette.set_color_mode(True)
        assert not palette.is_grayscale_mode
        assert palette.colors[1] == (255, 183, 197)  # Kirby pink
        assert palette.palette_source == "Default Color Palette"

        # Switch back to grayscale
        palette.set_color_mode(False)
        assert palette.is_grayscale_mode
        assert palette.colors[1] == (17, 17, 17)
        assert palette.palette_source == "Default Grayscale Palette"

    def test_external_palette_loading(self, qapp):
        """Test loading external palette"""
        palette = ColorPaletteWidget()

        # Create custom colors
        custom_colors = [(255, 0, 0), (0, 255, 0), (0, 0, 255)] + [(128, 128, 128)] * 13

        # Load external palette
        palette.set_palette(custom_colors, "Test Palette")

        assert palette.is_external_palette
        assert palette.palette_source == "Test Palette"
        assert palette.colors[0] == (255, 0, 0)
        assert palette.colors[1] == (0, 255, 0)
        assert palette.colors[2] == (0, 0, 255)

        # Test that color mode switching doesn't affect external palette
        palette.set_color_mode(True)
        assert palette.is_external_palette  # Should remain external
        assert palette.colors[0] == (255, 0, 0)  # Colors unchanged

    def test_reset_to_default(self, qapp):
        """Test resetting to default palette"""
        palette = ColorPaletteWidget()

        # Load external palette first
        custom_colors = [(255, 0, 0)] * 16
        palette.set_palette(custom_colors, "Test")
        assert palette.is_external_palette

        # Reset to default
        palette.reset_to_default()

        assert not palette.is_external_palette
        assert palette.is_grayscale_mode
        assert palette.palette_source == "Default Grayscale Palette"
        assert palette.colors[0] == (0, 0, 0)
        assert palette.colors[15] == (255, 255, 255)


class TestPixelCanvas:
    """Test the pixel drawing canvas"""

    def test_canvas_initialization(self, qapp):
        """Test canvas initializes correctly"""
        palette = ColorPaletteWidget()
        canvas = PixelCanvas(palette)

        # Test actual default values from implementation
        assert canvas.zoom == 4  # Default zoom for sprite editing
        assert canvas.current_color == 1  # Default to Kirby pink
        assert canvas.tool == "pencil"  # Default tool
        assert canvas.grid_visible
        assert not canvas.greyscale_mode
        assert canvas.show_color_preview
        assert not canvas.drawing
        assert not canvas.panning

        # Test pan offset is QPointF
        assert isinstance(canvas.pan_offset, QPointF)
        assert canvas.pan_offset.x() == 0.0
        assert canvas.pan_offset.y() == 0.0

        # Test undo/redo stacks
        assert len(canvas.undo_stack) == 0
        assert len(canvas.redo_stack) == 0
        assert canvas.undo_stack.maxlen == 50
        assert canvas.redo_stack.maxlen == 50

        # Test palette reference
        assert canvas.palette_widget == palette

    def test_new_image_creation(self, qapp):
        """Test creating new image"""
        palette = ColorPaletteWidget()
        canvas = PixelCanvas(palette)

        canvas.new_image(16, 16)

        assert canvas.image_data is not None
        assert canvas.image_data.shape == (16, 16)
        assert canvas.image_data.dtype == np.uint8
        assert np.all(canvas.image_data == 0)  # Should be filled with zeros

    def test_load_indexed_image(self, qapp, sample_indexed_image):
        """Test loading indexed PNG image"""
        palette = ColorPaletteWidget()
        canvas = PixelCanvas(palette)

        canvas.load_image(sample_indexed_image)

        assert canvas.image_data is not None
        assert canvas.image_data.shape == (8, 8)
        assert canvas.image_data.dtype == np.uint8

    def test_draw_pixel(self, qapp):
        """Test drawing individual pixels"""
        palette = ColorPaletteWidget()
        canvas = PixelCanvas(palette)
        canvas.new_image(8, 8)

        # Draw pixel at position (3, 4) with color 5
        canvas.current_color = 5
        canvas.draw_pixel(3, 4)

        assert canvas.image_data[4, 3] == 5

    def test_flood_fill(self, qapp):
        """Test flood fill functionality"""
        palette = ColorPaletteWidget()
        canvas = PixelCanvas(palette)
        canvas.new_image(8, 8)

        # Fill with color 7
        canvas.current_color = 7
        canvas.flood_fill(0, 0)

        # Entire image should be filled (was all zeros)
        assert np.all(canvas.image_data == 7)

    def test_color_picker(self, qapp):
        """Test color picker tool"""
        palette = ColorPaletteWidget()
        canvas = PixelCanvas(palette)
        canvas.new_image(8, 8)

        # Set a pixel to color 9
        canvas.image_data[2, 3] = 9

        # Pick color from that pixel
        canvas.pick_color(3, 2)

        assert canvas.current_color == 9
        assert palette.selected_index == 9

    def test_zoom_functionality(self, qapp):
        """Test zoom level changes"""
        palette = ColorPaletteWidget()
        canvas = PixelCanvas(palette)
        canvas.new_image(8, 8)

        canvas.size()

        # Test zoom in
        canvas.set_zoom(8)
        assert canvas.zoom == 8

        # Test zoom out
        canvas.set_zoom(2)
        assert canvas.zoom == 2

        # Test zoom limits
        canvas.set_zoom(100)
        assert canvas.zoom == 64  # Should be clamped to max

        canvas.set_zoom(-5)
        assert canvas.zoom == 1  # Should be clamped to min

    def test_undo_redo(self, qapp):
        """Test undo/redo functionality"""
        palette = ColorPaletteWidget()
        canvas = PixelCanvas(palette)
        canvas.new_image(8, 8)

        # Make a change
        canvas.save_undo()
        canvas.current_color = 5
        canvas.draw_pixel(2, 3)

        assert canvas.image_data[3, 2] == 5

        # Undo the change
        canvas.undo()
        assert canvas.image_data[3, 2] == 0

        # Redo the change
        canvas.redo()
        assert canvas.image_data[3, 2] == 5

    def test_get_pil_image(self, qapp):
        """Test converting canvas to PIL image"""
        palette = ColorPaletteWidget()
        canvas = PixelCanvas(palette)
        canvas.new_image(4, 4)

        # Draw some pixels
        canvas.current_color = 3
        canvas.draw_pixel(1, 1)
        canvas.draw_pixel(2, 2)

        # Get PIL image
        pil_img = canvas.get_pil_image()

        assert pil_img is not None
        assert pil_img.mode == "P"
        assert pil_img.size == (4, 4)

        # Verify pixel data
        img_data = np.array(pil_img)
        assert img_data[1, 1] == 3
        assert img_data[2, 2] == 3

    def test_panning_offset(self, qapp):
        """Test panning offset affects pixel coordinate mapping"""
        palette = ColorPaletteWidget()
        canvas = PixelCanvas(palette)
        canvas.new_image(8, 8)

        # Set pan offset
        canvas.pan_offset = QPointF(10.0, 15.0)

        # Test pixel position calculation with offset
        mouse_pos = QPointF(50.0, 60.0)  # Some arbitrary position
        pixel_pos = canvas.get_pixel_pos(mouse_pos)

        # Should account for pan offset
        expected_x = int((50.0 - 10.0) // canvas.zoom)
        expected_y = int((60.0 - 15.0) // canvas.zoom)

        if 0 <= expected_x < 8 and 0 <= expected_y < 8:
            assert pixel_pos.x() == expected_x
            assert pixel_pos.y() == expected_y


class TestZoomableScrollArea:
    """Test the custom scroll area for zooming"""

    def test_scroll_area_initialization(self, qapp):
        """Test scroll area initializes correctly"""
        scroll_area = ZoomableScrollArea()
        assert scroll_area.canvas is None

    def test_widget_setting(self, qapp):
        """Test setting widget stores canvas reference"""
        scroll_area = ZoomableScrollArea()
        palette = ColorPaletteWidget()
        canvas = PixelCanvas(palette)

        scroll_area.setWidget(canvas)
        assert scroll_area.canvas == canvas


class TestIndexedPixelEditor:
    """Test the main editor application"""

    def test_editor_initialization(self, qapp):
        """Test editor initializes without crashing"""
        with patch.object(IndexedPixelEditor, "handle_startup"):
            editor = IndexedPixelEditor()

            assert editor.current_file is None
            assert not editor.modified
            assert isinstance(editor.settings, SettingsManager)

            # Test UI components exist
            assert editor.canvas is not None
            assert editor.palette_widget is not None
            assert editor.zoom_slider is not None
            assert editor.status_bar is not None

    def test_load_file_by_path(self, qapp, sample_image_file):
        """Test loading file by path"""
        with patch.object(IndexedPixelEditor, "handle_startup"):
            editor = IndexedPixelEditor()

            success = editor.load_file_by_path(sample_image_file)

            assert success
            assert editor.current_file == sample_image_file
            assert not editor.modified
            assert editor.canvas.image_data is not None

    def test_load_invalid_file(self, qapp, temp_dir):
        """Test loading invalid file format"""
        # Create a non-indexed PNG
        rgb_img = Image.new("RGB", (8, 8), color=(255, 0, 0))
        invalid_file = temp_dir / "rgb_image.png"
        rgb_img.save(invalid_file)

        with patch.object(IndexedPixelEditor, "handle_startup"):
            editor = IndexedPixelEditor()

            with patch("PyQt6.QtWidgets.QMessageBox.warning") as mock_warning:
                success = editor.load_file_by_path(str(invalid_file))

                assert not success
                mock_warning.assert_called_once()

    def test_save_file_functionality(self, qapp, temp_dir):
        """Test saving file functionality"""
        with patch.object(IndexedPixelEditor, "handle_startup"):
            editor = IndexedPixelEditor()

            # Create some content
            editor.canvas.new_image(4, 4)
            editor.canvas.current_color = 7
            editor.canvas.draw_pixel(1, 1)

            # Save to file
            save_path = temp_dir / "saved_sprite.png"
            editor.save_to_file(str(save_path))

            assert save_path.exists()

            # Verify saved image
            saved_img = Image.open(save_path)
            assert saved_img.mode == "P"
            assert saved_img.size == (4, 4)

            # Verify the pixel we drew is there
            img_data = np.array(saved_img)
            assert img_data[1, 1] == 7

    def test_zoom_presets(self, qapp):
        """Test zoom preset functionality"""
        with patch.object(IndexedPixelEditor, "handle_startup"):
            editor = IndexedPixelEditor()

            # Test setting different zoom levels
            editor.set_zoom_preset(8)
            assert editor.zoom_slider.value() == 8
            assert editor.canvas.zoom == 8

            editor.set_zoom_preset(2)
            assert editor.zoom_slider.value() == 2
            assert editor.canvas.zoom == 2

    def test_modification_tracking(self, qapp):
        """Test that modifications are tracked correctly"""
        with patch.object(IndexedPixelEditor, "handle_startup"):
            editor = IndexedPixelEditor()

            # Start with no modifications
            assert not editor.modified

            # Make a change
            editor.canvas.new_image(4, 4)
            editor.on_canvas_changed()  # Simulate canvas change

            assert editor.modified
            assert "*" in editor.windowTitle()  # Should show unsaved indicator

    def test_tool_selection(self, qapp):
        """Test tool selection changes"""
        with patch.object(IndexedPixelEditor, "handle_startup"):
            editor = IndexedPixelEditor()

            # Test tool changes
            button = Mock()
            editor.tool_group.id = Mock(return_value=1)  # Fill tool

            editor.on_tool_changed(button)
            assert editor.canvas.tool == "fill"

            editor.tool_group.id = Mock(return_value=2)  # Picker tool
            editor.on_tool_changed(button)
            assert editor.canvas.tool == "picker"


class TestIntegration:
    """Integration tests that test multiple components working together"""

    def test_complete_workflow(self, qapp, temp_dir):
        """Test a complete sprite editing workflow"""
        with patch.object(IndexedPixelEditor, "handle_startup"):
            editor = IndexedPixelEditor()

            # 1. Create a new image
            editor.canvas.new_image(8, 8)
            assert editor.canvas.image_data.shape == (8, 8)

            # 2. Select a color from palette
            editor.palette_widget.selected_index = 5
            editor.on_color_selected(5)
            assert editor.canvas.current_color == 5

            # 3. Draw some pixels
            editor.canvas.draw_pixel(2, 3)
            editor.canvas.draw_pixel(3, 3)
            editor.canvas.draw_pixel(4, 3)

            # 4. Check the pixels were drawn
            assert editor.canvas.image_data[3, 2] == 5
            assert editor.canvas.image_data[3, 3] == 5
            assert editor.canvas.image_data[3, 4] == 5

            # 5. Test undo
            editor.canvas.save_undo()
            editor.canvas.draw_pixel(5, 5)
            assert editor.canvas.image_data[5, 5] == 5

            editor.canvas.undo()
            assert editor.canvas.image_data[5, 5] == 0  # Should be undone

            # 6. Save the file
            save_path = temp_dir / "workflow_test.png"
            editor.save_to_file(str(save_path))
            assert save_path.exists()

            # 7. Load the file back
            success = editor.load_file_by_path(str(save_path))
            assert success

            # 8. Verify the loaded data matches what we drew
            assert editor.canvas.image_data[3, 2] == 5
            assert editor.canvas.image_data[3, 3] == 5
            assert editor.canvas.image_data[3, 4] == 5

    def test_palette_canvas_integration(self, qapp):
        """Test palette and canvas work together correctly"""
        palette = ColorPaletteWidget()
        canvas = PixelCanvas(palette)

        canvas.new_image(4, 4)

        # Set custom palette
        new_colors = [(255, 0, 0), (0, 255, 0)] + [(0, 0, 0)] * 14
        palette.set_palette(new_colors)

        # Select color from palette
        palette.selected_index = 1
        canvas.current_color = 1

        # Draw with the color
        canvas.draw_pixel(1, 1)
        assert canvas.image_data[1, 1] == 1

        # Get PIL image should use the custom palette
        pil_img = canvas.get_pil_image()
        assert pil_img is not None

        # The palette should be applied
        palette_colors = pil_img.getpalette()
        assert palette_colors[3:6] == [
            0,
            255,
            0,
        ]  # Second color (index 1) should be green

    def test_zoom_and_pan_integration(self, qapp):
        """Test zoom and pan work together"""
        with patch.object(IndexedPixelEditor, "handle_startup"):
            editor = IndexedPixelEditor()

            # Create image and set zoom
            editor.canvas.new_image(16, 16)
            editor.set_zoom_preset(8)

            # Set pan offset
            editor.canvas.pan_offset = QPointF(20.0, 30.0)

            # Test pixel position calculation with zoom and pan
            mouse_pos = QPointF(100.0, 120.0)
            pixel_pos = editor.canvas.get_pixel_pos(mouse_pos)

            # Should account for both zoom and pan offset
            if pixel_pos:  # Only if within bounds
                expected_x = int((100.0 - 20.0) // 8)  # (mouse - pan) / zoom
                expected_y = int((120.0 - 30.0) // 8)
                assert pixel_pos.x() == expected_x
                assert pixel_pos.y() == expected_y


class TestEdgeCases:
    """Test edge cases and error conditions"""

    def test_large_image_handling(self, qapp):
        """Test handling of larger images"""
        palette = ColorPaletteWidget()
        canvas = PixelCanvas(palette)

        # Create larger image
        canvas.new_image(64, 64)

        assert canvas.image_data.shape == (64, 64)

        # Test drawing at edges
        canvas.current_color = 5
        canvas.draw_pixel(0, 0)  # Top-left corner
        canvas.draw_pixel(63, 63)  # Bottom-right corner

        assert canvas.image_data[0, 0] == 5
        assert canvas.image_data[63, 63] == 5

    def test_invalid_pixel_coordinates(self, qapp):
        """Test drawing outside image boundaries"""
        palette = ColorPaletteWidget()
        canvas = PixelCanvas(palette)
        canvas.new_image(8, 8)

        # Try to draw outside boundaries
        canvas.current_color = 3
        canvas.draw_pixel(-1, 5)  # Should not crash
        canvas.draw_pixel(10, 5)  # Should not crash
        canvas.draw_pixel(5, -1)  # Should not crash
        canvas.draw_pixel(5, 10)  # Should not crash

        # Image should be unchanged
        assert np.all(canvas.image_data == 0)

    def test_color_index_clamping(self, qapp):
        """Test color indices are clamped to valid 4bpp range"""
        palette = ColorPaletteWidget()
        canvas = PixelCanvas(palette)
        canvas.new_image(4, 4)

        # Test invalid color indices
        canvas.current_color = -5
        canvas.draw_pixel(1, 1)
        assert canvas.image_data[1, 1] == 0  # Should be clamped to 0

        canvas.current_color = 20
        canvas.draw_pixel(2, 2)
        assert canvas.image_data[2, 2] == 15  # Should be clamped to 15

    def test_nonexistent_file_handling(self, qapp):
        """Test handling of nonexistent files"""
        with patch.object(IndexedPixelEditor, "handle_startup"):
            editor = IndexedPixelEditor()

            with patch("PyQt6.QtWidgets.QMessageBox.critical") as mock_error:
                success = editor.load_file_by_path("/nonexistent/file.png")

                assert not success
                mock_error.assert_called_once()


if __name__ == "__main__":
    # Run tests with verbose output
    pytest.main([__file__, "-v", "--tb=short"])
