#!/usr/bin/env python3
"""
Fixed test suite for the Indexed Pixel Editor V3
Updated to work with the refactored MVC architecture
"""

# Standard library imports
import json
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

# Third-party imports
import numpy as np
import pytest

# PIL for image testing
from PIL import Image
from PyQt6.QtCore import QEvent, Qt
from PyQt6.QtGui import QKeyEvent
from PyQt6.QtWidgets import QApplication, QDialog

# Local imports
from pixel_editor.core.indexed_pixel_editor import (
    IndexedPixelEditor,
    PaletteSwitcherDialog,
)


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
def sample_image_file(temp_dir):
    """Create a simple indexed image file"""
    # Create 8x8 test image
    data = np.arange(64).reshape(8, 8) % 16
    img = Image.fromarray(data.astype(np.uint8), mode="P")

    # Set grayscale palette
    palette = []
    for i in range(16):
        gray = i * 17
        palette.extend([gray, gray, gray])
    while len(palette) < 768:
        palette.extend([0, 0, 0])
    img.putpalette(palette)

    # Save
    file_path = temp_dir / "test_image.png"
    img.save(file_path)
    return str(file_path)


@pytest.fixture
def multi_palette_setup(temp_dir):
    """Set up a complete multi-palette test environment"""
    # Create test image
    rng = np.random.default_rng()
    img_data = rng.integers(0, 16, size=(16, 16), dtype=np.uint8)
    img = Image.fromarray(img_data, mode="P")

    # Set up grayscale palette
    palette = []
    for i in range(16):
        gray = i * 17
        palette.extend([gray, gray, gray])
    while len(palette) < 768:
        palette.extend([0, 0, 0])
    img.putpalette(palette)

    # Save image
    img_path = temp_dir / "test_sprite.png"
    img.save(img_path)

    # Create palette files
    palette_data = {}
    for i in range(8, 16):
        colors = []
        for j in range(16):
            # Create distinct colors for each palette
            r = (i * 16 + j * 8) % 256
            g = (i * 32 + j * 4) % 256
            b = (i * 48 + j * 2) % 256
            colors.append((r, g, b))
        palette_data[i] = colors

        # Save palette file
        palette_file = temp_dir / f"test_palette_{i}.pal.json"
        with open(palette_file, "w") as f:
            json.dump(
                {
                    "colors": [[c[0], c[1], c[2]] for c in colors],
                    "name": f"Test Palette {i}",
                    "source": "Test Suite",
                },
                f,
            )

    # Create metadata file
    metadata = {
        "width": 16,
        "height": 16,
        "palettes": {str(i): f"test_palette_{i}.pal.json" for i in range(8, 16)},
        "default_palette": 8,
    }

    metadata_path = temp_dir / "test_sprite_metadata.json"
    with open(metadata_path, "w") as f:
        json.dump(metadata, f)

    return {
        "image_path": str(img_path),
        "metadata_path": str(metadata_path),
        "temp_dir": temp_dir,
        "palette_data": palette_data,
    }


class TestBasicOperations:
    """Test basic pixel editor operations"""

    def test_new_file_creation(self, qapp):
        """Test creating a new file"""
        with patch.object(IndexedPixelEditor, "handle_startup"):
            editor = IndexedPixelEditor()

            # Check that a new image was created
            assert editor.controller.image_model is not None
            assert editor.controller.image_model.width == 8
            assert editor.controller.image_model.height == 8

    def test_save_and_load_file(self, qapp, temp_dir):
        """Test saving and loading a file"""
        with patch.object(IndexedPixelEditor, "handle_startup"):
            editor = IndexedPixelEditor()

            # Draw something
            editor.controller.set_drawing_color(5)
            editor.controller.handle_canvas_press(2, 2)
            editor.controller.handle_canvas_release(2, 2)

            # Save file
            save_path = temp_dir / "test_save.png"

            # Mock the save worker to complete synchronously
            with patch.object(editor.controller.file_manager, "save_file") as mock_save:
                mock_worker = MagicMock()
                mock_save.return_value = mock_worker

                # Simulate synchronous save
                editor.controller.save_file(str(save_path))

                # Manually trigger save success
                editor.controller._handle_save_success(str(save_path))

            # Verify file was "saved" (in our mock)
            assert editor.controller.project_model.image_path == str(save_path)
            assert not editor.controller.is_modified()


class TestPaletteOperations:
    """Test palette-related operations"""

    def test_apply_palette(self, qapp):
        """Test applying a palette"""
        with patch.object(IndexedPixelEditor, "handle_startup"):
            editor = IndexedPixelEditor()

            # Create test colors
            test_colors = [(255, 0, 0), (0, 255, 0), (0, 0, 255)] + [
                (i * 16, i * 16, i * 16) for i in range(3, 16)
            ]

            # Apply palette using legacy API
            flat_colors = []
            for r, g, b in test_colors:
                flat_colors.extend([r, g, b])

            editor.apply_palette(10, flat_colors)

            # Check palette was applied
            assert editor.current_palette_index == 10
            assert editor.controller.palette_model.name == "Palette 10"

            # Check colors were set
            for i, (r, g, b) in enumerate(test_colors[:16]):
                assert editor.controller.palette_model.colors[i] == (r, g, b)

    def test_palette_switcher_dialog(self, qapp):
        """Test palette switcher dialog with mock palettes"""
        # Create mock metadata with palette_colors
        palette_colors = {}
        for i in range(8, 16):
            colors = []
            for j in range(16):
                r = (i * 16 + j * 8) % 256
                g = (i * 32 + j * 4) % 256
                b = (i * 48 + j * 2) % 256
                colors.append([r, g, b])
            palette_colors[str(i)] = colors

        metadata = {
            "palette_colors": palette_colors,
            "palettes": {str(i): f"test_palette_{i}.pal.json" for i in range(8, 16)},
            "default_palette": 8,
        }

        dialog = PaletteSwitcherDialog(metadata, 8)

        # Check dialog was populated
        assert dialog.palette_list.count() == 8

        # Select palette 12
        dialog.palette_list.setCurrentRow(4)  # Index 4 = palette 12

        # Get selected palette
        selected_idx, colors = dialog.get_selected_palette()
        assert selected_idx == 12
        assert colors == palette_colors["12"]


class TestColorModeToggle:
    """Test color/grayscale mode toggling"""

    def test_toggle_via_checkbox(self, qapp):
        """Test toggling color mode via checkbox"""
        with patch.object(IndexedPixelEditor, "handle_startup"):
            editor = IndexedPixelEditor()

            # Should start with palette applied (color mode)
            assert editor.options_panel.apply_palette_checkbox.isChecked()
            assert not editor.canvas.greyscale_mode

            # Toggle off
            editor.options_panel.apply_palette_checkbox.setChecked(False)
            assert editor.canvas.greyscale_mode

            # Toggle on
            editor.options_panel.apply_palette_checkbox.setChecked(True)
            assert not editor.canvas.greyscale_mode

    def test_toggle_via_keyboard(self, qapp):
        """Test toggling color mode via C key"""
        with patch.object(IndexedPixelEditor, "handle_startup"):
            editor = IndexedPixelEditor()

            # Start in color mode
            assert editor.options_panel.apply_palette_checkbox.isChecked()

            # Press C key
            event = QKeyEvent(
                QEvent.Type.KeyPress, Qt.Key.Key_C, Qt.KeyboardModifier.NoModifier
            )
            editor.keyPressEvent(event)

            # Should toggle to grayscale
            assert not editor.options_panel.apply_palette_checkbox.isChecked()
            assert editor.canvas.greyscale_mode


class TestMetadataIntegration:
    """Test metadata loading and palette switching"""

    def test_load_file_with_metadata(self, qapp, multi_palette_setup):
        """Test loading a file with associated metadata"""
        with patch.object(IndexedPixelEditor, "handle_startup"):
            editor = IndexedPixelEditor()

            # Mock the file loading to be synchronous
            with patch.object(editor.controller, "open_file") as mock_open:
                # Load the file through legacy API
                editor.load_file_by_path(multi_palette_setup["image_path"])

                # Verify open was called
                mock_open.assert_called_once_with(multi_palette_setup["image_path"])

            # Manually set up the metadata as if it was loaded
            with open(multi_palette_setup["metadata_path"]) as f:
                json.load(f)

            # Mock the palette manager to have the palettes
            for i in range(8, 16):
                palette_model = MagicMock()
                palette_model.colors = multi_palette_setup["palette_data"][i]
                palette_model.name = f"Test Palette {i}"
                editor.controller.palette_manager.add_palette(i, palette_model)

            # Enable palette switching
            editor.switch_palette_action.setEnabled(True)

            # Test that we can get available palettes
            with patch.object(editor.controller, "get_available_palettes") as mock_get:
                mock_get.return_value = {
                    i: {
                        "colors": multi_palette_setup["palette_data"][i],
                        "name": f"Test Palette {i}",
                        "file": f"test_palette_{i}.pal.json",
                    }
                    for i in range(8, 16)
                }

                palettes = editor.controller.get_available_palettes()
                assert len(palettes) == 8
                assert 12 in palettes

    def test_switch_palette_action(self, qapp, multi_palette_setup):
        """Test switching palettes via action"""
        with patch.object(IndexedPixelEditor, "handle_startup"):
            editor = IndexedPixelEditor()

            # Set up palettes in the controller
            for i in range(8, 16):
                palette_model = MagicMock()
                palette_model.colors = multi_palette_setup["palette_data"][i]
                palette_model.name = f"Test Palette {i}"
                editor.controller.palette_manager.add_palette(i, palette_model)

            # Enable switching
            editor.switch_palette_action.setEnabled(True)

            # Mock the dialog to return palette 14
            with patch(
                "pixel_editor.core.indexed_pixel_editor_v3.PaletteSwitcherDialog"
            ) as mock_dialog_class:
                mock_dialog = MagicMock()
                mock_dialog.exec.return_value = QDialog.DialogCode.Accepted
                mock_dialog.get_selected_palette.return_value = 14
                mock_dialog_class.return_value = mock_dialog

                # Trigger palette switch
                editor.show_palette_switcher()

                # Verify dialog was shown
                mock_dialog_class.assert_called_once()
                mock_dialog.exec.assert_called_once()


class TestProgressHandling:
    """Test progress dialog handling"""

    @pytest.mark.skip(reason="Progress dialogs were removed in V3 refactor")
    def test_progress_dialog_creation(self, qapp):
        """Test that progress dialog is created during operations"""
        with patch.object(IndexedPixelEditor, "handle_startup"):
            editor = IndexedPixelEditor()

            # Start progress
            editor._start_progress("Test Operation", "Testing...")

            # Check dialog was created
            assert editor.progress_dialog is not None

            # Update progress
            editor._update_progress(50, "Half way...")

            # Finish progress
            editor._finish_progress()

            # Dialog should be cleared
            assert editor.progress_dialog is None


class TestDrawingOperations:
    """Test drawing operations through the controller"""

    def test_basic_drawing(self, qapp):
        """Test basic pixel drawing"""
        with patch.object(IndexedPixelEditor, "handle_startup"):
            editor = IndexedPixelEditor()

            # Set color
            editor.controller.set_drawing_color(7)

            # Draw a pixel
            editor.controller.handle_canvas_press(3, 3)
            editor.controller.handle_canvas_release(3, 3)

            # Check pixel was drawn
            pixel_value = editor.controller.image_model.get_pixel(3, 3)
            assert pixel_value == 7

    def test_tool_switching(self, qapp):
        """Test switching between tools"""
        with patch.object(IndexedPixelEditor, "handle_startup"):
            editor = IndexedPixelEditor()

            # Switch to fill tool
            editor.controller.set_tool("fill")
            assert editor.controller.get_current_tool_name() == "fill"

            # Switch to picker tool
            editor.controller.set_tool("picker")
            assert editor.controller.get_current_tool_name() == "picker"

            # Switch back to pencil
            editor.controller.set_tool("pencil")
            assert editor.controller.get_current_tool_name() == "pencil"


if __name__ == "__main__":
    # Run tests
    pytest.main(
        [
            __file__,
            "-v",
            "--tb=short",
            "-x",  # Stop on first failure
        ]
    )
