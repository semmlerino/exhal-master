#!/usr/bin/env python3
"""
Create diagnostic views of different VRAM regions with multiple palette options
to help identify the correct palette for each sprite group.
"""

import sys

sys.path.append("sprite_editor")

import struct

from PIL import Image, ImageDraw

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

def render_region_with_palette(vram_data, offset, size_tiles, palette, tiles_per_row=8):
    """Render a region of VRAM with a specific palette"""
    tiles_y = (size_tiles + tiles_per_row - 1) // tiles_per_row
    width = tiles_per_row * 8
    height = tiles_y * 8

    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))

    for tile_idx in range(size_tiles):
        tile_offset = offset + (tile_idx * 32)

        if tile_offset + 32 <= len(vram_data):
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

    return img

def main():
    print("=== Diagnostic Palette Region Analysis ===")

    vram_file = "SnesVideoRam.VRAM.dmp"
    cgram_file = "SnesCgRam.dmp"

    # Load all OBJ palettes
    obj_palettes = {}
    for i in range(8):
        obj_palettes[i] = read_obj_palette(cgram_file, i)
        print(f"Loaded OBJ palette {i}")

    # Read VRAM
    with open(vram_file, "rb") as f:
        vram_data = f.read()

    # Define regions to analyze
    regions = [
        ("Enemy Region 1 (0xD800)", 0xD800, 64),
        ("Enemy Region 2 (0xE000)", 0xE000, 64),
        ("Items Region (0xE800)", 0xE800, 64),
        ("Effects Region (0xF000)", 0xF000, 64),
    ]

    # Test each region with different palettes
    test_palettes = [0, 1, 2, 3, 4, 5, 6, 7]  # All OBJ palettes

    for region_name, offset, size in regions:
        print(f"\nProcessing {region_name}...")

        # Create a grid showing the region with each palette
        grid_width = 4
        grid_height = 2
        cell_size = 128  # 8 tiles wide = 64 pixels, scale up

        grid_img = Image.new("RGB",
                           (cell_size * grid_width, cell_size * grid_height + 40),
                           (32, 32, 32))
        draw = ImageDraw.Draw(grid_img)

        # Title
        draw.text((grid_img.width // 2, 10), region_name,
                 fill=(255, 255, 255), anchor="mt")

        for i, pal_num in enumerate(test_palettes):
            x_pos = (i % grid_width) * cell_size
            y_pos = (i // grid_width) * cell_size + 40

            # Render region with this palette
            region_img = render_region_with_palette(vram_data, offset, size,
                                                   obj_palettes[pal_num])

            # Scale up for visibility
            region_img = region_img.resize((64, 64), resample=Image.NEAREST)

            # Paste into grid
            grid_img.paste(region_img, (x_pos + 32, y_pos + 20))

            # Label
            label = f"OAM P{pal_num}"
            cgram_label = f"(CGRAM P{pal_num + 8})"

            draw.text((x_pos + cell_size // 2, y_pos + 5), label,
                     fill=(255, 255, 255), anchor="mt")
            draw.text((x_pos + cell_size // 2, y_pos + 90), cgram_label,
                     fill=(128, 128, 128), anchor="mt")

        filename = f"diagnose_{region_name.lower().replace(' ', '_').replace('(', '').replace(')', '')}.png"
        grid_img.save(filename)
        print(f"✓ Saved {filename}")

    # Also create a single sprite showcase for each active palette
    print("\n\nCreating individual palette showcases...")

    # We know palettes 0 and 4 are active
    active_palettes = [0, 4]

    for pal_num in active_palettes:
        showcase_img = Image.new("RGB", (512, 300), (32, 32, 32))
        draw = ImageDraw.Draw(showcase_img)

        title = f"OAM Palette {pal_num} (CGRAM Palette {pal_num + 8}) Showcase"
        draw.text((256, 20), title, fill=(255, 255, 255), anchor="mt")

        # Show sprites from different regions
        y_offset = 50

        showcase_regions = [
            ("Kirby", 0xC000, 32, 8),
            ("Enemies 1", 0xD800, 32, 8),
            ("Enemies 2", 0xE000, 32, 8),
            ("Items", 0xE800, 32, 8),
        ]

        for region_name, offset, size, tiles_per_row in showcase_regions:
            region_img = render_region_with_palette(vram_data, offset, size,
                                                   obj_palettes[pal_num], tiles_per_row)
            region_img = region_img.resize((region_img.width * 2, region_img.height * 2),
                                         resample=Image.NEAREST)

            draw.text((20, y_offset), region_name + ":", fill=(200, 200, 200))
            showcase_img.paste(region_img, (120, y_offset))

            y_offset += region_img.height + 20

        showcase_img.save(f"showcase_oam_palette_{pal_num}.png")
        print(f"✓ Created showcase_oam_palette_{pal_num}.png")

    print("\n=== Diagnostic images created! ===")
    print("Check the diagnose_*.png files to identify correct palettes for each region")

if __name__ == "__main__":
    main()
