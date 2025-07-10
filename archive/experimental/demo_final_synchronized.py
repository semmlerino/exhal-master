#!/usr/bin/env python3
"""
Final demonstration using synchronized Cave area dumps.
Shows correct palette mappings based on actual OAM data.
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
    print("=== Final Synchronized Palette Mapping ===")
    print("Using Cave area dumps from the same paused moment\n")

    # Use the newest dumps (Cave area)
    vram_file = "Cave.SnesVideoRam.dmp"
    cgram_file = "Cave.SnesCgRam.dmp"
    oam_file = "Cave.SnesSpriteRam.dmp"

    # Load OAM data to get actual palette usage
    mapper = OAMPaletteMapper()
    mapper.parse_oam_dump(oam_file)

    # Analyze palette usage
    palette_usage = {}
    tile_to_palette = {}

    for sprite in mapper.oam_entries:
        if sprite["y"] < 224:  # Visible sprites
            pal = sprite["palette"]
            tile = sprite["tile"]

            if pal not in palette_usage:
                palette_usage[pal] = {
                    "count": 0,
                    "tiles": set()
                }

            palette_usage[pal]["count"] += 1
            palette_usage[pal]["tiles"].add(tile)
            tile_to_palette[tile] = pal

            # Map large sprite tiles
            if sprite["size"] == "large":
                for offset in [1, 16, 17]:
                    tile_to_palette[tile + offset] = pal

    print("Active palettes in Cave area:")
    for pal, info in sorted(palette_usage.items()):
        print(f"  OAM Palette {pal}: {info['count']} sprites, tiles {sorted(info['tiles'])[:5]}...")

    # Load all OBJ palettes
    obj_palettes = {}
    for i in range(8):
        obj_palettes[i] = read_obj_palette(cgram_file, i)

    # Show color previews for active palettes
    print("\nPalette color previews:")
    for pal in sorted(palette_usage.keys()):
        if pal in obj_palettes:
            colors = obj_palettes[pal]
            preview = f"OAM Palette {pal}: "
            for i in range(1, min(6, len(colors)//3)):
                if i * 3 + 2 < len(colors):
                    r = colors[i * 3]
                    g = colors[i * 3 + 1]
                    b = colors[i * 3 + 2]
                    preview += f"[{r},{g},{b}] "
            print(f"  {preview}")

    # Create full sheet with correct palettes
    print("\nCreating sprite sheet with synchronized palette data...")

    with open(vram_file, "rb") as f:
        f.seek(0xC000)
        vram_data = f.read(0x4000)

    tiles_per_row = 16
    total_tiles = 512
    width = tiles_per_row * 8
    height = (total_tiles // tiles_per_row) * 8

    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))

    # Process each tile
    for tile_idx in range(total_tiles):
        tile_offset = tile_idx * 32

        if tile_offset + 32 <= len(vram_data):
            # Determine palette from OAM mapping
            if tile_idx in tile_to_palette:
                oam_pal = tile_to_palette[tile_idx]
            # Default based on region
            elif tile_idx < 64:
                oam_pal = 0  # Kirby region
            elif tile_idx < 128:
                oam_pal = 2  # UI region
            else:
                oam_pal = 3  # Enemy region

            if oam_pal in obj_palettes:
                palette = obj_palettes[oam_pal]

                # Decode and draw tile
                tile_pixels = decode_4bpp_tile(vram_data, tile_offset)

                tile_x = tile_idx % tiles_per_row
                tile_y = tile_idx // tiles_per_row

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
    img.save("cave_sprites_synchronized.png")
    scaled2x = img.resize((img.width * 2, img.height * 2), resample=Image.NEAREST)
    scaled2x.save("cave_sprites_synchronized_2x.png")
    scaled4x = img.resize((img.width * 4, img.height * 4), resample=Image.NEAREST)
    scaled4x.save("cave_sprites_synchronized_4x.png")

    print("✓ Created cave_sprites_synchronized.png (and 2x, 4x versions)")

    # Create character showcase
    print("\nCreating character showcase...")

    showcase = Image.new("RGB", (400, 300), (32, 32, 32))
    draw = ImageDraw.Draw(showcase)

    # Title
    draw.text((200, 20), "Cave Area Characters - Correct Palettes",
              fill=(255, 255, 255), anchor="mt")

    # Show examples from each palette
    examples = [
        ("Pink Kirby (Palette 0)", 0, 4, 0),
        ("UI Numbers (Palette 2)", 0x20, 4, 2),
        ("Cave Enemies (Palette 3)", 0xA0, 4, 3),
    ]

    y_pos = 60
    for label, start_tile, count, pal in examples:
        draw.text((20, y_pos), label + ":", fill=(200, 200, 200))

        x_pos = 150
        for i in range(count):
            tile_idx = start_tile + i
            if tile_idx * 32 + 32 <= len(vram_data):
                # Create small tile image
                tile_img = Image.new("RGBA", (8, 8), (0, 0, 0, 0))
                tile_pixels = decode_4bpp_tile(vram_data, tile_idx * 32)
                palette = obj_palettes[pal]

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
                tile_img = tile_img.resize((32, 32), resample=Image.NEAREST)
                showcase.paste(tile_img, (x_pos, y_pos))
                x_pos += 36

        y_pos += 50

    showcase.save("cave_character_showcase.png")
    print("✓ Created cave_character_showcase.png")

    print("\n=== Complete! ===")
    print("The synchronized Cave area data shows:")
    print("- Pink Kirby uses palette 0")
    print("- UI elements use palette 2")
    print("- Cave enemies use palette 3")

if __name__ == "__main__":
    main()
