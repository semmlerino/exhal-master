#!/usr/bin/env python3
"""
Find and assemble Kirby sprites from tileset
"""

import sys

from PIL import Image


def find_kirby_arrangements():
    """Return known Kirby sprite arrangements based on VRAM analysis."""
    # Based on our VRAM findings, Kirby sprites are in the middle section
    # These are tile indices that form complete Kirby sprites

    return [
        # Standing Kirby (from row 16-17, around tiles 256+)
        ("kirby_stand_1", (2, 2), [256, 257, 264, 265]),
        ("kirby_stand_2", (2, 2), [258, 259, 266, 267]),

        # Walking Kirby frames
        ("kirby_walk_1", (2, 2), [260, 261, 268, 269]),
        ("kirby_walk_2", (2, 2), [262, 263, 270, 271]),

        # Kirby with ability (yellow Kirby we saw)
        ("kirby_beam_1", (2, 2), [272, 273, 280, 281]),
        ("kirby_beam_2", (2, 2), [274, 275, 282, 283]),

        # Larger Kirby (puffed up)
        ("kirby_puff", (3, 3), [288, 289, 290, 296, 297, 298, 304, 305, 306]),

        # Try some from visible area (rows 20-24)
        ("kirby_test_1", (2, 2), [320, 321, 328, 329]),
        ("kirby_test_2", (2, 2), [322, 323, 330, 331]),
        ("kirby_test_3", (2, 2), [324, 325, 332, 333]),

        # Enemy sprites nearby
        ("enemy_1", (2, 2), [336, 337, 344, 345]),
        ("enemy_2", (2, 2), [338, 339, 346, 347]),
    ]


def assemble_kirby_sheet(tileset_path):
    """Create a sheet with identified Kirby sprites."""
    # Load tileset
    img = Image.open(tileset_path)
    width, height = img.size
    tile_size = 8

    # Extract all tiles
    tiles = []
    for y in range(0, height, tile_size):
        for x in range(0, width, tile_size):
            tile = img.crop((x, y, x + tile_size, y + tile_size))
            tiles.append(tile)

    print(f"Loaded {len(tiles)} tiles")

    # Get Kirby arrangements
    arrangements = find_kirby_arrangements()

    # Create output sheet
    max_sprite_width = 32  # 4 tiles wide max
    max_sprite_height = 32  # 4 tiles tall max
    sprites_per_row = 4
    rows_needed = (len(arrangements) + sprites_per_row - 1) // sprites_per_row

    sheet_width = sprites_per_row * (max_sprite_width + 8)  # 8px spacing
    sheet_height = rows_needed * (max_sprite_height + 20)  # 20px for labels

    sheet = Image.new("RGBA", (sheet_width, sheet_height), (64, 64, 64, 255))

    # Place sprites
    for i, (name, (w, h), indices) in enumerate(arrangements):
        col = i % sprites_per_row
        row = i // sprites_per_row

        x_pos = col * (max_sprite_width + 8) + 4
        y_pos = row * (max_sprite_height + 20) + 4

        # Create sprite
        sprite_w = w * tile_size
        sprite_h = h * tile_size
        sprite = Image.new("P", (sprite_w, sprite_h))
        if img.mode == "P":
            sprite.putpalette(img.palette)

        # Place tiles
        valid_tiles = 0
        for j, tile_idx in enumerate(indices):
            if tile_idx < len(tiles):
                ty = j // w
                tx = j % w
                sprite.paste(tiles[tile_idx], (tx * tile_size, ty * tile_size))
                valid_tiles += 1

        # Convert to RGBA for the sheet
        if valid_tiles > 0:
            sprite_rgba = sprite.convert("RGBA")
            sheet.paste(sprite_rgba, (x_pos, y_pos), sprite_rgba)

        print(f"{name}: {w}x{h} tiles ({sprite_w}x{sprite_h} px) at sheet pos ({x_pos},{y_pos})")

    return sheet, arrangements

def main():
    if len(sys.argv) < 2:
        print("Usage: python find_kirby_sprites.py <tileset_image>")
        sys.exit(1)

    tileset_path = sys.argv[1]

    # Create Kirby sprite sheet
    sheet, arrangements = assemble_kirby_sheet(tileset_path)

    # Save sheet
    output_path = "kirby_sprites_identified.png"
    sheet.save(output_path)
    print(f"\nSaved Kirby sprite sheet to: {output_path}")

    # Save individual sprites for editing
    img = Image.open(tileset_path)
    width, height = img.size
    tile_size = 8

    # Extract tiles again for individual saves
    tiles = []
    for y in range(0, height, tile_size):
        for x in range(0, width, tile_size):
            tile = img.crop((x, y, x + tile_size, y + tile_size))
            tiles.append(tile)

    # Save each sprite individually
    for name, (w, h), indices in arrangements[:6]:  # Just the first 6 for testing
        sprite_w = w * tile_size
        sprite_h = h * tile_size
        sprite = Image.new("P", (sprite_w, sprite_h))
        if img.mode == "P":
            sprite.putpalette(img.palette)

        # Place tiles
        for j, tile_idx in enumerate(indices):
            if tile_idx < len(tiles):
                ty = j // w
                tx = j % w
                sprite.paste(tiles[tile_idx], (tx * tile_size, ty * tile_size))

        sprite.save(f"kirby_{name}.png")
        print(f"Saved individual sprite: kirby_{name}.png")

if __name__ == "__main__":
    main()
