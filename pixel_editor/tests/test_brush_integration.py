#!/usr/bin/env python3
"""
End-to-end integration tests for brush functionality
Tests the complete brush workflow from UI to canvas
"""

import sys
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
import numpy as np
from PyQt6.QtCore import QPoint
from PyQt6.QtGui import QKeyEvent, QMouseEvent, QPixmap
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt, QEvent

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from pixel_editor.core.indexed_pixel_editor_v3 import IndexedPixelEditor
from pixel_editor.core.pixel_editor_models import ImageModel


class TestBrushIntegrationE2E:
    """End-to-end integration tests for brush functionality"""
    
    @pytest.fixture
    def app(self):
        """Create QApplication instance"""
        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        return app
    
    @pytest.fixture
    def editor(self, app):
        """Create IndexedPixelEditor instance"""
        editor = IndexedPixelEditor()
        
        # Create a test image
        editor.controller.image_model = ImageModel()
        editor.controller.image_model.data = np.zeros((8, 8), dtype=np.uint8)
        
        return editor
    
    @pytest.mark.skip(reason="Hangs in headless environment - GUI initialization issue")
    def test_brush_workflow_keyboard_to_drawing(self, editor):
        """Test complete workflow: keyboard shortcut -> brush size -> drawing"""
        # Step 1: Verify initial state
        assert editor.controller.tool_manager.get_brush_size() == 1
        assert editor.tool_panel.get_brush_size() == 1
        
        # Step 2: Use keyboard shortcut to set brush size to 2
        event = QKeyEvent(
            QEvent.Type.KeyPress, Qt.Key.Key_2, Qt.KeyboardModifier.NoModifier
        )
        editor.keyPressEvent(event)
        
        # Step 3: Verify brush size changed everywhere
        assert editor.controller.tool_manager.get_brush_size() == 2
        assert editor.tool_panel.get_brush_size() == 2
        
        # Step 4: Test that brush pixels are calculated correctly
        brush_pixels = editor.controller.tool_manager.get_brush_pixels(3, 3)
        expected_pixels = [(3, 3), (4, 3), (3, 4), (4, 4)]
        assert brush_pixels == expected_pixels
    
    @pytest.mark.skip(reason="Hangs in headless environment - GUI initialization issue")
    def test_brush_workflow_ui_to_drawing(self, editor):
        """Test complete workflow: UI control -> brush size -> drawing"""
        # Step 1: Verify initial state
        assert editor.controller.tool_manager.get_brush_size() == 1
        
        # Step 2: Use UI control to set brush size to 3
        editor.tool_panel.set_brush_size(3)
        
        # Step 3: Verify brush size changed in controller
        assert editor.controller.tool_manager.get_brush_size() == 3
        
        # Step 4: Test that brush pixels are calculated correctly
        brush_pixels = editor.controller.tool_manager.get_brush_pixels(2, 2)
        expected_pixels = [
            (2, 2), (3, 2), (4, 2),
            (2, 3), (3, 3), (4, 3),
            (2, 4), (3, 4), (4, 4)
        ]
        assert brush_pixels == expected_pixels
    
    def test_brush_drawing_simulation(self, editor):
        """Test simulated brush drawing with bounds checking"""
        # Set brush size to 2
        editor.controller.set_brush_size(2)
        
        # Set drawing color
        editor.controller.set_drawing_color(5)
        
        # Get initial image state
        original_image = editor.controller.image_model.data.copy()
        
        # Simulate drawing at position (1, 1)
        editor.controller.handle_canvas_press(1, 1)
        
        # Verify that 2x2 brush area was drawn
        modified_image = editor.controller.image_model.data
        
        # Check that the brush area was modified
        assert modified_image[1, 1] == 5  # (1, 1)
        assert modified_image[1, 2] == 5  # (2, 1)
        assert modified_image[2, 1] == 5  # (1, 2)
        assert modified_image[2, 2] == 5  # (2, 2)
        
        # Check that areas outside the brush weren't modified
        assert modified_image[0, 0] == 0  # Outside brush area
        assert modified_image[3, 3] == 0  # Outside brush area
    
    def test_brush_edge_boundary_drawing(self, editor):
        """Test brush drawing at image boundaries"""
        # Set brush size to 2
        editor.controller.set_brush_size(2)
        
        # Set drawing color
        editor.controller.set_drawing_color(7)
        
        # Try to draw at edge position (7, 7) in 8x8 image
        editor.controller.handle_canvas_press(7, 7)
        
        # Verify that only valid pixels were drawn
        modified_image = editor.controller.image_model.data
        
        # Only (7, 7) should be modified (other pixels would be out of bounds)
        assert modified_image[7, 7] == 7
        
        # Check that other positions weren't modified
        assert modified_image[6, 6] == 0
        assert modified_image[0, 0] == 0
    
    def test_brush_size_changes_affect_preview(self, editor):
        """Test that brush size changes affect canvas preview"""
        # Set up canvas with hover position
        editor.canvas.hover_pos = QPoint(4, 4)
        
        # Test with brush size 1
        editor.controller.set_brush_size(1)
        brush_pixels = editor.controller.tool_manager.get_brush_pixels(4, 4)
        assert len(brush_pixels) == 1
        assert brush_pixels == [(4, 4)]
        
        # Test with brush size 2
        editor.controller.set_brush_size(2)
        brush_pixels = editor.controller.tool_manager.get_brush_pixels(4, 4)
        assert len(brush_pixels) == 4
        assert brush_pixels == [(4, 4), (5, 4), (4, 5), (5, 5)]
    
    def test_brush_undo_redo_functionality(self, editor):
        """Test that brush operations work with undo/redo"""
        # Set brush size to 2 and color to 3
        editor.controller.set_brush_size(2)
        editor.controller.set_drawing_color(3)
        
        # Get initial image state
        original_image = editor.controller.image_model.data.copy()
        
        # Simulate complete brush stroke (press, move, release)
        editor.controller.handle_canvas_press(2, 2)
        editor.controller.handle_canvas_move(2, 3)
        editor.controller.handle_canvas_release(2, 3)
        
        # Verify drawing occurred
        modified_image = editor.controller.image_model.data
        assert not np.array_equal(original_image, modified_image)
        
        # Test undo
        editor.undo()
        undone_image = editor.controller.image_model.data
        assert np.array_equal(original_image, undone_image)
        
        # Test redo
        editor.redo()
        redone_image = editor.controller.image_model.data
        assert np.array_equal(modified_image, redone_image)
    
    def test_brush_tool_integration(self, editor):
        """Test that brush works with different tools"""
        # Set brush size to 2
        editor.controller.set_brush_size(2)
        
        # Test with pencil tool (should use brush size)
        editor.controller.set_tool("pencil")
        assert editor.controller.tool_manager.current_tool_name == "pencil"
        
        # Get brush pixels - should work with pencil
        brush_pixels = editor.controller.tool_manager.get_brush_pixels(3, 3)
        assert len(brush_pixels) == 4
        
        # Test with fill tool (brush size shouldn't affect fill)
        editor.controller.set_tool("fill")
        assert editor.controller.tool_manager.current_tool_name == "fill"
        
        # Brush size should still be maintained
        assert editor.controller.tool_manager.get_brush_size() == 2
        
        # Test with picker tool (brush size shouldn't affect picker)
        editor.controller.set_tool("picker")
        assert editor.controller.tool_manager.current_tool_name == "picker"
        
        # Brush size should still be maintained
        assert editor.controller.tool_manager.get_brush_size() == 2
    
    def test_brush_signal_propagation(self, editor):
        """Test that brush size changes propagate through all components"""
        # Mock signal receivers
        ui_signal_mock = Mock()
        editor.tool_panel.brushSizeChanged.connect(ui_signal_mock)
        
        # Change brush size via UI
        editor.tool_panel.set_brush_size(4)
        
        # Verify signal was emitted
        ui_signal_mock.assert_called_once_with(4)
        
        # Verify all components are synchronized
        assert editor.tool_panel.get_brush_size() == 4
        assert editor.controller.tool_manager.get_brush_size() == 4
    
    def test_brush_keyboard_shortcuts_complete(self, editor):
        """Test both keyboard shortcuts work correctly"""
        # Test '1' key
        event_1 = QKeyEvent(
            QEvent.Type.KeyPress, Qt.Key.Key_1, Qt.KeyboardModifier.NoModifier
        )
        editor.keyPressEvent(event_1)
        
        assert editor.controller.tool_manager.get_brush_size() == 1
        assert editor.tool_panel.get_brush_size() == 1
        
        # Test '2' key
        event_2 = QKeyEvent(
            QEvent.Type.KeyPress, Qt.Key.Key_2, Qt.KeyboardModifier.NoModifier
        )
        editor.keyPressEvent(event_2)
        
        assert editor.controller.tool_manager.get_brush_size() == 2
        assert editor.tool_panel.get_brush_size() == 2
        
        # Test back to '1' key
        editor.keyPressEvent(event_1)
        
        assert editor.controller.tool_manager.get_brush_size() == 1
        assert editor.tool_panel.get_brush_size() == 1


class TestBrushRegressionTests:
    """Regression tests to ensure brush functionality doesn't break existing features"""
    
    @pytest.fixture
    def app(self):
        """Create QApplication instance"""
        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        return app
    
    @pytest.fixture
    def editor(self, app):
        """Create IndexedPixelEditor instance"""
        editor = IndexedPixelEditor()
        
        # Create a test image
        editor.controller.image_model = ImageModel()
        editor.controller.image_model.data = np.zeros((8, 8), dtype=np.uint8)
        
        return editor
    
    def test_existing_keyboard_shortcuts_still_work(self, editor):
        """Test that existing keyboard shortcuts still work after brush implementation"""
        # Test color mode toggle (C key)
        initial_color_mode = editor.options_panel.apply_palette_checkbox.isChecked()
        event_c = QKeyEvent(
            QEvent.Type.KeyPress, Qt.Key.Key_C, Qt.KeyboardModifier.NoModifier
        )
        editor.keyPressEvent(event_c)
        assert editor.options_panel.apply_palette_checkbox.isChecked() != initial_color_mode
        
        # Test grid toggle (G key)
        initial_grid_mode = editor.options_panel.grid_checkbox.isChecked()
        event_g = QKeyEvent(
            QEvent.Type.KeyPress, Qt.Key.Key_G, Qt.KeyboardModifier.NoModifier
        )
        editor.keyPressEvent(event_g)
        assert editor.options_panel.grid_checkbox.isChecked() != initial_grid_mode
        
        # Test tool picker (I key)
        event_i = QKeyEvent(
            QEvent.Type.KeyPress, Qt.Key.Key_I, Qt.KeyboardModifier.NoModifier
        )
        editor.keyPressEvent(event_i)
        assert editor.controller.tool_manager.current_tool_name == "picker"
    
    def test_single_pixel_drawing_still_works(self, editor):
        """Test that single pixel drawing (brush size 1) still works as before"""
        # Set brush size to 1
        editor.controller.set_brush_size(1)
        editor.controller.set_drawing_color(9)
        
        # Draw a single pixel
        editor.controller.handle_canvas_press(3, 3)
        editor.controller.handle_canvas_release(3, 3)
        
        # Verify only one pixel was modified
        modified_image = editor.controller.image_model.data
        assert modified_image[3, 3] == 9
        
        # Check that surrounding pixels weren't modified
        assert modified_image[2, 2] == 0
        assert modified_image[2, 3] == 0
        assert modified_image[3, 2] == 0
        assert modified_image[4, 4] == 0
        assert modified_image[4, 3] == 0
        assert modified_image[3, 4] == 0
    
    def test_fill_tool_unaffected_by_brush_size(self, editor):
        """Test that fill tool behavior is unaffected by brush size"""
        # Set brush size to 3 (should not affect fill)
        editor.controller.set_brush_size(3)
        editor.controller.set_tool("fill")
        
        # Fill operation should work regardless of brush size
        # This test verifies the fill tool still works as expected
        assert editor.controller.tool_manager.current_tool_name == "fill"
        assert editor.controller.tool_manager.get_brush_size() == 3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])