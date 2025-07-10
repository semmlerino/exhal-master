#!/usr/bin/env python3
"""Parse synchronized MSS savestate and dump files to determine correct palette mappings."""

import struct

from PIL import Image, ImageDraw


def parse_mss_savestate(filename):
    """Parse MSS savestate file format."""
    with open(filename, "rb") as f:
        data = f.read()

    print(f"MSS file size: {len(data)} bytes")

    # MSS format structure (based on analysis):
    # Header: 0x00-0x1F (32 bytes)
    # CPU registers: 0x20-0x4F (48 bytes)
    # Main RAM: 0x50-0x2004F (131072 bytes)
    # VRAM: 0x20050-0x3004F (65536 bytes)
    # CGRAM: 0x30050-0x3024F (512 bytes)
    # OAM: 0x30250-0x3046F (544 bytes)

    vram_offset = 0x20050
    cgram_offset = 0x30050
    oam_offset = 0x30250

    # Extract memory regions
    vram = data[vram_offset:vram_offset + 65536]
    cgram = data[cgram_offset:cgram_offset + 512]
    oam = data[oam_offset:oam_offset + 544]

    return vram, cgram, oam

def compare_data(savestate_data, dump_data, name):
    """Compare savestate data with dump file."""
    if len(savestate_data) != len(dump_data):
        print(f"{name}: Size mismatch - savestate: {len(savestate_data)}, dump: {len(dump_data)}")
        return False

    differences = sum(1 for i in range(len(savestate_data)) if savestate_data[i] != dump_data[i])
    if differences == 0:
        print(f"{name}: Perfect match!")
        return True
    print(f"{name}: {differences} bytes differ ({differences/len(savestate_data)*100:.2f}%)")
    return False

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

    print("\n=== OAM Analysis ===")
    print("Active sprites:")

    for i in range(128):
        sprite = parse_oam_entry(oam_data, i)
        if sprite and sprite["y"] < 224:  # Active sprite
            palette = sprite["palette"]
            tile = sprite["tile"]

            if palette not in palette_usage:
                palette_usage[palette] = []
            palette_usage[palette].append(i)

            if tile not in tile_to_palette:
                tile_to_palette[tile] = set()
            tile_to_palette[tile].add(palette)

            if i < 20:  # Show first 20 active sprites
                print(f"  Sprite {i:3d}: Tile {tile:3d} (0x{tile:02X}), Palette {palette}, Pos ({sprite['x']}, {sprite['y']})")

    print("\n=== Palette Usage Summary ===")
    for pal in sorted(palette_usage.keys()):
        print(f"Palette {pal}: {len(palette_usage[pal])} sprites")
        # Show some example tiles
        example_tiles = set()
        for sprite_idx in palette_usage[pal][:5]:
            sprite = parse_oam_entry(oam_data, sprite_idx)
            if sprite:
                example_tiles.add(sprite["tile"])
        print(f"  Example tiles: {sorted(example_tiles)}")

    return palette_usage, tile_to_palette

def decode_snes_color(color_bytes):
    """Decode SNES 15-bit color to RGB."""
    color = struct.unpack("<H", color_bytes)[0]
    r = (color & 0x1F) << 3
    g = ((color >> 5) & 0x1F) << 3
    b = ((color >> 10) & 0x1F) << 3
    return (r, g, b)

def extract_palettes(cgram_data):
    """Extract all palettes from CGRAM."""
    palettes = []
    for pal_idx in range(16):
        palette = []
        for color_idx in range(16):
            offset = (pal_idx * 16 + color_idx) * 2
            color = decode_snes_color(cgram_data[offset:offset+2])
            palette.append(color)
        palettes.append(palette)
    return palettes

def main():
    print("=== Parsing Synchronized Data ===\n")

    # Parse MSS savestate
    mss_file = "Kirby Super Star (USA)_2.mss"
    print(f"Parsing {mss_file}...")
    mss_vram, mss_cgram, mss_oam = parse_mss_savestate(mss_file)

    # Save extracted data for verification
    with open("mss2_VRAM.dmp", "wb") as f:
        f.write(mss_vram)
    with open("mss2_CGRAM.dmp", "wb") as f:
        f.write(mss_cgram)
    with open("mss2_OAM.dmp", "wb") as f:
        f.write(mss_oam)

    print("\nComparing with Cave dump files...")

    # Load Cave dump files
    with open("Cave.SnesVideoRam.dmp", "rb") as f:
        cave_vram = f.read()
    with open("Cave.SnesCgRam.dmp", "rb") as f:
        cave_cgram = f.read()
    with open("Cave.SnesSpriteRam.dmp", "rb") as f:
        cave_oam = f.read()

    # Compare data
    compare_data(mss_vram, cave_vram, "VRAM")
    compare_data(mss_cgram, cave_cgram, "CGRAM")
    compare_data(mss_oam, cave_oam, "OAM")

    # Analyze OAM palette usage
    print("\nAnalyzing OAM data from savestate...")
    palette_usage, tile_to_palette = analyze_oam_palettes(mss_oam)

    # Extract and display palettes
    print("\n=== CGRAM Palettes ===")
    palettes = extract_palettes(mss_cgram)

    # Create palette visualization
    img_width = 16 * 20 + 100
    img_height = 16 * 20 + 40
    img = Image.new("RGB", (img_width, img_height), (64, 64, 64))
    draw = ImageDraw.Draw(img)

    for pal_idx, palette in enumerate(palettes):
        y_base = 20 + pal_idx * 20

        # Draw palette colors
        for color_idx, color in enumerate(palette):
            x = 20 + color_idx * 20
            draw.rectangle([x, y_base, x + 18, y_base + 18], fill=color)

        # Label
        draw.text((360, y_base + 5), f"Pal {pal_idx}", fill=(255, 255, 255))

        # Show usage
        if pal_idx in palette_usage:
            count = len(palette_usage[pal_idx])
            draw.text((420, y_base + 5), f"({count} sprites)", fill=(200, 200, 200))

    img.save("synchronized_palette_analysis.png")
    print("\nSaved synchronized_palette_analysis.png")

    # Analyze tile regions and their palette assignments
    print("\n=== Tile Region Analysis ===")

    # Group tiles by region (every 64 tiles)
    regions = {}
    for tile, pals in tile_to_palette.items():
        region = tile // 64
        if region not in regions:
            regions[region] = {}
        regions[region][tile] = pals

    for region in sorted(regions.keys()):
        tiles_in_region = regions[region]
        print(f"\nRegion {region} (tiles {region*64}-{region*64+63}):")

        # Count palette usage in this region
        pal_count = {}
        for tile, pals in tiles_in_region.items():
            for pal in pals:
                pal_count[pal] = pal_count.get(pal, 0) + 1

        for pal in sorted(pal_count.keys()):
            print(f"  Palette {pal}: {pal_count[pal]} tiles")
            # Show example tiles
            examples = []
            for tile, pals in tiles_in_region.items():
                if pal in pals and len(examples) < 5:
                    examples.append(tile)
            print(f"    Example tiles: {examples}")

if __name__ == "__main__":
    main()
