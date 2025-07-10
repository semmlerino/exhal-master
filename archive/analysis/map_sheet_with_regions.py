#!/usr/bin/env python3
"""
Map the entire sprite sheet with correct palettes based on region analysis.
Since only OAM palettes 0 and 4 are active in this frame, we'll use region-based mapping.
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

def main():
    print("=== Mapping Sheet with Region-Based Palette Assignment ===")

    vram_file = "SnesVideoRam.VRAM.dmp"
    cgram_file = "SnesCgRam.dmp"
    oam_file = "SnesSpriteRam.OAM.dmp"

    # Load OAM to understand sprite mapping
    mapper = OAMPaletteMapper()
    mapper.parse_oam_dump(oam_file)

    # Build tile-to-palette mapping from OAM
    tile_to_palette = {}
    for sprite in mapper.oam_entries:
        if sprite["y"] < 224:  # Visible sprites
            tile = sprite["tile"]
            pal = sprite["palette"]
            tile_to_palette[tile] = pal

            # For large sprites, map additional tiles
            if sprite["size"] == "large":
                tile_to_palette[tile + 1] = pal
                tile_to_palette[tile + 16] = pal
                tile_to_palette[tile + 17] = pal

    print(f"Mapped {len(tile_to_palette)} tiles from OAM data")

    # Define regions and their typical palette assignments
    # Based on common Kirby sprite sheet organization
    regions = [
        # (name, vram_offset, size_tiles, default_oam_palette)
        ("Kirby sprites", 0xC000, 128, 0),      # First 128 tiles - Kirby
        ("UI/HUD elements", 0xD000, 64, 0),     # Next 64 tiles - UI
        ("Enemy sprites 1", 0xD800, 64, 4),     # Enemy group 1
        ("Enemy sprites 2", 0xE000, 64, 4),     # Enemy group 2
        ("Items/Powerups", 0xE800, 64, 0),      # Items (might use pal 0)
        ("Effects/Particles", 0xF000, 64, 4),   # Effects
    ]

    # Load all OBJ palettes we might need
    obj_palettes = {}
    for i in range(8):
        obj_palettes[i] = read_obj_palette(cgram_file, i)

    # Read entire VRAM region
    with open(vram_file, "rb") as f:
        f.seek(0xC000)
        vram_data = f.read(0x4000)  # 16KB of sprite data

    # Calculate full sheet dimensions
    tiles_per_row = 16
    total_tiles = len(vram_data) // 32
    tiles_y = (total_tiles + tiles_per_row - 1) // tiles_per_row

    width = tiles_per_row * 8
    height = tiles_y * 8

    # Create full sheet image
    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))

    # Track which tiles we actually render
    rendered_tiles = set()

    # Process each tile
    for tile_idx in range(total_tiles):
        tile_offset = tile_idx * 32

        if tile_offset + 32 <= len(vram_data):
            # Determine VRAM address for this tile
            vram_addr = 0xC000 + tile_offset

            # Determine palette based on region or OAM mapping
            oam_pal = 0  # Default to palette 0

            # First check if OAM explicitly maps this tile
            if tile_idx in tile_to_palette:
                oam_pal = tile_to_palette[tile_idx]
            else:
                # Use region-based assignment
                for region_name, region_start, region_size, default_pal in regions:
                    region_end = region_start + (region_size * 32)
                    if region_start <= vram_addr < region_end:
                        oam_pal = default_pal
                        break

            # Get the palette
            if oam_pal in obj_palettes:
                palette = obj_palettes[oam_pal]

                # Decode and draw tile
                tile_pixels = decode_4bpp_tile(vram_data, tile_offset)

                tile_x = tile_idx % tiles_per_row
                tile_y = tile_idx // tiles_per_row

                has_content = False
                for y in range(8):
                    for x in range(8):
                        pixel_idx = y * 8 + x
                        if pixel_idx < len(tile_pixels):
                            color_idx = tile_pixels[pixel_idx]

                            if color_idx > 0:  # Non-transparent
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
                    rendered_tiles.add(tile_idx)

    print(f"\nRendered {len(rendered_tiles)} non-empty tiles")

    # Save results
    img.save("full_sheet_region_based.png")
    scaled = img.resize((img.width * 2, img.height * 2), resample=Image.NEAREST)
    scaled.save("full_sheet_region_based_2x.png")
    print("✓ Created full_sheet_region_based.png and 2x version")

    # Create a debug view showing palette assignments
    debug_img = Image.new("RGB", (width * 2, height * 2), (32, 32, 32))
    draw = ImageDraw.Draw(debug_img)

    # Color code by palette
    palette_colors = {
        0: (255, 192, 192),  # Light red for OAM pal 0
        4: (192, 192, 255),  # Light blue for OAM pal 4
    }

    for tile_idx in rendered_tiles:
        tile_x = (tile_idx % tiles_per_row) * 16
        tile_y = (tile_idx // tiles_per_row) * 16

        # Determine palette for this tile
        if tile_idx in tile_to_palette:
            pal = tile_to_palette[tile_idx]
        else:
            # Check region
            vram_addr = 0xC000 + (tile_idx * 32)
            pal = 0
            for _, region_start, region_size, default_pal in regions:
                region_end = region_start + (region_size * 32)
                if region_start <= vram_addr < region_end:
                    pal = default_pal
                    break

        if pal in palette_colors:
            draw.rectangle([tile_x, tile_y, tile_x + 15, tile_y + 15],
                         outline=palette_colors[pal], width=1)

    debug_img.save("palette_assignment_debug.png")
    print("✓ Created palette_assignment_debug.png (red=pal0, blue=pal4)")

    # Report on regions
    print("\nRegion analysis:")
    for region_name, region_start, region_size, default_pal in regions:
        region_tiles = []
        for tile_idx in range(total_tiles):
            vram_addr = 0xC000 + (tile_idx * 32)
            region_end = region_start + (region_size * 32)
            if region_start <= vram_addr < region_end and tile_idx in rendered_tiles:
                region_tiles.append(tile_idx)

        if region_tiles:
            print(f"  {region_name}: {len(region_tiles)} tiles (OAM palette {default_pal})")

if __name__ == "__main__":
    main()
