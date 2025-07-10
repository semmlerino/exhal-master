#!/usr/bin/env python3
"""
Create full sprite sheet using known palette mappings from OAM,
and clearly marking which tiles we don't have palette data for.
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
    print("=== Creating Full Sheet with Known Palettes ===\n")

    vram_file = "Cave.SnesVideoRam.dmp"
    cgram_file = "Cave.SnesCgRam.dmp"
    oam_file = "Cave.SnesSpriteRam.dmp"

    # Load OAM data
    mapper = OAMPaletteMapper()
    mapper.parse_oam_dump(oam_file)

    # Build tile-to-palette mapping from visible sprites
    known_tile_palettes = {}

    for sprite in mapper.oam_entries:
        if sprite["y"] < 224:  # Visible sprites
            pal = sprite["palette"]
            tile = sprite["tile"]

            known_tile_palettes[tile] = pal

            # Map large sprite tiles
            if sprite["size"] == "large":
                for offset in [1, 16, 17]:
                    known_tile_palettes[tile + offset] = pal

    print(f"From OAM data, we know palettes for {len(known_tile_palettes)} tiles:")
    for pal in sorted(set(known_tile_palettes.values())):
        tiles = [t for t, p in known_tile_palettes.items() if p == pal]
        print(f"  Palette {pal}: tiles {sorted(tiles)}")

    # Load palettes
    obj_palettes = {}
    for i in range(8):
        obj_palettes[i] = read_obj_palette(cgram_file, i)

    # Load VRAM
    with open(vram_file, "rb") as f:
        f.seek(0xC000)
        vram_data = f.read(0x4000)

    # Create multiple versions to show the issue
    tiles_per_row = 16
    total_tiles = 512
    width = tiles_per_row * 8
    height = (total_tiles // tiles_per_row) * 8

    # Version 1: Only show tiles we know palettes for
    print("\n1. Creating sheet with only known palette tiles...")
    img_known = Image.new("RGBA", (width, height), (64, 64, 64, 255))

    known_count = 0
    for tile_idx in range(total_tiles):
        if tile_idx in known_tile_palettes:
            tile_offset = tile_idx * 32
            if tile_offset + 32 <= len(vram_data):
                pal = known_tile_palettes[tile_idx]
                if pal in obj_palettes:
                    palette = obj_palettes[pal]
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
                                        img_known.putpixel((px, py), (r, g, b, 255))
                    known_count += 1

    img_known.save("cave_known_palettes_only.png")
    scaled = img_known.resize((img_known.width * 2, img_known.height * 2), resample=Image.NEAREST)
    scaled.save("cave_known_palettes_only_2x.png")
    print(f"✓ Created cave_known_palettes_only.png (showing {known_count} tiles)")

    # Version 2: Show all tiles, using different palettes for each
    print("\n2. Creating diagnostic sheet showing all tiles with different palettes...")

    # Create a grid showing the same tiles with each palette
    showcase_width = 1200
    showcase_height = 800
    showcase = Image.new("RGB", (showcase_width, showcase_height), (32, 32, 32))
    draw = ImageDraw.Draw(showcase)

    draw.text((showcase_width // 2, 20), "Cave Sprite Sheet - Palette Comparison",
              fill=(255, 255, 255), anchor="mt")

    # Show some example tile ranges with different palettes
    tile_groups = [
        ("Kirby area (0-31)", 0, 16),
        ("UI area (32-63)", 32, 16),
        ("Enemy area (160-191)", 160, 16),
    ]

    y_pos = 60
    for group_name, start_tile, count in tile_groups:
        draw.text((20, y_pos), group_name, fill=(200, 200, 200))

        # Show with each of the active palettes
        x_offset = 20
        for test_pal in [0, 4, 6]:
            draw.text((x_offset, y_pos + 20), f"Palette {test_pal}:",
                     fill=(150, 150, 150))

            # Create small grid
            for i in range(min(8, count)):
                tile_idx = start_tile + i
                if tile_idx * 32 + 32 <= len(vram_data):
                    tile_img = Image.new("RGBA", (8, 8), (0, 0, 0, 0))
                    tile_pixels = decode_4bpp_tile(vram_data, tile_idx * 32)
                    palette = obj_palettes[test_pal]

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
                    tile_img = tile_img.resize((24, 24), resample=Image.NEAREST)
                    showcase.paste(tile_img, (x_offset + (i % 4) * 28,
                                            y_pos + 40 + (i // 4) * 28))

            x_offset += 140

        y_pos += 100

    # Add explanation
    draw.text((20, y_pos + 20), "Problem: OAM only shows palettes for sprites visible in this frame.",
             fill=(255, 255, 100))
    draw.text((20, y_pos + 40), "The full sprite sheet contains many more tiles not currently on screen.",
             fill=(200, 200, 200))
    draw.text((20, y_pos + 60), "We need savestate data from different game moments to map all tiles.",
             fill=(200, 200, 200))

    showcase.save("cave_palette_comparison.png")
    print("✓ Created cave_palette_comparison.png")

    # Version 3: Show which tiles we're missing
    print("\n3. Creating visualization of missing palette data...")

    missing_viz = Image.new("RGB", (width * 2, height * 2), (32, 32, 32))
    draw = ImageDraw.Draw(missing_viz)

    for tile_idx in range(total_tiles):
        tile_x = (tile_idx % tiles_per_row) * 16
        tile_y = (tile_idx // tiles_per_row) * 16

        if tile_idx in known_tile_palettes:
            # Known palette - color code by palette
            pal = known_tile_palettes[tile_idx]
            colors = {0: (255, 100, 255), 4: (255, 200, 100), 6: (100, 255, 255)}
            color = colors.get(pal, (128, 128, 128))
            draw.rectangle([tile_x, tile_y, tile_x + 15, tile_y + 15],
                         fill=color, outline=(200, 200, 200))
            draw.text((tile_x + 8, tile_y + 8), str(tile_idx),
                     fill=(0, 0, 0), anchor="mm")
        else:
            # Unknown palette
            draw.rectangle([tile_x, tile_y, tile_x + 15, tile_y + 15],
                         fill=(64, 64, 64), outline=(100, 100, 100))
            draw.text((tile_x + 8, tile_y + 8), "?",
                     fill=(150, 150, 150), anchor="mm")

    missing_viz.save("cave_palette_coverage.png")
    print("✓ Created cave_palette_coverage.png")

    print("\n=== Summary ===")
    print(f"Total tiles in sprite sheet: {total_tiles}")
    print(f"Tiles with known palettes: {len(known_tile_palettes)} ({len(known_tile_palettes)/total_tiles*100:.1f}%)")
    print(f"Tiles with unknown palettes: {total_tiles - len(known_tile_palettes)} ({(total_tiles - len(known_tile_palettes))/total_tiles*100:.1f}%)")
    print("\nTo get complete palette mappings, we would need:")
    print("- Multiple synchronized dumps from different game moments")
    print("- Or a way to determine palette assignments for off-screen sprites")

if __name__ == "__main__":
    main()
