#!/usr/bin/env python3
"""
Diagnostic script to understand the palette index inversion issue
"""

import numpy as np
from PIL import Image

from sprite_editor.palette_utils import get_grayscale_palette, read_cgram_palette


def analyze_grayscale_image(image_path):
    """Analyze a grayscale PNG to understand index distribution"""
    print(f"\nAnalyzing: {image_path}")

    img = Image.open(image_path)
    print(f"Image mode: {img.mode}")
    print(f"Image size: {img.size}")

    if img.mode == "P":
        # Get palette
        palette = img.getpalette()
        if palette:
            print("\nPalette analysis (first 16 colors):")
            for i in range(16):
                r = palette[i*3]
                g = palette[i*3+1]
                b = palette[i*3+2]
                print(f"  Index {i}: RGB({r}, {g}, {b})")

        # Analyze pixel distribution
        pixels = np.array(img)
        unique, counts = np.unique(pixels, return_counts=True)

        print("\nPixel index distribution:")
        total_pixels = pixels.size
        for idx, count in zip(unique, counts):
            percentage = (count / total_pixels) * 100
            print(f"  Index {idx}: {count} pixels ({percentage:.2f}%)")

        # Check which index is used for background vs sprites
        print("\nAnalyzing index usage:")
        # Sample some areas to determine background
        # Top-left corner (likely background)
        corner_sample = pixels[:8, :8].flatten()
        corner_unique = np.unique(corner_sample)
        print(f"  Top-left corner uses indices: {corner_unique}")

        # Find most common index (likely background)
        most_common_idx = unique[np.argmax(counts)]
        print(f"  Most common index (likely background): {most_common_idx}")

    return img

def analyze_cgram_palette(cgram_file, palette_num):
    """Analyze a palette from CGRAM"""
    print(f"\nAnalyzing CGRAM palette {palette_num}:")

    palette = read_cgram_palette(cgram_file, palette_num)
    if palette:
        print("First 16 colors:")
        for i in range(16):
            r = palette[i*3]
            g = palette[i*3+1]
            b = palette[i*3+2]
            print(f"  Index {i}: RGB({r}, {g}, {b})")
    else:
        print("  Failed to read palette")

def test_palette_application(image_path, cgram_file, palette_num):
    """Test applying a palette to see the result"""
    print("\nTesting palette application:")

    # Load image
    img = Image.open(image_path)
    if img.mode != "P":
        print("  Image is not indexed, skipping")
        return

    # Get current palette
    current_palette = img.getpalette()
    print("  Current palette (first 3 colors):")
    for i in range(3):
        r = current_palette[i*3]
        g = current_palette[i*3+1]
        b = current_palette[i*3+2]
        print(f"    Index {i}: RGB({r}, {g}, {b})")

    # Load and apply CGRAM palette
    new_palette = read_cgram_palette(cgram_file, palette_num)
    if new_palette:
        print(f"  Applying palette {palette_num} (first 3 colors):")
        for i in range(3):
            r = new_palette[i*3]
            g = new_palette[i*3+1]
            b = new_palette[i*3+2]
            print(f"    Index {i}: RGB({r}, {g}, {b})")

        # Apply palette and save test image
        img_copy = img.copy()
        img_copy.putpalette(new_palette)
        test_output = f"test_palette_{palette_num}_applied.png"
        img_copy.save(test_output)
        print(f"  Saved test image: {test_output}")

def check_index_mapping():
    """Check how indices are being mapped"""
    print("\nChecking grayscale palette generation:")

    grayscale = get_grayscale_palette()
    print("Grayscale palette (first 16 colors):")
    for i in range(16):
        r = grayscale[i*3]
        g = grayscale[i*3+1]
        b = grayscale[i*3+2]
        print(f"  Index {i}: RGB({r}, {g}, {b})")

    print("\nExpected mapping for SNES sprites:")
    print("  Index 0: Transparent/Background (should be darkest)")
    print("  Index 1-15: Sprite colors (increasing brightness)")

def main():
    # Analyze grayscale images
    grayscale_images = [
        "Kirby_sheet.png",
        "Level_Sprites_sheet.png",
        "UI_Elements_sheet.png",
        "Effects_sheet.png"
    ]

    for img_path in grayscale_images:
        try:
            analyze_grayscale_image(img_path)
        except FileNotFoundError:
            print(f"Skipping {img_path} - not found")

    # Check grayscale palette
    check_index_mapping()

    # If CGRAM file exists, analyze some palettes
    cgram_files = ["SnesCgRam.dmp", "cgram_from_savestate.dmp", "Cave.SnesCgRam.dmp"]
    cgram_file = None
    for cf in cgram_files:
        try:
            with open(cf, "rb"):
                cgram_file = cf
                break
        except FileNotFoundError:
            continue

    if cgram_file:
        print(f"\nUsing CGRAM file: {cgram_file}")
        # Analyze a few palettes
        for pal_num in [0, 4, 7, 8]:
            analyze_cgram_palette(cgram_file, pal_num)

        # Test palette application
        if grayscale_images:
            test_palette_application(grayscale_images[0], cgram_file, 0)

if __name__ == "__main__":
    main()
