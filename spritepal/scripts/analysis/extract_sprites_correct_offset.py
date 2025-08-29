#!/usr/bin/env python3
from __future__ import annotations

"""
Extract sprites from VRAM at the CORRECT offsets (0x4000/0x6000)
"""

import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.rom_extractor import ROMExtractor

def extract_sprites_from_vram(vram_path, output_prefix):
    """Extract sprites from VRAM at correct offsets"""

    print(f"\nExtracting sprites from: {vram_path}")

    vram_path_obj = Path(vram_path)
    with vram_path_obj.open("rb") as f:
        vram_data = f.read()

    extractor = ROMExtractor()

    # Extract from correct sprite offsets
    sprite_locations = [
        (0x4000, 8192, "primary"),    # 256 tiles
        (0x6000, 8192, "secondary"),  # 256 tiles
        (0x8000, 4096, "alt"),        # 128 tiles
    ]

    extracted_files = []

    for offset, size, name in sprite_locations:
        if offset + size > len(vram_data):
            print(f"Not enough data for {name} sprites at 0x{offset:04X}")
            continue

        sprite_data = vram_data[offset:offset + size]

        # Check if there's actual data
        non_zero = sum(1 for b in sprite_data if b != 0)
        if non_zero < 100:
            print(f"Too little data at {name} offset 0x{offset:04X}")
            continue

        # Convert to PNG
        output_path = f"{output_prefix}_{name}_sprites.png"
        tile_count = extractor._convert_4bpp_to_png(sprite_data, output_path)

        print(f"Extracted {tile_count} tiles from {name} sprites -> {output_path}")
        extracted_files.append(output_path)

    return extracted_files

def main():
    # Test with USA ROM VRAM dump
    vram_file = "../Kirby Super Star (USA)_2_VRAM.dmp"

    if not Path(vram_file).exists():
        print(f"VRAM file not found: {vram_file}")
        return

    # Extract sprites
    output_prefix = "kirby_vram_correct"
    extracted = extract_sprites_from_vram(vram_file, output_prefix)

    print(f"\nExtracted {len(extracted)} sprite sheets")
    print("\nIMPORTANT: These are grayscale because we're extracting from VRAM without palettes.")
    print("Check the images to see if we finally have actual Kirby sprites!")

if __name__ == "__main__":
    main()
