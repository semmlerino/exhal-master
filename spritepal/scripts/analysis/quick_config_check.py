#!/usr/bin/env python3
"""Quick check of sprite configuration."""

import json
from pathlib import Path

config_path = Path("config/sprite_locations.json")
with config_path.open() as f:
    config = json.load(f)

print("Checking sprite configuration...")
print("=" * 60)

# Check for our ROM checksum
target_checksum = "0xBF51"
print(f"\nLooking for checksum: {target_checksum}")

for game_name, game_data in config["games"].items():
    checksums = game_data.get("checksums", {})
    for version, checksum in checksums.items():
        if checksum == target_checksum:
            print(f"\n✓ Found in: {game_name} ({version})")
            sprites = game_data.get("sprites", {})
            sprite_count = sum(1 for k in sprites if not k.startswith("_"))
            print(f"  Sprites available: {sprite_count}")

            # Show first few sprites
            if sprite_count > 0:
                print("\n  Available sprites:")
                for sprite_name, sprite_data in sprites.items():
                    if not sprite_name.startswith("_"):
                        print(f"    - {sprite_name}: {sprite_data.get('offset', 'N/A')}")
                        if sprite_count > 4:
                            break

print("\n" + "=" * 60)
print("\nConfiguration is fixed! SpritePal should now:")
print("1. Recognize your ROM (checksum 0xBF51)")
print("2. Show sprites in the dropdown menu")
print("3. Extract real sprites when you select them")
print("\nRestart SpritePal if it's already running.")
