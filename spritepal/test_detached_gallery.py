#!/usr/bin/env python3
from __future__ import annotations

"""
Test the detached gallery window solution.
Verifies that the gallery doesn't stretch when in a separate window.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

try:
    from PySide6.QtCore import Qt, QTimer
    from PySide6.QtGui import QPixmap
    from PySide6.QtWidgets import QApplication, QMainWindow, QPushButton, QVBoxLayout, QWidget
    from ui.windows.detached_gallery_window import DetachedGalleryWindow
    QT_AVAILABLE = True
except ImportError:
    QT_AVAILABLE = False
    print("Qt not available")
    sys.exit(1)

class TestMainWindow(QMainWindow):
    """Test main window with button to open detached gallery."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Detached Gallery Test")

        # Create central widget
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        # Add button to open detached gallery
        self.open_btn = QPushButton("Open Detached Gallery")
        self.open_btn.clicked.connect(self.open_gallery)
        layout.addWidget(self.open_btn)

        layout.addStretch()  # Push button to top

        self.detached_window = None

    def open_gallery(self):
        """Open the detached gallery window."""
        if not self.detached_window:
            self.detached_window = DetachedGalleryWindow(self)
            self.detached_window.window_closed.connect(self.on_gallery_closed)

        # Create test sprites
        sprites = []
        for i in range(17):  # Match user's case
            sprites.append({
                'offset': i * 0x1000,
                'decompressed_size': 2048,
                'tile_count': 64,
                'compressed': i % 3 == 0,
            })

        # Set sprites
        self.detached_window.set_sprites(sprites)

        # Generate mock thumbnails
        for sprite in sprites:
            offset = sprite['offset']
            if offset in self.detached_window.gallery_widget.thumbnails:
                pixmap = QPixmap(128, 128)
                pixmap.fill(Qt.GlobalColor.darkGray)
                thumbnail = self.detached_window.gallery_widget.thumbnails[offset]
                thumbnail.set_sprite_data(pixmap, sprite)

        # Show window
        self.detached_window.show()

        # Test after a delay
        QTimer.singleShot(500, self.test_detached_window)

    def test_detached_window(self):
        """Test the detached window layout."""
        if not self.detached_window:
            return

        print("\n" + "="*60)
        print("DETACHED GALLERY WINDOW TEST")
        print("="*60)

        gallery = self.detached_window.gallery_widget
        self.detached_window.centralWidget()

        # Check gallery size policy
        policy = gallery.sizePolicy()
        h_policy = policy.horizontalPolicy()
        v_policy = policy.verticalPolicy()

        print("\nGallery Widget:")
        print(f"  Size Policy: H={h_policy.name}, V={v_policy.name}")
        print(f"  Size: {gallery.width()}x{gallery.height()}")

        from PySide6.QtWidgets import QSizePolicy
        if v_policy == QSizePolicy.Policy.Preferred:
            print("  ✅ Vertical policy is Preferred (won't stretch)")
        else:
            print(f"  ⚠️  Vertical policy is {v_policy.name}")

        # Check content sizing
        if gallery.container_widget:
            container = gallery.container_widget
            print("\nContainer Widget:")
            print(f"  Size: {container.width()}x{container.height()}")

            # Calculate expected height
            columns = gallery.columns
            rows = (17 + columns - 1) // columns
            thumbnail_height = gallery.thumbnail_size + 20
            spacing = gallery.spacing
            controls_height = 50

            expected_height = controls_height + (rows * thumbnail_height) + ((rows - 1) * spacing) + 20
            actual_height = container.height()

            print("\nContent Analysis:")
            print(f"  Expected height: ~{expected_height}px")
            print(f"  Actual height: {actual_height}px")

            if actual_height > expected_height + 100:
                print(f"  ❌ STRETCHING DETECTED: {actual_height - expected_height}px excess")
            else:
                print("  ✅ NO STRETCHING - Gallery fits content!")

        # Test maximizing the detached window
        print("\nMaximizing detached window...")
        self.detached_window.showMaximized()
        QTimer.singleShot(500, self.test_maximized)

    def test_maximized(self):
        """Test after maximizing."""
        if not self.detached_window:
            return

        print("\n" + "="*60)
        print("MAXIMIZED DETACHED WINDOW TEST")
        print("="*60)

        gallery = self.detached_window.gallery_widget

        if gallery.container_widget:
            container = gallery.container_widget
            viewport = gallery.viewport()

            print(f"\nWindow Size: {self.detached_window.width()}x{self.detached_window.height()}")
            print(f"Gallery Size: {gallery.width()}x{gallery.height()}")
            print(f"Container Size: {container.width()}x{container.height()}")
            print(f"Viewport Size: {viewport.width()}x{viewport.height()}")

            # Calculate expected vs actual
            columns = gallery.columns
            rows = (17 + columns - 1) // columns
            thumbnail_height = gallery.thumbnail_size + 20
            spacing = gallery.spacing
            controls_height = 50

            expected_height = controls_height + (rows * thumbnail_height) + ((rows - 1) * spacing) + 20
            actual_height = container.height()

            print("\nContent Analysis (Maximized):")
            print(f"  Expected height: ~{expected_height}px")
            print(f"  Actual height: {actual_height}px")
            print(f"  Window height: {self.detached_window.height()}px")

            if actual_height > expected_height + 100:
                excess = actual_height - expected_height
                print(f"  ❌ STILL STRETCHING: {excess}px of empty space")
            else:
                print("  ✅ SUCCESS! Gallery doesn't stretch in detached window")
                print("  The detached window solution WORKS!")

        print("\n" + "="*60)
        print("FINAL VERDICT")
        print("="*60)
        print("\nThe detached gallery window should solve the stretching issue by:")
        print("1. Removing the stretch factor from parent layout")
        print("2. Using Preferred vertical size policy")
        print("3. Adding a stretch spacer below the gallery")
        print("4. Giving full control over the window layout")

    def on_gallery_closed(self):
        """Handle gallery window closing."""
        self.detached_window = None
        print("\nDetached gallery window closed")

def main():
    """Run the test."""
    if not QT_AVAILABLE:
        return 1

    app = QApplication.instance() or QApplication(sys.argv)

    print("="*60)
    print("TESTING DETACHED GALLERY WINDOW SOLUTION")
    print("="*60)
    print("\nThis test verifies that opening the gallery in a")
    print("separate window prevents the stretching issue.")
    print("\nClick 'Open Detached Gallery' to test...")

    window = TestMainWindow()
    window.show()

    return app.exec()

if __name__ == "__main__":
    sys.exit(main())
