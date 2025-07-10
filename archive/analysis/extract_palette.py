#!/usr/bin/env python3
"""
Extract and apply SNES palettes to sprite images
"""

import struct
import sys

from PIL import Image


def read_snes_palette(data, offset, num_colors=16):
    """Read SNES BGR555 palette data."""
    palette = []
    for i in range(num_colors):
        if offset + i*2 < len(data):
            color = struct.unpack_from("<H", data, offset + i*2)[0]
            # BGR555 to RGB888
            b = ((color >> 10) & 0x1F) << 3
            g = ((color >> 5) & 0x1F) << 3
            r = (color & 0x1F) << 3
            palette.extend([r, g, b])
        else:
            palette.extend([0, 0, 0])
    return palette

def apply_kirby_palette(img):
    """Apply a typical Kirby pink palette."""
    # Approximate Kirby palette based on common values
    palette = []
    # First 16 colors for Kirby sprites
    kirby_colors = [
        (0, 0, 0),        # 0: Transparent/black
        (248, 184, 248),  # 1: Light pink (highlight)
        (248, 152, 248),  # 2: Pink
        (240, 96, 176),   # 3: Dark pink
        (168, 0, 88),     # 4: Deep red/outline
        (248, 248, 248),  # 5: White
        (208, 208, 208),  # 6: Light gray
        (144, 144, 144),  # 7: Gray
        (80, 80, 80),     # 8: Dark gray
        (248, 0, 0),      # 9: Red (cheeks)
        (248, 216, 0),    # A: Yellow
        (0, 152, 248),    # B: Blue (feet)
        (248, 152, 0),    # C: Orange
        (0, 248, 0),      # D: Green
        (184, 0, 184),    # E: Purple
        (248, 248, 0),    # F: Bright yellow
    ]

    for r, g, b in kirby_colors:
        palette.extend([r, g, b])

    # Fill rest of palette
    for _i in range(16, 256):
        palette.extend([0, 0, 0])

    img.putpalette(palette)
    return img

def main():
    if len(sys.argv) < 3:
        print("Usage: python extract_palette.py input.png output.png")
        print("Applies a typical Kirby color palette to grayscale sprites")
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2]

    # Load image
    img = Image.open(input_file)

    # Apply Kirby palette
    img = apply_kirby_palette(img)
    img.save(output_file)

    print(f"Applied Kirby palette to {output_file}")

if __name__ == "__main__":
    main()
