#!/usr/bin/env python3
from __future__ import annotations

"""
Test sprite gallery layout when window is maximized.
Measures actual dimensions to verify empty space fix.
"""

import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

try:
    from PySide6.QtCore import Qt, QTimer
    from PySide6.QtGui import QColor, QPixmap
    from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget

    # Import the gallery components
    from ui.tabs.sprite_gallery_tab import SpriteGalleryTab
    from ui.widgets.sprite_gallery_widget import SpriteGalleryWidget

    QT_AVAILABLE = True
except ImportError as e:
    print(f"Qt not available: {e}")
    QT_AVAILABLE = False

def create_mock_sprites(count=20):
    """Create mock sprite data for testing."""
    sprites = []
    for i in range(count):
        sprites.append({
            'offset': i * 0x1000,
            'decompressed_size': 2048 + (i * 100),
            'tile_count': 64 + i,
            'compressed': i % 3 == 0,  # Every 3rd sprite is compressed
            'width': 16,
            'height': 16
        })
    return sprites

class LayoutTestWindow(QMainWindow):
    """Test window for measuring gallery layout."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Gallery Layout Test")
        self.resize(800, 600)

        # Create central widget
        central = QWidget()
        self.setCentralWidget(central)

        # Create layout
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)

        # Create gallery tab
        self.gallery_tab = SpriteGalleryTab()
        layout.addWidget(self.gallery_tab)

        # Mock ROM data
        self.gallery_tab.rom_path = "test_rom.smc"
        self.gallery_tab.rom_size = 4 * 1024 * 1024  # 4MB

        # Create mock extractor
        class MockExtractor:
            def __init__(self):
                self.rom_injector = None

        self.gallery_tab.rom_extractor = MockExtractor()

        # Schedule measurements
        QTimer.singleShot(100, self.run_tests)

    def measure_layout(self, description=""):
        """Measure current layout dimensions."""
        gallery = self.gallery_tab.gallery_widget

        if not gallery:
            return None

        # Get dimensions
        viewport_size = gallery.viewport().size()
        content_widget = gallery.widget()

        if not content_widget:
            return None

        content_size = content_widget.size()

        # Calculate actual content height (controls + thumbnails)
        actual_content_height = 0

        # Get controls height
        if hasattr(gallery, 'controls_widget') and gallery.controls_widget:
            actual_content_height += gallery.controls_widget.sizeHint().height()

        # Get thumbnail grid height
        if hasattr(gallery, 'container_widget') and gallery.container_widget:
            container = gallery.container_widget
            grid_layout = container.layout()

            if grid_layout and grid_layout.count() > 0:
                # Calculate grid dimensions
                rows = (grid_layout.count() + gallery.columns - 1) // gallery.columns
                thumbnail_height = gallery.thumbnail_size + 20  # Size + label
                spacing = grid_layout.spacing()

                grid_height = rows * thumbnail_height + (rows - 1) * spacing
                actual_content_height += grid_height
            else:
                # No thumbnails, just get minimum height
                actual_content_height += container.minimumSizeHint().height()

        # Calculate metrics
        empty_space = content_size.height() - actual_content_height
        empty_space_ratio = empty_space / viewport_size.height() if viewport_size.height() > 0 else 0
        content_efficiency = actual_content_height / content_size.height() if content_size.height() > 0 else 0

        return {
            'description': description,
            'window_size': f"{self.width()}x{self.height()}",
            'viewport_size': f"{viewport_size.width()}x{viewport_size.height()}",
            'content_size': f"{content_size.width()}x{content_size.height()}",
            'actual_content_height': actual_content_height,
            'empty_space': empty_space,
            'empty_space_ratio': empty_space_ratio,
            'content_efficiency': content_efficiency,
            'has_scrollbar': gallery.verticalScrollBar().isVisible() if gallery.verticalScrollBar() else False
        }

    def run_tests(self):
        """Run layout tests in different window states."""
        results = []

        # Test 1: Normal window with sprites
        print("\n" + "="*60)
        print("TEST 1: Normal Window (800x600) with 20 sprites")
        print("="*60)

        # Add mock sprites
        sprites = create_mock_sprites(20)
        self.gallery_tab.sprites_data = sprites
        self.gallery_tab.gallery_widget.set_sprites(sprites)

        # Process events and measure
        QApplication.processEvents()
        QTimer.singleShot(50, lambda: self.measure_and_report(results, "Normal window (20 sprites)"))

        # Test 2: Maximized window
        QTimer.singleShot(200, lambda: self.test_maximized(results))

        # Test 3: Many sprites (scrolling required)
        QTimer.singleShot(400, lambda: self.test_many_sprites(results))

        # Final report
        QTimer.singleShot(600, lambda: self.final_report(results))

    def measure_and_report(self, results, description):
        """Measure layout and report results."""
        measurement = self.measure_layout(description)
        if measurement:
            results.append(measurement)
            self.print_measurement(measurement)

    def test_maximized(self, results):
        """Test with maximized window."""
        print("\n" + "="*60)
        print("TEST 2: Maximized Window with 20 sprites")
        print("="*60)

        self.showMaximized()
        QApplication.processEvents()
        QTimer.singleShot(50, lambda: self.measure_and_report(results, "Maximized window (20 sprites)"))

    def test_many_sprites(self, results):
        """Test with many sprites requiring scrolling."""
        print("\n" + "="*60)
        print("TEST 3: Maximized Window with 100 sprites (scrolling)")
        print("="*60)

        # Add many sprites
        sprites = create_mock_sprites(100)
        self.gallery_tab.sprites_data = sprites
        self.gallery_tab.gallery_widget.set_sprites(sprites)

        QApplication.processEvents()
        QTimer.singleShot(50, lambda: self.measure_and_report(results, "Maximized window (100 sprites)"))

    def print_measurement(self, m):
        """Print measurement results."""
        print(f"\nDescription: {m['description']}")
        print(f"Window Size: {m['window_size']}")
        print(f"Viewport Size: {m['viewport_size']}")
        print(f"Content Widget Size: {m['content_size']}")
        print(f"Actual Content Height: {m['actual_content_height']}px")
        print(f"Empty Space: {m['empty_space']}px")
        print(f"Empty Space Ratio: {m['empty_space_ratio']:.2%}")
        print(f"Content Efficiency: {m['content_efficiency']:.2%}")
        print(f"Has Scrollbar: {m['has_scrollbar']}")

        # Verdict
        if m['empty_space_ratio'] > 0.5:
            print("❌ ISSUE: Excessive empty space detected!")
        elif m['empty_space_ratio'] > 0.2:
            print("⚠️  WARNING: Some empty space present")
        else:
            print("✅ GOOD: Minimal empty space")

    def final_report(self, results):
        """Print final analysis."""
        print("\n" + "="*60)
        print("FINAL ANALYSIS")
        print("="*60)

        if not results:
            print("❌ No measurements collected")
            QApplication.quit()
            return

        # Analyze maximized window results
        maximized_results = [r for r in results if 'Maximized' in r['description']]

        if maximized_results:
            # Check for empty space issue
            issues = []
            for r in maximized_results:
                if r['empty_space_ratio'] > 0.3:  # More than 30% empty space
                    issues.append(f"- {r['description']}: {r['empty_space_ratio']:.1%} empty space")

            if issues:
                print("\n❌ EMPTY SPACE ISSUE DETECTED:")
                for issue in issues:
                    print(issue)
                print("\nThe layout fix may not be working correctly.")
                print("The gallery content should stay compact at the top.")
            else:
                print("\n✅ LAYOUT FIX VERIFIED SUCCESSFUL!")
                print("The gallery content stays compact without excessive empty space.")
                print("\nKey findings:")
                for r in maximized_results:
                    print(f"- {r['description']}: {r['content_efficiency']:.1%} content efficiency")

        # Check scrolling behavior
        scroll_results = [r for r in results if '100 sprites' in r['description']]
        if scroll_results and scroll_results[0]['has_scrollbar']:
            print("\n✅ Scrolling works correctly with many sprites")

        QApplication.quit()

def main():
    """Main test function."""
    if not QT_AVAILABLE:
        print("PySide6 not available. Please install it to run this test.")
        return 1

    # Set up Qt application
    app = QApplication.instance()
    if not app:
        app = QApplication(sys.argv)

    # For headless testing
    if os.environ.get('QT_QPA_PLATFORM') == 'offscreen':
        print("Running in headless mode (offscreen)")

    print("="*60)
    print("SPRITE GALLERY LAYOUT TEST - WINDOW MAXIMIZATION")
    print("="*60)
    print("\nThis test measures the actual layout dimensions to verify")
    print("that the empty space issue has been fixed when maximizing.")

    # Create and show test window
    window = LayoutTestWindow()
    window.show()

    # Run application
    return app.exec()

if __name__ == "__main__":
    sys.exit(main())
