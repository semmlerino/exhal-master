#!/usr/bin/env python3
"""
Test suite for Menu Action Handlers
Tests file operations, save/load workflows, and user interactions
"""

import os
import tempfile
from unittest.mock import patch

import numpy as np
import pytest
from PIL import Image
from PyQt6.QtWidgets import QApplication, QMessageBox

from indexed_pixel_editor import IndexedPixelEditor


class TestMenuActions:
    """Test cases for menu action handlers"""

    @pytest.fixture
    def qapp(self):
        """Ensure QApplication exists"""
        app = QApplication.instance()
        if not app:
            app = QApplication([])
        return app

    @pytest.fixture
    def editor(self, qapp, qtbot):
        """Create editor with minimal real components"""
        with patch.object(IndexedPixelEditor, "handle_startup"):
            editor = IndexedPixelEditor()
            qtbot.addWidget(editor)
            # Initialize with a small image
            editor.canvas.new_image(8, 8)
            return editor

    @pytest.fixture
    def temp_image(self):
        """Create a temporary indexed PNG file"""
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            # Create simple indexed image
            data = np.arange(64).reshape(8, 8) % 16
            img = Image.fromarray(data.astype(np.uint8), mode="P")
            # Set palette
            palette = []
            for i in range(16):
                gray = i * 17
                palette.extend([gray, gray, gray])
            while len(palette) < 768:
                palette.extend([0, 0, 0])
            img.putpalette(palette)
            img.save(f.name)
            yield f.name
        os.unlink(f.name)

    def test_new_file_no_changes(self, editor, qtbot):
        """Test creating new file when no changes made"""
        editor.modified = False

        editor.new_file()

        assert editor.canvas.image_data.shape == (8, 8)
        assert np.all(editor.canvas.image_data == 0)
        assert editor.current_file is None
        assert not editor.modified

    def test_new_file_with_save_prompt_save(self, editor, qtbot):
        """Test new file when current file has changes - user saves"""
        editor.modified = True
        editor.current_file = "test.png"

        with patch.object(QMessageBox, "question", return_value=QMessageBox.StandardButton.Save):
            with patch.object(editor, "save_file", return_value=True) as mock_save:
                editor.new_file()

                mock_save.assert_called_once()
                assert editor.canvas.image_data.shape == (8, 8)
                assert not editor.modified

    def test_new_file_with_save_prompt_discard(self, editor, qtbot):
        """Test new file when current file has changes - user discards"""
        editor.modified = True

        with patch.object(QMessageBox, "question", return_value=QMessageBox.StandardButton.Discard):
            editor.new_file()

            assert editor.canvas.image_data.shape == (8, 8)
            assert not editor.modified

    def test_new_file_with_save_prompt_cancel(self, editor, qtbot):
        """Test new file when current file has changes - user cancels"""
        editor.modified = True
        original_data = editor.canvas.image_data.copy()

        with patch.object(QMessageBox, "question", return_value=QMessageBox.StandardButton.Cancel):
            editor.new_file()

            # Should not create new file
            assert np.array_equal(editor.canvas.image_data, original_data)
            assert editor.modified  # Still modified

    @patch("indexed_pixel_editor.QFileDialog.getOpenFileName")
    def test_open_file_dialog_cancelled(self, mock_dialog, editor, qtbot):
        """Test canceling open file dialog"""
        mock_dialog.return_value = ("", "")

        editor.open_file()

        # Nothing should change
        assert editor.current_file is None

    @patch("indexed_pixel_editor.QFileDialog.getOpenFileName")
    def test_open_file_success(self, mock_dialog, editor, temp_image, qtbot):
        """Test successfully opening a file"""
        mock_dialog.return_value = (temp_image, "PNG Files (*.png)")

        editor.open_file()

        assert editor.current_file == temp_image
        assert editor.canvas.image_data is not None
        assert not editor.modified

    def test_save_file_with_current_path(self, editor, qtbot):
        """Test saving when current_file is set"""
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            temp_path = f.name

        try:
            editor.current_file = temp_path
            editor.canvas.current_color = 5
            editor.canvas.draw_pixel(2, 2)
            editor.modified = True

            result = editor.save_file()

            assert result is True
            assert os.path.exists(temp_path)
            assert not editor.modified

            # Verify file was saved correctly
            saved_img = Image.open(temp_path)
            saved_data = np.array(saved_img)
            assert saved_data[2, 2] == 5
        finally:
            os.unlink(temp_path)

    def test_save_file_without_current_path(self, editor, qtbot):
        """Test saving when current_file is None (triggers save as)"""
        editor.current_file = None

        with patch.object(editor, "save_file_as") as mock_save_as:
            editor.save_file()
            mock_save_as.assert_called_once()

    @patch("indexed_pixel_editor.QFileDialog.getSaveFileName")
    def test_save_file_as_with_extension(self, mock_dialog, editor, qtbot):
        """Test save as with filename that has extension"""
        with tempfile.TemporaryDirectory() as temp_dir:
            save_path = os.path.join(temp_dir, "test.png")
            mock_dialog.return_value = (save_path, "PNG Files (*.png)")

            editor.save_file_as()

            assert editor.current_file == save_path
            assert os.path.exists(save_path)
            assert not editor.modified

    @patch("indexed_pixel_editor.QFileDialog.getSaveFileName")
    def test_save_file_as_without_extension(self, mock_dialog, editor, qtbot):
        """Test save as with filename without extension"""
        with tempfile.TemporaryDirectory() as temp_dir:
            save_path = os.path.join(temp_dir, "test")
            mock_dialog.return_value = (save_path, "PNG Files (*.png)")

            editor.save_file_as()

            # Should add .png extension
            expected_path = save_path + ".png"
            assert editor.current_file == expected_path
            assert os.path.exists(expected_path)

    def test_save_to_file_error_handling(self, editor, qtbot):
        """Test save error handling"""
        # Try to save to invalid path
        with patch.object(QMessageBox, "critical") as mock_error:
            editor.save_to_file("/invalid/path/file.png")
            mock_error.assert_called_once()

    def test_load_file_by_path_indexed_png(self, editor, temp_image, qtbot):
        """Test loading valid indexed PNG"""
        result = editor.load_file_by_path(temp_image)

        assert result is True
        assert editor.current_file == temp_image
        assert editor.canvas.image_data.shape == (8, 8)
        assert not editor.modified

    def test_load_file_by_path_rgb_png(self, editor, qtbot):
        """Test loading non-indexed PNG (should fail)"""
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            # Create RGB image
            rgb_img = Image.new("RGB", (8, 8), color=(255, 0, 0))
            rgb_img.save(f.name)
            temp_path = f.name

        try:
            with patch.object(QMessageBox, "warning") as mock_warning:
                result = editor.load_file_by_path(temp_path)

                assert result is False
                mock_warning.assert_called_once()
                assert "indexed color mode" in str(mock_warning.call_args)
        finally:
            os.unlink(temp_path)

    def test_load_file_with_metadata(self, editor, qtbot):
        """Test loading file with associated metadata"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create image file
            img_path = os.path.join(temp_dir, "sprite.png")
            data = np.zeros((8, 8), dtype=np.uint8)
            img = Image.fromarray(data, mode="P")
            img.save(img_path)

            # Create metadata file
            metadata_path = os.path.join(temp_dir, "sprite_metadata.json")
            metadata = {
                "palette_colors": {
                    "8": [[255, 0, 0]] * 16
                }
            }
            import json
            with open(metadata_path, "w") as f:
                json.dump(metadata, f)

            # Mock the palette loading question
            with patch.object(QMessageBox, "question", return_value=QMessageBox.StandardButton.No):
                result = editor.load_file_by_path(img_path)

            assert result is True
            assert editor.metadata is not None

    def test_check_save_unmodified(self, editor):
        """Test check_save returns True when unmodified"""
        editor.modified = False
        result = editor.check_save()
        assert result is True

    def test_check_save_modified_save(self, editor):
        """Test check_save when modified - user saves"""
        editor.modified = True

        with patch.object(QMessageBox, "question", return_value=QMessageBox.StandardButton.Save):
            with patch.object(editor, "save_file", return_value=True) as mock_save:
                result = editor.check_save()

                mock_save.assert_called_once()
                assert result is True

    def test_check_save_modified_discard(self, editor):
        """Test check_save when modified - user discards"""
        editor.modified = True

        with patch.object(QMessageBox, "question", return_value=QMessageBox.StandardButton.Discard):
            result = editor.check_save()
            assert result is True

    def test_check_save_modified_cancel(self, editor):
        """Test check_save when modified - user cancels"""
        editor.modified = True

        with patch.object(QMessageBox, "question", return_value=QMessageBox.StandardButton.Cancel):
            result = editor.check_save()
            assert result is False

    @patch("indexed_pixel_editor.QFileDialog.getOpenFileName")
    def test_load_grayscale_with_palette(self, mock_dialog, editor, qtbot):
        """Test loading grayscale image with palette workflow"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create test files
            img_path = os.path.join(temp_dir, "test.png")
            pal_path = os.path.join(temp_dir, "test.pal.json")

            # Create grayscale image
            data = np.zeros((8, 8), dtype=np.uint8)
            img = Image.fromarray(data, mode="P")
            img.save(img_path)

            # Create palette file
            import json
            palette_data = {
                "palette": {
                    "name": "Test",
                    "colors": [[255, 0, 0]] * 16
                }
            }
            with open(pal_path, "w") as f:
                json.dump(palette_data, f)

            # Mock dialog returns
            mock_dialog.side_effect = [
                (img_path, "PNG Files (*.png)"),  # First call for image
                (pal_path, "Palette Files (*.pal.json)")  # Second call for palette
            ]

            editor.load_grayscale_with_palette()

            assert editor.current_file == img_path
            assert editor.current_palette_file == pal_path
