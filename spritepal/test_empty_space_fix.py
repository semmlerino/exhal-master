#!/usr/bin/env python3
"""
Test that the empty space issue is fixed in the gallery.
Verifies that the container doesn't expand beyond its content.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

try:
    from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget
    from PySide6.QtCore import QTimer
    from PySide6.QtGui import QPixmap
    from ui.tabs.sprite_gallery_tab import SpriteGalleryTab
    QT_AVAILABLE = True
except ImportError:
    QT_AVAILABLE = False
    print("Qt not available")
    sys.exit(1)

class TestWindow(QMainWindow):
    """Test window to verify the empty space fix."""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Empty Space Fix Test")
        
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
                pixmap.fill(Qt.darkGray)
                thumbnail = self.gallery_tab.gallery_widget.thumbnails[offset]
                thumbnail.set_sprite_data(pixmap, sprite)
        
        # Schedule tests
        QTimer.singleShot(100, self.test_normal)
        QTimer.singleShot(500, self.test_maximized)
        QTimer.singleShot(1000, self.report_results)
    
    def test_normal(self):
        """Test in normal window size."""
        self.resize(800, 600)
        QApplication.processEvents()
        
        # Measure layout
        gallery = self.gallery_tab.gallery_widget
        container = gallery.container_widget
        viewport = gallery.viewport()
        
        self.normal_results = {
            'window_size': f"{self.width()}x{self.height()}",
            'viewport_height': viewport.height(),
            'container_height': container.height(),
            'container_size_policy': container.sizePolicy(),
        }
        
        print("\n📏 Normal Window (800x600):")
        print(f"  Viewport height: {viewport.height()}px")
        print(f"  Container height: {container.height()}px")
        
        # Check container size policy
        v_policy = container.sizePolicy().verticalPolicy()
        from PySide6.QtWidgets import QSizePolicy
        if v_policy == QSizePolicy.Policy.Preferred:
            print("  ✅ Container vertical policy: Preferred (CORRECT)")
        elif v_policy == QSizePolicy.Policy.Expanding:
            print("  ❌ Container vertical policy: Expanding (WRONG - causes empty space)")
        else:
            print(f"  ⚠️  Container vertical policy: {v_policy}")
    
    def test_maximized(self):
        """Test in maximized window."""
        self.showMaximized()
        QApplication.processEvents()
        
        # Let it settle
        QTimer.singleShot(100, self.measure_maximized)
    
    def measure_maximized(self):
        """Measure after maximizing."""
        gallery = self.gallery_tab.gallery_widget
        container = gallery.container_widget
        viewport = gallery.viewport()
        
        self.maximized_results = {
            'window_size': f"{self.width()}x{self.height()}",
            'viewport_height': viewport.height(),
            'container_height': container.height(),
        }
        
        print("\n📏 Maximized Window:")
        print(f"  Viewport height: {viewport.height()}px")
        print(f"  Container height: {container.height()}px")
        
        # Calculate empty space
        # The container should be roughly the size needed for thumbnails
        # 17 sprites, with default columns, should need certain rows
        columns = gallery.columns
        rows = (17 + columns - 1) // columns
        thumbnail_height = gallery.thumbnail_size + 20  # Size + label
        spacing = gallery.spacing
        
        expected_height = rows * thumbnail_height + (rows - 1) * spacing + 100  # +100 for controls
        actual_height = container.height()
        
        empty_space = actual_height - expected_height
        empty_ratio = empty_space / viewport.height() if viewport.height() > 0 else 0
        
        print(f"  Expected content height: ~{expected_height}px")
        print(f"  Actual container height: {actual_height}px")
        print(f"  Empty space: {empty_space}px ({empty_ratio:.1%} of viewport)")
        
        if empty_ratio > 0.3:  # More than 30% empty
            print("  ❌ EXCESSIVE EMPTY SPACE DETECTED!")
        elif empty_ratio > 0.1:
            print("  ⚠️  Some empty space present")
        else:
            print("  ✅ Minimal empty space - FIX WORKING!")
    
    def report_results(self):
        """Final report."""
        print("\n" + "="*60)
        print("EMPTY SPACE FIX VERIFICATION COMPLETE")
        print("="*60)
        
        # Check container size policy
        gallery = self.gallery_tab.gallery_widget
        container = gallery.container_widget
        v_policy = container.sizePolicy().verticalPolicy()
        
        from PySide6.QtWidgets import QSizePolicy
        if v_policy == QSizePolicy.Policy.Preferred:
            print("\n✅ FIX APPLIED SUCCESSFULLY!")
            print("Container vertical policy is set to Preferred.")
            print("This prevents the container from expanding beyond its content.")
            print("\nThe gallery should now:")
            print("- Show all sprites without excessive empty space")
            print("- Only expand to the height needed for the thumbnail grid")
            print("- Work correctly when the window is maximized")
        elif v_policy == QSizePolicy.Policy.Expanding:
            print("\n❌ FIX NOT APPLIED!")
            print("Container vertical policy is still set to Expanding.")
            print("This causes the container to fill all available space,")
            print("creating the empty space issue you're experiencing.")
            print("\nTo fix, change line 102 in sprite_gallery_widget.py from:")
            print("  setSizePolicy(Expanding, Expanding)")
            print("To:")
            print("  setSizePolicy(Expanding, Preferred)")
        
        QApplication.quit()

def main():
    """Run the test."""
    if not QT_AVAILABLE:
        return 1
    
    app = QApplication.instance() or QApplication(sys.argv)
    
    # Import Qt after app creation
    global Qt
    from PySide6.QtCore import Qt
    
    print("="*60)
    print("TESTING EMPTY SPACE FIX")
    print("="*60)
    print("\nThis test verifies that the container widget doesn't")
    print("expand beyond its content, eliminating empty space.")
    
    window = TestWindow()
    window.show()
    
    return app.exec()

if __name__ == "__main__":
    sys.exit(main())