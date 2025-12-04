#!/usr/bin/env python3
from __future__ import annotations

"""
Final test for the empty space fix in sprite gallery.
Verifies that the main_widget and container don't expand beyond content.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

try:
    from PySide6.QtCore import Qt, QTimer
    from PySide6.QtGui import QPixmap
    from PySide6.QtWidgets import QApplication, QMainWindow, QSizePolicy, QVBoxLayout, QWidget
    from ui.tabs.sprite_gallery_tab import SpriteGalleryTab
    QT_AVAILABLE = True
except ImportError:
    QT_AVAILABLE = False
    print("Qt not available")
    sys.exit(1)

class TestWindow(QMainWindow):
    """Test window to verify the final empty space fix."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Final Empty Space Fix Test")

        # Create central widget
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        # Create gallery tab
        self.gallery_tab = SpriteGalleryTab()
        layout.addWidget(self.gallery_tab)

        # Setup mock data
        self.gallery_tab.rom_path = "test_rom.smc"
        self.gallery_tab.rom_size = 4 * 1024 * 1024

        class MockExtractor:
            def __init__(self):
                self.rom_injector = None

        self.gallery_tab.rom_extractor = MockExtractor()

        # Add test sprites (17 to match user's case)
        sprites = []
        for i in range(17):
            sprites.append({
                'offset': i * 0x1000,
                'decompressed_size': 2048,
                'tile_count': 64,
                'compressed': i % 3 == 0,
            })

        self.gallery_tab.sprites_data = sprites
        self.gallery_tab.gallery_widget.set_sprites(sprites)

        # Generate simple thumbnails
        for i, sprite in enumerate(sprites):
            offset = sprite['offset']
            if offset in self.gallery_tab.gallery_widget.thumbnails:
                pixmap = QPixmap(128, 128)
                pixmap.fill(Qt.GlobalColor.darkGray)
                thumbnail = self.gallery_tab.gallery_widget.thumbnails[offset]
                thumbnail.set_sprite_data(pixmap, sprite)

        # Schedule tests
        QTimer.singleShot(100, self.test_normal)
        QTimer.singleShot(500, self.test_maximized)
        QTimer.singleShot(1000, self.final_report)

    def test_normal(self):
        """Test in normal window size."""
        self.resize(800, 600)
        QApplication.processEvents()

        print("\n" + "="*60)
        print("NORMAL WINDOW TEST (800x600)")
        print("="*60)

        self.check_policies_and_sizes("Normal")

    def test_maximized(self):
        """Test in maximized window."""
        self.showMaximized()
        QApplication.processEvents()

        # Let it settle
        QTimer.singleShot(100, self.check_maximized)

    def check_maximized(self):
        """Check after maximizing."""
        print("\n" + "="*60)
        print("MAXIMIZED WINDOW TEST")
        print("="*60)

        self.check_policies_and_sizes("Maximized")

    def check_policies_and_sizes(self, state):
        """Check size policies and actual sizes."""
        gallery = self.gallery_tab.gallery_widget

        # Get the main_widget (content of scroll area)
        main_widget = gallery.widget()

        # Get the container widget
        container = gallery.container_widget

        # Get viewport
        viewport = gallery.viewport()

        print(f"\n{state} State Analysis:")
        print("-" * 40)

        # Check main_widget size policy
        if main_widget:
            policy = main_widget.sizePolicy()
            h_policy = policy.horizontalPolicy()
            v_policy = policy.verticalPolicy()

            print("Main Widget:")
            print(f"  Size Policy: H={h_policy.name}, V={v_policy.name}")
            print(f"  Actual Size: {main_widget.width()}x{main_widget.height()}")

            if v_policy == QSizePolicy.Policy.Maximum:
                print("  ✅ Vertical policy is Maximum (prevents expansion)")
            else:
                print(f"  ❌ Vertical policy is {v_policy.name} (should be Maximum)")

        # Check container size policy
        if container:
            policy = container.sizePolicy()
            h_policy = policy.horizontalPolicy()
            v_policy = policy.verticalPolicy()

            print("\nContainer Widget:")
            print(f"  Size Policy: H={h_policy.name}, V={v_policy.name}")
            print(f"  Actual Size: {container.width()}x{container.height()}")

            if v_policy == QSizePolicy.Policy.Maximum:
                print("  ✅ Vertical policy is Maximum (prevents expansion)")
            elif v_policy == QSizePolicy.Policy.Preferred:
                print("  ⚠️  Vertical policy is Preferred (may expand)")
            else:
                print(f"  ❌ Vertical policy is {v_policy.name}")

        # Check viewport
        print("\nViewport:")
        print(f"  Size: {viewport.width()}x{viewport.height()}")

        # Calculate content efficiency
        if main_widget and viewport:
            # Calculate expected height
            columns = gallery.columns
            rows = (17 + columns - 1) // columns
            thumbnail_height = gallery.thumbnail_size + 20
            spacing = gallery.spacing
            controls_height = 50  # Approximate

            expected_content_height = controls_height + (rows * thumbnail_height) + ((rows - 1) * spacing) + 20
            actual_height = main_widget.height()

            print("\nContent Analysis:")
            print(f"  Expected height: ~{expected_content_height}px")
            print(f"  Actual height: {actual_height}px")
            print(f"  Difference: {actual_height - expected_content_height}px")

            if actual_height > expected_content_height + 100:
                excess = actual_height - expected_content_height
                print(f"  ❌ EXCESSIVE EXPANSION: {excess}px of empty space!")
            else:
                print("  ✅ Content height is appropriate")

    def final_report(self):
        """Final report on the fix."""
        print("\n" + "="*60)
        print("FINAL EMPTY SPACE FIX VERIFICATION")
        print("="*60)

        gallery = self.gallery_tab.gallery_widget
        main_widget = gallery.widget()

        if main_widget:
            policy = main_widget.sizePolicy()
            v_policy = policy.verticalPolicy()

            if v_policy == QSizePolicy.Policy.Maximum:
                print("\n✅ FIX SUCCESSFULLY APPLIED!")
                print("\nThe main_widget has Maximum vertical policy which prevents")
                print("it from expanding beyond its content when setWidgetResizable")
                print("is True. This should eliminate the empty space issue.")
                print("\nKey changes made:")
                print("1. main_widget.setSizePolicy(Preferred, Maximum)")
                print("2. container_widget.setSizePolicy(Expanding, Maximum)")
                print("\nExpected behavior:")
                print("- Content stays compact at its natural size")
                print("- No excessive empty space when maximized")
                print("- Scrolling works when content exceeds viewport")
            else:
                print("\n❌ FIX NOT PROPERLY APPLIED")
                print(f"Main widget vertical policy is {v_policy.name}, not Maximum")
                print("The empty space issue will persist.")

        QApplication.quit()

def main():
    """Run the final test."""
    if not QT_AVAILABLE:
        return 1

    app = QApplication.instance() or QApplication(sys.argv)

    print("="*60)
    print("FINAL EMPTY SPACE FIX TEST")
    print("="*60)
    print("\nThis test verifies the final fix for the empty space issue:")
    print("- main_widget has Maximum vertical size policy")
    print("- container_widget has Maximum vertical size policy")
    print("- Content doesn't expand beyond its natural size")

    window = TestWindow()
    window.show()

    return app.exec()

if __name__ == "__main__":
    sys.exit(main())
