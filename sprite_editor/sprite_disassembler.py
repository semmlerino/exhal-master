#!/usr/bin/env python3
"""
Sprite Disassembly Tool - Splits combined sprites back into SNES tiles
"""

import os
import sys

from PIL import Image


def split_sprite_to_tiles(sprite_image, arrangement, tile_size=8):
    """Split a sprite image back into individual tiles."""
    tiles = []
    width_tiles, height_tiles = arrangement

    for row in range(height_tiles):
        for col in range(width_tiles):
            x = col * tile_size
            y = row * tile_size
            tile = sprite_image.crop((x, y, x + tile_size, y + tile_size))
            tiles.append(tile)

    return tiles


def rebuild_tileset(original_tileset_path, edited_sprites, arrangements_file):
    """Rebuild the tileset with edited sprites."""
    # Load original tileset
    original = Image.open(original_tileset_path)
    width, height = original.size
    tile_size = 8
    tiles_per_row = width // tile_size

    # Create new tileset
    new_tileset = original.copy()

    # Load arrangements
    arrangements = {}
    with open(arrangements_file) as f:
        for line in f:
            parts = line.strip().split("|")
            if len(parts) == 3:
                name = parts[0]
                w, h = map(int, parts[1].split(","))
                indices = list(map(int, parts[2].split(",")))
                arrangements[name] = ((w, h), indices)

    # Process each edited sprite
    for sprite_path in edited_sprites:
        sprite_name = (
            os.path.basename(sprite_path).replace("assembled_", "").replace(".png", "")
        )

        if sprite_name in arrangements:
            (w, h), tile_indices = arrangements[sprite_name]

            # Load edited sprite
            edited_sprite = Image.open(sprite_path)

            # Split into tiles
            edited_tiles = split_sprite_to_tiles(edited_sprite, (w, h), tile_size)

            # Place tiles back in tileset
            for i, tile_idx in enumerate(tile_indices):
                if i < len(edited_tiles) and tile_idx < (
                    tiles_per_row * (height // tile_size)
                ):
                    row = tile_idx // tiles_per_row
                    col = tile_idx % tiles_per_row
                    x = col * tile_size
                    y = row * tile_size
                    new_tileset.paste(edited_tiles[i], (x, y))

            print(
                f"Processed {sprite_name}: replaced {
                    len(edited_tiles)} tiles"
            )

    return new_tileset


def process_edit_sheet(edit_sheet_path, arrangements_file, original_tileset):
    """Process an edit sheet with multiple sprites."""
    sheet = Image.open(edit_sheet_path)
    width = sheet.width // 2  # Assumes left=original, right=edited

    # Load arrangements
    arrangements = []
    with open(arrangements_file) as f:
        for line in f:
            parts = line.strip().split("|")
            if len(parts) == 3:
                name = parts[0]
                w, h = map(int, parts[1].split(","))
                indices = list(map(int, parts[2].split(",")))
                arrangements.append((name, (w, h), indices))

    # Load original tileset
    original = Image.open(original_tileset)
    tileset_width, tileset_height = original.size
    tile_size = 8
    tiles_per_row = tileset_width // tile_size

    # Create new tileset
    new_tileset = original.copy()

    # Process each sprite in the sheet
    y_offset = 0
    for name, (w, h), tile_indices in arrangements:
        sprite_height = h * tile_size

        if y_offset + sprite_height <= sheet.height:
            # Extract edited sprite (right side)
            edited_sprite = sheet.crop(
                (width, y_offset, width * 2, y_offset + sprite_height)
            )

            # Split into tiles
            edited_tiles = split_sprite_to_tiles(edited_sprite, (w, h), tile_size)

            # Place tiles back in tileset
            for i, tile_idx in enumerate(tile_indices):
                if i < len(edited_tiles) and tile_idx < (
                    tiles_per_row * (tileset_height // tile_size)
                ):
                    row = tile_idx // tiles_per_row
                    col = tile_idx % tiles_per_row
                    x = col * tile_size
                    y = row * tile_size
                    new_tileset.paste(edited_tiles[i], (x, y))

            print(f"Processed {name}: {w}x{h} tiles")
            y_offset += sprite_height + 20

    return new_tileset


def main():
    if len(sys.argv) < 3:
        print(
            "Usage: python sprite_disassembler.py <original_tileset> <edited_sprite(s)> [output_tileset]"
        )
        print(
            "   or: python sprite_disassembler.py <original_tileset> <edit_sheet> --sheet [output_tileset]"
        )
        sys.exit(1)

    original_tileset = sys.argv[1]

    if len(sys.argv) >= 4 and sys.argv[3] == "--sheet":
        # Process edit sheet
        edit_sheet = sys.argv[2]
        output_tileset = sys.argv[4] if len(sys.argv) > 4 else "updated_tileset.png"
        arrangements_file = edit_sheet.replace("_edit_sheet.png", "_arrangements.txt")

        print(f"Processing edit sheet: {edit_sheet}")
        new_tileset = process_edit_sheet(
            edit_sheet, arrangements_file, original_tileset
        )

    else:
        # Process individual sprites
        edited_sprites = sys.argv[2:-1] if len(sys.argv) > 3 else [sys.argv[2]]
        output_tileset = sys.argv[-1] if len(sys.argv) > 3 else "updated_tileset.png"

        # Find arrangements file
        arrangements_file = None
        for sprite in edited_sprites:
            possible_file = sprite.replace(
                os.path.basename(sprite), "assembled_arrangements.txt"
            )
            if os.path.exists(possible_file):
                arrangements_file = possible_file
                break

        if not arrangements_file:
            print("Error: Could not find arrangements file")
            sys.exit(1)

        print(f"Using arrangements from: {arrangements_file}")
        new_tileset = rebuild_tileset(
            original_tileset, edited_sprites, arrangements_file
        )

    # Save updated tileset
    new_tileset.save(output_tileset)
    print(f"\nSaved updated tileset to: {output_tileset}")

    # Also save as raw binary if it's indexed
    if new_tileset.mode == "P":
        # This would need the png_to_snes conversion
        print(
            f"Note: To convert to SNES format, use: python png_to_snes.py {output_tileset}"
        )


if __name__ == "__main__":
    main()
