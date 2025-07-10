#!/usr/bin/env python3
"""
Generic script to apply correct palettes using synchronized memory dumps.
Works for any game area with synchronized VRAM, CGRAM, and OAM dumps.
"""

import os
import sys

sys.path.append("sprite_editor")

import struct

from PIL import Image

from sprite_editor.oam_palette_mapper import OAMPaletteMapper
from sprite_editor.tile_utils import decode_4bpp_tile


def read_obj_palette(cgram_data, obj_palette_num):
    """Read an OBJ palette from CGRAM data (not file)"""
    cgram_index = 128 + (obj_palette_num * 16)
    offset = cgram_index * 2

    palette = []
    for _i in range(16):
        if offset + 1 < len(cgram_data):
            color = struct.unpack("<H", cgram_data[offset:offset+2])[0]
            b = ((color >> 10) & 0x1F) * 8
            g = ((color >> 5) & 0x1F) * 8
            r = (color & 0x1F) * 8
            palette.extend([r, g, b])
            offset += 2

    return palette

def apply_synchronized_palettes(vram_file, cgram_file, oam_file, output_prefix="output"):
    """
    Apply correct palettes to sprites using synchronized dumps.

    Args:
        vram_file: Path to VRAM dump
        cgram_file: Path to CGRAM dump
        oam_file: Path to OAM dump
        output_prefix: Prefix for output files
    """
    print("Processing synchronized dumps:")
    print(f"  VRAM: {vram_file}")
    print(f"  CGRAM: {cgram_file}")
    print(f"  OAM: {oam_file}")

    # Load memory dumps
    with open(vram_file, "rb") as f:
        f.seek(0xC000)  # Sprite area
        vram_data = f.read(0x4000)

    with open(cgram_file, "rb") as f:
        cgram_data = f.read()

    # Parse OAM to get palette mappings
    mapper = OAMPaletteMapper()
    mapper.parse_oam_dump(oam_file)

    # Build tile-to-palette mapping
    tile_to_palette = {}
    active_palettes = set()

    for sprite in mapper.oam_entries:
        if sprite["y"] < 224:  # Visible sprites
            pal = sprite["palette"]
            tile = sprite["tile"]

            active_palettes.add(pal)
            tile_to_palette[tile] = pal

            # Map large sprite tiles
            if sprite["size"] == "large":
                for offset in [1, 16, 17]:
                    tile_to_palette[tile + offset] = pal

    print(f"\nActive OAM palettes: {sorted(active_palettes)}")
    print(f"Mapped {len(tile_to_palette)} tiles to palettes")

    # Load active palettes
    obj_palettes = {}
    for pal_num in range(8):
        obj_palettes[pal_num] = read_obj_palette(cgram_data, pal_num)

    # Create sprite sheet
    tiles_per_row = 16
    total_tiles = len(vram_data) // 32
    width = tiles_per_row * 8
    height = ((total_tiles + tiles_per_row - 1) // tiles_per_row) * 8

    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))

    # Process each tile
    rendered_count = 0
    for tile_idx in range(total_tiles):
        tile_offset = tile_idx * 32

        if tile_offset + 32 <= len(vram_data):
            # Determine palette
            if tile_idx in tile_to_palette:
                oam_pal = tile_to_palette[tile_idx]
            # Default palette assignment by region
            elif tile_idx < 64:
                oam_pal = 0  # Common for player sprites
            elif tile_idx < 128:
                oam_pal = min(active_palettes) if active_palettes else 0
            else:
                oam_pal = max(active_palettes) if active_palettes else 0

            if oam_pal in obj_palettes:
                palette = obj_palettes[oam_pal]

                # Decode tile
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
                    rendered_count += 1

    # Save outputs
    output_base = f"{output_prefix}_synchronized"

    img.save(f"{output_base}.png")
    img.resize((img.width * 2, img.height * 2), resample=Image.NEAREST).save(f"{output_base}_2x.png")
    img.resize((img.width * 4, img.height * 4), resample=Image.NEAREST).save(f"{output_base}_4x.png")

    print(f"\nRendered {rendered_count} non-empty tiles")
    print(f"Created: {output_base}.png (and 2x, 4x versions)")

    # Generate palette info report
    with open(f"{output_base}_palette_info.txt", "w") as f:
        f.write("Synchronized Palette Mapping Report\n")
        f.write("=" * 40 + "\n\n")

        f.write(f"Active OAM Palettes: {sorted(active_palettes)}\n\n")

        # Group tiles by palette
        palette_tiles = {}
        for tile, pal in tile_to_palette.items():
            if pal not in palette_tiles:
                palette_tiles[pal] = []
            palette_tiles[pal].append(tile)

        for pal in sorted(palette_tiles.keys()):
            tiles = sorted(palette_tiles[pal])
            f.write(f"Palette {pal} (CGRAM {pal + 8}):\n")
            f.write(f"  Tiles: {tiles[:10]}")
            if len(tiles) > 10:
                f.write(f"... ({len(tiles)} total)")
            f.write("\n")

            # Show first few colors
            if pal in obj_palettes:
                colors = obj_palettes[pal]
                f.write("  Colors: ")
                for i in range(1, min(5, len(colors)//3)):
                    if i * 3 + 2 < len(colors):
                        r = colors[i * 3]
                        g = colors[i * 3 + 1]
                        b = colors[i * 3 + 2]
                        f.write(f"[{r},{g},{b}] ")
                f.write("\n")
            f.write("\n")

    print(f"Created: {output_base}_palette_info.txt")

    return active_palettes, tile_to_palette

def main():
    """Example usage with command line arguments or default to Cave dumps"""
    if len(sys.argv) == 4:
        vram_file = sys.argv[1]
        cgram_file = sys.argv[2]
        oam_file = sys.argv[3]
        output_prefix = os.path.splitext(os.path.basename(vram_file))[0]
    else:
        # Default to Cave dumps
        vram_file = "Cave.SnesVideoRam.dmp"
        cgram_file = "Cave.SnesCgRam.dmp"
        oam_file = "Cave.SnesSpriteRam.dmp"
        output_prefix = "cave"

    apply_synchronized_palettes(vram_file, cgram_file, oam_file, output_prefix)

if __name__ == "__main__":
    main()
