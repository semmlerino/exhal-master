#!/usr/bin/env python3
"""
Final sprite sheet mapping with user-specified palette assignments.
Based on our findings:
- Kirby (OAM 0) is correct
- Enemy group 1 palette 12 (OAM 4) is correct
- Other regions need palette specification
"""

import sys

sys.path.append("sprite_editor")

import struct

from PIL import Image

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
    print("=== Final Sprite Sheet Mapping ===")
    print("Based on our analysis:")
    print("- Kirby uses OAM palette 0 (CGRAM palette 8) ✓")
    print("- Enemy group 1 uses OAM palette 4 (CGRAM palette 12) ✓")
    print("\n")

    vram_file = "SnesVideoRam.VRAM.dmp"
    cgram_file = "SnesCgRam.dmp"

    # Define region mappings
    # Format: (name, vram_start, size_tiles, oam_palette, confirmed)
    regions = [
        ("Kirby sprites", 0xC000, 128, 0, True),      # Confirmed pink Kirby
        ("UI/HUD elements", 0xD000, 64, 0, False),    # Needs confirmation
        ("Enemy sprites 1", 0xD800, 64, 4, True),     # Confirmed palette 12
        ("Enemy sprites 2", 0xE000, 64, None, False), # Need palette info
        ("Items/Powerups", 0xE800, 64, None, False),  # Need palette info
        ("Effects/Particles", 0xF000, 64, None, False), # Need palette info
    ]

    print("Current region assignments:")
    for name, _start, _size, pal, confirmed in regions:
        status = "✓" if confirmed else "?"
        if pal is not None:
            print(f"  {status} {name}: OAM palette {pal} (CGRAM {pal+8})")
        else:
            print(f"  {status} {name}: UNKNOWN - needs palette assignment")

    print("\nTo complete the mapping, please specify palettes for unknown regions.")
    print("Available OAM palettes: 0-7 (map to CGRAM palettes 8-15)")
    print("\nBased on the synchronized dumps, active palettes are 0 and 4.")

    # For now, let's create a version with known mappings
    # and use different test palettes for unknown regions
    test_regions = [
        ("Kirby sprites", 0xC000, 128, 0),
        ("UI/HUD elements", 0xD000, 64, 0),     # Try palette 0
        ("Enemy sprites 1", 0xD800, 64, 4),     # Confirmed
        ("Enemy sprites 2", 0xE000, 64, 4),     # Try palette 4
        ("Items/Powerups", 0xE800, 64, 0),      # Try palette 0
        ("Effects/Particles", 0xF000, 64, 4),   # Try palette 4
    ]

    # Load palettes
    obj_palettes = {}
    for i in range(8):
        obj_palettes[i] = read_obj_palette(cgram_file, i)

    # Read VRAM
    with open(vram_file, "rb") as f:
        vram_data = f.read()

    # Create full sheet
    tiles_per_row = 16
    total_tiles = 512  # Full sprite area
    height = (total_tiles // tiles_per_row) * 8
    width = tiles_per_row * 8

    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))

    # Process tiles by region
    for region_name, vram_start, size_tiles, oam_pal in test_regions:
        start_offset = vram_start - 0xC000  # Relative to sprite area start

        for local_tile in range(size_tiles):
            global_tile = start_offset // 32 + local_tile

            if global_tile < total_tiles:
                tile_offset = global_tile * 32

                if tile_offset + 32 <= len(vram_data):
                    # Get palette
                    palette = obj_palettes.get(oam_pal, obj_palettes[0])

                    # Decode tile
                    tile_pixels = decode_4bpp_tile(vram_data[0xC000:], tile_offset)

                    tile_x = global_tile % tiles_per_row
                    tile_y = global_tile // tiles_per_row

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

    # Save result
    img.save("sheet_final_test.png")
    scaled = img.resize((img.width * 2, img.height * 2), resample=Image.NEAREST)
    scaled.save("sheet_final_test_2x.png")

    print("\n✓ Created sheet_final_test.png with current palette assignments")
    print("\nPlease check the output and let me know:")
    print("1. Which OAM palette should Enemy sprites 2 use?")
    print("2. Which OAM palette should Items/Powerups use?")
    print("3. Which OAM palette should Effects/Particles use?")

    # Also create individual region previews for easier checking
    print("\nCreating individual region previews...")

    for region_name, vram_start, size_tiles, oam_pal in test_regions:
        if oam_pal is not None:
            palette = obj_palettes.get(oam_pal, obj_palettes[0])

            # Create region image
            region_width = 8 * 8  # 8 tiles wide
            region_height = ((size_tiles + 7) // 8) * 8
            region_img = Image.new("RGBA", (region_width, region_height), (0, 0, 0, 0))

            start_offset = vram_start - 0xC000

            for local_tile in range(size_tiles):
                tile_offset = start_offset + (local_tile * 32)

                if tile_offset + 32 <= len(vram_data[0xC000:]):
                    tile_pixels = decode_4bpp_tile(vram_data[0xC000:], tile_offset)

                    tile_x = local_tile % 8
                    tile_y = local_tile // 8

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
                                    if px < region_width and py < region_height:
                                        region_img.putpixel((px, py), (r, g, b, 255))

            filename = f"preview_{region_name.lower().replace(' ', '_').replace('/', '')}_pal{oam_pal}.png"
            region_img.save(filename)
            scaled = region_img.resize((region_img.width * 2, region_img.height * 2),
                                     resample=Image.NEAREST)
            scaled.save(filename.replace(".png", "_2x.png"))
            print(f"  ✓ {filename}")

if __name__ == "__main__":
    main()
