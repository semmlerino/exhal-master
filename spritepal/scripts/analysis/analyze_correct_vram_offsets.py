#!/usr/bin/env python3
from __future__ import annotations

"""
Analyze VRAM dumps at the CORRECT sprite offsets
Based on research findings that sprites are at 0x4000 or 0x6000, not 0xC000
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.rom_extractor import ROMExtractor
from utils.logging_config import get_logger

logger = get_logger(__name__)

def analyze_vram_at_correct_offsets(vram_path: str):
    """Analyze VRAM dump at the correct sprite offsets"""

    logger.info(f"Analyzing VRAM dump: {vram_path}")

    vram_path_obj = Path(vram_path)
    with vram_path_obj.open("rb") as f:
        vram_data = f.read()

    logger.info(f"VRAM size: {len(vram_data)} bytes")

    # Correct sprite offsets based on research
    sprite_offsets = [
        (0x4000, "Primary sprite area"),
        (0x6000, "Secondary sprite area"),
        (0x8000, "Alternative sprite area"),
        (0xC000, "Tilemap data (not sprites)")  # What we were incorrectly using
    ]

    extractor = ROMExtractor()

    for offset, description in sprite_offsets:
        logger.info(f"\n{'='*60}")
        logger.info(f"Checking offset 0x{offset:04X} ({description})")
        logger.info(f"{'='*60}")

        if offset + 8192 > len(vram_data):
            logger.warning(f"Not enough data at offset 0x{offset:04X}")
            continue

        # Extract 256 tiles (8KB) from this offset
        sprite_data = vram_data[offset:offset + 8192]

        # Check if there's actual data here
        non_zero_bytes = sum(1 for b in sprite_data if b != 0)
        logger.info(f"Non-zero bytes: {non_zero_bytes}/{len(sprite_data)}")

        if non_zero_bytes < 100:  # Too little data
            logger.info("Too little data at this offset")
            continue

        # Show first few tiles
        logger.info("\nFirst 3 tiles (96 bytes):")
        for tile_idx in range(3):
            tile_start = tile_idx * 32
            tile_data = sprite_data[tile_start:tile_start + 32]

            logger.info(f"\nTile {tile_idx + 1}:")
            for row in range(4):
                row_data = tile_data[row*8:(row+1)*8]
                hex_str = " ".join(f"{b:02X}" for b in row_data)
                logger.info(f"  {hex_str}")

        # Convert to PNG for visual inspection
        output_path = f"vram_{Path(vram_path).name}_{offset:04X}.png"
        try:
            _ = extractor._convert_4bpp_to_png(sprite_data, output_path)
            logger.info(f"\nSaved preview: {output_path}")
        except Exception:
            logger.exception("Failed to convert to PNG")

def check_rom_pointers(rom_path: str):
    """Check the ROM pointer table at $FF:0002 as discovered by research"""

    logger.info(f"\nChecking ROM pointer table in: {rom_path}")

    rom_path_obj = Path(rom_path)
    with rom_path_obj.open("rb") as f:
        rom_data = f.read()

    # Convert SNES address $FF:0002 to file offset
    # Bank $FF = offset 0x3F8000, so $FF:0002 = 0x3F8002
    pointer_table_offset = 0x3F8002

    if pointer_table_offset >= len(rom_data):
        logger.error("ROM too small to contain pointer table")
        return

    logger.info(f"\nReading pointer table at offset 0x{pointer_table_offset:06X}")

    # Read some pointers (16-bit little endian)
    for i in range(10):
        offset = pointer_table_offset + (i * 2)
        if offset + 2 <= len(rom_data):
            pointer = int.from_bytes(rom_data[offset:offset+2], "little")
            # Convert to full address assuming bank $FF
            full_address = 0xFF0000 | pointer
            file_offset = ((full_address >> 16) - 0xC0) * 0x8000 + (full_address & 0x7FFF)
            logger.info(f"  Pointer {i}: ${pointer:04X} -> SNES ${full_address:06X} -> File 0x{file_offset:06X}")

def main():
    """Main function"""

    # Look for VRAM dumps
    vram_files = []

    # Check parent directory
    parent_dir = ".."
    print(f"Checking directory: {Path(parent_dir).resolve()}")
    try:
        files = [f.name for f in Path(parent_dir).iterdir()]
        print(f"Found {len(files)} files in parent directory")
        for file in files:
            if file.endswith("_VRAM.dmp") or ("VRAM" in file and file.endswith(".dmp")):
                full_path = Path(parent_dir) / file
                print(f"Found VRAM file: {file}")
                vram_files.append(full_path)
    except Exception as e:
        print(f"Error listing directory: {e}")

    if not vram_files:
        logger.error("No VRAM dump files found")
        logger.info("Please ensure you have VRAM dumps from MSS savestates or emulator")
        return

    logger.info(f"Found {len(vram_files)} VRAM dumps")

    # Analyze each VRAM dump
    for vram_file in vram_files[:3]:  # Limit to first 3
        analyze_vram_at_correct_offsets(vram_file)

    # Check ROM pointers
    rom_files = ["Kirby Super Star (USA).sfc", "Kirby's Fun Pak (Europe).sfc"]
    for rom_file in rom_files:
        if Path(rom_file).exists():
            check_rom_pointers(rom_file)

if __name__ == "__main__":
    main()
