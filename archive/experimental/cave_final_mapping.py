#!/usr/bin/env python3
"""
Final Cave area sprite mapping with correct palette assignments from OAM data.
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

def identify_sprite_type(tiles):
    """Identify sprite type based on tile numbers"""
    if any(t < 32 for t in tiles):
        return "Kirby"
    if any(32 <= t < 64 for t in tiles):
        return "UI/Numbers"
    if any(160 <= t < 192 for t in tiles):
        return "Cave Enemies"
    return "Other"

def main():
    print("=== Cave Area Final Palette Mapping ===\n")

    vram_file = "Cave.SnesVideoRam.dmp"
    cgram_file = "Cave.SnesCgRam.dmp"
    oam_file = "Cave.SnesSpriteRam.dmp"

    # Load OAM data
    mapper = OAMPaletteMapper()
    mapper.parse_oam_dump(oam_file)

    # Analyze palette usage by sprite type
    palette_analysis = {}
    tile_to_palette = {}

    for sprite in mapper.oam_entries:
        if sprite["y"] < 224:  # Visible sprites
            pal = sprite["palette"]
            tile = sprite["tile"]

            # Map tiles
            tile_to_palette[tile] = pal
            if sprite["size"] == "large":
                for offset in [1, 16, 17]:
                    tile_to_palette[tile + offset] = pal

            # Categorize sprite
            sprite_type = identify_sprite_type([tile])

            if sprite_type not in palette_analysis:
                palette_analysis[sprite_type] = {}
            if pal not in palette_analysis[sprite_type]:
                palette_analysis[sprite_type][pal] = {
                    "count": 0,
                    "tiles": []
                }

            palette_analysis[sprite_type][pal]["count"] += 1
            palette_analysis[sprite_type][pal]["tiles"].append(tile)

    print("Sprite type analysis:")
    for sprite_type, palettes in palette_analysis.items():
        print(f"\n{sprite_type}:")
        for pal, info in palettes.items():
            tiles_str = str(sorted(info["tiles"])[:5])
            print(f"  Palette {pal}: {info['count']} sprites, tiles {tiles_str}")

    # Load palettes
    obj_palettes = {}
    for i in [0, 4, 6]:  # Only load active palettes
        obj_palettes[i] = read_obj_palette(cgram_file, i)

    # Create full sheet
    print("\n\nCreating full sprite sheet...")

    with open(vram_file, "rb") as f:
        f.seek(0xC000)
        vram_data = f.read(0x4000)

    tiles_per_row = 16
    total_tiles = 512
    width = tiles_per_row * 8
    height = (total_tiles // tiles_per_row) * 8

    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))

    # Define regions based on Cave area layout
    regions = [
        (0, 32, 0),      # Kirby sprites (tiles 0-31) - Palette 0
        (32, 32, 4),     # UI/Numbers (tiles 32-63) - Palette 4
        (64, 96, 0),     # Unused area - default to 0
        (160, 32, 6),    # Cave enemies (tiles 160-191) - Palette 6
        (192, 320, 0),   # Rest - default to 0
    ]

    # Process tiles
    for start_tile, count, default_pal in regions:
        for i in range(count):
            tile_idx = start_tile + i

            if tile_idx < total_tiles:
                tile_offset = tile_idx * 32

                if tile_offset + 32 <= len(vram_data):
                    # Use OAM mapping if available, otherwise default
                    oam_pal = tile_to_palette.get(tile_idx, default_pal)

                    if oam_pal in obj_palettes:
                        palette = obj_palettes[oam_pal]

                        # Decode tile
                        tile_pixels = decode_4bpp_tile(vram_data, tile_offset)

                        tile_x = tile_idx % tiles_per_row
                        tile_y = tile_idx // tiles_per_row

                        # Draw pixels
                        for y in range(8):
                            for x in range(8):
                                pixel_idx = y * 8 + x
                                if pixel_idx < len(tile_pixels):
                                    color_idx = tile_pixels[pixel_idx]

                                    if color_idx > 0 and color_idx * 3 + 2 < len(palette):
                                        r = palette[color_idx * 3]
                                        g = palette[color_idx * 3 + 1]
                                        b = palette[color_idx * 3 + 2]

                                        px = tile_x * 8 + x
                                        py = tile_y * 8 + y
                                        if px < width and py < height:
                                            img.putpixel((px, py), (r, g, b, 255))

    # Save results
    img.save("cave_final_sheet.png")
    scaled2x = img.resize((img.width * 2, img.height * 2), resample=Image.NEAREST)
    scaled2x.save("cave_final_sheet_2x.png")
    scaled4x = img.resize((img.width * 4, img.height * 4), resample=Image.NEAREST)
    scaled4x.save("cave_final_sheet_4x.png")

    print("✓ Created cave_final_sheet.png (and 2x, 4x versions)")

    # Create detailed showcase
    print("\nCreating detailed character showcase...")

    showcase = Image.new("RGB", (600, 400), (32, 32, 32))
    draw = ImageDraw.Draw(showcase)

    draw.text((300, 20), "Cave Area - Correct Palette Mapping",
              fill=(255, 255, 255), anchor="mt")

    # Palette descriptions
    palette_info = [
        (0, "Pink Kirby", [224,56,248], [0, 2, 3, 4]),
        (4, "UI/Numbers", [248,248,248], [32, 34, 35, 36]),
        (6, "Cave Enemies", [248,248,248], [160, 162, 176, 178]),
    ]

    y_pos = 60
    for pal_num, description, main_color, example_tiles in palette_info:
        # Palette header
        draw.text((20, y_pos), f"Palette {pal_num} - {description}:",
                 fill=(200, 200, 200))
        draw.text((250, y_pos), f"Main: RGB({main_color[0]},{main_color[1]},{main_color[2]})",
                 fill=(main_color[0], main_color[1], main_color[2]))

        # Show tiles
        x_pos = 20
        y_tile_pos = y_pos + 25

        for tile_idx in example_tiles[:6]:
            if tile_idx * 32 + 32 <= len(vram_data):
                # Create tile
                tile_img = Image.new("RGBA", (8, 8), (0, 0, 0, 0))
                tile_pixels = decode_4bpp_tile(vram_data, tile_idx * 32)
                palette = obj_palettes[pal_num]

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
                tile_img = tile_img.resize((40, 40), resample=Image.NEAREST)
                showcase.paste(tile_img, (x_pos, y_tile_pos))

                # Tile number
                draw.text((x_pos + 20, y_tile_pos + 42), str(tile_idx),
                         fill=(128, 128, 128), anchor="mt")

                x_pos += 45

        y_pos += 90

    # Summary
    draw.text((20, y_pos + 20), "Summary: Cave area uses OAM palettes 0, 4, and 6",
             fill=(0, 255, 0))
    draw.text((20, y_pos + 40), "Palette 0: Pink Kirby | Palette 4: UI | Palette 6: Cave enemies",
             fill=(200, 200, 200))

    showcase.save("cave_detailed_showcase.png")
    print("✓ Created cave_detailed_showcase.png")

    print("\n=== Complete! ===")
    print("\nFinal Cave area palette mapping:")
    print("- Kirby (tiles 0-31): Palette 0 (Pink/Purple)")
    print("- UI/Numbers (tiles 32-63): Palette 4 (White/Orange)")
    print("- Cave Enemies (tiles 160-191): Palette 6 (Yellow/Brown)")

if __name__ == "__main__":
    main()
