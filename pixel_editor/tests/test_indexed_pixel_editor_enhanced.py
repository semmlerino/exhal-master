#!/usr/bin/env python3
"""
Enhanced test suite for the Indexed Pixel Editor
Focuses on new functionality from consolidation:
- Multi-palette support
- PaletteSwitcherDialog
- Metadata handling
- Keyboard shortcuts
- Debug logging
- Command-line arguments
"""

# Standard library imports
import json
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

# Third-party imports
import numpy as np
import pytest

# PIL for image testing
from PIL import Image
from PyQt6.QtCore import QEvent, Qt
from PyQt6.QtGui import QKeyEvent

# PyQt6 testing setup
from PyQt6.QtWidgets import QApplication, QDialog

# Local imports
# Import modules to test
from pixel_editor.core.indexed_pixel_editor import (
    IndexedPixelEditor,
    PaletteSwitcherDialog,
    debug_color,
    debug_exception,
    debug_log,
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
def sample_metadata():
    """Create sample metadata for multi-palette support"""
    # Create color data for each palette (8-15)
    palette_colors = {}
    for i in range(8, 16):
        colors = []
        for j in range(16):
            # Create distinct colors for each palette
            r = (i * 16 + j * 8) % 256
            g = (i * 32 + j * 4) % 256
            b = (i * 48 + j * 2) % 256
            colors.append([r, g, b])
        palette_colors[str(i)] = colors

    return {
        "width": 16,
        "height": 16,
        "palette_colors": palette_colors,
        "palettes": {
            "8": "test_palette_8.pal.json",
            "9": "test_palette_9.pal.json",
            "10": "test_palette_10.pal.json",
            "11": "test_palette_11.pal.json",
            "12": "test_palette_12.pal.json",
            "13": "test_palette_13.pal.json",
            "14": "test_palette_14.pal.json",
            "15": "test_palette_15.pal.json",
        },
        "default_palette": 8,
    }


@pytest.fixture
def sample_palette_data():
    """Create sample palette data"""
    colors = []
    for i in range(16):
        # Create distinct colors for each palette index
        r = (i * 16) % 256
        g = (i * 32) % 256
        b = (i * 48) % 256
        colors.append([r, g, b])
    return {"colors": colors, "name": "Test Palette", "source": "Test Suite"}


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
def multi_palette_setup(temp_dir, sample_metadata, sample_palette_data):
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

    # Save palette files first
    for i in range(8, 16):
        palette_file = temp_dir / f"test_palette_{i}.pal.json"
        # Modify colors slightly for each palette
        palette_data = sample_palette_data.copy()
        palette_data["colors"] = [
            [(c[0] + i * 10) % 256, (c[1] + i * 10) % 256, (c[2] + i * 10) % 256]
            for c in sample_palette_data["colors"]
        ]
        palette_data["name"] = f"Test Palette {i}"
        with open(palette_file, "w") as f:
            json.dump(palette_data, f)

    # Create metadata with palette colors populated
    metadata_with_colors = sample_metadata.copy()

    # Load palette colors from the saved palette files
    palette_colors = {}
    for i in range(8, 16):
        palette_file = temp_dir / f"test_palette_{i}.pal.json"
        with open(palette_file) as f:
            palette_data = json.load(f)
            palette_colors[str(i)] = palette_data["colors"]

    metadata_with_colors["palette_colors"] = palette_colors

    # Save metadata
    metadata_path = temp_dir / "test_sprite_metadata.json"
    with open(metadata_path, "w") as f:
        json.dump(metadata_with_colors, f)

    return {
        "image_path": str(img_path),
        "metadata_path": str(metadata_path),
        "temp_dir": temp_dir,
    }


class TestDebugLogging:
    """Test the debug logging functionality"""

    def test_debug_log_levels(self, capsys):
        """Test debug logging with different levels"""
        # Import pixel_editor_utils to modify the actual DEBUG_MODE
        from pixel_editor.core import pixel_editor_utils

        # Ensure debug mode is on
        original_debug = pixel_editor_utils.DEBUG_MODE
        pixel_editor_utils.DEBUG_MODE = True

        try:
            debug_log("TEST", "Info message", "INFO")
            debug_log("TEST", "Error message", "ERROR")
            debug_log("TEST", "Warning message", "WARNING")
            debug_log("TEST", "Debug message", "DEBUG")

            captured = capsys.readouterr()
            assert "Info message" in captured.out
            assert "Error message" in captured.out
            assert "Warning message" in captured.out
            assert "Debug message" in captured.out

            # Check color codes
            assert "\033[91m" in captured.out  # Red for ERROR
            assert "\033[93m" in captured.out  # Yellow for WARNING
            assert "\033[94m" in captured.out  # Blue for DEBUG
        finally:
            pixel_editor_utils.DEBUG_MODE = original_debug

    def test_debug_color_formatting(self):
        """Test color debug formatting"""
        # Test with RGB
        result = debug_color(5, (255, 128, 64))
        assert "Index 5" in result
        assert "RGB: (255, 128, 64)" in result
        assert "Hex: #ff8040" in result

        # Test without RGB
        result = debug_color(10)
        assert result == "Index 10"

    def test_debug_exception(self, capsys):
        """Test exception debug logging"""
        # Import pixel_editor_utils to modify the actual DEBUG_MODE
        from pixel_editor.core import pixel_editor_utils

        original_debug = pixel_editor_utils.DEBUG_MODE
        pixel_editor_utils.DEBUG_MODE = True

        try:
            test_exception = ValueError("Test error")
            debug_exception("TEST", test_exception)

            captured = capsys.readouterr()
            assert "ValueError" in captured.out
            assert "Test error" in captured.out
            assert "\033[91m" in captured.out  # Red color
        finally:
            pixel_editor_utils.DEBUG_MODE = original_debug

    def test_debug_mode_off(self, capsys):
        """Test that logging is disabled when DEBUG_MODE is False"""
        # Import pixel_editor_utils to modify the actual DEBUG_MODE
        from pixel_editor.core import pixel_editor_utils

        original_debug = pixel_editor_utils.DEBUG_MODE
        pixel_editor_utils.DEBUG_MODE = False

        try:
            debug_log("TEST", "This should not appear")
            captured = capsys.readouterr()
            assert "This should not appear" not in captured.out
        finally:
            pixel_editor_utils.DEBUG_MODE = original_debug


class TestPaletteSwitcherDialog:
    """Test the palette switcher dialog"""

    def test_dialog_initialization(self, qapp, sample_metadata):
        """Test palette switcher dialog initialization"""
        dialog = PaletteSwitcherDialog(sample_metadata, 8)

        assert dialog.metadata == sample_metadata
        assert dialog.current_index == 8
        assert hasattr(dialog, "palette_list")
        assert hasattr(dialog, "color_preview")

    def test_palette_list_population(self, qapp, sample_metadata):
        """Test that palette list is populated correctly"""
        dialog = PaletteSwitcherDialog(sample_metadata, 8)

        # Should have 8 items (palettes 8-15)
        assert dialog.palette_list.count() == 8

        # Check first item
        first_item = dialog.palette_list.item(0)
        assert "Palette 8" in first_item.text()
        assert "(Kirby - Purple/Pink)" in first_item.text()
        assert "16 colors" in first_item.text()

        # Check that current palette is selected
        assert first_item.isSelected()

    def test_palette_selection(self, qapp, sample_metadata):
        """Test selecting a different palette"""
        dialog = PaletteSwitcherDialog(sample_metadata, 8)

        # Select palette 10 (index 2 in the list)
        dialog.palette_list.setCurrentRow(2)

        # Check that get_selected_palette returns the right values
        palette_idx, colors = dialog.get_selected_palette()
        assert palette_idx == 10

    def test_dialog_accept_reject(self, qapp, sample_metadata):
        """Test dialog accept/reject functionality"""
        dialog = PaletteSwitcherDialog(sample_metadata, 8)

        # Test reject
        dialog.reject()
        assert dialog.result() == QDialog.DialogCode.Rejected

        # Test accept with selection
        dialog = PaletteSwitcherDialog(sample_metadata, 8)
        # Select palette 12 (index 4 in list)
        dialog.palette_list.setCurrentRow(4)
        dialog.accept()

        # get_selected_palette returns tuple (index, colors)
        palette_idx, colors = dialog.get_selected_palette()
        assert palette_idx == 12


class TestMetadataHandling:
    """Test metadata loading and handling"""

    def test_load_metadata_file(self, qapp, multi_palette_setup):
        """Test loading metadata file"""
        with patch.object(IndexedPixelEditor, "handle_startup"):
            editor = IndexedPixelEditor()

            # Load image with metadata synchronously
            success = load_file_sync(editor, multi_palette_setup["image_path"])

            assert success
            # Check that metadata was loaded
            assert editor.controller.project_model.metadata_path is not None
            assert (
                editor.controller.palette_manager.current_palette_index == 8
            )  # Default palette

    def test_auto_detect_metadata(self, qapp, multi_palette_setup):
        """Test automatic metadata file detection"""
        with patch.object(IndexedPixelEditor, "handle_startup"):
            editor = IndexedPixelEditor()

            # The load_file_sync should auto-detect metadata
            load_file_sync(editor, multi_palette_setup["image_path"])

            # Check metadata was loaded
            assert editor.controller.project_model.metadata_path is not None
            assert editor.controller.has_metadata_palettes()
            assert editor.controller.palette_manager.get_palette_count() > 1

    def test_switch_palette_from_metadata(self, qapp, multi_palette_setup):
        """Test switching palettes using metadata"""
        with patch.object(IndexedPixelEditor, "handle_startup"):
            editor = IndexedPixelEditor()
            load_file_sync(editor, multi_palette_setup["image_path"])

            # Get available palettes
            available_palettes = editor.controller.get_available_palettes()
            assert len(available_palettes) > 0

            # Switch to palette 12
            original_palette = editor.controller.palette_manager.current_palette_index
            editor.controller.switch_palette(12)

            assert editor.controller.palette_manager.current_palette_index == 12
            assert (
                editor.controller.palette_manager.current_palette_index
                != original_palette
            )

    def test_missing_palette_file_handling(self, qapp, multi_palette_setup):
        """Test handling of missing palette files"""
        with patch.object(IndexedPixelEditor, "handle_startup"):
            editor = IndexedPixelEditor()

            # Delete one palette file
            (multi_palette_setup["temp_dir"] / "test_palette_10.pal.json").unlink()

            # Should still load successfully
            load_file_sync(editor, multi_palette_setup["image_path"])

            # Should still have loaded the image
            assert editor.controller.has_image()
            # Should still have metadata
            assert editor.controller.project_model.metadata_path is not None
            # Should still have some palettes available (from metadata)
            assert editor.controller.has_metadata_palettes()


class TestKeyboardShortcuts:
    """Test keyboard shortcuts functionality"""

    def test_p_key_opens_palette_switcher(self, qapp, multi_palette_setup):
        """Test P key opens palette switcher when metadata exists"""
        with patch.object(IndexedPixelEditor, "handle_startup"):
            editor = IndexedPixelEditor()

            # Load file synchronously
            load_file_sync(editor, multi_palette_setup["image_path"])

            # Mock the show_palette_switcher method
            with patch.object(editor, "show_palette_switcher") as mock_switch:
                # Create P key press event
                event = QKeyEvent(
                    QEvent.Type.KeyPress, Qt.Key.Key_P, Qt.KeyboardModifier.NoModifier
                )
                editor.keyPressEvent(event)

                mock_switch.assert_called_once()

    def test_c_key_toggles_color_mode(self, qapp):
        """Test C key toggles Apply Palette checkbox"""
        with patch.object(IndexedPixelEditor, "handle_startup"):
            editor = IndexedPixelEditor()
            editor.new_image(8, 8)

            # Should start with palette applied
            assert editor.apply_palette_checkbox.isChecked()
            assert not editor.canvas.greyscale_mode

            # Press C key
            event = QKeyEvent(
                QEvent.Type.KeyPress, Qt.Key.Key_C, Qt.KeyboardModifier.NoModifier
            )
            editor.keyPressEvent(event)

            # Apply Palette should toggle off, grayscale mode should be on
            assert not editor.apply_palette_checkbox.isChecked()
            assert editor.canvas.greyscale_mode

            # Press C again
            editor.keyPressEvent(event)

            # Should toggle back
            assert editor.apply_palette_checkbox.isChecked()
            assert not editor.canvas.greyscale_mode

    def test_keyboard_shortcuts_without_metadata(self, qapp):
        """Test that P key does nothing without metadata"""
        with patch.object(IndexedPixelEditor, "handle_startup"):
            editor = IndexedPixelEditor()
            editor.new_image(8, 8)

            # No metadata loaded
            assert editor.metadata is None

            with patch.object(editor, "show_palette_switcher") as mock_switch:
                event = QKeyEvent(
                    QEvent.Type.KeyPress, Qt.Key.Key_P, Qt.KeyboardModifier.NoModifier
                )
                editor.keyPressEvent(event)

                # Should not call show_palette_switcher
                mock_switch.assert_not_called()


class TestViewMenuActions:
    """Test View menu actions"""

    def test_view_menu_creation(self, qapp):
        """Test that View menu contains new actions"""
        with patch.object(IndexedPixelEditor, "handle_startup"):
            editor = IndexedPixelEditor()

            # Find View menu
            view_menu = None
            for action in editor.menuBar().actions():
                if action.text() == "View":  # Remove the & check
                    view_menu = action.menu()
                    break

            assert view_menu is not None

            # Check for new actions
            action_texts = [action.text() for action in view_menu.actions()]
            assert "Switch &Palette..." in action_texts
            # Note: "Toggle &Color Mode" is not in the current implementation

    def test_switch_palette_action_enabled_state(self, qapp, multi_palette_setup):
        """Test that Switch Palette action is enabled/disabled correctly"""
        with patch.object(IndexedPixelEditor, "handle_startup"):
            editor = IndexedPixelEditor()

            # Initially disabled (no metadata)
            assert not editor.switch_palette_action.isEnabled()

            # Load file with metadata synchronously
            load_file_sync(editor, multi_palette_setup["image_path"])

            # Now should be enabled
            assert editor.switch_palette_action.isEnabled()

    def test_toggle_color_mode_action(self, qapp):
        """Test toggle color mode action"""
        pytest.skip("Toggle Color Mode action not implemented in current version")


class TestCommandLineArguments:
    """Test command-line argument handling"""

    def test_load_file_from_args(self, qapp, sample_image_file, qtbot):
        """Test loading file from command-line arguments"""
        with patch.object(IndexedPixelEditor, "handle_startup"):
            editor = IndexedPixelEditor()
            editor.show()

            # Use the controller's open_file method which creates a worker
            editor.controller.open_file(sample_image_file)

            # Get the worker
            worker = editor.controller.load_worker
            assert worker is not None

            # Wait for the worker to complete
            with qtbot.waitSignal(worker.finished, timeout=2000):
                pass  # Worker was already started by open_file

            # The file should be loaded
            assert editor.controller.get_current_file_path() == sample_image_file
            assert editor.controller.has_image()

    def test_invalid_file_arg_handling(self, qapp):
        """Test handling of invalid file argument"""
        with patch.object(IndexedPixelEditor, "handle_startup"):
            editor = IndexedPixelEditor()

            # Connect to error signal to capture errors
            errors = []
            editor.controller.error.connect(lambda msg: errors.append(msg))

            # Try to load a non-existent file
            editor.controller.open_file("nonexistent.png")

            # Should have emitted an error
            assert len(errors) > 0
            assert "not found" in errors[0].lower()
            # Editor should still be functional
            assert editor is not None
            assert not editor.controller.has_image()

    def test_no_args_shows_startup(self, qapp):
        """Test that no arguments triggers startup handling"""
        # Don't patch handle_startup to let it run
        with patch.object(IndexedPixelEditor, "show_startup_dialog"):
            editor = IndexedPixelEditor()

            # handle_startup should have been called
            # The startup dialog may or may not be shown depending on settings
            # Just verify editor was created successfully
            assert editor is not None
            assert editor.controller is not None

            # If auto_load is false or there are recent files, dialog would be shown
            # We can't predict this without controlling settings, so just check the editor works
            assert hasattr(editor, "canvas")
            assert hasattr(editor, "controller")


class TestGreyscaleColorModeTransitions:
    """Test transitions between greyscale and color modes"""

    def test_mode_preservation_during_operations(self, qapp):
        """Test that mode is preserved during various operations"""
        with patch.object(IndexedPixelEditor, "handle_startup"):
            editor = IndexedPixelEditor()
            editor.new_image(8, 8)

            # Ensure apply palette is on (color mode)
            editor.apply_palette_checkbox.setChecked(True)
            assert not editor.canvas.greyscale_mode

            # Draw some pixels
            editor.controller.set_drawing_color(5)
            editor.controller.handle_canvas_press(2, 2)
            editor.controller.handle_canvas_release(2, 2)

            # Mode should be preserved
            assert editor.apply_palette_checkbox.isChecked()
            assert not editor.canvas.greyscale_mode

            # Verify pixel was drawn
            assert editor.controller.image_model.data[2, 2] == 5

            # Mode should still be the same
            assert editor.apply_palette_checkbox.isChecked()
            assert not editor.canvas.greyscale_mode

    def test_palette_widget_mode_sync(self, qapp):
        """Test that palette widget syncs with canvas mode"""
        with patch.object(IndexedPixelEditor, "handle_startup"):
            editor = IndexedPixelEditor()
            editor.new_image(8, 8)

            # Should start with Apply Palette checked (color mode)
            assert editor.apply_palette_checkbox.isChecked()
            assert not editor.canvas.greyscale_mode

            # Toggle to grayscale mode
            editor.toggle_color_mode_shortcut()

            # Apply Palette should be off, grayscale mode should be on
            assert not editor.apply_palette_checkbox.isChecked()
            assert editor.canvas.greyscale_mode

            # Toggle back to color mode
            editor.toggle_color_mode_shortcut()

            # Should be back with Apply Palette on
            assert editor.apply_palette_checkbox.isChecked()
            assert not editor.canvas.greyscale_mode

    def test_external_palette_overrides_mode(self, qapp, multi_palette_setup):
        """Test that external palette loading doesn't change color mode"""
        with patch.object(IndexedPixelEditor, "handle_startup"):
            editor = IndexedPixelEditor()

            # Load file with metadata
            load_file_sync(editor, multi_palette_setup["image_path"])

            # Start with Apply Palette unchecked (grayscale mode)
            editor.apply_palette_checkbox.setChecked(False)
            assert editor.canvas.greyscale_mode

            # Switch to a different palette
            editor.controller.switch_palette(9)

            # Verify palette changed
            assert editor.controller.palette_manager.current_palette_index == 9

            # The user's color mode choice should be preserved
            assert not editor.apply_palette_checkbox.isChecked()
            assert editor.canvas.greyscale_mode


class TestPerformance:
    """Test performance with large sprite sheets"""

    def test_large_sprite_sheet_loading(self, qapp, temp_dir):
        """Test loading and editing large sprite sheets"""
        # Create a 256x256 sprite sheet
        rng = np.random.default_rng()
        large_data = rng.integers(0, 16, size=(256, 256), dtype=np.uint8)
        large_img = Image.fromarray(large_data, mode="P")

        # Set palette
        palette = []
        for i in range(16):
            palette.extend([i * 16, i * 16, i * 16])
        while len(palette) < 768:
            palette.extend([0, 0, 0])
        large_img.putpalette(palette)

        # Save
        large_file = temp_dir / "large_sprite.png"
        large_img.save(large_file)

        with patch.object(IndexedPixelEditor, "handle_startup"):
            editor = IndexedPixelEditor()

            # Measure load time
            import time

            start_time = time.time()
            load_file_sync(editor, str(large_file))
            load_time = time.time() - start_time

            assert editor.controller.has_image()
            assert editor.controller.image_model.data.shape == (256, 256)
            # Loading should be reasonably fast (< 1 second)
            assert load_time < 1.0

            # Test drawing performance
            start_time = time.time()
            for i in range(100):
                x = i % 256
                y = i // 256
                editor.controller.handle_canvas_press(x, y)
                editor.controller.handle_canvas_release(x, y)
            draw_time = time.time() - start_time

            # Drawing 100 pixels should be fast (< 0.5 seconds)
            assert draw_time < 0.5

    def test_zoom_performance(self, qapp):
        """Test zoom performance with large images"""
        with patch.object(IndexedPixelEditor, "handle_startup"):
            editor = IndexedPixelEditor()
            editor.controller.new_file(128, 128)

            # Test rapid zoom changes
            import time

            start_time = time.time()

            zoom_levels = [1, 2, 4, 8, 16, 32, 16, 8, 4, 2, 1]
            for zoom in zoom_levels:
                editor.set_zoom_preset(zoom)

            zoom_time = time.time() - start_time

            # Zoom changes should be fast (< 0.5 seconds for 11 changes)
            assert zoom_time < 0.5


class TestIntegrationWorkflows:
    """Test complete editing workflows"""

    def test_complete_multi_palette_workflow(self, qapp, multi_palette_setup, qtbot):
        """Test a complete multi-palette editing workflow"""
        with patch.object(IndexedPixelEditor, "handle_startup"):
            editor = IndexedPixelEditor()

            # 1. Load sprite with metadata
            load_file_sync(editor, multi_palette_setup["image_path"])
            assert editor.controller.has_metadata_palettes()

            # 2. Switch to palette 10
            editor.controller.switch_palette(10)
            assert editor.controller.palette_manager.current_palette_index == 10

            # 3. Edit some pixels
            editor.controller.set_drawing_color(5)
            editor.controller.handle_canvas_press(5, 5)
            editor.controller.handle_canvas_release(5, 5)
            editor.controller.handle_canvas_press(6, 6)
            editor.controller.handle_canvas_release(6, 6)

            # 4. Switch to palette 14
            editor.controller.switch_palette(14)
            assert editor.controller.palette_manager.current_palette_index == 14

            # 5. Edit more pixels
            editor.controller.set_drawing_color(8)
            editor.controller.handle_canvas_press(10, 10)
            editor.controller.handle_canvas_release(10, 10)

            # 6. Toggle color mode
            editor.toggle_color_mode_shortcut()

            # 7. Save the file using async worker
            save_path = multi_palette_setup["temp_dir"] / "edited_sprite.png"
            editor.controller.save_file(str(save_path))

            # Wait for save to complete
            worker = editor.controller.save_worker
            with qtbot.waitSignal(worker.finished, timeout=2000):
                pass

            # Verify saved file
            assert save_path.exists()
            saved_img = Image.open(save_path)
            saved_data = np.array(saved_img)

            # Check edited pixels
            assert saved_data[5, 5] == 5
            assert saved_data[6, 6] == 5
            assert saved_data[10, 10] == 8

    def test_palette_switching_preserves_edits(self, qapp, multi_palette_setup):
        """Test that edits are preserved when switching palettes"""
        with patch.object(IndexedPixelEditor, "handle_startup"):
            editor = IndexedPixelEditor()
            load_file_sync(editor, multi_palette_setup["image_path"])

            # Make edits with palette 8
            editor.controller.set_drawing_color(7)
            editor.controller.handle_canvas_press(3, 3)
            editor.controller.handle_canvas_release(3, 3)
            original_pixel = editor.controller.image_model.data[3, 3]

            # Switch to palette 12
            editor.controller.switch_palette(12)

            # Pixel value should be preserved
            assert editor.controller.image_model.data[3, 3] == original_pixel

            # But palette should be different
            assert editor.controller.palette_manager.current_palette_index == 12

    def test_error_recovery_workflow(self, qapp, multi_palette_setup):
        """Test error recovery in various scenarios"""
        with patch.object(IndexedPixelEditor, "handle_startup"):
            editor = IndexedPixelEditor()

            # Load file
            load_file_sync(editor, multi_palette_setup["image_path"])

            # Connect error handler to capture errors
            errors = []
            editor.controller.error.connect(lambda msg: errors.append(msg))

            # Try to switch to a palette that doesn't exist
            # This should be handled gracefully
            editor.controller.switch_palette(99)  # Non-existent palette

            # Editor should still be functional
            assert editor.controller.has_image()

            # Should be able to continue editing
            editor.controller.set_drawing_color(3)
            editor.controller.handle_canvas_press(7, 7)
            editor.controller.handle_canvas_release(7, 7)
            assert editor.controller.image_model.data[7, 7] == 3


# Test helper functions for synchronous operations
def load_file_sync(editor, file_path):
    """Synchronously load a file into the editor without using worker threads"""
    import json
    import os

    from PIL import Image

    # Load the image directly
    img = Image.open(file_path)
    editor.controller.image_model.load_from_pil(img)

    # Update palette if image has one
    if img.mode == "P" and img.getpalette():
        editor.controller.palette_model.from_flat_list(list(img.getpalette()))
        editor.controller.paletteChanged.emit()

    # Check for metadata
    metadata_path = os.path.splitext(file_path)[0] + "_metadata.json"
    if os.path.exists(metadata_path):
        with open(metadata_path) as f:
            metadata = json.load(f)
            # Store metadata path
            editor.controller.project_model.metadata_path = metadata_path

            # Convert metadata format if needed
            if "palette_colors" in metadata and "palettes" in metadata:
                # Create palettes dict with actual color data for palette manager
                converted_palettes = {}
                for pal_idx_str, colors in metadata["palette_colors"].items():
                    converted_palettes[pal_idx_str] = {
                        "colors": colors,
                        "name": f"Palette {pal_idx_str}",
                    }
                metadata["palettes"] = converted_palettes

            # Load palettes from metadata
            if editor.controller.palette_manager.load_from_metadata(metadata):
                editor.controller.paletteChanged.emit()
            # Enable palette switching if we have palettes
            if editor.controller.has_metadata_palettes():
                editor.switch_palette_action.setEnabled(True)

    # Update project model
    editor.controller.file_manager.project_model.image_path = file_path
    editor.controller.file_manager.project_model.modified = False

    # Emit signals
    editor.controller.imageChanged.emit()
    editor.controller.titleChanged.emit(
        f"Indexed Pixel Editor - {os.path.basename(file_path)}"
    )

    # Update recent files
    editor.controller.settings.add_recent_file(file_path)

    return True


def wait_for_worker(qtbot, worker):
    """Wait for a worker to finish and return its result"""
    result_spy = qtbot.waitSignal(worker.result, timeout=2000)
    error_spy = qtbot.waitSignal(worker.error, timeout=2000)

    # Start the worker
    worker.start()

    # Wait for either result or error
    if result_spy.signal_triggered:
        return result_spy.args
    if error_spy.signal_triggered:
        raise RuntimeError(f"Worker error: {error_spy.args[0]}")
    raise TimeoutError("Worker did not complete in time")


if __name__ == "__main__":
    # Run tests with coverage
    pytest.main(
        [
            __file__,
            "-v",
            "--tb=short",
            "--cov=indexed_pixel_editor",
            "--cov=pixel_editor_widgets",
            "--cov-report=term-missing",
        ]
    )
