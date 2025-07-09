#!/usr/bin/env python3
"""
Extract all palettes from CGRAM dump and apply to sprites
"""

import struct
import sys

from PIL import Image


def read_cgram_palettes(cgram_file):
    """Read all 16 palettes from CGRAM dump."""
    with open(cgram_file, "rb") as f:
        cgram_data = f.read()

    palettes = []
    # CGRAM has 16 palettes of 16 colors each
    for pal_num in range(16):
        palette = []
        for color_num in range(16):
            offset = (pal_num * 16 + color_num) * 2
            if offset < len(cgram_data):
                # Read BGR555 color
                color_word = struct.unpack_from("<H", cgram_data, offset)[0]
                # Convert BGR555 to RGB888
                b = ((color_word >> 10) & 0x1F) << 3
                g = ((color_word >> 5) & 0x1F) << 3
                r = (color_word & 0x1F) << 3
                palette.extend([r, g, b])
            else:
                palette.extend([0, 0, 0])
        palettes.append(palette)

    return palettes


def apply_palette(img, palette_num, palettes):
    """Apply a specific palette to an image."""
    if palette_num >= len(palettes):
        return img

    full_palette = []
    # Use the selected palette
    full_palette.extend(palettes[palette_num])
    # Fill rest with black
    for _i in range(16, 256):
        full_palette.extend([0, 0, 0])

    img.putpalette(full_palette)
    return img


def main():
    if len(sys.argv) < 4:
        print("Usage: python extract_all_palettes.py CGRAM.dmp input.png palette_num")
        print("Palette numbers: 0-15")
        sys.exit(1)

    cgram_file = sys.argv[1]
    input_file = sys.argv[2]
    palette_num = int(sys.argv[3])

    # Read all palettes
    palettes = read_cgram_palettes(cgram_file)

    # Load image
    img = Image.open(input_file)

    # Apply selected palette
    img = apply_palette(img, palette_num, palettes)

    # Save with palette number in filename
    output_file = input_file.replace(".png", f"_pal{palette_num}.png")
    img.save(output_file)

    print(f"Applied palette {palette_num} to {output_file}")

    # Also save a preview of all palettes
    if palette_num == 0:
        print("\nPalette preview (first 8 colors of each):")
        for i, pal in enumerate(palettes[:8]):
            colors = []
            for j in range(0, 24, 3):
                colors.append(f"({pal[j]:3},{pal[j + 1]:3},{pal[j + 2]:3})")
            print(f"Palette {i}: {' '.join(colors[:4])}")


if __name__ == "__main__":
    main()
