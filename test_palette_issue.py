#!/usr/bin/env python3
"""
Test script to identify palette-related issues in the sprite editor
"""

import os
import sys

from PIL import Image

# Add sprite_editor directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "sprite_editor"))

from palette_utils import get_grayscale_palette, read_cgram_palette
from sprite_editor_core import SpriteEditorCore


def test_palette_loading():
    """Test basic palette loading functionality"""
    print("Testing palette loading functionality...")

    # Test grayscale palette
    print("\n1. Testing grayscale palette:")
    grayscale_pal = get_grayscale_palette()
    print(f"   - Grayscale palette length: {len(grayscale_pal)}")
    print("   - First 16 colors (RGB):")
    for i in range(16):
        r = grayscale_pal[i*3]
        g = grayscale_pal[i*3+1]
        b = grayscale_pal[i*3+2]
        print(f"     Color {i}: RGB({r}, {g}, {b})")

    # Test CGRAM palette loading if file exists
    cgram_files = ["SnesCgRam.dmp", "cgram_from_savestate.dmp", "mss2_CGRAM.dmp"]
    cgram_file = None
    for f in cgram_files:
        if os.path.exists(f):
            cgram_file = f
            break

    if cgram_file:
        print(f"\n2. Testing CGRAM palette from {cgram_file}:")
        for pal_num in range(4):  # Test first 4 palettes
            palette = read_cgram_palette(cgram_file, pal_num)
            if palette:
                print(f"   - Palette {pal_num} loaded successfully")
                print(f"     First color: RGB({palette[0]}, {palette[1]}, {palette[2]})")
                print(f"     Second color: RGB({palette[3]}, {palette[4]}, {palette[5]})")
            else:
                print(f"   - Palette {pal_num} failed to load")
    else:
        print("\n2. No CGRAM file found for testing")

def test_image_palette_application():
    """Test applying palettes to images"""
    print("\n\nTesting palette application to images...")

    # Create a simple test image
    print("\n1. Creating test image:")
    test_img = Image.new("P", (32, 32))

    # Create simple pattern using palette indices
    pixels = []
    for y in range(32):
        for x in range(32):
            # Create a pattern that uses different palette indices
            if (x // 8 + y // 8) % 2 == 0:
                pixels.append((x // 2) % 16)  # Use indices 0-15
            else:
                pixels.append(0)  # Black

    test_img.putdata(pixels)
    print("   - Created 32x32 indexed image")
    print(f"   - Mode: {test_img.mode}")

    # Test with grayscale palette
    print("\n2. Applying grayscale palette:")
    grayscale_pal = get_grayscale_palette()
    test_img.putpalette(grayscale_pal)

    # Verify palette was applied
    if hasattr(test_img, "palette") and test_img.palette:
        print("   - Palette applied successfully")
        print(f"   - Palette mode: {test_img.palette.mode}")

        # Save test image
        test_img.save("test_grayscale_palette.png")
        print("   - Saved test_grayscale_palette.png")
    else:
        print("   - ERROR: Palette not applied!")

def test_sprite_extraction_with_palette():
    """Test sprite extraction with palette application"""
    print("\n\nTesting sprite extraction with palettes...")

    # Look for VRAM file
    vram_files = ["vram_from_savestate.dmp", "SnesVideoRam.VRAM.dmp", "mss2_VRAM.dmp"]
    vram_file = None
    for f in vram_files:
        if os.path.exists(f):
            vram_file = f
            break

    if not vram_file:
        print("   - No VRAM file found for testing")
        return

    print(f"\n1. Extracting sprites from {vram_file}:")
    core = SpriteEditorCore()

    try:
        # Extract a small portion
        img, total_tiles = core.extract_sprites(
            vram_file=vram_file,
            offset=0x6000,  # Common sprite location
            size=0x400,     # 32 tiles
            tiles_per_row=8
        )

        print(f"   - Extracted {total_tiles} tiles")
        print(f"   - Image size: {img.size}")
        print(f"   - Image mode: {img.mode}")

        # Check if image has palette
        if hasattr(img, "palette") and img.palette:
            print("   - Image has palette")

            # Save with grayscale palette
            img.save("test_extraction_grayscale.png")
            print("   - Saved test_extraction_grayscale.png")

            # Try applying a CGRAM palette
            cgram_file = None
            for f in ["SnesCgRam.dmp", "cgram_from_savestate.dmp", "mss2_CGRAM.dmp"]:
                if os.path.exists(f):
                    cgram_file = f
                    break

            if cgram_file:
                print(f"\n2. Applying CGRAM palette from {cgram_file}:")
                palette = read_cgram_palette(cgram_file, 0)  # Try palette 0
                if palette:
                    img2 = img.copy()
                    img2.putpalette(palette)
                    img2.save("test_extraction_cgram.png")
                    print("   - Applied CGRAM palette 0")
                    print("   - Saved test_extraction_cgram.png")
                else:
                    print("   - Failed to load CGRAM palette")
        else:
            print("   - ERROR: Image has no palette!")

    except Exception as e:
        print(f"   - ERROR: {e}")
        import traceback
        traceback.print_exc()

def main():
    """Run all palette tests"""
    print("=" * 60)
    print("SPRITE EDITOR PALETTE TESTING")
    print("=" * 60)

    test_palette_loading()
    test_image_palette_application()
    test_sprite_extraction_with_palette()

    print("\n" + "=" * 60)
    print("Testing complete. Check generated PNG files.")
    print("=" * 60)

if __name__ == "__main__":
    main()
