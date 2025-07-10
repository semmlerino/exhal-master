#!/usr/bin/env python3
"""
Custom widgets for the indexed pixel editor
Extracted for better code organization
"""

# Standard library imports
from typing import Optional

# Third-party imports
import numpy as np
from PIL import Image
from PyQt6.QtCore import QPoint, QPointF, QRect, Qt, pyqtSignal
from PyQt6.QtGui import (
    QBrush,
    QColor,
    QMouseEvent,
    QPainter,
    QPainterPath,
    QPen,
    QPolygon,
    QWheelEvent,
)
from PyQt6.QtWidgets import (
    QDialog,
    QLabel,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

# Import constants
from pixel_editor_constants import (
    GRID_VISIBLE_THRESHOLD,
    COLOR_INVALID_INDEX,
    COLOR_GRID_LINES,
    PALETTE_COLORS_COUNT,
)

# Import common utilities
from pixel_editor_utils import (
    DEBUG_MODE,
    debug_log,
    debug_color,
    debug_exception,
    validate_color_index,
    validate_rgb_color,
    should_use_white_text,
    extract_palette_from_pil_image,
    is_grayscale_palette,
    create_indexed_palette,
    DEFAULT_GRAYSCALE_PALETTE,
    DEFAULT_COLOR_PALETTE,
)

# Import undo/redo command system
from pixel_editor_commands import (
    UndoManager,
    DrawPixelCommand,
    DrawLineCommand,
    FloodFillCommand,
    BatchCommand,
)


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
        debug_log(
            "SCROLL_AREA",
            f"Wheel event: delta={event.angleDelta().y()}, modifiers={event.modifiers()}",
            "DEBUG",
        )

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
        # Use default palettes from utilities
        self.default_grayscale = DEFAULT_GRAYSCALE_PALETTE.copy()
        self.default_colors = DEFAULT_COLOR_PALETTE.copy()
        
        # Start with grayscale palette by default
        self.colors = self.default_grayscale.copy()
        self.selected_index = 1
        self.cell_size = 32
        self.is_grayscale_mode = True

        # External palette tracking
        self.is_external_palette = False
        self.palette_source = "Default Grayscale Palette"
        
        # Connected canvas for automatic updates
        self._connected_canvas = None

        self.setFixedSize(4 * self.cell_size + 10, 4 * self.cell_size + 10)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)

        # Set initial tooltip
        self._update_tooltip()

    def set_palette(
        self, colors: list[tuple[int, int, int]], source: str = "External Palette"
    ):
        """Set the palette colors"""
        if len(colors) >= 16:
            # Ensure we have valid tuples
            self.colors = []
            for i in range(16):
                if i < len(colors):
                    c = colors[i]
                    self.colors.append(validate_rgb_color(c))
                else:
                    self.colors.append((0, 0, 0))

            self.is_external_palette = True
            self.palette_source = source
            self._update_tooltip()
            self.update()
            self.repaint()  # Force immediate repaint
            debug_log("PALETTE", f"Loaded external palette: {source}")
            debug_log(
                "PALETTE",
                f"First 4 colors: {[debug_color(i, c) for i, c in enumerate(self.colors[:4])]}",
                "DEBUG",
            )
            # Check if colors are valid
            if all(c == (0, 0, 0) for c in self.colors):
                debug_log("PALETTE", "All colors are black!", "WARNING")
            
            # Signal that colors have changed
            self.colors_changed()

    def reset_to_default(self):
        """Reset to default grayscale palette"""
        self.colors = self.default_grayscale.copy()
        self.is_external_palette = False
        self.is_grayscale_mode = True
        self.palette_source = "Default Grayscale Palette"
        self._update_tooltip()
        self.update()
        debug_log("PALETTE", "Reset to default grayscale palette")
        
        # Signal that colors have changed
        self.colors_changed()

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
            debug_log(
                "PALETTE", f"Switched to {'color' if use_colors else 'grayscale'} mode"
            )
            debug_log(
                "PALETTE",
                f"New palette colors: {[debug_color(i, c) for i, c in enumerate(self.colors[:4])]}",
                "DEBUG",
            )
    
    def colors_changed(self):
        """Signal that colors have changed - used by canvas for cache invalidation"""
        # Notify connected canvas to update its color cache
        if hasattr(self, '_connected_canvas') and self._connected_canvas:
            self._connected_canvas._palette_version += 1
            self._connected_canvas.update()
    
    def connect_canvas(self, canvas):
        """Connect a canvas widget to receive palette updates"""
        self._connected_canvas = canvas

    def _update_tooltip(self):
        """Update the tooltip to show current palette information"""
        if self.is_external_palette:
            tooltip = f"External Palette: {self.palette_source}\nRight-click to reset to default"
        else:
            tooltip = "Default Editor Palette\n16 colors for sprite editing"
        self.setToolTip(tooltip)

    def _show_context_menu(self, position):
        """Show context menu for palette operations"""
        # Third-party imports
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
                rgb = validate_rgb_color(self.colors[i])
                color = QColor(*rgb)
            else:
                color = QColor(0, 0, 0)

            painter.fillRect(x, y, self.cell_size - 2, self.cell_size - 2, color)

            # Draw external palette indicator on first cell
            if self.is_external_palette and i == 0:
                # Small green indicator triangle in top-left corner
                painter.setBrush(QBrush(Qt.GlobalColor.green))
                painter.setPen(QPen(Qt.GlobalColor.green))
                triangle = QPolygon([QPoint(x, y), QPoint(x + 8, y), QPoint(x, y + 8)])
                painter.drawPolygon(triangle)

            # Draw selection border
            if i == self.selected_index:
                painter.setPen(QPen(Qt.GlobalColor.yellow, 3))
                painter.drawRect(x - 1, y - 1, self.cell_size, self.cell_size)

            # Draw index number
            if i < len(self.colors):
                painter.setPen(
                    Qt.GlobalColor.white
                    if should_use_white_text(self.colors[i])
                    else Qt.GlobalColor.black
                )
            else:
                painter.setPen(Qt.GlobalColor.white)
            painter.drawText(
                QRect(x, y, self.cell_size - 2, self.cell_size - 2),
                Qt.AlignmentFlag.AlignCenter,
                str(i),
            )

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
                    debug_log(
                        "PALETTE",
                        f"Color selected: {debug_color(old_index)} -> {debug_color(index, self.colors[index])}",
                    )

                    self.colorSelected.emit(index)
                    self.update()
                    # Notify any connected canvas that palette changed
                    self.colors_changed()


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
        self.pan_offset = QPointF(
            0.0, 0.0
        )  # Current pan offset for rendering (use float for smooth)
        self.editor_parent = None  # Reference to parent editor for zoom control
        
        # QColor caching for performance
        self._qcolor_cache = {}  # Dict[int, QColor] - maps color index to QColor
        self._palette_version = 0  # Incremented when palette changes
        self._cached_palette_version = -1  # Version of cached colors

        # Debug: Show canvas initialization
        debug_log(
            "CANVAS",
            f"Canvas initialized with zoom={self.zoom}, current_color={self.current_color}",
        )
        if self.palette_widget:
            debug_log(
                "CANVAS",
                f"Received palette widget with {len(self.palette_widget.colors)} colors",
            )
            key_colors = [
                debug_color(i, self.palette_widget.colors[i])
                for i in [0, 1, 4]
                if i < len(self.palette_widget.colors)
            ]
            debug_log("CANVAS", f"Palette key colors: {key_colors}", "DEBUG")
        else:
            debug_log(
                "CANVAS",
                "No palette widget provided - will use grayscale fallback",
                "WARNING",
            )

        # Undo/redo system - using delta-based command pattern
        self.undo_manager = UndoManager(max_commands=100, compression_age=20)
        self.current_batch = None  # For grouping continuous drawing operations
        
        # Connect to palette widget for automatic updates
        if self.palette_widget:
            self.palette_widget.connect_canvas(self)

        # Canvas setup
        self.setMouseTracking(True)
        self.setMinimumSize(200, 200)

        # Hover support
        self.hover_pos = None
        
        # Dirty rectangle tracking
        self._dirty_rect = None  # QRect of area needing redraw
        self._accumulate_dirty = False  # Whether to accumulate dirty rects

    def new_image(self, width: int, height: int):
        """Create a new blank image"""
        self.image_data = np.zeros((height, width), dtype=np.uint8)
        self.undo_manager.clear()
        self._palette_version += 1  # Force color cache update

        # Debug: Show new image creation
        debug_log("CANVAS", f"Created new image: {width}x{height}")
        if self.palette_widget and self.current_color < len(self.palette_widget.colors):
            rgb_color = self.palette_widget.colors[self.current_color]
            debug_log(
                "CANVAS",
                f"Current drawing color: {debug_color(self.current_color, rgb_color)}",
            )
        else:
            debug_log(
                "CANVAS", f"Current drawing color: {debug_color(self.current_color)}"
            )

        self.update_size()
        self.update()

    def load_image(self, pil_image: Image.Image):
        """Load an indexed image"""
        if pil_image.mode != "P":
            raise ValueError("Image must be in indexed color mode (P)")

        # Convert to numpy array
        self.image_data = np.array(pil_image)
        self._palette_version += 1  # Force color cache update

        # Store palette if available
        if pil_image.palette:
            colors = extract_palette_from_pil_image(pil_image, max_colors=16)

            # Check if this is a grayscale palette
            is_grayscale = is_grayscale_palette(colors)

            # Don't override the palette widget if it already has an external palette loaded
            if (
                self.palette_widget
                and not is_grayscale
                and not self.palette_widget.is_external_palette
            ):
                # Only set as external palette if it's not grayscale AND no external palette is loaded
                self.palette_widget.set_palette(colors)
                debug_log(
                    "CANVAS",
                    f"Set palette from image: {[debug_color(i, c) for i, c in enumerate(colors[:4])]}",
                    "DEBUG",
                )
            elif self.palette_widget and is_grayscale:
                # Keep grayscale mode but don't mark as external
                debug_log(
                    "CANVAS", "Detected grayscale palette, keeping current palette mode"
                )
            elif self.palette_widget and self.palette_widget.is_external_palette:
                debug_log(
                    "CANVAS",
                    f"Keeping existing external palette: {self.palette_widget.palette_source}",
                )

        self.undo_manager.clear()
        self.update_size()
        self.update()

    def get_pil_image(self) -> Optional[Image.Image]:
        """Convert current image to PIL Image"""
        if self.image_data is None:
            return None

        # Create indexed image
        img = Image.fromarray(self.image_data, mode="P")

        # Set palette based on mode
        if self.greyscale_mode:
            # Greyscale mode: use grayscale palette
            colors = [(i * 255) // 15 for i in range(16)]
            palette = create_indexed_palette([(g, g, g) for g in colors])
        # Color mode: use external palette if available, otherwise use palette widget
        elif (
            self.editor_parent
            and hasattr(self.editor_parent, "external_palette_colors")
            and self.editor_parent.external_palette_colors
        ):
            # Use external palette for game-accurate colors
            palette = create_indexed_palette(self.editor_parent.external_palette_colors)
        elif self.palette_widget:
            palette = create_indexed_palette(self.palette_widget.colors)
        else:
            # Default grayscale palette
            colors = [(i * 255) // 15 for i in range(16)]
            palette = create_indexed_palette([(g, g, g) for g in colors])

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

    def undo(self):
        """Undo last operation"""
        if self.undo_manager.undo(self):
            self.update()
            self.pixelChanged.emit()

    def redo(self):
        """Redo last undone operation"""
        if self.undo_manager.redo(self):
            self.update()
            self.pixelChanged.emit()

    def get_undo_count(self) -> int:
        """Get number of available undo operations"""
        stats = self.undo_manager.get_memory_usage()
        return stats['current_index'] + 1 if stats['can_undo'] else 0

    def get_redo_count(self) -> int:
        """Get number of available redo operations"""
        stats = self.undo_manager.get_memory_usage()
        if stats['can_redo']:
            return stats['command_count'] - stats['current_index'] - 1
        return 0

    def _update_qcolor_cache(self):
        """Update cached QColor objects when palette changes"""
        self._qcolor_cache.clear()
        
        # Get current color palette
        if self.greyscale_mode:
            # Greyscale mode: show indices as shades of grey
            colors = [(i * 17, i * 17, i * 17) for i in range(PALETTE_COLORS_COUNT)]
        elif (
            self.editor_parent
            and hasattr(self.editor_parent, "external_palette_colors")
            and self.editor_parent.external_palette_colors
        ):
            # Use external palette for game-accurate colors
            colors = self.editor_parent.external_palette_colors
        elif self.palette_widget:
            colors = self.palette_widget.colors
        else:
            # Default grayscale palette
            colors = [(i * 17, i * 17, i * 17) for i in range(PALETTE_COLORS_COUNT)]
        
        # Pre-create QColor objects for all 16 colors
        for i in range(min(len(colors), PALETTE_COLORS_COUNT)):
            self._qcolor_cache[i] = QColor(*colors[i])
        
        # Add magenta for invalid indices
        self._qcolor_cache[-1] = QColor(*COLOR_INVALID_INDEX)
        
        self._cached_palette_version = self._palette_version
        debug_log("CANVAS", f"Updated QColor cache with {len(self._qcolor_cache)-1} colors", "DEBUG")

    def _get_visible_pixel_range(self):
        """Calculate which pixels are visible in the current viewport"""
        if self.image_data is None:
            return None
        
        # Get the parent widget (should be the scroll area's viewport)
        parent = self.parent()
        if not parent:
            return None
            
        # Get viewport rect in our coordinate system
        viewport_rect = self.rect()
        
        # If we're in a scroll area, get the actual visible rect
        scroll_area = parent.parent() if parent else None
        if scroll_area and hasattr(scroll_area, 'viewport'):
            viewport = scroll_area.viewport()
            if viewport:
                # Get the visible area in scroll area coordinates
                visible_rect = viewport.rect()
                # Map to our coordinates
                top_left = self.mapFromParent(visible_rect.topLeft())
                bottom_right = self.mapFromParent(visible_rect.bottomRight())
                viewport_rect = QRect(top_left, bottom_right)
        
        # Account for pan offset
        adjusted_rect = viewport_rect.translated(-int(self.pan_offset.x()), -int(self.pan_offset.y()))
        
        # Calculate pixel boundaries
        left = max(0, adjusted_rect.left() // self.zoom)
        top = max(0, adjusted_rect.top() // self.zoom)
        right = min(self.image_data.shape[1], (adjusted_rect.right() // self.zoom) + 2)
        bottom = min(self.image_data.shape[0], (adjusted_rect.bottom() // self.zoom) + 2)
        
        return (left, top, right, bottom)

    def paintEvent(self, event):
        if self.image_data is None:
            return

        painter = QPainter(self)

        # Apply pan offset transform for smooth panning
        painter.translate(self.pan_offset)

        height, width = self.image_data.shape
        
        # Update color cache if palette changed
        if self._cached_palette_version != self._palette_version:
            self._update_qcolor_cache()

        # Get visible pixel range for viewport culling
        visible_range = self._get_visible_pixel_range()
        if not visible_range:
            # Fallback to full image if we can't determine visibility
            visible_range = (0, 0, width, height)
        
        left, top, right, bottom = visible_range
        debug_log(
            "CANVAS", 
            f"Viewport culling: drawing pixels ({left},{top}) to ({right},{bottom}) out of {width}x{height}",
            "DEBUG"
        )

        # Draw pixels with viewport culling
        for y in range(top, bottom):
            for x in range(left, right):
                pixel_index = self.image_data[y, x]
                
                # Use cached QColor - much faster than creating new ones
                if pixel_index < PALETTE_COLORS_COUNT and pixel_index in self._qcolor_cache:
                    color = self._qcolor_cache[pixel_index]
                else:
                    color = self._qcolor_cache.get(-1, QColor(*COLOR_INVALID_INDEX))

                painter.fillRect(
                    x * self.zoom, y * self.zoom, self.zoom, self.zoom, color
                )

        # Draw grid with optimized path drawing (only for visible area)
        if self.grid_visible and self.zoom > GRID_VISIBLE_THRESHOLD:
            self._draw_grid_optimized(painter, left, top, right, bottom)

        # Draw hover highlight
        if self.hover_pos and not self.panning:
            painter.setPen(QPen(Qt.GlobalColor.white, 2))
            painter.drawRect(
                self.hover_pos.x() * self.zoom,
                self.hover_pos.y() * self.zoom,
                self.zoom,
                self.zoom,
            )
        
        # Clear dirty rect after painting
        self._dirty_rect = None
    
    def _draw_grid_optimized(self, painter, left, top, right, bottom):
        """Draw grid lines only for visible area using QPainterPath for efficiency"""
        painter.setPen(QPen(QColor(*COLOR_GRID_LINES), 1))
        
        # Create a path for all grid lines
        grid_path = QPainterPath()
        
        # Vertical lines
        for x in range(left, right + 1):
            grid_path.moveTo(x * self.zoom, top * self.zoom)
            grid_path.lineTo(x * self.zoom, bottom * self.zoom)
        
        # Horizontal lines  
        for y in range(top, bottom + 1):
            grid_path.moveTo(left * self.zoom, y * self.zoom)
            grid_path.lineTo(right * self.zoom, y * self.zoom)
        
        # Draw all grid lines in one operation
        painter.drawPath(grid_path)

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drawing = True
            pos = self.get_pixel_pos(event.position())
            if pos:
                if self.tool == "pencil":
                    # Start a batch command for continuous drawing
                    self.current_batch = BatchCommand()
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
            debug_log(
                "CANVAS",
                f"Started panning at position {event.position().x():.0f}, {event.position().y():.0f}",
                "DEBUG",
            )

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
                    self.draw_line(
                        self.last_point.x(), self.last_point.y(), pos.x(), pos.y()
                    )
                    self.last_point = pos
                else:
                    self.draw_pixel(pos.x(), pos.y())

    def mouseReleaseEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drawing = False
            self.last_point = None
            
            # Finalize batch command if we were doing continuous drawing
            if self.current_batch and len(self.current_batch.commands) > 0:
                self.undo_manager.execute_command(self.current_batch, self)
                self.current_batch = None
        elif event.button() == Qt.MouseButton.MiddleButton:
            self.panning = False
            self.pan_last_point = None
            self.setCursor(Qt.CursorShape.ArrowCursor)
            debug_log(
                "CANVAS",
                f"Stopped panning, total offset: {self.pan_offset.x():.0f}, {self.pan_offset.y():.0f}",
                "DEBUG",
            )

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
                debug_log(
                    "CANVAS",
                    f"Mouse wheel zoom: {current_zoom}x -> {new_zoom}x (delta: {delta})",
                    "DEBUG",
                )
            else:
                debug_log("CANVAS", "No editor_parent.set_zoom_preset method", "ERROR")
        else:
            debug_log(
                "CANVAS", f"Mouse wheel zoom: Already at {current_zoom}x limit", "DEBUG"
            )

        # Also try direct zoom setting as fallback
        if new_zoom != current_zoom and not hasattr(
            self.editor_parent, "set_zoom_preset"
        ):
            debug_log("CANVAS", "Trying direct zoom setting as fallback", "WARNING")
            self.set_zoom(new_zoom)

        event.accept()

    def enterEvent(self, event):
        """Show help cursor when entering canvas"""
        if not self.panning and not self.drawing:
            self.setToolTip(
                "Left click: Draw • Middle click + drag: Pan • Wheel: Zoom • Ctrl+Wheel: Scroll"
            )
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

    def mark_dirty(self, x: int, y: int, w: int = 1, h: int = 1):
        """Mark a region as needing redraw"""
        # Convert pixel coordinates to canvas coordinates
        canvas_x = int(x * self.zoom)
        canvas_y = int(y * self.zoom) 
        canvas_w = int(w * self.zoom)
        canvas_h = int(h * self.zoom)
        
        dirty = QRect(canvas_x, canvas_y, canvas_w, canvas_h)
        
        if self._dirty_rect is None:
            self._dirty_rect = dirty
        else:
            self._dirty_rect = self._dirty_rect.united(dirty)
        
        # Schedule update for dirty region only
        self.update(self._dirty_rect)
    
    def draw_pixel(self, x: int, y: int):
        """Draw a single pixel"""
        if self.image_data is None:
            debug_log("CANVAS", "Cannot draw pixel - no image data", "ERROR")
            return

        height, width = self.image_data.shape
        if 0 <= x < width and 0 <= y < height:
            # Validate and clamp color to 4bpp range (0-15)
            color = validate_color_index(self.current_color)
            old_value = self.image_data[y, x]
            
            # Don't draw if color is already the same
            if old_value == color:
                return
            
            # Create command for this pixel change
            command = DrawPixelCommand(x=x, y=y, old_color=old_value, new_color=color)
            
            # If we're in a batch (continuous drawing), add to batch
            if self.current_batch is not None:
                self.current_batch.add_command(command)
                # Execute immediately for visual feedback
                command.execute(self)
            else:
                # Single pixel operation - execute through undo manager
                self.undo_manager.execute_command(command, self)

            # Debug: Show pixel drawing with detailed information
            if self.palette_widget and color < len(self.palette_widget.colors):
                old_rgb = (
                    self.palette_widget.colors[old_value]
                    if old_value < len(self.palette_widget.colors)
                    else None
                )
                new_rgb = self.palette_widget.colors[color]
                debug_log(
                    "CANVAS",
                    f"Pixel ({x},{y}): {debug_color(old_value, old_rgb)} -> {debug_color(color, new_rgb)}",
                )
            else:
                debug_log(
                    "CANVAS",
                    f"Pixel ({x},{y}): index {old_value} -> {color} (no palette)",
                    "WARNING",
                )

            # Mark only this pixel as dirty for efficient redraw
            self.mark_dirty(x, y)
            self.pixelChanged.emit()
        else:
            debug_log(
                "CANVAS",
                f"Draw pixel out of bounds: ({x},{y}) for {width}x{height} image",
                "WARNING",
            )

    def draw_line(self, x0: int, y0: int, x1: int, y1: int):
        """Draw a line between two points using Bresenham's algorithm"""
        if self.image_data is None:
            return
            
        # Collect all pixels in the line first
        pixels = []
        dx = abs(x1 - x0)
        dy = abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx - dy
        
        x, y = x0, y0
        while True:
            # Only add valid pixels
            height, width = self.image_data.shape
            if 0 <= x < width and 0 <= y < height:
                old_color = self.image_data[y, x]
                pixels.append((x, y, old_color))

            if x == x1 and y == y1:
                break

            e2 = 2 * err
            if e2 > -dy:
                err -= dy
                x += sx
            if e2 < dx:
                err += dx
                y += sy
        
        # Create line command
        color = validate_color_index(self.current_color)
        command = DrawLineCommand(pixels=pixels, new_color=color)
        
        # If we're in a batch (continuous drawing), add to batch
        if self.current_batch is not None:
            self.current_batch.add_command(command)
            # Execute immediately for visual feedback
            command.execute(self)
        else:
            # Single line operation - execute through undo manager
            self.undo_manager.execute_command(command, self)
        
        # Mark affected area as dirty
        if pixels:
            min_x = min(p[0] for p in pixels)
            max_x = max(p[0] for p in pixels)
            min_y = min(p[1] for p in pixels)
            max_y = max(p[1] for p in pixels)
            self.mark_dirty(min_x, min_y, max_x - min_x + 1, max_y - min_y + 1)
        
        self.pixelChanged.emit()

    def flood_fill(self, x: int, y: int):
        """Flood fill from the given point"""
        if self.image_data is None:
            return

        height, width = self.image_data.shape
        if not (0 <= x < width and 0 <= y < height):
            return

        target_color = self.image_data[y, x]
        # Validate and clamp color to 4bpp range (0-15)
        replacement_color = validate_color_index(self.current_color)

        if target_color == replacement_color:
            return

        # First, find the affected region
        # We'll do a preliminary scan to find bounds
        stack = [(x, y)]
        visited = set()
        min_x, max_x = x, x
        min_y, max_y = y, y
        
        # Find bounds of affected area
        while stack:
            cx, cy = stack.pop()
            
            if (cx, cy) in visited:
                continue
            if not (0 <= cx < width and 0 <= cy < height):
                continue
            if self.image_data[cy, cx] != target_color:
                continue
                
            visited.add((cx, cy))
            min_x = min(min_x, cx)
            max_x = max(max_x, cx)
            min_y = min(min_y, cy)
            max_y = max(max_y, cy)
            
            # Add neighboring pixels
            stack.extend([(cx + 1, cy), (cx - 1, cy), (cx, cy + 1), (cx, cy - 1)])
        
        # Create affected region data
        region_width = max_x - min_x + 1
        region_height = max_y - min_y + 1
        old_data = np.full((region_height, region_width), 255, dtype=np.uint8)  # 255 = not affected
        
        # Copy old data for affected pixels
        for py in range(min_y, max_y + 1):
            for px in range(min_x, max_x + 1):
                if (px, py) in visited:
                    old_data[py - min_y, px - min_x] = self.image_data[py, px]
        
        # Create flood fill command
        command = FloodFillCommand(
            affected_region=(min_x, min_y, region_width, region_height),
            old_data=old_data,
            new_color=replacement_color
        )
        
        # Execute through undo manager
        self.undo_manager.execute_command(command, self)

        # Get color info for logging
        color_info = replacement_color
        if self.palette_widget and replacement_color < len(self.palette_widget.colors):
            rgb = self.palette_widget.colors[replacement_color]
            color_info = debug_color(replacement_color, rgb)

        debug_log(
            "CANVAS",
            f"Flood fill: filled {len(visited)} pixels with {color_info} (replaced index {target_color})",
        )
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
                # Update palette version when external palette changes
                if hasattr(self.palette_widget, 'colors_changed'):
                    self._palette_version += 1

            # Get color info for logging
            color_info = picked_color
            if self.palette_widget and picked_color < len(self.palette_widget.colors):
                rgb = self.palette_widget.colors[picked_color]
                color_info = debug_color(picked_color, rgb)

            debug_log("CANVAS", f"Picked {color_info} from pixel ({x},{y})")
    
    def set_greyscale_mode(self, enabled: bool):
        """Toggle greyscale mode"""
        if self.greyscale_mode != enabled:
            self.greyscale_mode = enabled
            self._palette_version += 1  # Force color cache update
            self.update()
            debug_log("CANVAS", f"Greyscale mode changed to: {enabled}")
    
    def get_undo_memory_stats(self) -> dict:
        """Get memory usage statistics for the undo system"""
        return self.undo_manager.get_memory_usage()


class ProgressDialog(QDialog):
    """Progress dialog for long-running operations with cancel support"""
    
    def __init__(self, title: str, message: str, parent=None):
        """Initialize the progress dialog.
        
        Args:
            title: Dialog window title
            message: Progress message to display
            parent: Parent widget
        """
        super().__init__(parent)
        self.cancelled = False
        
        # Dialog settings
        self.setWindowTitle(title)
        self.setModal(True)
        self.setFixedSize(400, 150)
        
        # Remove close button (user must cancel explicitly)
        self.setWindowFlags(
            self.windowFlags() 
            & ~Qt.WindowType.WindowCloseButtonHint
            | Qt.WindowType.WindowStaysOnTopHint
        )
        
        # Layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Message label
        self.message_label = QLabel(message)
        self.message_label.setWordWrap(True)
        layout.addWidget(self.message_label)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        layout.addWidget(self.progress_bar)
        
        # Status label
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("QLabel { color: #666; }")
        layout.addWidget(self.status_label)
        
        # Cancel button
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.on_cancel)
        layout.addWidget(self.cancel_button)
        
        layout.addStretch()
        
    def on_cancel(self):
        """Handle cancel button click"""
        self.cancelled = True
        self.cancel_button.setEnabled(False)
        self.cancel_button.setText("Cancelling...")
        self.status_label.setText("Cancelling operation...")
        
    def update_progress(self, value: int):
        """Update progress bar value.
        
        Args:
            value: Progress percentage (0-100)
        """
        self.progress_bar.setValue(value)
        
    def update_message(self, message: str):
        """Update the main message.
        
        Args:
            message: New message to display
        """
        self.message_label.setText(message)
        
    def update_status(self, status: str):
        """Update the status message.
        
        Args:
            status: Status text to display
        """
        self.status_label.setText(status)
        
    def is_cancelled(self) -> bool:
        """Check if operation was cancelled.
        
        Returns:
            True if user clicked cancel
        """
        return self.cancelled
        
    def finish(self):
        """Mark operation as finished and close dialog"""
        self.accept()
