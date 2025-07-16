#!/usr/bin/env python3
"""
Extract palette mappings from Mesen-S savestate file.
MSS format contains compressed VRAM, CGRAM, and OAM data.
"""

import json
import struct
import zlib


def parse_mss_savestate(filename):
    """Parse MSS savestate and extract memory regions"""
    with open(filename, "rb") as f:
        # Read header
        signature = f.read(3)
        if signature != b"MSS":
            raise ValueError(f"Not a valid MSS file (got {signature})")

        # Skip to compressed data (offset 0x23)
        f.seek(0x23)
        compressed_data = f.read()

        # Decompress
        decompressed = zlib.decompress(compressed_data)

        # Extract memory regions
        vram_data = decompressed[0x00000:0x10000]  # 64KB VRAM
        cgram_data = decompressed[0x10000:0x10200]  # 512B CGRAM
        oam_data = decompressed[0x10200:0x10420]   # 544B OAM

        return vram_data, cgram_data, oam_data

def analyze_oam_palette_usage(oam_data):
    """Analyze which palettes are used by visible sprites"""
    palette_usage = {}
    sprite_details = []

    for i in range(128):
        # Parse OAM entry
        base = i * 4
        x_low = oam_data[base]
        y = oam_data[base + 1]
        tile_lo = oam_data[base + 2]
        attr = oam_data[base + 3]

        # High table bits
        hi_byte = oam_data[0x200 + (i // 4)]
        hi_pair = (hi_byte >> ((i % 4) * 2)) & 0b11
        x_high = hi_pair & 0b01
        size_bit = (hi_pair >> 1) & 0b01

        x = x_low + (x_high << 8)
        tile = tile_lo | ((attr & 0x01) << 8)
        palette = (attr >> 1) & 0x07

        # Only count visible sprites
        if y < 224:
            if palette not in palette_usage:
                palette_usage[palette] = 0
            palette_usage[palette] += 1

            sprite_details.append({
                "index": i,
                "x": x,
                "y": y,
                "tile": tile,
                "palette": palette,
                "size": "large" if size_bit else "small"
            })

    return palette_usage, sprite_details

def decode_cgram_palette(cgram_data, palette_num):
    """Decode a palette from CGRAM data"""
    colors = []
    base = palette_num * 32  # 16 colors * 2 bytes each

    for i in range(16):
        offset = base + (i * 2)
        if offset + 1 < len(cgram_data):
            color = struct.unpack("<H", cgram_data[offset:offset+2])[0]
            b = ((color >> 10) & 0x1F) * 8
            g = ((color >> 5) & 0x1F) * 8
            r = (color & 0x1F) * 8
            colors.append({"r": r, "g": g, "b": b})

    return colors

def main():
    savestate_file = "Kirby Super Star (USA)_2.mss"

    print(f"=== Analyzing {savestate_file} ===\n")

    # Parse savestate
    vram_data, cgram_data, oam_data = parse_mss_savestate(savestate_file)

    print("Extracted data sizes:")
    print(f"  VRAM: {len(vram_data)} bytes")
    print(f"  CGRAM: {len(cgram_data)} bytes")
    print(f"  OAM: {len(oam_data)} bytes")

    # Analyze OAM palette usage
    palette_usage, sprite_details = analyze_oam_palette_usage(oam_data)

    print("\nOAM Palette Usage (visible sprites only):")
    for pal, count in sorted(palette_usage.items()):
        print(f"  OAM Palette {pal}: {count} sprites")

    # Map tiles to palettes
    tile_to_palette = {}
    for sprite in sprite_details:
        tile = sprite["tile"]
        pal = sprite["palette"]
        tile_to_palette[tile] = pal

        # For large sprites, map additional tiles
        if sprite["size"] == "large":
            tile_to_palette[tile + 1] = pal
            tile_to_palette[tile + 16] = pal
            tile_to_palette[tile + 17] = pal

    print(f"\nMapped {len(tile_to_palette)} unique tiles to palettes")

    # Analyze CGRAM palettes
    print("\nCGRAM Analysis:")
    print("OBJ palettes (8-15) colors:")

    for obj_pal in range(8):
        cgram_pal = obj_pal + 8
        colors = decode_cgram_palette(cgram_data, cgram_pal)
        if colors and len(colors) > 5:
            # Show first few colors as preview
            preview = f"OBJ Palette {obj_pal} (CGRAM {cgram_pal}): "
            preview += f"[{colors[1]['r']},{colors[1]['g']},{colors[1]['b']}] "
            preview += f"[{colors[2]['r']},{colors[2]['g']},{colors[2]['b']}] "
            preview += f"[{colors[3]['r']},{colors[3]['g']},{colors[3]['b']}]"
            print(f"  {preview}")

    # Save extracted data for further analysis
    with open("vram_from_savestate.dmp", "wb") as f:
        f.write(vram_data)
    with open("cgram_from_savestate.dmp", "wb") as f:
        f.write(cgram_data)
    with open("oam_from_savestate.dmp", "wb") as f:
        f.write(oam_data)

    print("\nSaved extracted memory dumps:")
    print("  - vram_from_savestate.dmp")
    print("  - cgram_from_savestate.dmp")
    print("  - oam_from_savestate.dmp")

    # Export mapping data
    mapping_data = {
        "palette_usage": palette_usage,
        "tile_to_palette": tile_to_palette,
        "sprite_count": len(sprite_details),
        "active_palettes": list(palette_usage.keys())
    }

    with open("savestate_palette_mapping.json", "w") as f:
        json.dump(mapping_data, f, indent=2)

    print("\nExported palette mapping to savestate_palette_mapping.json")

    # Create region analysis based on tile ranges
    print("\n\nRegion Analysis (based on tile numbers):")
    region_tiles = {}

    for sprite in sprite_details:
        tile = sprite["tile"]
        pal = sprite["palette"]

        # Categorize by tile range
        if tile < 64:
            region = "Kirby sprites (0-63)"
        elif tile < 128:
            region = "UI/HUD (64-127)"
        elif tile < 192:
            region = "Enemies 1 (128-191)"
        elif tile < 256:
            region = "Enemies 2 (192-255)"
        else:
            region = f"Other ({tile})"

        if region not in region_tiles:
            region_tiles[region] = {}
        if pal not in region_tiles[region]:
            region_tiles[region][pal] = 0
        region_tiles[region][pal] += 1

    for region, palettes in sorted(region_tiles.items()):
        print(f"\n{region}:")
        for pal, count in sorted(palettes.items()):
            print(f"  OAM Palette {pal}: {count} sprites")

if __name__ == "__main__":
    main()
