#!/usr/bin/env python3
"""
Debug OAM mapping to understand why enemy palettes are wrong
"""

import sys

sys.path.append("sprite_editor")
from sprite_editor.oam_palette_mapper import OAMPaletteMapper


def debug_oam():
    mapper = OAMPaletteMapper()
    mapper.parse_oam_dump("OAM.dmp")

    print("=== OAM SPRITE ENTRIES ===")
    print("Showing first 20 visible sprites:")

    visible_sprites = [s for s in mapper.oam_entries if s["y"] < 224]
    for sprite in visible_sprites[:20]:
        print(f"\nSprite {sprite['index']}:")
        print(f"  Position: ({sprite['x']}, {sprite['y']})")
        print(f"  Tile number: {sprite['tile']} (0x{sprite['tile']:03X})")
        print(f"  Palette: {sprite['palette']}")
        print(f"  Size: {sprite['size']}")

        # Calculate approximate VRAM offset
        # This is a guess - sprites could be anywhere in VRAM
        # Tile 0 might start at different VRAM locations
        if sprite["tile"] < 0x100:  # Low tiles
            vram_offset = 0xC000 + (sprite["tile"] * 32)
            print(f"  Estimated VRAM offset: 0x{vram_offset:04X}")

    print("\n=== PALETTE ASSIGNMENTS ===")
    print("Tiles using each palette:")

    for pal_num in sorted(set(mapper.tile_palette_map.values())):
        tiles = [t for t, p in mapper.tile_palette_map.items() if p == pal_num]
        print(f"\nPalette {pal_num}: {len(tiles)} tiles")
        print(f"  Tile numbers: {', '.join(f'0x{t:03X}' for t in sorted(tiles)[:10])}")
        if len(tiles) > 10:
            print(f"  ... and {len(tiles) - 10} more")

if __name__ == "__main__":
    debug_oam()
