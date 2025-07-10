#!/usr/bin/env python3
"""
Test the core functionality of the indexed pixel editor
Tests loading, editing, and saving of indexed images
"""

# Standard library imports
import os
import sys

# Third-party imports
import numpy as np
from PIL import Image


# Test basic indexed image operations
def test_indexed_image_operations():
    """Test basic indexed image operations"""
    print("Testing indexed image operations...")

    # Load test image
    try:
        img = Image.open("test_smiley_8x8.png")
        print(f"✓ Loaded test image: {img.size}, mode: {img.mode}")

        if img.mode != "P":
            print("✗ Image is not in indexed mode")
            return False

        # Test pixel access
        pixels = np.array(img)
        print(f"✓ Converted to numpy array: {pixels.shape}")

        # Test pixel modification
        original_pixel = pixels[0, 0]
        pixels[0, 0] = 5  # Change to color index 5
        print(f"✓ Modified pixel: {original_pixel} -> {pixels[0, 0]}")

        # Test conversion back to PIL
        modified_img = Image.fromarray(pixels, mode="P")
        modified_img.putpalette(img.palette.palette)
        print("✓ Converted back to PIL Image")

        # Test saving
        modified_img.save("test_modified.png")
        print("✓ Saved modified image")

    except Exception as e:
        print(f"✗ Error: {e}")
        return False
    else:
        return True


def test_palette_operations():
    """Test palette operations"""
    print("\nTesting palette operations...")

    try:
        img = Image.open("test_kirby_16x16.png")

        # Extract palette
        if img.palette:
            palette_data = img.palette.palette
            colors = []
            for i in range(16):
                if i * 3 + 2 < len(palette_data):
                    r = palette_data[i * 3]
                    g = palette_data[i * 3 + 1]
                    b = palette_data[i * 3 + 2]
                    colors.append((r, g, b))
                else:
                    colors.append((0, 0, 0))

            print(f"✓ Extracted {len(colors)} colors from palette")
            print("First 8 colors:", colors[:8])

            # Test palette modification
            new_palette = []
            for color in colors:
                new_palette.extend(color)
            # Pad to 256 colors
            while len(new_palette) < 768:
                new_palette.extend([0, 0, 0])

            img.putpalette(new_palette)
            print("✓ Applied modified palette")

        else:
            print("✗ No palette found")
            return False

    except Exception as e:
        print(f"✗ Error: {e}")
        return False
    else:
        return True


def test_drawing_operations():
    """Test basic drawing operations"""
    print("\nTesting drawing operations...")

    try:
        img = Image.open("test_smiley_8x8.png")
        pixels = np.array(img)

        # Test pencil drawing
        pixels[2, 2] = 7  # Set pixel to color 7
        print("✓ Pencil drawing (single pixel)")

        # Test line drawing (simple horizontal line)
        for x in range(2, 6):
            pixels[4, x] = 8
        print("✓ Line drawing")

        # Test flood fill (simple implementation)
        def flood_fill(pixels, x, y, old_color, new_color):
            if x < 0 or x >= pixels.shape[1] or y < 0 or y >= pixels.shape[0]:
                return
            if pixels[y, x] != old_color:
                return

            pixels[y, x] = new_color
            flood_fill(pixels, x + 1, y, old_color, new_color)
            flood_fill(pixels, x - 1, y, old_color, new_color)
            flood_fill(pixels, x, y + 1, old_color, new_color)
            flood_fill(pixels, x, y - 1, old_color, new_color)

        # Fill a small area
        old_color = pixels[6, 6]
        flood_fill(pixels, 6, 6, old_color, 9)
        print("✓ Flood fill")

        # Save result
        result_img = Image.fromarray(pixels, mode="P")
        result_img.putpalette(img.palette.palette)
        result_img.save("test_drawing_result.png")
        print("✓ Saved drawing result")

    except Exception as e:
        print(f"✗ Error: {e}")
        return False
    else:
        return True


def test_format_validation():
    """Test format validation and constraints"""
    print("\nTesting format validation...")

    try:
        # Test 4bpp constraint (max 16 colors)
        img = Image.open("test_smiley_8x8.png")
        pixels = np.array(img)

        # Check if all pixels are within 0-15 range
        max_index = np.max(pixels)
        min_index = np.min(pixels)
        print(f"✓ Pixel range: {min_index} to {max_index}")

        if max_index > 15:
            print("✗ Pixel values exceed 4bpp limit (0-15)")
            return False

        # Test tile constraints (8x8 alignment)
        height, width = pixels.shape
        print(f"✓ Image size: {width}x{height}")

        if width % 8 != 0 or height % 8 != 0:
            print("⚠ Image size not aligned to 8x8 tiles")

    except Exception as e:
        print(f"✗ Error: {e}")
        return False
    else:
        return True


def main():
    """Run all tests"""
    print("=== Indexed Pixel Editor Core Tests ===\n")

    # Check if test files exist
    if not os.path.exists("test_smiley_8x8.png"):
        print("✗ test_smiley_8x8.png not found. Run create_test_sprite.py first.")
        return False

    if not os.path.exists("test_kirby_16x16.png"):
        print("✗ test_kirby_16x16.png not found. Run create_test_sprite.py first.")
        return False

    # Run tests
    tests = [
        test_indexed_image_operations,
        test_palette_operations,
        test_drawing_operations,
        test_format_validation,
    ]

    passed = 0
    failed = 0

    for test in tests:
        if test():
            passed += 1
        else:
            failed += 1

    print("\n=== Test Results ===")
    print(f"Passed: {passed}/{len(tests)}")
    print(f"Failed: {failed}/{len(tests)}")

    if failed == 0:
        print("🎉 All tests passed!")
    else:
        print("❌ Some tests failed")

    return failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
