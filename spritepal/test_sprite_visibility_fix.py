#!/usr/bin/env python3
"""
Test script to verify sprite visibility fixes.
Tests the rendering improvements for dark sprites on light backgrounds.
"""

import sys
from pathlib import Path
from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QLabel
from PyQt6.QtGui import QPixmap, QImage, QPainter, QColor
from PyQt6.QtCore import Qt

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from ui.widgets.sprite_preview_widget import SpritePreviewWidget
from ui.zoomable_preview import ZoomablePreviewWidget, PreviewPanel


def create_test_pixmap(dark: bool = True) -> QPixmap:
    """Create a test pixmap to simulate a sprite."""
    size = 64
    image = QImage(size, size, QImage.Format.Format_RGBA8888)
    
    painter = QPainter(image)
    
    # Create a simple sprite pattern
    if dark:
        # Dark sprite that would be invisible on dark background
        colors = [QColor(20, 20, 20), QColor(40, 40, 40), QColor(60, 60, 60)]
    else:
        # Light sprite for comparison
        colors = [QColor(200, 200, 200), QColor(150, 150, 150), QColor(100, 100, 100)]
    
    # Draw concentric squares
    for i, color in enumerate(colors):
        margin = i * 10
        painter.fillRect(margin, margin, size - 2 * margin, size - 2 * margin, color)
    
    # Add some detail
    painter.setPen(QColor(255, 0, 0))  # Red accent
    painter.drawLine(10, 10, size - 10, size - 10)
    painter.drawLine(10, size - 10, size - 10, 10)
    
    painter.end()
    
    return QPixmap.fromImage(image)


class TestWindow(QMainWindow):
    """Test window to demonstrate sprite visibility fixes."""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Sprite Visibility Test - Fixed Rendering")
        self.setGeometry(100, 100, 800, 600)
        
        # Central widget
        central = QWidget()
        self.setCentralWidget(central)
        
        layout = QVBoxLayout(central)
        
        # Title
        title = QLabel("<h2>Sprite Rendering Visibility Test</h2>")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        # Info label
        info = QLabel(
            "<p>This tests the sprite rendering fixes:</p>"
            "<ul>"
            "<li>✓ Light checkerboard background for dark sprites</li>"
            "<li>✓ Optional transparency for palette index 0</li>"
            "<li>✓ Better contrast colors</li>"
            "<li>✓ Consistent size constraints</li>"
            "</ul>"
        )
        layout.addWidget(info)
        
        # Test dark sprite (main issue)
        dark_label = QLabel("<b>Dark Sprite (Previously Invisible):</b>")
        layout.addWidget(dark_label)
        
        dark_preview = SpritePreviewWidget("Dark Sprite Test")
        dark_pixmap = create_test_pixmap(dark=True)
        dark_preview.set_sprite(dark_pixmap)
        layout.addWidget(dark_preview)
        
        # Test light sprite (for comparison)
        light_label = QLabel("<b>Light Sprite (Always Visible):</b>")
        layout.addWidget(light_label)
        
        light_preview = SpritePreviewWidget("Light Sprite Test")
        light_pixmap = create_test_pixmap(dark=False)
        light_preview.set_sprite(light_pixmap)
        layout.addWidget(light_preview)
        
        # Test zoomable preview
        zoom_label = QLabel("<b>Zoomable Preview (With Transparency Toggle):</b>")
        layout.addWidget(zoom_label)
        
        zoom_preview = PreviewPanel()
        zoom_preview.preview.set_preview(dark_pixmap)
        layout.addWidget(zoom_preview)
        
        # Result label
        result = QLabel(
            "<p style='color: green;'><b>✓ Sprites should now be visible!</b></p>"
            "<p>Dark sprites are displayed on a light checkerboard background.</p>"
        )
        result.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(result)


def main():
    """Run the test application."""
    app = QApplication(sys.argv)
    
    window = TestWindow()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()