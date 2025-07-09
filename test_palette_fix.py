#!/usr/bin/env python3
"""
Test script to verify the palette transparency fix works correctly
"""

import os

from PIL import Image

from sprite_editor.models.palette_model import PaletteModel
from sprite_editor.palette_utils import (
    apply_palette_with_transparency,
    get_grayscale_palette,
    read_cgram_palette,
)


def test_transparency_fix():
    """Test that the palette transparency fix works correctly"""

    print("Testing palette transparency fix...")

    # Test 1: Check grayscale palette
    print("\n1. Testing grayscale palette:")
    grayscale = get_grayscale_palette()
    print(f"   Index 0 color: RGB({grayscale[0]}, {grayscale[1]}, {grayscale[2]})")
    print(f"   Index 1 color: RGB({grayscale[3]}, {grayscale[4]}, {grayscale[5]})")
    print(f"   Index 15 color: RGB({grayscale[45]}, {grayscale[46]}, {grayscale[47]})")

    # Test 2: Load a test image
    test_images = ["Kirby_sheet.png", "Level_Sprites_sheet.png"]
    test_image = None
    for img_name in test_images:
        if os.path.exists(img_name):
            test_image = img_name
            break

    if not test_image:
        print("No test image found")
        return

    print(f"\n2. Loading test image: {test_image}")
    img = Image.open(test_image)
    print(f"   Image mode: {img.mode}")
    print(f"   Image size: {img.size}")

    # Test 3: Apply color palette with transparency
    cgram_files = ["SnesCgRam.dmp", "cgram_from_savestate.dmp", "Cave.SnesCgRam.dmp"]
    cgram_file = None
    for cf in cgram_files:
        if os.path.exists(cf):
            cgram_file = cf
            break

    if cgram_file:
        print(f"\n3. Testing color palette application with {cgram_file}")

        # Load a palette
        palette = read_cgram_palette(cgram_file, 8)  # Kirby's palette
        if palette:
            print(f"   Original palette index 0: RGB({palette[0]}, {palette[1]}, {palette[2]})")

            # Apply with transparency handling
            modified_palette = apply_palette_with_transparency(palette)
            print(f"   Modified palette index 0: RGB({modified_palette[0]}, {modified_palette[1]}, {modified_palette[2]})")

            # Apply to image
            img_copy = img.copy()
            img_copy.putpalette(modified_palette)
            img_copy.save("test_transparency_fixed.png")
            print("   Saved test image: test_transparency_fixed.png")

            # Also test with PaletteModel
            print("\n4. Testing PaletteModel integration:")
            model = PaletteModel()
            model._palettes = [palette]  # Add test palette

            img_copy2 = img.copy()
            success = model.apply_palette_to_image(img_copy2, 0)
            if success:
                img_copy2.save("test_model_fixed.png")
                print("   Saved model test image: test_model_fixed.png")
            else:
                print("   Failed to apply palette through model")

    print("\nTest complete! Check the generated images to verify:")
    print("- Background (index 0) should appear as light gray (240,240,240)")
    print("- Sprites should have proper colors")
    print("- No more inverted/negative appearance")

if __name__ == "__main__":
    test_transparency_fix()
