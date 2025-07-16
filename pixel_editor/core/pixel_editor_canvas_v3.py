#!/usr/bin/env python3
"""
Refactored Canvas widget for the pixel editor - Phase 3.3
Uses controller's models and managers instead of maintaining its own state
"""

# Standard library imports
from typing import Optional

# Third-party imports
from PyQt6.QtCore import QPoint, QPointF, QRect, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QImage, QMouseEvent, QPainter, QPen, QWheelEvent
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
        self.temporary_picker = (
            False  # Track if we're temporarily using picker with right-click
        )
        self.previous_tool = None  # Store previous tool when using temporary picker

        # Performance caches
        self._qcolor_cache = {}
        self._palette_version = 0
        self._cached_palette_version = -1

        # QImage-based rendering optimization
        self._qimage_buffer = None  # QImage buffer for efficient rendering
        self._qimage_scaled = None  # Cached scaled version of the image
        self._cached_zoom = 0  # Last zoom level used for scaled image
        self._dirty_rect = QRect()  # Rectangle that needs repainting
        self._image_version = 0  # Track image data changes
        self._cached_image_version = -1

        # Setup
        self.setMouseTracking(True)
        self.setMinimumSize(200, 200)

        # Connect to controller signals
        self.controller.imageChanged.connect(self._on_image_changed)
        self.controller.paletteChanged.connect(self._on_palette_changed)
        self.controller.toolChanged.connect(self._on_tool_changed)

        # Set initial cursor for current tool
        current_tool = self.controller.get_current_tool_name()
        self._update_cursor_for_tool(current_tool)

    def _on_image_changed(self):
        """Handle image change from controller"""
        self._update_size()
        self._palette_version += 1  # Force color cache update
        self._image_version += 1  # Force image buffer update
        self._invalidate_image_cache()
        self.update()

    def _on_palette_changed(self):
        """Handle palette change from controller"""
        self._palette_version += 1  # Force color cache update
        self._invalidate_image_cache()
        self.update()

    def _on_tool_changed(self, tool_name: str):
        """Handle tool change from controller"""
        self._update_cursor_for_tool(tool_name)

    def _update_cursor_for_tool(self, tool_name: str):
        """Update cursor based on the current tool"""
        if self.panning:
            # Don't change cursor while panning
            return

        if tool_name == "pencil":
            self.setCursor(Qt.CursorShape.CrossCursor)
        elif tool_name == "fill":
            self.setCursor(Qt.CursorShape.PointingHandCursor)
        elif tool_name == "picker":
            # Use WhatsThisCursor as a dropper cursor substitute
            # (Qt doesn't have a built-in eyedropper cursor)
            self.setCursor(Qt.CursorShape.WhatsThisCursor)
        else:
            self.setCursor(Qt.CursorShape.ArrowCursor)

    def _update_size(self):
        """Update widget size based on image and zoom"""
        size = self.controller.get_image_size()
        if size:
            width, height = size
            self.setFixedSize(width * self.zoom, height * self.zoom)

    def set_zoom(self, zoom: int, center_on_canvas: bool = True):
        """Set zoom level

        Args:
            zoom: New zoom level
            center_on_canvas: If True, zoom centered on canvas; if False, preserve pan
        """
        new_zoom = max(1, min(64, zoom))
        if new_zoom != self.zoom:
            if center_on_canvas and self.controller.get_image_size():
                # Get canvas center point
                canvas_center = QPointF(self.width() / 2, self.height() / 2)

                # Calculate the point in image space that's at center
                old_image_point = (canvas_center - self.pan_offset) / self.zoom

                # Update zoom
                self.zoom = new_zoom
                self._update_size()

                # Calculate new position to keep the same image point at center
                new_canvas_point = old_image_point * new_zoom
                self.pan_offset = canvas_center - new_canvas_point
            else:
                # Simple zoom without adjusting pan
                self.zoom = new_zoom
                self._update_size()

            # Invalidate scaled image cache since zoom changed
            self._invalidate_scaled_cache()
            self.update()

    def set_grid_visible(self, visible: bool):
        """Toggle grid visibility"""
        self.grid_visible = visible
        self.update()

    def set_greyscale_mode(self, greyscale: bool):
        """Toggle greyscale display mode"""
        self.greyscale_mode = greyscale
        self._palette_version += 1  # Force color cache update
        self._invalidate_image_cache()
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
                if i == 0:
                    # Index 0 is transparent
                    self._qcolor_cache[i] = QColor(gray, gray, gray, 0)
                else:
                    self._qcolor_cache[i] = QColor(gray, gray, gray)
        else:
            # Use actual colors
            for i, rgb in enumerate(colors[:16]):
                if i == 0:
                    # Index 0 is transparent
                    self._qcolor_cache[i] = QColor(rgb[0], rgb[1], rgb[2], 0)
                else:
                    self._qcolor_cache[i] = QColor(*rgb)

        # Add magenta for invalid indices
        self._qcolor_cache[-1] = QColor(255, 0, 255)

        self._cached_palette_version = self._palette_version

    def _invalidate_image_cache(self):
        """Invalidate QImage buffer cache"""
        self._qimage_buffer = None
        self._qimage_scaled = None
        self._cached_zoom = 0
        self._cached_image_version = -1

    def _invalidate_scaled_cache(self):
        """Invalidate only the scaled image cache"""
        self._qimage_scaled = None
        self._cached_zoom = 0

    def _update_qimage_buffer(self):
        """Update QImage buffer from current image data"""
        if (
            self._qimage_buffer is not None
            and self._cached_image_version == self._image_version
            and self._cached_palette_version == self._palette_version
        ):
            return  # Cache is still valid

        if not self.controller.has_image():
            return

        image_model = self.controller.image_model
        if image_model.data is None:
            return

        height, width = image_model.data.shape

        # Update color cache if needed
        if self._cached_palette_version != self._palette_version:
            self._update_qcolor_cache()

        # Create QImage buffer
        self._qimage_buffer = QImage(width, height, QImage.Format.Format_RGB32)

        # Fill the buffer with pixel data
        for y in range(height):
            for x in range(width):
                color_index = image_model.data[y, x]
                qcolor = self._qcolor_cache.get(color_index, self._qcolor_cache.get(-1))
                if qcolor is not None:
                    self._qimage_buffer.setPixel(x, y, qcolor.rgb())
                else:
                    # Fallback to magenta for invalid colors
                    self._qimage_buffer.setPixel(x, y, QColor(255, 0, 255).rgb())

        self._cached_image_version = self._image_version

    def _get_scaled_qimage(self):
        """Get scaled QImage for current zoom level"""
        if self._qimage_scaled is not None and self._cached_zoom == self.zoom:
            return self._qimage_scaled

        # Update base image buffer first
        self._update_qimage_buffer()

        if self._qimage_buffer is None:
            return None

        # Create scaled version
        scaled_width = self._qimage_buffer.width() * self.zoom
        scaled_height = self._qimage_buffer.height() * self.zoom

        self._qimage_scaled = self._qimage_buffer.scaled(
            scaled_width,
            scaled_height,
            Qt.AspectRatioMode.IgnoreAspectRatio,
            Qt.TransformationMode.FastTransformation,
        )

        self._cached_zoom = self.zoom
        return self._qimage_scaled

    def _update_hover_regions(self, old_pos, new_pos):
        """Update only the regions affected by hover position change"""
        if self.drawing:
            # Skip hover updates during drawing
            return

        # Calculate update regions
        regions_to_update = []

        # Add old hover position to update list
        if old_pos is not None:
            regions_to_update.append(
                QRect(
                    old_pos.x() * self.zoom,
                    old_pos.y() * self.zoom,
                    self.zoom,
                    self.zoom,
                )
            )

        # Add new hover position to update list
        if new_pos is not None:
            regions_to_update.append(
                QRect(
                    new_pos.x() * self.zoom,
                    new_pos.y() * self.zoom,
                    self.zoom,
                    self.zoom,
                )
            )

        # Apply pan offset to regions
        for rect in regions_to_update:
            rect.translate(int(self.pan_offset.x()), int(self.pan_offset.y()))
            self.update(rect)

    def _draw_checkerboard(self, painter, width, height):
        """Draw a checkerboard background for transparency visualization"""
        checker_size = 8  # Size of each checker square
        light_color = QColor(220, 220, 220)
        dark_color = QColor(180, 180, 180)

        for y in range(0, height, checker_size):
            for x in range(0, width, checker_size):
                # Alternate colors in checkerboard pattern
                if (x // checker_size + y // checker_size) % 2 == 0:
                    color = light_color
                else:
                    color = dark_color

                # Draw the checker square
                painter.fillRect(
                    x,
                    y,
                    min(checker_size, width - x),
                    min(checker_size, height - y),
                    color,
                )

    def paintEvent(self, event):
        """Paint the canvas using optimized QImage rendering"""
        if not self.controller.has_image():
            return

        painter = QPainter(self)

        # Apply pan offset
        painter.translate(self.pan_offset)

        # Get scaled QImage
        scaled_qimage = self._get_scaled_qimage()
        if scaled_qimage is None:
            return

        width = scaled_qimage.width()
        height = scaled_qimage.height()

        # Draw checkerboard background for transparency
        self._draw_checkerboard(painter, width, height)

        # Enable composition mode for proper transparency
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)

        # Draw the entire image with a single call - this is the key optimization!
        painter.drawImage(0, 0, scaled_qimage)

        # Draw grid if visible and zoomed in enough
        if self.grid_visible and self.zoom >= 4:
            painter.setPen(QPen(QColor(64, 64, 64), 1))

            # Get original image dimensions
            image_width = width // self.zoom
            image_height = height // self.zoom

            # Vertical lines
            for x in range(image_width + 1):
                painter.drawLine(x * self.zoom, 0, x * self.zoom, height)

            # Horizontal lines
            for y in range(image_height + 1):
                painter.drawLine(0, y * self.zoom, width, y * self.zoom)

        # Draw hover highlight
        if self.hover_pos and not self.drawing:
            x, y = self.hover_pos.x(), self.hover_pos.y()
            image_width = width // self.zoom
            image_height = height // self.zoom

            if 0 <= x < image_width and 0 <= y < image_height:
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
            # Temporary color picker
            pos = self._get_pixel_pos(event.position())
            if pos and self.controller.has_image():
                # Store current tool and temporarily switch to picker
                self.previous_tool = self.controller.get_current_tool_name()
                self.temporary_picker = True
                self.controller.set_tool("picker")
                self.pixelPressed.emit(pos.x(), pos.y())

    def mouseMoveEvent(self, event: QMouseEvent):
        """Handle mouse move with optimized hover updates"""
        # Handle panning
        if self.panning and self.pan_last_point:
            delta = event.position() - self.pan_last_point
            self.pan_last_point = event.position()
            self.pan_offset += delta
            self.update()
            return

        # Update hover position with optimized partial repaints
        pos = self._get_pixel_pos(event.position())
        if pos != self.hover_pos:
            old_hover_pos = self.hover_pos
            self.hover_pos = pos

            # Only update the regions that need repainting
            self._update_hover_regions(old_hover_pos, pos)

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
            # Restore cursor for current tool
            current_tool = self.controller.get_current_tool_name()
            self._update_cursor_for_tool(current_tool)

        elif (
            event.button() == Qt.MouseButton.RightButton
            and self.temporary_picker
            and self.previous_tool
        ):
            # Restore previous tool after temporary picker
            self.controller.set_tool(self.previous_tool)
            self.temporary_picker = False
            self.previous_tool = None

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
            # Store the mouse position before zoom for cursor-focused zooming
            mouse_pos = event.position()

            # Calculate the point in image space that's under the cursor
            old_image_point = (mouse_pos - self.pan_offset) / self.zoom

            # Update zoom
            self.zoom = new_zoom
            self._update_size()

            # Calculate new position to keep the same image point under cursor
            new_canvas_point = old_image_point * new_zoom
            self.pan_offset = mouse_pos - new_canvas_point

            # Emit signal for UI update
            self.zoomRequested.emit(new_zoom)
            self.update()

        event.accept()

    def leaveEvent(self, event):
        """Handle mouse leave event"""
        old_hover_pos = self.hover_pos
        self.hover_pos = None
        self._update_hover_regions(old_hover_pos, None)

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
        """Show tooltip on enter and update cursor"""
        self.setToolTip(
            "Left click: Draw • Right click: Pick color • "
            "Middle click + drag: Pan • Wheel: Zoom"
        )
        # Update cursor for current tool
        if not self.panning:
            current_tool = self.controller.get_current_tool_name()
            self._update_cursor_for_tool(current_tool)
        super().enterEvent(event)
