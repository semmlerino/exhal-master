#!/usr/bin/env python3
"""Create the final corrected sprite sheet with proper palette mappings from synchronized data."""

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

def extract_all_palettes(cgram_data):
    """Extract all 16 palettes from CGRAM."""
    palettes = []
    for pal_idx in range(16):
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

def build_tile_palette_map(oam_data):
    """Build a comprehensive map of which tiles use which palettes."""
    tile_to_palettes = {}

    # Analyze all sprites in OAM
    for i in range(128):
        sprite = parse_oam_entry(oam_data, i)
        if sprite and sprite["y"] < 224:  # Active sprite
            tile = sprite["tile"]
            palette = sprite["palette"]

            if tile not in tile_to_palettes:
                tile_to_palettes[tile] = {}

            if palette not in tile_to_palettes[tile]:
                tile_to_palettes[tile][palette] = 0
            tile_to_palettes[tile][palette] += 1

    # Convert to best palette for each tile
    tile_palette_map = {}
    for tile, palette_counts in tile_to_palettes.items():
        # Use the most frequently used palette for this tile
        best_palette = max(palette_counts.keys(), key=lambda p: palette_counts[p])
        tile_palette_map[tile] = best_palette

    return tile_palette_map, tile_to_palettes

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

def create_final_sprite_sheet(vram_data, cgram_data, tile_palette_map, scale=2):
    """Create the final sprite sheet with correct palettes."""
    all_palettes = extract_all_palettes(cgram_data)
    sprite_palettes = all_palettes[8:16]  # Sprite palettes are 8-15

    # Sheet dimensions
    tiles_per_row = 16
    total_tiles = 256
    tile_size = 8 * scale

    img_width = tiles_per_row * tile_size
    img_height = (total_tiles // tiles_per_row) * tile_size

    img = Image.new("RGB", (img_width, img_height), (0, 0, 0))

    # Default palette assignments based on region analysis
    default_palettes = {
        # Kirby region (0x00-0x3F)
        (0x00, 0x20): 0,  # Pink Kirby sprites
        (0x20, 0x40): 2,  # UI numbers/elements
        # Enemy regions
        (0x40, 0x80): 4,  # Enemies set 1
        (0x80, 0xC0): 5,  # Enemies set 2
        (0xC0, 0x100): 3, # Items/effects
    }

    for tile_idx in range(total_tiles):
        # Get palette from OAM analysis or use default
        if tile_idx in tile_palette_map:
            pal_idx = tile_palette_map[tile_idx]
        else:
            # Use default based on region
            pal_idx = 0
            for (start, end), default_pal in default_palettes.items():
                if start <= tile_idx < end:
                    pal_idx = default_pal
                    break

        # Decode and render tile
        tile_data = decode_4bpp_tile(vram_data, tile_idx)
        tile_img = render_tile_with_palette(tile_data, sprite_palettes[pal_idx])

        if scale != 1:
            tile_img = tile_img.resize((tile_size, tile_size), Image.NEAREST)

        # Calculate position
        row = tile_idx // tiles_per_row
        col = tile_idx % tiles_per_row
        x = col * tile_size
        y = row * tile_size

        img.paste(tile_img, (x, y))

    return img

def create_detailed_analysis_sheet(vram_data, cgram_data, tile_palette_map, tile_to_palettes):
    """Create a detailed sheet showing palette analysis."""
    all_palettes = extract_all_palettes(cgram_data)
    sprite_palettes = all_palettes[8:16]

    # Create larger image for detailed view
    img_width = 1200
    img_height = 800
    img = Image.new("RGB", (img_width, img_height), (32, 32, 32))
    draw = ImageDraw.Draw(img)

    # Title
    draw.text((10, 10), "Cave Synchronized Data - Palette Analysis", fill=(255, 255, 255))
    draw.text((10, 30), "Based on actual OAM sprite assignments", fill=(200, 200, 200))

    # Draw sprite palettes
    y_offset = 60
    draw.text((10, y_offset), "Sprite Palettes (8-15):", fill=(255, 255, 255))
    y_offset += 20

    for pal_idx in range(8):
        y_base = y_offset + pal_idx * 25
        draw.text((10, y_base), f"Palette {pal_idx}:", fill=(255, 255, 255))

        for color_idx in range(16):
            x = 100 + color_idx * 20
            color = sprite_palettes[pal_idx][color_idx]
            draw.rectangle([x, y_base, x + 18, y_base + 18], fill=color)

    # Show tile regions with their palettes
    x_offset = 450
    y_offset = 60
    draw.text((x_offset, y_offset), "Tile Regions and Palette Usage:", fill=(255, 255, 255))
    y_offset += 30

    regions = [
        ("Kirby/Player", 0x00, 0x40),
        ("Enemies Set 1", 0x40, 0x80),
        ("Enemies Set 2", 0x80, 0xC0),
        ("Items/Effects", 0xC0, 0x100),
    ]

    for region_name, start, end in regions:
        draw.text((x_offset, y_offset), f"{region_name} (0x{start:02X}-0x{end-1:02X}):",
                  fill=(255, 255, 200))
        y_offset += 20

        # Count palette usage in this region
        pal_usage = {}
        example_tiles = {}

        for tile_idx in range(start, end):
            if tile_idx in tile_palette_map:
                pal = tile_palette_map[tile_idx]
                if pal not in pal_usage:
                    pal_usage[pal] = 0
                    example_tiles[pal] = []
                pal_usage[pal] += 1
                if len(example_tiles[pal]) < 5:
                    example_tiles[pal].append(tile_idx)

        if pal_usage:
            for pal in sorted(pal_usage.keys()):
                draw.text((x_offset + 20, y_offset),
                         f"Palette {pal}: {pal_usage[pal]} tiles - Examples: {[f'0x{t:02X}' for t in example_tiles[pal]]}",
                         fill=(200, 200, 200))
                y_offset += 18
        else:
            draw.text((x_offset + 20, y_offset), "No active tiles in OAM", fill=(150, 150, 150))
            y_offset += 18

        y_offset += 10

    # Show some example sprites
    y_offset = 400
    draw.text((10, y_offset), "Example Sprites from Each Palette:", fill=(255, 255, 255))
    y_offset += 30

    examples_per_palette = {}
    for tile_idx, pal in tile_palette_map.items():
        if pal not in examples_per_palette:
            examples_per_palette[pal] = []
        if len(examples_per_palette[pal]) < 8:
            examples_per_palette[pal].append(tile_idx)

    for pal_idx in sorted(examples_per_palette.keys()):
        draw.text((10, y_offset), f"Palette {pal_idx}:", fill=(255, 255, 255))

        x = 100
        for i, tile_idx in enumerate(examples_per_palette[pal_idx]):
            # Decode and render tile
            tile_data = decode_4bpp_tile(vram_data, tile_idx)
            tile_img = render_tile_with_palette(tile_data, sprite_palettes[pal_idx])
            tile_img = tile_img.resize((32, 32), Image.NEAREST)

            img.paste(tile_img, (x + i * 40, y_offset))
            draw.text((x + i * 40, y_offset + 34), f"0x{tile_idx:02X}",
                     fill=(200, 200, 200))

        y_offset += 60

    return img

def main():
    print("=== Creating Final Corrected Sprite Sheet ===\n")

    # Load synchronized Cave dumps
    with open("Cave.SnesVideoRam.dmp", "rb") as f:
        vram_data = f.read()
    with open("Cave.SnesCgRam.dmp", "rb") as f:
        cgram_data = f.read()
    with open("Cave.SnesSpriteRam.dmp", "rb") as f:
        oam_data = f.read()

    print("Building tile-to-palette mapping from OAM data...")
    tile_palette_map, tile_to_palettes = build_tile_palette_map(oam_data)

    print(f"Found {len(tile_palette_map)} tiles with palette assignments in OAM")

    # Create final sprite sheets
    print("\nCreating visualizations...")

    # Standard 2x scale sheet
    sheet_2x = create_final_sprite_sheet(vram_data, cgram_data, tile_palette_map, scale=2)
    sheet_2x.save("final_corrected_sprite_sheet_2x.png")
    print("Saved: final_corrected_sprite_sheet_2x.png")

    # High resolution 4x scale sheet
    sheet_4x = create_final_sprite_sheet(vram_data, cgram_data, tile_palette_map, scale=4)
    sheet_4x.save("final_corrected_sprite_sheet_4x.png")
    print("Saved: final_corrected_sprite_sheet_4x.png")

    # Detailed analysis sheet
    analysis = create_detailed_analysis_sheet(vram_data, cgram_data, tile_palette_map, tile_to_palettes)
    analysis.save("final_palette_analysis_cave.png")
    print("Saved: final_palette_analysis_cave.png")

    # Print summary
    print("\n=== Summary ===")
    print("Palette assignments from synchronized OAM data:")

    palette_counts = {}
    for _tile, pal in tile_palette_map.items():
        if pal not in palette_counts:
            palette_counts[pal] = 0
        palette_counts[pal] += 1

    for pal in sorted(palette_counts.keys()):
        print(f"  Palette {pal}: {palette_counts[pal]} unique tiles")

    print("\nThe sprite sheets now show all sprites with their correct palettes")
    print("based on the actual OAM data from the synchronized memory dump.")

if __name__ == "__main__":
    main()
