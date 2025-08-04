#!/usr/bin/env python3
"""
Simple VRAM analyzer to extract sprite patterns
"""

import os
import sys


def analyze_vram(vram_path: str):
    """Analyze VRAM dump and show sprite patterns"""

    print(f"Loading VRAM dump: {vram_path}")
    with open(vram_path, "rb") as f:
        vram_data = f.read()

    print(f"VRAM size: {len(vram_data)} bytes")

    # Sprite data typically starts at 0xC000 in VRAM
    sprite_start = 0xC000
    sprite_size = 0x4000  # 16KB of sprite data

    if len(vram_data) < sprite_start + sprite_size:
        print("VRAM dump too small, using available data")
        sprite_data = vram_data[sprite_start:]
    else:
        sprite_data = vram_data[sprite_start:sprite_start + sprite_size]

    print(f"\nSprite area: 0x{sprite_start:04X}-0x{sprite_start + len(sprite_data):04X}")
    print(f"Sprite data size: {len(sprite_data)} bytes")

    # Find non-empty tiles
    tile_size = 32  # 8x8 tile in 4bpp = 32 bytes
    num_tiles = len(sprite_data) // tile_size
    non_empty_tiles = []

    for i in range(num_tiles):
        offset = i * tile_size
        tile = sprite_data[offset:offset + tile_size]

        # Check if not all zeros
        if any(b != 0 for b in tile):
            non_empty_tiles.append((sprite_start + offset, tile))

    print(f"\nNon-empty tiles: {len(non_empty_tiles)} out of {num_tiles}")

    # Show first few non-empty tiles
    print("\nFirst 10 non-empty tiles:")
    for i, (vram_offset, tile) in enumerate(non_empty_tiles[:10]):
        print(f"\nTile {i+1} at VRAM offset 0x{vram_offset:04X}:")

        # Show hex dump in 8-byte rows
        for row in range(4):
            row_data = tile[row*8:(row+1)*8]
            hex_str = " ".join(f"{b:02X}" for b in row_data)
            print(f"  {hex_str}")

        # Calculate statistics
        non_zero = sum(1 for b in tile if b != 0)
        max_val = max(tile)
        min_val = min(b for b in tile if b > 0) if any(b > 0 for b in tile) else 0

        print(f"  Stats: {non_zero} non-zero bytes, range: 0x{min_val:02X}-0x{max_val:02X}")

    # Show specific interesting offsets
    print("\n" + "="*60)
    print("Checking specific VRAM locations:")

    interesting_offsets = [
        (0xC000, "Start of sprite area"),
        (0xC800, "Common Kirby sprite location"),
        (0xD000, "Enemy sprites area"),
        (0xE000, "Additional sprites")
    ]

    for offset, desc in interesting_offsets:
        if offset < len(vram_data):
            # Get 32 bytes (one tile)
            tile = vram_data[offset:offset + 32]
            non_zero = sum(1 for b in tile if b != 0)
            print(f"\n0x{offset:04X} ({desc}): {non_zero}/32 non-zero bytes")
            if non_zero > 0:
                print(f"  First 16 bytes: {' '.join(f'{b:02X}' for b in tile[:16])}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python analyze_vram_simple.py <vram_dump_path>")
        sys.exit(1)

    vram_path = sys.argv[1]
    if not os.path.exists(vram_path):
        print(f"File not found: {vram_path}")
        sys.exit(1)

    analyze_vram(vram_path)
