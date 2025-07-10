#!/usr/bin/env python3
"""
Tests for inject controller
Tests injection functionality with minimal mocking
"""

import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from PIL import Image
from PyQt6.QtWidgets import QFileDialog, QMessageBox

from sprite_editor.controllers.inject_controller import InjectController
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

    # Mock model validate_png method
    sprite_model.validate_png = MagicMock(return_value=(True, []))

    return sprite_model, project_model


@pytest.fixture
def mock_view():
    """Create mock inject view"""
    view = MagicMock()

    # Add signal mocks
    view.inject_requested = MagicMock()
    view.browse_png_requested = MagicMock()
    view.browse_vram_requested = MagicMock()

    # Add method mocks
    view.get_injection_params = MagicMock()
    view.clear_output = MagicMock()
    view.append_output = MagicMock()
    view.set_inject_enabled = MagicMock()
    view.set_vram_file = MagicMock()
    view.set_png_file = MagicMock()
    view.set_validation_text = MagicMock()

    return view


@pytest.fixture
def controller(models, mock_view):
    """Create inject controller instance"""
    sprite_model, project_model = models
    return InjectController(sprite_model, project_model, mock_view)
    # Don't call connect_signals() - it's automatically called in BaseController.__init__


@pytest.fixture
def temp_files(tmp_path):
    """Create temporary test files"""
    # Create test VRAM file
    vram_file = tmp_path / "test.vram"
    vram_file.write_bytes(b"\x00" * 0x10000)  # 64KB

    # Create test PNG file (8x8 minimal valid PNG)
    png_file = tmp_path / "test.png"
    img = Image.new("RGB", (8, 8), color="red")
    img.save(png_file)

    return {"vram": str(vram_file), "png": str(png_file), "dir": str(tmp_path)}


@pytest.mark.unit
class TestInjectControllerInitialization:
    """Test controller initialization"""

    def test_controller_creation(self, models, mock_view):
        """Test creating inject controller"""
        sprite_model, project_model = models
        controller = InjectController(sprite_model, project_model, mock_view)

        assert controller.model == sprite_model
        assert controller.project_model == project_model
        assert controller.view == mock_view
        assert controller.inject_worker is None

    def test_signal_connections(self, controller, mock_view):
        """Test signal connections are established"""
        # Check view signal connections
        assert mock_view.inject_requested.connect.called
        assert mock_view.browse_png_requested.connect.called
        assert mock_view.browse_vram_requested.connect.called


@pytest.mark.unit
class TestFileOperations:
    """Test file browsing operations"""

    def test_browse_png_file_selected(self, controller, temp_files):
        """Test browsing and selecting PNG file"""
        with patch.object(QFileDialog, "getOpenFileName") as mock_dialog:
            mock_dialog.return_value = (temp_files["png"], "PNG Files (*.png)")

            # PNG validation is already mocked in fixture

            controller.browse_png_file()

            # Verify dialog was called
            mock_dialog.assert_called_once()
            args = mock_dialog.call_args[0]
            assert args[1] == "Select PNG File"

            # Verify view was updated
            controller.view.set_png_file.assert_called_with(temp_files["png"])

            # Verify recent file was added
            controller.project_model.add_recent_file.assert_called_with(
                temp_files["png"], "png"
            )

            # Verify PNG was validated
            controller.model.validate_png.assert_called_with(temp_files["png"])
            controller.view.set_validation_text.assert_called_with(
                "✓ PNG is valid for SNES conversion", True
            )

    def test_browse_png_file_cancelled(self, controller):
        """Test cancelling PNG file dialog"""
        with patch.object(QFileDialog, "getOpenFileName") as mock_dialog:
            mock_dialog.return_value = ("", "")

            controller.browse_png_file()

            # View should not be updated
            controller.view.set_png_file.assert_not_called()
            controller.project_model.add_recent_file.assert_not_called()

    def test_browse_vram_file_selected(self, controller, temp_files):
        """Test browsing and selecting VRAM file"""
        with patch.object(QFileDialog, "getOpenFileName") as mock_dialog:
            mock_dialog.return_value = (temp_files["vram"], "Dump Files (*.dmp)")

            controller.browse_vram_file()

            # Verify dialog was called
            mock_dialog.assert_called_once()
            args = mock_dialog.call_args[0]
            assert args[1] == "Select Target VRAM"

            # Verify both view and model were updated
            controller.view.set_vram_file.assert_called_with(temp_files["vram"])
            assert controller.model.vram_file == temp_files["vram"]

            # Verify recent file was added
            controller.project_model.add_recent_file.assert_called_with(
                temp_files["vram"], "vram"
            )

    def test_browse_vram_with_existing_file(self, controller, temp_files):
        """Test browsing with existing VRAM file sets initial directory"""
        # Set existing file
        controller.model.vram_file = temp_files["vram"]

        with patch.object(QFileDialog, "getOpenFileName") as mock_dialog:
            mock_dialog.return_value = ("", "")

            controller.browse_vram_file()

            # Check initial directory was set
            args = mock_dialog.call_args[0]
            assert args[2] == str(Path(temp_files["vram"]).parent)


@pytest.mark.unit
class TestPNGValidation:
    """Test PNG validation functionality"""

    def test_validate_png_valid(self, controller, temp_files):
        """Test validating a valid PNG"""
        # Already mocked in fixture to return (True, [])
        controller.validate_png(temp_files["png"])

        controller.view.set_validation_text.assert_called_once_with(
            "✓ PNG is valid for SNES conversion", True
        )

    def test_validate_png_invalid(self, controller, temp_files):
        """Test validating an invalid PNG"""
        issues = ["Width must be multiple of 8", "Too many colors"]
        # Change the mock return value for this test
        controller.model.validate_png.return_value = (False, issues)

        controller.validate_png(temp_files["png"])

        controller.view.set_validation_text.assert_called_once_with(
            "✗ Issues found:\nWidth must be multiple of 8\nToo many colors", False
        )

    def test_validate_png_nonexistent(self, controller):
        """Test validating non-existent PNG"""
        controller.validate_png("/nonexistent/file.png")

        # Should not call model validation
        controller.model.validate_png.assert_not_called()
        controller.view.set_validation_text.assert_not_called()


@pytest.mark.unit
class TestInjectionValidation:
    """Test injection parameter validation"""

    def test_inject_sprites_no_png_file(self, controller, mock_view):
        """Test injection with missing PNG file"""
        mock_view.get_injection_params.return_value = {
            "png_file": "",
            "vram_file": "/some/vram.dmp",
            "offset": 0xC000,
            "output_file": "",
        }

        with patch.object(QMessageBox, "warning") as mock_warning:
            controller.inject_sprites()

            # Verify warning was shown
            mock_warning.assert_called_once()
            args = mock_warning.call_args[0]
            assert args[1] == "Error"
            assert "valid PNG file" in args[2]

            # Verify injection didn't proceed
            mock_view.clear_output.assert_not_called()
            assert controller.inject_worker is None

    def test_inject_sprites_nonexistent_png(self, controller, mock_view):
        """Test injection with non-existent PNG file"""
        mock_view.get_injection_params.return_value = {
            "png_file": "/nonexistent/file.png",
            "vram_file": "/some/vram.dmp",
            "offset": 0xC000,
            "output_file": "",
        }

        with patch.object(QMessageBox, "warning") as mock_warning:
            controller.inject_sprites()

            mock_warning.assert_called_once()
            assert "valid PNG file" in mock_warning.call_args[0][2]

    def test_inject_sprites_no_vram_file(self, controller, mock_view, temp_files):
        """Test injection with missing VRAM file"""
        mock_view.get_injection_params.return_value = {
            "png_file": temp_files["png"],
            "vram_file": "",
            "offset": 0xC000,
            "output_file": "",
        }

        with patch.object(QMessageBox, "warning") as mock_warning:
            controller.inject_sprites()

            # Verify warning was shown
            mock_warning.assert_called_once()
            args = mock_warning.call_args[0]
            assert args[1] == "Error"
            assert "valid VRAM file" in args[2]

    def test_inject_sprites_nonexistent_vram(self, controller, mock_view, temp_files):
        """Test injection with non-existent VRAM file"""
        mock_view.get_injection_params.return_value = {
            "png_file": temp_files["png"],
            "vram_file": "/nonexistent/vram.dmp",
            "offset": 0xC000,
            "output_file": "",
        }

        with patch.object(QMessageBox, "warning") as mock_warning:
            controller.inject_sprites()

            mock_warning.assert_called_once()
            assert "valid VRAM file" in mock_warning.call_args[0][2]


@pytest.mark.unit
class TestInjectionProcess:
    """Test the injection process"""

    def test_successful_injection_default_output(
        self, controller, mock_view, temp_files
    ):
        """Test successful injection with default output filename"""
        params = {
            "png_file": temp_files["png"],
            "vram_file": temp_files["vram"],
            "offset": 0xC000,
            "output_file": "",
        }
        mock_view.get_injection_params.return_value = params

        # Mock the worker
        with patch(
            "sprite_editor.controllers.inject_controller.InjectWorker"
        ) as mock_worker_class:
            mock_worker = MagicMock()
            mock_worker_class.return_value = mock_worker

            controller.inject_sprites()

            # Verify worker was created with correct parameters
            # Default output should be in same directory as VRAM
            expected_output = os.path.join(
                os.path.dirname(temp_files["vram"]), "VRAM_edited.dmp"
            )
            mock_worker_class.assert_called_once_with(
                temp_files["png"], temp_files["vram"], 0xC000, expected_output
            )

            # Verify UI updates
            mock_view.clear_output.assert_called_once()
            mock_view.append_output.assert_called_with("Starting injection...")
            mock_view.set_inject_enabled.assert_called_with(False)

            # Verify worker signals were connected
            assert mock_worker.progress.connect.called
            assert mock_worker.finished.connect.called
            assert mock_worker.error.connect.called

            # Verify worker was started
            mock_worker.start.assert_called_once()

    def test_successful_injection_custom_output(
        self, controller, mock_view, temp_files
    ):
        """Test successful injection with custom output filename"""
        custom_output = os.path.join(temp_files["dir"], "custom_output.dmp")
        params = {
            "png_file": temp_files["png"],
            "vram_file": temp_files["vram"],
            "offset": 0xC000,
            "output_file": custom_output,
        }
        mock_view.get_injection_params.return_value = params

        with patch(
            "sprite_editor.controllers.inject_controller.InjectWorker"
        ) as mock_worker_class:
            mock_worker = MagicMock()
            mock_worker_class.return_value = mock_worker

            controller.inject_sprites()

            # Verify worker was created with custom output path
            mock_worker_class.assert_called_once_with(
                temp_files["png"], temp_files["vram"], 0xC000, custom_output
            )

    def test_injection_progress_callback(self, controller, mock_view):
        """Test handling injection progress updates"""
        controller.on_inject_progress("Converting tile 25/50")

        mock_view.append_output.assert_called_once_with("Converting tile 25/50")

    def test_injection_finished_callback(self, controller, mock_view):
        """Test handling successful injection completion"""
        output_file = "/path/to/output.dmp"

        with patch.object(QMessageBox, "information") as mock_info:
            controller.on_inject_finished(output_file)

            # Verify UI was re-enabled
            mock_view.set_inject_enabled.assert_called_once_with(True)

            # Verify output messages
            mock_view.append_output.assert_any_call(
                f"\nSuccess! Created: {output_file}"
            )
            mock_view.append_output.assert_any_call(
                "You can now load this file in your emulator"
            )

            # Verify success dialog
            mock_info.assert_called_once()
            args = mock_info.call_args[0]
            assert args[1] == "Success"
            assert output_file in args[2]

            # Verify project was marked as modified
            controller.project_model.mark_modified.assert_called_once()

    def test_injection_error_callback(self, controller, mock_view):
        """Test handling injection error"""
        error_msg = "PNG dimensions not compatible"

        with patch.object(QMessageBox, "critical") as mock_critical:
            controller.on_inject_error(error_msg)

            # Verify UI was re-enabled
            mock_view.set_inject_enabled.assert_called_once_with(True)

            # Verify error was logged
            mock_view.append_output.assert_called_once_with(f"\nError: {error_msg}")

            # Verify error dialog was shown
            mock_critical.assert_called_once()
            args = mock_critical.call_args[0]
            assert args[1] == "Injection Error"
            assert args[2] == error_msg
