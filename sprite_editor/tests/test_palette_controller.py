#!/usr/bin/env python3
"""
Comprehensive tests for palette controller
Tests palette management functionality with minimal mocking
"""

import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from PIL import Image
from PyQt6.QtWidgets import QFileDialog, QMessageBox

from sprite_editor.controllers.palette_controller import PaletteController
from sprite_editor.models.palette_model import PaletteModel
from sprite_editor.models.project_model import ProjectModel
from sprite_editor.models.sprite_model import SpriteModel


@pytest.fixture
def models(tmp_path):
    """Create real model instances"""
    sprite_model = SpriteModel()
    palette_model = PaletteModel()
    project_model = ProjectModel()

    # Create test CGRAM file
    cgram_file = tmp_path / "test.cgram"
    # Create a simple CGRAM with 16 palettes (512 bytes)
    cgram_data = bytearray()
    for i in range(16):  # 16 palettes
        for j in range(16):  # 16 colors per palette
            # Simple gradient for each palette
            color = (i * 16 + j) & 0x7FFF
            cgram_data.extend([color & 0xFF, (color >> 8) & 0xFF])
    cgram_file.write_bytes(cgram_data)

    return sprite_model, palette_model, project_model, str(cgram_file)


@pytest.fixture
def mock_view():
    """Create mock palette view"""
    view = MagicMock()

    # Add signal mocks
    view.browse_oam_requested = MagicMock()
    view.generate_preview_requested = MagicMock()
    view.palette_selected = MagicMock()

    # Add method mocks
    view.set_oam_file = MagicMock()
    view.get_preview_size = MagicMock(return_value=16)  # 16 tiles
    view.set_single_image_all_palettes = MagicMock()
    view.set_oam_statistics = MagicMock()

    return view


@pytest.fixture
def controller(models, mock_view):
    """Create palette controller instance"""
    sprite_model, palette_model, project_model, _ = models
    return PaletteController(sprite_model, palette_model, project_model, mock_view)
    # Don't call connect_signals() - it's automatically called in BaseController.__init__


@pytest.fixture
def temp_files(tmp_path):
    """Create temporary test files"""
    # Create test OAM file
    oam_file = tmp_path / "test.oam"
    # Simple OAM data (128 sprites * 4 bytes each = 512 bytes)
    oam_data = bytearray()
    for i in range(128):
        # X pos, Y pos, Tile index, Attributes (palette in bits 1-3)
        oam_data.extend([i & 0xFF, (i >> 1) & 0xFF, i & 0xFF, (i % 8) << 1])
    oam_file.write_bytes(oam_data)

    # Create test VRAM file
    vram_file = tmp_path / "test.vram"
    vram_file.write_bytes(b"\x00" * 0x10000)  # 64KB

    return {"oam": str(oam_file), "vram": str(vram_file), "dir": str(tmp_path)}


@pytest.mark.unit
class TestPaletteControllerInitialization:
    """Test controller initialization"""

    def test_controller_creation(self, models, mock_view):
        """Test creating palette controller"""
        sprite_model, palette_model, project_model, _ = models
        controller = PaletteController(
            sprite_model, palette_model, project_model, mock_view
        )

        assert controller.model == palette_model
        assert controller.sprite_model == sprite_model
        assert controller.project_model == project_model
        assert controller.view == mock_view

    def test_signal_connections(self, controller, mock_view):
        """Test signal connections are established"""
        # Check view signal connections
        assert mock_view.browse_oam_requested.connect.called
        assert mock_view.generate_preview_requested.connect.called
        assert mock_view.palette_selected.connect.called


@pytest.mark.unit
class TestOAMFileOperations:
    """Test OAM file operations"""

    def test_browse_oam_file_selected(self, controller, temp_files):
        """Test browsing and selecting OAM file"""
        with patch.object(QFileDialog, "getOpenFileName") as mock_dialog:
            mock_dialog.return_value = (temp_files["oam"], "Dump Files (*.dmp)")

            # Mock load_oam_mapping to return True
            controller.sprite_model.load_oam_mapping = MagicMock(return_value=True)

            with patch.object(QMessageBox, "information") as mock_info:
                controller.browse_oam_file()

                # Verify dialog was called
                mock_dialog.assert_called_once()
                args = mock_dialog.call_args[0]
                assert args[1] == "Select OAM Dump"

                # Verify model was updated
                assert controller.sprite_model.oam_file == temp_files["oam"]

                # Verify recent file was added
                controller.project_model.add_recent_file = MagicMock()
                controller.browse_oam_file()
                controller.project_model.add_recent_file.assert_called()

                # Verify success message
                mock_info.assert_called()
                assert "Success" in str(mock_info.call_args)

    def test_browse_oam_file_cancelled(self, controller):
        """Test cancelling OAM file dialog"""
        with patch.object(QFileDialog, "getOpenFileName") as mock_dialog:
            mock_dialog.return_value = ("", "")

            controller.browse_oam_file()

            # Model should not be updated
            assert controller.sprite_model.oam_file == ""

    def test_browse_oam_file_load_failure(self, controller, temp_files):
        """Test OAM file loading failure"""
        with patch.object(QFileDialog, "getOpenFileName") as mock_dialog:
            mock_dialog.return_value = (temp_files["oam"], "Dump Files (*.dmp)")

            # Mock load_oam_mapping to return False
            controller.sprite_model.load_oam_mapping = MagicMock(return_value=False)

            with patch.object(QMessageBox, "warning") as mock_warning:
                controller.browse_oam_file()

                # Verify warning was shown
                mock_warning.assert_called_once()
                assert "Error" in str(mock_warning.call_args)
                assert "Failed to load OAM data" in str(mock_warning.call_args)

    def test_browse_oam_with_existing_file(self, controller, temp_files):
        """Test browsing with existing OAM file sets initial directory"""
        # Set existing file
        controller.sprite_model.oam_file = temp_files["oam"]

        with patch.object(QFileDialog, "getOpenFileName") as mock_dialog:
            mock_dialog.return_value = ("", "")

            controller.browse_oam_file()

            # Check initial directory was set
            args = mock_dialog.call_args[0]
            assert args[2] == str(Path(temp_files["oam"]).parent)


@pytest.mark.unit
class TestPaletteLoading:
    """Test palette loading functionality"""

    def test_load_palettes_with_cgram(self, controller, models):
        """Test loading palettes when CGRAM file exists"""
        _, _, _, cgram_file = models
        controller.sprite_model.cgram_file = cgram_file

        result = controller.load_palettes()

        # Should return True (palettes loaded)
        assert result

        # Verify palettes were loaded (load_palettes_from_cgram returns count)
        assert len(controller.model.get_all_palettes()) > 0

    def test_load_palettes_no_cgram(self, controller):
        """Test loading palettes when no CGRAM file"""
        controller.sprite_model.cgram_file = ""

        result = controller.load_palettes()

        # Should return False
        assert not result


@pytest.mark.unit
class TestMultiPalettePreview:
    """Test multi-palette preview generation"""

    def test_generate_preview_no_vram(self, controller, mock_view):
        """Test generating preview without VRAM file"""
        controller.sprite_model.vram_file = ""

        with patch.object(QMessageBox, "warning") as mock_warning:
            controller.generate_multi_palette_preview()

            # Should show warning
            mock_warning.assert_called_once()
            args = mock_warning.call_args[0]
            assert args[1] == "Error"
            assert "load a VRAM file" in args[2]

    def test_generate_preview_no_cgram(self, controller, mock_view, temp_files):
        """Test generating preview without CGRAM file"""
        controller.sprite_model.vram_file = temp_files["vram"]
        controller.sprite_model.cgram_file = ""

        with patch.object(QMessageBox, "warning") as mock_warning:
            controller.generate_multi_palette_preview()

            # Should show warning
            mock_warning.assert_called_once()
            args = mock_warning.call_args[0]
            assert args[1] == "Error"
            assert "load a CGRAM file" in args[2]

    def test_generate_preview_success(self, controller, mock_view, temp_files, models):
        """Test successful preview generation"""
        _, _, _, cgram_file = models
        controller.sprite_model.vram_file = temp_files["vram"]
        controller.sprite_model.cgram_file = cgram_file
        controller.sprite_model.extraction_offset = 0xC000
        controller.sprite_model.tiles_per_row = 16

        # Mock the core extractor
        mock_core = MagicMock()
        mock_core.extract_sprites = MagicMock(
            return_value=(Image.new("P", (128, 128)), 256)
        )
        mock_core.oam_mapper = None
        controller.sprite_model.core = mock_core

        with patch.object(QMessageBox, "information") as mock_info:
            controller.generate_multi_palette_preview()

            # Verify extraction was called
            mock_core.extract_sprites.assert_called_once()
            args = mock_core.extract_sprites.call_args[0]
            assert args[0] == temp_files["vram"]
            assert args[1] == 0xC000
            assert args[2] == 16 * 32  # preview_tiles * 32
            assert args[3] == 8  # min(8, tiles_per_row)

            # Verify palettes were loaded
            assert len(controller.model.get_all_palettes()) > 0

            # Verify view was updated
            mock_view.set_single_image_all_palettes.assert_called_once()

            # Verify success message
            mock_info.assert_called_once()
            assert "Success" in str(mock_info.call_args)
            assert "256 tiles" in str(mock_info.call_args)

    def test_generate_preview_with_oam_stats(
        self, controller, mock_view, temp_files, models
    ):
        """Test preview generation with OAM statistics"""
        _, _, _, cgram_file = models
        controller.sprite_model.vram_file = temp_files["vram"]
        controller.sprite_model.cgram_file = cgram_file

        # Mock the core with OAM mapper
        mock_core = MagicMock()
        mock_core.extract_sprites = MagicMock(
            return_value=(Image.new("P", (128, 128)), 256)
        )
        mock_oam_mapper = MagicMock()
        # Return the format that set_oam_statistics expects - direct palette: count mapping
        mock_oam_mapper.get_palette_usage_stats = MagicMock(
            return_value={0: 10, 1: 20, 2: 15}
        )
        mock_core.oam_mapper = mock_oam_mapper
        controller.sprite_model.core = mock_core

        with patch.object(QMessageBox, "information"):
            controller.generate_multi_palette_preview()

            # Verify OAM stats were retrieved and set
            mock_oam_mapper.get_palette_usage_stats.assert_called_once()
            controller.model.set_oam_statistics = MagicMock()

            # Verify stats were set on the model
            assert mock_oam_mapper.get_palette_usage_stats.called

            # Verify view was updated with stats
            assert mock_view.set_oam_statistics.call_count >= 1

    def test_generate_preview_exception(
        self, controller, mock_view, temp_files, models
    ):
        """Test preview generation with exception"""
        _, _, _, cgram_file = models
        controller.sprite_model.vram_file = temp_files["vram"]
        controller.sprite_model.cgram_file = cgram_file

        # Mock the core to raise exception
        mock_core = MagicMock()
        mock_core.extract_sprites = MagicMock(side_effect=Exception("Test error"))
        controller.sprite_model.core = mock_core

        with patch.object(QMessageBox, "critical") as mock_critical:
            controller.generate_multi_palette_preview()

            # Should show error
            mock_critical.assert_called_once()
            args = mock_critical.call_args[0]
            assert args[1] == "Error"
            assert "Test error" in args[2]


@pytest.mark.unit
class TestPaletteSelection:
    """Test palette selection handling"""

    def test_on_palette_selected_with_image(self, controller):
        """Test palette selection when image exists"""
        # Create test image
        test_image = Image.new("P", (128, 128))
        controller.sprite_model.current_image = test_image

        # Mock apply_palette_to_image
        controller.model.apply_palette_to_image = MagicMock(return_value=True)

        controller.on_palette_selected(5)

        # Verify palette was applied to the model (not palette_model)
        controller.model.apply_palette_to_image.assert_called_once_with(test_image, 5)

    def test_on_palette_selected_no_image(self, controller):
        """Test palette selection when no image exists"""
        controller.sprite_model.current_image = None

        # Mock apply_palette_to_image
        controller.model.apply_palette_to_image = MagicMock()

        controller.on_palette_selected(5)

        # Should not try to apply palette
        controller.model.apply_palette_to_image.assert_not_called()

    def test_on_palette_selected_apply_fails(self, controller):
        """Test palette selection when apply fails"""
        test_image = Image.new("P", (128, 128))
        controller.sprite_model.current_image = test_image

        # Mock apply_palette_to_image to return False
        controller.model.apply_palette_to_image = MagicMock(return_value=False)

        controller.on_palette_selected(5)

        # Verify palette application was attempted
        controller.model.apply_palette_to_image.assert_called_once_with(test_image, 5)


@pytest.mark.unit
class TestPaletteExport:
    """Test palette export functionality"""

    def test_export_palette_act_format(self, controller, mock_view, tmp_path):
        """Test exporting palette in ACT format"""
        output_file = str(tmp_path / "test_palette.act")

        with patch.object(QFileDialog, "getSaveFileName") as mock_dialog:
            mock_dialog.return_value = (output_file, "Adobe Color Table (*.act)")

            # Mock export_palette to return binary data
            test_data = b"\x00\x11\x22" * 256  # 768 bytes
            controller.model.export_palette = MagicMock(return_value=test_data)

            with patch.object(QMessageBox, "information") as mock_info:
                controller.export_palette(3, "act")

                # Verify dialog was shown
                mock_dialog.assert_called_once()
                args = mock_dialog.call_args[0]
                assert args[1] == "Export Palette"
                assert "palette_3.act" in args[2]

                # Verify export was called
                controller.model.export_palette.assert_called_once_with(3, "act")

                # Verify file was written
                assert os.path.exists(output_file)
                with open(output_file, "rb") as f:
                    assert f.read() == test_data

                # Verify success message
                mock_info.assert_called_once()
                assert "Success" in str(mock_info.call_args)

    def test_export_palette_pal_format(self, controller, mock_view, tmp_path):
        """Test exporting palette in PAL format"""
        output_file = str(tmp_path / "test_palette.pal")

        with patch.object(QFileDialog, "getSaveFileName") as mock_dialog:
            mock_dialog.return_value = (output_file, "JASC Palette (*.pal)")

            # Mock export_palette to return text data
            test_data = "JASC-PAL\n0100\n256\n0 0 0\n16 16 16\n"
            controller.model.export_palette = MagicMock(return_value=test_data)

            with patch.object(QMessageBox, "information"):
                controller.export_palette(5, "pal")

            # Verify file was written as text
            assert os.path.exists(output_file)
            with open(output_file) as f:
                assert f.read() == test_data

    def test_export_palette_cancelled(self, controller, mock_view):
        """Test cancelling palette export"""
        with patch.object(QFileDialog, "getSaveFileName") as mock_dialog:
            mock_dialog.return_value = ("", "")

            controller.export_palette(3, "act")

            # Model method should not be called
            controller.model.export_palette = MagicMock()
            controller.export_palette(3, "act")
            # Note: export_palette is not called because dialog was cancelled

    def test_export_palette_failure(self, controller, mock_view):
        """Test palette export failure"""
        with patch.object(QFileDialog, "getSaveFileName") as mock_dialog:
            mock_dialog.return_value = ("/tmp/test.act", "Adobe Color Table (*.act)")

            # Mock export_palette to return None (failure)
            controller.model.export_palette = MagicMock(return_value=None)

            with patch.object(QMessageBox, "warning") as mock_warning:
                controller.export_palette(3, "act")

                # Should show warning
                mock_warning.assert_called_once()
                assert "Error" in str(mock_warning.call_args)
                assert "Failed to export palette" in str(mock_warning.call_args)


@pytest.mark.integration
class TestPaletteControllerIntegration:
    """Integration tests for PaletteController"""

    def test_complete_oam_workflow(self, controller, temp_files):
        """Test complete OAM loading workflow"""
        # Mock necessary methods
        controller.sprite_model.load_oam_mapping = MagicMock(return_value=True)
        controller.project_model.add_recent_file = MagicMock()

        with patch.object(QFileDialog, "getOpenFileName") as mock_dialog:
            mock_dialog.return_value = (temp_files["oam"], "Dump Files (*.dmp)")

            with patch.object(QMessageBox, "information"):
                controller.browse_oam_file()

        # Verify complete workflow
        assert controller.sprite_model.oam_file == temp_files["oam"]
        controller.sprite_model.load_oam_mapping.assert_called_once()
        controller.project_model.add_recent_file.assert_called_with(
            temp_files["oam"], "oam"
        )

    def test_signal_connections_workflow(self, models, mock_view):
        """Test signal connections are properly established"""
        sprite_model, palette_model, project_model, _ = models

        # Track signal connections
        connections = []

        def track_connection(signal_name):
            def wrapper(*args):
                connections.append(signal_name)

            return wrapper

        # Replace connect methods to track calls
        mock_view.browse_oam_requested.connect = track_connection("browse_oam")
        mock_view.generate_preview_requested.connect = track_connection(
            "generate_preview"
        )
        mock_view.palette_selected.connect = track_connection("palette_selected")

        # Create controller - signals are connected automatically in BaseController.__init__
        PaletteController(sprite_model, palette_model, project_model, mock_view)

        # Verify all signals were connected
        assert "browse_oam" in connections
        assert "generate_preview" in connections
        assert "palette_selected" in connections
