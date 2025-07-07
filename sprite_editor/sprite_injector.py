#!/usr/bin/env python3
"""
Kirby Super Star Sprite Injector
Automates the process of converting edited PNG sprites and injecting them into VRAM

Usage:
    python sprite_injector.py <edited_png> [options]

Options:
    --vram <file>     VRAM dump file (default: VRAM.dmp)
    --offset <hex>    VRAM offset to inject at (default: 0xC000 for $6000)
    --output <file>   Output VRAM file (default: VRAM_edited.dmp)
    --preview         Generate preview images with palettes
"""

import sys
import os
import argparse
from PIL import Image
try:
    from tile_utils import encode_4bpp_tile, decode_4bpp_tile
    from palette_utils import read_cgram_palette
except ImportError:
    from .tile_utils import encode_4bpp_tile, decode_4bpp_tile
    from .palette_utils import read_cgram_palette

# Functions now imported from utility modules

def png_to_snes(png_file):
    """Convert PNG to SNES 4bpp tile data."""
    try:
        img = Image.open(png_file)

        # Ensure indexed color mode
        if img.mode != 'P':
            print(f"Warning: Image is in {img.mode} mode, converting to indexed...")
            img = img.convert('P', palette=Image.ADAPTIVE, colors=16)

        width, height = img.size
        tiles_x = width // 8
        tiles_y = height // 8
        total_tiles = tiles_x * tiles_y

        print(f"Converting {tiles_x}x{tiles_y} tiles ({total_tiles} total)")

        # Convert to raw pixel data
        pixels = list(img.getdata())

        # Process tiles
        output_data = bytearray()

        for tile_y in range(tiles_y):
            for tile_x in range(tiles_x):
                # Extract 8x8 tile
                tile_pixels = []
                for y in range(8):
                    for x in range(8):
                        pixel_x = tile_x * 8 + x
                        pixel_y = tile_y * 8 + y
                        pixel_index = pixel_y * width + pixel_x

                        if pixel_index < len(pixels):
                            tile_pixels.append(pixels[pixel_index] & 0x0F)
                        else:
                            tile_pixels.append(0)

                # Encode tile
                tile_data = encode_4bpp_tile(tile_pixels)
                output_data.extend(tile_data)

        return bytes(output_data)

    except Exception as e:
        print(f"Error converting PNG: {e}")
        return None

def inject_into_vram(tile_data, vram_file, offset, output_file):
    """Inject tile data into VRAM dump at specified offset."""
    try:
        # Read original VRAM
        with open(vram_file, 'rb') as f:
            vram_data = bytearray(f.read())

        # Validate offset
        if offset + len(tile_data) > len(vram_data):
            print(f"Error: Tile data ({len(tile_data)} bytes) would exceed VRAM size at offset {hex(offset)}")
            return False

        # Inject tile data
        vram_data[offset:offset + len(tile_data)] = tile_data

        # Write modified VRAM
        with open(output_file, 'wb') as f:
            f.write(vram_data)

        print(f"Injected {len(tile_data)} bytes at offset {hex(offset)}")
        print(f"Created: {output_file}")
        return True

    except Exception as e:
        print(f"Error injecting into VRAM: {e}")
        return False

# decode_4bpp_tile is now imported from tile_utils

def create_preview(vram_file, offset, size, output_png):
    """Create a preview PNG of the injected sprites."""
    try:
        with open(vram_file, 'rb') as f:
            f.seek(offset)
            data = f.read(size)

        # Calculate dimensions
        tiles = len(data) // 32
        tiles_x = 16  # 16 tiles wide
        tiles_y = (tiles + tiles_x - 1) // tiles_x

        width = tiles_x * 8
        height = tiles_y * 8

        # Create image
        img = Image.new('P', (width, height))

        # Set grayscale palette
        palette = []
        for i in range(256):
            gray = (i * 255) // 15 if i < 16 else 0
            palette.extend([gray, gray, gray])
        img.putpalette(palette)

        # Decode tiles
        pixels = []
        for tile_idx in range(tiles):
            if tile_idx * 32 + 32 <= len(data):
                tile = decode_4bpp_tile(data, tile_idx * 32)
                pixels.extend(tile)

        # Arrange in image
        img_pixels = [0] * (width * height)
        for tile_idx in range(min(tiles, tiles_x * tiles_y)):
            tile_x = tile_idx % tiles_x
            tile_y = tile_idx // tiles_x

            for y in range(8):
                for x in range(8):
                    src_idx = tile_idx * 64 + y * 8 + x
                    dst_x = tile_x * 8 + x
                    dst_y = tile_y * 8 + y

                    if src_idx < len(pixels) and dst_y < height and dst_x < width:
                        img_pixels[dst_y * width + dst_x] = pixels[src_idx]

        img.putdata(img_pixels)
        img.save(output_png)
        print(f"Created preview: {output_png}")

    except Exception as e:
        print(f"Error creating preview: {e}")

def main():
    parser = argparse.ArgumentParser(description='Kirby Super Star Sprite Injector')
    parser.add_argument('input_png', help='Edited PNG file to inject')
    parser.add_argument('--vram', default='VRAM.dmp', help='VRAM dump file (default: VRAM.dmp)')
    parser.add_argument('--offset', default='0xC000', help='VRAM offset in hex (default: 0xC000)')
    parser.add_argument('--output', default='VRAM_edited.dmp', help='Output VRAM file')
    parser.add_argument('--preview', action='store_true', help='Generate preview images')

    args = parser.parse_args()

    # Parse offset
    offset = int(args.offset, 16)

    print("Sprite Injector - Kirby Super Star")
    print("=================================")
    print(f"Input PNG: {args.input_png}")
    print(f"VRAM file: {args.vram}")
    print(f"Offset: {hex(offset)} (VRAM ${hex(offset//2)})")
    print(f"Output: {args.output}")
    print()

    # Check files exist
    if not os.path.exists(args.input_png):
        print(f"Error: Input file '{args.input_png}' not found")
        return 1

    if not os.path.exists(args.vram):
        print(f"Error: VRAM file '{args.vram}' not found")
        return 1

    # Convert PNG to SNES format
    print("Converting PNG to SNES 4bpp format...")
    tile_data = png_to_snes(args.input_png)
    if not tile_data:
        return 1

    print(f"Converted {len(tile_data)} bytes ({len(tile_data)//32} tiles)")

    # Inject into VRAM
    print("\nInjecting into VRAM...")
    if not inject_into_vram(tile_data, args.vram, offset, args.output):
        return 1

    # Create preview if requested
    if args.preview:
        print("\nCreating preview...")
        preview_name = args.output.replace('.dmp', '_preview.png')
        create_preview(args.output, offset, len(tile_data), preview_name)

    print("\nSuccess! You can now load the modified VRAM in your emulator.")
    print("\nSprite data location:")
    print(f"  File offset: {hex(offset)}")
    print(f"  VRAM address: ${hex(offset//2)}")
    print(f"  Size: {len(tile_data)} bytes")

    return 0

if __name__ == "__main__":
    sys.exit(main())