#!/usr/bin/env python3
"""
Custom PyQt widget for sprite viewing with zoom and grid overlay
"""

from PIL import Image
from PyQt6.QtCore import QRect, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QImage, QMouseEvent, QPainter, QPen, QPixmap
from PyQt6.QtWidgets import QLabel, QScrollArea, QWidget


class SpriteViewerWidget(QScrollArea):
    """Custom widget for viewing sprite images with zoom and grid support"""

    # Signals
    tile_hovered = pyqtSignal(int, int)  # tile_x, tile_y
    pixel_hovered = pyqtSignal(int, int, int)  # x, y, color_index

    def __init__(self, parent=None):
        super().__init__(parent)

        # Internal state
        self._image = None
        self._pixmap = None
        self._zoom_level = 1
        self._show_grid = True
        self._tile_size = 8
        self._hover_tile = None

        # Palette state
        self._current_palette = 0
        self._available_palettes = []
        self._palette_names = {}
        self._show_palette_overlay = False
        self._tile_palette_map = {}  # tile_offset -> palette_num

        # Setup UI
        self._setup_ui()

    def _setup_ui(self):
        """Initialize the UI components"""
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        # Create the display label
        self._display_label = QLabel()
        self._display_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._display_label.setMouseTracking(True)
        self._display_label.mouseMoveEvent = self._on_mouse_move

        self.setWidget(self._display_label)
        self.setStyleSheet("""
            QScrollArea {
                background-color: #2b2b2b;
                border: 1px solid #555;
            }
            QLabel {
                background-color: #2b2b2b;
            }
        """)

    def set_image(self, image):
        """Set the image to display (PIL Image or QPixmap)"""
        if isinstance(image, Image.Image):
            # Convert PIL to QPixmap
            if image.mode == 'P':
                # Handle indexed images
                image_rgb = image.convert('RGBA')
                data = image_rgb.tobytes('raw', 'RGBA')
                qimage = QImage(
                    data,
                    image.width,
                    image.height,
                    QImage.Format.Format_RGBA8888)
            else:
                data = image.tobytes('raw', 'RGB')
                qimage = QImage(
                    data,
                    image.width,
                    image.height,
                    QImage.Format.Format_RGB888)

            self._pixmap = QPixmap.fromImage(qimage)
            self._image = image
        elif isinstance(image, QPixmap):
            self._pixmap = image
            self._image = None
        else:
            return

        self._update_display()

    def set_zoom(self, zoom_level):
        """Set the zoom level (1-16)"""
        self._zoom_level = max(1, min(16, zoom_level))
        self._update_display()

    def zoom_in(self):
        """Increase zoom level"""
        self.set_zoom(self._zoom_level + 1)

    def zoom_out(self):
        """Decrease zoom level"""
        self.set_zoom(self._zoom_level - 1)

    def zoom_fit(self):
        """Fit image to window"""
        if not self._pixmap:
            return

        # Calculate zoom to fit
        viewport_size = self.viewport().size()
        image_size = self._pixmap.size()

        zoom_x = viewport_size.width() / image_size.width()
        zoom_y = viewport_size.height() / image_size.height()

        self.set_zoom(int(min(zoom_x, zoom_y)))

    def set_show_grid(self, show):
        """Toggle grid overlay"""
        self._show_grid = show
        self._update_display()

    def _update_display(self):
        """Update the displayed image with current zoom and overlays"""
        if not self._pixmap:
            return

        # Scale the pixmap
        scaled_pixmap = self._pixmap.scaled(
            self._pixmap.width() * self._zoom_level,
            self._pixmap.height() * self._zoom_level,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.FastTransformation
        )

        # Draw overlays if enabled
        if (self._show_grid and self._zoom_level >=
                2) or self._show_palette_overlay:
            painter = QPainter(scaled_pixmap)

            # Draw palette overlay first (under grid)
            if self._show_palette_overlay:
                self._draw_palette_overlay(
                    painter, scaled_pixmap.width(), scaled_pixmap.height())

            # Draw grid overlay on top
            if self._show_grid and self._zoom_level >= 2:
                self._draw_grid(
                    painter,
                    scaled_pixmap.width(),
                    scaled_pixmap.height())

            painter.end()

        self._display_label.setPixmap(scaled_pixmap)
        self._display_label.adjustSize()

    def _draw_grid(self, painter, width, height):
        """Draw tile grid overlay"""
        pen = QPen(QColor(255, 255, 255, 60))
        pen.setWidth(1)
        painter.setPen(pen)

        # Draw vertical lines
        tile_width = self._tile_size * self._zoom_level
        for x in range(0, width + 1, tile_width):
            painter.drawLine(x, 0, x, height)

        # Draw horizontal lines
        for y in range(0, height + 1, tile_width):
            painter.drawLine(0, y, width, y)

        # Highlight hovered tile
        if self._hover_tile:
            tile_x, tile_y = self._hover_tile
            rect = QRect(
                tile_x * tile_width,
                tile_y * tile_width,
                tile_width,
                tile_width
            )

            highlight_pen = QPen(QColor(255, 255, 0, 100))
            highlight_pen.setWidth(2)
            painter.setPen(highlight_pen)
            painter.fillRect(rect, QColor(255, 255, 0, 30))
            painter.drawRect(rect)

    def _on_mouse_move(self, event: QMouseEvent):
        """Handle mouse movement for tile/pixel info"""
        if not self._pixmap:
            return

        # Get position relative to image
        x = event.position().x() // self._zoom_level
        y = event.position().y() // self._zoom_level

        # Check bounds
        if x < 0 or y < 0 or x >= self._pixmap.width() or y >= self._pixmap.height():
            self._hover_tile = None
            return

        # Calculate tile position
        tile_x = int(x // self._tile_size)
        tile_y = int(y // self._tile_size)

        # Update hover tile
        if self._hover_tile != (tile_x, tile_y):
            self._hover_tile = (tile_x, tile_y)
            self._update_display()
            self.tile_hovered.emit(tile_x, tile_y)

        # Get pixel color if we have the original indexed image
        if self._image and self._image.mode == 'P':
            try:
                pixel_value = self._image.getpixel((int(x), int(y)))
                self.pixel_hovered.emit(int(x), int(y), pixel_value)
            except (IndexError, AttributeError):
                pass

    def get_current_zoom(self):
        """Get current zoom level"""
        return self._zoom_level

    def get_image_info(self):
        """Get information about current image"""
        if not self._pixmap:
            return None

        info = {
            'width': self._pixmap.width(),
            'height': self._pixmap.height(),
            'tiles_x': self._pixmap.width() // self._tile_size,
            'tiles_y': self._pixmap.height() // self._tile_size,
            'total_tiles': (self._pixmap.width() // self._tile_size) * (self._pixmap.height() // self._tile_size)
        }

        if self._image:
            info['mode'] = self._image.mode
            if self._image.mode == 'P':
                info['colors'] = len(set(self._image.getdata()))

        return info

    def set_available_palettes(self, palettes, names=None):
        """Set available palettes for switching

        Args:
            palettes: list of palette data arrays
            names: optional dict of palette_num -> name
        """
        self._available_palettes = palettes
        self._palette_names = names or {}

    def set_current_palette(self, palette_num):
        """Switch to a specific palette"""
        if 0 <= palette_num < len(self._available_palettes):
            self._current_palette = palette_num

            # Apply new palette to image if it's indexed
            if self._image and self._image.mode == 'P':
                self._image.putpalette(self._available_palettes[palette_num])
                self.set_image(self._image)  # Refresh display

    def set_tile_palette_map(self, tile_palette_map):
        """Set mapping of tile positions to palette numbers

        Args:
            tile_palette_map: dict of (tile_x, tile_y) -> palette_num
        """
        self._tile_palette_map = tile_palette_map
        self._update_display()

    def set_show_palette_overlay(self, show):
        """Toggle palette assignment overlay"""
        self._show_palette_overlay = show
        self._update_display()

    def get_current_palette(self):
        """Get current palette number"""
        return self._current_palette

    def get_palette_for_tile(self, tile_x, tile_y):
        """Get palette number for a specific tile"""
        return self._tile_palette_map.get((tile_x, tile_y), None)

    def _draw_palette_overlay(self, painter, width, height):
        """Draw overlay showing palette assignments"""
        if not self._tile_palette_map or not self._show_palette_overlay:
            return

        tile_width = self._tile_size * self._zoom_level

        # Define colors for each palette
        palette_colors = [
            QColor(255, 0, 0, 60),      # Palette 0 - Red
            QColor(0, 255, 0, 60),      # Palette 1 - Green
            QColor(0, 0, 255, 60),      # Palette 2 - Blue
            QColor(255, 255, 0, 60),    # Palette 3 - Yellow
            QColor(255, 0, 255, 60),    # Palette 4 - Magenta
            QColor(0, 255, 255, 60),    # Palette 5 - Cyan
            QColor(255, 128, 0, 60),    # Palette 6 - Orange
            QColor(128, 0, 255, 60),    # Palette 7 - Purple
        ]

        # Draw colored overlay for each tile
        for (tile_x, tile_y), palette_num in self._tile_palette_map.items():
            if palette_num < len(palette_colors):
                rect = QRect(
                    tile_x * tile_width,
                    tile_y * tile_width,
                    tile_width,
                    tile_width
                )

                painter.fillRect(rect, palette_colors[palette_num])

                # Draw palette number if zoom is high enough
                if self._zoom_level >= 4:
                    painter.setPen(QPen(Qt.GlobalColor.white))
                    painter.drawText(rect.center(), str(palette_num))


class PaletteViewerWidget(QWidget):
    """Widget for displaying color palette"""

    color_clicked = pyqtSignal(int)  # color index

    def __init__(self, parent=None):
        super().__init__(parent)

        self._palette = None
        self._selected_index = None
        self.setFixedHeight(40)
        self.setMinimumWidth(320)

    def set_palette(self, palette):
        """Set the palette to display (list of RGB values)"""
        self._palette = palette
        self.update()

    def paintEvent(self, event):
        """Draw the palette"""
        if not self._palette:
            return

        painter = QPainter(self)

        # Calculate color box size
        num_colors = min(16, len(self._palette) // 3)
        box_width = self.width() // num_colors
        box_height = self.height()

        # Draw each color
        for i in range(num_colors):
            r = self._palette[i * 3]
            g = self._palette[i * 3 + 1]
            b = self._palette[i * 3 + 2]

            color = QColor(r, g, b)
            rect = QRect(i * box_width, 0, box_width, box_height)

            painter.fillRect(rect, color)

            # Draw border
            painter.setPen(QPen(Qt.GlobalColor.black, 1))
            painter.drawRect(rect)

            # Highlight selected
            if i == self._selected_index:
                painter.setPen(QPen(Qt.GlobalColor.yellow, 3))
                painter.drawRect(rect.adjusted(1, 1, -1, -1))

    def mousePressEvent(self, event):
        """Handle color selection"""
        if not self._palette or event.button() != Qt.MouseButton.LeftButton:
            return

        num_colors = min(16, len(self._palette) // 3)
        box_width = self.width() // num_colors

        index = int(event.position().x() // box_width)
        if 0 <= index < num_colors:
            self._selected_index = index
            self.color_clicked.emit(index)
            self.update()
