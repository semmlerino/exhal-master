#!/usr/bin/env python3
"""
Convert edited PNG sprites back to SNES 4bpp tile format
"""

import sys

from PIL import Image

try:
    from tile_utils import encode_4bpp_tile
except ImportError:
    from .tile_utils import encode_4bpp_tile


def png_to_snes(input_file, output_file):
    """Convert PNG to SNES 4bpp tile data."""
    img = Image.open(input_file)

    # Ensure it's in indexed color mode
    if img.mode != 'P':
        print("Converting to indexed color mode...")
        img = img.convert('P', palette=Image.ADAPTIVE, colors=16)

    width, height = img.size
    tiles_x = width // 8
    tiles_y = height // 8

    print(f"Converting {tiles_x}x{tiles_y} tiles ({tiles_x * tiles_y} total)")

    output_data = bytearray()

    # Process each tile
    for tile_y in range(tiles_y):
        for tile_x in range(tiles_x):
            # Extract 8x8 tile (1D format for canonical encode_4bpp_tile)
            tile_pixels = []
            for y in range(8):
                for x in range(8):
                    pixel = img.getpixel((tile_x * 8 + x, tile_y * 8 + y))
                    tile_pixels.append(pixel & 0xF)  # Ensure 4-bit value

            # Encode tile using canonical function
            tile_data = encode_4bpp_tile(tile_pixels)
            output_data.extend(tile_data)

    # Write output
    with open(output_file, 'wb') as f:
        f.write(output_data)

    print(f"Wrote {len(output_data)} bytes to {output_file}")
    return len(output_data)


def main():
    if len(sys.argv) < 3:
        print("Usage: python png_to_snes.py input.png output.bin")
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2]

    png_to_snes(input_file, output_file)


if __name__ == "__main__":
    main()
