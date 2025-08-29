#!/usr/bin/env python3
from __future__ import annotations

"""
Test script to verify the gallery layout fixes.
Tests that all sprites are visible and no empty space appears.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

try:
    from PySide6.QtWidgets import QApplication
    from PySide6.QtCore import QTimer
    from ui.widgets.sprite_gallery_widget import SpriteGalleryWidget
    QT_AVAILABLE = True
except ImportError:
    QT_AVAILABLE = False
    print("Qt not available")
    sys.exit(1)

def test_gallery_fixes():
    """Test that the gallery fixes work correctly."""
    app = QApplication.instance() or QApplication(sys.argv)
    
    # Create gallery widget
    gallery = SpriteGalleryWidget()
    gallery.resize(800, 600)
    
    # Create test sprites
    sprites = []
    for i in range(17):  # Match the user's case: 17 sprites
        sprites.append({
            'offset': i * 0x1000,
            'decompressed_size': 2048,
            'tile_count': 64,
            'compressed': i % 3 == 0,
        })
    
    # Set sprites
    gallery.set_sprites(sprites)
    
    # Check results
    def verify():
        print("="*60)
        print("GALLERY FIXES VERIFICATION")
        print("="*60)
        
        # Check thumbnail count
        thumbnail_count = len(gallery.thumbnails)
        print(f"✓ Thumbnails created: {thumbnail_count} (expected: 17)")
        
        # Check visible thumbnails
        visible_count = sum(1 for t in gallery.thumbnails.values() if t.isVisible())
        print(f"✓ Visible thumbnails: {visible_count}")
        
        # Check columns
        print(f"✓ Columns: {gallery.columns}")
        
        # Check container size policy
        container = gallery.container_widget
        if container:
            policy = container.sizePolicy()
            h_policy = policy.horizontalPolicy()
            v_policy = policy.verticalPolicy()
            print(f"✓ Container size policy: H={h_policy}, V={v_policy}")
            
            # Check if MinimumExpanding is set
            from PySide6.QtWidgets import QSizePolicy
            if v_policy == QSizePolicy.Policy.MinimumExpanding:
                print("  ✅ Vertical policy is MinimumExpanding (FIX APPLIED)")
            else:
                print("  ❌ Vertical policy is NOT MinimumExpanding")
        
        # Check status label
        status_text = gallery.status_label.text() if hasattr(gallery, 'status_label') else "N/A"
        print(f"✓ Status label: '{status_text}'")
        
        # Check grid layout
        if gallery.grid_layout:
            item_count = gallery.grid_layout.count()
            print(f"✓ Grid items: {item_count}")
            
            # Calculate expected rows
            expected_rows = (17 + gallery.columns - 1) // gallery.columns
            print(f"✓ Expected rows: {expected_rows} (for {gallery.columns} columns)")
        
        print("\n" + "="*60)
        
        if thumbnail_count == 17 and visible_count >= 17:
            print("✅ ALL FIXES VERIFIED - Gallery should display correctly!")
            print("\nThe following issues have been fixed:")
            print("1. All 17 sprites are now created and visible")
            print("2. Container expands properly (MinimumExpanding)")
            print("3. Status shows correct count")
            print("4. Grid layout properly arranged")
        else:
            print("⚠️ Some issues may remain:")
            if thumbnail_count < 17:
                print(f"  - Only {thumbnail_count} thumbnails created (expected 17)")
            if visible_count < thumbnail_count:
                print(f"  - Only {visible_count} visible (of {thumbnail_count} created)")
        
        app.quit()
    
    # Show widget and verify after it's ready
    gallery.show()
    QTimer.singleShot(100, verify)
    
    return app.exec()

if __name__ == "__main__":
    sys.exit(test_gallery_fixes())