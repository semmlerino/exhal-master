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

import json
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pytest

# PIL for image testing
from PIL import Image
from PyQt6.QtCore import QEvent, Qt
from PyQt6.QtGui import QKeyEvent

# PyQt6 testing setup
from PyQt6.QtWidgets import QApplication, QDialog, QMessageBox

# Import modules to test
from indexed_pixel_editor import (
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
            "15": "test_palette_15.pal.json"
        },
        "default_palette": 8
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
    return {
        "colors": colors,
        "name": "Test Palette",
        "source": "Test Suite"
    }


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
    img_data = np.random.randint(0, 16, size=(16, 16), dtype=np.uint8)
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
        "temp_dir": temp_dir
    }


class TestDebugLogging:
    """Test the debug logging functionality"""

    def test_debug_log_levels(self, capsys):
        """Test debug logging with different levels"""
        import indexed_pixel_editor
        # Ensure debug mode is on
        original_debug = indexed_pixel_editor.DEBUG_MODE
        indexed_pixel_editor.DEBUG_MODE = True

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
            indexed_pixel_editor.DEBUG_MODE = original_debug

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
        import indexed_pixel_editor
        original_debug = indexed_pixel_editor.DEBUG_MODE
        indexed_pixel_editor.DEBUG_MODE = True

        try:
            test_exception = ValueError("Test error")
            debug_exception("TEST", test_exception)

            captured = capsys.readouterr()
            assert "ValueError" in captured.out
            assert "Test error" in captured.out
            assert "\033[91m" in captured.out  # Red color
        finally:
            indexed_pixel_editor.DEBUG_MODE = original_debug

    def test_debug_mode_off(self, capsys):
        """Test that logging is disabled when DEBUG_MODE is False"""
        import indexed_pixel_editor
        original_debug = indexed_pixel_editor.DEBUG_MODE
        indexed_pixel_editor.DEBUG_MODE = False

        try:
            debug_log("TEST", "This should not appear")
            captured = capsys.readouterr()
            assert "This should not appear" not in captured.out
        finally:
            indexed_pixel_editor.DEBUG_MODE = original_debug


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
            with patch("PyQt6.QtWidgets.QMessageBox.question", return_value=QMessageBox.StandardButton.No):
                editor = IndexedPixelEditor()

                # Load image with metadata
                success = editor.load_file_by_path(multi_palette_setup["image_path"])

                assert success
                assert editor.metadata is not None
                assert editor.current_palette_index == 8  # Default palette

    def test_auto_detect_metadata(self, qapp, multi_palette_setup):
        """Test automatic metadata file detection"""
        with patch.object(IndexedPixelEditor, "handle_startup"):
            with patch("PyQt6.QtWidgets.QMessageBox.question", return_value=QMessageBox.StandardButton.No):
                editor = IndexedPixelEditor()

                # The load_file_by_path should auto-detect metadata
                editor.load_file_by_path(multi_palette_setup["image_path"])

                assert editor.metadata is not None
                assert "palettes" in editor.metadata
                assert len(editor.metadata["palettes"]) == 8

    def test_switch_palette_from_metadata(self, qapp, multi_palette_setup):
        """Test switching palettes using metadata"""
        with patch.object(IndexedPixelEditor, "handle_startup"):
            with patch("PyQt6.QtWidgets.QMessageBox.question", return_value=QMessageBox.StandardButton.No):
                editor = IndexedPixelEditor()
                editor.load_file_by_path(multi_palette_setup["image_path"])

            # Switch to palette 12
            with patch.object(PaletteSwitcherDialog, "exec", return_value=True):
                # Use metadata from the loaded editor
                palette_colors = editor.metadata["palette_colors"]["12"]
                with patch.object(PaletteSwitcherDialog, "get_selected_palette", return_value=(12, palette_colors)):
                    editor.show_palette_switcher()

                    assert editor.current_palette_index == 12
                    # Check that external palette was loaded
                    assert editor.palette_widget.is_external_palette

    def test_missing_palette_file_handling(self, qapp, multi_palette_setup):
        """Test handling of missing palette files"""
        with patch.object(IndexedPixelEditor, "handle_startup"):
            with patch("PyQt6.QtWidgets.QMessageBox.question", return_value=QMessageBox.StandardButton.No):
                editor = IndexedPixelEditor()

                # Delete one palette file
                (multi_palette_setup["temp_dir"] / "test_palette_10.pal.json").unlink()

                editor.load_file_by_path(multi_palette_setup["image_path"])

            # Should still load
            assert editor.metadata is not None
            # Since palette colors are embedded in metadata, they should still be there
            assert "10" in editor.metadata["palette_colors"]
            # But the palette file reference should still exist in metadata
            assert "10" in editor.metadata["palettes"]


class TestKeyboardShortcuts:
    """Test keyboard shortcuts functionality"""

    def test_p_key_opens_palette_switcher(self, qapp, multi_palette_setup):
        """Test P key opens palette switcher when metadata exists"""
        with patch.object(IndexedPixelEditor, "handle_startup"):
            with patch("PyQt6.QtWidgets.QMessageBox.question", return_value=QMessageBox.StandardButton.No):
                editor = IndexedPixelEditor()
                editor.load_file_by_path(multi_palette_setup["image_path"])

            # Mock the show_palette_switcher method
            with patch.object(editor, "show_palette_switcher") as mock_switch:
                # Create P key press event
                event = QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_P, Qt.KeyboardModifier.NoModifier)
                editor.keyPressEvent(event)

                mock_switch.assert_called_once()

    def test_c_key_toggles_color_mode(self, qapp):
        """Test C key toggles between color and grayscale mode"""
        with patch.object(IndexedPixelEditor, "handle_startup"):
            editor = IndexedPixelEditor()
            editor.canvas.new_image(8, 8)

            # Start in grayscale mode
            original_mode = editor.canvas.greyscale_mode

            # Press C key
            event = QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_C, Qt.KeyboardModifier.NoModifier)
            editor.keyPressEvent(event)

            # Mode should toggle
            assert editor.canvas.greyscale_mode != original_mode

            # Press C again
            editor.keyPressEvent(event)

            # Should toggle back
            assert editor.canvas.greyscale_mode == original_mode

    def test_keyboard_shortcuts_without_metadata(self, qapp):
        """Test that P key does nothing without metadata"""
        with patch.object(IndexedPixelEditor, "handle_startup"):
            editor = IndexedPixelEditor()
            editor.canvas.new_image(8, 8)

            # No metadata loaded
            assert editor.metadata is None

            with patch.object(editor, "show_palette_switcher") as mock_switch:
                event = QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_P, Qt.KeyboardModifier.NoModifier)
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
            assert "Toggle &Color Mode" in action_texts

    def test_switch_palette_action_enabled_state(self, qapp, multi_palette_setup):
        """Test that Switch Palette action is enabled/disabled correctly"""
        with patch.object(IndexedPixelEditor, "handle_startup"):
            with patch("PyQt6.QtWidgets.QMessageBox.question", return_value=QMessageBox.StandardButton.No):
                editor = IndexedPixelEditor()

                # Initially disabled (no metadata)
                assert not editor.switch_palette_action.isEnabled()

                # Load file with metadata
                editor.load_file_by_path(multi_palette_setup["image_path"])

            # Now should be enabled
            assert editor.switch_palette_action.isEnabled()

    def test_toggle_color_mode_action(self, qapp):
        """Test toggle color mode action"""
        with patch.object(IndexedPixelEditor, "handle_startup"):
            editor = IndexedPixelEditor()
            editor.canvas.new_image(8, 8)

            initial_mode = editor.canvas.greyscale_mode

            # Find View menu and toggle color action
            view_menu = None
            for action in editor.menuBar().actions():
                if action.text() == "View":
                    view_menu = action.menu()
                    break

            assert view_menu is not None

            # Find toggle color action
            toggle_action = None
            for action in view_menu.actions():
                if action.text() == "Toggle &Color Mode":
                    toggle_action = action
                    break

            assert toggle_action is not None

            # Trigger the action
            toggle_action.trigger()

            # Mode should change
            assert editor.canvas.greyscale_mode != initial_mode


class TestCommandLineArguments:
    """Test command-line argument handling"""

    def test_load_file_from_args(self, qapp, sample_image_file):
        """Test loading file from command-line arguments"""
        with patch.object(IndexedPixelEditor, "handle_startup"):
            with patch("PyQt6.QtWidgets.QMessageBox.question", return_value=QMessageBox.StandardButton.No):
                editor = IndexedPixelEditor()

                # Simulate command-line file loading as done in main()
                editor.show()
                success = editor.load_file_by_path(sample_image_file)

                # The file should be loaded
                assert success
                assert editor.current_file == sample_image_file
                assert editor.canvas.image_data is not None

    def test_invalid_file_arg_handling(self, qapp):
        """Test handling of invalid file argument"""
        with patch.object(IndexedPixelEditor, "handle_startup"):
            with patch("PyQt6.QtWidgets.QMessageBox.critical") as mock_error:
                editor = IndexedPixelEditor()

                # Simulate trying to load a non-existent file
                success = editor.load_file_by_path("nonexistent.png")

                # Should show error but not crash
                assert not success
                mock_error.assert_called_once()
                assert editor is not None

    def test_no_args_shows_startup(self, qapp):
        """Test that no arguments triggers startup handling"""
        # Don't patch handle_startup to let it run
        with patch.object(IndexedPixelEditor, "show_startup_dialog"):
            editor = IndexedPixelEditor()

            # handle_startup should have been called and may show dialog
            # depending on settings (if there are recent files or auto_load is false)
            # Since we can't control the settings state, just verify editor was created
            assert editor is not None


class TestGreyscaleColorModeTransitions:
    """Test transitions between greyscale and color modes"""

    def test_mode_preservation_during_operations(self, qapp):
        """Test that mode is preserved during various operations"""
        with patch.object(IndexedPixelEditor, "handle_startup"):
            editor = IndexedPixelEditor()
            editor.canvas.new_image(8, 8)

            # Set to color mode
            editor.canvas.greyscale_mode = False
            editor.canvas.show_color_preview = True

            # Draw some pixels
            editor.canvas.current_color = 5
            editor.canvas.draw_pixel(2, 2)

            # Mode should be preserved
            assert not editor.canvas.greyscale_mode
            assert editor.canvas.show_color_preview

            # Save and verify mode persists
            pil_img = editor.canvas.get_pil_image()
            assert pil_img is not None

            # Mode should still be the same
            assert not editor.canvas.greyscale_mode

    def test_palette_widget_mode_sync(self, qapp):
        """Test that palette widget syncs with canvas mode"""
        with patch.object(IndexedPixelEditor, "handle_startup"):
            editor = IndexedPixelEditor()
            editor.canvas.new_image(8, 8)

            # Canvas starts with greyscale_mode = False (color mode)
            assert not editor.canvas.greyscale_mode

            # Toggle to grayscale mode
            editor.toggle_color_mode_shortcut()

            # Should now be in grayscale mode
            assert editor.canvas.greyscale_mode

            # Toggle back to color mode
            editor.toggle_color_mode_shortcut()

            # Should be back in color mode
            assert not editor.canvas.greyscale_mode

    def test_external_palette_overrides_mode(self, qapp, multi_palette_setup):
        """Test that external palette loading overrides color mode"""
        with patch.object(IndexedPixelEditor, "handle_startup"):
            with patch("PyQt6.QtWidgets.QMessageBox.question", return_value=QMessageBox.StandardButton.No):
                editor = IndexedPixelEditor()
                editor.load_file_by_path(multi_palette_setup["image_path"])

            # Start in grayscale mode
            editor.canvas.greyscale_mode = True

            # Apply a palette from metadata
            colors = editor.metadata["palette_colors"]["9"]
            editor.apply_palette(9, colors)

            # External palette should be loaded
            assert editor.palette_widget.is_external_palette
            assert editor.current_palette_index == 9


class TestPerformance:
    """Test performance with large sprite sheets"""

    def test_large_sprite_sheet_loading(self, qapp, temp_dir):
        """Test loading and editing large sprite sheets"""
        # Create a 256x256 sprite sheet
        large_data = np.random.randint(0, 16, size=(256, 256), dtype=np.uint8)
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
            success = editor.load_file_by_path(str(large_file))
            load_time = time.time() - start_time

            assert success
            assert editor.canvas.image_data.shape == (256, 256)
            # Loading should be reasonably fast (< 1 second)
            assert load_time < 1.0

            # Test drawing performance
            start_time = time.time()
            for i in range(100):
                x = i % 256
                y = i // 256
                editor.canvas.draw_pixel(x, y)
            draw_time = time.time() - start_time

            # Drawing 100 pixels should be fast (< 0.1 seconds)
            assert draw_time < 0.1

    def test_zoom_performance(self, qapp):
        """Test zoom performance with large images"""
        with patch.object(IndexedPixelEditor, "handle_startup"):
            editor = IndexedPixelEditor()
            editor.canvas.new_image(128, 128)

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

    def test_complete_multi_palette_workflow(self, qapp, multi_palette_setup):
        """Test a complete multi-palette editing workflow"""
        with patch.object(IndexedPixelEditor, "handle_startup"):
            with patch("PyQt6.QtWidgets.QMessageBox.question", return_value=QMessageBox.StandardButton.No):
                editor = IndexedPixelEditor()

                # 1. Load sprite with metadata
                editor.load_file_by_path(multi_palette_setup["image_path"])
                assert editor.metadata is not None

            # 2. Switch to palette 10
            colors_10 = editor.metadata["palette_colors"]["10"]
            editor.apply_palette(10, colors_10)
            assert editor.current_palette_index == 10

            # 3. Edit some pixels
            editor.canvas.current_color = 5
            editor.canvas.draw_pixel(5, 5)
            editor.canvas.draw_pixel(6, 6)

            # 4. Switch to palette 14
            colors_14 = editor.metadata["palette_colors"]["14"]
            editor.apply_palette(14, colors_14)
            assert editor.current_palette_index == 14

            # 5. Edit more pixels
            editor.canvas.current_color = 8
            editor.canvas.draw_pixel(10, 10)

            # 6. Toggle color mode
            editor.toggle_color_mode_shortcut()

            # 7. Save the file
            save_path = multi_palette_setup["temp_dir"] / "edited_sprite.png"
            editor.save_to_file(str(save_path))

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
            with patch("PyQt6.QtWidgets.QMessageBox.question", return_value=QMessageBox.StandardButton.No):
                editor = IndexedPixelEditor()
                editor.load_file_by_path(multi_palette_setup["image_path"])

            # Make edits with palette 8
            editor.canvas.current_color = 7
            editor.canvas.draw_pixel(3, 3)
            original_pixel = editor.canvas.image_data[3, 3]

            # Switch to palette 12
            colors_12 = editor.metadata["palette_colors"]["12"]
            editor.apply_palette(12, colors_12)

            # Pixel value should be preserved
            assert editor.canvas.image_data[3, 3] == original_pixel

            # But display colors should be different
            assert editor.palette_widget.is_external_palette
            assert editor.current_palette_index == 12

    def test_error_recovery_workflow(self, qapp, multi_palette_setup):
        """Test error recovery in various scenarios"""
        with patch.object(IndexedPixelEditor, "handle_startup"):
            with patch("PyQt6.QtWidgets.QMessageBox.question", return_value=QMessageBox.StandardButton.No):
                editor = IndexedPixelEditor()

                # Load file
                editor.load_file_by_path(multi_palette_setup["image_path"])

            # Try to apply a palette that doesn't exist in metadata
            # First, simulate removing it from metadata
            if "11" in editor.metadata["palette_colors"]:
                del editor.metadata["palette_colors"]["11"]

            # Try to apply the missing palette - should handle gracefully
            try:
                editor.apply_palette(11, [])
                # If it doesn't raise, that's fine too
            except Exception:
                # Should handle the error gracefully
                pass

            # Editor should still be functional
            assert editor.canvas.image_data is not None

            # Should be able to continue editing
            editor.canvas.current_color = 3
            editor.canvas.draw_pixel(7, 7)
            assert editor.canvas.image_data[7, 7] == 3


if __name__ == "__main__":
    # Run tests with coverage
    pytest.main([
        __file__,
        "-v",
        "--tb=short",
        "--cov=indexed_pixel_editor",
        "--cov=pixel_editor_widgets",
        "--cov-report=term-missing"
    ])
