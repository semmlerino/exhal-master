#!/usr/bin/env python3
"""
Fixed palette mapping based on SNES architecture:
- OBJ palettes are stored at CGRAM indices 128-255 (palettes 8-15)
- OAM palette 0-7 map to CGRAM palettes 8-15
"""

import sys

sys.path.append("sprite_editor")

import struct

from PIL import Image

from sprite_editor.oam_palette_mapper import OAMPaletteMapper
from sprite_editor.sprite_editor_core import SpriteEditorCore
from sprite_editor.tile_utils import decode_4bpp_tile


def read_obj_palette(cgram_file, obj_palette_num):
    """
    Read an OBJ palette from CGRAM.
    OBJ palettes start at CGRAM index 128 (palette 8)
    """
    with open(cgram_file, "rb") as f:
        # OBJ palette N starts at CGRAM index (128 + N*16)
        cgram_index = 128 + (obj_palette_num * 16)
        f.seek(cgram_index * 2)  # Each color is 2 bytes

        palette = []
        for _i in range(16):
            data = f.read(2)
            if len(data) < 2:
                break

            # Convert BGR555 to RGB888
            color = struct.unpack("<H", data)[0]
            b = ((color >> 10) & 0x1F) * 8
            g = ((color >> 5) & 0x1F) * 8
            r = (color & 0x1F) * 8

            palette.extend([r, g, b])

        return palette

def demo_fixed_palettes():
    print("=== Fixed Palette Mapping Demo ===")
    print("OBJ palettes are at CGRAM indices 128-255")
    print("OAM palette N = CGRAM palette (N+8)\n")

    vram_file = "SnesVideoRam.VRAM.dmp"
    cgram_file = "SnesCgRam.dmp"
    oam_file = "SnesSpriteRam.OAM.dmp"

    # Load OAM data
    mapper = OAMPaletteMapper()
    mapper.parse_oam_dump(oam_file)

    # Count actual palette usage
    palette_usage = {}
    for sprite in mapper.oam_entries:
        if sprite["y"] < 224:
            pal = sprite["palette"]
            palette_usage[pal] = palette_usage.get(pal, 0) + 1

    print("Active OAM palettes in this frame:")
    for pal, count in sorted(palette_usage.items()):
        print(f"  OAM Palette {pal}: {count} sprites")

    # Demo 1: Show Pink Kirby with OAM palette 0
    print("\n\nDemo 1: Pink Kirby (OAM palette 0)")

    # Read VRAM at Kirby's location
    SpriteEditorCore()
    with open(vram_file, "rb") as f:
        f.seek(0xC000)
        vram_data = f.read(0x800)  # First 64 tiles

    # Get OBJ palette 0
    obj_pal_0 = read_obj_palette(cgram_file, 0)

    # Create image showing first 64 tiles with OBJ palette 0
    img = Image.new("RGBA", (128, 32), (0, 0, 0, 0))

    for tile_idx in range(64):
        tile_offset = tile_idx * 32
        if tile_offset + 32 <= len(vram_data):
            tile_pixels = decode_4bpp_tile(vram_data, tile_offset)

            tile_x = tile_idx % 16
            tile_y = tile_idx // 16

            for y in range(8):
                for x in range(8):
                    pixel_idx = y * 8 + x
                    if pixel_idx < len(tile_pixels):
                        color_idx = tile_pixels[pixel_idx]

                        if color_idx > 0 and color_idx * 3 + 2 < len(obj_pal_0):
                            r = obj_pal_0[color_idx * 3]
                            g = obj_pal_0[color_idx * 3 + 1]
                            b = obj_pal_0[color_idx * 3 + 2]

                            px = tile_x * 8 + x
                            py = tile_y * 8 + y
                            img.putpixel((px, py), (r, g, b, 255))

    img.save("demo_fixed_kirby_obj_pal_0.png")
    scaled = img.resize((img.width * 4, img.height * 4), resample=Image.NEAREST)
    scaled.save("demo_fixed_kirby_obj_pal_0_4x.png")
    print("✓ Created demo_fixed_kirby_obj_pal_0.png")

    # Demo 2: Show enemies with OAM palette 4
    print("\nDemo 2: Enemies (OAM palette 4)")

    with open(vram_file, "rb") as f:
        f.seek(0xD000)
        vram_data = f.read(0x1000)

    obj_pal_4 = read_obj_palette(cgram_file, 4)

    img = Image.new("RGBA", (128, 64), (0, 0, 0, 0))

    for tile_idx in range(128):
        tile_offset = tile_idx * 32
        if tile_offset + 32 <= len(vram_data):
            tile_pixels = decode_4bpp_tile(vram_data, tile_offset)

            tile_x = tile_idx % 16
            tile_y = tile_idx // 16

            for y in range(8):
                for x in range(8):
                    pixel_idx = y * 8 + x
                    if pixel_idx < len(tile_pixels):
                        color_idx = tile_pixels[pixel_idx]

                        if color_idx > 0 and color_idx * 3 + 2 < len(obj_pal_4):
                            r = obj_pal_4[color_idx * 3]
                            g = obj_pal_4[color_idx * 3 + 1]
                            b = obj_pal_4[color_idx * 3 + 2]

                            px = tile_x * 8 + x
                            py = tile_y * 8 + y
                            img.putpixel((px, py), (r, g, b, 255))

    img.save("demo_fixed_enemies_obj_pal_4.png")
    scaled = img.resize((img.width * 2, img.height * 2), resample=Image.NEAREST)
    scaled.save("demo_fixed_enemies_obj_pal_4_2x.png")
    print("✓ Created demo_fixed_enemies_obj_pal_4.png")

    # Show color comparison
    print("\n\nColor verification:")
    print("OBJ Palette 0 colors (should show pink for Kirby):")
    for i in range(min(16, len(obj_pal_0)//3)):
        if i * 3 + 2 < len(obj_pal_0):
            r = obj_pal_0[i * 3]
            g = obj_pal_0[i * 3 + 1]
            b = obj_pal_0[i * 3 + 2]
            print(f"  Color {i}: RGB({r}, {g}, {b})")
            if i == 5:  # Check what should be pink
                break

    print("\n=== Complete! ===")

if __name__ == "__main__":
    demo_fixed_palettes()
