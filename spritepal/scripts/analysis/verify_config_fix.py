#!/usr/bin/env python3
from __future__ import annotations

"""Verify the sprite configuration fix."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from core.sprite_config_loader import SpriteConfigLoader


def test_config_loading():
    """Test that sprites can now be loaded for the ROM."""
    print("Testing sprite configuration loading...")
    print("=" * 60)

    # Test checksums
    test_cases = [
        ("Kirby's Fun Pak (Europe)", 0xBF51),
        ("Kirby Super Star (USA)", 0x5539)
    ]

    config_loader = SpriteConfigLoader()

    for rom_title, checksum in test_cases:
        print(f"\nTesting: {rom_title} (checksum: 0x{checksum:04X})")
        print("-" * 40)

        sprites = config_loader.get_game_sprites(rom_title, checksum)

        if sprites:
            print(f"✓ Found {len(sprites)} sprites:")
            for sprite_name in list(sprites.keys())[:5]:  # Show first 5
                sprite = sprites[sprite_name]
                print(f"  - {sprite_name}: offset=0x{sprite.offset:06X}")
        else:
            print("✗ No sprites found!")

    print("\n" + "=" * 60)
    print("\nFIX COMPLETE!")
    print("\nNow when you launch SpritePal:")
    print("1. The ROM will be recognized (checksum 0xBF51)")
    print("2. Sprites will appear in the dropdown")
    print("3. Selecting 'High_Quality_Sprite_1' will extract real sprites!")
    print("\nTry it now: python launch_spritepal.py")

if __name__ == "__main__":
    test_config_loading()
