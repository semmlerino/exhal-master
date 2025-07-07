#!/usr/bin/env python3
"""
Convert SNES 4bpp tile data to PNG images.
SNES 4bpp format: Each 8x8 tile is 32 bytes, stored in a planar format.
"""

import sys

from PIL import Image

try:
    from tile_utils import decode_4bpp_tile
except ImportError:
    from .tile_utils import decode_4bpp_tile

# Function now imported from tile_utils


def convert_tiles_to_image(data, width_in_tiles=16, height_in_tiles=None):
    """Convert SNES tile data to PIL Image."""
    bytes_per_tile = 32  # 4bpp = 32 bytes per 8x8 tile
    num_tiles = len(data) // bytes_per_tile

    if height_in_tiles is None:
        height_in_tiles = (num_tiles + width_in_tiles - 1) // width_in_tiles

    # Create image
    img_width = width_in_tiles * 8
    img_height = height_in_tiles * 8
    img = Image.new('P', (img_width, img_height))

    # Default palette (grayscale)
    palette = []
    for i in range(16):
        val = i * 17  # 0-255 range
        palette.extend([val, val, val])
    # Fill rest of palette
    for i in range(16, 256):
        palette.extend([0, 0, 0])
    img.putpalette(palette)

    # Decode tiles
    pixels = []
    for tile_y in range(height_in_tiles):
        for row in range(8):
            row_pixels = []
            for tile_x in range(width_in_tiles):
                tile_idx = tile_y * width_in_tiles + tile_x
                if tile_idx < num_tiles:
                    tile_offset = tile_idx * bytes_per_tile
                    tile = decode_4bpp_tile(data, tile_offset)
                    row_pixels.extend(tile[row])
                else:
                    row_pixels.extend([0] * 8)
            pixels.extend(row_pixels)

    img.putdata(pixels)
    return img


def main():
    if len(sys.argv) < 3:
        print(
            "Usage: python snes_tiles_to_png.py input.bin output.png [width_in_tiles]")
        print("Default width is 16 tiles (128 pixels)")
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2]
    width_in_tiles = int(sys.argv[3]) if len(sys.argv) > 3 else 16

    # Read input file
    with open(input_file, 'rb') as f:
        data = f.read()

    # Convert and save
    img = convert_tiles_to_image(data, width_in_tiles)
    img.save(output_file, 'PNG')

    print(
        f"Converted {
            len(data)} bytes ({
            len(data) //
            32} tiles) to {output_file}")
    print(f"Image size: {img.width}x{img.height} pixels")


if __name__ == "__main__":
    main()
