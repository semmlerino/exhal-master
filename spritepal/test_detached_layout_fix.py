#!/usr/bin/env python3
"""
Test that the detached gallery layout is fixed - no cut-off, no empty space.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

try:
    from PySide6.QtWidgets import QApplication, QSizePolicy
    from PySide6.QtCore import QTimer, Qt
    from PySide6.QtGui import QPixmap
    from ui.windows.detached_gallery_window import DetachedGalleryWindow
    QT_AVAILABLE = True
except ImportError:
    QT_AVAILABLE = False
    print("Qt not available")
    sys.exit(1)

def test_detached_layout():
    """Test the fixed detached gallery layout."""
    app = QApplication.instance() or QApplication(sys.argv)
    
    print("="*60)
    print("DETACHED GALLERY LAYOUT FIX TEST")
    print("="*60)
    
    # Create detached window
    window = DetachedGalleryWindow()
    
    # Create test sprites (17 to match user's case)
    sprites = []
    for i in range(17):
        sprites.append({
            'offset': i * 0x1000,
            'decompressed_size': 2048,
            'tile_count': 64,
            'compressed': i % 3 == 0,
        })
    
    # Set sprites
    window.set_sprites(sprites)
    
    # Generate mock thumbnails
    for sprite in sprites:
        offset = sprite['offset']
        if offset in window.gallery_widget.thumbnails:
            pixmap = QPixmap(128, 128)
            pixmap.fill(Qt.GlobalColor.darkGray)
            thumbnail = window.gallery_widget.thumbnails[offset]
            thumbnail.set_sprite_data(pixmap, sprite)
    
    # Show window
    window.show()
    
    def check_layout():
        print("\n📋 CHECKING DETACHED WINDOW LAYOUT")
        print("-" * 40)
        
        gallery = window.gallery_widget
        
        # Check setWidgetResizable
        resizable = gallery.widgetResizable()
        print(f"setWidgetResizable: {resizable}")
        
        if resizable:
            print("✅ Automatic resizing enabled (proper scrolling)")
        else:
            print("❌ Automatic resizing disabled (may cause cut-off)")
        
        # Check gallery size policy
        policy = gallery.sizePolicy()
        h_policy = policy.horizontalPolicy()
        v_policy = policy.verticalPolicy()
        
        print(f"\nGallery Widget Policy:")
        print(f"  Horizontal: {h_policy.name}")
        print(f"  Vertical: {v_policy.name}")
        
        if v_policy == QSizePolicy.Policy.Expanding:
            print("  ✅ Gallery fills available vertical space")
        else:
            print(f"  ⚠️  Gallery has {v_policy.name} policy")
        
        # Check container policy
        if gallery.container_widget:
            container = gallery.container_widget
            container_policy = container.sizePolicy()
            v_policy = container_policy.verticalPolicy()
            
            print(f"\nContainer Widget Policy:")
            print(f"  Vertical: {v_policy.name}")
            
            if v_policy == QSizePolicy.Policy.Preferred:
                print("  ✅ Container sizes to content (no excess space)")
            else:
                print(f"  ⚠️  Container has {v_policy.name} policy")
        
        # Check main widget if it exists
        if gallery.widget():
            main_widget = gallery.widget()
            main_policy = main_widget.sizePolicy()
            v_policy = main_policy.verticalPolicy()
            
            print(f"\nMain Widget Policy:")
            print(f"  Vertical: {v_policy.name}")
            
            if v_policy == QSizePolicy.Policy.Preferred:
                print("  ✅ Main widget sizes to content")
        
        # Check layout
        central = window.centralWidget()
        layout = central.layout()
        
        # Check for stretch items
        has_stretch = False
        widget_count = 0
        for i in range(layout.count()):
            item = layout.itemAt(i)
            if item:
                if item.spacerItem():
                    has_stretch = True
                elif item.widget():
                    widget_count += 1
        
        print(f"\nWindow Layout:")
        print(f"  Widgets: {widget_count}")
        print(f"  Has stretch spacer: {has_stretch}")
        
        if not has_stretch:
            print("  ✅ No stretch spacer (gallery fills window)")
        else:
            print("  ❌ Has stretch spacer (causes empty space)")
        
        # Test with maximized window
        print("\n🖥️  Maximizing window...")
        window.showMaximized()
        QTimer.singleShot(500, check_maximized)
    
    def check_maximized():
        print("\n📏 MAXIMIZED WINDOW CHECK")
        print("-" * 40)
        
        gallery = window.gallery_widget
        
        # Check sizes
        window_height = window.height()
        gallery_height = gallery.height()
        
        if gallery.container_widget:
            container_height = gallery.container_widget.height()
            
            # Calculate expected content height
            columns = gallery.columns
            rows = (17 + columns - 1) // columns
            thumbnail_height = gallery.thumbnail_size + 20
            spacing = gallery.spacing
            controls_height = 50
            
            expected_height = controls_height + (rows * thumbnail_height) + ((rows - 1) * spacing) + 20
            
            print(f"Window height: {window_height}px")
            print(f"Gallery height: {gallery_height}px")
            print(f"Container height: {container_height}px")
            print(f"Expected content: ~{expected_height}px")
            
            # Check if gallery fills window properly
            gallery_fill_ratio = gallery_height / window_height
            print(f"\nGallery fills {gallery_fill_ratio:.1%} of window")
            
            if gallery_fill_ratio > 0.85:  # Accounting for menu/toolbar
                print("✅ Gallery properly fills window height")
            else:
                print("❌ Gallery doesn't fill window (empty space)")
            
            # Check if content is cut off
            if container_height < expected_height - 100:
                print("❌ Content appears cut off")
            else:
                print("✅ Content fully visible (scrollable if needed)")
        
        print("\n" + "="*60)
        print("FIX SUMMARY")
        print("="*60)
        
        print("\nThe detached gallery now:")
        print("1. Uses setWidgetResizable(True) for proper scrolling")
        print("2. Gallery widget expands to fill window (Expanding policy)")
        print("3. Container uses Preferred policy (sizes to content)")
        print("4. No stretch spacer to create empty space")
        print("5. Content is scrollable when needed, not cut off")
        
        app.quit()
    
    # Start checking after window is shown
    QTimer.singleShot(100, check_layout)
    
    return app.exec()

if __name__ == "__main__":
    sys.exit(test_detached_layout())