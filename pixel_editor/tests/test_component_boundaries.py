#!/usr/bin/env python3
"""
Component Boundary Tests for Pixel Editor
Tests interactions at the boundaries where components meet.
These are the places where integration bugs like ProgressDialog hide.
"""

import json
from unittest.mock import Mock, patch

import numpy as np
import pytest
from PIL import Image
from PyQt6.QtCore import QPointF, Qt
from PyQt6.QtWidgets import QApplication

from pixel_editor.core import pixel_editor_constants, pixel_editor_utils

# Test all boundary interactions
from pixel_editor.core.indexed_pixel_editor import IndexedPixelEditor
from pixel_editor.core.pixel_editor_commands import DrawPixelCommand, UndoManager
from pixel_editor.core.widgets import ColorPaletteWidget
from pixel_editor.core.pixel_editor_canvas_v3 import PixelCanvasV3
from pixel_editor.core.pixel_editor_controller_v3 import PixelEditorController
from pixel_editor.core.pixel_editor_workers import FileLoadWorker, PaletteLoadWorker


class TestWidgetToWidgetBoundaries:
    """Test interactions between widget components"""

    @pytest.fixture
    def app(self):
        """Create QApplication for tests"""
        if not QApplication.instance():
            app = QApplication([])
            yield app
            app.quit()
        else:
            yield QApplication.instance()

    def test_canvas_palette_widget_boundary(self, app):
        """Test PixelCanvasV3 <-> ColorPaletteWidget interaction through controller"""
        controller = PixelEditorController()
        canvas = PixelCanvasV3(controller)
        palette = ColorPaletteWidget()

        # Test 1: Controller manages palette colors
        test_colors = [(i * 10, i * 10, i * 10) for i in range(16)]
        palette.set_palette(test_colors)

        # Set palette in controller's palette manager
        from pixel_editor.core.pixel_editor_models import PaletteModel
        palette_model = PaletteModel(colors=test_colors, name="Test Palette", index=0)
        controller.palette_manager.add_palette(0, palette_model)

        # Test getting colors through controller
        colors = controller.get_current_colors()
        assert len(colors) >= 16
        assert colors[0] == (0, 0, 0)

        # Test 2: Palette selection affecting drawing color
        palette.colorSelected.connect(controller.set_drawing_color)
        palette.current_color = 5
        palette.colorSelected.emit(5)

        assert controller.tool_manager.current_color == 5

    def test_canvas_editor_parent_boundary(self, app):
        """Test PixelCanvas <-> IndexedPixelEditor parent access"""
        with (
            patch("pixel_editor.core.indexed_pixel_editor_v3.QFileDialog"),
            patch.object(IndexedPixelEditor, "handle_startup"),
        ):
            editor = IndexedPixelEditor()
            canvas = editor.canvas

            # Canvas accessing controller (proper architecture)
            # This tests the boundary between canvas and editor via controller
            assert hasattr(canvas, "controller")
            assert canvas.controller is editor.controller

            # Test modification tracking through controller
            # Simulate a modification by directly marking the model as modified
            editor.controller.image_model.modified = True

            # Should update editor's modified state via controller
            assert editor.controller.is_modified()


class TestWorkerToUIBoundaries:
    """Test worker thread to UI component boundaries"""

    @pytest.fixture
    def app(self):
        """Create QApplication for tests"""
        if not QApplication.instance():
            app = QApplication([])
            yield app
            app.quit()
        else:
            yield QApplication.instance()

    def test_worker_result_to_editor_boundary(self, app, tmp_path):
        """Test Worker result -> Editor processing"""
        # Create test image
        test_file = tmp_path / "test.png"
        img_array = np.ones((8, 8), dtype=np.uint8)
        img = Image.fromarray(img_array, mode="P")
        img.putpalette([i % 256 for i in range(768)])
        img.save(str(test_file))

        worker = FileLoadWorker(str(test_file))

        # Test result handling pattern
        results = []

        def handle_result(image_array, metadata):
            results.append((image_array, metadata))

        worker.result.connect(handle_result)

        # Run worker
        worker.run()  # Direct call for testing

        # Should have received result
        assert len(results) == 1
        assert isinstance(results[0][0], np.ndarray)
        assert isinstance(results[0][1], dict)


class TestUtilsToComponentBoundaries:
    """Test utility functions used by components"""

    def test_debug_utils_boundary(self):
        """Test debug utilities used across components"""
        # Test that debug functions handle various inputs

        # From widgets
        pixel_editor_utils.debug_log("WIDGET", "Test message")
        pixel_editor_utils.debug_color(5, (255, 0, 0))

        # From workers
        try:
            raise ValueError("Test error")
        except Exception as e:
            pixel_editor_utils.debug_exception("WORKER", e)

        # Should not raise any exceptions
        assert True

    def test_validation_utils_boundary(self):
        """Test validation utilities at component boundaries"""
        # Test color index validation used by canvas
        valid_index = pixel_editor_utils.validate_color_index(5)
        assert valid_index == 5

        # Test clamping (function always clamps, no clamp parameter needed)
        clamped = pixel_editor_utils.validate_color_index(20)
        assert clamped == 15  # MAX_COLOR_INDEX

        # Test RGB validation used by palette widget
        valid_color = pixel_editor_utils.validate_rgb_color((255, 128, 0))
        assert valid_color == (255, 128, 0)

        # Test invalid color handling
        fixed_color = pixel_editor_utils.validate_rgb_color((300, -10, 128))
        assert fixed_color == (255, 0, 128)


class TestConstantsAcrossBoundaries:
    """Test constants used across component boundaries"""

    @pytest.fixture
    def app(self):
        """Create QApplication for tests"""
        if not QApplication.instance():
            app = QApplication([])
            yield app
            app.quit()
        else:
            yield QApplication.instance()

    def test_constants_usage_consistency(self, app):
        """Test that components use constants consistently"""
        # Check that MAX_COLORS is used consistently
        assert pixel_editor_constants.MAX_COLORS == 16

        # Verify components would use the same value
        # (In real code, they should import and use the constant)
        controller = PixelEditorController()
        PixelCanvasV3(controller)
        palette = ColorPaletteWidget()

        # Both should handle 16 colors
        test_colors = [(i, i, i) for i in range(pixel_editor_constants.MAX_COLORS)]
        palette.set_palette(test_colors)
        assert len(palette.get_palette()) == pixel_editor_constants.MAX_COLORS


class TestCommandSystemBoundaries:
    """Test undo/redo command system boundaries"""

    @pytest.fixture
    def app(self):
        """Create QApplication for tests"""
        if not QApplication.instance():
            app = QApplication([])
            yield app
            app.quit()
        else:
            yield QApplication.instance()

    def test_command_to_canvas_boundary(self, app):
        """Test Command -> Canvas interaction"""
        controller = PixelEditorController()
        canvas = PixelCanvasV3(controller)
        controller.new_file(8, 8)

        # Create command
        cmd = DrawPixelCommand(x=2, y=2, old_color=0, new_color=5)

        # In V3 architecture, commands should operate on the model adapter
        from pixel_editor.core.pixel_editor_controller_v3 import ImageModelAdapter
        adapter = ImageModelAdapter(controller.image_model)
        
        # Execute should modify the model
        cmd.execute(adapter)
        assert controller.image_model.data[2, 2] == 5

        # Unexecute should restore
        cmd.unexecute(adapter)
        assert controller.image_model.data[2, 2] == 0

    def test_manager_to_command_boundary(self, app):
        """Test UndoManager -> Command interaction"""
        controller = PixelEditorController()
        canvas = PixelCanvasV3(controller)
        controller.new_file(8, 8)
        manager = UndoManager()

        # Create and execute command through manager
        cmd = DrawPixelCommand(x=3, y=3, old_color=0, new_color=7)
        
        # In V3 architecture, commands should operate on the model adapter
        from pixel_editor.core.pixel_editor_controller_v3 import ImageModelAdapter
        adapter = ImageModelAdapter(controller.image_model)
        manager.execute_command(cmd, adapter)

        # Check state
        usage = manager.get_memory_usage()
        assert usage["can_undo"]
        assert not usage["can_redo"]

        # Undo through manager
        manager.undo(adapter)
        assert controller.image_model.data[3, 3] == 0
        usage = manager.get_memory_usage()
        assert usage["can_redo"]


class TestFileFormatBoundaries:
    """Test file format handling at boundaries"""

    def test_palette_file_format_boundary(self, tmp_path):
        """Test palette file format handling between components"""
        # Create different palette formats

        # JSON format (custom)
        json_file = tmp_path / "test.pal.json"
        json_data = {
            "format_version": "1.0",
            "colors": [[255, 0, 0], [0, 255, 0], [0, 0, 255]],
        }
        json_file.write_text(json.dumps(json_data))

        # Binary format
        bin_file = tmp_path / "test.pal"
        bin_data = bytes([255, 0, 0, 0, 255, 0, 0, 0, 255] + [0] * 759)
        bin_file.write_bytes(bin_data)

        # Test loading through worker
        json_worker = PaletteLoadWorker(str(json_file))
        bin_worker = PaletteLoadWorker(str(bin_file))

        # Both should handle their formats
        json_results = []
        bin_results = []

        json_worker.result.connect(lambda d: json_results.append(d))
        bin_worker.result.connect(lambda d: bin_results.append(d))

        json_worker.run()
        bin_worker.run()

        # Both should produce similar results
        assert len(json_results) == 1
        assert len(bin_results) == 1
        assert "colors" in json_results[0]
        assert "colors" in bin_results[0]


class TestEventHandlingBoundaries:
    """Test event handling across component boundaries"""

    @pytest.fixture
    def app(self):
        """Create QApplication for tests"""
        if not QApplication.instance():
            app = QApplication([])
            yield app
            app.quit()
        else:
            yield QApplication.instance()

    def test_keyboard_event_propagation(self, app):
        """Test keyboard events across components"""
        with (
            patch("pixel_editor.core.indexed_pixel_editor_v3.QFileDialog"),
            patch.object(IndexedPixelEditor, "handle_startup"),
        ):
            editor = IndexedPixelEditor()

            # Test keyboard shortcuts that cross boundaries
            # P key should trigger palette switching
            event = Mock()
            event.key.return_value = Qt.Key.Key_P
            event.modifiers.return_value = Qt.KeyboardModifier.NoModifier

            # Should handle the event
            editor.keyPressEvent(event)
            # (Would open palette dialog in real usage)

    def test_mouse_event_boundaries(self, app):
        """Test mouse events between canvas and editor"""
        controller = PixelEditorController()
        canvas = PixelCanvasV3(controller)
        controller.new_file(8, 8)

        # Mouse press should start drawing
        event = Mock()
        event.button.return_value = Qt.MouseButton.LeftButton
        event.position.return_value = QPointF(10, 10)

        canvas.mousePressEvent(event)
        assert canvas.drawing

        # Should create undo command on release
        canvas.mouseReleaseEvent(event)
        assert not canvas.drawing


class TestAsyncBoundaries:
    """Test asynchronous operation boundaries"""

    @pytest.fixture
    def app(self):
        """Create QApplication for tests"""
        if not QApplication.instance():
            app = QApplication([])
            yield app
            app.quit()
        else:
            yield QApplication.instance()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
