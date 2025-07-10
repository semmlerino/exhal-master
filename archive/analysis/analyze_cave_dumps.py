#!/usr/bin/env python3
"""Analyze synchronized Cave dumps to determine correct palette mappings."""

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

def extract_palettes(cgram_data):
    """Extract all sprite palettes from CGRAM (palettes 8-15)."""
    palettes = []
    # Sprite palettes are 8-15 (bytes 256-511)
    for pal_idx in range(8, 16):
        palette = []
        for color_idx in range(16):
            offset = (pal_idx * 16 + color_idx) * 2
            color = decode_snes_color(cgram_data[offset:offset+2])
            palette.append(color)
        palettes.append(palette)
    return palettes

def parse_oam_entry(oam_data, index):
    """Parse a single OAM entry."""
    offset = index * 4
    if offset + 4 > len(oam_data):
        return None

    x = oam_data[offset]
    y = oam_data[offset + 1]
    tile = oam_data[offset + 2]
    attrs = oam_data[offset + 3]

    # Extract attributes
    palette = (attrs >> 1) & 0x07
    priority = (attrs >> 4) & 0x03
    flip_h = (attrs >> 6) & 0x01
    flip_v = (attrs >> 7) & 0x01

    return {
        "x": x,
        "y": y,
        "tile": tile,
        "palette": palette,
        "priority": priority,
        "flip_h": flip_h,
        "flip_v": flip_v
    }

def analyze_oam_palettes(oam_data):
    """Analyze which palettes are used in OAM."""
    palette_usage = {}
    tile_to_palette = {}
    sprite_info = []

    print("\n=== OAM Analysis ===")
    print("Active sprites (on-screen):")

    active_count = 0
    for i in range(128):
        sprite = parse_oam_entry(oam_data, i)
        if sprite and sprite["y"] < 224:  # Active sprite
            active_count += 1
            palette = sprite["palette"]
            tile = sprite["tile"]

            sprite_info.append({
                "index": i,
                "sprite": sprite
            })

            if palette not in palette_usage:
                palette_usage[palette] = []
            palette_usage[palette].append(i)

            if tile not in tile_to_palette:
                tile_to_palette[tile] = set()
            tile_to_palette[tile].add(palette)

            if active_count <= 20:  # Show first 20 active sprites
                print(f"  Sprite {i:3d}: Tile 0x{tile:02X} ({tile:3d}), Palette {palette}, Pos ({sprite['x']:3d}, {sprite['y']:3d})")

    print(f"\nTotal active sprites: {active_count}")

    print("\n=== Palette Usage Summary ===")
    for pal in sorted(palette_usage.keys()):
        print(f"Palette {pal}: {len(palette_usage[pal])} sprites")
        # Show some example tiles
        example_tiles = set()
        for sprite_idx in palette_usage[pal][:10]:
            sprite = parse_oam_entry(oam_data, sprite_idx)
            if sprite:
                example_tiles.add(sprite["tile"])
        print(f"  Example tiles: {[f'0x{t:02X}' for t in sorted(example_tiles)]}")

    return palette_usage, tile_to_palette, sprite_info

def decode_4bpp_tile(vram_data, tile_index):
    """Decode a 4bpp tile from VRAM."""
    tile_offset = tile_index * 32  # 32 bytes per 4bpp tile
    tile_data = np.zeros((8, 8), dtype=np.uint8)

    if tile_offset + 32 > len(vram_data):
        return tile_data

    for row in range(8):
        # Read the 4 bytes for this row
        b0 = vram_data[tile_offset + row * 2]
        b1 = vram_data[tile_offset + row * 2 + 1]
        b2 = vram_data[tile_offset + 16 + row * 2]
        b3 = vram_data[tile_offset + 16 + row * 2 + 1]

        # Decode each pixel
        for col in range(8):
            bit = 7 - col
            pixel = ((b0 >> bit) & 1) | \
                    (((b1 >> bit) & 1) << 1) | \
                    (((b2 >> bit) & 1) << 2) | \
                    (((b3 >> bit) & 1) << 3)
            tile_data[row, col] = pixel

    return tile_data

def render_tile_with_palette(tile_data, palette):
    """Render a tile with a specific palette."""
    img = Image.new("RGB", (8, 8))
    pixels = img.load()

    for y in range(8):
        for x in range(8):
            color_idx = tile_data[y, x]
            color = palette[color_idx] if color_idx < len(palette) else (0, 0, 0)
            pixels[x, y] = color

    return img

def create_palette_demo_sheet(vram_data, cgram_data, oam_data, tile_to_palette):
    """Create a demo sheet showing tiles with their correct palettes."""
    sprite_palettes = extract_palettes(cgram_data)

    # Create regions based on tile ranges
    regions = [
        ("Kirby/Player", 0x00, 0x40, None),  # Let OAM determine
        ("Enemies Set 1", 0x40, 0x80, None),
        ("Enemies Set 2", 0x80, 0xC0, None),
        ("Items/Effects", 0xC0, 0x100, None),
    ]

    # Calculate image size
    tiles_per_row = 16
    tile_size = 16  # Display at 2x
    padding = 4

    img_width = tiles_per_row * (tile_size + padding) + 100
    img_height = len(regions) * 5 * (tile_size + padding) + 100

    img = Image.new("RGB", (img_width, img_height), (32, 32, 32))
    draw = ImageDraw.Draw(img)

    y_offset = 20

    for region_name, start_tile, end_tile, forced_pal in regions:
        # Draw region header
        draw.text((10, y_offset), f"{region_name} (Tiles 0x{start_tile:02X}-0x{end_tile-1:02X})",
                  fill=(255, 255, 255))
        y_offset += 20

        # Draw tiles in this region
        for tile_idx in range(start_tile, min(end_tile, start_tile + 64)):
            # Determine palette from OAM data
            if tile_idx in tile_to_palette:
                palettes_used = list(tile_to_palette[tile_idx])
                pal_idx = palettes_used[0] if palettes_used else 0
            else:
                pal_idx = forced_pal if forced_pal is not None else 0

            # Decode and render tile
            tile_data = decode_4bpp_tile(vram_data, tile_idx)
            tile_img = render_tile_with_palette(tile_data, sprite_palettes[pal_idx])
            tile_img = tile_img.resize((tile_size, tile_size), Image.NEAREST)

            # Calculate position
            row = (tile_idx - start_tile) // tiles_per_row
            col = (tile_idx - start_tile) % tiles_per_row
            x = 10 + col * (tile_size + padding)
            y = y_offset + row * (tile_size + padding)

            # Paste tile
            img.paste(tile_img, (x, y))

            # Add palette indicator
            if tile_idx in tile_to_palette:
                draw.text((x + tile_size - 12, y + tile_size - 10),
                         f"P{pal_idx}", fill=(255, 255, 0))

        y_offset += 5 * (tile_size + padding)

    # Draw palette reference on the right
    x_pal = img_width - 180
    y_pal = 20
    draw.text((x_pal, y_pal), "Sprite Palettes:", fill=(255, 255, 255))
    y_pal += 20

    for pal_idx, palette in enumerate(sprite_palettes):
        draw.text((x_pal, y_pal), f"Pal {pal_idx}:", fill=(255, 255, 255))
        for color_idx in range(16):
            x = x_pal + 40 + (color_idx % 8) * 12
            y = y_pal + (color_idx // 8) * 12
            draw.rectangle([x, y, x + 10, y + 10], fill=palette[color_idx])
        y_pal += 30

    return img

def create_full_sheet_with_correct_palettes(vram_data, cgram_data, tile_to_palette):
    """Create the full sprite sheet with correct palette assignments."""
    sprite_palettes = extract_palettes(cgram_data)

    # Sheet layout
    tiles_per_row = 16
    total_tiles = 256
    tile_size = 16  # 2x scale

    img_width = tiles_per_row * tile_size
    img_height = (total_tiles // tiles_per_row) * tile_size

    img = Image.new("RGB", (img_width, img_height), (0, 0, 0))

    for tile_idx in range(total_tiles):
        # Determine correct palette from OAM analysis
        if tile_idx in tile_to_palette:
            palettes_used = list(tile_to_palette[tile_idx])
            # Use the most common palette for this tile
            pal_idx = palettes_used[0] if palettes_used else 0
        # Default palette based on region
        elif tile_idx < 0x40:
            pal_idx = 0  # Kirby
        elif tile_idx < 0x80:
            pal_idx = 4  # Enemies 1
        elif tile_idx < 0xC0:
            pal_idx = 5  # Enemies 2
        else:
            pal_idx = 0  # Items/UI

        # Decode and render tile
        tile_data = decode_4bpp_tile(vram_data, tile_idx)
        tile_img = render_tile_with_palette(tile_data, sprite_palettes[pal_idx])
        tile_img = tile_img.resize((tile_size, tile_size), Image.NEAREST)

        # Calculate position
        row = tile_idx // tiles_per_row
        col = tile_idx % tiles_per_row
        x = col * tile_size
        y = row * tile_size

        img.paste(tile_img, (x, y))

    return img

def main():
    print("=== Analyzing Cave Synchronized Dumps ===\n")

    # Load dump files
    with open("Cave.SnesVideoRam.dmp", "rb") as f:
        vram_data = f.read()
    with open("Cave.SnesCgRam.dmp", "rb") as f:
        cgram_data = f.read()
    with open("Cave.SnesSpriteRam.dmp", "rb") as f:
        oam_data = f.read()

    print("Loaded dumps:")
    print(f"  VRAM: {len(vram_data)} bytes")
    print(f"  CGRAM: {len(cgram_data)} bytes")
    print(f"  OAM: {len(oam_data)} bytes")

    # Analyze OAM to determine palette usage
    palette_usage, tile_to_palette, sprite_info = analyze_oam_palettes(oam_data)

    # Show palette details
    print("\n=== CGRAM Sprite Palettes (8-15) ===")
    sprite_palettes = extract_palettes(cgram_data)
    for pal_idx, palette in enumerate(sprite_palettes):
        print(f"Palette {pal_idx}: ", end="")
        # Show first few colors
        for i in range(4):
            r, g, b = palette[i]
            print(f"({r},{g},{b}) ", end="")
        print("...")

    # Create visualizations
    print("\n=== Creating Visualizations ===")

    # Create palette demo sheet
    demo_img = create_palette_demo_sheet(vram_data, cgram_data, oam_data, tile_to_palette)
    demo_img.save("cave_palette_demo_sheet.png")
    print("Saved: cave_palette_demo_sheet.png")

    # Create full corrected sheet
    full_img = create_full_sheet_with_correct_palettes(vram_data, cgram_data, tile_to_palette)
    full_img.save("cave_full_sheet_corrected.png")
    print("Saved: cave_full_sheet_corrected.png")

    # Create a detailed palette mapping visualization
    print("\n=== Tile to Palette Mapping ===")
    print("Based on OAM analysis:")

    # Group by regions
    regions = [
        ("Kirby/Player", 0x00, 0x40),
        ("Enemies Set 1", 0x40, 0x80),
        ("Enemies Set 2", 0x80, 0xC0),
        ("Items/Effects", 0xC0, 0x100),
    ]

    for region_name, start, end in regions:
        print(f"\n{region_name}:")
        region_pal_usage = {}
        for tile_idx in range(start, end):
            if tile_idx in tile_to_palette:
                for pal in tile_to_palette[tile_idx]:
                    region_pal_usage[pal] = region_pal_usage.get(pal, 0) + 1

        for pal in sorted(region_pal_usage.keys()):
            print(f"  Palette {pal}: {region_pal_usage[pal]} tiles")

if __name__ == "__main__":
    main()
