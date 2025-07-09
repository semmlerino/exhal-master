#!/usr/bin/env python3
"""
Fix grayscale PNG files to have proper grayscale palettes
"""

import sys

import numpy as np
from PIL import Image


def fix_grayscale_palette(input_file, output_file):
    """Fix a grayscale PNG to have a proper grayscale palette"""
    print(f"\nFixing grayscale palette for: {input_file}")

    # Open the image
    img = Image.open(input_file)

    if img.mode != "P":
        print(f"Image is not in palette mode (mode: {img.mode})")
        return False

    # Get the pixel data
    pixels = np.array(img)

    # Find unique pixel values
    unique_values = np.unique(pixels)
    print(f"Unique pixel values in image: {unique_values}")

    # Create a proper grayscale palette
    # We'll use the same mapping as in extract_grayscale_sheet.py
    gray_levels = {}
    gray_levels[0] = 0  # Transparent
    for i in range(1, 16):
        # Map indices 1-15 to gray values 17-255 (evenly spaced)
        gray_levels[i] = int(17 + (i-1) * (255-17) / 14)

    # Create full 256-color palette
    palette_data = []
    for i in range(256):
        if i < 16:
            # Use our grayscale mapping for first 16 colors
            gray = gray_levels.get(i, 0)
            palette_data.extend([gray, gray, gray])
        else:
            # Rest of palette is black
            palette_data.extend([0, 0, 0])

    # Apply the fixed palette
    img.putpalette(palette_data)

    # Save with the fixed palette
    img.save(output_file)

    print(f"Fixed grayscale palette saved to: {output_file}")
    print("\nGrayscale mapping (index -> gray value):")
    for idx in range(16):
        gray = gray_levels.get(idx, 0)
        print(f"  Index {idx:2d}: {gray:3d} {'(transparent)' if idx == 0 else ''}")

    return True

def main():
    """Fix grayscale palettes in common sprite sheets"""
    files_to_fix = [
        ("kirby_sprites_grayscale_fixed.png", "kirby_sprites_grayscale_fixed_v2.png"),
        ("kirby_sprites_grayscale_ultrathink.png", "kirby_sprites_grayscale_ultrathink_v2.png"),
        ("test_grayscale_palette.png", "test_grayscale_palette_v2.png"),
    ]

    for input_file, output_file in files_to_fix:
        try:
            fix_grayscale_palette(input_file, output_file)
        except FileNotFoundError:
            print(f"File not found: {input_file}")
        except Exception as e:
            print(f"Error processing {input_file}: {e}")

    # Also handle command-line arguments
    if len(sys.argv) > 1:
        input_file = sys.argv[1]
        output_file = sys.argv[2] if len(sys.argv) > 2 else input_file.replace(".png", "_fixed.png")
        fix_grayscale_palette(input_file, output_file)

if __name__ == "__main__":
    main()
