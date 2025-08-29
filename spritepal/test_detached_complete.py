#!/usr/bin/env python3
from __future__ import annotations

"""
Final test of the complete detached gallery solution.
Verifies both stretching fix and thumbnail copying work together.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

try:
    from PySide6.QtWidgets import QApplication, QSizePolicy
    from PySide6.QtCore import QTimer, Qt
    from PySide6.QtGui import QPixmap, QPainter, QColor
    from ui.tabs.sprite_gallery_tab import SpriteGalleryTab
    QT_AVAILABLE = True
except ImportError:
    QT_AVAILABLE = False
    print("Qt not available")
    sys.exit(1)

def test_complete_solution():
    """Test the complete detached gallery solution."""
    app = QApplication.instance() or QApplication(sys.argv)
    
    print("="*60)
    print("COMPLETE DETACHED GALLERY SOLUTION TEST")
    print("="*60)
    
    # Create gallery tab (simulating main app usage)
    gallery_tab = SpriteGalleryTab()
    
    # Setup mock data
    gallery_tab.rom_path = "test_rom.smc"
    gallery_tab.rom_size = 4 * 1024 * 1024
    
    class MockExtractor:
        def __init__(self):
            self.rom_injector = None
    
    gallery_tab.rom_extractor = MockExtractor()
    
    # Create test sprites
    sprites = []
    for i in range(17):
        sprites.append({
            'offset': i * 0x1000,
            'decompressed_size': 2048,
            'tile_count': 64,
            'compressed': i % 3 == 0,
        })
    
    gallery_tab.sprites_data = sprites
    gallery_tab.gallery_widget.set_sprites(sprites)
    
    # Generate real-looking thumbnails
    print("\n📸 Generating thumbnails in main gallery...")
    for i, sprite in enumerate(sprites):
        offset = sprite['offset']
        if offset in gallery_tab.gallery_widget.thumbnails:
            pixmap = QPixmap(128, 128)
            pixmap.fill(Qt.GlobalColor.darkGray)  # Simpler approach
            
            painter = QPainter(pixmap)
            painter.setPen(Qt.GlobalColor.white)
            painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, f"Sprite {i}")
            painter.end()
            
            thumbnail = gallery_tab.gallery_widget.thumbnails[offset]
            thumbnail.set_sprite_data(pixmap, sprite)
    
    print(f"  Generated {len(sprites)} thumbnails")
    
    # Show the tab
    gallery_tab.show()
    
    def open_detached():
        print("\n🗖 Opening detached gallery window...")
        gallery_tab._open_detached_gallery()
        
        # Check after a delay
        QTimer.singleShot(200, verify_detached)
    
    def verify_detached():
        if not gallery_tab.detached_window:
            print("❌ Detached window not created!")
            app.quit()
            return
        
        print("\n✅ VERIFICATION RESULTS:")
        print("-" * 40)
        
        detached = gallery_tab.detached_window
        detached_gallery = detached.gallery_widget
        
        # 1. Check stretching fix
        policy = detached_gallery.sizePolicy()
        v_policy = policy.verticalPolicy()
        
        print("\n1️⃣ STRETCHING FIX:")
        if v_policy == QSizePolicy.Policy.Preferred:
            print("  ✅ Gallery uses Preferred policy (won't stretch)")
        else:
            print(f"  ❌ Gallery uses {v_policy.name} policy")
        
        # Check for stretch spacer in layout
        layout = detached.centralWidget().layout()
        has_stretch = False
        for i in range(layout.count()):
            item = layout.itemAt(i)
            if item and item.spacerItem():
                has_stretch = True
                break
        
        if has_stretch:
            print("  ✅ Layout has stretch spacer (prevents expansion)")
        else:
            print("  ❌ No stretch spacer found")
        
        # 2. Check thumbnail copying
        print("\n2️⃣ THUMBNAIL COPYING:")
        
        thumbnail_count = len(detached_gallery.thumbnails)
        print(f"  Thumbnail widgets: {thumbnail_count}")
        
        valid_pixmaps = 0
        for offset, thumbnail in detached_gallery.thumbnails.items():
            if hasattr(thumbnail, 'sprite_pixmap') and thumbnail.sprite_pixmap:
                if not thumbnail.sprite_pixmap.isNull():
                    valid_pixmaps += 1
        
        print(f"  Valid pixmaps: {valid_pixmaps}")
        
        if valid_pixmaps == len(sprites):
            print("  ✅ All thumbnails copied successfully!")
        elif valid_pixmaps > 0:
            print(f"  ⚠️  Partial copy: {valid_pixmaps}/{len(sprites)}")
        else:
            print("  ❌ No thumbnails copied!")
        
        # 3. Check window independence
        print("\n3️⃣ WINDOW INDEPENDENCE:")
        
        is_window = detached.windowFlags() & Qt.WindowType.Window
        if is_window:
            print("  ✅ Opens as independent window")
        else:
            print("  ❌ Not an independent window")
        
        # Final summary
        print("\n" + "="*60)
        print("SOLUTION SUMMARY")
        print("="*60)
        
        if v_policy == QSizePolicy.Policy.Preferred and has_stretch and valid_pixmaps == len(sprites):
            print("\n🎉 COMPLETE SUCCESS!")
            print("\nThe detached gallery solution provides:")
            print("  ✅ No vertical stretching (Preferred policy + stretch spacer)")
            print("  ✅ Real thumbnails displayed (not placeholders)")
            print("  ✅ Independent window (can be maximized without issues)")
            print("\n📝 HOW TO USE:")
            print("  Click '🗖 Detach Gallery' button in the toolbar")
            print("  to open gallery in a separate, non-stretching window")
        else:
            print("\n⚠️  Some issues remain:")
            if v_policy != QSizePolicy.Policy.Preferred:
                print("  - Size policy needs adjustment")
            if not has_stretch:
                print("  - Missing stretch spacer")
            if valid_pixmaps != len(sprites):
                print("  - Thumbnail copying incomplete")
        
        app.quit()
    
    # Start the test sequence
    QTimer.singleShot(100, open_detached)
    
    return app.exec()

if __name__ == "__main__":
    sys.exit(test_complete_solution())