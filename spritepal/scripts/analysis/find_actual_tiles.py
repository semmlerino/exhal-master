#!/usr/bin/env python3
"""
Search VRAM for actual tile graphics data (not tilemap indices)
"""

import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.rom_extractor import ROMExtractor


def analyze_vram_region(vram_data, start_offset, region_size, region_name):
    """Analyze a VRAM region to determine what type of data it contains"""

    print(f"\n{'='*60}")
    print(f"Analyzing {region_name} (0x{start_offset:04X}-0x{start_offset+region_size:04X})")
    print(f"{'='*60}")

    if start_offset + region_size > len(vram_data):
        print("Region exceeds VRAM size")
        return

    region_data = vram_data[start_offset:start_offset + region_size]

    # Check for empty region
    non_zero = sum(1 for b in region_data if b != 0)
    empty_ratio = 1.0 - (non_zero / len(region_data))
    print(f"Empty ratio: {empty_ratio:.1%}")

    if non_zero < 100:
        print("Region is mostly empty")
        return

    # Check for tilemap characteristics (repeating 16-bit patterns)
    tilemap_score = 0
    for i in range(0, min(len(region_data) - 2, 100), 2):
        value = int.from_bytes(region_data[i:i+2], "little")
        # Tilemap entries typically have specific bit patterns
        if 0 < value < 0x8000 and (value & 0xFC00) != 0:  # Has palette bits
            tilemap_score += 1

    print(f"Tilemap likelihood: {tilemap_score}%")

    # Check for graphics data characteristics
    # Graphics data should have good byte distribution
    byte_counts = [0] * 256
    for b in region_data[:1024]:  # Sample first 1KB
        byte_counts[b] += 1

    unique_bytes = sum(1 for c in byte_counts if c > 0)
    print(f"Unique byte values: {unique_bytes}/256")

    # Try extracting as tiles
    print("\nAttempting tile extraction...")
    extractor = ROMExtractor()

    # Extract first 64 tiles (2KB)
    tile_data = region_data[:2048]
    output_path = f"vram_region_{start_offset:04X}.png"

    try:
        tile_count = extractor._convert_4bpp_to_png(tile_data, output_path)
        print(f"Successfully extracted {tile_count} tiles -> {output_path}")

        # Also show hex dump of first tile
        print("\nFirst tile data (32 bytes):")
        for row in range(4):
            row_data = tile_data[row*8:(row+1)*8]
            hex_str = " ".join(f"{b:02X}" for b in row_data)
            print(f"  {hex_str}")

    except Exception as e:
        print(f"Tile extraction failed: {e}")


def search_for_graphics(vram_path):
    """Search entire VRAM for graphics data"""

    print(f"Searching for graphics data in: {vram_path}")

    with open(vram_path, "rb") as f:
        vram_data = f.read()

    print(f"VRAM size: {len(vram_data)} bytes (0x{len(vram_data):04X})")

    # Common VRAM regions to check
    regions = [
        (0x0000, 0x2000, "Region 0: 0x0000-0x2000"),
        (0x2000, 0x2000, "Region 1: 0x2000-0x4000"),
        (0x4000, 0x2000, "Region 2: 0x4000-0x6000 (where we found tilemaps)"),
        (0x6000, 0x2000, "Region 3: 0x6000-0x8000"),
        (0x8000, 0x2000, "Region 4: 0x8000-0xA000"),
        (0xA000, 0x2000, "Region 5: 0xA000-0xC000"),
        (0xC000, 0x2000, "Region 6: 0xC000-0xE000"),
        (0xE000, 0x2000, "Region 7: 0xE000-0x10000"),
    ]

    for start, size, name in regions:
        analyze_vram_region(vram_data, start, size, name)

    # Also do a targeted search for Kirby patterns
    print("\n" + "="*60)
    print("Searching for Kirby-like patterns...")
    print("="*60)

    # Kirby sprites often have specific characteristics
    # Look for tiles with circular patterns (for Kirby's round body)
    for offset in range(0, len(vram_data) - 32, 32):
        tile_data = vram_data[offset:offset + 32]

        # Skip empty tiles
        if sum(tile_data) < 50:
            continue

        # Check for symmetry (Kirby is often symmetric)
        # Compare left and right halves of tile
        symmetry_score = 0
        for row in range(8):
            byte_idx = row * 2
            if byte_idx + 1 < len(tile_data):
                # Get the row's pixel data
                # This is a rough check - real symmetry check would be more complex
                left_bits = tile_data[byte_idx]
                right_bits = tile_data[byte_idx + 1]

                # Check for some symmetry
                if bin(left_bits).count("1") == bin(right_bits).count("1"):
                    symmetry_score += 1

        if symmetry_score >= 4:
            print(f"\nPotential sprite tile at 0x{offset:04X} (symmetry score: {symmetry_score}/8)")


def main():
    vram_file = "../Kirby Super Star (USA)_2_VRAM.dmp"

    if not os.path.exists(vram_file):
        print(f"VRAM file not found: {vram_file}")
        return

    search_for_graphics(vram_file)


if __name__ == "__main__":
    main()
