#!/usr/bin/env python3
"""
Tests for extract controller
Tests extraction functionality with minimal mocking
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from PIL import Image
from PyQt6.QtWidgets import QFileDialog, QMessageBox

from sprite_editor.controllers.extract_controller import ExtractController
from sprite_editor.models.project_model import ProjectModel
from sprite_editor.models.sprite_model import SpriteModel


@pytest.fixture
def models():
    """Create model instances with mocked methods where needed"""
    sprite_model = SpriteModel()
    project_model = ProjectModel()

    # Mock methods that need tracking
    project_model.add_recent_file = MagicMock(wraps=project_model.add_recent_file)
    project_model.mark_modified = MagicMock(wraps=project_model.mark_modified)

    return sprite_model, project_model


@pytest.fixture
def mock_view():
    """Create mock extract view"""
    view = MagicMock()

    # Add signal mocks
    view.extract_requested = MagicMock()
    view.browse_vram_requested = MagicMock()
    view.browse_cgram_requested = MagicMock()

    # Add method mocks
    view.get_extraction_params = MagicMock()
    view.clear_output = MagicMock()
    view.append_output = MagicMock()
    view.set_extract_enabled = MagicMock()
    view.set_vram_file = MagicMock()
    view.set_cgram_file = MagicMock()

    return view


@pytest.fixture
def controller(models, mock_view):
    """Create extract controller instance"""
    sprite_model, project_model = models
    return ExtractController(sprite_model, project_model, mock_view)
    # Don't call connect_signals() - it's automatically called in BaseController.__init__


@pytest.fixture
def temp_files(tmp_path):
    """Create temporary test files"""
    # Create test VRAM file
    vram_file = tmp_path / "test.vram"
    vram_file.write_bytes(b"\x00" * 0x10000)  # 64KB

    # Create test CGRAM file
    cgram_file = tmp_path / "test.cgram"
    cgram_file.write_bytes(b"\x00" * 512)  # 512 bytes

    return {"vram": str(vram_file), "cgram": str(cgram_file), "dir": str(tmp_path)}


@pytest.mark.unit
class TestExtractControllerInitialization:
    """Test controller initialization"""

    def test_controller_creation(self, models, mock_view):
        """Test creating extract controller"""
        sprite_model, project_model = models
        controller = ExtractController(sprite_model, project_model, mock_view)

        assert controller.model == sprite_model
        assert controller.project_model == project_model
        assert controller.view == mock_view
        assert controller.extract_worker is None

    def test_signal_connections(self, controller, mock_view):
        """Test signal connections are established"""
        # Check view signal connections
        assert mock_view.extract_requested.connect.called
        assert mock_view.browse_vram_requested.connect.called
        assert mock_view.browse_cgram_requested.connect.called


@pytest.mark.unit
class TestFileOperations:
    """Test file browsing operations"""

    def test_browse_vram_file_selected(self, controller, temp_files):
        """Test browsing and selecting VRAM file"""
        with patch.object(QFileDialog, "getOpenFileName") as mock_dialog:
            mock_dialog.return_value = (temp_files["vram"], "Dump Files (*.dmp)")

            controller.browse_vram_file()

            # Verify dialog was called
            mock_dialog.assert_called_once()
            args = mock_dialog.call_args[0]
            assert args[1] == "Select VRAM Dump"

            # Verify model was updated
            assert controller.model.vram_file == temp_files["vram"]

            # Verify recent file was added
            controller.project_model.add_recent_file.assert_called_with(
                temp_files["vram"], "vram"
            )

    def test_browse_vram_file_cancelled(self, controller):
        """Test cancelling VRAM file dialog"""
        with patch.object(QFileDialog, "getOpenFileName") as mock_dialog:
            mock_dialog.return_value = ("", "")

            controller.browse_vram_file()

            # Model should not be updated
            assert controller.model.vram_file == ""
            controller.project_model.add_recent_file.assert_not_called()

    def test_browse_cgram_file_selected(self, controller, temp_files):
        """Test browsing and selecting CGRAM file"""
        with patch.object(QFileDialog, "getOpenFileName") as mock_dialog:
            mock_dialog.return_value = (temp_files["cgram"], "Dump Files (*.dmp)")

            controller.browse_cgram_file()

            # Verify dialog was called
            mock_dialog.assert_called_once()
            args = mock_dialog.call_args[0]
            assert args[1] == "Select CGRAM Dump"

            # Verify model was updated
            assert controller.model.cgram_file == temp_files["cgram"]

            # Verify recent file was added
            controller.project_model.add_recent_file.assert_called_with(
                temp_files["cgram"], "cgram"
            )

    def test_browse_with_existing_file(self, controller, temp_files):
        """Test browsing with existing file sets initial directory"""
        # Set existing file
        controller.model.vram_file = temp_files["vram"]

        with patch.object(QFileDialog, "getOpenFileName") as mock_dialog:
            mock_dialog.return_value = ("", "")

            controller.browse_vram_file()

            # Check initial directory was set
            args = mock_dialog.call_args[0]
            assert args[2] == str(Path(temp_files["vram"]).parent)

    def test_browse_cgram_with_existing_file(self, controller, temp_files):
        """Test browsing CGRAM with existing file sets initial directory"""
        # Set existing CGRAM file
        controller.model.cgram_file = temp_files["cgram"]

        with patch.object(QFileDialog, "getOpenFileName") as mock_dialog:
            mock_dialog.return_value = ("", "")

            controller.browse_cgram_file()

            # Check initial directory was set
            args = mock_dialog.call_args[0]
            assert args[2] == str(Path(temp_files["cgram"]).parent)


@pytest.mark.unit
class TestExtractionValidation:
    """Test extraction parameter validation"""

    def test_extract_sprites_no_vram_file(self, controller, mock_view):
        """Test extraction with missing VRAM file"""
        # Setup view to return empty params
        mock_view.get_extraction_params.return_value = {
            "vram_file": "",
            "offset": 0xC000,
            "size": 0x1000,
            "tiles_per_row": 16,
            "use_palette": False,
        }

        with patch.object(QMessageBox, "warning") as mock_warning:
            controller.extract_sprites()

            # Verify warning was shown
            mock_warning.assert_called_once()
            args = mock_warning.call_args[0]
            assert args[1] == "Error"
            assert "valid VRAM file" in args[2]

            # Verify extraction didn't proceed
            mock_view.clear_output.assert_not_called()
            assert controller.extract_worker is None

    def test_extract_sprites_nonexistent_file(self, controller, mock_view):
        """Test extraction with non-existent VRAM file"""
        mock_view.get_extraction_params.return_value = {
            "vram_file": "/nonexistent/file.vram",
            "offset": 0xC000,
            "size": 0x1000,
            "tiles_per_row": 16,
            "use_palette": False,
        }

        with patch.object(QMessageBox, "warning") as mock_warning:
            controller.extract_sprites()

            # Verify warning was shown
            mock_warning.assert_called_once()
            mock_view.clear_output.assert_not_called()


@pytest.mark.unit
class TestExtractionProcess:
    """Test the extraction process"""

    def test_successful_extraction_without_palette(
        self, controller, mock_view, temp_files
    ):
        """Test successful extraction without palette"""
        params = {
            "vram_file": temp_files["vram"],
            "offset": 0xC000,
            "size": 0x1000,
            "tiles_per_row": 16,
            "use_palette": False,
        }
        mock_view.get_extraction_params.return_value = params

        # Mock the worker
        with patch(
            "sprite_editor.controllers.extract_controller.ExtractWorker"
        ) as mock_worker_class:
            mock_worker = MagicMock()
            mock_worker_class.return_value = mock_worker

            controller.extract_sprites()

            # Verify worker was created with correct parameters
            mock_worker_class.assert_called_once_with(
                temp_files["vram"], 0xC000, 0x1000, 16, None, None
            )

            # Verify UI updates
            mock_view.clear_output.assert_called_once()
            mock_view.append_output.assert_called_with("Starting extraction...")
            mock_view.set_extract_enabled.assert_called_with(False)

            # Verify worker signals were connected
            assert mock_worker.progress.connect.called
            assert mock_worker.finished.connect.called
            assert mock_worker.error.connect.called

            # Verify worker was started
            mock_worker.start.assert_called_once()

    def test_successful_extraction_with_palette(
        self, controller, mock_view, temp_files
    ):
        """Test successful extraction with palette"""
        params = {
            "vram_file": temp_files["vram"],
            "offset": 0xC000,
            "size": 0x1000,
            "tiles_per_row": 16,
            "use_palette": True,
            "palette_num": 5,
            "cgram_file": temp_files["cgram"],
        }
        mock_view.get_extraction_params.return_value = params

        with patch(
            "sprite_editor.controllers.extract_controller.ExtractWorker"
        ) as mock_worker_class:
            mock_worker = MagicMock()
            mock_worker_class.return_value = mock_worker

            controller.extract_sprites()

            # Verify worker was created with palette parameters
            mock_worker_class.assert_called_once_with(
                temp_files["vram"], 0xC000, 0x1000, 16, 5, temp_files["cgram"]
            )

    def test_extraction_progress_callback(self, controller, mock_view):
        """Test handling extraction progress updates"""
        controller.on_extract_progress("Processing tile 50/100")

        mock_view.append_output.assert_called_once_with("Processing tile 50/100")

    def test_extraction_finished_callback(self, controller, mock_view):
        """Test handling successful extraction completion"""
        # Create a test image
        test_image = Image.new("RGB", (256, 256))

        controller.on_extract_finished(test_image, 64)

        # Verify UI was re-enabled
        mock_view.set_extract_enabled.assert_called_once_with(True)

        # Verify model was updated
        assert controller.model.current_image == test_image

        # Verify output messages
        mock_view.append_output.assert_any_call("\nSuccess! Extracted 64 tiles")
        mock_view.append_output.assert_any_call("Image size: 256x256 pixels")

        # Verify project was marked as modified
        controller.project_model.mark_modified.assert_called_once()

    def test_extraction_error_callback(self, controller, mock_view):
        """Test handling extraction error"""
        error_msg = "Failed to read VRAM file"

        with patch.object(QMessageBox, "critical") as mock_critical:
            controller.on_extract_error(error_msg)

            # Verify UI was re-enabled
            mock_view.set_extract_enabled.assert_called_once_with(True)

            # Verify error was logged
            mock_view.append_output.assert_called_once_with(f"\nError: {error_msg}")

            # Verify error dialog was shown
            mock_critical.assert_called_once()
            args = mock_critical.call_args[0]
            assert args[1] == "Extraction Error"
            assert args[2] == error_msg


@pytest.mark.unit
class TestRecentFiles:
    """Test loading recent files"""

    def test_load_recent_vram_exists(self, controller, temp_files):
        """Test loading existing recent VRAM file"""
        controller.load_recent_vram(temp_files["vram"])

        # Verify model was updated
        assert controller.model.vram_file == temp_files["vram"]

        # Verify it was added to recent files
        controller.project_model.add_recent_file.assert_called_with(
            temp_files["vram"], "vram"
        )

    def test_load_recent_vram_not_exists(self, controller):
        """Test loading non-existent recent VRAM file"""
        controller.load_recent_vram("/nonexistent/file.vram")

        # Model should not be updated
        assert controller.model.vram_file == ""
        controller.project_model.add_recent_file.assert_not_called()

    def test_load_recent_cgram_exists(self, controller, temp_files):
        """Test loading existing recent CGRAM file"""
        controller.load_recent_cgram(temp_files["cgram"])

        # Verify model was updated
        assert controller.model.cgram_file == temp_files["cgram"]

        # Verify it was added to recent files
        controller.project_model.add_recent_file.assert_called_with(
            temp_files["cgram"], "cgram"
        )

    def test_browse_cgram_with_nonexistent_directory(self, controller):
        """Test browsing CGRAM when directory doesn't exist"""
        # Set existing file with non-existent directory
        controller.model.cgram_file = "/nonexistent/directory/file.cgram"

        with patch.object(QFileDialog, "getOpenFileName") as mock_dialog:
            mock_dialog.return_value = ("", "")

            controller.browse_cgram_file()

            # Check dialog was called with empty initial directory
            args = mock_dialog.call_args[0]
            assert args[2] == ""  # Initial directory should be empty
