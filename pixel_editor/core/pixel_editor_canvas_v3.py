#!/usr/bin/env python3
"""
Refactored Canvas widget for the pixel editor - Phase 3.3
Uses controller's models and managers instead of maintaining its own state
"""

# Standard library imports
from typing import Optional

# Third-party imports
from PyQt6.QtCore import QPoint, QPointF, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QMouseEvent, QPainter, QPen, QWheelEvent
from PyQt6.QtWidgets import QWidget


class PixelCanvasV3(QWidget):
    """Refactored canvas that delegates to controller"""

    # Signals
    pixelPressed = pyqtSignal(int, int)  # x, y in image space
    pixelMoved = pyqtSignal(int, int)  # x, y in image space
    pixelReleased = pyqtSignal(int, int)  # x, y in image space
    zoomRequested = pyqtSignal(int)  # new zoom level

    def __init__(self, controller, parent=None):
        super().__init__(parent)

        # Store controller reference
        self.controller = controller

        # View state (not business logic)
        self.zoom = 4
        self.grid_visible = False
        self.greyscale_mode = False

        # Interaction state
        self.drawing = False
        self.panning = False
        self.pan_offset = QPointF(0.0, 0.0)
        self.pan_last_point = None
        self.hover_pos = None

        # Performance caches
        self._qcolor_cache = {}
        self._palette_version = 0
        self._cached_palette_version = -1

        # Setup
        self.setMouseTracking(True)
        self.setMinimumSize(200, 200)

        # Connect to controller signals
        self.controller.imageChanged.connect(self._on_image_changed)
        self.controller.paletteChanged.connect(self._on_palette_changed)

    def _on_image_changed(self):
        """Handle image change from controller"""
        self._update_size()
        self._palette_version += 1  # Force color cache update
        self.update()

    def _on_palette_changed(self):
        """Handle palette change from controller"""
        self._palette_version += 1  # Force color cache update
        self.update()

    def _update_size(self):
        """Update widget size based on image and zoom"""
        size = self.controller.get_image_size()
        if size:
            width, height = size
            self.setFixedSize(width * self.zoom, height * self.zoom)

    def set_zoom(self, zoom: int):
        """Set zoom level"""
        self.zoom = max(1, min(64, zoom))
        self._update_size()
        self.update()

    def set_grid_visible(self, visible: bool):
        """Toggle grid visibility"""
        self.grid_visible = visible
        self.update()

    def set_greyscale_mode(self, greyscale: bool):
        """Toggle greyscale display mode"""
        self.greyscale_mode = greyscale
        self._palette_version += 1  # Force color cache update
        self.update()

    def _update_qcolor_cache(self):
        """Update cached QColor objects when palette changes"""
        self._qcolor_cache.clear()

        # Get colors from controller
        colors = self.controller.get_current_colors()

        if self.greyscale_mode:
            # Override with grayscale
            for i in range(16):
                gray = (i * 255) // 15
                self._qcolor_cache[i] = QColor(gray, gray, gray)
        else:
            # Use actual colors
            for i, rgb in enumerate(colors[:16]):
                self._qcolor_cache[i] = QColor(*rgb)

        # Add magenta for invalid indices
        self._qcolor_cache[-1] = QColor(255, 0, 255)

        self._cached_palette_version = self._palette_version

    def paintEvent(self, event):
        """Paint the canvas"""
        if not self.controller.has_image():
            return

        painter = QPainter(self)

        # Apply pan offset
        painter.translate(self.pan_offset)

        # Get image data from controller
        image_model = self.controller.image_model
        if image_model.data is None:
            return

        height, width = image_model.data.shape

        # Update color cache if needed
        if self._cached_palette_version != self._palette_version:
            self._update_qcolor_cache()

        # Draw pixels
        for y in range(height):
            for x in range(width):
                color_index = image_model.data[y, x]

                # Get QColor (with fallback for invalid indices)
                qcolor = self._qcolor_cache.get(color_index, self._qcolor_cache.get(-1))

                # Draw pixel
                painter.fillRect(
                    x * self.zoom, y * self.zoom, self.zoom, self.zoom, qcolor
                )

        # Draw grid if visible and zoomed in enough
        if self.grid_visible and self.zoom >= 4:
            painter.setPen(QPen(QColor(64, 64, 64), 1))

            # Vertical lines
            for x in range(width + 1):
                painter.drawLine(x * self.zoom, 0, x * self.zoom, height * self.zoom)

            # Horizontal lines
            for y in range(height + 1):
                painter.drawLine(0, y * self.zoom, width * self.zoom, y * self.zoom)

        # Draw hover highlight
        if self.hover_pos and not self.drawing:
            x, y = self.hover_pos.x(), self.hover_pos.y()
            if 0 <= x < width and 0 <= y < height:
                painter.setPen(QPen(QColor(255, 255, 0), 2))
                painter.drawRect(
                    x * self.zoom, y * self.zoom, self.zoom - 1, self.zoom - 1
                )

    def mousePressEvent(self, event: QMouseEvent):
        """Handle mouse press"""
        if event.button() == Qt.MouseButton.LeftButton:
            pos = self._get_pixel_pos(event.position())
            if pos:
                self.drawing = True
                self.pixelPressed.emit(pos.x(), pos.y())

        elif event.button() == Qt.MouseButton.MiddleButton:
            # Start panning
            self.panning = True
            self.pan_last_point = event.position()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)

        elif event.button() == Qt.MouseButton.RightButton:
            # Color picker
            pos = self._get_pixel_pos(event.position())
            if pos and self.controller.has_image():
                # Set tool to picker and trigger pick
                self.controller.set_tool("picker")
                self.pixelPressed.emit(pos.x(), pos.y())

    def mouseMoveEvent(self, event: QMouseEvent):
        """Handle mouse move"""
        # Handle panning
        if self.panning and self.pan_last_point:
            delta = event.position() - self.pan_last_point
            self.pan_last_point = event.position()
            self.pan_offset += delta
            self.update()
            return

        # Update hover position
        pos = self._get_pixel_pos(event.position())
        if pos != self.hover_pos:
            self.hover_pos = pos
            self.update()

        # Handle drawing
        if self.drawing and pos:
            self.pixelMoved.emit(pos.x(), pos.y())

    def mouseReleaseEvent(self, event: QMouseEvent):
        """Handle mouse release"""
        if event.button() == Qt.MouseButton.LeftButton:
            if self.drawing:
                self.drawing = False
                pos = self._get_pixel_pos(event.position())
                if pos:
                    self.pixelReleased.emit(pos.x(), pos.y())

        elif event.button() == Qt.MouseButton.MiddleButton:
            self.panning = False
            self.pan_last_point = None
            self.setCursor(Qt.CursorShape.ArrowCursor)

    def wheelEvent(self, event: QWheelEvent):
        """Handle mouse wheel for zooming"""
        delta = event.angleDelta().y()

        # Zoom levels
        zoom_levels = [1, 2, 4, 8, 16, 32, 64]

        # Find current index
        current_index = 0
        for i, level in enumerate(zoom_levels):
            if level <= self.zoom:
                current_index = i
            else:
                break

        # Calculate new zoom
        if delta > 0:
            new_index = min(current_index + 1, len(zoom_levels) - 1)
        else:
            new_index = max(current_index - 1, 0)

        new_zoom = zoom_levels[new_index]

        if new_zoom != self.zoom:
            self.zoomRequested.emit(new_zoom)

        event.accept()

    def leaveEvent(self, event):
        """Handle mouse leave event"""
        self.hover_pos = None
        self.update()

    def _get_pixel_pos(self, pos) -> Optional[QPoint]:
        """Convert mouse position to pixel coordinates"""
        if not self.controller.has_image():
            return None

        # Adjust for pan offset
        adjusted_pos = pos - self.pan_offset

        x = int(adjusted_pos.x() // self.zoom)
        y = int(adjusted_pos.y() // self.zoom)

        width, height = self.controller.get_image_size()
        if 0 <= x < width and 0 <= y < height:
            return QPoint(x, y)
        return None

    def enterEvent(self, event):
        """Show tooltip on enter"""
        self.setToolTip(
            "Left click: Draw • Right click: Pick color • "
            "Middle click + drag: Pan • Wheel: Zoom"
        )
        super().enterEvent(event)
