#!/usr/bin/env python3
"""
Unit tests for PixelCanvasV3
Tests the canvas view behavior and interaction with controller
"""

from unittest.mock import MagicMock, patch

import numpy as np
import pytest
from PyQt6.QtCore import QPoint, QPointF, Qt
from PyQt6.QtGui import QColor, QMouseEvent, QWheelEvent
from PyQt6.QtWidgets import QApplication

from pixel_editor.core.pixel_editor_canvas_v3 import PixelCanvasV3
from pixel_editor.core.pixel_editor_controller_v3 import PixelEditorController


@pytest.fixture(scope="module")
def qapp():
    """Create QApplication for testing"""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


class TestPixelCanvasV3:
    """Test the refactored canvas widget"""

    @pytest.fixture
    def controller(self):
        """Create a mock controller"""
        controller = MagicMock(spec=PixelEditorController)

        # Setup default return values
        controller.get_image_size.return_value = (8, 8)
        controller.get_current_colors.return_value = [
            (i * 16, i * 16, i * 16) for i in range(16)
        ]
        controller.has_image.return_value = True

        # Setup image model mock
        controller.image_model = MagicMock()
        controller.image_model.data = np.zeros((8, 8), dtype=np.uint8)
        controller.image_model.width = 8
        controller.image_model.height = 8

        return controller

    @pytest.fixture
    def canvas(self, controller, qapp):
        """Create a canvas instance"""
        return PixelCanvasV3(controller)

    # Initialization tests
    def test_canvas_initialization(self, canvas, controller):
        """Test canvas is properly initialized"""
        assert canvas.controller == controller
        assert canvas.zoom == 4
        assert canvas.grid_visible is False
        assert canvas.greyscale_mode is False
        assert canvas.drawing is False
        assert canvas.panning is False

        # Check signal connections
        controller.imageChanged.connect.assert_called()
        controller.paletteChanged.connect.assert_called()

    def test_initial_size(self, canvas, controller):
        """Test initial widget size based on image"""
        # Trigger size update
        canvas._update_size()

        # Should be image size * zoom
        assert canvas.width() == 8 * 4
        assert canvas.height() == 8 * 4

    # View state tests
    def test_set_zoom(self, canvas):
        """Test setting zoom level"""
        canvas.set_zoom(8)
        assert canvas.zoom == 8
        assert canvas.width() == 8 * 8

        # Test clamping
        canvas.set_zoom(100)
        assert canvas.zoom == 64

        canvas.set_zoom(0)
        assert canvas.zoom == 1

    def test_set_grid_visible(self, canvas):
        """Test toggling grid visibility"""
        update_spy = MagicMock()
        canvas.update = update_spy

        canvas.set_grid_visible(False)
        assert canvas.grid_visible is False
        update_spy.assert_called()

        canvas.set_grid_visible(True)
        assert canvas.grid_visible is True

    def test_set_greyscale_mode(self, canvas):
        """Test toggling greyscale mode"""
        update_spy = MagicMock()
        canvas.update = update_spy

        canvas.set_greyscale_mode(True)
        assert canvas.greyscale_mode is True
        assert canvas._palette_version > canvas._cached_palette_version
        update_spy.assert_called()

    # Signal handling tests
    def test_on_image_changed(self, canvas):
        """Test handling image change signal"""
        update_spy = MagicMock()
        canvas.update = update_spy
        canvas._update_size = MagicMock()

        old_version = canvas._palette_version
        canvas._on_image_changed()

        canvas._update_size.assert_called_once()
        assert canvas._palette_version > old_version
        update_spy.assert_called()

    def test_on_palette_changed(self, canvas):
        """Test handling palette change signal"""
        update_spy = MagicMock()
        canvas.update = update_spy

        old_version = canvas._palette_version
        canvas._on_palette_changed()

        assert canvas._palette_version > old_version
        update_spy.assert_called()

    # Mouse interaction tests
    def test_mouse_press_drawing(self, canvas):
        """Test mouse press starts drawing"""
        pixel_pressed_spy = MagicMock()
        canvas.pixelPressed.connect(pixel_pressed_spy)

        # Create mouse event at canvas position (10, 10)
        event = MagicMock(spec=QMouseEvent)
        event.button.return_value = Qt.MouseButton.LeftButton
        event.position.return_value = QPointF(10, 10)

        canvas.mousePressEvent(event)

        assert canvas.drawing is True
        # Should convert to image coordinates (10/4, 10/4) = (2, 2)
        pixel_pressed_spy.assert_called_once_with(2, 2)

    def test_mouse_press_panning(self, canvas):
        """Test middle mouse starts panning"""
        event = MagicMock(spec=QMouseEvent)
        event.button.return_value = Qt.MouseButton.MiddleButton
        event.position.return_value = QPointF(20, 20)

        canvas.mousePressEvent(event)

        assert canvas.panning is True
        assert canvas.pan_last_point == QPointF(20, 20)
        assert canvas.drawing is False

    def test_mouse_move_drawing(self, canvas):
        """Test mouse move while drawing"""
        pixel_moved_spy = MagicMock()
        canvas.pixelMoved.connect(pixel_moved_spy)

        # Start drawing
        canvas.drawing = True

        # Move mouse
        event = MagicMock(spec=QMouseEvent)
        event.position.return_value = QPointF(12, 16)

        canvas.mouseMoveEvent(event)

        # Should emit pixel moved signal
        pixel_moved_spy.assert_called_once_with(3, 4)  # 12/4, 16/4

    def test_mouse_move_panning(self, canvas):
        """Test mouse move while panning"""
        # Setup panning state
        canvas.panning = True
        canvas.pan_last_point = QPointF(10, 10)
        canvas.pan_offset = QPointF(0, 0)

        update_spy = MagicMock()
        canvas.update = update_spy

        # Move mouse
        event = MagicMock(spec=QMouseEvent)
        event.position.return_value = QPointF(20, 15)

        canvas.mouseMoveEvent(event)

        # Check pan offset updated
        assert canvas.pan_offset == QPointF(10, 5)  # Delta from last point
        assert canvas.pan_last_point == QPointF(20, 15)
        update_spy.assert_called()

    def test_mouse_move_hover(self, canvas):
        """Test mouse move updates hover position"""
        update_spy = MagicMock()
        canvas.update = update_spy

        # Move mouse (not drawing or panning)
        event = MagicMock(spec=QMouseEvent)
        event.position.return_value = QPointF(8, 12)

        canvas.mouseMoveEvent(event)

        assert canvas.hover_pos == QPoint(2, 3)  # 8/4, 12/4
        update_spy.assert_called()

    def test_mouse_release(self, canvas):
        """Test mouse release ends drawing/panning"""
        pixel_released_spy = MagicMock()
        canvas.pixelReleased.connect(pixel_released_spy)

        # Setup drawing state
        canvas.drawing = True
        canvas.panning = True

        # Release left button (drawing)
        event = MagicMock(spec=QMouseEvent)
        event.button.return_value = Qt.MouseButton.LeftButton
        event.position.return_value = QPointF(16, 20)

        canvas.mouseReleaseEvent(event)

        assert canvas.drawing is False
        pixel_released_spy.assert_called_once_with(4, 5)  # 16/4, 20/4

        # Release middle button (panning)
        event2 = MagicMock(spec=QMouseEvent)
        event2.button.return_value = Qt.MouseButton.MiddleButton

        canvas.mouseReleaseEvent(event2)

        assert canvas.panning is False

    def test_mouse_leave(self, canvas):
        """Test mouse leave clears hover"""
        canvas.hover_pos = QPoint(2, 2)
        update_spy = MagicMock()
        canvas.update = update_spy

        canvas.leaveEvent(None)

        assert canvas.hover_pos is None
        update_spy.assert_called()

    # Wheel event tests
    def test_wheel_zoom_in(self, canvas):
        """Test zooming in with mouse wheel"""
        zoom_requested_spy = MagicMock()
        canvas.zoomRequested.connect(zoom_requested_spy)

        # Create wheel event with positive delta
        event = MagicMock(spec=QWheelEvent)
        event.angleDelta.return_value.y.return_value = 120
        event.modifiers.return_value = Qt.KeyboardModifier.ControlModifier

        canvas.wheelEvent(event)
        event.accept.assert_called()

        # Should request zoom in
        zoom_requested_spy.assert_called_once()
        requested_zoom = zoom_requested_spy.call_args[0][0]
        assert requested_zoom > canvas.zoom

    def test_wheel_zoom_out(self, canvas):
        """Test zooming out with mouse wheel"""
        zoom_requested_spy = MagicMock()
        canvas.zoomRequested.connect(zoom_requested_spy)

        canvas.zoom = 8  # Start zoomed in

        # Create wheel event with negative delta
        event = MagicMock(spec=QWheelEvent)
        event.angleDelta.return_value.y.return_value = -120
        event.modifiers.return_value = Qt.KeyboardModifier.ControlModifier

        canvas.wheelEvent(event)

        # Should request zoom out
        zoom_requested_spy.assert_called_once()
        requested_zoom = zoom_requested_spy.call_args[0][0]
        assert requested_zoom < 8

    def test_wheel_without_ctrl(self, canvas):
        """Test wheel without Ctrl still allows zooming"""
        zoom_requested_spy = MagicMock()
        canvas.zoomRequested.connect(zoom_requested_spy)

        # Reset zoom to known state
        canvas.zoom = 4

        event = MagicMock(spec=QWheelEvent)
        event.angleDelta.return_value.y.return_value = 120
        event.modifiers.return_value = Qt.KeyboardModifier.NoModifier

        canvas.wheelEvent(event)
        event.accept.assert_called()
        zoom_requested_spy.assert_called_once_with(8)  # Zoom in from 4 to 8

    # Color cache tests
    def test_update_qcolor_cache(self, canvas):
        """Test QColor cache updates correctly"""
        # Clear cache
        canvas._qcolor_cache.clear()
        canvas._cached_palette_version = -1

        # Update cache
        canvas._update_qcolor_cache()

        # Check colors cached (includes -1 for transparent)
        assert len(canvas._qcolor_cache) == 17
        assert isinstance(canvas._qcolor_cache[0], QColor)
        assert canvas._cached_palette_version == canvas._palette_version

    def test_update_qcolor_cache_greyscale(self, canvas):
        """Test QColor cache in greyscale mode"""
        canvas.greyscale_mode = True
        canvas._qcolor_cache.clear()

        canvas._update_qcolor_cache()

        # Check greyscale colors
        assert canvas._qcolor_cache[0] == QColor(0, 0, 0)
        assert canvas._qcolor_cache[15] == QColor(255, 255, 255)
        assert canvas._qcolor_cache[8] == QColor(136, 136, 136)  # (8 * 255) // 15

    # Coordinate conversion tests
    def test_get_pixel_pos(self, canvas):
        """Test converting canvas position to pixel coordinates"""
        # Test basic conversion
        pos = canvas._get_pixel_pos(QPointF(8, 12))
        assert pos == QPoint(2, 3)

        pos = canvas._get_pixel_pos(QPointF(0, 0))
        assert pos == QPoint(0, 0)

        pos = canvas._get_pixel_pos(QPointF(31, 31))
        assert pos == QPoint(7, 7)

        # Test with pan offset
        canvas.pan_offset = QPointF(4, -8)
        pos = canvas._get_pixel_pos(QPointF(8, 12))
        assert pos == QPoint(1, 5)

        # Test out of bounds
        pos = canvas._get_pixel_pos(QPointF(-4, -4))
        assert pos is None

        pos = canvas._get_pixel_pos(QPointF(100, 100))
        assert pos is None

    # Edge case tests
    def test_draw_outside_bounds(self, canvas):
        """Test drawing outside image bounds"""
        pixel_pressed_spy = MagicMock()
        canvas.pixelPressed.connect(pixel_pressed_spy)

        # Click outside image bounds
        event = MagicMock(spec=QMouseEvent)
        event.button.return_value = Qt.MouseButton.LeftButton
        event.position.return_value = QPointF(100, 100)  # Way outside 32x32 canvas

        canvas.mousePressEvent(event)

        # Should NOT emit signal for out-of-bounds clicks
        pixel_pressed_spy.assert_not_called()

    def test_no_image_loaded(self, canvas, controller):
        """Test behavior when no image is loaded"""
        controller.has_image.return_value = False
        controller.image_model.data = None
        controller.get_image_size.return_value = None

        # Should handle gracefully
        canvas._update_size()  # Should not crash

        # Try to draw
        event = MagicMock(spec=QMouseEvent)
        event.button.return_value = Qt.MouseButton.LeftButton
        event.position.return_value = QPointF(10, 10)

        # Should not crash
        canvas.mousePressEvent(event)


class TestCanvasRendering:
    """Tests for canvas rendering - focusing on public behavior not internals"""

    """Test the canvas rendering logic"""

    @pytest.fixture
    def canvas(self, qapp):
        """Create canvas with real controller for rendering tests"""
        controller = PixelEditorController()
        controller.new_file(4, 4)
        canvas = PixelCanvasV3(controller)
        canvas.zoom = 10  # Larger zoom for testing
        canvas._update_size()
        return canvas

    def test_paint_event_with_no_image(self, canvas):
        """Test paint event handles no image gracefully"""
        # Clear the image data
        canvas.controller.image_model.data = None

        # Should not crash
        event = MagicMock()
        canvas.paintEvent(event)

    def test_paint_event_with_image(self, canvas):
        """Test paint event renders when image exists"""
        # Mock QPainter to avoid actual painting
        with patch(
            "pixel_editor.core.pixel_editor_canvas_v3.QPainter"
        ) as mock_painter_class:
            mock_painter = MagicMock()
            mock_painter_class.return_value = mock_painter

            event = MagicMock()
            canvas.paintEvent(event)

            # Should create painter and do some operations
            mock_painter_class.assert_called_once_with(canvas)
            mock_painter.translate.assert_called_once()

    def test_grid_visibility_affects_rendering(self, canvas):
        """Test that grid visibility triggers update"""
        with patch.object(canvas, "update") as mock_update:
            canvas.set_grid_visible(True)
            mock_update.assert_called_once()

            mock_update.reset_mock()
            canvas.set_grid_visible(False)
            mock_update.assert_called_once()

    def test_hover_updates_canvas(self, canvas):
        """Test hover position changes trigger update"""
        with patch.object(canvas, "update") as mock_update:
            # Simulate mouse move with hover
            event = MagicMock(spec=QMouseEvent)
            event.position.return_value = QPointF(8, 8)
            event.buttons.return_value = Qt.MouseButton.NoButton

            canvas.mouseMoveEvent(event)

            # Should have set hover_pos and called update
            assert canvas.hover_pos is not None
            mock_update.assert_called()


class TestCanvasPerformance:
    """Test performance-related features"""

    @pytest.fixture
    def large_canvas(self, qapp):
        """Create canvas with larger image for performance testing"""
        controller = PixelEditorController()
        controller.new_file(64, 64)
        return PixelCanvasV3(controller)

    def test_color_cache_reuse(self, large_canvas):
        """Test color cache is reused when palette unchanged"""
        # Force cache update
        large_canvas._update_qcolor_cache()
        initial_version = large_canvas._cached_palette_version
        initial_cache_keys = set(large_canvas._qcolor_cache.keys())

        # Paint without palette change - cache should not be rebuilt
        with patch.object(large_canvas, "_update_qcolor_cache") as mock_update:
            with patch("pixel_editor.core.pixel_editor_canvas_v3.QPainter"):
                large_canvas.paintEvent(None)

        # Cache update should not have been called since palette didn't change
        mock_update.assert_not_called()
        assert large_canvas._cached_palette_version == initial_version
        assert set(large_canvas._qcolor_cache.keys()) == initial_cache_keys

    def test_color_cache_invalidation(self, large_canvas):
        """Test color cache invalidates on palette change"""
        # Force cache update
        large_canvas._update_qcolor_cache()
        old_version = large_canvas._cached_palette_version

        # Change palette
        large_canvas._on_palette_changed()

        # Cache should be invalidated
        assert large_canvas._palette_version != old_version
        assert large_canvas._cached_palette_version != large_canvas._palette_version

    def test_flood_fill_large_area(self, large_canvas):
        """Test flood fill performance on large area"""
        # This is more of an integration test
        controller = large_canvas.controller
        controller.set_tool("fill")
        controller.set_drawing_color(7)

        # Fill large area
        import time

        start = time.time()
        controller.handle_canvas_press(32, 32)
        elapsed = time.time() - start

        # Should complete quickly even for 64x64 image
        assert elapsed < 0.1  # 100ms max

        # Verify fill worked
        assert np.all(controller.image_model.data == 7)
