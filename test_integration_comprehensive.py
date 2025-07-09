#!/usr/bin/env python3
"""
Comprehensive integration tests for IndexedPixelEditor
Tests end-to-end workflows that span multiple components
"""

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import numpy as np
import pytest
from PIL import Image
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QKeyEvent
from PyQt6.QtWidgets import QMessageBox

from indexed_pixel_editor import IndexedPixelEditor, StartupDialog


class TestApplicationLifecycle:
    """Test complete application lifecycle scenarios"""

    @pytest.fixture
    def temp_workspace(self):
        """Create a temporary workspace with settings and files"""
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            settings_dir = workspace / ".indexed_pixel_editor"
            settings_dir.mkdir()

            # Create test image
            img_path = workspace / "test_sprite.png"
            data = np.zeros((16, 16), dtype=np.uint8)
            data[5:10, 5:10] = 5  # Draw a square
            img = Image.fromarray(data, mode="P")
            palette = []
            for i in range(16):
                palette.extend([i*16, i*16, i*16])
            while len(palette) < 768:
                palette.extend([0, 0, 0])
            img.putpalette(palette)
            img.save(img_path)

            # Create palette file
            pal_path = workspace / "test_palette.pal.json"
            palette_data = {
                "palette": {
                    "name": "Test Palette",
                    "colors": [[255, 0, 0], [0, 255, 0], [0, 0, 255]] + [[128, 128, 128]] * 13
                }
            }
            with open(pal_path, "w") as f:
                json.dump(palette_data, f)

            # Create metadata file
            meta_path = workspace / "test_sprite_metadata.json"
            metadata = {
                "palette_colors": {
                    "8": [[240, 56, 248]] * 16,
                    "10": [[0, 255, 0]] * 16
                }
            }
            with open(meta_path, "w") as f:
                json.dump(metadata, f)

            yield {
                "workspace": workspace,
                "image": str(img_path),
                "palette": str(pal_path),
                "metadata": str(meta_path)
            }

    def test_first_launch_workflow(self, qapp):
        """Test first application launch with no existing settings"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Override home directory for clean settings
            with patch("pathlib.Path.home", return_value=Path(temp_dir)):
                with patch.object(IndexedPixelEditor, "handle_startup") as mock_startup:
                    editor = IndexedPixelEditor()

                    # Should create settings directory
                    settings_dir = Path(temp_dir) / ".indexed_pixel_editor"
                    assert settings_dir.exists()

                    # Should call handle_startup
                    mock_startup.assert_called_once()

                    # Settings should be empty
                    assert editor.settings.settings["recent_files"] == []
                    assert editor.settings.settings["last_file"] == ""

    def test_startup_dialog_new_file_workflow(self, qapp):
        """Test startup dialog -> new file workflow"""
        with patch.object(StartupDialog, "exec") as mock_exec:
            with patch.object(StartupDialog, "__init__", return_value=None):
                # Mock dialog to choose new file
                mock_dialog = Mock()
                mock_dialog.action = "new_file"
                mock_exec.return_value = StartupDialog.DialogCode.Accepted

                with patch("indexed_pixel_editor.StartupDialog", return_value=mock_dialog):
                    editor = IndexedPixelEditor()
                    editor.show_startup_dialog()

                    # Should have created new 8x8 image
                    assert editor.canvas.image_data is not None
                    assert editor.canvas.image_data.shape == (8, 8)
                    assert editor.current_file is None

    def test_session_persistence_workflow(self, qapp, temp_workspace):
        """Test settings persistence across sessions"""
        # First session - open and edit a file
        with patch("pathlib.Path.home", return_value=temp_workspace["workspace"].parent):
            with patch.object(IndexedPixelEditor, "handle_startup"):
                # Mock any message boxes that might appear
                with patch("indexed_pixel_editor.QMessageBox.warning"):
                    with patch("indexed_pixel_editor.QMessageBox.critical"):
                        with patch("indexed_pixel_editor.QMessageBox.question", return_value=QMessageBox.StandardButton.No):
                            editor1 = IndexedPixelEditor()

                            # Load the test file
                            result = editor1.load_file_by_path(temp_workspace["image"])
                            assert result is True, "Failed to load test image"
                            assert editor1.current_file == temp_workspace["image"], "Current file not set after loading"

                            # Make some edits
                            editor1.canvas.current_color = 7
                            editor1.canvas.draw_pixel(2, 2)

                            # Save - now we're sure current_file is set
                            editor1.save_file()

                            # Verify the file was saved (modified flag should be False)
                            assert editor1.modified is False, "File not marked as saved"

                            # Window geometry would normally be saved
                            editor1.settings.settings["window_geometry"] = {"x": 100, "y": 200}
                            editor1.settings.save_settings()

        # Second session - should remember last file
        with patch("pathlib.Path.home", return_value=temp_workspace["workspace"].parent):
            with patch.object(IndexedPixelEditor, "handle_startup"):
                editor2 = IndexedPixelEditor()

                # Should have the file in recent files
                assert temp_workspace["image"] in editor2.settings.settings["recent_files"]
                assert editor2.settings.settings["last_file"] == temp_workspace["image"]

                # Window geometry should be preserved
                assert editor2.settings.settings["window_geometry"]["x"] == 100


class TestCompleteEditingWorkflows:
    """Test complete editing workflows from start to finish"""

    def test_tool_workflow(self, qapp):
        """Test complete tool switching workflow"""
        with patch.object(IndexedPixelEditor, "handle_startup"):
            editor = IndexedPixelEditor()
            editor.canvas.new_image(16, 16)

            # Start with pencil tool
            assert editor.canvas.tool == "pencil"

            # Draw with pencil
            editor.canvas.current_color = 5
            editor.canvas.save_undo()
            editor.canvas.draw_pixel(5, 5)
            editor.canvas.draw_pixel(6, 5)
            assert editor.canvas.image_data[5, 5] == 5

            # Switch to fill tool
            editor.tool_group.button(1).click()  # Fill tool
            assert editor.canvas.tool == "fill"

            # Fill an area
            editor.canvas.save_undo()
            editor.canvas.current_color = 8
            editor.canvas.flood_fill(0, 0)
            # Should fill everything except the drawn pixels
            assert editor.canvas.image_data[0, 0] == 8
            assert editor.canvas.image_data[5, 5] == 5  # Preserved

            # Switch to picker tool
            editor.tool_group.button(2).click()  # Picker tool
            assert editor.canvas.tool == "picker"

            # Pick a color
            editor.canvas.pick_color(5, 5)
            assert editor.canvas.current_color == 5
            assert editor.palette_widget.selected_index == 5

            # Switch back to pencil
            editor.tool_group.button(0).click()
            assert editor.canvas.tool == "pencil"

    def test_undo_redo_complex_workflow(self, qapp):
        """Test undo/redo across multiple operations"""
        with patch.object(IndexedPixelEditor, "handle_startup"):
            editor = IndexedPixelEditor()
            editor.canvas.new_image(8, 8)

            # Operation 1: Draw pixels
            editor.canvas.current_color = 1
            editor.canvas.save_undo()
            editor.canvas.draw_pixel(1, 1)
            editor.canvas.draw_pixel(2, 2)

            # Operation 2: Change color and draw
            editor.canvas.current_color = 5
            editor.canvas.save_undo()
            editor.canvas.draw_pixel(3, 3)

            # Operation 3: Fill
            editor.canvas.tool = "fill"
            editor.canvas.save_undo()
            editor.canvas.flood_fill(5, 5)

            # Verify state
            assert editor.canvas.image_data[1, 1] == 1
            assert editor.canvas.image_data[3, 3] == 5
            assert editor.canvas.image_data[5, 5] == 5

            # Undo fill
            editor.canvas.undo()
            assert editor.canvas.image_data[5, 5] == 0

            # Undo second draw
            editor.canvas.undo()
            assert editor.canvas.image_data[3, 3] == 0

            # Redo second draw
            editor.canvas.redo()
            assert editor.canvas.image_data[3, 3] == 5

            # Redo fill
            editor.canvas.redo()
            assert editor.canvas.image_data[5, 5] == 5

    def test_keyboard_driven_workflow(self, qapp):
        """Test workflow using keyboard shortcuts"""
        with patch.object(IndexedPixelEditor, "handle_startup"):
            editor = IndexedPixelEditor()
            editor.canvas.new_image(8, 8)

            # Start in color mode
            assert not editor.canvas.greyscale_mode

            # Press C to toggle to grayscale
            event = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_C, Qt.KeyboardModifier.NoModifier)
            editor.keyPressEvent(event)
            assert editor.canvas.greyscale_mode

            # Draw in grayscale mode
            editor.canvas.current_color = 5
            editor.canvas.save_undo()  # Need to save state before drawing
            editor.canvas.draw_pixel(2, 2)

            # Press C again to go back to color
            editor.keyPressEvent(event)
            assert not editor.canvas.greyscale_mode

            # Test Ctrl+Z for undo (directly on canvas)
            editor.canvas.undo()
            assert editor.canvas.image_data[2, 2] == 0  # Undone

            # Test Ctrl+Y for redo (directly on canvas)
            editor.canvas.redo()
            assert editor.canvas.image_data[2, 2] == 5  # Redone


class TestPaletteWorkflows:
    """Test complete palette-related workflows"""

    @patch("indexed_pixel_editor.QFileDialog.getOpenFileName")
    def test_external_palette_loading_workflow(self, mock_dialog, qapp):
        """Test complete external palette loading workflow"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create palette file
            pal_path = os.path.join(temp_dir, "custom.pal.json")
            palette_data = {
                "palette": {
                    "name": "Custom Colors",
                    "colors": [[255, 0, 0], [0, 255, 0], [0, 0, 255]] + [[100, 100, 100]] * 13
                }
            }
            with open(pal_path, "w") as f:
                json.dump(palette_data, f)

            # Mock dialog to return our palette
            mock_dialog.return_value = (pal_path, "Palette Files (*.pal.json)")

            with patch.object(IndexedPixelEditor, "handle_startup"):
                editor = IndexedPixelEditor()
                editor.canvas.new_image(8, 8)

                # Draw with default palette
                editor.canvas.current_color = 1
                editor.canvas.draw_pixel(2, 2)

                # Load external palette through menu action
                editor.load_palette_file()

                # Verify palette loaded
                assert editor.palette_widget.is_external_palette
                assert "Custom Colors" in editor.palette_widget.palette_source
                assert editor.external_palette_colors[0] == (255, 0, 0)

                # Draw with new palette
                editor.canvas.current_color = 0
                editor.canvas.draw_pixel(3, 3)

                # Save and verify palette is preserved
                save_path = os.path.join(temp_dir, "output.png")
                editor.save_to_file(save_path)

                # Load back and check
                saved_img = Image.open(save_path)
                palette_data = saved_img.getpalette()
                assert palette_data[0:3] == [255, 0, 0]  # Red from custom palette

    def test_metadata_palette_switching_workflow(self, qapp):
        """Test complete metadata-based palette switching workflow"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create test image with metadata
            img_path = os.path.join(temp_dir, "sprite.png")
            data = np.zeros((16, 16), dtype=np.uint8)
            img = Image.fromarray(data, mode="P")
            img.save(img_path)

            # Create metadata with multiple palettes
            meta_path = os.path.join(temp_dir, "sprite_metadata.json")
            metadata = {
                "palette_colors": {
                    "8": [[240, 56, 248]] * 16,  # Pink
                    "10": [[0, 255, 0]] * 16,    # Green
                    "14": [[255, 255, 0]] * 16   # Yellow
                }
            }
            with open(meta_path, "w") as f:
                json.dump(metadata, f)

            with patch.object(IndexedPixelEditor, "handle_startup"):
                with patch("PyQt6.QtWidgets.QMessageBox.question", return_value=QMessageBox.StandardButton.No):
                    editor = IndexedPixelEditor()
                    editor.load_file_by_path(img_path)

                    # Should have loaded metadata
                    assert editor.metadata is not None
                    assert editor.current_palette_index == 8

                    # Draw with first palette
                    editor.canvas.current_color = 5
                    editor.canvas.draw_pixel(5, 5)

                    # Mock palette switcher dialog
                    with patch("indexed_pixel_editor.PaletteSwitcherDialog") as mock_dialog_class:
                        mock_dialog = Mock()
                        mock_dialog.exec.return_value = True
                        mock_dialog.get_selected_palette.return_value = (10, metadata["palette_colors"]["10"])
                        mock_dialog_class.return_value = mock_dialog

                        # Press P to open switcher
                        event = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_P, Qt.KeyboardModifier.NoModifier)
                        editor.keyPressEvent(event)

                        # Should have switched palette
                        assert editor.current_palette_index == 10

                    # Edit with new palette
                    editor.canvas.current_color = 8
                    editor.canvas.draw_pixel(8, 8)

                    # Save preserves pixel indices
                    save_path = os.path.join(temp_dir, "edited.png")
                    editor.save_to_file(save_path)

                    # Verify
                    saved_img = Image.open(save_path)
                    saved_data = np.array(saved_img)
                    assert saved_data[5, 5] == 5
                    assert saved_data[8, 8] == 8


class TestFileOperationWorkflows:
    """Test complete file operation workflows"""

    def test_save_workflow_with_confirmations(self, qapp):
        """Test save workflow with user confirmations"""
        with patch.object(IndexedPixelEditor, "handle_startup"):
            editor = IndexedPixelEditor()
            editor.canvas.new_image(8, 8)

            # Make edits
            editor.canvas.current_color = 5
            editor.canvas.draw_pixel(2, 2)
            editor.on_canvas_changed()  # Mark as modified

            assert editor.modified
            assert "*" in editor.windowTitle()

            # Try to create new file - should prompt to save
            with patch.object(QMessageBox, "question", return_value=QMessageBox.StandardButton.Save) as mock_question:
                with patch.object(editor, "save_file", return_value=True) as mock_save:
                    # Mock save_file to set modified to False
                    def mock_save_impl():
                        editor.modified = False
                        return True
                    mock_save.side_effect = mock_save_impl

                    editor.new_file()

                    # Should have asked to save
                    mock_question.assert_called_once()
                    mock_save.assert_called_once()

                    # Should have new image
                    assert editor.canvas.image_data.shape == (8, 8)
                    assert np.all(editor.canvas.image_data == 0)
                    assert not editor.modified

    @patch("indexed_pixel_editor.QFileDialog.getSaveFileName")
    def test_save_as_workflow(self, mock_dialog, qapp):
        """Test complete save as workflow"""
        with tempfile.TemporaryDirectory() as temp_dir:
            save_path = os.path.join(temp_dir, "new_sprite")  # No extension
            mock_dialog.return_value = (save_path, "PNG Files (*.png)")

            with patch.object(IndexedPixelEditor, "handle_startup"):
                editor = IndexedPixelEditor()
                editor.canvas.new_image(8, 8)

                # Draw something
                editor.canvas.current_color = 3
                editor.canvas.draw_pixel(4, 4)

                # Save as
                editor.save_file_as()

                # Should add .png extension
                expected_path = save_path + ".png"
                assert editor.current_file == expected_path
                assert os.path.exists(expected_path)
                assert not editor.modified

                # Should be in recent files
                assert expected_path in editor.settings.settings["recent_files"]

    def test_grayscale_color_mode_save_workflow(self, qapp):
        """Test saving preserves color mode correctly"""
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch.object(IndexedPixelEditor, "handle_startup"):
                editor = IndexedPixelEditor()
                editor.canvas.new_image(8, 8)

                # Start in color mode
                assert not editor.canvas.greyscale_mode

                # Draw in color mode
                editor.canvas.current_color = 5
                editor.canvas.draw_pixel(2, 2)

                # Switch to grayscale
                editor.toggle_color_mode_shortcut()
                assert editor.canvas.greyscale_mode

                # Draw in grayscale
                editor.canvas.current_color = 8
                editor.canvas.draw_pixel(4, 4)

                # Save
                save_path = os.path.join(temp_dir, "mixed_mode.png")
                editor.save_to_file(save_path)

                # Load back
                editor.load_file_by_path(save_path)

                # Pixel values should be preserved
                assert editor.canvas.image_data[2, 2] == 5
                assert editor.canvas.image_data[4, 4] == 8

                # Mode should reset to default (color)
                assert not editor.canvas.greyscale_mode


class TestErrorHandlingWorkflows:
    """Test error handling and recovery workflows"""

    def test_corrupt_file_recovery_workflow(self, qapp):
        """Test recovery from corrupt file loading"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create corrupt "PNG" file
            corrupt_path = os.path.join(temp_dir, "corrupt.png")
            with open(corrupt_path, "w") as f:
                f.write("This is not a PNG file")

            with patch.object(IndexedPixelEditor, "handle_startup"):
                with patch.object(QMessageBox, "critical") as mock_error:
                    editor = IndexedPixelEditor()

                    # Should handle error gracefully
                    success = editor.load_file_by_path(corrupt_path)
                    assert not success
                    mock_error.assert_called_once()

                    # Editor should still be functional
                    assert editor.canvas.image_data is None

                    # Should be able to create new file
                    editor.new_file()
                    assert editor.canvas.image_data is not None

    def test_save_permission_error_workflow(self, qapp):
        """Test handling save permission errors"""
        with patch.object(IndexedPixelEditor, "handle_startup"):
            editor = IndexedPixelEditor()
            editor.canvas.new_image(8, 8)

            # Try to save to read-only location
            with patch.object(QMessageBox, "critical") as mock_error:
                editor.save_to_file("/root/no_permission.png")

                # Should show error
                mock_error.assert_called_once()

                # Should still be marked as modified
                assert editor.modified

                # Editor should still be functional
                editor.canvas.current_color = 5
                editor.canvas.draw_pixel(2, 2)
                assert editor.canvas.image_data[2, 2] == 5


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
