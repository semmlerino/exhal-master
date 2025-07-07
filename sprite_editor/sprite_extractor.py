#!/usr/bin/env python3
"""
Kirby Super Star Sprite Extractor
Extracts sprites from VRAM dump for editing

Usage:
    python sprite_extractor.py [options]

Options:
    --vram <file>     VRAM dump file (default: VRAM.dmp)
    --offset <hex>    VRAM offset to extract from (default: 0xC000)
    --size <hex>      Number of bytes to extract (default: 0x4000)
    --output <file>   Output PNG file (default: sprites_to_edit.png)
    --width <tiles>   Tiles per row (default: 16)
    --palette <num>   Apply CGRAM palette (requires CGRAM.dmp)
"""

import argparse
import os
import sys

from PIL import Image

try:
    from palette_utils import read_cgram_palette
    from tile_utils import decode_4bpp_tile
except ImportError:
    from .palette_utils import read_cgram_palette
    from .tile_utils import decode_4bpp_tile

# Functions now imported from utility modules


def extract_sprites(vram_file, offset, size, tiles_per_row=16):
    """Extract sprites from VRAM dump."""
    try:
        # Read VRAM data
        with open(vram_file, 'rb') as f:
            f.seek(offset)
            data = f.read(size)

        # Calculate dimensions
        total_tiles = len(data) // 32
        tiles_x = tiles_per_row
        tiles_y = (total_tiles + tiles_x - 1) // tiles_x

        width = tiles_x * 8
        height = tiles_y * 8

        print(f"Extracting {total_tiles} tiles ({tiles_x}x{tiles_y})")
        print(f"Image size: {width}x{height} pixels")

        # Create indexed color image
        img = Image.new('P', (width, height))

        # Set grayscale palette by default
        palette = []
        for i in range(256):
            gray = (i * 255) // 15 if i < 16 else 0
            palette.extend([gray, gray, gray])
        img.putpalette(palette)

        # Decode all tiles
        pixels = []
        for tile_idx in range(total_tiles):
            if tile_idx * 32 + 32 <= len(data):
                tile = decode_4bpp_tile(data, tile_idx * 32)
                pixels.extend(tile)

        # Arrange tiles in image
        img_pixels = [0] * (width * height)
        for tile_idx in range(min(total_tiles, tiles_x * tiles_y)):
            tile_x = tile_idx % tiles_x
            tile_y = tile_idx // tiles_x

            for y in range(8):
                for x in range(8):
                    src_idx = tile_idx * 64 + y * 8 + x
                    dst_x = tile_x * 8 + x
                    dst_y = tile_y * 8 + y

                    if src_idx < len(
                            pixels) and dst_y < height and dst_x < width:
                        img_pixels[dst_y * width + dst_x] = pixels[src_idx]

        img.putdata(img_pixels)
        return img

    except Exception as e:
        print(f"Error extracting sprites: {e}")
        return None


def main():
    parser = argparse.ArgumentParser(
        description='Kirby Super Star Sprite Extractor')
    parser.add_argument('--vram', default='VRAM.dmp', help='VRAM dump file')
    parser.add_argument(
        '--offset',
        default='0xC000',
        help='VRAM offset in hex')
    parser.add_argument(
        '--size',
        default='0x4000',
        help='Size to extract in hex')
    parser.add_argument(
        '--output',
        default='sprites_to_edit.png',
        help='Output PNG file')
    parser.add_argument('--width', type=int, default=16, help='Tiles per row')
    parser.add_argument(
        '--palette',
        type=int,
        help='Apply CGRAM palette number')

    args = parser.parse_args()

    # Parse hex values
    offset = int(args.offset, 16)
    size = int(args.size, 16)

    print("Sprite Extractor - Kirby Super Star")
    print("===================================")
    print(f"VRAM file: {args.vram}")
    print(f"Offset: {hex(offset)} (VRAM ${hex(offset // 2)})")
    print(f"Size: {hex(size)} ({size} bytes)")
    print(f"Output: {args.output}")
    print()

    # Check VRAM file exists
    if not os.path.exists(args.vram):
        print(f"Error: VRAM file '{args.vram}' not found")
        return 1

    # Extract sprites
    print("Extracting sprites...")
    img = extract_sprites(args.vram, offset, size, args.width)
    if not img:
        return 1

    # Apply palette if requested
    if args.palette is not None:
        cgram_file = 'CGRAM.dmp'
        if os.path.exists(cgram_file):
            print(f"Applying palette {args.palette}...")
            palette = read_cgram_palette(cgram_file, args.palette)
            if palette:
                img.putpalette(palette)
        else:
            print("Warning: CGRAM.dmp not found, using grayscale")

    # Save image
    img.save(args.output)
    print(f"\nSuccess! Extracted sprites to: {args.output}")

    print("\nEditing tips:")
    print("- KEEP the image in indexed color mode (Image > Mode > Indexed)")
    print("- Use only the existing 16 colors in the palette")
    print("- Save as PNG with indexed color preserved")
    print("- Use sprite_injector.py to reinsert your edits")

    return 0


if __name__ == "__main__":
    sys.exit(main())
