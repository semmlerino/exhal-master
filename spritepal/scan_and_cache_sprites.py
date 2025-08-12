#!/usr/bin/env python3
"""
Scan a ROM for sprites and cache the results for later use.
This allows us to quickly load sprite data for screenshots without re-scanning.
"""

import json
import sys
from pathlib import Path
from typing import Any

# Add parent directory to path to import SpritePal modules
sys.path.insert(0, str(Path(__file__).parent))

from core.rom_extractor import ROMExtractor
from core.sprite_finder import SpriteFinder
from utils.logging_config import get_logger

logger = get_logger(__name__)

def scan_rom_for_sprites(rom_path: Path, limit: int = 50) -> list[dict[str, Any]]:
    """
    Scan a ROM file for sprites.

    Args:
        rom_path: Path to the ROM file
        limit: Maximum number of sprites to find (for performance)

    Returns:
        List of sprite data dictionaries
    """
    print(f"Scanning ROM: {rom_path}")

    # Load ROM data for size check
    with open(rom_path, 'rb') as f:
        rom_data = f.read()

    print(f"ROM size: {len(rom_data):,} bytes")

    # Create extractor - it takes no arguments
    extractor = ROMExtractor()

    # Find sprites using SpriteFinder
    SpriteFinder(rom_data)
    sprites = []

    print(f"Searching for sprites (limit: {limit})...")

    # Scan through ROM for sprites
    offset = 0
    found_count = 0
    scan_step = 2048  # Check every 2KB for performance

    # Use known good offsets for test data or scan for HAL-compressed sprites
    known_offsets = [
        0x100, 0x500, 0x1000, 0x2000, 0x3000, 0x4000, 0x5000,
        0x8000, 0x10000, 0x20000, 0x30000, 0x40000, 0x50000
    ]

    # First try known offsets
    for offset in known_offsets:
        if offset >= len(rom_data) or found_count >= limit:
            break

        try:
            # Try to extract sprite at this offset
            sprite_data = extractor.extract_sprite_data(str(rom_path), offset)
            if sprite_data and len(sprite_data) > 256:  # Minimum size for a sprite
                # We found a sprite!
                sprite_info = {
                    'offset': offset,
                    'offset_hex': f"0x{offset:06X}",
                    'size': len(sprite_data),
                    'width': 128,  # Default width
                    'height': min(256, len(sprite_data) // 128 if len(sprite_data) >= 128 else 64),
                    'name': f"Sprite_{found_count:03d}",
                    'compressed': True,
                    'palette_index': found_count % 8  # Vary palettes for visual interest
                }
                sprites.append(sprite_info)
                found_count += 1
                print(f"  Found sprite #{found_count} at offset 0x{offset:06X} ({len(sprite_data)} bytes)")
        except Exception:
            # Not a valid sprite at this offset
            pass

    # If we don't have enough, scan through ROM
    while offset < min(len(rom_data), 0x100000) and found_count < limit:  # Limit scan to first 1MB
        # Try to extract sprite at this offset
        try:
            sprite_data = extractor.extract_sprite_data(str(rom_path), offset)
            if sprite_data and len(sprite_data) > 256:
                # We found a sprite!
                sprite_info = {
                    'offset': offset,
                    'offset_hex': f"0x{offset:06X}",
                    'size': len(sprite_data),
                    'width': 128,  # Default width
                    'height': min(256, len(sprite_data) // 128 if len(sprite_data) >= 128 else 64),
                    'name': f"Sprite_{found_count:03d}",
                    'compressed': True,
                    'palette_index': found_count % 8  # Vary palettes for visual interest
                }
                sprites.append(sprite_info)
                found_count += 1
                print(f"  Found sprite #{found_count} at offset 0x{offset:06X} ({len(sprite_data)} bytes)")

                # Skip past this sprite
                offset += max(len(sprite_data), scan_step)
            else:
                offset += scan_step
        except Exception:
            # Not a valid sprite at this offset
            offset += scan_step

    print(f"Found {len(sprites)} sprites")
    return sprites

def save_sprite_cache(sprites: list[dict[str, Any]], cache_path: Path):
    """
    Save sprite data to a JSON cache file.

    Args:
        sprites: List of sprite data dictionaries
        cache_path: Path to save the cache file
    """
    cache_data = {
        'version': 1,
        'sprite_count': len(sprites),
        'sprites': sprites
    }

    with open(cache_path, 'w') as f:
        json.dump(cache_data, f, indent=2)

    print(f"Saved sprite cache to: {cache_path}")

def load_sprite_cache(cache_path: Path) -> list[dict[str, Any]]:
    """
    Load sprite data from a cache file.

    Args:
        cache_path: Path to the cache file

    Returns:
        List of sprite data dictionaries
    """
    with open(cache_path) as f:
        cache_data = json.load(f)

    print(f"Loaded {cache_data['sprite_count']} sprites from cache")
    return cache_data['sprites']

def main():
    """Main function to scan ROM and cache results."""
    # Use test_rom.sfc by default, or specify another
    rom_files = [
        Path("test_rom.sfc"),
        Path("Kirby Super Star (USA).sfc"),
        Path("Kirby's Fun Pak (Europe).sfc")
    ]

    # Find first available ROM
    rom_path = None
    for rom_file in rom_files:
        if rom_file.exists():
            rom_path = rom_file
            break

    if not rom_path:
        print("No ROM file found!")
        return 1

    # Scan for sprites
    sprites = scan_rom_for_sprites(rom_path, limit=30)

    if not sprites:
        print("No sprites found!")
        return 1

    # Save to cache
    cache_path = Path("sprite_cache.json")
    save_sprite_cache(sprites, cache_path)

    # Test loading from cache
    loaded_sprites = load_sprite_cache(cache_path)
    print(f"Successfully verified cache with {len(loaded_sprites)} sprites")

    return 0

if __name__ == "__main__":
    sys.exit(main())
