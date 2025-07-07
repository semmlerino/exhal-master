#!/usr/bin/env python3
"""
Sprite Assembly Tool - Combines SNES tiles into full character sprites
"""

from PIL import Image
import numpy as np
import sys

def load_tiles_from_image(image_path, tile_size=8):
    """Load tiles from a tileset image."""
    img = Image.open(image_path)
    width, height = img.size
    tiles_per_row = width // tile_size
    tiles_per_col = height // tile_size

    tiles = []
    for row in range(tiles_per_col):
        for col in range(tiles_per_row):
            x = col * tile_size
            y = row * tile_size
            tile = img.crop((x, y, x + tile_size, y + tile_size))
            tiles.append(tile)

    return tiles, img.mode, img.palette

def assemble_sprite(tiles, tile_indices, arrangement, tile_size=8):
    """
    Assemble tiles into a sprite based on arrangement.

    tile_indices: list of tile numbers to use
    arrangement: tuple (width, height) in tiles, e.g. (2,2) for 16x16 sprite
    """
    sprite_width = arrangement[0] * tile_size
    sprite_height = arrangement[1] * tile_size

    # Create sprite image
    if tiles[0].mode == 'P':
        sprite = Image.new('P', (sprite_width, sprite_height))
        sprite.putpalette(tiles[0].palette)
    else:
        sprite = Image.new(tiles[0].mode, (sprite_width, sprite_height))

    # Place tiles
    for i, tile_idx in enumerate(tile_indices):
        if tile_idx < len(tiles):
            row = i // arrangement[0]
            col = i % arrangement[0]
            x = col * tile_size
            y = row * tile_size
            sprite.paste(tiles[tile_idx], (x, y))

    return sprite

def create_sprite_sheet(tiles, arrangements):
    """Create a sheet with multiple sprite arrangements."""
    tile_size = 8
    sprites = []

    # Common Kirby arrangements
    for name, (w, h), indices in arrangements:
        sprite = assemble_sprite(tiles, indices, (w, h), tile_size)
        sprites.append((name, sprite))

    # Calculate sheet size
    max_width = max(s[1].width for s in sprites)
    total_height = sum(s[1].height + 20 for s in sprites)  # 20px for labels

    # Create sheet
    sheet = Image.new('RGBA', (max_width * 2, total_height), (0, 0, 0, 0))

    y_offset = 0
    for name, sprite in sprites:
        # Original sprite
        sheet.paste(sprite, (0, y_offset))
        # Space for edited version
        sheet.paste(sprite, (max_width, y_offset))
        y_offset += sprite.height + 20

    return sheet, sprites

def main():
    if len(sys.argv) < 2:
        print("Usage: python sprite_assembler.py <tileset_image> [output_prefix]")
        sys.exit(1)

    tileset_path = sys.argv[1]
    output_prefix = sys.argv[2] if len(sys.argv) > 2 else "assembled"

    # Load tiles
    tiles, mode, palette = load_tiles_from_image(tileset_path)
    print(f"Loaded {len(tiles)} tiles from {tileset_path}")

    # Define common sprite arrangements for Kirby
    # Format: (name, (width_in_tiles, height_in_tiles), [tile_indices])
    arrangements = [
        # 16x16 sprites (2x2 tiles) - most common for Kirby
        ("kirby_16x16_1", (2, 2), [0, 1, 2, 3]),
        ("kirby_16x16_2", (2, 2), [4, 5, 6, 7]),
        ("kirby_16x16_3", (2, 2), [8, 9, 10, 11]),
        ("kirby_16x16_4", (2, 2), [12, 13, 14, 15]),

        # 24x24 sprites (3x3 tiles) - for larger Kirby poses
        ("kirby_24x24_1", (3, 3), [0, 1, 2, 8, 9, 10, 16, 17, 18]),

        # 16x24 sprites (2x3 tiles) - for tall Kirby poses
        ("kirby_16x24_1", (2, 3), [0, 1, 8, 9, 16, 17]),

        # 32x32 sprites (4x4 tiles) - for big Kirby
        ("kirby_32x32_1", (4, 4), list(range(16))),
    ]

    # Try to find Kirby patterns automatically
    # Look for pink/yellow pixels in early tiles
    kirby_tiles = []
    for i, tile in enumerate(tiles[:64]):  # Check first 64 tiles
        pixels = np.array(tile)
        if tile.mode == 'P':
            # Check if tile has non-zero pixels
            if np.any(pixels > 0):
                kirby_tiles.append(i)

    if kirby_tiles:
        print(f"Found potential Kirby tiles: {kirby_tiles[:16]}")
        # Add automatic arrangements based on found tiles
        if len(kirby_tiles) >= 4:
            arrangements.insert(0, ("auto_kirby_16x16", (2, 2), kirby_tiles[:4]))
        if len(kirby_tiles) >= 6:
            arrangements.insert(1, ("auto_kirby_16x24", (2, 3), kirby_tiles[:6]))

    # Create individual sprite files
    for name, (w, h), indices in arrangements:
        sprite = assemble_sprite(tiles, indices, (w, h))
        sprite.save(f"{output_prefix}_{name}.png")
        print(f"Saved {name}: {w*8}x{h*8} pixels")

    # Create a combined edit sheet
    sheet, sprites = create_sprite_sheet(tiles, arrangements)
    sheet.save(f"{output_prefix}_edit_sheet.png")
    print(f"\nCreated edit sheet: {output_prefix}_edit_sheet.png")
    print("Left column: original sprites")
    print("Right column: space for edited sprites")

    # Save arrangement data for splitting later
    with open(f"{output_prefix}_arrangements.txt", "w") as f:
        for name, (w, h), indices in arrangements:
            f.write(f"{name}|{w},{h}|{','.join(map(str, indices))}\n")

    print(f"\nSaved arrangement data to {output_prefix}_arrangements.txt")

if __name__ == "__main__":
    main()