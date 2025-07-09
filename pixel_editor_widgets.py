#!/usr/bin/env python3
"""
Custom widgets for the indexed pixel editor
Extracted for better code organization
"""

import traceback
from collections import deque
from datetime import datetime
from typing import Optional

import numpy as np
from PIL import Image
from PyQt6.QtCore import QPoint, QPointF, QRect, Qt, pyqtSignal
from PyQt6.QtGui import (
    QBrush,
    QColor,
    QMouseEvent,
    QPainter,
    QPen,
    QPolygon,
    QWheelEvent,
)
from PyQt6.QtWidgets import QScrollArea, QWidget

# Enhanced debug logging utilities (duplicated here for module independence)
DEBUG_MODE = True  # Set to False to disable debug logging

def debug_log(category: str, message: str, level: str = "INFO"):
    """Enhanced debug logging with timestamps and categories"""
    if not DEBUG_MODE:
        return

    timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
    formatted_msg = f"[{timestamp}] [{category}] [{level}] {message}"

    # Color coding for different log levels
    if level == "ERROR":
        print(f"\033[91m{formatted_msg}\033[0m")  # Red
    elif level == "WARNING":
        print(f"\033[93m{formatted_msg}\033[0m")  # Yellow
    elif level == "DEBUG":
        print(f"\033[94m{formatted_msg}\033[0m")  # Blue
    else:
        print(formatted_msg)  # Default

def debug_color(color_index: int, rgb: Optional[tuple[int, int, int]] = None) -> str:
    """Format color information for debugging"""
    if rgb:
        hex_color = f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}"
        return f"Index {color_index} (RGB: {rgb}, Hex: {hex_color})"
    return f"Index {color_index}"

def debug_exception(category: str, exception: Exception):
    """Log exceptions with full traceback"""
    debug_log(category, f"Exception: {type(exception).__name__}: {exception!s}", "ERROR")
    if DEBUG_MODE:
        traceback.print_exc()


class ZoomableScrollArea(QScrollArea):
    """Custom scroll area that forwards wheel events to canvas for zooming"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.canvas = None

    def setWidget(self, widget):
        """Override to store canvas reference"""
        super().setWidget(widget)
        if hasattr(widget, "wheelEvent"):
            self.canvas = widget

    def wheelEvent(self, event):
        """Forward wheel events to canvas for zooming, unless Ctrl is held for scrolling"""
        debug_log("SCROLL_AREA", f"Wheel event: delta={event.angleDelta().y()}, modifiers={event.modifiers()}", "DEBUG")

        # If Ctrl is held, use normal scroll behavior
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            debug_log("SCROLL_AREA", "Ctrl held, using scroll behavior")
            super().wheelEvent(event)
            return

        # Otherwise, forward to canvas for zooming
        if self.canvas and hasattr(self.canvas, "wheelEvent"):
            debug_log("SCROLL_AREA", "Forwarding to canvas for zooming", "DEBUG")
            self.canvas.wheelEvent(event)
        else:
            debug_log("SCROLL_AREA", "No canvas, using default behavior", "WARNING")
            super().wheelEvent(event)


class ColorPaletteWidget(QWidget):
    """Widget for displaying and selecting colors from the palette"""
    colorSelected = pyqtSignal(int)  # Emits the color index

    def __init__(self):
        super().__init__()
        # Default grayscale palette for proper visualization
        self.default_grayscale = [
            (0, 0, 0),        # 0 - Black (transparent)
            (17, 17, 17),     # 1
            (34, 34, 34),     # 2
            (51, 51, 51),     # 3
            (68, 68, 68),     # 4
            (85, 85, 85),     # 5
            (102, 102, 102),  # 6
            (119, 119, 119),  # 7
            (136, 136, 136),  # 8
            (153, 153, 153),  # 9
            (170, 170, 170),  # 10
            (187, 187, 187),  # 11
            (204, 204, 204),  # 12
            (221, 221, 221),  # 13
            (238, 238, 238),  # 14
            (255, 255, 255),  # 15 - White
        ]
        # Default color palette (for color mode)
        self.default_colors = [
            (0, 0, 0),        # 0 - Black (transparent)
            (255, 183, 197),  # 1 - Kirby pink
            (255, 255, 255),  # 2 - White
            (64, 64, 64),     # 3 - Dark gray (outline)
            (255, 0, 0),      # 4 - Red
            (0, 0, 255),      # 5 - Blue
            (255, 220, 220),  # 6 - Light pink
            (200, 120, 150),  # 7 - Dark pink
            (255, 255, 0),    # 8 - Yellow
            (0, 255, 0),      # 9 - Green
            (255, 128, 0),    # 10 - Orange
            (128, 0, 255),    # 11 - Purple
            (0, 128, 128),    # 12 - Teal
            (128, 128, 0),    # 13 - Olive
            (128, 128, 128),  # 14 - Gray
            (192, 192, 192),  # 15 - Light gray
        ]
        # Start with grayscale palette by default
        self.colors = self.default_grayscale.copy()
        self.selected_index = 1
        self.cell_size = 32
        self.is_grayscale_mode = True

        # External palette tracking
        self.is_external_palette = False
        self.palette_source = "Default Grayscale Palette"

        self.setFixedSize(4 * self.cell_size + 10, 4 * self.cell_size + 10)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)

        # Set initial tooltip
        self._update_tooltip()

    def set_palette(self, colors: list[tuple[int, int, int]], source: str = "External Palette"):
        """Set the palette colors"""
        if len(colors) >= 16:
            # Ensure we have valid tuples
            self.colors = []
            for i in range(16):
                if i < len(colors):
                    c = colors[i]
                    if isinstance(c, (list, tuple)) and len(c) >= 3:
                        self.colors.append((int(c[0]), int(c[1]), int(c[2])))
                    else:
                        self.colors.append((0, 0, 0))
                else:
                    self.colors.append((0, 0, 0))

            self.is_external_palette = True
            self.palette_source = source
            self._update_tooltip()
            self.update()
            self.repaint()  # Force immediate repaint
            debug_log("PALETTE", f"Loaded external palette: {source}")
            debug_log("PALETTE", f"First 4 colors: {[debug_color(i, c) for i, c in enumerate(self.colors[:4])]}", "DEBUG")
            # Check if colors are valid
            if all(c == (0, 0, 0) for c in self.colors):
                debug_log("PALETTE", "All colors are black!", "WARNING")

    def reset_to_default(self):
        """Reset to default grayscale palette"""
        self.colors = self.default_grayscale.copy()
        self.is_external_palette = False
        self.is_grayscale_mode = True
        self.palette_source = "Default Grayscale Palette"
        self._update_tooltip()
        self.update()
        debug_log("PALETTE", "Reset to default grayscale palette")

    def set_color_mode(self, use_colors: bool):
        """Switch between grayscale and color default palettes"""
        if not self.is_external_palette:
            if use_colors:
                self.colors = self.default_colors.copy()
                self.palette_source = "Default Color Palette"
                self.is_grayscale_mode = False
            else:
                self.colors = self.default_grayscale.copy()
                self.palette_source = "Default Grayscale Palette"
                self.is_grayscale_mode = True
            self._update_tooltip()
            self.update()
            debug_log("PALETTE", f"Switched to {'color' if use_colors else 'grayscale'} mode")
            debug_log("PALETTE", f"New palette colors: {[debug_color(i, c) for i, c in enumerate(self.colors[:4])]}", "DEBUG")

    def _update_tooltip(self):
        """Update the tooltip to show current palette information"""
        if self.is_external_palette:
            tooltip = f"External Palette: {self.palette_source}\nRight-click to reset to default"
        else:
            tooltip = "Default Editor Palette\n16 colors for sprite editing"
        self.setToolTip(tooltip)

    def _show_context_menu(self, position):
        """Show context menu for palette operations"""
        from PyQt6.QtGui import QAction
        from PyQt6.QtWidgets import QMenu

        menu = QMenu(self)

        if self.is_external_palette:
            reset_action = QAction("Reset to Default Palette", self)
            reset_action.triggered.connect(self.reset_to_default)
            menu.addAction(reset_action)

        info_action = QAction(f"Palette Source: {self.palette_source}", self)
        info_action.setEnabled(False)
        menu.addAction(info_action)

        if menu.actions():
            menu.exec(self.mapToGlobal(position))

    def paintEvent(self, event):
        painter = QPainter(self)

        # Draw external palette indicator border
        if self.is_external_palette:
            painter.setPen(QPen(Qt.GlobalColor.green, 2))
            painter.drawRect(1, 1, self.width() - 2, self.height() - 2)

        for i in range(16):
            row = i // 4
            col = i % 4
            x = col * self.cell_size + 5
            y = row * self.cell_size + 5

            # Draw color swatch - ensure we have valid colors
            if i < len(self.colors):
                try:
                    # Ensure color values are valid integers
                    r, g, b = self.colors[i]
                    r = int(r) if r is not None else 0
                    g = int(g) if g is not None else 0
                    b = int(b) if b is not None else 0
                    color = QColor(r, g, b)
                except (ValueError, TypeError, IndexError) as e:
                    debug_log("PALETTE", f"Error with color {i}: {self.colors[i]} - {e}", "ERROR")
                    color = QColor(0, 0, 0)
            else:
                color = QColor(0, 0, 0)

            painter.fillRect(x, y, self.cell_size - 2, self.cell_size - 2, color)

            # Debug: Draw index number for debugging
            # painter.setPen(Qt.GlobalColor.white if sum(self.colors[i]) < 384 else Qt.GlobalColor.black)
            # painter.drawText(x + 2, y + self.cell_size - 4, str(i))

            # Draw external palette indicator on first cell
            if self.is_external_palette and i == 0:
                # Small green indicator triangle in top-left corner
                painter.setBrush(QBrush(Qt.GlobalColor.green))
                painter.setPen(QPen(Qt.GlobalColor.green))
                triangle = QPolygon([
                    QPoint(x, y),
                    QPoint(x + 8, y),
                    QPoint(x, y + 8)
                ])
                painter.drawPolygon(triangle)

            # Draw selection border
            if i == self.selected_index:
                painter.setPen(QPen(Qt.GlobalColor.yellow, 3))
                painter.drawRect(x - 1, y - 1, self.cell_size, self.cell_size)

            # Draw index number
            painter.setPen(Qt.GlobalColor.white if sum(self.colors[i]) < 384 else Qt.GlobalColor.black)
            painter.drawText(QRect(x, y, self.cell_size - 2, self.cell_size - 2),
                           Qt.AlignmentFlag.AlignCenter, str(i))

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            x = int((event.position().x() - 5) // self.cell_size)
            y = int((event.position().y() - 5) // self.cell_size)
            if 0 <= x < 4 and 0 <= y < 4:
                index = y * 4 + x
                if 0 <= index < 16:
                    old_index = self.selected_index
                    self.selected_index = index

                    # Debug: Show color selection
                    debug_log("PALETTE", f"Color selected: {debug_color(old_index)} -> {debug_color(index, self.colors[index])}")

                    self.colorSelected.emit(index)
                    self.update()


class PixelCanvas(QWidget):
    """Main canvas for pixel editing with zoom support"""
    pixelChanged = pyqtSignal()

    def __init__(self, palette_widget=None):
        super().__init__()
        self.image_data = None  # numpy array of pixel indices
        self.zoom = 4  # Default zoom level - better for sprite sheets
        self.grid_visible = True
        self.greyscale_mode = False  # Show indices as greyscale
        self.show_color_preview = True  # Show color preview
        self.current_color = 1
        self.tool = "pencil"
        self.drawing = False
        self.last_point = None
        self.palette_widget = palette_widget  # Direct reference to palette widget

        # Transform-based panning (smooth, no scrollbar manipulation)
        self.panning = False
        self.pan_last_point = None
        self.pan_offset = QPointF(0.0, 0.0)  # Current pan offset for rendering (use float for smooth)
        self.editor_parent = None  # Reference to parent editor for zoom control

        # Debug: Show canvas initialization
        debug_log("CANVAS", f"Canvas initialized with zoom={self.zoom}, current_color={self.current_color}")
        if self.palette_widget:
            debug_log("CANVAS", f"Received palette widget with {len(self.palette_widget.colors)} colors")
            key_colors = [debug_color(i, self.palette_widget.colors[i]) for i in [0, 1, 4] if i < len(self.palette_widget.colors)]
            debug_log("CANVAS", f"Palette key colors: {key_colors}", "DEBUG")
        else:
            debug_log("CANVAS", "No palette widget provided - will use grayscale fallback", "WARNING")

        # Undo/redo system
        self.undo_stack = deque(maxlen=50)
        self.redo_stack = deque(maxlen=50)

        # Canvas setup
        self.setMouseTracking(True)
        self.setMinimumSize(200, 200)

        # Hover support
        self.hover_pos = None

    def new_image(self, width: int, height: int):
        """Create a new blank image"""
        self.image_data = np.zeros((height, width), dtype=np.uint8)
        self.undo_stack.clear()
        self.redo_stack.clear()

        # Debug: Show new image creation
        debug_log("CANVAS", f"Created new image: {width}x{height}")
        if self.palette_widget and self.current_color < len(self.palette_widget.colors):
            rgb_color = self.palette_widget.colors[self.current_color]
            debug_log("CANVAS", f"Current drawing color: {debug_color(self.current_color, rgb_color)}")
        else:
            debug_log("CANVAS", f"Current drawing color: {debug_color(self.current_color)}")

        self.update_size()
        self.update()

    def load_image(self, pil_image: Image.Image):
        """Load an indexed image"""
        if pil_image.mode != "P":
            raise ValueError("Image must be in indexed color mode (P)")

        # Convert to numpy array
        self.image_data = np.array(pil_image)

        # Store palette if available
        if pil_image.palette:
            palette_data = pil_image.palette.palette
            colors = []
            for i in range(16):
                if i * 3 + 2 < len(palette_data):
                    r = palette_data[i * 3]
                    g = palette_data[i * 3 + 1]
                    b = palette_data[i * 3 + 2]
                    colors.append((r, g, b))
                else:
                    colors.append((0, 0, 0))

            # Check if this is a grayscale palette
            is_grayscale = all(r == g == b for r, g, b in colors)

            # Don't override the palette widget if it already has an external palette loaded
            if self.palette_widget and not is_grayscale and not self.palette_widget.is_external_palette:
                # Only set as external palette if it's not grayscale AND no external palette is loaded
                self.palette_widget.set_palette(colors)
                debug_log("CANVAS", f"Set palette from image: {[debug_color(i, c) for i, c in enumerate(colors[:4])]}", "DEBUG")
            elif self.palette_widget and is_grayscale:
                # Keep grayscale mode but don't mark as external
                debug_log("CANVAS", "Detected grayscale palette, keeping current palette mode")
            elif self.palette_widget and self.palette_widget.is_external_palette:
                debug_log("CANVAS", f"Keeping existing external palette: {self.palette_widget.palette_source}")

        self.undo_stack.clear()
        self.redo_stack.clear()
        self.update_size()
        self.update()

    def get_pil_image(self) -> Optional[Image.Image]:
        """Convert current image to PIL Image"""
        if self.image_data is None:
            return None

        # Create indexed image
        img = Image.fromarray(self.image_data, mode="P")

        # Set palette based on mode
        palette = []
        if self.greyscale_mode:
            # Greyscale mode: use grayscale palette
            for i in range(16):
                gray = (i * 255) // 15
                palette.extend([gray, gray, gray])
        # Color mode: use external palette if available, otherwise use palette widget
        elif self.editor_parent and hasattr(self.editor_parent, "external_palette_colors") and self.editor_parent.external_palette_colors:
            # Use external palette for game-accurate colors
            for color in self.editor_parent.external_palette_colors:
                palette.extend(color)
        elif self.palette_widget:
            for color in self.palette_widget.colors:
                palette.extend(color)
        else:
            # Default grayscale palette
            for i in range(16):
                gray = (i * 255) // 15
                palette.extend([gray, gray, gray])

        # Pad to 256 colors
        while len(palette) < 768:
            palette.extend([0, 0, 0])

        img.putpalette(palette)
        return img

    def update_size(self):
        """Update widget size based on image and zoom"""
        if self.image_data is not None:
            height, width = self.image_data.shape
            self.setFixedSize(width * self.zoom, height * self.zoom)

    def set_zoom(self, zoom: int):
        """Set zoom level"""
        self.zoom = max(1, min(64, zoom))
        self.update_size()
        self.update()

    def save_undo(self):
        """Save current state for undo"""
        if self.image_data is not None:
            self.undo_stack.append(self.image_data.copy())
            self.redo_stack.clear()

    def undo(self):
        """Undo last operation"""
        if self.undo_stack and self.image_data is not None:
            self.redo_stack.append(self.image_data.copy())
            self.image_data = self.undo_stack.pop()
            self.update()
            self.pixelChanged.emit()

    def redo(self):
        """Redo last undone operation"""
        if self.redo_stack and self.image_data is not None:
            self.undo_stack.append(self.image_data.copy())
            self.image_data = self.redo_stack.pop()
            self.update()
            self.pixelChanged.emit()

    def paintEvent(self, event):
        if self.image_data is None:
            return

        painter = QPainter(self)

        # Apply pan offset transform for smooth panning
        painter.translate(self.pan_offset)

        height, width = self.image_data.shape

        # Get colors based on mode
        if self.greyscale_mode:
            # Greyscale mode: show indices as shades of grey
            colors = [(i * 17, i * 17, i * 17) for i in range(16)]
            if not hasattr(self, "_last_paint_mode") or self._last_paint_mode != "greyscale":
                debug_log("CANVAS", "PaintEvent using greyscale mode", "DEBUG")
                self._last_paint_mode = "greyscale"
        # Color mode: use external palette if available, otherwise use palette widget
        elif self.editor_parent and hasattr(self.editor_parent, "external_palette_colors") and self.editor_parent.external_palette_colors:
            # Use external palette for game-accurate colors
            colors = self.editor_parent.external_palette_colors
            if not hasattr(self, "_last_paint_mode") or self._last_paint_mode != "external":
                debug_log("CANVAS", "PaintEvent using external palette colors", "DEBUG")
                debug_log("CANVAS", f"External palette: {[debug_color(i, c) for i, c in enumerate(colors[:4])]}", "DEBUG")
                self._last_paint_mode = "external"
        elif self.palette_widget:
            colors = self.palette_widget.colors
            # Debug: print first few colors to verify they're not all black
            if not hasattr(self, "_debug_colors_printed"):
                debug_log("CANVAS", "PaintEvent using palette widget colors", "DEBUG")
                debug_log("CANVAS", f"Palette colors: {[debug_color(i, c) for i, c in enumerate(colors[:4])]}", "DEBUG")

                # Check if palette looks correct
                unique_colors = set(colors)
                if len(unique_colors) == 1:
                    debug_log("CANVAS", f"All palette colors are the same: {colors[0]}", "WARNING")
                elif len(unique_colors) < 4:
                    debug_log("CANVAS", f"Only {len(unique_colors)} unique colors in palette", "WARNING")
                else:
                    debug_log("CANVAS", f"Palette has {len(unique_colors)} unique colors", "DEBUG")

                self._debug_colors_printed = True
                self._last_paint_mode = "palette_widget"
        else:
            # Default grayscale palette
            colors = [(i * 17, i * 17, i * 17) for i in range(16)]
            debug_log("CANVAS", "PaintEvent using grayscale fallback colors!", "WARNING")
            self._last_paint_mode = "fallback"

        # Draw pixels
        for y in range(height):
            for x in range(width):
                pixel_index = self.image_data[y, x]
                if pixel_index < len(colors):
                    color = QColor(*colors[pixel_index])
                else:
                    color = QColor(255, 0, 255)  # Magenta for invalid indices

                painter.fillRect(x * self.zoom, y * self.zoom,
                               self.zoom, self.zoom, color)

        # Draw grid
        if self.grid_visible and self.zoom > 4:
            painter.setPen(QPen(QColor(128, 128, 128, 128), 1))

            # Vertical lines
            for x in range(width + 1):
                painter.drawLine(x * self.zoom, 0, x * self.zoom, height * self.zoom)

            # Horizontal lines
            for y in range(height + 1):
                painter.drawLine(0, y * self.zoom, width * self.zoom, y * self.zoom)

        # Draw hover highlight
        if self.hover_pos and not self.panning:
            painter.setPen(QPen(Qt.GlobalColor.white, 2))
            painter.drawRect(self.hover_pos.x() * self.zoom,
                           self.hover_pos.y() * self.zoom,
                           self.zoom, self.zoom)

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drawing = True
            self.save_undo()
            pos = self.get_pixel_pos(event.position())
            if pos:
                if self.tool == "pencil":
                    self.draw_pixel(pos.x(), pos.y())
                elif self.tool == "fill":
                    self.flood_fill(pos.x(), pos.y())
                elif self.tool == "picker":
                    self.pick_color(pos.x(), pos.y())
                self.last_point = pos
        elif event.button() == Qt.MouseButton.MiddleButton:
            self.panning = True
            self.pan_last_point = event.position()
            self.setCursor(Qt.CursorShape.OpenHandCursor)
            debug_log("CANVAS", f"Started panning at position {event.position().x():.0f}, {event.position().y():.0f}", "DEBUG")

    def mouseMoveEvent(self, event: QMouseEvent):
        # Handle transform-based panning - direct and smooth
        if self.panning and self.pan_last_point:
            delta = event.position() - self.pan_last_point
            self.pan_last_point = event.position()

            # Apply delta directly to pan offset (smooth transform-based panning)
            self.pan_offset += delta

            # Trigger immediate repaint for smooth visual feedback
            self.update()

            return  # Don't do regular drawing while panning

        pos = self.get_pixel_pos(event.position())
        if pos:
            self.hover_pos = pos
            self.update()

            if self.drawing and self.tool == "pencil":
                if self.last_point and self.last_point != pos:
                    self.draw_line(self.last_point.x(), self.last_point.y(),
                                 pos.x(), pos.y())
                    self.last_point = pos
                else:
                    self.draw_pixel(pos.x(), pos.y())

    def mouseReleaseEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drawing = False
            self.last_point = None
        elif event.button() == Qt.MouseButton.MiddleButton:
            self.panning = False
            self.pan_last_point = None
            self.setCursor(Qt.CursorShape.ArrowCursor)
            debug_log("CANVAS", f"Stopped panning, total offset: {self.pan_offset.x():.0f}, {self.pan_offset.y():.0f}", "DEBUG")

    def wheelEvent(self, event: QWheelEvent):
        """Handle mouse wheel for zooming"""
        if self.editor_parent is None:
            return

        # Get wheel delta (positive = zoom in, negative = zoom out)
        delta = event.angleDelta().y()
        current_zoom = self.zoom

        # Predefined zoom levels for smooth progression
        zoom_levels = [1, 2, 4, 8, 16, 32, 64]

        # Find current zoom level index
        current_index = 0
        for i, level in enumerate(zoom_levels):
            if level <= current_zoom:
                current_index = i
            else:
                break

        # Calculate new zoom level
        if delta > 0:
            # Zoom in - move to next higher level
            new_index = min(current_index + 1, len(zoom_levels) - 1)
        else:
            # Zoom out - move to next lower level
            new_index = max(current_index - 1, 0)

        new_zoom = zoom_levels[new_index]

        # Apply zoom if different
        if new_zoom != current_zoom:
            if hasattr(self.editor_parent, "set_zoom_preset"):
                self.editor_parent.set_zoom_preset(new_zoom)
                debug_log("CANVAS", f"Mouse wheel zoom: {current_zoom}x -> {new_zoom}x (delta: {delta})", "DEBUG")
            else:
                debug_log("CANVAS", "No editor_parent.set_zoom_preset method", "ERROR")
        else:
            debug_log("CANVAS", f"Mouse wheel zoom: Already at {current_zoom}x limit", "DEBUG")

        # Also try direct zoom setting as fallback
        if new_zoom != current_zoom and not hasattr(self.editor_parent, "set_zoom_preset"):
            debug_log("CANVAS", "Trying direct zoom setting as fallback", "WARNING")
            self.set_zoom(new_zoom)

        event.accept()

    def enterEvent(self, event):
        """Show help cursor when entering canvas"""
        if not self.panning and not self.drawing:
            self.setToolTip("Left click: Draw • Middle click + drag: Pan • Wheel: Zoom • Ctrl+Wheel: Scroll")
        super().enterEvent(event)

    def leaveEvent(self, event):
        """Reset cursor when leaving canvas"""
        if not self.panning:
            self.setCursor(Qt.CursorShape.ArrowCursor)
        super().leaveEvent(event)

    def get_pixel_pos(self, pos) -> Optional[QPoint]:
        """Convert mouse position to pixel coordinates (accounting for pan offset)"""
        if self.image_data is None:
            return None

        # Adjust mouse position by pan offset to get actual pixel coordinates
        adjusted_pos = pos - self.pan_offset

        x = int(adjusted_pos.x() // self.zoom)
        y = int(adjusted_pos.y() // self.zoom)

        height, width = self.image_data.shape
        if 0 <= x < width and 0 <= y < height:
            return QPoint(x, y)
        return None

    def draw_pixel(self, x: int, y: int):
        """Draw a single pixel"""
        if self.image_data is None:
            debug_log("CANVAS", "Cannot draw pixel - no image data", "ERROR")
            return

        height, width = self.image_data.shape
        if 0 <= x < width and 0 <= y < height:
            # Validate and clamp color to 4bpp range (0-15)
            color = max(0, min(15, int(self.current_color)))
            old_value = self.image_data[y, x]
            self.image_data[y, x] = np.uint8(color)

            # Debug: Show pixel drawing with detailed information
            if self.palette_widget and color < len(self.palette_widget.colors):
                old_rgb = self.palette_widget.colors[old_value] if old_value < len(self.palette_widget.colors) else None
                new_rgb = self.palette_widget.colors[color]
                debug_log("CANVAS", f"Pixel ({x},{y}): {debug_color(old_value, old_rgb)} -> {debug_color(color, new_rgb)}")
            else:
                debug_log("CANVAS", f"Pixel ({x},{y}): index {old_value} -> {color} (no palette)", "WARNING")

            self.update()
            self.pixelChanged.emit()
        else:
            debug_log("CANVAS", f"Draw pixel out of bounds: ({x},{y}) for {width}x{height} image", "WARNING")

    def draw_line(self, x0: int, y0: int, x1: int, y1: int):
        """Draw a line between two points using Bresenham's algorithm"""
        dx = abs(x1 - x0)
        dy = abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx - dy

        while True:
            self.draw_pixel(x0, y0)

            if x0 == x1 and y0 == y1:
                break

            e2 = 2 * err
            if e2 > -dy:
                err -= dy
                x0 += sx
            if e2 < dx:
                err += dx
                y0 += sy

    def flood_fill(self, x: int, y: int):
        """Flood fill from the given point"""
        if self.image_data is None:
            return

        height, width = self.image_data.shape
        if not (0 <= x < width and 0 <= y < height):
            return

        target_color = self.image_data[y, x]
        # Validate and clamp color to 4bpp range (0-15)
        replacement_color = max(0, min(15, int(self.current_color)))

        if target_color == replacement_color:
            return

        # Simple flood fill using a stack
        stack = [(x, y)]
        filled_pixels = 0

        while stack:
            cx, cy = stack.pop()

            if not (0 <= cx < width and 0 <= cy < height):
                continue
            if self.image_data[cy, cx] != target_color:
                continue

            self.image_data[cy, cx] = np.uint8(replacement_color)
            filled_pixels += 1

            # Add neighboring pixels
            stack.extend([(cx+1, cy), (cx-1, cy), (cx, cy+1), (cx, cy-1)])

        # Get color info for logging
        color_info = replacement_color
        if self.palette_widget and replacement_color < len(self.palette_widget.colors):
            rgb = self.palette_widget.colors[replacement_color]
            color_info = debug_color(replacement_color, rgb)

        debug_log("CANVAS", f"Flood fill: filled {filled_pixels} pixels with {color_info} (replaced index {target_color})")
        self.update()
        self.pixelChanged.emit()

    def pick_color(self, x: int, y: int):
        """Pick color from pixel"""
        if self.image_data is None:
            return

        height, width = self.image_data.shape
        if 0 <= x < width and 0 <= y < height:
            picked_color = int(self.image_data[y, x])
            self.current_color = picked_color

            if self.palette_widget:
                self.palette_widget.selected_index = picked_color
                self.palette_widget.update()
                self.palette_widget.colorSelected.emit(picked_color)

            # Get color info for logging
            color_info = picked_color
            if self.palette_widget and picked_color < len(self.palette_widget.colors):
                rgb = self.palette_widget.colors[picked_color]
                color_info = debug_color(picked_color, rgb)

            debug_log("CANVAS", f"Picked {color_info} from pixel ({x},{y})")
