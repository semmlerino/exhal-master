#!/usr/bin/env python3
"""
Capture screenshots of the gallery tab in normal and maximized states.
This will show visually whether the empty space issue is fixed.
"""

import sys
from datetime import datetime
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

try:
    from PySide6.QtCore import Qt, QTimer
    from PySide6.QtGui import QColor, QFont, QPainter, QPen, QPixmap
    from PySide6.QtWidgets import QApplication, QWidget

    from ui.dialogs.manual_offset_unified_integrated import UnifiedManualOffsetDialog

    # Import the gallery components
    from ui.tabs.sprite_gallery_tab import SpriteGalleryTab

    QT_AVAILABLE = True
except ImportError as e:
    print(f"Qt not available: {e}")
    QT_AVAILABLE = False
    sys.exit(1)

def create_mock_sprites(count=20):
    """Create mock sprite data with visual thumbnails."""
    sprites = []
    for i in range(count):
        sprites.append({
            'offset': i * 0x1000,
            'decompressed_size': 2048 + (i * 100),
            'tile_count': 64 + i,
            'compressed': i % 3 == 0,
            'width': 16,
            'height': 16
        })
    return sprites

class GalleryTestDialog(UnifiedManualOffsetDialog):
    """Test dialog showing the gallery tab."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Gallery Layout Test - Visual")

        # Switch to Gallery tab
        if self.tab_widget:
            for i in range(self.tab_widget.count()):
                if self.tab_widget.tabText(i) == "Gallery":
                    self.tab_widget.setCurrentIndex(i)
                    break

        # Get the gallery tab
        self.gallery_tab = None
        if self.tab_widget:
            for i in range(self.tab_widget.count()):
                tab = self.tab_widget.widget(i)
                if isinstance(tab, SpriteGalleryTab):
                    self.gallery_tab = tab
                    break

        if self.gallery_tab:
            # Set up mock data
            self.gallery_tab.rom_path = "test_rom.smc"
            self.gallery_tab.rom_size = 4 * 1024 * 1024

            # Mock extractor
            class MockExtractor:
                def __init__(self):
                    self.rom_injector = None

            self.gallery_tab.rom_extractor = MockExtractor()

            # Add visual mock sprites
            self.add_visual_sprites(15)

        # Schedule captures
        QTimer.singleShot(100, self.capture_normal)
        QTimer.singleShot(500, self.capture_maximized)
        QTimer.singleShot(1000, self.capture_with_many)
        QTimer.singleShot(1500, self.generate_report)

    def add_visual_sprites(self, count):
        """Add sprites with actual visual thumbnails."""
        if not self.gallery_tab:
            return

        sprites = create_mock_sprites(count)
        self.gallery_tab.sprites_data = sprites
        if self.gallery_tab.gallery_widget:
            self.gallery_tab.gallery_widget.set_sprites(sprites)

        # Generate visual thumbnails for each sprite
        for i, sprite in enumerate(sprites):
            offset = sprite['offset']

            # Create a colorful thumbnail
            pixmap = QPixmap(128, 128)
            pixmap.fill(QColor(40, 40, 40))

            # Draw a pattern to make it visible
            painter = QPainter(pixmap)

            # Draw colored rectangle
            color = QColor.fromHsv((i * 30) % 360, 200, 180)
            painter.fillRect(10, 10, 108, 108, color)

            # Draw sprite number
            painter.setPen(QPen(Qt.GlobalColor.white, 2))
            font = QFont("Arial", 20, QFont.Weight.Bold)
            painter.setFont(font)
            painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, f"#{i+1}")

            painter.end()

            # Set the pixmap on the thumbnail widget
            if self.gallery_tab and self.gallery_tab.gallery_widget:
                if offset in self.gallery_tab.gallery_widget.thumbnails:
                    thumbnail = self.gallery_tab.gallery_widget.thumbnails[offset]
                    thumbnail.set_sprite_data(pixmap, sprite)

    def capture_normal(self):
        """Capture normal window state."""
        self.resize(1000, 700)
        QApplication.processEvents()
        QTimer.singleShot(50, lambda: self.take_screenshot("normal_window"))

    def capture_maximized(self):
        """Capture maximized window state."""
        self.showMaximized()
        QApplication.processEvents()
        QTimer.singleShot(50, lambda: self.take_screenshot("maximized_window"))

    def capture_with_many(self):
        """Capture with many sprites (scrolling)."""
        self.add_visual_sprites(50)
        QApplication.processEvents()
        QTimer.singleShot(50, lambda: self.take_screenshot("maximized_many_sprites"))

    def take_screenshot(self, name):
        """Take a screenshot of the current window."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"gallery_test_{name}_{timestamp}.png"

        # Capture the window
        pixmap = self.grab()

        # Save to file
        save_path = Path(__file__).parent / "test_screenshots"
        save_path.mkdir(exist_ok=True)

        filepath = save_path / filename
        pixmap.save(str(filepath))

        print(f"✅ Captured: {filename}")
        print(f"   Size: {pixmap.width()}x{pixmap.height()}")

        # Analyze the image for empty space
        self.analyze_screenshot(pixmap, name)

    def analyze_screenshot(self, pixmap, name):
        """Analyze screenshot for empty space."""
        # Convert to QImage for pixel access
        image = pixmap.toImage()

        # Sample the gallery area (skip toolbar and bottom bar)
        width = image.width()
        height = image.height()

        # Estimate gallery area (middle 80% of window)
        start_y = int(height * 0.15)  # Skip top toolbar
        end_y = int(height * 0.85)    # Skip bottom bar

        # Count non-background pixels
        background_color = QColor(30, 30, 30)  # Dark background
        content_pixels = 0
        total_pixels = 0

        # Sample every 10th pixel for speed
        for y in range(start_y, end_y, 10):
            for x in range(0, width, 10):
                pixel_color = image.pixelColor(x, y)
                total_pixels += 1

                # Check if pixel is not background
                if abs(pixel_color.red() - background_color.red()) > 20 or \
                   abs(pixel_color.green() - background_color.green()) > 20 or \
                   abs(pixel_color.blue() - background_color.blue()) > 20:
                    content_pixels += 1

        content_ratio = content_pixels / total_pixels if total_pixels > 0 else 0

        print(f"   Content density: {content_ratio:.1%}")
        if content_ratio < 0.2:
            print("   ⚠️  Low content density - possible empty space issue")
        else:
            print("   ✅ Good content density")

    def generate_report(self):
        """Generate final report."""
        print("\n" + "="*60)
        print("VISUAL TEST COMPLETE")
        print("="*60)
        print("\nScreenshots saved to: test_screenshots/")
        print("\nThe screenshots show the gallery in different states:")
        print("1. Normal window (1000x700) with 15 sprites")
        print("2. Maximized window with 15 sprites")
        print("3. Maximized window with 50 sprites (scrolling)")
        print("\nIf the fix is working correctly:")
        print("- Sprites should be at the TOP of the gallery area")
        print("- No large empty space between toolbar and sprites")
        print("- Scrollbar only appears when needed")
        print("\n✅ Test complete. Check screenshots to verify layout.")

        QApplication.quit()

def main():
    """Run the visual capture test."""
    if not QT_AVAILABLE:
        return 1

    app = QApplication.instance()
    if not app:
        app = QApplication(sys.argv)

    print("="*60)
    print("GALLERY LAYOUT VISUAL TEST")
    print("="*60)
    print("\nCapturing screenshots to verify layout fix...")

    # Create test dialog
    dialog = GalleryTestDialog()
    dialog.show()

    return app.exec()

if __name__ == "__main__":
    sys.exit(main())
