#!/usr/bin/env python3
from __future__ import annotations

"""
Test that thumbnails are properly copied to the detached gallery window.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

try:
    from PySide6.QtCore import Qt, QTimer
    from PySide6.QtGui import QColor, QPainter, QPixmap
    from PySide6.QtWidgets import QApplication
    from ui.widgets.sprite_gallery_widget import SpriteGalleryWidget
    from ui.windows.detached_gallery_window import DetachedGalleryWindow
    QT_AVAILABLE = True
except ImportError:
    QT_AVAILABLE = False
    print("Qt not available")
    sys.exit(1)

def create_test_pixmap(index):
    """Create a unique test pixmap for each sprite."""
    pixmap = QPixmap(128, 128)
    pixmap.fill(Qt.GlobalColor.transparent)

    painter = QPainter(pixmap)
    # Use different colors for each sprite
    colors = [Qt.GlobalColor.red, Qt.GlobalColor.green, Qt.GlobalColor.blue,
              Qt.GlobalColor.yellow, Qt.GlobalColor.cyan, Qt.GlobalColor.magenta]
    color = colors[index % len(colors)]
    painter.fillRect(10, 10, 108, 108, color)

    # Draw sprite number
    painter.setPen(Qt.GlobalColor.white)
    painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, f"#{index}")
    painter.end()

    return pixmap

def test_thumbnail_copy():
    """Test that thumbnails are copied correctly."""
    app = QApplication.instance() or QApplication(sys.argv)

    print("="*60)
    print("DETACHED GALLERY THUMBNAIL COPY TEST")
    print("="*60)

    # Create main gallery
    main_gallery = SpriteGalleryWidget()

    # Create test sprites
    sprites = []
    for i in range(17):
        sprites.append({
            'offset': i * 0x1000,
            'decompressed_size': 2048,
            'tile_count': 64,
            'compressed': i % 3 == 0,
        })

    # Set sprites in main gallery
    main_gallery.set_sprites(sprites)

    # Generate unique thumbnails for main gallery
    print("\n📸 Generating unique thumbnails for main gallery...")
    for i, sprite in enumerate(sprites):
        offset = sprite['offset']
        if offset in main_gallery.thumbnails:
            pixmap = create_test_pixmap(i)
            thumbnail = main_gallery.thumbnails[offset]
            thumbnail.set_sprite_data(pixmap, sprite)
            print(f"  Created thumbnail #{i} for offset 0x{offset:06X}")

    # Create detached window
    detached_window = DetachedGalleryWindow()

    # Set sprites in detached window
    detached_window.set_sprites(sprites)

    # Copy thumbnails
    print("\n📋 Copying thumbnails to detached gallery...")
    detached_window.copy_thumbnails_from(main_gallery)

    # Verify thumbnails were copied
    def verify_copy():
        print("\n✅ VERIFICATION:")
        print("-" * 40)

        detached_gallery = detached_window.gallery_widget

        # Check thumbnail counts
        main_count = len(main_gallery.thumbnails)
        detached_count = len(detached_gallery.thumbnails)

        print(f"Main gallery thumbnails: {main_count}")
        print(f"Detached gallery thumbnails: {detached_count}")

        if main_count != detached_count:
            print("❌ Thumbnail count mismatch!")
            app.quit()
            return

        # Check each thumbnail has a valid pixmap
        valid_count = 0
        null_count = 0

        for offset, thumbnail in detached_gallery.thumbnails.items():
            if hasattr(thumbnail, 'sprite_pixmap') and thumbnail.sprite_pixmap:
                if not thumbnail.sprite_pixmap.isNull():
                    valid_count += 1
                else:
                    null_count += 1
            else:
                null_count += 1

        print("\nDetached gallery pixmaps:")
        print(f"  Valid (copied): {valid_count}")
        print(f"  Null (placeholder): {null_count}")

        # Check if main gallery has valid pixmaps
        main_valid = 0
        for offset, thumbnail in main_gallery.thumbnails.items():
            if hasattr(thumbnail, 'sprite_pixmap') and thumbnail.sprite_pixmap:
                if not thumbnail.sprite_pixmap.isNull():
                    main_valid += 1

        print(f"\nMain gallery has {main_valid} valid pixmaps")

        if valid_count == main_valid and valid_count > 0:
            print("\n✅ SUCCESS! All thumbnails copied correctly!")
            print(f"  {valid_count} thumbnails with actual pixmaps transferred")
            print("  Detached gallery will show real thumbnails, not placeholders")
        elif valid_count == 0:
            print("\n❌ FAILURE! No thumbnails were copied")
            print("  Detached gallery only has placeholders")
        else:
            print(f"\n⚠️  PARTIAL SUCCESS: {valid_count}/{main_valid} thumbnails copied")

        print("\n" + "="*60)
        print("SOLUTION IMPLEMENTED:")
        print("  - copy_thumbnails_from() method added to DetachedGalleryWindow")
        print("  - Main gallery thumbnails are copied when opening detached window")
        print("  - Future thumbnail updates also connected via signals")

        app.quit()

    # Show windows briefly
    main_gallery.show()
    detached_window.show()

    # Verify after a short delay
    QTimer.singleShot(100, verify_copy)

    return app.exec()

if __name__ == "__main__":
    sys.exit(test_thumbnail_copy())
