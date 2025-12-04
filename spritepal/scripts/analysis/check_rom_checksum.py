#!/usr/bin/env python3
from __future__ import annotations

"""Check ROM checksum to debug sprite selection issue."""

import struct
from pathlib import Path


def calculate_snes_checksum(rom_data: bytes) -> int:
    """Calculate SNES ROM checksum."""
    # SNES checksum is at 0x7FDC-0x7FDD (or 0xFFDC-0xFFDD for HiROM)
    # Try LoROM location first
    checksum_offset = 0x7FDC
    if checksum_offset + 2 <= len(rom_data):
        checksum = struct.unpack(">H", rom_data[checksum_offset:checksum_offset+2])[0]
        complement = struct.unpack(">H", rom_data[checksum_offset+2:checksum_offset+4])[0]
        print(f"LoROM checksum at 0x7FDC: 0x{checksum:04X} (complement: 0x{complement:04X})")
        return checksum

    # Try HiROM location
    checksum_offset = 0xFFDC
    if checksum_offset + 2 <= len(rom_data):
        checksum = struct.unpack(">H", rom_data[checksum_offset:checksum_offset+2])[0]
        complement = struct.unpack(">H", rom_data[checksum_offset+2:checksum_offset+4])[0]
        print(f"HiROM checksum at 0xFFDC: 0x{checksum:04X} (complement: 0x{complement:04X})")
        return checksum

    return 0

def get_rom_title(rom_data: bytes) -> str:
    """Extract ROM title from header."""
    # Try LoROM location first (0x7FC0)
    title_offset = 0x7FC0
    if title_offset + 21 <= len(rom_data):
        title = rom_data[title_offset:title_offset+21].decode("ascii", errors="ignore").strip()
        if title and not all(c == "\x00" for c in title):
            return title

    # Try HiROM location (0xFFC0)
    title_offset = 0xFFC0
    if title_offset + 21 <= len(rom_data):
        return rom_data[title_offset:title_offset+21].decode("ascii", errors="ignore").strip()

    return "Unknown"

def main():
    print("Checking ROM checksums...")
    print("=" * 60)

    # Find all ROM files
    rom_files = list(Path().glob("*.sfc")) + list(Path().glob("*.smc"))

    for rom_file in rom_files:
        print(f"\nROM: {rom_file.name}")
        print("-" * 40)

        with rom_file.open("rb") as f:
            rom_data = f.read()

        # Skip SMC header if present
        if len(rom_data) % 1024 == 512:
            print("  Detected SMC header, skipping 512 bytes")
            rom_data = rom_data[512:]

        title = get_rom_title(rom_data)
        checksum = calculate_snes_checksum(rom_data)

        print(f"  Title: '{title}'")
        print(f"  Checksum: 0x{checksum:04X}")

        # Check against known values
        known_checksums = {
            "0x8A5C": "KIRBY SUPER STAR (USA)",
            "0x7F4C": "KIRBY SUPER STAR (Japan)",
            "0x8B5C": "KIRBY SUPER STAR (Europe) / KIRBY'S FUN PAK",
            "0xC6AA": "KIRBY SUPER DELUXE (PAL)",
            "0x8E5C": "KIRBY SUPER DELUXE (Japan Rev)",
            "0xAE40": "KIRBY'S FUN PAK (Europe Alt)"
        }

        checksum_hex = f"0x{checksum:04X}"
        if checksum_hex in known_checksums:
            print(f"  ✓ Matches: {known_checksums[checksum_hex]}")
        else:
            print("  ✗ Unknown checksum")

    print("\n" + "=" * 60)
    print("\nDEBUG INFO for SpritePal:")
    print("If your ROM checksum is 0x8B5C (Europe/Fun Pak), it should match")
    print("the 'KIRBY SUPER STAR' entry in sprite_locations.json.")
    print("\nThe issue might be:")
    print("1. ROM title not matching expected pattern")
    print("2. SpritePal might need restart after config change")
    print("3. Config file format issue")

if __name__ == "__main__":
    main()
