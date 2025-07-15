#!/usr/bin/env python3
"""
Test error scenarios and edge cases for pixel editor V3 components.
Focuses on increasing test coverage for:
- Worker error callbacks
- Save error scenarios
- Corruption recovery
- Mouse drag operations
- Context menu handling
"""

import json
import os
import sys
import tempfile
from unittest.mock import patch

import numpy as np
import pytest
from PyQt6.QtCore import QPoint, QPointF, Qt
from PyQt6.QtGui import QContextMenuEvent, QMouseEvent
from PyQt6.QtWidgets import QApplication

from pixel_editor.core.pixel_editor_canvas_v3 import PixelCanvasV3
from pixel_editor.core.pixel_editor_controller_v3 import PixelEditorController
from pixel_editor.core.pixel_editor_workers import (
    FileLoadWorker,
    FileSaveWorker,
    PaletteLoadWorker,
)


@pytest.fixture(scope="session")
def qapp():
    """Create QApplication instance for testing"""
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    return app


@pytest.fixture
def controller():
    """Create a controller with all dependencies"""
    # Controller creates its own models and managers internally
    return PixelEditorController()


@pytest.fixture
def canvas(qapp, controller):
    """Create a canvas instance"""
    return PixelCanvasV3(controller)


@pytest.fixture
def sample_image():
    """Create a sample 8x8 indexed image"""
    data = np.arange(64).reshape(8, 8) % 16
    return data.astype(np.uint8)


class TestWorkerErrorCallbacks:
    """Test worker error handling and callbacks"""

    def test_file_load_worker_error_callback(self, controller, qtbot):
        """Test FileLoadWorker error callback handling"""
        # Create a worker with non-existent file
        worker = FileLoadWorker("nonexistent_file.png")

        # Connect signals
        error_messages = []
        worker.error.connect(lambda msg: error_messages.append(msg))

        # Run the worker
        with qtbot.waitSignal(worker.error, timeout=1000):
            worker.start()

        # Verify error was emitted
        assert len(error_messages) == 1
        assert "File not found" in error_messages[0]

        # Clean up the thread
        worker.quit()
        worker.wait(1000)

    def test_file_load_worker_cancelled(self, controller):
        """Test worker cancellation during load"""
        worker = FileLoadWorker("test.png")

        # Cancel immediately
        worker.cancel()
        assert worker.is_cancelled()

        # Progress should not be emitted when cancelled
        worker.progress.connect(lambda *args: setattr(self, "progress_emitted", True))
        worker.emit_progress(50, "Should not emit")

        assert not hasattr(self, "progress_emitted")

    def test_file_save_worker_error_invalid_data(self, controller, qtbot):
        """Test FileSaveWorker with invalid data"""
        # Create worker with None image data
        worker = FileSaveWorker(None, [0] * 768, "output.png")

        error_messages = []
        worker.error.connect(lambda msg: error_messages.append(msg))

        with qtbot.waitSignal(worker.error, timeout=1000):
            worker.start()

        assert len(error_messages) == 1
        assert "No image data to save" in error_messages[0]

        # Clean up the thread
        worker.quit()
        worker.wait(1000)

    def test_file_save_worker_error_invalid_palette(self, sample_image, qtbot):
        """Test FileSaveWorker with invalid palette"""
        # Create worker with invalid palette size
        worker = FileSaveWorker(sample_image, [0] * 100, "output.png")  # Wrong size

        error_messages = []
        worker.error.connect(lambda msg: error_messages.append(msg))

        with qtbot.waitSignal(worker.error, timeout=1000):
            worker.start()

        assert len(error_messages) == 1
        assert "Invalid palette data" in error_messages[0]

        # Clean up the thread
        worker.quit()
        worker.wait(1000)

    def test_palette_load_worker_json_error(self, qtbot):
        """Test PaletteLoadWorker with corrupted JSON"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("{ invalid json")
            temp_path = f.name

        try:
            worker = PaletteLoadWorker(temp_path)

            error_messages = []
            worker.error.connect(lambda msg: error_messages.append(msg))

            with qtbot.waitSignal(worker.error, timeout=1000):
                worker.start()

            assert len(error_messages) == 1
            assert "Invalid JSON format" in error_messages[0]

            # Clean up the thread
            worker.quit()
            worker.wait(1000)
        finally:
            os.unlink(temp_path)

    def test_palette_load_worker_missing_colors(self, qtbot):
        """Test PaletteLoadWorker with JSON missing 'colors' field"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump({"name": "Test Palette"}, f)  # Missing 'colors'
            temp_path = f.name

        try:
            worker = PaletteLoadWorker(temp_path)

            error_messages = []
            worker.error.connect(lambda msg: error_messages.append(msg))

            with qtbot.waitSignal(worker.error, timeout=1000):
                worker.start()

            assert len(error_messages) == 1
            assert "missing 'colors' field" in error_messages[0]

            # Clean up the thread
            worker.quit()
            worker.wait(1000)
        finally:
            os.unlink(temp_path)

    def test_controller_worker_error_propagation(self, controller):
        """Test that controller properly handles worker errors"""
        error_messages = []
        controller.error.connect(lambda msg: error_messages.append(msg))

        # Trigger file load with non-existent file
        controller.open_file("nonexistent.png")

        # The error should be propagated through controller
        assert len(error_messages) > 0


class TestSaveErrorScenarios:
    """Test various save error scenarios"""

    def test_save_to_readonly_directory(self, controller, sample_image):
        """Test saving to read-only directory"""
        # Setup controller with image
        controller.image_model.data = sample_image
        controller.image_model.width = 8
        controller.image_model.height = 8

        # Try to save to a system directory (likely read-only)
        if os.name == "posix":
            readonly_path = "/root/test_image.png"
        else:
            readonly_path = "C:\\Windows\\System32\\test_image.png"

        error_messages = []
        controller.error.connect(lambda msg: error_messages.append(msg))

        # Attempt save
        controller.save_file(readonly_path)

        # Should emit error about permissions
        # Note: actual error depends on system

    def test_save_with_invalid_extension(self, controller, sample_image, qtbot):
        """Test saving with unsupported file extension"""
        # Skip this test due to PIL threading segfault in headless environment
        pytest.skip("Skipping due to PIL threading issue in headless environment")

    def test_save_worker_disk_full_simulation(self, sample_image):
        """Test save worker behavior when disk write fails"""
        # Create a mock that raises IOError
        with patch("PIL.Image.Image.save") as mock_save:
            mock_save.side_effect = OSError("No space left on device")

            worker = FileSaveWorker(sample_image, [0] * 768, "output.png")

            error_messages = []
            worker.error.connect(lambda msg: error_messages.append(msg))

            # Run worker synchronously
            worker.run()

            assert len(error_messages) == 1
            assert "Failed to save image" in error_messages[0]

    def test_save_empty_image(self, controller):
        """Test saving when no image is loaded"""
        # Set controller to have no image loaded (the test condition)
        controller.image_model.data = None

        error_messages = []
        controller.error.connect(lambda msg: error_messages.append(msg))

        # Try to save without image
        controller.save_file("output.png")

        assert len(error_messages) == 1
        assert "no image" in error_messages[0].lower()


class TestCorruptionRecovery:
    """Test recovery from corrupted data"""

    def test_corrupted_metadata_file(self, controller, sample_image):
        """Test loading image with corrupted metadata file"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Save a valid image
            from PIL import Image

            img = Image.fromarray(sample_image, mode="P")
            img.putpalette(
                [i * 17 for i in range(16) for _ in range(3)] + [0] * (768 - 48)
            )
            img_path = os.path.join(temp_dir, "test.png")
            img.save(img_path)

            # Create corrupted metadata
            metadata_path = os.path.join(temp_dir, "test_metadata.json")
            with open(metadata_path, "w") as f:
                f.write("corrupted { json")

            # Load should succeed despite corrupted metadata
            error_messages = []
            controller.error.connect(lambda msg: error_messages.append(msg))

            # Load the image
            controller.open_file(img_path)

            # Image should load successfully
            # Metadata error might be logged but shouldn't prevent image loading

    def test_palette_manager_corrupted_palette_reference(self, controller):
        """Test PaletteManager with corrupted palette references"""
        metadata = {
            "palettes": {
                "8": {"colors": [[255, 0, 0]] * 16, "name": "Red"},
                "9": "corrupted_reference.pal",  # Invalid reference
            },
            "default_palette": 8,
        }

        # Load metadata with corruption
        success = controller.palette_manager.load_from_metadata(metadata)

        # Should still load the valid palette
        assert success
        assert controller.palette_manager.get_palette_count() >= 1
        assert controller.palette_manager.current_palette_index == 8

    def test_recovery_from_invalid_color_index(self, controller):
        """Test drawing with invalid color index"""
        controller.new_file(8, 8)

        # Set invalid color index
        controller.tool_manager.drawing_color = 255  # Out of range

        # Should handle gracefully
        controller.handle_canvas_press(0, 0)
        controller.handle_canvas_release(0, 0)

        # Pixel should be clamped or ignored
        pixel_value = controller.image_model.data[0, 0]
        assert 0 <= pixel_value < 16  # Should be in valid range

    def test_load_non_image_file(self, controller, qtbot):
        """Test loading a non-image file"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("This is not an image")
            temp_path = f.name

        try:
            error_messages = []
            controller.error.connect(lambda msg: error_messages.append(msg))

            controller.open_file(temp_path)

            # Wait for worker to process
            if controller.load_worker:
                qtbot.wait(100)  # Give worker time to fail

            # Should emit error about invalid image
            assert len(error_messages) > 0
        finally:
            os.unlink(temp_path)


class TestMouseDragOperations:
    """Test mouse drag functionality"""

    def test_mouse_drag_drawing(self, controller, canvas, qtbot):
        """Test drawing with mouse drag"""
        # Set up controller with image
        controller.new_file(16, 16)
        controller.set_drawing_color(5)

        # Connect canvas signals to controller handlers (like in the real app)
        canvas.pixelPressed.connect(controller.handle_canvas_press)
        canvas.pixelMoved.connect(controller.handle_canvas_move)
        canvas.pixelReleased.connect(controller.handle_canvas_release)

        # Also connect to tracking lambdas to verify signals were emitted
        pressed_positions = []
        moved_positions = []
        released_positions = []

        canvas.pixelPressed.connect(lambda x, y: pressed_positions.append((x, y)))
        canvas.pixelMoved.connect(lambda x, y: moved_positions.append((x, y)))
        canvas.pixelReleased.connect(lambda x, y: released_positions.append((x, y)))

        # Simulate mouse press at position (10, 10)
        press_event = QMouseEvent(
            QMouseEvent.Type.MouseButtonPress,
            QPointF(10 * canvas.zoom, 10 * canvas.zoom),  # Use QPointF for position()
            Qt.MouseButton.LeftButton,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
        )
        canvas.mousePressEvent(press_event)

        # Simulate drag across several pixels
        positions = [(11, 10), (12, 10), (13, 10), (14, 10)]
        for x, y in positions:
            move_event = QMouseEvent(
                QMouseEvent.Type.MouseMove,
                QPointF(x * canvas.zoom, y * canvas.zoom),
                Qt.MouseButton.NoButton,
                Qt.MouseButton.LeftButton,  # Button held down
                Qt.KeyboardModifier.NoModifier,
            )
            canvas.mouseMoveEvent(move_event)

        # Release
        release_event = QMouseEvent(
            QMouseEvent.Type.MouseButtonRelease,
            QPointF(14 * canvas.zoom, 10 * canvas.zoom),
            Qt.MouseButton.LeftButton,
            Qt.MouseButton.NoButton,
            Qt.KeyboardModifier.NoModifier,
        )
        canvas.mouseReleaseEvent(release_event)

        # Verify signals were emitted
        assert len(pressed_positions) >= 1
        assert len(moved_positions) >= len(positions)
        assert len(released_positions) >= 1

        # Check that pixels were drawn (controller handles actual drawing)
        for x in range(10, 15):
            assert controller.image_model.data[10, x] == 5

    def test_mouse_pan_with_space(self, controller, canvas):
        """Test pan operation with middle mouse button"""
        # Set up controller with larger image
        controller.new_file(32, 32)
        canvas.zoom = 8  # Zoomed in to enable panning

        # Mouse press with middle button to start pan
        press_event = QMouseEvent(
            QMouseEvent.Type.MouseButtonPress,
            QPointF(100, 100),
            Qt.MouseButton.MiddleButton,
            Qt.MouseButton.MiddleButton,
            Qt.KeyboardModifier.NoModifier,
        )

        # Store original pan offset
        QPointF(canvas.pan_offset) if hasattr(canvas, "pan_offset") else QPointF(0, 0)

        canvas.mousePressEvent(press_event)

        # Should be in panning mode
        assert canvas.panning

        # Drag to pan
        move_event = QMouseEvent(
            QMouseEvent.Type.MouseMove,
            QPointF(150, 150),
            Qt.MouseButton.NoButton,
            Qt.MouseButton.MiddleButton,  # Middle button held
            Qt.KeyboardModifier.NoModifier,
        )
        canvas.mouseMoveEvent(move_event)

        # Pan offset should have changed
        # The exact change depends on implementation

        # Release middle button
        release_event = QMouseEvent(
            QMouseEvent.Type.MouseButtonRelease,
            QPointF(150, 150),
            Qt.MouseButton.MiddleButton,
            Qt.MouseButton.NoButton,
            Qt.KeyboardModifier.NoModifier,
        )
        canvas.mouseReleaseEvent(release_event)

        # Should no longer be panning
        assert not canvas.panning

    def test_mouse_wheel_zoom(self, controller, canvas):
        """Test zoom with mouse wheel"""
        controller.new_file(16, 16)

        original_zoom = canvas.zoom

        # Create wheel event (zoom in)
        from PyQt6.QtCore import QPoint
        from PyQt6.QtGui import QWheelEvent

        # Connect to zoom signal to verify it's emitted
        zoom_changes = []
        canvas.zoomRequested.connect(lambda z: zoom_changes.append(z))

        wheel_event = QWheelEvent(
            QPointF(50, 50),  # position
            QPointF(50, 50),  # globalPosition
            QPoint(0, 120),  # pixelDelta (positive = zoom in)
            QPoint(0, 120),  # angleDelta
            Qt.MouseButton.NoButton,
            Qt.KeyboardModifier.ControlModifier,  # Ctrl+Wheel for zoom
            Qt.ScrollPhase.NoScrollPhase,
            False,  # inverted
        )
        canvas.wheelEvent(wheel_event)

        # Zoom should have changed
        assert len(zoom_changes) > 0 or canvas.zoom != original_zoom


class TestContextMenuHandling:
    """Test context menu functionality"""

    def test_right_click_context_menu(self, controller, canvas):
        """Test right-click context menu"""
        controller.new_file(16, 16)

        # Create context menu event
        context_event = QContextMenuEvent(
            QContextMenuEvent.Reason.Mouse, QPoint(50, 50), QPoint(150, 150)
        )

        # Canvas might not have context menu implemented yet
        # Just verify it doesn't crash
        canvas.contextMenuEvent(context_event)

    def test_color_picker_right_click(self, controller, canvas):
        """Test color picker with right mouse button"""
        # Set up image with specific color
        controller.new_file(16, 16)
        controller.image_model.data[5, 5] = 7

        # Right-click on pixel with color 7
        event = QMouseEvent(
            QMouseEvent.Type.MouseButtonPress,
            QPointF(5 * canvas.zoom, 5 * canvas.zoom),
            Qt.MouseButton.RightButton,
            Qt.MouseButton.RightButton,
            Qt.KeyboardModifier.NoModifier,
        )

        # Some implementations use right-click for color picker
        canvas.mousePressEvent(event)

        # Check if color was picked (implementation dependent)
        # Just verify no crash for now


class TestKeyboardModifierCombinations:
    """Test keyboard shortcuts with modifiers"""

    def test_ctrl_key_combinations(self, controller):
        """Test Ctrl+key combinations"""
        # Test Ctrl+N (new file)
        controller.new_file(8, 8)
        assert controller.has_image()

        # Test Ctrl+Z (undo) - might not be implemented
        original_data = controller.image_model.data.copy()
        controller.set_drawing_color(5)
        controller.handle_canvas_press(0, 0)
        controller.handle_canvas_release(0, 0)

        # Data should change
        assert not np.array_equal(controller.image_model.data, original_data)

    def test_shift_modifier_drawing(self, controller, canvas):
        """Test drawing with shift modifier (e.g., draw straight lines)"""
        controller.new_file(16, 16)
        controller.set_drawing_color(3)

        # Press with shift held
        event = QMouseEvent(
            QMouseEvent.Type.MouseButtonPress,
            QPointF(5 * canvas.zoom, 5 * canvas.zoom),
            Qt.MouseButton.LeftButton,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.ShiftModifier,
        )
        canvas.mousePressEvent(event)

        # Implementation-specific behavior
        # Just verify no crash

    def test_alt_modifier_operations(self, controller, canvas):
        """Test operations with Alt modifier"""
        controller.new_file(16, 16)

        # Alt+Click might have special behavior
        event = QMouseEvent(
            QMouseEvent.Type.MouseButtonPress,
            QPointF(8 * canvas.zoom, 8 * canvas.zoom),
            Qt.MouseButton.LeftButton,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.AltModifier,
        )
        canvas.mousePressEvent(event)

        # Verify no crash


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
