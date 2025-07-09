#!/usr/bin/env python3
"""
Test color palette functionality to ensure indexed colors work properly
"""

import os
import sys

import numpy as np
from PIL import Image


def test_palette_colors():
    """Test that indexed colors map to proper palette colors"""
    print("=== Testing Palette Color Mapping ===\n")

    # Create a simple test image with various color indices
    width, height = 4, 4
    img = Image.new("P", (width, height))

    # Create a colorful palette
    palette = []
    test_colors = [
        (0, 0, 0),        # 0 - Black
        (255, 183, 197),  # 1 - Kirby pink
        (255, 255, 255),  # 2 - White
        (64, 64, 64),     # 3 - Dark gray
        (255, 0, 0),      # 4 - Red
        (0, 0, 255),      # 5 - Blue
        (255, 220, 220),  # 6 - Light pink
        (200, 120, 150),  # 7 - Dark pink
        (255, 255, 0),    # 8 - Yellow
        (0, 255, 0),      # 9 - Green
        (255, 128, 0),    # 10 - Orange
        (128, 0, 255),    # 11 - Purple
        (0, 128, 128),    # 12 - Teal
        (128, 128, 0),    # 13 - Olive
        (192, 192, 192),  # 14 - Light gray
        (128, 128, 128),  # 15 - Medium gray
    ]

    for color in test_colors:
        palette.extend(color)

    # Pad to 256 colors
    while len(palette) < 768:
        palette.extend([0, 0, 0])

    img.putpalette(palette)

    # Create a pattern with different color indices
    pattern = [
        [0, 1, 2, 3],  # Black, Pink, White, Gray
        [4, 5, 6, 7],  # Red, Blue, Light Pink, Dark Pink
        [8, 9, 10, 11], # Yellow, Green, Orange, Purple
        [12, 13, 14, 15] # Teal, Olive, Light Gray, Medium Gray
    ]

    # Set pixel data
    pixels = []
    for row in pattern:
        pixels.extend(row)

    img.putdata(pixels)

    # Save test image
    img.save("test_palette_colors.png")
    print("✓ Created test_palette_colors.png with indexed colors")

    # Verify the image can be loaded and colors are correct
    loaded_img = Image.open("test_palette_colors.png")

    if loaded_img.mode != "P":
        print("✗ Image is not in palette mode")
        return False

    # Check pixel values
    pixel_array = np.array(loaded_img)
    print(f"✓ Loaded image: {pixel_array.shape}")
    print(f"✓ Pixel values:\n{pixel_array}")

    # Check that pixels have the expected indices
    expected_indices = np.array(pattern)
    if np.array_equal(pixel_array, expected_indices):
        print("✓ Pixel indices match expected pattern")
    else:
        print("✗ Pixel indices don't match expected pattern")
        return False

    # Check palette extraction
    if loaded_img.palette:
        palette_data = loaded_img.palette.palette
        extracted_colors = []
        for i in range(16):
            if i * 3 + 2 < len(palette_data):
                r = palette_data[i * 3]
                g = palette_data[i * 3 + 1]
                b = palette_data[i * 3 + 2]
                extracted_colors.append((r, g, b))
            else:
                extracted_colors.append((0, 0, 0))

        print("✓ Extracted palette colors:")
        for i, color in enumerate(extracted_colors):
            print(f"  {i}: {color}")

        # Verify some key colors
        if extracted_colors[1] == (255, 183, 197):  # Kirby pink
            print("✓ Kirby pink color (index 1) is correct")
        else:
            print(f"✗ Kirby pink color is wrong: {extracted_colors[1]}")
            return False

        if extracted_colors[4] == (255, 0, 0):  # Red
            print("✓ Red color (index 4) is correct")
        else:
            print(f"✗ Red color is wrong: {extracted_colors[4]}")
            return False

        if extracted_colors[8] == (255, 255, 0):  # Yellow
            print("✓ Yellow color (index 8) is correct")
        else:
            print(f"✗ Yellow color is wrong: {extracted_colors[8]}")
            return False
    else:
        print("✗ No palette found in loaded image")
        return False

    print("\n✅ All palette tests passed!")
    return True

def test_editor_integration():
    """Test that the editor components work with the palette correctly"""
    print("\n=== Testing Editor Integration ===\n")

    # Check if we can run GUI tests
    if os.name != "nt" and "DISPLAY" not in os.environ and "WAYLAND_DISPLAY" not in os.environ:
        print("⚠ No display available, skipping GUI tests")
        return True

    # Import our palette widget
    try:
        from PyQt6.QtWidgets import QApplication

        from indexed_pixel_editor import ColorPaletteWidget

        # Create QApplication for GUI components with offscreen mode
        QApplication([])

        # Try to use offscreen mode for headless testing
        try:
            from PyQt6.QtGui import QGuiApplication
            QGuiApplication.setAttribute(Qt.ApplicationAttribute.AA_DisableWindowContextHelpButton)
        except:
            pass

        # Create palette widget
        palette_widget = ColorPaletteWidget()

        # Check that it has proper colors (not all black)
        print("✓ Palette widget created")
        print(f"✓ Color 0: {palette_widget.colors[0]} (should be black)")
        print(f"✓ Color 1: {palette_widget.colors[1]} (should be Kirby pink)")
        print(f"✓ Color 4: {palette_widget.colors[4]} (should be red)")
        print(f"✓ Color 8: {palette_widget.colors[8]} (should be yellow)")

        # Verify colors are not all the same
        unique_colors = set(palette_widget.colors)
        if len(unique_colors) > 1:
            print(f"✓ Palette has {len(unique_colors)} unique colors")
        else:
            print(f"✗ Palette has only {len(unique_colors)} unique color(s)")
            return False

        # Check specific colors
        if palette_widget.colors[1] == (255, 183, 197):
            print("✓ Kirby pink is correct in palette widget")
        else:
            print(f"✗ Kirby pink is wrong: {palette_widget.colors[1]}")
            return False

        # Check selected index
        if palette_widget.selected_index == 1:
            print("✓ Default selection is index 1 (Kirby pink)")
        else:
            print(f"✗ Default selection is wrong: {palette_widget.selected_index}")
            return False

        print("\n✅ Editor integration tests passed!")
        return True

    except ImportError as e:
        print(f"✗ Could not import editor components: {e}")
        return False
    except Exception as e:
        print(f"✗ Error testing editor integration: {e}")
        return False

def main():
    """Run all color palette tests"""
    print("Testing indexed color palette functionality...\n")

    success = True

    # Test basic palette functionality
    if not test_palette_colors():
        success = False

    # Test editor integration
    if not test_editor_integration():
        success = False

    if success:
        print("\n🎉 All color palette tests passed!")
        print("\nThe indexed pixel editor should now draw with proper colors!")
        print("- Index 0: Black (transparent)")
        print("- Index 1: Kirby pink (default selection)")
        print("- Index 4: Red")
        print("- Index 8: Yellow")
        print("- Index 9: Green")
        print("- etc...")
    else:
        print("\n❌ Some tests failed")

    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())
