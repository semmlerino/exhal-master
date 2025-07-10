#!/usr/bin/env python3
"""
Analyze and visualize the actual tile-to-palette mapping from OAM data.
Shows which specific tiles use which palettes without assuming regions.
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
    print("=== Analyzing Actual Tile-to-Palette Mapping ===\n")

    vram_file = "Cave.SnesVideoRam.dmp"
    cgram_file = "Cave.SnesCgRam.dmp"
    oam_file = "Cave.SnesSpriteRam.dmp"

    # Load OAM data
    mapper = OAMPaletteMapper()
    mapper.parse_oam_dump(oam_file)

    # Build precise tile-to-palette mapping
    tile_to_palette = {}
    sprite_positions = {}  # Track where sprites are on screen

    for sprite in mapper.oam_entries:
        if sprite["y"] < 224:  # Visible sprites
            pal = sprite["palette"]
            tile = sprite["tile"]

            tile_to_palette[tile] = pal
            sprite_positions[tile] = {"x": sprite["x"], "y": sprite["y"], "size": sprite["size"]}

            # Map large sprite tiles
            if sprite["size"] == "large":
                for offset in [1, 16, 17]:
                    tile_to_palette[tile + offset] = pal

    print(f"OAM mapping shows {len(tile_to_palette)} tiles with explicit palette assignments:")

    # Group by palette
    palette_groups = {}
    for tile, pal in sorted(tile_to_palette.items()):
        if pal not in palette_groups:
            palette_groups[pal] = []
        palette_groups[pal].append(tile)

    for pal, tiles in sorted(palette_groups.items()):
        print(f"\nPalette {pal}: {len(tiles)} tiles")
        print(f"  Tile numbers: {sorted(tiles)}")

    # Load palettes
    obj_palettes = {}
    for i in range(8):
        obj_palettes[i] = read_obj_palette(cgram_file, i)

    # Load VRAM
    with open(vram_file, "rb") as f:
        f.seek(0xC000)
        vram_data = f.read(0x4000)

    # Create visualization showing tile ranges and their palettes
    print("\n\nCreating tile range visualization...")

    viz_width = 800
    viz_height = 600
    viz = Image.new("RGB", (viz_width, viz_height), (32, 32, 32))
    draw = ImageDraw.Draw(viz)

    # Title
    draw.text((viz_width // 2, 20), "Cave Area - Actual Tile-to-Palette Mapping",
              fill=(255, 255, 255), anchor="mt")

    # Show tile ranges
    y_pos = 60
    tile_ranges = [
        ("Tiles 0-31 (Player area)", 0, 32),
        ("Tiles 32-63 (UI area)", 32, 32),
        ("Tiles 64-159 (Various)", 64, 96),
        ("Tiles 160-191 (Enemy area)", 160, 32),
        ("Tiles 192+ (Other)", 192, 64),
    ]

    for range_name, start_tile, count in tile_ranges:
        draw.text((20, y_pos), range_name + ":", fill=(200, 200, 200))

        # Check which palettes are used in this range
        palettes_in_range = {}
        for tile in range(start_tile, start_tile + count):
            if tile in tile_to_palette:
                pal = tile_to_palette[tile]
                if pal not in palettes_in_range:
                    palettes_in_range[pal] = []
                palettes_in_range[pal].append(tile)

        if palettes_in_range:
            x_offset = 250
            for pal, tiles in sorted(palettes_in_range.items()):
                color = [(224,56,248), (0,0,0), (0,0,0), (0,0,0),
                        (248,248,248), (0,0,0), (128,224,232), (0,0,0)][pal]

                text = f"Pal {pal}: tiles {tiles[:3]}{'...' if len(tiles) > 3 else ''}"
                draw.text((x_offset, y_pos), text, fill=color)
                x_offset += 150
        else:
            draw.text((250, y_pos), "No active sprites", fill=(128, 128, 128))

        y_pos += 30

    # Create tile grid showing actual palette usage
    y_pos += 20
    draw.text((20, y_pos), "Tile Grid (colored by palette):", fill=(255, 255, 255))

    grid_start_y = y_pos + 30
    grid_size = 8
    tiles_per_row = 32

    # Define palette colors for visualization
    palette_colors = {
        0: (255, 100, 255),  # Pink for Kirby
        4: (255, 200, 100),  # Orange for UI
        6: (100, 255, 255),  # Cyan for enemies
    }

    for tile_idx in range(256):  # Show first 256 tiles
        if tile_idx in tile_to_palette:
            pal = tile_to_palette[tile_idx]
            color = palette_colors.get(pal, (128, 128, 128))
        else:
            color = (64, 64, 64)  # Dark gray for unmapped

        x = 20 + (tile_idx % tiles_per_row) * grid_size
        y = grid_start_y + (tile_idx // tiles_per_row) * grid_size

        draw.rectangle([x, y, x + grid_size - 1, y + grid_size - 1],
                      fill=color, outline=(32, 32, 32))

    # Legend
    legend_y = grid_start_y + 9 * grid_size
    draw.text((20, legend_y), "Legend:", fill=(255, 255, 255))
    for i, (pal, color) in enumerate(palette_colors.items()):
        x = 80 + i * 100
        draw.rectangle([x, legend_y, x + 20, legend_y + 20], fill=color)
        draw.text((x + 25, legend_y + 10), f"Palette {pal}", fill=(200, 200, 200), anchor="lm")

    viz.save("tile_palette_mapping_analysis.png")
    print("✓ Created tile_palette_mapping_analysis.png")

    # Create corrected showcase with actual mappings
    print("\nCreating corrected showcase...")

    showcase = Image.new("RGB", (800, 500), (32, 32, 32))
    draw = ImageDraw.Draw(showcase)

    draw.text((400, 20), "Cave Area - Corrected Tile Display",
              fill=(255, 255, 255), anchor="mt")

    # Show specific examples with their actual palettes
    examples = [
        ("Pink Kirby (Actual mapping)", [(0, 0), (2, 0), (3, 0), (4, 0)]),
        ("UI Numbers (Actual mapping)", [(32, 4), (34, 4), (35, 4), (36, 4)]),
        ("Cave Enemies (Actual mapping)", [(160, 6), (162, 6), (176, 6), (178, 6)]),
    ]

    y_pos = 60
    for title, tile_palette_pairs in examples:
        draw.text((20, y_pos), title + ":", fill=(200, 200, 200))

        x_pos = 20
        for tile_idx, actual_pal in tile_palette_pairs:
            if tile_idx * 32 + 32 <= len(vram_data) and actual_pal in obj_palettes:
                # Create tile with its actual palette
                tile_img = Image.new("RGBA", (8, 8), (0, 0, 0, 0))
                tile_pixels = decode_4bpp_tile(vram_data, tile_idx * 32)
                palette = obj_palettes[actual_pal]

                for y in range(8):
                    for x in range(8):
                        pixel_idx = y * 8 + x
                        if pixel_idx < len(tile_pixels):
                            color_idx = tile_pixels[pixel_idx]
                            if color_idx > 0 and color_idx * 3 + 2 < len(palette):
                                r = palette[color_idx * 3]
                                g = palette[color_idx * 3 + 1]
                                b = palette[color_idx * 3 + 2]
                                tile_img.putpixel((x, y), (r, g, b, 255))

                # Scale and paste
                tile_img = tile_img.resize((48, 48), resample=Image.NEAREST)
                showcase.paste(tile_img, (x_pos, y_pos + 25))

                # Label with tile number and palette
                draw.text((x_pos + 24, y_pos + 75), f"T{tile_idx}",
                         fill=(128, 128, 128), anchor="mt")
                draw.text((x_pos + 24, y_pos + 90), f"P{actual_pal}",
                         fill=palette_colors.get(actual_pal, (200, 200, 200)), anchor="mt")

                x_pos += 60

        y_pos += 120

    # Add note about mapping
    draw.text((20, y_pos), "Note: Palettes are assigned per-sprite in OAM, not by region!",
             fill=(255, 255, 100))
    draw.text((20, y_pos + 20), "Some tiles in the same area may use different palettes.",
             fill=(200, 200, 200))

    showcase.save("cave_corrected_showcase.png")
    print("✓ Created cave_corrected_showcase.png")

    print("\n=== Analysis Complete ===")
    print("The OAM data shows that palettes are assigned per-sprite,")
    print("not by region. This is why tiles in the same area may use")
    print("different palettes depending on the game state.")

if __name__ == "__main__":
    main()
