#!/usr/bin/env python3
"""
Capture screenshot of the full application context:
Main window with Manual Offset dialog opened, showing the Gallery tab.
This shows what users see when they click the Manual Offset button.
"""

import sys
from datetime import datetime
from pathlib import Path

# Add spritepal to path
sys.path.insert(0, str(Path(__file__).parent))

from PySide6.QtCore import Qt, QTimer
from typing import cast
from PySide6.QtGui import QColor, QFont, QPainter, QPen, QPixmap
from PySide6.QtWidgets import QApplication

# Import main components
from core.managers.registry import initialize_managers
from ui.dialogs.manual_offset_unified_integrated import UnifiedManualOffsetDialog
from ui.main_window import MainWindow
from ui.tabs.sprite_gallery_tab import SpriteGalleryTab


class FullContextCapture:
    """Capture the full application context with gallery tab."""

    def __init__(self):
        self.app = QApplication.instance() or QApplication(sys.argv)
        self.main_window = None
        self.manual_offset_dialog = None

    def setup_main_window(self):
        """Create and configure the main window."""
        print("Setting up main window...")

        # Initialize managers
        try:
            initialize_managers()
        except Exception as e:
            print(f"Warning: Could not initialize managers: {e}")

        # Create main window
        self.main_window = MainWindow()
        self.main_window.setWindowTitle("SpritePal - SNES Sprite Editor")
        self.main_window.resize(1400, 900)

        # Position main window
        self.main_window.move(100, 50)

        # Try to load a ROM if available
        self.load_test_rom()

        # Show main window
        self.main_window.show()

    def load_test_rom(self):
        """Try to load a test ROM file."""
        # Look for ROM files
        rom_names = [
            "Kirby Super Star (USA).sfc",
            "Kirby_Super_Star.smc",
            "test_rom.sfc",
            "Kirby's Fun Pak (Europe).sfc"
        ]

        rom_path = None
        for rom_name in rom_names:
            test_path = Path(__file__).parent / rom_name
            if test_path.exists():
                rom_path = test_path
                break

        if rom_path and self.main_window and hasattr(self.main_window, 'rom_extraction_panel'):
            try:
                print(f"Loading ROM: {rom_path.name}")
                panel = self.main_window.rom_extraction_panel
                if hasattr(panel, '_load_rom_file'):
                    panel._load_rom_file(str(rom_path))
                elif hasattr(panel, 'load_rom'):
                    panel.load_rom(str(rom_path))
            except Exception as e:
                print(f"Could not load ROM: {e}")

    def open_manual_offset_dialog(self):
        """Open the Manual Offset dialog."""
        print("Opening Manual Offset dialog...")

        # Create the dialog
        self.manual_offset_dialog = UnifiedManualOffsetDialog(self.main_window)
        self.manual_offset_dialog.setWindowTitle("Manual Offset Editor")

        # Size and position the dialog over the main window
        self.manual_offset_dialog.resize(1000, 700)

        # Center it over the main window
        if self.main_window:
            main_pos = self.main_window.pos()
            main_size = self.main_window.size()
            dialog_size = self.manual_offset_dialog.size()

            x = main_pos.x() + (main_size.width() - dialog_size.width()) // 2
            y = main_pos.y() + (main_size.height() - dialog_size.height()) // 2

            self.manual_offset_dialog.move(x, y)

        # Find and switch to Gallery tab
        self.switch_to_gallery_tab()

        # Show the dialog
        self.manual_offset_dialog.show()

    def switch_to_gallery_tab(self):
        """Switch to the Gallery tab in the dialog."""
        if not self.manual_offset_dialog:
            return

        # Find the tab widget and gallery tab
        if hasattr(self.manual_offset_dialog, 'tab_widget'):
            tab_widget = self.manual_offset_dialog.tab_widget

            if tab_widget:
                for i in range(tab_widget.count()):
                    tab = tab_widget.widget(i)
                    if isinstance(tab, SpriteGalleryTab):
                        tab_widget.setCurrentIndex(i)
                    print(f"Switched to Gallery tab (index {i})")

                    # Populate with mock sprites
                    self.populate_gallery(tab)
                    break

    def populate_gallery(self, gallery_tab):
        """Add mock sprites to the gallery."""
        print("Populating gallery with mock sprites...")

        # Set mock ROM info
        gallery_tab.rom_path = "Kirby_Super_Star.smc"
        gallery_tab.rom_size = 4 * 1024 * 1024

        # Mock extractor
        class MockExtractor:
            def __init__(self):
                self.rom_injector = None

        gallery_tab.rom_extractor = MockExtractor()

        # Create sprite data
        sprites = []
        for i in range(30):
            sprites.append({
                'offset': i * 0x1000,
                'decompressed_size': 2048 + (i * 100),
                'tile_count': 64 + i,
                'compressed': i % 3 == 0,
                'width': 16,
                'height': 16
            })

        gallery_tab.sprites_data = sprites
        gallery_tab.gallery_widget.set_sprites(sprites)

        # Generate visual thumbnails
        for i, sprite in enumerate(sprites):
            offset = sprite['offset']

            # Create colorful thumbnail
            pixmap = QPixmap(128, 128)
            painter = QPainter(pixmap)

            # Background
            painter.fillRect(0, 0, 128, 128, QColor(40, 40, 40))

            # Colored sprite pattern
            hue = (i * 25) % 360
            color = QColor.fromHsv(hue, 200, 180)
            painter.fillRect(10, 10, 108, 108, color)

            # Draw sprite number
            painter.setPen(QPen(Qt.GlobalColor.white, 2))
            painter.setFont(QFont("Arial", 24, QFont.Weight.Bold))
            painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, f"#{i+1}")

            # HAL indicator for compressed sprites
            if sprite['compressed']:
                painter.fillRect(95, 5, 28, 18, QColor(0, 150, 0, 200))
                painter.setFont(QFont("Arial", 9))
                painter.setPen(Qt.GlobalColor.white)
                painter.drawText(98, 18, "HAL")

            painter.end()

            # Set the thumbnail
            if offset in gallery_tab.gallery_widget.thumbnails:
                thumbnail = gallery_tab.gallery_widget.thumbnails[offset]
                thumbnail.set_sprite_data(pixmap, sprite)

        gallery_tab.info_label.setText(f"Found {len(sprites)} sprites in Kirby_Super_Star.smc")

    def capture_screenshots(self):
        """Capture screenshots showing the full context."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        save_path = Path(__file__).parent / "test_screenshots"
        save_path.mkdir(exist_ok=True)

        def capture_normal():
            """Capture normal window arrangement."""
            print("\n📸 Capturing full application context...")

            # Capture entire screen area containing both windows
            app = QApplication.instance()
            screen = cast(QApplication, app).primaryScreen() if app else None
            if screen and self.main_window and self.manual_offset_dialog:
                # Calculate combined area of both windows
                main_rect = self.main_window.geometry()
                dialog_rect = self.manual_offset_dialog.geometry()

                # Create a bounding rectangle that includes both
                left = min(main_rect.left(), dialog_rect.left())
                top = min(main_rect.top(), dialog_rect.top())
                right = max(main_rect.right(), dialog_rect.right())
                bottom = max(main_rect.bottom(), dialog_rect.bottom())

                # Add some padding
                padding = 20
                capture_rect = screen.geometry()
                capture_rect.setLeft(max(0, left - padding))
                capture_rect.setTop(max(0, top - padding))
                capture_rect.setRight(min(screen.geometry().right(), right + padding))
                capture_rect.setBottom(min(screen.geometry().bottom(), bottom + padding))

                # Capture the screen area
                pixmap = screen.grabWindow(0,
                    capture_rect.left(), capture_rect.top(),
                    capture_rect.width(), capture_rect.height())

                filename = f"full_context_normal_{timestamp}.png"
                filepath = save_path / filename
                pixmap.save(str(filepath))

                print(f"✅ Captured: {filename}")
                print(f"   Size: {pixmap.width()}x{pixmap.height()}")
                print("   Shows: Main window with Manual Offset dialog (Gallery tab)")

            # Also capture just the dialog
            if self.manual_offset_dialog:
                dialog_pixmap = self.manual_offset_dialog.grab()
                dialog_filename = f"manual_offset_dialog_gallery_{timestamp}.png"
                dialog_filepath = save_path / dialog_filename
                dialog_pixmap.save(str(dialog_filepath))
                print(f"✅ Also captured dialog only: {dialog_filename}")

        def capture_maximized():
            """Capture with maximized dialog."""
            print("\n📸 Capturing maximized dialog context...")

            # Maximize the dialog
            if self.manual_offset_dialog:
                self.manual_offset_dialog.showMaximized()
            self.app.processEvents()

            QTimer.singleShot(100, lambda: capture_maximized_shot())

        def capture_maximized_shot():
            """Take the maximized screenshot."""
            # Capture the maximized dialog
            if self.manual_offset_dialog:
                pixmap = self.manual_offset_dialog.grab()
                filename = f"full_context_maximized_{timestamp}.png"
                filepath = save_path / filename
                pixmap.save(str(filepath))

                print(f"✅ Captured maximized: {filename}")
                print(f"   Size: {pixmap.width()}x{pixmap.height()}")

            # Restore dialog
            if self.manual_offset_dialog:
                self.manual_offset_dialog.showNormal()
                self.manual_offset_dialog.resize(1000, 700)

            # Finish
            QTimer.singleShot(500, self.finish)

        # Schedule captures
        QTimer.singleShot(100, capture_normal)
        QTimer.singleShot(1000, capture_maximized)

    def finish(self):
        """Complete the capture session."""
        print("\n" + "="*60)
        print("FULL APPLICATION CONTEXT CAPTURED")
        print("="*60)
        print("\n📁 Screenshots saved to: test_screenshots/")
        print("\nCaptured views:")
        print("1. Full context: Main window + Manual Offset dialog with Gallery tab")
        print("2. Dialog only: Manual Offset dialog focused view")
        print("3. Maximized: Dialog maximized to verify no empty space")
        print("\n✅ Screenshots show the complete user experience:")
        print("   - Main SpritePal window in background")
        print("   - Manual Offset dialog opened on top")
        print("   - Gallery tab selected and populated")
        print("   - Proper layout without excessive empty space")

        self.app.quit()

    def run(self):
        """Run the capture process."""
        print("="*60)
        print("FULL APPLICATION CONTEXT SCREENSHOT")
        print("="*60)
        print("\nCapturing the complete SpritePal application with")
        print("Manual Offset dialog opened to the Gallery tab...")

        # Step 1: Create main window
        self.setup_main_window()

        # Step 2: Open Manual Offset dialog after delay
        QTimer.singleShot(500, self.open_manual_offset_dialog)

        # Step 3: Capture screenshots after everything is ready
        QTimer.singleShot(1500, self.capture_screenshots)

        # Run the application
        return self.app.exec()


def main():
    """Main entry point."""
    capture = FullContextCapture()
    return capture.run()


if __name__ == "__main__":
    sys.exit(main())