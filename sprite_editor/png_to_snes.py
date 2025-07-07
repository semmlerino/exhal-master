#!/usr/bin/env python3
"""
Convert edited PNG sprites back to SNES 4bpp tile format
"""

import sys
from PIL import Image

def encode_4bpp_tile(tile_pixels):
    """Encode an 8x8 tile to SNES 4bpp format."""
    output = bytearray(32)  # 32 bytes per tile

    for y in range(8):
        # Bitplanes 0 and 1 (interleaved)
        bp0 = 0
        bp1 = 0
        for x in range(8):
            pixel = tile_pixels[y][x] & 0xF
            if pixel & 1:
                bp0 |= (1 << (7 - x))
            if pixel & 2:
                bp1 |= (1 << (7 - x))
        output[y * 2] = bp0
        output[y * 2 + 1] = bp1

        # Bitplanes 2 and 3 (interleaved)
        bp2 = 0
        bp3 = 0
        for x in range(8):
            pixel = tile_pixels[y][x] & 0xF
            if pixel & 4:
                bp2 |= (1 << (7 - x))
            if pixel & 8:
                bp3 |= (1 << (7 - x))
        output[16 + y * 2] = bp2
        output[16 + y * 2 + 1] = bp3

    return output

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
            # Extract 8x8 tile
            tile_pixels = []
            for y in range(8):
                row = []
                for x in range(8):
                    pixel = img.getpixel((tile_x * 8 + x, tile_y * 8 + y))
                    row.append(pixel)
                tile_pixels.append(row)

            # Encode tile
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