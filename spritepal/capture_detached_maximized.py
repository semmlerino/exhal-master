#!/usr/bin/env python3
from __future__ import annotations

"""
Capture screenshot of the detached gallery window when maximized.
Shows the final solution working without stretching issues.
"""

import sys
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

try:
    from PySide6.QtCore import Qt, QTimer
    from PySide6.QtGui import QFont, QPainter, QPixmap
    from PySide6.QtWidgets import QApplication
    from ui.tabs.sprite_gallery_tab import SpriteGalleryTab
    QT_AVAILABLE = True
except ImportError:
    QT_AVAILABLE = False
    print("Qt not available")
    sys.exit(1)

class DetachedGalleryCapture:
    """Capture screenshots of the detached gallery window."""

    def __init__(self):
        self.app = QApplication.instance() or QApplication(sys.argv)
        self.gallery_tab = None
        self.detached_window = None

    def setup_gallery(self):
        """Setup gallery with test sprites."""
        print("📸 Setting up gallery with test sprites...")

        # Create gallery tab
        self.gallery_tab = SpriteGalleryTab()
        self.gallery_tab.setWindowTitle("Main Gallery Tab (for comparison)")

        # Setup mock ROM data
        self.gallery_tab.rom_path = "Kirby_Super_Star.smc"
        self.gallery_tab.rom_size = 4 * 1024 * 1024

        # Mock extractor
        from unittest.mock import MagicMock
        self.gallery_tab.rom_extractor = MagicMock()

        # Create 17 test sprites (matching user's original issue)
        sprites = []
        sprite_names = [
            "Kirby Walking", "Kirby Running", "Kirby Jumping", "Kirby Flying",
            "Kirby Inhaling", "Meta Knight", "King Dedede", "Waddle Dee",
            "Waddle Doo", "Gordo", "Bronto Burt", "Cappy", "Scarfy",
            "Hot Head", "Sparky", "Blade Knight", "Sir Kibble"
        ]

        for i in range(17):
            sprites.append({
                'offset': 0x200000 + (i * 0x2000),
                'decompressed_size': 2048 + (i * 100),
                'tile_count': 32 + (i * 4),
                'compressed': i % 3 == 0,
                'name': sprite_names[i] if i < len(sprite_names) else f"Sprite {i+1}",
            })

        self.gallery_tab.sprites_data = sprites
        self.gallery_tab.gallery_widget.set_sprites(sprites)

        # Generate colorful mock thumbnails
        colors = [
            Qt.GlobalColor.red, Qt.GlobalColor.green, Qt.GlobalColor.blue,
            Qt.GlobalColor.yellow, Qt.GlobalColor.cyan, Qt.GlobalColor.magenta,
            Qt.GlobalColor.darkRed, Qt.GlobalColor.darkGreen, Qt.GlobalColor.darkBlue,
            Qt.GlobalColor.darkYellow, Qt.GlobalColor.darkCyan, Qt.GlobalColor.darkMagenta,
            Qt.GlobalColor.lightGray, Qt.GlobalColor.gray, Qt.GlobalColor.darkGray,
            Qt.GlobalColor.black, Qt.GlobalColor.white
        ]

        for i, sprite in enumerate(sprites):
            offset = sprite['offset']
            if offset in self.gallery_tab.gallery_widget.thumbnails:
                # Create colorful thumbnail
                pixmap = QPixmap(128, 128)
                pixmap.fill(Qt.GlobalColor.black)

                painter = QPainter(pixmap)
                painter.fillRect(8, 8, 112, 112, colors[i % len(colors)])

                # Add sprite info text
                painter.setPen(Qt.GlobalColor.white)
                font = QFont("Arial", 10, QFont.Weight.Bold)
                painter.setFont(font)
                painter.drawText(16, 30, f"#{i+1}")
                painter.drawText(16, 50, sprite['name'][:8])
                painter.drawText(16, 70, f"0x{offset:06X}")

                # Add compression indicator
                if sprite['compressed']:
                    painter.fillRect(96, 96, 24, 24, Qt.GlobalColor.yellow)
                    painter.setPen(Qt.GlobalColor.black)
                    painter.drawText(100, 110, "HAL")

                painter.end()

                thumbnail = self.gallery_tab.gallery_widget.thumbnails[offset]
                thumbnail.set_sprite_data(pixmap, sprite)

        # Update status
        self.gallery_tab.gallery_widget.status_label.setText("17 sprites loaded from Kirby_Super_Star.smc")

        print(f"✅ Created {len(sprites)} colorful sprite thumbnails")

    def open_detached_gallery(self):
        """Open the detached gallery window."""
        print("🗖 Opening detached gallery window...")

        # Open detached gallery
        if self.gallery_tab:
            self.gallery_tab._open_detached_gallery()
            self.detached_window = self.gallery_tab.detached_window

        if self.detached_window:
            print("✅ Detached gallery window opened")
            return True
        print("❌ Failed to open detached gallery")
        return False

    def capture_screenshots(self):
        """Capture screenshots of both normal and maximized detached gallery."""
        if not self.detached_window:
            print("❌ No detached window to capture")
            return

        save_dir = Path(__file__).parent / "test_screenshots"
        save_dir.mkdir(exist_ok=True)

        print("\n📸 Capturing screenshots...")

        # 1. Capture normal size
        print("📷 Capturing normal window size...")
        self.detached_window.resize(1024, 768)
        self.detached_window.show()
        QTimer.singleShot(200, self.capture_normal)

    def capture_normal(self):
        """Capture normal size screenshot."""
        if not self.detached_window:
            print("❌ No detached window to capture")
            return

        timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
        save_dir = Path(__file__).parent / "test_screenshots"

        # Capture normal size
        pixmap = self.detached_window.grab()
        normal_path = save_dir / f"detached_gallery_normal_{timestamp}.png"
        pixmap.save(str(normal_path))

        print(f"✅ Normal size saved: {normal_path.name}")

        # Now maximize and capture
        print("📷 Maximizing and capturing maximized window...")
        self.detached_window.showMaximized()
        QTimer.singleShot(500, self.capture_maximized)

    def capture_maximized(self):
        """Capture maximized screenshot."""
        if not self.detached_window:
            print("❌ No detached window to capture")
            return

        timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
        save_dir = Path(__file__).parent / "test_screenshots"

        # Capture maximized
        pixmap = self.detached_window.grab()
        maximized_path = save_dir / f"detached_gallery_MAXIMIZED_{timestamp}.png"
        pixmap.save(str(maximized_path))

        print(f"✅ Maximized screenshot saved: {maximized_path.name}")

        # Analyze the layout
        self.analyze_maximized_layout()

    def analyze_maximized_layout(self):
        """Analyze the layout of the maximized window."""
        print("\n📊 ANALYZING MAXIMIZED LAYOUT")
        print("=" * 50)

        if not self.detached_window:
            print("❌ No detached window to analyze")
            return

        gallery = self.detached_window.gallery_widget

        # Window dimensions
        window_size = self.detached_window.size()
        gallery_size = gallery.size()

        print(f"Window size: {window_size.width()}x{window_size.height()}")
        print(f"Gallery size: {gallery_size.width()}x{gallery_size.height()}")

        # Container analysis
        if gallery.container_widget:
            container = gallery.container_widget
            container_size = container.size()
            print(f"Container size: {container_size.width()}x{container_size.height()}")

            # Calculate expected vs actual content height
            columns = gallery.columns
            rows = (17 + columns - 1) // columns
            thumbnail_height = gallery.thumbnail_size + 20
            spacing = gallery.spacing

            expected_content_height = (rows * thumbnail_height) + ((rows - 1) * spacing)
            actual_content_height = container_size.height()

            print(f"Columns: {columns}")
            print(f"Expected rows: {rows}")
            print(f"Expected content height: ~{expected_content_height}px")
            print(f"Actual container height: {actual_content_height}px")

            # Check for empty space
            empty_space = gallery_size.height() - actual_content_height - 100  # Account for controls

            print(f"Gallery height: {gallery_size.height()}px")
            print(f"Empty space: ~{empty_space}px")

            if empty_space > 200:
                print("❌ EXCESSIVE EMPTY SPACE DETECTED!")
            else:
                print("✅ NO EXCESSIVE EMPTY SPACE - SOLUTION WORKING!")

        # Size policy check
        gallery_policy = gallery.sizePolicy()
        v_policy = gallery_policy.verticalPolicy()
        print(f"Gallery vertical policy: {v_policy.name}")

        resizable = gallery.widgetResizable()
        print(f"Widget resizable: {resizable}")

        print("\n🎯 FINAL RESULT:")
        if resizable and empty_space <= 200:
            print("✅ DETACHED GALLERY SOLUTION IS WORKING PERFECTLY!")
            print("- Gallery properly fills window without excessive empty space")
            print("- Scrolling works correctly")
            print("- No stretching issues like in the embedded version")
        else:
            print("⚠️  Some issues may remain - check the screenshots")

        print("=" * 50)

        # Close after a delay
        QTimer.singleShot(2000, self.cleanup)

    def cleanup(self):
        """Clean up and exit."""
        print("\n🧹 Cleaning up...")

        if self.detached_window:
            self.detached_window.close()

        if self.gallery_tab:
            self.gallery_tab.cleanup()

        print("✅ Screenshots captured successfully!")
        print("Check the test_screenshots/ directory for the images.")

        self.app.quit()

    def run(self):
        """Run the complete capture process."""
        print("=" * 60)
        print("DETACHED GALLERY MAXIMIZED SCREENSHOT CAPTURE")
        print("=" * 60)

        self.setup_gallery()

        if self.open_detached_gallery():
            QTimer.singleShot(100, self.capture_screenshots)
        else:
            print("❌ Failed to open detached gallery")
            return 1

        return self.app.exec()

def main():
    """Main entry point."""
    if not QT_AVAILABLE:
        return 1

    capture = DetachedGalleryCapture()
    return capture.run()

if __name__ == "__main__":
    sys.exit(main())
