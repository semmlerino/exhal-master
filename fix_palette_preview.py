#!/usr/bin/env python3
"""
Debug and fix the black color preview issue in the palette widget
"""

import os
import sys

from PyQt6.QtWidgets import QApplication

from indexed_pixel_editor import IndexedPixelEditor


def debug_palette_widget():
    """Debug the palette widget color display"""
    app = QApplication(sys.argv)
    editor = IndexedPixelEditor()

    # Load test image
    test_image = "ultrathink/sprites/kirby_sprites.png"
    if os.path.exists(test_image):
        editor.load_file(test_image)

        # Check palette widget colors
        print("\n=== PALETTE WIDGET DEBUG ===")
        print(f"Number of colors: {len(editor.palette_widget.colors)}")
        print(f"First 4 colors: {editor.palette_widget.colors[:4]}")
        print(f"Is external palette: {editor.palette_widget.is_external_palette}")
        print(f"Palette source: {editor.palette_widget.palette_source}")

        # Check if colors are all black
        all_black = all(color == (0, 0, 0) for color in editor.palette_widget.colors)
        if all_black:
            print("\n⚠️  WARNING: All colors are black!")

        # Check editor's external palette
        if hasattr(editor, "external_palette_colors") and editor.external_palette_colors:
            print(f"\nEditor external palette colors: {editor.external_palette_colors[:4]}")
            print(f"Use external palette: {editor.use_external_palette}")

    editor.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    debug_palette_widget()
