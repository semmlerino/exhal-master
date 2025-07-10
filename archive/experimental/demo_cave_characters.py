#!/usr/bin/env python3
"""Demonstrate specific characters with correct palettes from Cave synchronized data."""

import struct

import numpy as np
from PIL import Image, ImageDraw


def decode_snes_color(color_bytes):
    """Decode SNES 15-bit color to RGB."""
    color = struct.unpack("<H", color_bytes)[0]
    r = (color & 0x1F) << 3
    g = ((color >> 5) & 0x1F) << 3
    b = ((color >> 10) & 0x1F) << 3
    return (r, g, b)

def extract_sprite_palettes(cgram_data):
    """Extract sprite palettes (8-15) from CGRAM."""
    palettes = []
    for pal_idx in range(8, 16):
        palette = []
        for color_idx in range(16):
            offset = (pal_idx * 16 + color_idx) * 2
            color = decode_snes_color(cgram_data[offset:offset+2])
            palette.append(color)
        palettes.append(palette)
    return palettes

def decode_4bpp_tile(vram_data, tile_index):
    """Decode a 4bpp tile from VRAM."""
    tile_offset = tile_index * 32
    tile_data = np.zeros((8, 8), dtype=np.uint8)

    if tile_offset + 32 > len(vram_data):
        return tile_data

    for row in range(8):
        b0 = vram_data[tile_offset + row * 2]
        b1 = vram_data[tile_offset + row * 2 + 1]
        b2 = vram_data[tile_offset + 16 + row * 2]
        b3 = vram_data[tile_offset + 16 + row * 2 + 1]

        for col in range(8):
            bit = 7 - col
            pixel = ((b0 >> bit) & 1) | \
                    (((b1 >> bit) & 1) << 1) | \
                    (((b2 >> bit) & 1) << 2) | \
                    (((b3 >> bit) & 1) << 3)
            tile_data[row, col] = pixel

    return tile_data

def render_sprite(vram_data, tiles, palette, scale=4):
    """Render a multi-tile sprite."""
    # Assume 2x2 tile arrangement
    sprite_img = Image.new("RGB", (16 * scale, 16 * scale), (0, 0, 0))

    positions = [(0, 0), (8, 0), (0, 8), (8, 8)]

    for i, tile_idx in enumerate(tiles):
        if i >= len(positions):
            break

        tile_data = decode_4bpp_tile(vram_data, tile_idx)
        tile_img = Image.new("RGB", (8, 8))
        pixels = tile_img.load()

        for y in range(8):
            for x in range(8):
                color_idx = tile_data[y, x]
                color = palette[color_idx] if color_idx < len(palette) else (0, 0, 0)
                pixels[x, y] = color

        tile_img = tile_img.resize((8 * scale, 8 * scale), Image.NEAREST)
        x, y = positions[i]
        sprite_img.paste(tile_img, (x * scale, y * scale))

    return sprite_img

def create_character_showcase(vram_data, cgram_data, oam_tiles):
    """Create a showcase of characters with their correct palettes."""
    sprite_palettes = extract_sprite_palettes(cgram_data)

    # Define character sprites based on OAM analysis
    characters = [
        {
            "name": "Pink Kirby",
            "tiles": [0x00, 0x02, 0x03, 0x04],  # From OAM
            "palette": 0,  # Palette 0 from OAM
            "description": "Main character - Palette 0"
        },
        {
            "name": "UI Numbers",
            "tiles": [0x20, 0x22, 0x23, 0x24],  # From OAM
            "palette": 2,  # Palette 2 from OAM
            "description": "UI elements - Palette 2"
        },
        {
            "name": "Cave Enemy",
            "tiles": [0xA0, 0xA2, 0xB0, 0xB2],  # From OAM
            "palette": 3,  # Palette 3 from OAM
            "description": "Enemy sprite - Palette 3"
        },
        {
            "name": "Beam Kirby",
            "tiles": [0x12, 0x13, 0x32, 0x33],  # Mixed from OAM
            "palette": 0,  # Try palette 0
            "description": "Beam ability - Palette 0"
        }
    ]

    # Create image
    img_width = 800
    img_height = 600
    img = Image.new("RGB", (img_width, img_height), (32, 32, 32))
    draw = ImageDraw.Draw(img)

    # Title
    draw.text((10, 10), "Cave Data - Character Showcase", fill=(255, 255, 255))
    draw.text((10, 30), "Sprites with correct palettes from synchronized OAM data", fill=(200, 200, 200))

    # Draw characters
    y_offset = 70

    for char in characters:
        # Draw character name
        draw.text((10, y_offset), char["name"], fill=(255, 255, 255))
        draw.text((10, y_offset + 20), char["description"], fill=(180, 180, 180))

        # Render character
        sprite = render_sprite(vram_data, char["tiles"], sprite_palettes[char["palette"]], scale=4)
        img.paste(sprite, (10, y_offset + 40))

        # Show tile indices
        draw.text((80, y_offset + 50), f"Tiles: {[f'0x{t:02X}' for t in char['tiles']]}",
                 fill=(150, 150, 150))

        # Show palette colors
        x_pal = 300
        draw.text((x_pal, y_offset), f"Palette {char['palette']} colors:", fill=(200, 200, 200))
        for i in range(16):
            x = x_pal + (i % 8) * 20
            y = y_offset + 20 + (i // 8) * 20
            color = sprite_palettes[char["palette"]][i]
            draw.rectangle([x, y, x + 18, y + 18], fill=color)

        y_offset += 120

    # Add OAM data summary
    draw.text((500, 70), "OAM Data Summary:", fill=(255, 255, 255))
    draw.text((500, 90), f"Total tiles in OAM: {len(oam_tiles)}", fill=(200, 200, 200))
    draw.text((500, 110), "Palette usage:", fill=(200, 200, 200))

    pal_counts = {}
    for _tile, pal in oam_tiles.items():
        if pal not in pal_counts:
            pal_counts[pal] = 0
        pal_counts[pal] += 1

    y = 130
    for pal in sorted(pal_counts.keys()):
        draw.text((520, y), f"Palette {pal}: {pal_counts[pal]} tiles", fill=(180, 180, 180))
        y += 20

    return img

def main():
    print("=== Creating Cave Character Showcase ===\n")

    # Load data
    with open("Cave.SnesVideoRam.dmp", "rb") as f:
        vram_data = f.read()
    with open("Cave.SnesCgRam.dmp", "rb") as f:
        cgram_data = f.read()
    with open("Cave.SnesSpriteRam.dmp", "rb") as f:
        oam_data = f.read()

    # Parse OAM to get tile->palette mapping
    oam_tiles = {}
    for i in range(128):
        offset = i * 4
        if offset + 4 <= len(oam_data):
            y = oam_data[offset + 1]
            if y < 224:  # Active sprite
                tile = oam_data[offset + 2]
                attrs = oam_data[offset + 3]
                palette = (attrs >> 1) & 0x07
                oam_tiles[tile] = palette

    print(f"Found {len(oam_tiles)} active tiles in OAM")

    # Create showcase
    showcase = create_character_showcase(vram_data, cgram_data, oam_tiles)
    showcase.save("cave_character_showcase.png")
    print("Saved: cave_character_showcase.png")

    # Also create individual character images
    sprite_palettes = extract_sprite_palettes(cgram_data)

    # Pink Kirby with palette 0
    kirby_tiles = [0x00, 0x02, 0x03, 0x04]
    kirby_sprite = render_sprite(vram_data, kirby_tiles, sprite_palettes[0], scale=8)
    kirby_sprite.save("cave_pink_kirby_pal0.png")
    print("Saved: cave_pink_kirby_pal0.png")

    # UI elements with palette 2
    ui_tiles = [0x20, 0x22, 0x23, 0x24]
    ui_sprite = render_sprite(vram_data, ui_tiles, sprite_palettes[2], scale=8)
    ui_sprite.save("cave_ui_elements_pal2.png")
    print("Saved: cave_ui_elements_pal2.png")

    # Enemy with palette 3
    enemy_tiles = [0xA0, 0xA2, 0xB0, 0xB2]
    enemy_sprite = render_sprite(vram_data, enemy_tiles, sprite_palettes[3], scale=8)
    enemy_sprite.save("cave_enemy_pal3.png")
    print("Saved: cave_enemy_pal3.png")

    print("\nCharacter showcase complete!")

if __name__ == "__main__":
    main()
