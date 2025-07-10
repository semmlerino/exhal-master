#!/usr/bin/env python3
"""
Debug version of the pixel editor to diagnose color issues
"""

# Standard library imports
import sys

# Third-party imports
from PyQt6.QtWidgets import QApplication

# Local imports
from indexed_pixel_editor import IndexedPixelEditor


def debug_pixel_editor():
    """Debug the pixel editor to see what's happening with colors"""

    app = QApplication(sys.argv)
    editor = IndexedPixelEditor()

    # Debug: Check palette widget colors
    print("=== Debugging Pixel Editor Colors ===")
    print("Palette widget colors:")
    for i, color in enumerate(editor.palette_widget.colors):
        print(f"  {i}: {color}")

    print(f"\nSelected color index: {editor.palette_widget.selected_index}")
    print(f"Canvas current color: {editor.canvas.current_color}")

    # Debug: Check canvas palette reference
    if editor.canvas.palette_widget:
        print("\nCanvas has palette widget: YES")
        print(
            f"Canvas palette widget colors[0]: {editor.canvas.palette_widget.colors[0]}"
        )
        print(
            f"Canvas palette widget colors[1]: {editor.canvas.palette_widget.colors[1]}"
        )
        print(
            f"Canvas palette widget colors[4]: {editor.canvas.palette_widget.colors[4]}"
        )
    else:
        print("\nCanvas has palette widget: NO - THIS IS THE PROBLEM!")

    # Check if canvas is using fallback
    print(
        f"\nCanvas image data: {editor.canvas.image_data.shape if editor.canvas.image_data is not None else 'None'}"
    )

    # Show editor
    editor.show()

    # Create a simple test drawing
    print("\n=== Creating Test Drawing ===")

    # Set different colors and draw pixels
    test_colors = [1, 4, 8, 9]  # Pink, Red, Yellow, Green

    for i, color_idx in enumerate(test_colors):
        editor.palette_widget.selected_index = color_idx
        editor.canvas.current_color = color_idx

        # Draw a pixel
        editor.canvas.draw_pixel(i + 1, 1)

        print(f"Drew pixel at ({i+1}, 1) with color index {color_idx}")

        # Check what color it should be
        expected_color = editor.palette_widget.colors[color_idx]
        print(f"  Expected color: {expected_color}")

        # Check what's actually in the canvas
        if editor.canvas.image_data is not None:
            actual_index = editor.canvas.image_data[1, i + 1]
            print(f"  Actual index in canvas: {actual_index}")

    print("\nIf you see colors other than gray/black, the palette is working!")
    print(
        "If you see only gray/black, there's still an issue with the palette rendering."
    )

    return app.exec()


if __name__ == "__main__":
    sys.exit(debug_pixel_editor())
