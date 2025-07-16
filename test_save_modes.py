#!/usr/bin/env python3
"""
Test the new save modes in the pixel editor
"""

import os
import sys

from PIL import Image


def test_save_modes():
    """Test both grayscale and color save modes"""

    print("Testing Pixel Editor Save Modes")
    print("=" * 50)

    # Test file
    test_sprite = "kirby_test_sprites/kirby_small.png"

    if not os.path.exists(test_sprite):
        print(f"Error: Test sprite '{test_sprite}' not found!")
        print("Please run create_multiple_kirby_sprites.py first")
        return 1

    print(f"\nTest sprite: {test_sprite}")

    # Instructions for manual testing
    print("\nManual Testing Instructions:")
    print("-" * 50)
    print("1. Launch the pixel editor:")
    print(f"   python launch_pixel_editor.py {test_sprite}")
    print()
    print("2. Make a small edit (draw a pixel)")
    print()
    print("3. Test GRAYSCALE save (default):")
    print("   - File > Save As... > save as 'test_grayscale.png'")
    print("   - This should save as indexed grayscale")
    print()
    print("4. Test COLOR save:")
    print("   - File > Save with Color Palette... > save as 'test_color.png'")
    print("   - This should save with the color palette applied")
    print()
    print("5. Close the editor and run this script again to verify")
    print()

    # Check if test files exist
    if os.path.exists("test_grayscale.png") and os.path.exists("test_color.png"):
        print("\nVerifying saved files...")
        print("-" * 50)

        # Check grayscale file
        img_gray = Image.open("test_grayscale.png")
        print("\ntest_grayscale.png:")
        print(f"  Mode: {img_gray.mode}")
        print(f"  Size: {img_gray.size}")

        if img_gray.mode == "P":
            # Get palette
            palette = img_gray.getpalette()
            if palette:
                # Check if it's grayscale
                is_grayscale = True
                for i in range(16):
                    r = palette[i * 3]
                    g = palette[i * 3 + 1]
                    b = palette[i * 3 + 2]
                    if r != g or g != b:
                        is_grayscale = False
                        break
                print(f"  Grayscale palette: {'YES' if is_grayscale else 'NO'}")

                # Show first few colors
                print("  First 4 colors:")
                for i in range(4):
                    r = palette[i * 3]
                    g = palette[i * 3 + 1]
                    b = palette[i * 3 + 2]
                    print(f"    Index {i}: RGB({r},{g},{b})")

        # Check color file
        img_color = Image.open("test_color.png")
        print("\ntest_color.png:")
        print(f"  Mode: {img_color.mode}")
        print(f"  Size: {img_color.size}")

        if img_color.mode == "P":
            # Get palette
            palette = img_color.getpalette()
            if palette:
                # Check if it's NOT grayscale
                is_grayscale = True
                for i in range(16):
                    r = palette[i * 3]
                    g = palette[i * 3 + 1]
                    b = palette[i * 3 + 2]
                    if r != g or g != b:
                        is_grayscale = False
                        break
                print(f"  Grayscale palette: {'YES' if is_grayscale else 'NO'}")

                # Show first few colors
                print("  First 4 colors:")
                for i in range(4):
                    r = palette[i * 3]
                    g = palette[i * 3 + 1]
                    b = palette[i * 3 + 2]
                    print(f"    Index {i}: RGB({r},{g},{b})")

        print("\n✅ Test complete! Check if:")
        print("  - test_grayscale.png has grayscale palette")
        print("  - test_color.png has color palette")

    return 0


if __name__ == "__main__":
    sys.exit(test_save_modes())
