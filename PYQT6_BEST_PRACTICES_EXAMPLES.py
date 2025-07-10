#!/usr/bin/env python3
"""
PyQt6 Best Practices Examples
Demonstrates proper patterns for the issues found in the code review
"""

import sys
from functools import partial
from typing import Optional

import numpy as np
from PIL import Image
from PyQt6.QtCore import (
    QObject,
    QPoint,
    QRect,
    QThread,
    Qt,
    pyqtSignal,
    QTimer,
    QEvent,
)
from PyQt6.QtGui import (
    QImage,
    QPainter,
    QPixmap,
    QWheelEvent,
    QMouseEvent,
    QPaintEvent,
)
from PyQt6.QtWidgets import QApplication, QLabel, QWidget


# 1. PROPER WORKER THREAD FOR FILE OPERATIONS
class FileLoadWorker(QThread):
    """Proper worker thread for async file loading"""
    
    # Signals for communication
    progress = pyqtSignal(int)  # Progress percentage
    finished = pyqtSignal(Image.Image)  # Loaded image
    error = pyqtSignal(str)  # Error message
    
    def __init__(self, file_path: str):
        super().__init__()
        self.file_path = file_path
    
    def run(self):
        """Run in separate thread"""
        try:
            self.progress.emit(0)
            
            # Simulate loading stages
            img = Image.open(self.file_path)
            self.progress.emit(50)
            
            # Validate image
            if img.mode != "P":
                img = img.convert("P")
            self.progress.emit(100)
            
            self.finished.emit(img)
        except Exception as e:
            self.error.emit(str(e))


# 2. PROPER EVENT FILTER FOR ZOOM HANDLING
class ZoomEventFilter(QObject):
    """Proper event filter for wheel zoom"""
    
    zoom_changed = pyqtSignal(int)  # New zoom level
    
    def __init__(self, zoom_levels=None):
        super().__init__()
        self.zoom_levels = zoom_levels or [1, 2, 4, 8, 16, 32, 64]
        self.current_zoom = 4
    
    def eventFilter(self, obj: QObject, event: QEvent) -> bool:
        """Filter wheel events for zooming"""
        if event.type() == QEvent.Type.Wheel:
            wheel_event = event
            
            # Only zoom if no modifiers (Ctrl+Wheel = scroll)
            if wheel_event.modifiers() == Qt.KeyboardModifier.NoModifier:
                delta = wheel_event.angleDelta().y()
                
                # Find current index
                try:
                    current_idx = self.zoom_levels.index(self.current_zoom)
                except ValueError:
                    current_idx = 2  # Default to 4x
                
                # Calculate new zoom
                if delta > 0:
                    new_idx = min(current_idx + 1, len(self.zoom_levels) - 1)
                else:
                    new_idx = max(current_idx - 1, 0)
                
                new_zoom = self.zoom_levels[new_idx]
                if new_zoom != self.current_zoom:
                    self.current_zoom = new_zoom
                    self.zoom_changed.emit(new_zoom)
                
                return True  # Event handled
        
        return super().eventFilter(obj, event)


# 3. PROPER CUSTOM WIDGET WITH EVENT HANDLING
class ProperPixelCanvas(QWidget):
    """Canvas with proper event handling and caching"""
    
    pixel_changed = pyqtSignal(int, int, int)  # x, y, color
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.image_data = None
        self.zoom = 4
        self._cached_pixmap = None
        self._cache_valid = False
        
        # Batch update timer
        self._update_timer = QTimer()
        self._update_timer.timeout.connect(self._perform_update)
        self._update_timer.setSingleShot(True)
        self._update_regions = []
        
        self.setMouseTracking(True)
    
    def set_image_data(self, data: np.ndarray):
        """Set image data and invalidate cache"""
        self.image_data = data
        self._cache_valid = False
        self.update()
    
    def draw_pixel(self, x: int, y: int, color: int):
        """Draw pixel with batched updates"""
        if self.image_data is None:
            return
        
        h, w = self.image_data.shape
        if 0 <= x < w and 0 <= y < h:
            self.image_data[y, x] = color
            
            # Add to update regions
            pixel_rect = QRect(x * self.zoom, y * self.zoom, self.zoom, self.zoom)
            self._update_regions.append(pixel_rect)
            
            # Start/restart timer for batched update
            if not self._update_timer.isActive():
                self._update_timer.start(16)  # ~60 FPS
            
            self.pixel_changed.emit(x, y, color)
    
    def _perform_update(self):
        """Perform batched update"""
        if self._update_regions:
            # Combine regions into bounding rect
            combined = self._update_regions[0]
            for rect in self._update_regions[1:]:
                combined = combined.united(rect)
            
            self._update_regions.clear()
            self._cache_valid = False
            self.update(combined)  # Update only affected region
    
    def _update_cache(self):
        """Update cached pixmap"""
        if self.image_data is None:
            return
        
        h, w = self.image_data.shape
        
        # Create QImage from numpy array efficiently
        qimage = QImage(w, h, QImage.Format.Format_Indexed8)
        
        # Set color table (palette)
        for i in range(16):
            gray = (i * 255) // 15
            qimage.setColor(i, (0xFF << 24) | (gray << 16) | (gray << 8) | gray)
        
        # Copy data efficiently
        ptr = qimage.bits()
        ptr.setsize(h * w)
        np.frombuffer(ptr, dtype=np.uint8).reshape(h, w)[:] = self.image_data
        
        # Scale once and cache
        self._cached_pixmap = QPixmap.fromImage(qimage).scaled(
            w * self.zoom, h * self.zoom,
            Qt.AspectRatioMode.IgnoreAspectRatio,
            Qt.TransformationMode.FastTransformation
        )
        self._cache_valid = True
    
    def paintEvent(self, event: QPaintEvent):
        """Efficient paint event with caching"""
        if self.image_data is None:
            return
        
        # Update cache if needed
        if not self._cache_valid:
            self._update_cache()
        
        # Use context manager for painter
        with QPainter(self) as painter:
            # Only paint the requested region
            painter.setClipRegion(event.region())
            
            if self._cached_pixmap:
                painter.drawPixmap(0, 0, self._cached_pixmap)
    
    def mouseMoveEvent(self, event: QMouseEvent):
        """Proper mouse event handling"""
        # Your mouse handling code here
        super().mouseMoveEvent(event)  # Don't forget to call parent!
    
    def wheelEvent(self, event: QWheelEvent):
        """Proper wheel event handling"""
        # Let it propagate up - event filter will handle it
        event.ignore()


# 4. PROPER SIGNAL CONNECTIONS WITHOUT LAMBDAS IN LOOPS
class ProperButtonConnections(QWidget):
    """Demonstrates proper signal connections"""
    
    def __init__(self):
        super().__init__()
        self.zoom_buttons = []
        
    def create_zoom_buttons(self, zoom_presets):
        """Create buttons with proper connections"""
        for label, value in zoom_presets:
            btn = QPushButton(label)
            # Use functools.partial instead of lambda
            btn.clicked.connect(partial(self.set_zoom_preset, value))
            # Or store value as property
            btn.setProperty("zoom_value", value)
            btn.clicked.connect(self.on_zoom_button_clicked)
            self.zoom_buttons.append(btn)
    
    def on_zoom_button_clicked(self):
        """Handle zoom button click"""
        sender = self.sender()
        if sender:
            zoom_value = sender.property("zoom_value")
            if zoom_value:
                self.set_zoom_preset(zoom_value)
    
    def set_zoom_preset(self, value):
        """Set zoom to preset value"""
        print(f"Setting zoom to {value}")


# 5. PROPER IMAGE CONVERSION WITH CACHING
class ImageCache:
    """Efficient image conversion and caching"""
    
    def __init__(self):
        self._cache = {}  # (image_id, format) -> QPixmap
    
    def get_qpixmap(self, pil_image: Image.Image, image_id: str = None) -> QPixmap:
        """Get QPixmap with caching"""
        if image_id is None:
            image_id = id(pil_image)
        
        cache_key = (image_id, pil_image.mode)
        
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        # Convert efficiently based on mode
        if pil_image.mode == "P":
            # Indexed mode - preserve palette
            image_rgb = pil_image.convert("RGBA")
            data = image_rgb.tobytes("raw", "RGBA")
            qimage = QImage(
                data, 
                pil_image.width, 
                pil_image.height, 
                QImage.Format.Format_RGBA8888
            )
        elif pil_image.mode == "RGBA":
            data = pil_image.tobytes("raw", "RGBA")
            qimage = QImage(
                data,
                pil_image.width,
                pil_image.height,
                QImage.Format.Format_RGBA8888
            )
        else:
            # Convert to RGB for other modes
            image_rgb = pil_image.convert("RGB")
            data = image_rgb.tobytes("raw", "RGB")
            qimage = QImage(
                data,
                image_rgb.width,
                image_rgb.height,
                QImage.Format.Format_RGB888
            )
        
        pixmap = QPixmap.fromImage(qimage)
        self._cache[cache_key] = pixmap
        
        return pixmap
    
    def clear_cache(self):
        """Clear the cache"""
        self._cache.clear()


# 6. PROPER CUSTOM LABEL WITH EVENT HANDLING
class ProperCustomLabel(QLabel):
    """Proper way to extend QLabel with custom events"""
    
    tile_hovered = pyqtSignal(int, int)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMouseTracking(True)
    
    def mouseMoveEvent(self, event: QMouseEvent):
        """Override mouse move properly"""
        # Calculate tile position
        tile_x = int(event.position().x() // 8)
        tile_y = int(event.position().y() // 8)
        
        self.tile_hovered.emit(tile_x, tile_y)
        
        # Always call parent implementation!
        super().mouseMoveEvent(event)


def main():
    """Demo application"""
    app = QApplication(sys.argv)
    
    # Example usage
    widget = ProperPixelCanvas()
    widget.show()
    
    # Install event filter
    zoom_filter = ZoomEventFilter()
    widget.installEventFilter(zoom_filter)
    zoom_filter.zoom_changed.connect(lambda z: print(f"Zoom changed to {z}"))
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()