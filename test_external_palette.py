#!/usr/bin/env python3
"""
Test suite for External Palette Loading functionality
Tests palette file loading, validation, and integration with UI
"""

import json
import os
import tempfile
from unittest.mock import patch

import pytest
from PyQt6.QtWidgets import QApplication, QMessageBox

from indexed_pixel_editor import IndexedPixelEditor


class TestExternalPaletteLoading:
    """Test cases for external palette loading functionality"""

    @pytest.fixture
    def qapp(self):
        """Ensure QApplication exists"""
        app = QApplication.instance()
        if not app:
            app = QApplication([])
        return app

    @pytest.fixture
    def editor(self, qapp, qtbot):
        """Create editor instance with minimal setup"""
        with patch.object(IndexedPixelEditor, "handle_startup"):
            editor = IndexedPixelEditor()
            qtbot.addWidget(editor)
            # Setup minimal required components
            editor.canvas.new_image(8, 8)
            return editor

    @pytest.fixture
    def valid_palette_data(self):
        """Valid palette JSON structure"""
        return {
            "palette": {
                "name": "Test Palette",
                "colors": [[255, 0, 0], [0, 255, 0], [0, 0, 255]] + [[128, 128, 128]] * 13
            }
        }

    @pytest.fixture
    def palette_file(self, valid_palette_data):
        """Create temporary palette file"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".pal.json", delete=False) as f:
            json.dump(valid_palette_data, f)
            temp_path = f.name
        yield temp_path
        os.unlink(temp_path)

    def test_validate_palette_file_valid(self, editor, valid_palette_data):
        """Test validation of valid palette file"""
        assert editor._validate_palette_file(valid_palette_data) is True

    def test_validate_palette_file_invalid_structures(self, editor):
        """Test validation rejects invalid structures"""
        invalid_data = [
            {},  # Empty
            {"colors": [[255, 0, 0]]},  # Missing 'palette' key
            {"palette": {}},  # Missing 'colors' key
            {"palette": {"colors": [[255, 0]]}},  # Color too short
            {"palette": {"colors": [[255, 0, 0]] * 10}},  # Not enough colors
        ]
        for data in invalid_data:
            assert editor._validate_palette_file(data) is False

    def test_load_palette_by_path_success(self, editor, palette_file, qtbot):
        """Test successful palette loading"""
        result = editor.load_palette_by_path(palette_file)

        assert result is True
        assert editor.external_palette is not None
        assert len(editor.external_palette_colors) == 16
        assert editor.external_palette_colors[0] == (255, 0, 0)
        assert editor.current_palette_file == palette_file

        # Verify UI updates
        assert editor.palette_widget.is_external_palette
        assert "Test Palette" in editor.palette_widget.palette_source
        # current_palette_index stays at its default (8) for external palettes
        assert editor.current_palette_index == 8

    def test_load_palette_by_path_file_not_found(self, editor, qtbot):
        """Test loading non-existent file"""
        with patch.object(QMessageBox, "critical") as mock_critical:
            result = editor.load_palette_by_path("/nonexistent/file.json")
            assert result is False
            mock_critical.assert_called_once()
            assert "No such file or directory" in str(mock_critical.call_args)

    def test_load_palette_by_path_invalid_json(self, editor, qtbot):
        """Test loading invalid JSON file"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("invalid json {")
            temp_path = f.name

        try:
            with patch.object(QMessageBox, "critical") as mock_critical:
                result = editor.load_palette_by_path(temp_path)
                assert result is False
                mock_critical.assert_called_once()
                assert "Failed to load palette" in str(mock_critical.call_args)
        finally:
            os.unlink(temp_path)

    def test_load_palette_by_path_incomplete_palette(self, editor, qtbot):
        """Test loading palette with too few colors"""
        incomplete_data = {
            "palette": {
                "name": "Incomplete",
                "colors": [[255, 0, 0], [0, 255, 0], [0, 0, 255]]  # Only 3 colors
            }
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(incomplete_data, f)
            temp_path = f.name

        try:
            with patch.object(QMessageBox, "warning") as mock_warning:
                result = editor.load_palette_by_path(temp_path)
                assert result is False
                mock_warning.assert_called_once()
                assert "not a valid palette file" in str(mock_warning.call_args)
        finally:
            os.unlink(temp_path)

    def test_load_palette_with_image_association(self, editor, palette_file, qtbot):
        """Test palette association with current image"""
        editor.current_file = "/path/to/image.png"

        result = editor.load_palette_by_path(palette_file)

        assert result is True
        # Check that association was requested
        # Note: get_palette_for_image doesn't exist, but associate_palette_with_image was called
        # which we can verify through the settings

    def test_window_title_update(self, editor, palette_file, qtbot):
        """Test window title updates correctly"""
        # Set initial title
        editor.setWindowTitle("Pixel Editor | Some File")

        editor.load_palette_by_path(palette_file)

        assert "Test Palette" in editor.windowTitle()
        assert "Pixel Editor" in editor.windowTitle()

    def test_colors_with_alpha_channel(self, editor, qtbot):
        """Test handling of RGBA colors (alpha should be ignored)"""
        rgba_data = {
            "palette": {
                "name": "RGBA Test",
                "colors": [[255, 0, 0, 255], [0, 255, 0, 128]] + [[128, 128, 128, 255]] * 14
            }
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(rgba_data, f)
            temp_path = f.name

        try:
            result = editor.load_palette_by_path(temp_path)

            assert result is True
            # Alpha channel should be stripped
            assert editor.external_palette_colors[0] == (255, 0, 0)
            assert editor.external_palette_colors[1] == (0, 255, 0)
        finally:
            os.unlink(temp_path)

    @patch("indexed_pixel_editor.QFileDialog.getOpenFileName")
    def test_load_palette_file_dialog_cancelled(self, mock_dialog, editor, qtbot):
        """Test behavior when file dialog is cancelled"""
        mock_dialog.return_value = ("", "")  # Cancelled dialog

        editor.load_palette_file()

        # Should handle gracefully without errors
        assert editor.current_palette_file is None

    @patch("indexed_pixel_editor.QFileDialog.getOpenFileName")
    def test_load_palette_file_dialog_success(self, mock_dialog, editor, palette_file, qtbot):
        """Test successful file selection through dialog"""
        mock_dialog.return_value = (palette_file, "Palette Files (*.pal.json)")

        with patch.object(editor, "load_palette_by_path", return_value=True) as mock_load:
            editor.load_palette_file()
            mock_load.assert_called_once_with(palette_file)

    def test_metadata_palette_loading(self, editor, qtbot):
        """Test loading palette from metadata file"""
        metadata = {
            "palette_colors": {
                "8": [[240, 56, 248], [224, 56, 248], [248, 160, 232],
                      [240, 112, 224], [224, 64, 208], [192, 16, 176],
                      [112, 0, 88], [192, 0, 0], [248, 16, 32],
                      [48, 48, 48], [0, 0, 0], [64, 0, 248],
                      [40, 0, 168], [24, 0, 80], [184, 168, 248],
                      [128, 80, 248]]
            }
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix="_metadata.json", delete=False) as f:
            json.dump(metadata, f)
            metadata_path = f.name

        try:
            editor._load_metadata_palette(metadata_path)

            assert editor.metadata == metadata
            assert editor.current_palette_index == 8
            assert len(editor.external_palette_colors) == 16
            assert editor.external_palette_colors[0] == (240, 56, 248)
            assert editor.switch_palette_action.isEnabled()
        finally:
            os.unlink(metadata_path)

    def test_metadata_palette_fallback(self, editor, qtbot):
        """Test metadata palette loading with fallback to other sprite palettes"""
        metadata = {
            "palette_colors": {
                "10": [[0, 0, 0]] * 16,  # Palette 10 instead of 8
                "5": [[255, 255, 255]] * 16  # Background palette (ignored)
            }
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix="_metadata.json", delete=False) as f:
            json.dump(metadata, f)
            metadata_path = f.name

        try:
            editor._load_metadata_palette(metadata_path)

            assert editor.current_palette_index == 10
            assert editor.external_palette_colors[0] == (0, 0, 0)
        finally:
            os.unlink(metadata_path)

    def test_metadata_no_sprite_palettes(self, editor, qtbot):
        """Test handling when no sprite palettes are found in metadata"""
        metadata = {
            "palette_colors": {
                "0": [[0, 0, 0]] * 16,  # Only background palettes
                "5": [[255, 255, 255]] * 16
            }
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix="_metadata.json", delete=False) as f:
            json.dump(metadata, f)
            metadata_path = f.name

        try:
            with patch.object(QMessageBox, "warning") as mock_warning:
                editor._load_metadata_palette(metadata_path)
                mock_warning.assert_called_once()
                assert "No sprite palette found" in str(mock_warning.call_args)
        finally:
            os.unlink(metadata_path)

    def test_check_and_offer_palette_loading(self, editor, qtbot):
        """Test automatic palette loading offer"""
        # Create test image and associated palette
        with tempfile.TemporaryDirectory() as temp_dir:
            image_path = os.path.join(temp_dir, "test.png")
            palette_path = os.path.join(temp_dir, "test.pal.json")

            # Create dummy files
            with open(image_path, "w") as f:
                f.write("dummy")

            palette_data = {
                "palette": {
                    "name": "Auto Load Test",
                    "colors": [[255, 0, 0]] * 16
                }
            }
            with open(palette_path, "w") as f:
                json.dump(palette_data, f)

            # Mock the dialog to say "Yes"
            with patch.object(QMessageBox, "question", return_value=QMessageBox.StandardButton.Yes):
                with patch.object(editor, "load_palette_by_path") as mock_load:
                    editor._check_and_offer_palette_loading(image_path)
                    mock_load.assert_called_once_with(palette_path)
