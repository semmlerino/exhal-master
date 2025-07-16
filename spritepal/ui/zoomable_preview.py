"""
Zoomable sprite preview widget for SpritePal
"""

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel
from PyQt6.QtCore import Qt, QSize, QPointF, QRectF, QPoint
from PyQt6.QtGui import QPixmap, QPainter, QColor, QPen, QWheelEvent, QMouseEvent, QTransform


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
        
        self.setMinimumSize(QSize(256, 256))
        self.setMouseTracking(True)
        self.setCursor(Qt.CursorShape.CrossCursor)
        self.setStyleSheet("""
            ZoomablePreviewWidget {
                background-color: #1e1e1e;
                border: 1px solid #555;
            }
        """)
        
    def paintEvent(self, event):
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
            painter.drawPixmap(0, 0, self._pixmap)
            
            # Reset transform for UI elements
            painter.resetTransform()
            
            # Draw zoom level indicator
            painter.setPen(QPen(QColor(200, 200, 200), 1))
            painter.setFont(painter.font())
            zoom_text = f"Zoom: {self._zoom:.1f}x"
            painter.drawText(10, 20, zoom_text)
            
            # Draw grid if zoomed in enough
            if self._zoom > 4.0:
                self._draw_pixel_grid(painter, transform)
                
        else:
            # Draw placeholder
            painter.setPen(QPen(QColor(100, 100, 100), 2))
            painter.drawText(
                self.rect(),
                Qt.AlignmentFlag.AlignCenter,
                "Sprite preview will appear here"
            )
    
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
    
    def wheelEvent(self, event: QWheelEvent):
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
    
    def mousePressEvent(self, event: QMouseEvent):
        """Handle mouse press for panning"""
        if event.button() == Qt.MouseButton.LeftButton:
            self._is_panning = True
            self._last_mouse_pos = event.position()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
        elif event.button() == Qt.MouseButton.RightButton:
            # Right click to reset view
            self.reset_view()
    
    def mouseReleaseEvent(self, event: QMouseEvent):
        """Handle mouse release"""
        if event.button() == Qt.MouseButton.LeftButton:
            self._is_panning = False
            self.setCursor(Qt.CursorShape.CrossCursor)
    
    def mouseMoveEvent(self, event: QMouseEvent):
        """Handle mouse move for panning"""
        if self._is_panning and self._last_mouse_pos:
            delta = event.position() - self._last_mouse_pos
            self._pan_offset += delta
            self._last_mouse_pos = event.position()
            self.update()
    
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
        
        # Zoom controls
        self.zoom_fit_btn = QPushButton("Fit")
        self.zoom_fit_btn.clicked.connect(self.preview.zoom_to_fit)
        self.zoom_fit_btn.setMaximumWidth(60)
        
        self.zoom_reset_btn = QPushButton("1:1")
        self.zoom_reset_btn.clicked.connect(self.preview.reset_view)
        self.zoom_reset_btn.setMaximumWidth(60)
        
        # Help text
        help_label = QLabel("Scroll: Zoom | Drag: Pan | Right-click: Reset")
        help_label.setStyleSheet("color: #888; font-size: 10px;")
        
        controls.addWidget(self.zoom_fit_btn)
        controls.addWidget(self.zoom_reset_btn)
        controls.addWidget(help_label)
        controls.addStretch()
        
        layout.addLayout(controls)
        
    def set_preview(self, pixmap, tile_count=0, tiles_per_row=0):
        """Set the preview pixmap"""
        self.preview.set_preview(pixmap, tile_count, tiles_per_row)
        
    def set_preview_from_file(self, file_path):
        """Load preview from file"""
        self.preview.set_preview_from_file(file_path)
        
    def clear(self):
        """Clear the preview"""
        self.preview.clear()