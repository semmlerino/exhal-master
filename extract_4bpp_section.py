#!/usr/bin/env python3
"""
Extract a small 4bpp section of sprites for focused editing
"""

import json
import os

from PIL import Image

from sprite_edit_helpers import decode_4bpp_tile, parse_cgram


def extract_4bpp_section(
    vram_file,
    cgram_file,
    mapping_file=None,
    start_tile=0,
    tile_count=64,
    tiles_per_row=8,
    offset=0xC000,
    output_png="4bpp_section_ultrathink.png",
):
    """Extract a small section of sprites in indexed grayscale mode"""

    # Load palette mappings if available
    tile_to_palette = {}
    if mapping_file and os.path.exists(mapping_file):
        with open(mapping_file) as f:
            data = json.load(f)
        if "tile_mappings" in data:
            for tile_str, info in data["tile_mappings"].items():
                tile_idx = int(tile_str)
                tile_to_palette[tile_idx] = info["palette"]

    # Read VRAM data
    with open(vram_file, "rb") as f:
        f.seek(offset)
        vram_data = f.read(0x4000)  # Read full sprite area

    # Parse palettes
    palettes = parse_cgram(cgram_file)

    # Calculate section dimensions
    bytes_per_tile = 32
    rows = (tile_count + tiles_per_row - 1) // tiles_per_row

    sheet_width = tiles_per_row * 8
    sheet_height = rows * 8

    # Create grayscale sheet
    grayscale_sheet = Image.new("L", (sheet_width, sheet_height), 0)

    # Grayscale mapping for 4bpp (0-15 indices)
    gray_levels = {}
    gray_levels[0] = 0  # Transparent
    for i in range(1, 16):
        gray_levels[i] = int(17 + (i - 1) * (255 - 17) / 14)

    # Create metadata
    metadata = {
        "source_vram": os.path.abspath(vram_file),
        "source_cgram": os.path.abspath(cgram_file),
        "offset": offset,
        "start_tile": start_tile,
        "tile_count": tile_count,
        "tiles_per_row": tiles_per_row,
        "sheet_dimensions": [sheet_width, sheet_height],
        "tile_info": {},
        "palette_colors": {},
        "extraction_mode": "4bpp_section",
        "grayscale_mapping": {
            "description": "4bpp palette indices mapped to grayscale",
            "transparent": 0,
            "color_mapping": gray_levels,
        },
    }

    # Store original palette colors
    for pal_idx in range(16):
        colors = []
        for color_idx in range(16):
            color = palettes[pal_idx][color_idx]
            colors.append(list(color))
        metadata["palette_colors"][pal_idx] = colors

    # Process selected tiles
    extracted_tiles = 0
    for i in range(tile_count):
        tile_idx = start_tile + i

        # Check bounds
        if tile_idx * bytes_per_tile >= len(vram_data):
            break

        tile_data = vram_data[
            tile_idx * bytes_per_tile : (tile_idx + 1) * bytes_per_tile
        ]

        # Skip completely empty tiles
        if all(b == 0 for b in tile_data):
            continue

        extracted_tiles += 1

        # Decode tile
        pixels = decode_4bpp_tile(tile_data)

        # Get palette assignment
        oam_pal = tile_to_palette.get(tile_idx, 0)
        cgram_pal = oam_pal + 8

        # Calculate position in section
        section_x = (i % tiles_per_row) * 8
        section_y = (i // tiles_per_row) * 8

        # Create grayscale tile
        for py in range(8):
            for px in range(8):
                pixel_idx = py * 8 + px
                color_idx = pixels[pixel_idx]

                # Map 4bpp index to grayscale value
                gray_value = gray_levels[color_idx]
                grayscale_sheet.putpixel((section_x + px, section_y + py), gray_value)

        # Store tile metadata
        metadata["tile_info"][i] = {
            "original_tile_idx": tile_idx,
            "palette": oam_pal,
            "cgram_palette": cgram_pal,
            "empty": False,
            "section_x": section_x,
            "section_y": section_y,
        }

    # Convert to indexed mode
    palette_data = []
    for i in range(256):
        if i in gray_levels.values():
            palette_data.extend([i, i, i])
        else:
            palette_data.extend([0, 0, 0])

    indexed_sheet = grayscale_sheet.convert("P")
    indexed_sheet.putpalette(palette_data)

    # Save files
    indexed_sheet.save(output_png)

    metadata_file = output_png.replace(".png", "_metadata.json")
    with open(metadata_file, "w") as f:
        json.dump(metadata, f, indent=2)

    # Create editing guide
    _create_section_guide(
        indexed_sheet,
        gray_levels,
        start_tile,
        tile_count,
        output_png.replace(".png", "_guide.png"),
    )

    print(f"4bpp section extracted to: {output_png}")
    print(f"Metadata saved to: {metadata_file}")
    print(f"Section: tiles {start_tile}-{start_tile + tile_count - 1}")
    print(f"Extracted tiles with data: {extracted_tiles}/{tile_count}")
    print(f"Section dimensions: {sheet_width}x{sheet_height} pixels")
    print(f"Grid: {tiles_per_row} tiles per row, {rows} rows")

    return metadata


def _create_section_guide(sheet, gray_levels, start_tile, tile_count, output_file):
    """Create editing guide for the section"""
    guide_width = max(400, sheet.width + 150)
    guide_height = max(300, sheet.height + 100)

    guide = Image.new("RGB", (guide_width, guide_height), (40, 40, 40))

    # Paste the sprite section
    guide.paste(sheet.convert("RGB"), (10, 10))

    # Add info text area
    info_x = sheet.width + 20
    info_y = 10

    # Add grayscale reference swatches
    for idx, gray in sorted(gray_levels.items()):
        swatch = Image.new("RGB", (20, 20), (gray, gray, gray))
        guide.paste(swatch, (info_x, info_y + idx * 25))

    guide.save(output_file)
    print(f"Editing guide saved to: {output_file}")


def find_interesting_section(vram_file, offset=0xC000):
    """Find a section with interesting sprite data"""
    with open(vram_file, "rb") as f:
        f.seek(offset)
        vram_data = f.read(0x4000)

    bytes_per_tile = 32
    total_tiles = len(vram_data) // bytes_per_tile

    # Look for sections with good sprite density
    best_sections = []

    for start in range(0, total_tiles - 64, 8):  # Check every 8 tiles
        non_empty = 0
        for i in range(64):  # Check 64 tile section
            tile_idx = start + i
            if tile_idx >= total_tiles:
                break

            tile_data = vram_data[
                tile_idx * bytes_per_tile : (tile_idx + 1) * bytes_per_tile
            ]
            if not all(b == 0 for b in tile_data):
                non_empty += 1

        if non_empty > 20:  # Good density
            best_sections.append((start, non_empty))

    # Sort by sprite density
    best_sections.sort(key=lambda x: x[1], reverse=True)

    print("Best sections found:")
    for i, (start, count) in enumerate(best_sections[:5]):
        print(f"  {i+1}. Tiles {start}-{start+63}: {count}/64 sprites")

    return best_sections[0][0] if best_sections else 0


if __name__ == "__main__":
    vram_file = "Cave.SnesVideoRam.dmp"
    cgram_file = "Cave.SnesCgRam.dmp"
    mapping_file = "archive/analysis/final_palette_mapping.json"

    if all(os.path.exists(f) for f in [vram_file, cgram_file]):
        print("Finding interesting sprite section...")
        best_start = find_interesting_section(vram_file)
        print(f"\\nExtracting section starting at tile {best_start}...")

        extract_4bpp_section(
            vram_file,
            cgram_file,
            mapping_file,
            start_tile=best_start,
            tile_count=64,  # 8x8 tile grid
            tiles_per_row=8,
            output_png="kirby_4bpp_section_ultrathink.png",
        )
    else:
        print("Required dump files not found!")
