#!/usr/bin/env python3
"""
Simple test to analyze VRAM at correct offsets
"""

import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def analyze_vram_simple(vram_path):
    print(f"\nAnalyzing VRAM file: {vram_path}")

    if not os.path.exists(vram_path):
        print(f"File not found: {vram_path}")
        return

    with open(vram_path, "rb") as f:
        vram_data = f.read()

    print(f"VRAM size: {len(vram_data)} bytes")

    # Correct sprite offsets based on research
    sprite_offsets = [
        (0x4000, "Primary sprite area"),
        (0x6000, "Secondary sprite area"),
        (0x8000, "Alternative sprite area"),
    ]

    for offset, description in sprite_offsets:
        print(f"\n{'='*60}")
        print(f"Checking offset 0x{offset:04X} ({description})")
        print(f"{'='*60}")

        if offset + 256 > len(vram_data):
            print(f"Not enough data at offset 0x{offset:04X}")
            continue

        # Extract first 8 tiles (256 bytes)
        sprite_data = vram_data[offset:offset + 256]

        # Check if there's actual data
        non_zero = sum(1 for b in sprite_data if b != 0)
        print(f"Non-zero bytes: {non_zero}/256")

        if non_zero < 10:
            print("Too little data at this offset")
            continue

        # Show first tile
        print("\nFirst tile (32 bytes):")
        for row in range(4):
            row_data = sprite_data[row*8:(row+1)*8]
            hex_str = " ".join(f"{b:02X}" for b in row_data)
            print(f"  {hex_str}")

# Test with a specific VRAM file
vram_file = "../Kirby Super Star (USA)_2_VRAM.dmp"
analyze_vram_simple(vram_file)
