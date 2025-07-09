#!/usr/bin/env python3
"""
Test script for greyscale mode functionality
"""

import sys

from PIL import Image
from PyQt6.QtWidgets import QApplication

from indexed_pixel_editor import ColorPaletteWidget, PixelCanvas


def test_greyscale_mode():
    """Test greyscale mode functionality"""
    print("🎨 Testing Greyscale Mode Functionality")

    # Create QApplication for Qt widgets
    QApplication(sys.argv)

    # Create a palette widget with colors
    palette_widget = ColorPaletteWidget()
    print(f"[TEST] Created palette widget with {len(palette_widget.colors)} colors")
    print(f"[TEST] First few colors: {palette_widget.colors[:4]}")

    # Create a canvas with the palette
    canvas = PixelCanvas(palette_widget)
    print(f"[TEST] Created canvas with greyscale_mode={canvas.greyscale_mode}")

    # Create a simple test image
    canvas.new_image(8, 8)
    print("[TEST] Created 8x8 image")

    # Draw some pixels with different colors
    test_pixels = [
        (2, 2, 1),  # Kirby pink
        (3, 3, 4),  # Red
        (4, 4, 8),  # Yellow
        (5, 5, 9),  # Green
        (6, 6, 5),  # Blue
    ]

    for x, y, color in test_pixels:
        canvas.current_color = color
        canvas.draw_pixel(x, y)

    print(f"[TEST] Drew {len(test_pixels)} test pixels")

    # Test color mode
    print("\n--- Testing Color Mode ---")
    canvas.greyscale_mode = False
    color_img = canvas.get_pil_image()
    if color_img:
        color_img.save("test_color_mode.png")
        print("✓ Saved test_color_mode.png")
    else:
        print("✗ Failed to get color image")

    # Test greyscale mode
    print("\n--- Testing Greyscale Mode ---")
    canvas.greyscale_mode = True
    grey_img = canvas.get_pil_image()
    if grey_img:
        grey_img.save("test_greyscale_mode.png")
        print("✓ Saved test_greyscale_mode.png")
    else:
        print("✗ Failed to get greyscale image")

    # Test preview functionality
    print("\n--- Testing Color Preview ---")
    canvas.greyscale_mode = True  # Enable greyscale mode

    # Simulate get_color_preview_image functionality
    if canvas.image_data is not None:
        # Create indexed image
        img = Image.fromarray(canvas.image_data, mode="P")

        # Set palette using the actual palette colors
        palette = []
        for color in palette_widget.colors:
            palette.extend(color)

        # Pad to 256 colors
        while len(palette) < 768:
            palette.extend([0, 0, 0])

        img.putpalette(palette)
        img.save("test_color_preview.png")
        print("✓ Saved test_color_preview.png")
    else:
        print("✗ No image data for color preview")

    # Analyze the results
    print("\n--- Analysis ---")
    try:
        # Check if files were created
        color_img = Image.open("test_color_mode.png")
        grey_img = Image.open("test_greyscale_mode.png")
        preview_img = Image.open("test_color_preview.png")

        print(f"Color mode image: {color_img.size} {color_img.mode}")
        print(f"Greyscale mode image: {grey_img.size} {grey_img.mode}")
        print(f"Color preview image: {preview_img.size} {preview_img.mode}")

        # Check pixel values
        print(f"Color mode pixel at (2,2): {color_img.getpixel((2, 2))}")
        print(f"Greyscale mode pixel at (2,2): {grey_img.getpixel((2, 2))}")
        print(f"Color preview pixel at (2,2): {preview_img.getpixel((2, 2))}")

        print("\n✅ Greyscale mode test completed successfully!")
        return True

    except Exception as e:
        print(f"✗ Error analyzing results: {e}")
        return False

if __name__ == "__main__":
    success = test_greyscale_mode()
    sys.exit(0 if success else 1)
