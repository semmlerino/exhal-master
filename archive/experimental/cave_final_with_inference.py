#!/usr/bin/env python3
"""
Create the best possible sprite sheet using known palette mappings
and reasonable inferences for unmapped tiles based on patterns.
"""

import sys

sys.path.append("sprite_editor")

import struct

from PIL import Image, ImageDraw

from sprite_editor.oam_palette_mapper import OAMPaletteMapper
from sprite_editor.tile_utils import decode_4bpp_tile


def read_obj_palette(cgram_file, obj_palette_num):
    """Read an OBJ palette from CGRAM starting at index 128"""
    with open(cgram_file, "rb") as f:
        cgram_index = 128 + (obj_palette_num * 16)
        f.seek(cgram_index * 2)

        palette = []
        for _i in range(16):
            data = f.read(2)
            if len(data) < 2:
                break

            color = struct.unpack("<H", data)[0]
            b = ((color >> 10) & 0x1F) * 8
            g = ((color >> 5) & 0x1F) * 8
            r = (color & 0x1F) * 8

            palette.extend([r, g, b])

        return palette

def infer_palette_for_tile(tile_idx, known_mappings, vram_data):
    """
    Infer palette for unmapped tiles based on patterns and nearby mapped tiles.
    """
    # Check if any nearby tiles have known palettes
    search_offsets = [1, -1, 16, -16, 17, -17, 15, -15]

    for offset in search_offsets:
        neighbor = tile_idx + offset
        if neighbor in known_mappings:
            return known_mappings[neighbor]

    # Use default regions based on common sprite sheet organization
    if tile_idx < 32:
        return 0  # Player sprites typically use palette 0
    if tile_idx < 64:
        return 4  # UI elements often use a different palette
    if tile_idx >= 160 and tile_idx < 192:
        return 6  # Enemy region based on our known mappings
    if tile_idx >= 192 and tile_idx < 256:
        return 6  # Extended enemy region
    # Check if tile has content to decide
    if tile_idx * 32 + 32 <= len(vram_data):
        tile_pixels = decode_4bpp_tile(vram_data, tile_idx * 32)
        # If tile has significant content, assign based on position
        non_zero = sum(1 for p in tile_pixels if p > 0)
        if non_zero > 16:  # More than 25% filled
            if tile_idx < 128:
                return 0
            return 6

    return 0  # Default fallback

def main():
    print("=== Creating Final Cave Sprite Sheet with Inference ===\n")

    vram_file = "Cave.SnesVideoRam.dmp"
    cgram_file = "Cave.SnesCgRam.dmp"
    oam_file = "Cave.SnesSpriteRam.dmp"

    # Load OAM data for known mappings
    mapper = OAMPaletteMapper()
    mapper.parse_oam_dump(oam_file)

    # Build known mappings
    known_mappings = {}
    for sprite in mapper.oam_entries:
        if sprite["y"] < 224:
            pal = sprite["palette"]
            tile = sprite["tile"]
            known_mappings[tile] = pal

            if sprite["size"] == "large":
                for offset in [1, 16, 17]:
                    known_mappings[tile + offset] = pal

    print(f"Known palette mappings: {len(known_mappings)} tiles")

    # Load VRAM
    with open(vram_file, "rb") as f:
        f.seek(0xC000)
        vram_data = f.read(0x4000)

    # Load palettes
    obj_palettes = {}
    for i in range(8):
        obj_palettes[i] = read_obj_palette(cgram_file, i)

    # Create final sprite sheet
    tiles_per_row = 16
    total_tiles = 512
    width = tiles_per_row * 8
    height = (total_tiles // tiles_per_row) * 8

    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))

    # Track statistics
    stats = {
        "known": 0,
        "inferred": 0,
        "empty": 0,
        "by_palette": {0: 0, 4: 0, 6: 0}
    }

    # Process all tiles
    for tile_idx in range(total_tiles):
        tile_offset = tile_idx * 32

        if tile_offset + 32 <= len(vram_data):
            # Determine palette
            if tile_idx in known_mappings:
                pal = known_mappings[tile_idx]
                stats["known"] += 1
            else:
                pal = infer_palette_for_tile(tile_idx, known_mappings, vram_data)
                stats["inferred"] += 1

            if pal in obj_palettes:
                palette = obj_palettes[pal]
                tile_pixels = decode_4bpp_tile(vram_data, tile_offset)

                tile_x = tile_idx % tiles_per_row
                tile_y = tile_idx // tiles_per_row

                has_content = False
                for y in range(8):
                    for x in range(8):
                        pixel_idx = y * 8 + x
                        if pixel_idx < len(tile_pixels):
                            color_idx = tile_pixels[pixel_idx]

                            if color_idx > 0:
                                has_content = True
                                if color_idx * 3 + 2 < len(palette):
                                    r = palette[color_idx * 3]
                                    g = palette[color_idx * 3 + 1]
                                    b = palette[color_idx * 3 + 2]

                                    px = tile_x * 8 + x
                                    py = tile_y * 8 + y
                                    if px < width and py < height:
                                        img.putpixel((px, py), (r, g, b, 255))

                if has_content:
                    stats["by_palette"][pal] = stats["by_palette"].get(pal, 0) + 1
                else:
                    stats["empty"] += 1

    # Save results
    img.save("cave_final_inferred.png")
    for scale in [2, 4]:
        scaled = img.resize((img.width * scale, img.height * scale), resample=Image.NEAREST)
        scaled.save(f"cave_final_inferred_{scale}x.png")

    print("\n✓ Created cave_final_inferred.png (and 2x, 4x versions)")

    # Print statistics
    print("\nStatistics:")
    print(f"  Known mappings used: {stats['known']}")
    print(f"  Inferred mappings: {stats['inferred']}")
    print(f"  Empty tiles: {stats['empty']}")
    print("\nTiles per palette:")
    for pal, count in sorted(stats["by_palette"].items()):
        print(f"  Palette {pal}: {count} tiles")

    # Create a debug overlay showing which tiles are known vs inferred
    print("\nCreating debug overlay...")

    debug_scale = 4
    debug_img = img.resize((img.width * debug_scale, img.height * debug_scale),
                          resample=Image.NEAREST).convert("RGBA")
    debug_draw = ImageDraw.Draw(debug_img)

    for tile_idx in range(total_tiles):
        tile_x = (tile_idx % tiles_per_row) * 8 * debug_scale
        tile_y = (tile_idx // tiles_per_row) * 8 * debug_scale

        if tile_idx in known_mappings:
            # Draw green border for known mappings
            for i in range(2):
                debug_draw.rectangle([tile_x + i, tile_y + i,
                                    tile_x + 8 * debug_scale - 1 - i,
                                    tile_y + 8 * debug_scale - 1 - i],
                                   outline=(0, 255, 0, 128))

    debug_img.save("cave_final_debug_overlay.png")
    print("✓ Created cave_final_debug_overlay.png (green borders = known palettes)")

    # Create reference sheet
    print("\nCreating reference sheet...")

    ref_width = 800
    ref_height = 600
    ref = Image.new("RGB", (ref_width, ref_height), (32, 32, 32))
    ref_draw = ImageDraw.Draw(ref)

    ref_draw.text((ref_width // 2, 20), "Cave Area Sprite Sheet - Final Version",
                 fill=(255, 255, 255), anchor="mt")

    # Show examples
    y_pos = 60
    ref_draw.text((20, y_pos), "Known mappings (from OAM):", fill=(0, 255, 0))
    y_pos += 25

    for pal in [0, 4, 6]:
        tiles = [t for t, p in known_mappings.items() if p == pal][:4]
        if tiles:
            ref_draw.text((40, y_pos), f"Palette {pal}: tiles {tiles}",
                         fill=(200, 200, 200))
            y_pos += 20

    y_pos += 20
    ref_draw.text((20, y_pos), "Inference rules used:", fill=(255, 255, 100))
    y_pos += 25

    rules = [
        "• Tiles 0-31: Palette 0 (player sprites)",
        "• Tiles 32-63: Palette 4 (UI elements)",
        "• Tiles 160-255: Palette 6 (enemies)",
        "• Nearby tiles: Use neighbor's palette",
        "• Empty tiles: Skipped"
    ]

    for rule in rules:
        ref_draw.text((40, y_pos), rule, fill=(200, 200, 200))
        y_pos += 20

    ref.save("cave_final_reference.png")
    print("✓ Created cave_final_reference.png")

    print("\n=== Complete! ===")
    print("The sprite sheet has been created using:")
    print("- Known palette mappings from visible sprites")
    print("- Intelligent inference for remaining tiles")
    print("- Pattern-based assignment for common sprite types")

if __name__ == "__main__":
    main()
