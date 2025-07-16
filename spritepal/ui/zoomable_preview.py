"""
Zoomable sprite preview widget for SpritePal
"""

from PyQt6.QtCore import QPointF, QRectF, QSize, Qt
from PyQt6.QtGui import (
    QColor,
    QKeyEvent,
    QMouseEvent,
    QPainter,
    QPen,
    QPixmap,
    QTransform,
    QWheelEvent,
)
from PyQt6.QtWidgets import QCheckBox, QComboBox, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget


class ZoomablePreviewWidget(QWidget):
    """Widget for previewing sprites with zoom and pan functionality"""

    def __init__(self):
        super().__init__()
        self._pixmap = None
        self._tile_count = 0
        self._tiles_per_row = 0

        # Zoom and pan state
        self._zoom = 1.0
        self._min_zoom = 0.1
        self._max_zoom = 20.0
        self._pan_offset = QPointF(0, 0)
        self._last_mouse_pos = None
        self._is_panning = False
        self._grid_visible = True

        self.setMinimumSize(QSize(256, 256))
        self.setMouseTracking(True)
        self.setCursor(Qt.CursorShape.CrossCursor)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setStyleSheet("""
            ZoomablePreviewWidget {
                background-color: #1e1e1e;
                border: 1px solid #555;
            }
        """)

    def paintEvent(self, event):  # noqa: N802
        """Paint the preview with zoom and pan"""
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(30, 30, 30))

        if self._pixmap:
            painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

            # Apply transformations
            transform = QTransform()

            # Center the image
            center_x = self.width() / 2
            center_y = self.height() / 2

            # Apply pan and zoom around center
            transform.translate(center_x + self._pan_offset.x(),
                              center_y + self._pan_offset.y())
            transform.scale(self._zoom, self._zoom)
            transform.translate(-self._pixmap.width() / 2,
                              -self._pixmap.height() / 2)

            painter.setTransform(transform)
            
            # Draw checkerboard background for transparency visibility
            self._draw_checkerboard(painter, transform)
            
            painter.drawPixmap(0, 0, self._pixmap)

            # Reset transform for UI elements
            painter.resetTransform()

            # Draw zoom level indicator
            painter.setPen(QPen(QColor(200, 200, 200), 1))
            painter.setFont(painter.font())
            zoom_text = f"Zoom: {self._zoom:.1f}x"
            painter.drawText(10, 20, zoom_text)

            # Draw grid if zoomed in enough and grid is visible
            if self._zoom > 4.0 and self._grid_visible:
                self._draw_pixel_grid(painter, transform)

        else:
            # Draw placeholder
            painter.setPen(QPen(QColor(100, 100, 100), 2))
            painter.drawText(
                self.rect(),
                Qt.AlignmentFlag.AlignCenter,
                "Sprite preview will appear here"
            )

    def _draw_checkerboard(self, painter, transform):
        """Draw a checkerboard background for transparency visibility"""
        if not self._pixmap:
            return

        # Create inverse transform to get visible area in image coordinates
        inv_transform, _ = transform.inverted()

        # Get visible rectangle in image coordinates
        visible_rect = inv_transform.mapRect(QRectF(self.rect()))

        # Limit drawing to visible area
        left = max(0, int(visible_rect.left()))
        right = min(self._pixmap.width(), int(visible_rect.right()) + 1)
        top = max(0, int(visible_rect.top()))
        bottom = min(self._pixmap.height(), int(visible_rect.bottom()) + 1)

        # Draw checkerboard pattern
        tile_size = max(1, int(8 / self._zoom))  # Adjust tile size based on zoom
        
        for y in range(top, bottom, tile_size):
            for x in range(left, right, tile_size):
                # Alternate colors
                if (x // tile_size + y // tile_size) % 2 == 0:
                    painter.fillRect(x, y, tile_size, tile_size, QColor(180, 180, 180))
                else:
                    painter.fillRect(x, y, tile_size, tile_size, QColor(120, 120, 120))

    def _draw_pixel_grid(self, painter, transform):
        """Draw a pixel grid when zoomed in"""
        if not self._pixmap:
            return

        # Create inverse transform to get visible area in image coordinates
        inv_transform, _ = transform.inverted()

        # Get visible rectangle in image coordinates
        visible_rect = inv_transform.mapRect(QRectF(self.rect()))

        # Limit grid drawing to visible area
        left = max(0, int(visible_rect.left()))
        right = min(self._pixmap.width(), int(visible_rect.right()) + 1)
        top = max(0, int(visible_rect.top()))
        bottom = min(self._pixmap.height(), int(visible_rect.bottom()) + 1)

        # Draw grid
        painter.setPen(QPen(QColor(60, 60, 60), 0.5))

        # Vertical lines
        for x in range(left, right + 1):
            p1 = transform.map(QPointF(x, top))
            p2 = transform.map(QPointF(x, bottom))
            painter.drawLine(p1, p2)

        # Horizontal lines
        for y in range(top, bottom + 1):
            p1 = transform.map(QPointF(left, y))
            p2 = transform.map(QPointF(right, y))
            painter.drawLine(p1, p2)

    def wheelEvent(self, event: QWheelEvent):  # noqa: N802
        """Handle mouse wheel for zooming"""
        if not self._pixmap:
            return

        # Get mouse position in widget coordinates
        mouse_pos = event.position()

        # Calculate zoom factor
        zoom_factor = 1.1 if event.angleDelta().y() > 0 else 0.9
        new_zoom = self._zoom * zoom_factor

        # Clamp zoom
        new_zoom = max(self._min_zoom, min(self._max_zoom, new_zoom))

        if new_zoom != self._zoom:
            # Calculate mouse position in image space before zoom
            center_x = self.width() / 2
            center_y = self.height() / 2

            # Mouse position relative to center
            mouse_rel_x = mouse_pos.x() - center_x - self._pan_offset.x()
            mouse_rel_y = mouse_pos.y() - center_y - self._pan_offset.y()

            # Scale the relative position
            scale_ratio = new_zoom / self._zoom

            # Adjust pan to keep mouse position fixed
            self._pan_offset.setX(
                self._pan_offset.x() + mouse_rel_x * (1 - scale_ratio)
            )
            self._pan_offset.setY(
                self._pan_offset.y() + mouse_rel_y * (1 - scale_ratio)
            )

            self._zoom = new_zoom
            self.update()

    def mousePressEvent(self, event: QMouseEvent):  # noqa: N802
        """Handle mouse press for panning"""
        if event.button() in (Qt.MouseButton.LeftButton, Qt.MouseButton.MiddleButton):
            self._is_panning = True
            self._last_mouse_pos = event.position()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
        elif event.button() == Qt.MouseButton.RightButton:
            # Right click to reset view
            self.reset_view()

    def mouseReleaseEvent(self, event: QMouseEvent):  # noqa: N802
        """Handle mouse release"""
        if event.button() in (Qt.MouseButton.LeftButton, Qt.MouseButton.MiddleButton):
            self._is_panning = False
            self.setCursor(Qt.CursorShape.CrossCursor)

    def mouseMoveEvent(self, event: QMouseEvent):  # noqa: N802
        """Handle mouse move for panning"""
        if self._is_panning and self._last_mouse_pos:
            delta = event.position() - self._last_mouse_pos
            self._pan_offset += delta
            self._last_mouse_pos = event.position()
            self.update()

    def keyPressEvent(self, event):  # noqa: N802
        """Handle keyboard input"""
        if event.key() == Qt.Key.Key_G:
            self._grid_visible = not self._grid_visible
            self.update()
        else:
            super().keyPressEvent(event)

    def set_preview(self, pixmap, tile_count=0, tiles_per_row=0):
        """Set the preview pixmap"""
        self._pixmap = pixmap
        self._tile_count = tile_count
        self._tiles_per_row = tiles_per_row
        self.reset_view()

    def set_preview_from_file(self, file_path):
        """Load preview from file"""
        pixmap = QPixmap(file_path)
        if not pixmap.isNull():
            self.set_preview(pixmap)

    def clear(self):
        """Clear the preview"""
        self._pixmap = None
        self._tile_count = 0
        self._tiles_per_row = 0
        self._zoom = 1.0
        self._pan_offset = QPointF(0, 0)
        self.update()

    def get_tile_info(self):
        """Get tile information"""
        return self._tile_count, self._tiles_per_row

    def reset_view(self):
        """Reset zoom and pan to default"""
        self._zoom = 1.0
        self._pan_offset = QPointF(0, 0)
        self.update()

    def zoom_to_fit(self):
        """Zoom to fit the image in the widget"""
        if not self._pixmap:
            return

        # Calculate scale to fit
        scale_x = self.width() / self._pixmap.width()
        scale_y = self.height() / self._pixmap.height()
        self._zoom = min(scale_x, scale_y) * 0.9  # 90% to leave some margin
        self._pan_offset = QPointF(0, 0)
        self.update()


class PreviewPanel(QWidget):
    """Panel containing the zoomable preview with controls"""

    def __init__(self):
        super().__init__()
        self._grayscale_image = None
        self._colorized_image = None
        self._current_palettes = {}
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self._init_ui()

    def _init_ui(self):
        """Initialize the UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Preview widget
        self.preview = ZoomablePreviewWidget()
        layout.addWidget(self.preview)

        # Control buttons
        controls = QHBoxLayout()
        controls.setContentsMargins(5, 5, 5, 5)

        # Palette application controls
        self.palette_toggle = QCheckBox("Apply Palette")
        self.palette_toggle.setChecked(False)
        self.palette_toggle.toggled.connect(self._on_palette_toggle)
        
        self.palette_selector = QComboBox()
        self.palette_selector.setMinimumWidth(80)
        self.palette_selector.setEnabled(False)
        self.palette_selector.currentTextChanged.connect(self._on_palette_changed)
        
        # Populate palette selector
        for i in range(8, 16):
            self.palette_selector.addItem(f"Palette {i}", i)

        # Zoom controls
        self.zoom_fit_btn = QPushButton("Fit")
        self.zoom_fit_btn.clicked.connect(self.preview.zoom_to_fit)
        self.zoom_fit_btn.setMaximumWidth(60)

        self.zoom_reset_btn = QPushButton("1:1")
        self.zoom_reset_btn.clicked.connect(self.preview.reset_view)
        self.zoom_reset_btn.setMaximumWidth(60)

        # Help text
        help_label = QLabel("Scroll: Zoom | Drag/MMB: Pan | Right-click: Reset | G: Toggle Grid | C: Toggle Palette")
        help_label.setStyleSheet("color: #888; font-size: 10px;")

        controls.addWidget(self.palette_toggle)
        controls.addWidget(self.palette_selector)
        controls.addWidget(QLabel("|"))  # Separator
        controls.addWidget(self.zoom_fit_btn)
        controls.addWidget(self.zoom_reset_btn)
        controls.addWidget(help_label)
        controls.addStretch()

        layout.addLayout(controls)

    def _on_palette_toggle(self, checked):
        """Handle palette toggle"""
        self.palette_selector.setEnabled(checked)
        if checked and self._grayscale_image and self._current_palettes:
            self._apply_current_palette()
        else:
            self._show_grayscale()

    def _on_palette_changed(self, palette_name):
        """Handle palette selection change"""
        if self.palette_toggle.isChecked() and self._grayscale_image and self._current_palettes:
            self._apply_current_palette()

    def _apply_current_palette(self):
        """Apply the currently selected palette to the grayscale image"""
        if not self._grayscale_image or not self._current_palettes:
            return
        
        # Get selected palette index
        palette_index = self.palette_selector.currentData()
        if palette_index not in self._current_palettes:
            return
        
        # Apply palette to create colorized version
        self._colorized_image = self._apply_palette_to_image(
            self._grayscale_image, 
            self._current_palettes[palette_index]
        )
        
        # Update preview with colorized image
        if self._colorized_image:
            pixmap = self._pil_to_pixmap(self._colorized_image)
            self.preview.set_preview(pixmap, self.preview._tile_count, self.preview._tiles_per_row)

    def _show_grayscale(self):
        """Show the grayscale version of the image"""
        if self._grayscale_image:
            # Convert grayscale to RGBA for transparency
            rgba_image = self._grayscale_image.convert('RGBA')
            pixels = rgba_image.load()
            width, height = rgba_image.size
            
            # Make palette index 0 transparent
            for y in range(height):
                for x in range(width):
                    pixel_value = self._grayscale_image.getpixel((x, y))
                    # For palette mode images, pixel value is already the palette index
                    if self._grayscale_image.mode == 'P':
                        palette_index = pixel_value
                    else:
                        # For grayscale images, map to palette index
                        palette_index = min(15, pixel_value // 16)
                    
                    if palette_index == 0:
                        # Set transparent pixel
                        pixels[x, y] = (0, 0, 0, 0)
                    else:
                        # Keep grayscale value with full alpha
                        gray_value = pixel_value if self._grayscale_image.mode != 'P' else (pixel_value * 255) // 15
                        pixels[x, y] = (gray_value, gray_value, gray_value, 255)
            
            pixmap = self._pil_to_pixmap(rgba_image)
            self.preview.set_preview(pixmap, self.preview._tile_count, self.preview._tiles_per_row)

    def set_preview(self, pixmap, tile_count=0, tiles_per_row=0):
        """Set the preview pixmap"""
        self.preview.set_preview(pixmap, tile_count, tiles_per_row)

    def set_preview_from_file(self, file_path):
        """Load preview from file"""
        self.preview.set_preview_from_file(file_path)

    def clear(self):
        """Clear the preview"""
        self._grayscale_image = None
        self._colorized_image = None
        self._current_palettes = {}
        self.palette_toggle.setChecked(False)
        self.palette_selector.setEnabled(False)
        self.preview.clear()

    def set_grayscale_image(self, pil_image):
        """Set the grayscale PIL image for palette application"""
        self._grayscale_image = pil_image

    def set_palettes(self, palettes_dict):
        """Set the available palettes"""
        self._current_palettes = palettes_dict
        
        # Enable palette controls if we have both image and palettes
        has_data = self._grayscale_image is not None and bool(self._current_palettes)
        self.palette_toggle.setEnabled(has_data)
        
        if self.palette_toggle.isChecked() and has_data:
            self._apply_current_palette()

    def _apply_palette_to_image(self, grayscale_image, palette_colors):
        """Apply a palette to a grayscale image"""
        if not grayscale_image or not palette_colors:
            return None
        
        try:
            # Convert grayscale to RGBA for transparency support
            rgba_image = grayscale_image.convert('RGBA')
            
            # Get image data
            pixels = rgba_image.load()
            width, height = rgba_image.size
            
            # Apply palette
            for y in range(height):
                for x in range(width):
                    # Get pixel value
                    pixel_value = grayscale_image.getpixel((x, y))
                    
                    # For palette mode images, pixel value is already the palette index
                    if grayscale_image.mode == 'P':
                        palette_index = pixel_value
                    else:
                        # For grayscale images, map to palette index
                        palette_index = min(15, pixel_value // 16)
                    
                    # Handle transparency for palette index 0
                    if palette_index == 0:
                        # Set transparent pixel
                        pixels[x, y] = (0, 0, 0, 0)
                    elif palette_index < len(palette_colors):
                        # Get RGB color from palette
                        r, g, b = palette_colors[palette_index]
                        pixels[x, y] = (r, g, b, 255)
                    else:
                        # Use black for out of range indices
                        pixels[x, y] = (0, 0, 0, 255)
            
            return rgba_image
            
        except Exception as e:
            print(f"Error applying palette: {e}")
            return None

    def _pil_to_pixmap(self, pil_image):
        """Convert PIL image to QPixmap"""
        if not pil_image:
            return None
        
        try:
            import io
            # Save to bytes
            buffer = io.BytesIO()
            pil_image.save(buffer, format="PNG")
            buffer.seek(0)
            
            # Create QPixmap
            pixmap = QPixmap()
            pixmap.loadFromData(buffer.read())
            return pixmap
        except Exception as e:
            print(f"Error converting PIL to QPixmap: {e}")
            return None

    def keyPressEvent(self, event):  # noqa: N802
        """Handle keyboard input"""
        if event.key() == Qt.Key.Key_C:
            # Toggle palette application
            self.palette_toggle.setChecked(not self.palette_toggle.isChecked())
        else:
            super().keyPressEvent(event)

    def mousePressEvent(self, event):  # noqa: N802
        """Handle mouse press to ensure focus"""
        self.setFocus()
        super().mousePressEvent(event)
