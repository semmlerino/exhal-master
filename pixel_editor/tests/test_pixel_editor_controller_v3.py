#!/usr/bin/env python3
"""
Unit tests for PixelEditorController V3
Tests core functionality without heavy mocking, focusing on business logic
"""

import json
import os
import tempfile
from unittest.mock import MagicMock, patch

import numpy as np
import pytest
from PIL import Image

from pixel_editor.core.pixel_editor_controller_v3 import PixelEditorController
from pixel_editor.core.pixel_editor_models import PaletteModel


class TestPixelEditorController:
    """Test the main controller class"""

    @pytest.fixture
    def controller(self):
        """Create a controller instance for testing"""
        controller = PixelEditorController()
        # Connect basic signal handlers for testing
        controller.error_handler = MagicMock()
        controller.error.connect(controller.error_handler)
        return controller
    
    def _trigger_pending_updates(self, controller):
        """Helper to trigger any pending batched updates"""
        if controller._update_pending:
            controller._emit_batched_update()

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for test files"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    # Basic initialization tests  
    @pytest.mark.mock_gui
    def test_initialization(self, controller):
        """Test that controller initializes properly"""
        assert controller is not None
        assert controller.image_model is not None
        assert controller.palette_model is not None
        assert controller.project_model is not None
        assert controller.tool_manager is not None
        assert controller.file_manager is not None
        assert controller.palette_manager is not None
        assert controller.undo_manager is not None
        
    # Tool operations tests
    def test_set_tool(self, controller):
        """Test setting different tools"""
        controller.set_tool("pencil")
        assert controller.get_current_tool_name() == "pencil"

        controller.set_tool("fill")
        assert controller.get_current_tool_name() == "fill"

        controller.set_tool("picker")
        assert controller.get_current_tool_name() == "picker"

    def test_set_drawing_color(self, controller):
        """Test setting drawing color"""
        controller.set_drawing_color(5)
        assert controller.tool_manager.current_color == 5

        # Test clamping
        controller.set_drawing_color(20)
        assert controller.tool_manager.current_color == 15

        controller.set_drawing_color(-1)
        assert controller.tool_manager.current_color == 0

    # File operations tests
    def test_new_file(self, controller):
        """Test creating a new file"""
        # Create signal spy
        image_changed_spy = MagicMock()
        palette_changed_spy = MagicMock()
        title_changed_spy = MagicMock()

        controller.imageChanged.connect(image_changed_spy)
        controller.paletteChanged.connect(palette_changed_spy)
        controller.titleChanged.connect(title_changed_spy)

        # Create new file
        controller.new_file(16, 16)
        
        # Trigger any pending updates
        self._trigger_pending_updates(controller)

        # Check model state
        assert controller.image_model.width == 16
        assert controller.image_model.height == 16
        assert controller.image_model.data.shape == (16, 16)
        assert np.all(controller.image_model.data == 0)

        # Check signals were emitted
        image_changed_spy.assert_called_once()
        palette_changed_spy.assert_called_once()
        title_changed_spy.assert_called_once_with("Indexed Pixel Editor - New File")

    def test_open_file_success(self, controller, temp_dir):
        """Test successfully opening an image file"""
        # Create a test image
        test_image = Image.new("P", (8, 8))
        test_palette = []
        for i in range(16):
            test_palette.extend([i * 16, i * 16, i * 16])
        test_palette.extend([0] * (768 - len(test_palette)))
        test_image.putpalette(test_palette)

        # Save test image
        test_path = os.path.join(temp_dir, "test.png")
        test_image.save(test_path)

        # Mock worker behavior
        with patch.object(controller.file_manager, "load_file") as mock_load:
            # Create a mock worker
            mock_worker = MagicMock()
            mock_worker.file_path = test_path  # Set the file_path attribute
            mock_load.return_value = mock_worker

            # Open file
            controller.open_file(test_path)

            # Verify worker was created
            mock_load.assert_called_once_with(test_path)
            assert mock_worker.file_path == test_path
            mock_worker.start.assert_called_once()

    def test_open_file_not_found(self, controller):
        """Test opening a non-existent file"""
        controller.open_file("/path/that/does/not/exist.png")
        controller.error_handler.assert_called_once()
        assert "File not found" in controller.error_handler.call_args[0][0]

    def test_save_file(self, controller, temp_dir):
        """Test saving the current image"""
        # Setup image data
        controller.new_file(8, 8)
        controller.image_model.data[0, 0] = 5

        save_path = os.path.join(temp_dir, "output.png")

        # Mock worker behavior
        with patch.object(controller.file_manager, "save_file") as mock_save:
            mock_worker = MagicMock()
            mock_save.return_value = mock_worker

            # Save file
            controller.save_file(save_path)

            # Verify worker was created
            mock_save.assert_called_once_with(
                controller.image_model, controller.palette_model, save_path, use_grayscale_palette=True
            )
            mock_worker.start.assert_called_once()

    def test_handle_load_result(self, controller):
        """Test handling successful file load"""
        # Create test data
        test_array = np.ones((8, 8), dtype=np.uint8) * 5
        test_palette = [255, 0, 0] * 16 + [0] * (768 - 48)
        metadata = {"palette": test_palette}

        # Create mock worker with file_path
        controller.load_worker = MagicMock()
        controller.load_worker.file_path = "/test/path.png"

        # Spy on signals
        image_changed_spy = MagicMock()
        palette_changed_spy = MagicMock()
        controller.imageChanged.connect(image_changed_spy)
        controller.paletteChanged.connect(palette_changed_spy)

        # Handle result
        controller._handle_load_result(test_array, metadata)
        
        # Trigger any pending updates
        self._trigger_pending_updates(controller)

        # Verify image loaded
        assert controller.image_model.width == 8
        assert controller.image_model.height == 8
        assert np.all(controller.image_model.data == 5)

        # Verify palette loaded
        assert controller.palette_model.colors[0] == (255, 0, 0)

        # Verify signals emitted
        image_changed_spy.assert_called()
        palette_changed_spy.assert_called()

    # Palette operations tests
    def test_load_json_palette(self, controller, temp_dir):
        """Test loading a JSON palette file"""
        # Create test palette
        palette_data = {
            "palette": {
                "name": "Test Palette",
                "colors": [[255, 0, 0], [0, 255, 0], [0, 0, 255]] + [[0, 0, 0]] * 13,
            }
        }

        palette_path = os.path.join(temp_dir, "test.pal.json")
        with open(palette_path, "w") as f:
            json.dump(palette_data, f)

        # Spy on signals
        palette_changed_spy = MagicMock()
        controller.paletteChanged.connect(palette_changed_spy)

        # Load palette
        controller.load_palette_file(palette_path)

        # Verify palette loaded
        assert controller.palette_model.name == "Test Palette"
        assert controller.palette_model.colors[0] == (255, 0, 0)
        assert controller.palette_model.colors[1] == (0, 255, 0)
        assert controller.palette_model.colors[2] == (0, 0, 255)

        # Verify signal emitted
        palette_changed_spy.assert_called()

    def test_switch_palette(self, controller):
        """Test switching between palettes"""
        # Add multiple palettes
        pal1 = PaletteModel(name="Palette 1")
        pal2 = PaletteModel(name="Palette 2")

        controller.palette_manager.add_palette(8, pal1)
        controller.palette_manager.add_palette(9, pal2)

        # Switch palette
        palette_changed_spy = MagicMock()
        controller.paletteChanged.connect(palette_changed_spy)

        controller.switch_palette(9)

        # Verify switch
        assert controller.palette_model.name == "Palette 2"
        palette_changed_spy.assert_called_once()

    # Image operations tests
    def test_update_image_data(self, controller):
        """Test updating image data"""
        controller.new_file(8, 8)

        # Spy on signal
        image_changed_spy = MagicMock()
        controller.imageChanged.connect(image_changed_spy)

        # Update data
        new_data = np.ones((8, 8), dtype=np.uint8) * 3
        controller.update_image_data(new_data)
        
        # Trigger any pending updates
        self._trigger_pending_updates(controller)

        # Verify update
        assert np.all(controller.image_model.data == 3)
        assert controller.image_model.modified
        image_changed_spy.assert_called_once()

    def test_get_image_size(self, controller):
        """Test getting image dimensions"""
        controller.new_file(16, 24)
        assert controller.get_image_size() == (16, 24)

    def test_is_modified(self, controller):
        """Test checking if image is modified"""
        controller.new_file(8, 8)
        assert not controller.is_modified()

        controller.image_model.modified = True
        assert controller.is_modified()

    # Drawing operations tests
    def test_handle_canvas_press_pencil(self, controller):
        """Test pencil tool drawing"""
        controller.new_file(8, 8)
        controller.set_tool("pencil")
        controller.set_drawing_color(5)

        # Draw pixel
        controller.handle_canvas_press(3, 4)
        
        # Trigger any pending updates  
        self._trigger_pending_updates(controller)

        # Verify pixel drawn
        assert controller.image_model.data[4, 3] == 5
        assert controller.image_model.modified

    def test_handle_canvas_press_fill(self, controller):
        """Test fill tool"""
        controller.new_file(8, 8)
        controller.set_tool("fill")
        controller.set_drawing_color(7)

        # Fill from corner
        controller.handle_canvas_press(0, 0)
        
        # Trigger any pending updates
        self._trigger_pending_updates(controller)

        # Verify all pixels filled (they were all 0)
        assert np.all(controller.image_model.data == 7)
        assert controller.image_model.modified

    def test_handle_canvas_press_picker(self, controller):
        """Test color picker tool"""
        controller.new_file(8, 8)
        controller.image_model.data[2, 3] = 9
        controller.set_tool("picker")

        # Pick color
        controller.handle_canvas_press(3, 2)

        # Verify color picked
        assert controller.tool_manager.current_color == 9

    def test_handle_canvas_move(self, controller):
        """Test continuous drawing with pencil"""
        controller.new_file(8, 8)
        controller.set_tool("pencil")
        controller.set_drawing_color(4)

        # Start drawing with press
        controller.handle_canvas_press(0, 0)
        
        # Draw line
        for x in range(1, 4):
            controller.handle_canvas_move(x, 0)
            
        # Release to finish drawing
        controller.handle_canvas_release(3, 0)
        
        # Trigger any pending updates
        self._trigger_pending_updates(controller)

        # Verify line drawn
        for x in range(4):
            assert controller.image_model.data[0, x] == 4

    def test_flood_fill_boundary(self, controller):
        """Test flood fill respects boundaries"""
        controller.new_file(8, 8)

        # Create a box
        controller.image_model.data[1:4, 1] = 1  # Left wall
        controller.image_model.data[1:4, 3] = 1  # Right wall
        controller.image_model.data[1, 1:4] = 1  # Top wall
        controller.image_model.data[3, 1:4] = 1  # Bottom wall

        controller.set_tool("fill")
        controller.set_drawing_color(5)

        # Fill inside box
        controller.handle_canvas_press(2, 2)
        
        # Trigger any pending updates
        self._trigger_pending_updates(controller)

        # Verify only inside was filled
        assert controller.image_model.data[2, 2] == 5
        assert controller.image_model.data[0, 0] == 0  # Outside unchanged
        assert controller.image_model.data[1, 1] == 1  # Wall unchanged

    def test_flood_fill_same_color(self, controller):
        """Test flood fill with same color does nothing"""
        controller.new_file(8, 8)
        controller.image_model.data.fill(3)

        controller.set_tool("fill")
        controller.set_drawing_color(3)

        # Reset modified flag
        controller.image_model.modified = False

        # Try to fill with same color
        controller.handle_canvas_press(0, 0)

        # Nothing should change
        assert not controller.image_model.modified
        assert np.all(controller.image_model.data == 3)

    # Preview generation tests
    @pytest.mark.gui
    def test_get_preview_pixmap_with_palette(self, controller, monkeypatch):
        """Test generating preview with palette applied"""
        controller.new_file(4, 4)
        controller.image_model.data[0, 0] = 1

        # Set distinct palette colors
        controller.palette_model.colors[0] = (255, 0, 0)
        controller.palette_model.colors[1] = (0, 255, 0)

        # Mock QPixmap to avoid headless issues
        mock_pixmap = MagicMock()
        mock_pixmap.width.return_value = 4
        mock_pixmap.height.return_value = 4

        monkeypatch.setattr(
            "pixel_editor.core.pixel_editor_controller_v3.QPixmap.fromImage", lambda img: mock_pixmap
        )

        pixmap = controller.get_preview_pixmap(apply_palette=True)

        assert pixmap is not None
        assert pixmap.width() == 4
        assert pixmap.height() == 4

    @pytest.mark.gui
    def test_get_preview_pixmap_grayscale(self, controller, monkeypatch):
        """Test generating preview in grayscale mode"""
        controller.new_file(4, 4)
        controller.image_model.data[0, 0] = 15

        # Mock QPixmap to avoid headless issues
        mock_pixmap = MagicMock()
        mock_pixmap.width.return_value = 4
        mock_pixmap.height.return_value = 4

        monkeypatch.setattr(
            "pixel_editor.core.pixel_editor_controller_v3.QPixmap.fromImage", lambda img: mock_pixmap
        )

        pixmap = controller.get_preview_pixmap(apply_palette=False)

        assert pixmap is not None
        assert pixmap.width() == 4
        assert pixmap.height() == 4

    # Metadata tests
    def test_check_for_metadata(self, controller, temp_dir):
        """Test loading metadata file"""
        # Create image and metadata files
        image_path = os.path.join(temp_dir, "test.png")
        metadata_path = os.path.join(temp_dir, "test.metadata.json")

        metadata = {
            "palettes": {
                "8": {
                    "name": "Sprite Palette",
                    "colors": [[255, 0, 0]] + [[0, 0, 0]] * 15,
                }
            }
        }

        with open(metadata_path, "w") as f:
            json.dump(metadata, f)

        # Check for metadata
        controller._check_for_metadata(image_path)

        # Verify palette loaded
        assert controller.palette_manager.get_palette(8) is not None
        assert controller.palette_manager.get_palette(8).name == "Sprite Palette"

    def test_check_for_paired_palette(self, controller, temp_dir):
        """Test auto-loading paired palette file"""
        # Create image and palette files
        image_path = os.path.join(temp_dir, "test.png")
        palette_path = os.path.join(temp_dir, "test.pal.json")

        palette_data = {
            "palette": {
                "name": "Paired Palette",
                "colors": [[0, 255, 255]] + [[0, 0, 0]] * 15,
            }
        }

        with open(palette_path, "w") as f:
            json.dump(palette_data, f)

        # Mock load_palette_file to verify it's called
        with patch.object(controller, "load_palette_file") as mock_load:
            controller._check_for_paired_palette(image_path)
            mock_load.assert_called_once_with(palette_path)

    # Settings operations tests
    def test_get_recent_files(self, controller):
        """Test getting recent files from settings"""
        with patch.object(
            controller.settings, "get_recent_files", return_value=["/path1", "/path2"]
        ):
            recent = controller.get_recent_files()
            assert recent == ["/path1", "/path2"]

    def test_should_auto_load_last(self, controller):
        """Test checking auto-load setting"""
        with patch.object(
            controller.settings, "should_auto_load_last", return_value=True
        ):
            assert controller.should_auto_load_last()

    def test_get_last_file(self, controller):
        """Test getting last opened file"""
        with patch.object(
            controller.settings, "get_last_file", return_value="/last/file.png"
        ):
            assert controller.get_last_file() == "/last/file.png"

    # Palette metadata operations tests
    def test_has_metadata_palettes(self, controller):
        """Test checking for multiple palettes"""
        assert not controller.has_metadata_palettes()

        # Add another palette
        controller.palette_manager.add_palette(9, PaletteModel())
        assert controller.has_metadata_palettes()

    def test_get_available_palettes(self, controller):
        """Test getting list of available palettes"""
        # Add test palettes
        pal1 = PaletteModel(name="Palette 8")
        pal2 = PaletteModel(name="Palette 10")

        controller.palette_manager.add_palette(8, pal1)
        controller.palette_manager.add_palette(10, pal2)

        available = controller.get_available_palettes()

        assert len(available) == 2
        assert (8, "Palette 8") in available
        assert (10, "Palette 10") in available

    def test_has_image(self, controller):
        """Test checking if image is loaded"""
        # Ensure controller starts without an image
        controller.image_model.data = None
        assert not controller.has_image()

        controller.new_file(8, 8)
        assert controller.has_image()

    def test_get_current_colors(self, controller):
        """Test getting current palette colors"""
        controller.palette_model.colors[0] = (255, 128, 64)
        colors = controller.get_current_colors()

        assert len(colors) == 16
        assert colors[0] == (255, 128, 64)


class TestControllerErrorHandling:
    """Test error handling in the controller"""

    @pytest.fixture
    def controller(self):
        """Create a controller with error tracking"""
        controller = PixelEditorController()
        controller.errors = []
        controller.error.connect(lambda msg: controller.errors.append(msg))
        return controller

    def test_handle_load_error(self, controller):
        """Test handling file load errors"""
        controller._handle_load_error("Test error message")

        assert len(controller.errors) == 1
        assert "Failed to load file: Test error message" in controller.errors[0]

    def test_handle_save_error(self, controller):
        """Test handling file save errors"""
        controller._handle_save_error("Save failed")

        assert len(controller.errors) == 1
        assert "Failed to save file: Save failed" in controller.errors[0]

    def test_handle_palette_error(self, controller):
        """Test handling palette load errors"""
        controller._handle_palette_error("Invalid format")

        assert len(controller.errors) == 1
        assert "Failed to load palette: Invalid format" in controller.errors[0]

    def test_load_result_exception(self, controller):
        """Test exception handling in load result"""
        # Create invalid worker
        controller.load_worker = MagicMock()
        controller.load_worker.file_path = "/test.png"

        # Pass invalid data that will cause exception
        controller._handle_load_result(None, {})

        assert len(controller.errors) == 1
        assert "Failed to load file:" in controller.errors[0]

    def test_palette_result_invalid_format(self, controller):
        """Test handling invalid palette format"""
        controller._handle_palette_result({"invalid": "data"})

        assert len(controller.errors) == 1
        assert "Invalid palette format" in controller.errors[0]


class TestControllerIntegration:
    """Integration tests for controller with real file operations"""

    @pytest.fixture
    def controller(self):
        """Create controller for integration tests"""
        return PixelEditorController()

    @pytest.fixture
    def test_image_path(self, tmp_path):
        """Create a test image file"""
        # Create 8x8 test image
        img = Image.new("P", (8, 8))

        # Set some pixels
        pixels = img.load()
        pixels[0, 0] = 1
        pixels[7, 7] = 15

        # Create palette
        palette = []
        for i in range(16):
            palette.extend([i * 16, i * 8, 255 - i * 16])
        palette.extend([0] * (768 - len(palette)))
        img.putpalette(palette)

        # Save
        path = tmp_path / "test_image.png"
        img.save(str(path))
        return str(path)

    def test_full_save_load_cycle(self, controller, tmp_path, test_image_path):
        """Test complete save/load cycle"""
        # Load test image (using mock worker for simplicity)
        test_array = np.array(Image.open(test_image_path))
        controller._handle_load_result(
            test_array, {"palette": list(Image.open(test_image_path).getpalette())}
        )

        # Modify image
        controller.handle_canvas_press(3, 3)
        controller.set_drawing_color(7)
        controller.handle_canvas_press(4, 4)

        # Save to new file
        save_path = tmp_path / "saved_image.png"

        # Manually save (bypassing worker)
        img = controller.image_model.to_pil_image(
            controller.palette_model.to_flat_list()
        )
        img.save(str(save_path))

        # Load saved file and verify
        saved_img = Image.open(str(save_path))
        saved_array = np.array(saved_img)

        assert saved_array[3, 3] == 0  # Default drawing color
        assert saved_array[4, 4] == 7
        assert saved_array[0, 0] == 1  # Original pixel
        assert saved_array[7, 7] == 15  # Original pixel
