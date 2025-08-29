#!/usr/bin/env python3
from __future__ import annotations

"""
Capture screenshot of the gallery tab within its parent dialog window.
Shows the complete context with all UI elements.
"""

import sys
from datetime import datetime
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

try:
    from PySide6.QtCore import Qt, QTimer
    from PySide6.QtGui import QColor, QFont, QPainter, QPen, QPixmap
    from PySide6.QtWidgets import QApplication

    # Import the main dialog
    from ui.dialogs.manual_offset_unified_integrated import UnifiedManualOffsetDialog
    from ui.tabs.sprite_gallery_tab import SpriteGalleryTab

    QT_AVAILABLE = True
except ImportError as e:
    print(f"Qt not available: {e}")
    QT_AVAILABLE = False
    sys.exit(1)

def create_visual_sprites(count=25):
    """Create visually distinct mock sprites."""
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

class ScreenshotDialog(UnifiedManualOffsetDialog):
    """Dialog configured for screenshot capture."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("SpritePal - Manual Offset Editor")

        # Set a good size for the screenshot
        self.resize(1200, 800)

        # Find and switch to Gallery tab
        self.gallery_tab = None
        gallery_index = -1

        if self.tab_widget:
            for i in range(self.tab_widget.count()):
                tab = self.tab_widget.widget(i)
                if isinstance(tab, SpriteGalleryTab):
                    self.gallery_tab = tab
                    gallery_index = i
                    break

        if gallery_index >= 0:
            if self.tab_widget:
                self.tab_widget.setCurrentIndex(gallery_index)
            print(f"✅ Switched to Gallery tab (index {gallery_index})")

        if self.gallery_tab:
            # Set up mock ROM data
            self.gallery_tab.rom_path = "Kirby_Super_Star.smc"
            self.gallery_tab.rom_size = 4 * 1024 * 1024  # 4MB

            # Mock extractor
            class MockExtractor:
                def __init__(self):
                    self.rom_injector = None

            self.gallery_tab.rom_extractor = MockExtractor()

            # Update info label to look realistic
            self.gallery_tab.info_label.setText("ROM: Kirby_Super_Star.smc (4.0MB)")

            # Add colorful mock sprites
            self.populate_gallery_with_sprites()

        # Schedule screenshots
        QTimer.singleShot(200, self.capture_normal)
        QTimer.singleShot(600, self.capture_maximized)
        QTimer.singleShot(1000, self.capture_with_scroll)
        QTimer.singleShot(1400, self.finish_capture)

    def populate_gallery_with_sprites(self):
        """Add realistic-looking sprite thumbnails."""
        if not self.gallery_tab:
            return

        sprites = create_visual_sprites(25)
        self.gallery_tab.sprites_data = sprites
        if self.gallery_tab.gallery_widget:
            self.gallery_tab.gallery_widget.set_sprites(sprites)

        # Generate colorful thumbnails
        for i, sprite in enumerate(sprites):
            offset = sprite['offset']

            # Create a visually appealing thumbnail
            pixmap = QPixmap(128, 128)

            # Background gradient
            painter = QPainter(pixmap)
            painter.fillRect(0, 0, 128, 128, QColor(50, 50, 50))

            # Create a sprite-like pattern
            base_hue = (i * 25) % 360

            # Draw tile grid pattern (8x8 tiles)
            tile_size = 16
            for ty in range(8):
                for tx in range(8):
                    # Vary the color slightly for each tile
                    hue = (base_hue + (tx + ty) * 5) % 360
                    saturation = 180 + (tx * 10) % 50
                    value = 140 + (ty * 10) % 60

                    color = QColor.fromHsv(hue, saturation, value)
                    painter.fillRect(tx * tile_size, ty * tile_size,
                                   tile_size - 1, tile_size - 1, color)

            # Draw sprite info overlay
            painter.setPen(QPen(Qt.GlobalColor.white, 2))
            painter.fillRect(0, 100, 128, 28, QColor(0, 0, 0, 180))

            font = QFont("Arial", 10)
            painter.setFont(font)
            painter.setPen(Qt.GlobalColor.white)
            painter.drawText(5, 120, f"Sprite #{i+1:02d}")

            # Add a HAL compression indicator for some sprites
            if sprite['compressed']:
                painter.fillRect(100, 5, 23, 15, QColor(0, 150, 0, 200))
                painter.setFont(QFont("Arial", 8))
                painter.drawText(102, 17, "HAL")

            painter.end()

            # Set the thumbnail
            if self.gallery_tab and self.gallery_tab.gallery_widget:
                if offset in self.gallery_tab.gallery_widget.thumbnails:
                    thumbnail = self.gallery_tab.gallery_widget.thumbnails[offset]
                    thumbnail.set_sprite_data(pixmap, sprite)

        # Update status
        if self.gallery_tab and self.gallery_tab.info_label:
            self.gallery_tab.info_label.setText(
                f"Found {len(sprites)} sprites in Kirby_Super_Star.smc"
            )

    def capture_normal(self):
        """Capture normal window state."""
        print("\n📸 Capturing normal window (1200x800)...")
        QApplication.processEvents()
        QTimer.singleShot(50, lambda: self.take_screenshot("normal",
            "Gallery tab in normal window - showing sprite thumbnails"))

    def capture_maximized(self):
        """Capture maximized window state."""
        print("\n📸 Capturing maximized window...")
        self.showMaximized()
        QApplication.processEvents()
        QTimer.singleShot(50, lambda: self.take_screenshot("maximized",
            "Gallery tab in maximized window - verifying no empty space"))

    def capture_with_scroll(self):
        """Capture with more sprites to show scrolling."""
        print("\n📸 Capturing with scrollable content...")

        if not self.gallery_tab:
            return

        # Add more sprites
        sprites = create_visual_sprites(60)
        self.gallery_tab.sprites_data = sprites
        if self.gallery_tab.gallery_widget:
            self.gallery_tab.gallery_widget.set_sprites(sprites)

        # Regenerate thumbnails for new sprites
        for i, sprite in enumerate(sprites):
            offset = sprite['offset']

            pixmap = QPixmap(128, 128)
            painter = QPainter(pixmap)

            # Simpler coloring for many sprites
            color = QColor.fromHsv((i * 6) % 360, 200, 160)
            painter.fillRect(0, 0, 128, 128, color)

            # Draw number
            painter.setPen(Qt.GlobalColor.white)
            painter.setFont(QFont("Arial", 24, QFont.Weight.Bold))
            painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, str(i + 1))

            painter.end()

            if self.gallery_tab and self.gallery_tab.gallery_widget:
                if offset in self.gallery_tab.gallery_widget.thumbnails:
                    thumbnail = self.gallery_tab.gallery_widget.thumbnails[offset]
                    thumbnail.set_sprite_data(pixmap, sprite)

        if self.gallery_tab and self.gallery_tab.info_label:
            self.gallery_tab.info_label.setText(
                f"Found {len(sprites)} sprites in Kirby_Super_Star.smc (scrollable)"
            )

        QApplication.processEvents()
        QTimer.singleShot(50, lambda: self.take_screenshot("scrollable",
            "Gallery with many sprites - demonstrating scroll functionality"))

    def take_screenshot(self, name, description):
        """Take and save a screenshot."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"gallery_dialog_{name}_{timestamp}.png"

        # Capture the entire dialog
        pixmap = self.grab()

        # Save to screenshots directory
        save_path = Path(__file__).parent / "test_screenshots"
        save_path.mkdir(exist_ok=True)

        filepath = save_path / filename
        pixmap.save(str(filepath))

        print(f"✅ Captured: {filename}")
        print(f"   Size: {pixmap.width()}x{pixmap.height()}")
        print(f"   Description: {description}")

        # Quick analysis
        self.analyze_layout(pixmap, name)

    def analyze_layout(self, pixmap, name):
        """Analyze the screenshot for layout issues."""
        image = pixmap.toImage()
        height = image.height()
        width = image.width()

        # Sample the center area where gallery content should be
        center_y_start = int(height * 0.2)  # Below tabs
        center_y_end = int(height * 0.8)    # Above bottom buttons

        # Count content vs background pixels
        background_samples = 0
        content_samples = 0

        for y in range(center_y_start, center_y_end, 5):
            for x in range(int(width * 0.2), int(width * 0.8), 5):
                color = image.pixelColor(x, y)

                # Dark background is roughly rgb(30, 30, 30)
                if color.red() < 40 and color.green() < 40 and color.blue() < 40:
                    background_samples += 1
                else:
                    content_samples += 1

        total_samples = background_samples + content_samples
        if total_samples > 0:
            content_ratio = content_samples / total_samples
            print(f"   Content ratio: {content_ratio:.1%}")

            if content_ratio < 0.15:
                print("   ⚠️  Very low content - possible empty space issue")
            elif content_ratio < 0.3:
                print("   📊 Some empty space detected")
            else:
                print("   ✅ Good content distribution")

    def finish_capture(self):
        """Complete the capture session."""
        print("\n" + "="*60)
        print("SCREENSHOT CAPTURE COMPLETE")
        print("="*60)
        print("\n📁 Screenshots saved to: test_screenshots/")
        print("\nCaptured 3 views of the gallery tab:")
        print("1. Normal window (1200x800)")
        print("2. Maximized window")
        print("3. With scrollable content (60 sprites)")
        print("\n✅ The screenshots show the complete dialog context")
        print("   with the gallery tab selected and populated.")

        QApplication.quit()

def main():
    """Run the screenshot capture."""
    if not QT_AVAILABLE:
        print("PySide6 not available")
        return 1

    app = QApplication.instance()
    if not app:
        app = QApplication(sys.argv)

    print("="*60)
    print("GALLERY TAB SCREENSHOT CAPTURE")
    print("="*60)
    print("\nCapturing the gallery tab within the UnifiedManualOffsetDialog...")
    print("This shows the complete UI context with all elements.")

    # Create and show the dialog
    dialog = ScreenshotDialog()
    dialog.show()

    return app.exec()

if __name__ == "__main__":
    sys.exit(main())
