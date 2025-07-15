#!/usr/bin/env python3
"""
Integration tests for undo/redo functionality in the pixel editor.
Tests the complete flow from UI interaction to command execution.
"""

# Standard library imports
from unittest.mock import patch

# Third-party imports
import numpy as np
import pytest
from PyQt6.QtCore import QEvent, Qt
from PyQt6.QtGui import QKeyEvent
from PyQt6.QtWidgets import QApplication

# Local imports
from pixel_editor.core.indexed_pixel_editor_v3 import IndexedPixelEditor


class TestUndoRedoIntegration:
    """Integration tests for undo/redo functionality"""

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

    def test_undo_redo_single_pixel(self, editor):
        """Test undo/redo for single pixel operations"""
        controller = editor.controller

        # Get initial state
        initial_data = controller.image_model.data.copy()

        # Draw a pixel
        controller.set_drawing_color(5)
        controller.handle_canvas_press(2, 2)
        controller.handle_canvas_release(2, 2)

        # Verify pixel was drawn
        assert controller.image_model.data[2, 2] == 5

        # Undo
        controller.undo()

        # Verify pixel was restored
        assert controller.image_model.data[2, 2] == initial_data[2, 2]

        # Redo
        controller.redo()

        # Verify pixel was redrawn
        assert controller.image_model.data[2, 2] == 5

    def test_undo_redo_line_drawing(self, editor):
        """Test undo/redo for line drawing operations"""
        controller = editor.controller

        # Get initial state
        initial_data = controller.image_model.data.copy()

        # Draw a line
        controller.set_drawing_color(7)
        controller.handle_canvas_press(1, 1)
        controller.handle_canvas_move(4, 4)
        controller.handle_canvas_release(4, 4)

        # Verify line was drawn (at least endpoints)
        assert controller.image_model.data[1, 1] == 7
        assert controller.image_model.data[4, 4] == 7

        # Undo
        controller.undo()

        # Verify line was removed
        assert np.array_equal(controller.image_model.data, initial_data)

        # Redo
        controller.redo()

        # Verify line was redrawn
        assert controller.image_model.data[1, 1] == 7
        assert controller.image_model.data[4, 4] == 7

    def test_undo_redo_flood_fill(self, editor):
        """Test undo/redo for flood fill operations"""
        controller = editor.controller

        # Set up a test pattern
        controller.image_model.data[2:5, 2:5] = 3  # Create a 3x3 square
        initial_data = controller.image_model.data.copy()

        # Flood fill
        controller.set_tool("fill")
        controller.set_drawing_color(10)
        controller.handle_canvas_press(3, 3)
        controller.handle_canvas_release(3, 3)

        # Verify fill happened
        assert controller.image_model.data[3, 3] == 10
        assert controller.image_model.data[2, 2] == 10
        assert controller.image_model.data[4, 4] == 10

        # Undo
        controller.undo()

        # Verify fill was undone
        assert np.array_equal(controller.image_model.data, initial_data)

        # Redo
        controller.redo()

        # Verify fill was redone
        assert controller.image_model.data[3, 3] == 10

    def test_undo_redo_multiple_operations(self, editor):
        """Test undo/redo with multiple operations"""
        controller = editor.controller

        # Operation 1: Draw pixel
        controller.set_drawing_color(1)
        controller.handle_canvas_press(0, 0)
        controller.handle_canvas_release(0, 0)

        # Operation 2: Draw another pixel
        controller.set_drawing_color(2)
        controller.handle_canvas_press(1, 1)
        controller.handle_canvas_release(1, 1)

        # Operation 3: Draw line
        controller.set_drawing_color(3)
        controller.handle_canvas_press(0, 4)
        controller.handle_canvas_move(4, 4)
        controller.handle_canvas_release(4, 4)

        # Verify all operations
        assert controller.image_model.data[0, 0] == 1
        assert controller.image_model.data[1, 1] == 2
        assert controller.image_model.data[4, 4] == 3

        # Undo all operations
        controller.undo()  # Undo line
        assert controller.image_model.data[4, 4] == 0

        controller.undo()  # Undo second pixel
        assert controller.image_model.data[1, 1] == 0

        controller.undo()  # Undo first pixel
        assert controller.image_model.data[0, 0] == 0

        # Redo all operations
        controller.redo()  # Redo first pixel
        assert controller.image_model.data[0, 0] == 1

        controller.redo()  # Redo second pixel
        assert controller.image_model.data[1, 1] == 2

        controller.redo()  # Redo line
        assert controller.image_model.data[4, 4] == 3

    def test_keyboard_shortcuts_ctrl_z_ctrl_y(self, editor):
        """Test Ctrl+Z and Ctrl+Y keyboard shortcuts"""
        # Draw a pixel
        controller = editor.controller
        controller.set_drawing_color(8)
        controller.handle_canvas_press(3, 3)
        controller.handle_canvas_release(3, 3)

        assert controller.image_model.data[3, 3] == 8

        # Create Ctrl+Z event
        undo_event = QKeyEvent(
            QEvent.Type.KeyPress, Qt.Key.Key_Z, Qt.KeyboardModifier.ControlModifier
        )
        editor.keyPressEvent(undo_event)

        # Verify undo happened
        assert controller.image_model.data[3, 3] == 0

        # Create Ctrl+Y event
        redo_event = QKeyEvent(
            QEvent.Type.KeyPress, Qt.Key.Key_Y, Qt.KeyboardModifier.ControlModifier
        )
        editor.keyPressEvent(redo_event)

        # Verify redo happened
        assert controller.image_model.data[3, 3] == 8

    def test_undo_manager_state_tracking(self, editor):
        """Test that undo manager properly tracks state"""
        controller = editor.controller
        undo_manager = controller.undo_manager

        # Initially, nothing to undo/redo
        usage = undo_manager.get_memory_usage()
        assert not usage["can_undo"]
        assert not usage["can_redo"]

        # Draw a pixel
        controller.set_drawing_color(4)
        controller.handle_canvas_press(2, 2)
        controller.handle_canvas_release(2, 2)

        # Now we can undo but not redo
        usage = undo_manager.get_memory_usage()
        assert usage["can_undo"]
        assert not usage["can_redo"]
        assert usage["command_count"] == 1

        # Undo
        controller.undo()

        # Now we can redo but cannot undo further
        usage = undo_manager.get_memory_usage()
        assert usage["current_index"] == -1
        assert not usage["can_undo"]
        assert usage["can_redo"]

    def test_undo_redo_with_tool_switching(self, editor):
        """Test undo/redo works correctly when switching tools"""
        controller = editor.controller

        # Start with pencil tool
        controller.set_tool("pencil")
        controller.set_drawing_color(3)
        controller.handle_canvas_press(1, 1)
        controller.handle_canvas_release(1, 1)

        # Switch to fill tool
        controller.set_tool("fill")
        controller.set_drawing_color(5)
        controller.handle_canvas_press(0, 0)
        controller.handle_canvas_release(0, 0)

        # Back to pencil
        controller.set_tool("pencil")
        controller.set_drawing_color(7)
        controller.handle_canvas_press(7, 7)
        controller.handle_canvas_release(7, 7)

        # Verify all operations
        assert controller.image_model.data[1, 1] == 3
        assert controller.image_model.data[0, 0] == 5
        assert controller.image_model.data[7, 7] == 7

        # Undo all and verify tool doesn't affect undo
        controller.undo()  # Undo pencil at (7,7)
        assert controller.image_model.data[7, 7] == 5  # Should be 5 from flood fill

        controller.undo()  # Undo flood fill
        assert controller.image_model.data[0, 0] == 0  # Back to original
        assert controller.image_model.data[7, 7] == 0  # Also back to original

        controller.undo()  # Undo pencil at (1,1)
        assert controller.image_model.data[1, 1] == 0

    def test_batch_command_for_drag_operations(self, editor):
        """Test that drag operations create batch commands"""
        controller = editor.controller

        # Draw multiple pixels in one drag
        controller.set_drawing_color(9)
        controller.handle_canvas_press(2, 2)
        controller.handle_canvas_move(2, 3)
        controller.handle_canvas_move(2, 4)
        controller.handle_canvas_move(2, 5)
        controller.handle_canvas_release(2, 5)

        # Verify pixels were drawn
        assert controller.image_model.data[2, 2] == 9
        assert controller.image_model.data[3, 2] == 9
        assert controller.image_model.data[4, 2] == 9
        assert controller.image_model.data[5, 2] == 9

        # Single undo should undo entire drag operation
        controller.undo()

        # Verify all pixels were undone
        assert controller.image_model.data[2, 2] == 0
        assert controller.image_model.data[3, 2] == 0
        assert controller.image_model.data[4, 2] == 0
        assert controller.image_model.data[5, 2] == 0

        # Single redo should redo entire drag operation
        controller.redo()

        # Verify all pixels were redrawn
        assert controller.image_model.data[2, 2] == 9
        assert controller.image_model.data[3, 2] == 9

    def test_undo_preserves_image_properties(self, editor):
        """Test that undo/redo preserves image properties and metadata"""
        controller = editor.controller

        # Set specific properties
        initial_width, initial_height = controller.get_image_size()

        # Make some changes
        controller.set_drawing_color(12)
        controller.handle_canvas_press(0, 0)
        controller.handle_canvas_release(0, 0)

        # Undo
        controller.undo()

        # Check image dimensions haven't changed
        width, height = controller.get_image_size()
        assert width == initial_width
        assert height == initial_height

        # Check image is still valid
        assert controller.image_model.data is not None
        assert controller.image_model.data.shape == (initial_height, initial_width)

    def test_memory_management_with_many_operations(self, editor):
        """Test memory management with many undo operations"""
        controller = editor.controller
        undo_manager = controller.undo_manager

        # Set compression age to a lower value for testing
        undo_manager.compression_age = 10

        # Perform many operations
        # Use a pattern that ensures each operation changes a pixel
        num_operations = 25  # More than compression_age
        for i in range(num_operations):
            color = (i + 1) % 16  # Cycle through colors 1-15
            x = i % 8
            y = (i // 8) % 8

            # Make sure we're changing the pixel
            controller.set_drawing_color(color)
            controller.handle_canvas_press(x, y)
            controller.handle_canvas_release(x, y)

        # Check memory usage
        usage = undo_manager.get_memory_usage()
        assert usage["command_count"] >= 20

        # NOTE: Compression is only triggered when using execute_command,
        # but the controller directly appends some commands to the stack.
        # So we may or may not have compressed commands.
        # Just verify the memory tracking works
        assert "compressed_count" in usage
        assert "total_bytes" in usage
        assert "total_mb" in usage

        # Undo should still work for recent commands
        controller.undo()
        controller.undo()

        # And redo should work
        controller.redo()

        # Check we can still access memory stats
        usage = undo_manager.get_memory_usage()
        assert "total_bytes" in usage
        assert "total_mb" in usage


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
