#!/usr/bin/env python3
"""
Tests for keyboard shortcuts in the pixel editor.
Tests all keyboard shortcuts work correctly.
"""

# Standard library imports
from unittest.mock import patch

# Third-party imports
import pytest
from PyQt6.QtCore import QEvent, Qt
from PyQt6.QtGui import QKeyEvent
from PyQt6.QtWidgets import QApplication

# Local imports
from pixel_editor.core.indexed_pixel_editor_v3 import IndexedPixelEditor


class TestKeyboardShortcuts:
    """Test keyboard shortcuts functionality"""

    @pytest.fixture
    def app(self):
        """Create QApplication for tests"""
        if not QApplication.instance():
            app = QApplication([])
            yield app
            app.quit()
        else:
            yield QApplication.instance()

    @pytest.fixture
    def editor(self, app):
        """Create editor instance"""
        # Mock out the startup dialog
        with patch(
            "pixel_editor.core.indexed_pixel_editor_v3.IndexedPixelEditor.handle_startup"
        ):
            editor = IndexedPixelEditor()
            # Create a new image for testing
            editor.controller.new_file(8, 8)
            yield editor
            editor.close()

    def test_color_mode_toggle_shortcut_c(self, editor):
        """Test 'C' key toggles color mode"""
        # Get initial state
        checkbox = editor.options_panel.apply_palette_checkbox
        initial_state = checkbox.isChecked()

        # Press C key
        event = QKeyEvent(
            QEvent.Type.KeyPress, Qt.Key.Key_C, Qt.KeyboardModifier.NoModifier
        )
        editor.keyPressEvent(event)

        # Verify state changed
        assert checkbox.isChecked() != initial_state

        # Press C again
        editor.keyPressEvent(event)

        # Verify state changed back
        assert checkbox.isChecked() == initial_state

    def test_grid_toggle_shortcut_g(self, editor):
        """Test 'G' key toggles grid visibility"""
        # Get initial state
        checkbox = editor.options_panel.grid_checkbox
        initial_state = checkbox.isChecked()

        # Press G key
        event = QKeyEvent(
            QEvent.Type.KeyPress, Qt.Key.Key_G, Qt.KeyboardModifier.NoModifier
        )
        editor.keyPressEvent(event)

        # Verify state changed
        assert checkbox.isChecked() != initial_state

        # Verify canvas grid state changed
        assert editor.canvas.grid_visible == checkbox.isChecked()

    def test_color_picker_shortcut_i(self, editor):
        """Test 'I' key switches to color picker tool"""
        # Start with a different tool
        editor.tool_panel.set_tool("pencil")
        assert editor.controller.tool_manager.current_tool_name == "pencil"

        # Press I key
        event = QKeyEvent(
            QEvent.Type.KeyPress, Qt.Key.Key_I, Qt.KeyboardModifier.NoModifier
        )
        editor.keyPressEvent(event)

        # Verify tool changed to picker
        assert editor.controller.tool_manager.current_tool_name == "picker"
        assert editor.tool_panel.get_current_tool() == "picker"

    def test_palette_switcher_shortcut_p(self, editor):
        """Test 'P' key opens palette switcher when palettes available"""
        # Mock palette metadata
        with patch.object(
            editor.controller, "has_metadata_palettes", return_value=True
        ):
            with patch.object(editor, "show_palette_switcher") as mock_show:
                # Press P key
                event = QKeyEvent(
                    QEvent.Type.KeyPress, Qt.Key.Key_P, Qt.KeyboardModifier.NoModifier
                )
                editor.keyPressEvent(event)

                # Verify palette switcher was called
                mock_show.assert_called_once()

    def test_palette_switcher_not_called_without_palettes(self, editor):
        """Test 'P' key does nothing when no palettes available"""
        # Ensure no metadata palettes
        with patch.object(
            editor.controller, "has_metadata_palettes", return_value=False
        ):
            with patch.object(editor, "show_palette_switcher") as mock_show:
                # Press P key
                event = QKeyEvent(
                    QEvent.Type.KeyPress, Qt.Key.Key_P, Qt.KeyboardModifier.NoModifier
                )
                editor.keyPressEvent(event)

                # Verify palette switcher was NOT called
                mock_show.assert_not_called()

    def test_file_operations_shortcuts(self, editor):
        """Test file operation shortcuts are properly configured"""
        # Get file menu
        file_menu = editor.menuBar().actions()[0].menu()

        # Find actions by text
        new_action = None
        open_action = None
        save_action = None

        for action in file_menu.actions():
            if action.text() == "New":
                new_action = action
            elif action.text() == "Open":
                open_action = action
            elif action.text() == "Save":
                save_action = action

        # Verify shortcuts are set
        assert new_action is not None
        assert new_action.shortcut().toString() == "Ctrl+N"

        assert open_action is not None
        assert open_action.shortcut().toString() == "Ctrl+O"

        assert save_action is not None
        assert save_action.shortcut().toString() == "Ctrl+S"

    def test_zoom_shortcuts(self, editor):
        """Test zoom shortcuts are properly configured"""
        # Get view menu
        view_menu = editor.menuBar().actions()[2].menu()

        # Find zoom actions
        zoom_in_action = None
        zoom_out_action = None

        for action in view_menu.actions():
            if action.text() == "Zoom In":
                zoom_in_action = action
            elif action.text() == "Zoom Out":
                zoom_out_action = action

        # Verify shortcuts are set
        assert zoom_in_action is not None
        assert zoom_in_action.shortcut().toString() == "Ctrl++"

        assert zoom_out_action is not None
        assert zoom_out_action.shortcut().toString() == "Ctrl+-"

    def test_modifier_keys_dont_trigger_shortcuts(self, editor):
        """Test that shortcuts don't trigger with wrong modifiers"""
        # Get initial states
        color_checkbox = editor.options_panel.apply_palette_checkbox
        grid_checkbox = editor.options_panel.grid_checkbox
        initial_color_state = color_checkbox.isChecked()
        initial_grid_state = grid_checkbox.isChecked()
        initial_tool = editor.controller.tool_manager.current_tool_name

        # Test C with Ctrl modifier - should not toggle color mode
        event = QKeyEvent(
            QEvent.Type.KeyPress, Qt.Key.Key_C, Qt.KeyboardModifier.ControlModifier
        )
        editor.keyPressEvent(event)
        assert color_checkbox.isChecked() == initial_color_state

        # Test G with Alt modifier - should not toggle grid
        event = QKeyEvent(
            QEvent.Type.KeyPress, Qt.Key.Key_G, Qt.KeyboardModifier.AltModifier
        )
        editor.keyPressEvent(event)
        assert grid_checkbox.isChecked() == initial_grid_state

        # Test I with Shift modifier - should not change tool
        event = QKeyEvent(
            QEvent.Type.KeyPress, Qt.Key.Key_I, Qt.KeyboardModifier.ShiftModifier
        )
        editor.keyPressEvent(event)
        assert editor.controller.tool_manager.current_tool_name == initial_tool

    def test_keyboard_event_propagation(self, editor):
        """Test that unhandled keys are propagated to parent"""
        # Mock the parent keyPressEvent
        with patch.object(
            IndexedPixelEditor.__bases__[0], "keyPressEvent"
        ) as mock_parent:
            # Press an unhandled key
            event = QKeyEvent(
                QEvent.Type.KeyPress, Qt.Key.Key_X, Qt.KeyboardModifier.NoModifier
            )
            editor.keyPressEvent(event)

            # Verify parent was called
            mock_parent.assert_called_once_with(event)

    def test_multiple_shortcuts_in_sequence(self, editor):
        """Test multiple shortcuts work correctly in sequence"""
        # Initial state
        color_checkbox = editor.options_panel.apply_palette_checkbox
        grid_checkbox = editor.options_panel.grid_checkbox

        # Toggle color mode
        event_c = QKeyEvent(
            QEvent.Type.KeyPress, Qt.Key.Key_C, Qt.KeyboardModifier.NoModifier
        )
        editor.keyPressEvent(event_c)
        color_state_1 = color_checkbox.isChecked()

        # Toggle grid
        event_g = QKeyEvent(
            QEvent.Type.KeyPress, Qt.Key.Key_G, Qt.KeyboardModifier.NoModifier
        )
        editor.keyPressEvent(event_g)
        grid_state_1 = grid_checkbox.isChecked()

        # Switch to picker tool
        event_i = QKeyEvent(
            QEvent.Type.KeyPress, Qt.Key.Key_I, Qt.KeyboardModifier.NoModifier
        )
        editor.keyPressEvent(event_i)

        # Verify all changes happened
        assert editor.controller.tool_manager.current_tool_name == "picker"

        # Toggle color mode again
        editor.keyPressEvent(event_c)
        assert color_checkbox.isChecked() != color_state_1

        # Toggle grid again
        editor.keyPressEvent(event_g)
        assert grid_checkbox.isChecked() != grid_state_1

    def test_brush_size_shortcut_1(self, editor):
        """Test that '1' key sets brush size to 1"""
        # Set initial brush size to something different
        editor.controller.set_brush_size(2)
        assert editor.controller.tool_manager.get_brush_size() == 2
        
        # Press '1' key
        event = QKeyEvent(
            QEvent.Type.KeyPress, Qt.Key.Key_1, Qt.KeyboardModifier.NoModifier
        )
        editor.keyPressEvent(event)
        
        # Verify brush size changed to 1
        assert editor.controller.tool_manager.get_brush_size() == 1
        assert editor.tool_panel.get_brush_size() == 1

    def test_brush_size_shortcut_2(self, editor):
        """Test that '2' key sets brush size to 2"""
        # Set initial brush size to 1
        editor.controller.set_brush_size(1)
        assert editor.controller.tool_manager.get_brush_size() == 1
        
        # Press '2' key
        event = QKeyEvent(
            QEvent.Type.KeyPress, Qt.Key.Key_2, Qt.KeyboardModifier.NoModifier
        )
        editor.keyPressEvent(event)
        
        # Verify brush size changed to 2
        assert editor.controller.tool_manager.get_brush_size() == 2
        assert editor.tool_panel.get_brush_size() == 2

    def test_brush_size_shortcuts_with_modifiers(self, editor):
        """Test that brush size shortcuts don't work with modifiers"""
        # Set initial brush size
        initial_size = editor.controller.tool_manager.get_brush_size()
        
        # Test 1 with Ctrl modifier - should not change brush size
        event = QKeyEvent(
            QEvent.Type.KeyPress, Qt.Key.Key_1, Qt.KeyboardModifier.ControlModifier
        )
        editor.keyPressEvent(event)
        assert editor.controller.tool_manager.get_brush_size() == initial_size
        
        # Test 2 with Shift modifier - should not change brush size
        event = QKeyEvent(
            QEvent.Type.KeyPress, Qt.Key.Key_2, Qt.KeyboardModifier.ShiftModifier
        )
        editor.keyPressEvent(event)
        assert editor.controller.tool_manager.get_brush_size() == initial_size

    def test_brush_size_shortcuts_sequence(self, editor):
        """Test brush size shortcuts work in sequence"""
        # Start with size 1
        editor.controller.set_brush_size(1)
        
        # Press '2' to change to size 2
        event_2 = QKeyEvent(
            QEvent.Type.KeyPress, Qt.Key.Key_2, Qt.KeyboardModifier.NoModifier
        )
        editor.keyPressEvent(event_2)
        assert editor.controller.tool_manager.get_brush_size() == 2
        
        # Press '1' to change back to size 1
        event_1 = QKeyEvent(
            QEvent.Type.KeyPress, Qt.Key.Key_1, Qt.KeyboardModifier.NoModifier
        )
        editor.keyPressEvent(event_1)
        assert editor.controller.tool_manager.get_brush_size() == 1
        
        # Press '2' again
        editor.keyPressEvent(event_2)
        assert editor.controller.tool_manager.get_brush_size() == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
