#!/usr/bin/env python3
"""
Test script for virtual scrolling sprite gallery implementation.
Creates a test application with many sprites to verify performance.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPixmap, QColor, QPainter, QFont
from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton, QLabel

from ui.widgets.sprite_gallery_widget import SpriteGalleryWidget
from utils.logging_config import setup_logging, get_logger

setup_logging()
logger = get_logger(__name__)


def create_test_sprite_data(count: int = 1000) -> list[dict]:
    """Create test sprite data for testing."""
    sprites = []
    for i in range(count):
        offset = 0x200000 + (i * 0x800)
        sprites.append({
            'offset': offset,
            'size': 1024 + (i * 10),
            'decompressed_size': 2048 + (i * 20),
            'compressed': i % 3 == 0,  # Every third sprite is compressed
            'tile_count': 8 + (i % 32),
            'width': 128,
            'height': 128,
            'name': f"Sprite_{i:04d}"
        })
    return sprites


def create_test_thumbnail(offset: int) -> QPixmap:
    """Create a test thumbnail for a sprite."""
    pixmap = QPixmap(128, 128)
    pixmap.fill(QColor(50, 50, 50))
    
    painter = QPainter(pixmap)
    
    # Draw a gradient based on offset
    gradient_color = QColor.fromHsv((offset // 0x1000) % 360, 200, 150)
    painter.fillRect(10, 10, 108, 108, gradient_color)
    
    # Draw offset text
    painter.setPen(Qt.GlobalColor.white)
    painter.setFont(QFont("Arial", 10, QFont.Weight.Bold))
    painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, f"0x{offset:06X}")
    
    painter.end()
    
    return pixmap


class TestWindow(QMainWindow):
    """Test window for virtual scrolling gallery."""
    
    def __init__(self):
        super().__init__()
        
        self.setWindowTitle("Virtual Scrolling Gallery Test")
        self.setGeometry(100, 100, 1200, 800)
        
        # Central widget
        central = QWidget()
        self.setCentralWidget(central)
        
        layout = QVBoxLayout()
        
        # Info label
        self.info_label = QLabel("Virtual Scrolling Test - 1000 Sprites")
        self.info_label.setStyleSheet("font-size: 14px; font-weight: bold; padding: 10px;")
        layout.addWidget(self.info_label)
        
        # Create gallery widget
        self.gallery = SpriteGalleryWidget()
        self.gallery.sprite_selected.connect(self.on_sprite_selected)
        self.gallery.thumbnail_request.connect(self.on_thumbnail_request)
        layout.addWidget(self.gallery, 1)
        
        # Test buttons
        button_layout = QVBoxLayout()
        
        load_100_btn = QPushButton("Load 100 Sprites")
        load_100_btn.clicked.connect(lambda: self.load_sprites(100))
        button_layout.addWidget(load_100_btn)
        
        load_500_btn = QPushButton("Load 500 Sprites")
        load_500_btn.clicked.connect(lambda: self.load_sprites(500))
        button_layout.addWidget(load_500_btn)
        
        load_1000_btn = QPushButton("Load 1000 Sprites (Stress Test)")
        load_1000_btn.clicked.connect(lambda: self.load_sprites(1000))
        button_layout.addWidget(load_1000_btn)
        
        clear_btn = QPushButton("Clear Gallery")
        clear_btn.clicked.connect(self.clear_gallery)
        button_layout.addWidget(clear_btn)
        
        layout.addLayout(button_layout)
        
        central.setLayout(layout)
        
        # Thumbnail generation tracking
        self.thumbnail_cache = {}
        self.requests_pending = set()
        
        # Status timer
        self.status_timer = QTimer()
        self.status_timer.timeout.connect(self.update_status)
        self.status_timer.start(1000)
        
    def load_sprites(self, count: int):
        """Load test sprites into gallery."""
        logger.info(f"Loading {count} test sprites")
        
        # Create test data
        sprites = create_test_sprite_data(count)
        
        # Set in gallery
        self.gallery.set_sprites(sprites)
        
        self.info_label.setText(f"Loaded {count} sprites - scroll to load thumbnails on demand")
        
    def on_sprite_selected(self, offset: int):
        """Handle sprite selection."""
        logger.info(f"Sprite selected: 0x{offset:06X}")
        
    def on_thumbnail_request(self, offset: int, priority: int):
        """Handle thumbnail request from gallery."""
        if offset in self.thumbnail_cache:
            # Already have it cached
            self.gallery.set_thumbnail(offset, self.thumbnail_cache[offset])
        elif offset not in self.requests_pending:
            # Schedule generation
            self.requests_pending.add(offset)
            QTimer.singleShot(50 + priority * 10, lambda: self.generate_thumbnail(offset))
            
    def generate_thumbnail(self, offset: int):
        """Generate a thumbnail for the given offset."""
        if offset in self.requests_pending:
            self.requests_pending.discard(offset)
            
            # Create thumbnail
            pixmap = create_test_thumbnail(offset)
            
            # Cache it
            self.thumbnail_cache[offset] = pixmap
            
            # Set in gallery
            self.gallery.set_thumbnail(offset, pixmap)
            
            logger.debug(f"Generated thumbnail for 0x{offset:06X}")
            
    def clear_gallery(self):
        """Clear the gallery."""
        self.gallery.set_sprites([])
        self.thumbnail_cache.clear()
        self.requests_pending.clear()
        self.info_label.setText("Gallery cleared")
        
    def update_status(self):
        """Update status display."""
        if self.gallery.model:
            visible, total, selected = self.gallery.model.get_sprite_count_info()
            cached = len(self.thumbnail_cache)
            pending = len(self.requests_pending)
            
            status = f"Sprites: {visible}/{total} | Selected: {selected} | Thumbnails: {cached} cached, {pending} pending"
            self.setWindowTitle(f"Virtual Scrolling Test - {status}")


def main():
    """Run the test application."""
    app = QApplication(sys.argv)
    
    # Set dark theme
    app.setStyle("Fusion")
    
    window = TestWindow()
    window.show()
    
    # Auto-load 1000 sprites for immediate testing
    QTimer.singleShot(100, lambda: window.load_sprites(1000))
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()