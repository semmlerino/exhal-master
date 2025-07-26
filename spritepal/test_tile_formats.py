#!/usr/bin/env python3
"""
Test different tile format interpretations to figure out the correct format
"""

import os
import sys

import numpy as np
from PIL import Image

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def extract_2bpp_tile(data, offset):
    """Extract 8x8 tile in 2bpp format (16 bytes per tile)"""
    tile = np.zeros((8, 8), dtype=np.uint8)

    for y in range(8):
        # 2 bitplanes, 1 byte each per row
        byte0 = data[offset + y * 2]
        byte1 = data[offset + y * 2 + 1]

        for x in range(8):
            bit = 7 - x
            pixel = ((byte1 >> bit) & 1) << 1 | ((byte0 >> bit) & 1)
            tile[y, x] = pixel * 85  # Scale 0-3 to 0-255

    return tile


def extract_4bpp_planar_tile(data, offset):
    """Extract 8x8 tile in 4bpp planar format (32 bytes per tile)"""
    tile = np.zeros((8, 8), dtype=np.uint8)

    for y in range(8):
        # First two bitplanes
        byte0 = data[offset + y * 2]
        byte1 = data[offset + y * 2 + 1]
        # Second two bitplanes
        byte2 = data[offset + 16 + y * 2]
        byte3 = data[offset + 16 + y * 2 + 1]

        for x in range(8):
            bit = 7 - x
            pixel = (
                ((byte3 >> bit) & 1) << 3 |
                ((byte2 >> bit) & 1) << 2 |
                ((byte1 >> bit) & 1) << 1 |
                ((byte0 >> bit) & 1)
            )
            tile[y, x] = pixel * 17  # Scale 0-15 to 0-255

    return tile


def extract_4bpp_linear_tile(data, offset):
    """Extract 8x8 tile in 4bpp linear format (32 bytes per tile)"""
    tile = np.zeros((8, 8), dtype=np.uint8)

    for y in range(8):
        for x in range(0, 8, 2):
            # Each byte contains 2 pixels
            byte_idx = offset + y * 4 + x // 2
            byte_val = data[byte_idx]

            # High nibble is left pixel
            tile[y, x] = (byte_val >> 4) * 17
            # Low nibble is right pixel
            tile[y, x + 1] = (byte_val & 0x0F) * 17

    return tile


def test_formats_on_vram(vram_path, test_offset):
    """Test different format interpretations on VRAM data"""

    print(f"\nTesting formats on {vram_path} at offset 0x{test_offset:04X}")

    with open(vram_path, "rb") as f:
        vram_data = f.read()

    # Show raw hex data
    print("\nRaw hex data (first 32 bytes):")
    for i in range(4):
        row_data = vram_data[test_offset + i*8:test_offset + (i+1)*8]
        hex_str = " ".join(f"{b:02X}" for b in row_data)
        print(f"  {hex_str}")

    # Create test image with different interpretations
    fig_width = 12  # tiles per row
    fig_height = 4  # rows
    img = Image.new("L", (fig_width * 8, fig_height * 8), 0)

    formats = [
        ("2bpp", 16, extract_2bpp_tile),
        ("4bpp_planar", 32, extract_4bpp_planar_tile),
        ("4bpp_linear", 32, extract_4bpp_linear_tile),
    ]

    y_offset = 0
    for format_name, bytes_per_tile, extract_func in formats:
        print(f"\nTesting {format_name} format:")

        # Extract multiple tiles
        for i in range(fig_width):
            offset = test_offset + i * bytes_per_tile
            if offset + bytes_per_tile <= len(vram_data):
                try:
                    tile = extract_func(vram_data, offset)

                    # Place tile in image
                    for y in range(8):
                        for x in range(8):
                            img.putpixel((i * 8 + x, y_offset + y), int(tile[y, x]))

                except Exception as e:
                    print(f"  Error extracting tile {i}: {e}")

        y_offset += 8

    # Save test image
    output_path = f"format_test_{test_offset:04X}.png"
    img.save(output_path)
    print(f"\nSaved format comparison to: {output_path}")

    # Also check if this might be tilemap data
    print("\nChecking if this is tilemap data (16-bit entries):")
    for i in range(8):
        offset = test_offset + i * 2
        if offset + 2 <= len(vram_data):
            value = int.from_bytes(vram_data[offset:offset+2], "little")
            tile_idx = value & 0x3FF  # Lower 10 bits are tile index
            palette = (value >> 10) & 0x7  # Bits 10-12 are palette
            print(f"  Entry {i}: 0x{value:04X} -> Tile #{tile_idx}, Palette {palette}")


def main():
    # Test with VRAM dump
    vram_file = "../Kirby Super Star (USA)_2_VRAM.dmp"

    if not os.path.exists(vram_file):
        print(f"VRAM file not found: {vram_file}")
        return

    # Test at different offsets
    test_offsets = [
        0x0000,  # Start of VRAM
        0x4000,  # Where we thought sprites were
        0x6000,  # Secondary sprite area
        0x8000,  # Alternative area
    ]

    for offset in test_offsets:
        test_formats_on_vram(vram_file, offset)


if __name__ == "__main__":
    main()
