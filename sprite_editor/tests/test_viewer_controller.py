#!/usr/bin/env python3
"""
Comprehensive tests for viewer controller
Tests viewer functionality with minimal mocking
"""

import os
from unittest.mock import MagicMock, patch

import pytest
from PIL import Image
from PyQt6.QtWidgets import QFileDialog, QMessageBox

from sprite_editor.controllers.viewer_controller import ViewerController
from sprite_editor.models.palette_model import PaletteModel
from sprite_editor.models.sprite_model import SpriteModel


@pytest.fixture
def models():
    """Create real model instances"""
    sprite_model = SpriteModel()
    palette_model = PaletteModel()
    return sprite_model, palette_model


@pytest.fixture
def mock_view():
    """Create mock viewer view"""
    view = MagicMock()

    # Add signal mocks
    view.zoom_in_requested = MagicMock()
    view.zoom_out_requested = MagicMock()
    view.zoom_fit_requested = MagicMock()
    view.grid_toggled = MagicMock()
    view.save_requested = MagicMock()
    view.open_editor_requested = MagicMock()

    # Add method mocks
    view.set_image = MagicMock()
    view.set_palette = MagicMock()
    view.update_zoom_label = MagicMock()
    view.update_image_info = MagicMock()

    # Mock sprite viewer
    sprite_viewer = MagicMock()
    sprite_viewer.zoom_in = MagicMock()
    sprite_viewer.zoom_out = MagicMock()
    sprite_viewer.zoom_fit = MagicMock()
    sprite_viewer.set_show_grid = MagicMock()
    sprite_viewer.get_current_zoom = MagicMock(return_value=100)
    sprite_viewer.get_image_info = MagicMock(
        return_value={
            "width": 256,
            "height": 256,
            "tiles_x": 32,
            "tiles_y": 32,
            "total_tiles": 1024,
            "mode": "P",
            "colors": 16,
        }
    )

    view.get_sprite_viewer = MagicMock(return_value=sprite_viewer)

    return view


@pytest.fixture
def controller(models, mock_view):
    """Create viewer controller instance"""
    sprite_model, palette_model = models
    return ViewerController(sprite_model, palette_model, mock_view)
    # Don't call connect_signals() - it's automatically called in BaseController.__init__


@pytest.fixture
def test_image():
    """Create a test image"""
    img = Image.new("P", (128, 128))
    # Create a simple palette (16 colors)
    palette = []
    for i in range(16):
        palette.extend([i * 16, i * 16, i * 16])  # Grayscale
    # Pad to 256 colors
    palette.extend([0, 0, 0] * (256 - 16))
    img.putpalette(palette)
    return img


@pytest.mark.unit
class TestViewerControllerInitialization:
    """Test controller initialization"""

    def test_controller_creation(self, models, mock_view):
        """Test creating viewer controller"""
        sprite_model, palette_model = models
        controller = ViewerController(sprite_model, palette_model, mock_view)

        assert controller.model == sprite_model
        assert controller.palette_model == palette_model
        assert controller.view == mock_view

    def test_signal_connections(self, controller, mock_view):
        """Test signal connections are established"""
        # Check view signal connections
        assert mock_view.zoom_in_requested.connect.called
        assert mock_view.zoom_out_requested.connect.called
        assert mock_view.zoom_fit_requested.connect.called
        assert mock_view.grid_toggled.connect.called
        assert mock_view.save_requested.connect.called
        assert mock_view.open_editor_requested.connect.called


@pytest.mark.unit
class TestImageDisplay:
    """Test image display functionality"""

    def test_set_image_with_valid_image(self, controller, mock_view, test_image):
        """Test setting a valid image"""
        controller.set_image(test_image)

        # Verify image was set in view
        mock_view.set_image.assert_called_once_with(test_image)

        # Verify image info was updated
        mock_view.update_image_info.assert_called_once()

        # Verify palette was set (image has palette)
        mock_view.set_palette.assert_called_once()
        assert len(mock_view.set_palette.call_args[0][0]) == 768  # 256 * 3

    def test_set_image_with_none(self, controller, mock_view):
        """Test setting None as image"""
        controller.set_image(None)

        # View should not be updated
        mock_view.set_image.assert_not_called()
        mock_view.update_image_info.assert_not_called()

    def test_set_image_without_palette(self, controller, mock_view):
        """Test setting an image without palette"""
        # Create RGB image (no palette)
        img = Image.new("RGB", (128, 128))

        controller.set_image(img)

        # Image should be set
        mock_view.set_image.assert_called_once_with(img)

        # Palette should not be set
        mock_view.set_palette.assert_not_called()

    def test_update_image_info(self, controller, mock_view):
        """Test updating image information"""
        controller.update_image_info()

        # Should get info from viewer
        sprite_viewer = mock_view.get_sprite_viewer()
        sprite_viewer.get_image_info.assert_called_once()

        # Should update view with info
        expected_info = {
            "width": 256,
            "height": 256,
            "tiles_x": 32,
            "tiles_y": 32,
            "total_tiles": 1024,
            "mode": "P",
            "colors": 16,
        }
        mock_view.update_image_info.assert_called_once_with(expected_info)


@pytest.mark.unit
class TestZoomFunctionality:
    """Test zoom control functionality"""

    def test_zoom_in(self, controller, mock_view):
        """Test zooming in"""
        controller.zoom_in()

        # Get sprite viewer
        sprite_viewer = mock_view.get_sprite_viewer()

        # Verify zoom in was called
        sprite_viewer.zoom_in.assert_called_once()

        # Verify zoom label was updated
        mock_view.update_zoom_label.assert_called_once_with(100)

    def test_zoom_out(self, controller, mock_view):
        """Test zooming out"""
        controller.zoom_out()

        # Get sprite viewer
        sprite_viewer = mock_view.get_sprite_viewer()

        # Verify zoom out was called
        sprite_viewer.zoom_out.assert_called_once()

        # Verify zoom label was updated
        mock_view.update_zoom_label.assert_called_once_with(100)

    def test_zoom_fit(self, controller, mock_view):
        """Test zoom fit"""
        controller.zoom_fit()

        # Get sprite viewer
        sprite_viewer = mock_view.get_sprite_viewer()

        # Verify zoom fit was called
        sprite_viewer.zoom_fit.assert_called_once()

        # Verify zoom label was updated
        mock_view.update_zoom_label.assert_called_once_with(100)

    def test_toggle_grid_on(self, controller, mock_view):
        """Test toggling grid on"""
        controller.toggle_grid(True)

        sprite_viewer = mock_view.get_sprite_viewer()
        sprite_viewer.set_show_grid.assert_called_once_with(True)

    def test_toggle_grid_off(self, controller, mock_view):
        """Test toggling grid off"""
        controller.toggle_grid(False)

        sprite_viewer = mock_view.get_sprite_viewer()
        sprite_viewer.set_show_grid.assert_called_once_with(False)


@pytest.mark.unit
class TestFileSaveOperations:
    """Test file save operations"""

    def test_save_current_view_no_image(self, controller, mock_view):
        """Test saving when no image is loaded"""
        controller.model.current_image = None

        with patch.object(QMessageBox, "warning") as mock_warning:
            controller.save_current_view()

            # Warning should be shown
            mock_warning.assert_called_once()
            args = mock_warning.call_args[0]
            assert args[1] == "Error"
            assert "No image to save" in args[2]

    def test_save_current_view_cancelled(self, controller, mock_view, test_image):
        """Test saving when dialog is cancelled"""
        controller.model.current_image = test_image

        with patch.object(QFileDialog, "getSaveFileName") as mock_dialog:
            mock_dialog.return_value = ("", "")

            controller.save_current_view()

            # Dialog should be shown
            mock_dialog.assert_called_once()
            args = mock_dialog.call_args[0]
            assert args[1] == "Save Image"
            assert args[2] == "sprites.png"

    def test_save_current_view_success(
        self, controller, mock_view, test_image, tmp_path
    ):
        """Test successful save"""
        controller.model.current_image = test_image
        output_file = str(tmp_path / "test_output.png")

        with patch.object(QFileDialog, "getSaveFileName") as mock_dialog:
            mock_dialog.return_value = (output_file, "PNG Files (*.png)")

            with patch.object(QMessageBox, "information") as mock_info:
                controller.save_current_view()

                # Verify file was saved
                assert os.path.exists(output_file)

                # Verify success message
                mock_info.assert_called_once()
                args = mock_info.call_args[0]
                assert args[1] == "Success"
                assert output_file in args[2]


@pytest.mark.unit
class TestExternalEditor:
    """Test opening in external editor"""

    def test_open_in_editor_no_image(self, controller, mock_view):
        """Test opening editor when no image is loaded"""
        controller.model.current_image = None

        with patch.object(QMessageBox, "warning") as mock_warning:
            controller.open_in_editor()

            # Warning should be shown
            mock_warning.assert_called_once()
            args = mock_warning.call_args[0]
            assert args[1] == "Error"
            assert "No image to edit" in args[2]

    def test_open_in_editor_windows(self, controller, mock_view, test_image):
        """Test opening in editor on Windows"""
        controller.model.current_image = test_image

        with patch("sys.platform", "win32"):
            # Mock os module with startfile attribute
            mock_os = MagicMock()
            mock_os.startfile = MagicMock()

            with patch("sprite_editor.controllers.viewer_controller.os", mock_os):
                with patch("tempfile.NamedTemporaryFile") as mock_temp:
                    # Mock temp file
                    mock_file = MagicMock()
                    mock_file.name = "/tmp/test.png"
                    mock_temp.return_value.__enter__.return_value = mock_file

                    controller.open_in_editor()

                    # Verify startfile was called
                    mock_os.startfile.assert_called_once_with("/tmp/test.png")

    def test_open_in_editor_macos(self, controller, mock_view, test_image):
        """Test opening in editor on macOS"""
        controller.model.current_image = test_image

        with patch("sys.platform", "darwin"), patch("os.system") as mock_system:
            with patch("tempfile.NamedTemporaryFile") as mock_temp:
                # Mock temp file
                mock_file = MagicMock()
                mock_file.name = "/tmp/test.png"
                mock_temp.return_value.__enter__.return_value = mock_file

                controller.open_in_editor()

                # Verify open command was called
                mock_system.assert_called_once_with("open '/tmp/test.png'")

    def test_open_in_editor_linux(self, controller, mock_view, test_image):
        """Test opening in editor on Linux"""
        controller.model.current_image = test_image

        with patch("sys.platform", "linux"), patch("os.system") as mock_system:
            with patch("tempfile.NamedTemporaryFile") as mock_temp:
                # Mock temp file
                mock_file = MagicMock()
                mock_file.name = "/tmp/test.png"
                mock_temp.return_value.__enter__.return_value = mock_file

                controller.open_in_editor()

                # Verify xdg-open was called
                mock_system.assert_called_once_with("xdg-open '/tmp/test.png'")


@pytest.mark.unit
class TestPaletteIntegration:
    """Test palette integration"""

    def test_on_palette_applied_with_image(self, controller, mock_view, test_image):
        """Test palette application when image exists"""
        controller.model.current_image = test_image

        # Clear previous calls
        mock_view.set_image.reset_mock()

        controller._on_palette_applied(5)

        # Image should be refreshed
        mock_view.set_image.assert_called_once_with(test_image)

    def test_on_palette_applied_no_image(self, controller, mock_view):
        """Test palette application when no image exists"""
        controller.model.current_image = None

        controller._on_palette_applied(5)

        # Nothing should happen
        mock_view.set_image.assert_not_called()


@pytest.mark.unit
class TestSignalHandling:
    """Test model signal handling"""

    def test_current_image_changed_signal(self, test_image):
        """Test handling current_image_changed signal"""
        # Create fresh instances for this test
        sprite_model = SpriteModel()
        palette_model = PaletteModel()
        mock_view = MagicMock()
        mock_view.set_image = MagicMock()
        mock_view.update_image_info = MagicMock()
        mock_view.set_palette = MagicMock()
        mock_view.get_sprite_viewer = MagicMock(
            return_value=MagicMock(get_image_info=MagicMock(return_value={}))
        )

        # Create controller - signals are connected automatically in BaseController.__init__
        ViewerController(sprite_model, palette_model, mock_view)
        # Don't call connect_signals() again - it's already been called!

        # Clear any initialization calls
        mock_view.set_image.reset_mock()

        # Set the property - this automatically emits the signal due to ObservableProperty
        sprite_model.current_image = test_image

        # Verify image was set exactly once
        assert mock_view.set_image.call_count == 1
        mock_view.set_image.assert_called_with(test_image)

    def test_palette_applied_signal(self, test_image):
        """Test handling palette_applied signal"""
        # Create fresh instances for this test
        sprite_model = SpriteModel()
        palette_model = PaletteModel()
        mock_view = MagicMock()
        mock_view.set_image = MagicMock()
        mock_view.update_image_info = MagicMock()
        mock_view.set_palette = MagicMock()
        mock_view.get_sprite_viewer = MagicMock(
            return_value=MagicMock(get_image_info=MagicMock(return_value={}))
        )

        # Create controller - signals are connected automatically in BaseController.__init__
        ViewerController(sprite_model, palette_model, mock_view)
        # Don't call connect_signals() again - it's already been called!

        # Set current image
        sprite_model.current_image = test_image

        # Clear any initialization calls
        mock_view.set_image.reset_mock()

        # Emit signal
        palette_model.palette_applied.emit(3)

        # Verify image was refreshed exactly once
        assert mock_view.set_image.call_count == 1
        mock_view.set_image.assert_called_with(test_image)


@pytest.mark.integration
class TestViewerControllerIntegration:
    """Integration tests for ViewerController"""

    def test_complete_zoom_workflow(self, controller, mock_view):
        """Test complete zoom workflow"""
        sprite_viewer = mock_view.get_sprite_viewer()

        # Set different zoom levels for each operation
        zoom_levels = [150, 75, 100]
        sprite_viewer.get_current_zoom.side_effect = zoom_levels

        # Zoom in
        controller.zoom_in()
        assert mock_view.update_zoom_label.call_args[0][0] == 150

        # Zoom out
        controller.zoom_out()
        assert mock_view.update_zoom_label.call_args[0][0] == 75

        # Zoom fit
        controller.zoom_fit()
        assert mock_view.update_zoom_label.call_args[0][0] == 100

        # Verify all operations were called
        assert sprite_viewer.zoom_in.call_count == 1
        assert sprite_viewer.zoom_out.call_count == 1
        assert sprite_viewer.zoom_fit.call_count == 1
        assert mock_view.update_zoom_label.call_count == 3

    def test_image_save_workflow(self, controller, mock_view, test_image, tmp_path):
        """Test complete image save workflow"""
        # Set image
        controller.model.current_image = test_image
        controller.set_image(test_image)

        # Save image
        output_file = str(tmp_path / "workflow_test.png")

        with patch.object(QFileDialog, "getSaveFileName") as mock_dialog:
            mock_dialog.return_value = (output_file, "PNG Files (*.png)")

            with patch.object(QMessageBox, "information"):
                controller.save_current_view()

        # Verify file exists and is valid
        assert os.path.exists(output_file)
        saved_img = Image.open(output_file)
        assert saved_img.size == (128, 128)
        assert saved_img.mode == "P"
