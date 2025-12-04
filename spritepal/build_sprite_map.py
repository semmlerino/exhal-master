#!/usr/bin/env python3
"""
Build a comprehensive mapping of RAM addresses to ROM offsets for sprites.

This script automates the process of finding ROM offsets for all captured
RAM sprites, creating a reusable mapping file.
"""

import json
import subprocess
import tempfile
from pathlib import Path


def scan_rom_for_sprites(rom_path: str, start: int = 0x40000, end: int = 0x200000) -> dict[int, bytes]:
    """
    Scan ROM for all HAL-compressed sprites and build a database.
    
    Returns:
        Dictionary mapping ROM offset to first 64 bytes of decompressed data
    """
    sprite_db = {}
    exhal_path = "./exhal.exe" if sys.platform == "win32" else "./exhal"

    print("Building sprite database from ROM...")
    print(f"Scanning range: 0x{start:06X} to 0x{end:06X}")

    # Scan every 16 bytes (HAL compression typically aligned)
    for offset in range(start, end, 16):
        if offset % 0x1000 == 0:
            print(f"Scanning: 0x{offset:06X} ({(offset-start)/(end-start)*100:.1f}%)", end='\r')

        try:
            # Try to decompress
            with tempfile.NamedTemporaryFile(delete=False, suffix=".bin") as tmp:
                output_path = tmp.name

            cmd = [exhal_path, rom_path, f"0x{offset:X}", output_path]
            result = subprocess.run(cmd, capture_output=True, timeout=1)

            if result.returncode == 0 and Path(output_path).exists():
                with open(output_path, 'rb') as f:
                    data = f.read()

                # Store first 64 bytes as signature
                if len(data) >= 64:
                    sprite_db[offset] = data[:64]

                Path(output_path).unlink()
            elif Path(output_path).exists():
                Path(output_path).unlink()

        except subprocess.TimeoutExpired:
            # Skip if decompression takes too long
            continue
        except Exception:
            continue

    print(f"\nFound {len(sprite_db)} potential sprites in ROM")
    return sprite_db

def match_ram_to_rom(ram_data: bytes, sprite_db: dict[int, bytes]) -> int | None:
    """
    Find ROM offset that matches RAM sprite data.
    
    Args:
        ram_data: Decompressed sprite data from RAM
        sprite_db: Database of ROM sprites and their signatures
    
    Returns:
        ROM offset if match found, None otherwise
    """
    # Get signature from RAM data
    signature = ram_data[:min(64, len(ram_data))]

    # Search database for match
    for rom_offset, rom_signature in sprite_db.items():
        if rom_signature == signature:
            return rom_offset

    return None

def build_mapping_from_session(session_file: str, rom_path: str) -> dict[str, int]:
    """
    Build RAM to ROM mapping from a session export file.
    
    Args:
        session_file: Path to sprite_session.json from Lua script
        rom_path: Path to ROM file
    
    Returns:
        Dictionary mapping RAM addresses (as strings) to ROM offsets
    """
    mapping = {}

    # Load session data
    with open(session_file) as f:
        session = json.load(f)

    # Build sprite database from ROM
    sprite_db = scan_rom_for_sprites(rom_path)

    # Process each captured sprite
    for sprite in session.get("sprites", []):
        ram_offset = sprite.get("rom_offset", 0)

        # Check if it's a RAM address (high bit set in our marking scheme)
        if ram_offset >= 0x800000:
            actual_ram = ram_offset & 0x7FFFFF

            # Check if we have RAM dump for this address
            dump_file = f"sprite_ram_{actual_ram:06X}.bin"
            if Path(dump_file).exists():
                with open(dump_file, 'rb') as f:
                    ram_data = f.read()

                # Find matching ROM offset
                rom_offset = match_ram_to_rom(ram_data, sprite_db)
                if rom_offset:
                    mapping[f"0x{actual_ram:06X}"] = rom_offset
                    print(f"Mapped RAM 0x{actual_ram:06X} -> ROM 0x{rom_offset:06X}")

    return mapping

def create_mapping_file(mapping: dict[str, int], output_file: str = "sprite_mapping.json"):
    """Save RAM to ROM mapping to a JSON file."""
    with open(output_file, 'w') as f:
        # Convert integer offsets to hex strings for readability
        readable_mapping = {
            ram: f"0x{rom:06X}" for ram, rom in mapping.items()
        }
        json.dump(readable_mapping, f, indent=2)

    print(f"Saved mapping to {output_file}")

def quick_find_sprite(rom_path: str, ram_dump: str) -> int | None:
    """
    Quick method to find a single sprite's ROM offset.
    
    This is optimized for finding individual sprites rather than
    building a complete database.
    """
    # Read RAM dump
    with open(ram_dump, 'rb') as f:
        ram_data = f.read()

    # Common sprite regions in Kirby games
    search_regions = [
        (0x048000, 0x080000),  # Kirby's sprites
        (0x088000, 0x0C0000),  # Enemy sprites
        (0x0C8000, 0x100000),  # Boss sprites
        (0x108000, 0x140000),  # Effects
        (0x148000, 0x180000),  # More sprites
    ]

    exhal_path = "./exhal.exe" if sys.platform == "win32" else "./exhal"
    signature = ram_data[:64]

    for start, end in search_regions:
        print(f"Searching region 0x{start:06X}-0x{end:06X}...")

        for offset in range(start, end, 8):  # Check every 8 bytes
            try:
                with tempfile.NamedTemporaryFile(delete=False, suffix=".bin") as tmp:
                    output_path = tmp.name

                cmd = [exhal_path, rom_path, f"0x{offset:X}", output_path]
                result = subprocess.run(cmd, capture_output=True, timeout=0.5)

                if result.returncode == 0 and Path(output_path).exists():
                    with open(output_path, 'rb') as f:
                        decompressed = f.read()

                    if len(decompressed) >= 64 and decompressed[:64] == signature:
                        Path(output_path).unlink()
                        print(f"Found sprite at ROM offset 0x{offset:06X}!")
                        return offset

                    Path(output_path).unlink()

            except Exception:
                continue

    return None

import sys  # Add this import at the top


def main():
    """Main entry point."""
    if len(sys.argv) < 3:
        print("Usage:")
        print("  python build_sprite_map.py <rom_path> <ram_dump>")
        print("  python build_sprite_map.py <rom_path> --session <session.json>")
        print("\nExamples:")
        print("  python build_sprite_map.py kirby.sfc sprite_ram_7ECBA1.bin")
        print("  python build_sprite_map.py kirby.sfc --session sprite_session.json")
        return

    rom_path = sys.argv[1]

    if not Path(rom_path).exists():
        print(f"ROM not found: {rom_path}")
        return

    if sys.argv[2] == "--session":
        # Build complete mapping from session
        session_file = sys.argv[3]
        mapping = build_mapping_from_session(session_file, rom_path)
        create_mapping_file(mapping)
    else:
        # Quick find single sprite
        ram_dump = sys.argv[2]
        rom_offset = quick_find_sprite(rom_path, ram_dump)
        if rom_offset:
            print(f"\n✅ SUCCESS! Use ROM offset 0x{rom_offset:06X} in SpritePal")
            print("This is the compressed sprite location in the ROM.")
        else:
            print("\n❌ Sprite not found in common regions.")
            print("Try building a full database with --session mode.")

if __name__ == "__main__":
    main()
