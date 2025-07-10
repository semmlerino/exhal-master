#!/usr/bin/env python3
"""
Extract sprites specifically for the indexed pixel editor
Uses the editor's expected color palette instead of grayscale
"""

# Standard library imports
import json
import os

# Third-party imports
from PIL import Image

# Local imports
from sprite_edit_helpers import decode_4bpp_tile, parse_cgram


def extract_for_pixel_editor(
    vram_file,
    cgram_file,
    mapping_file=None,
    start_tile=0,
    tile_count=64,
    tiles_per_row=8,
    offset=0xC000,
    output_png="editor_ready_ultrathink.png",
):
    """Extract sprites using the pixel editor's color palette"""

    # The indexed pixel editor's hardcoded palette (from the code)
    editor_palette = [
        (0, 0, 0),  # 0 - Black (transparent)
        (255, 183, 197),  # 1 - Kirby pink
        (255, 255, 255),  # 2 - White
        (64, 64, 64),  # 3 - Dark gray (outline)
        (255, 0, 0),  # 4 - Red
        (0, 0, 255),  # 5 - Blue
        (255, 220, 220),  # 6 - Light pink
        (200, 120, 150),  # 7 - Dark pink
        (255, 255, 0),  # 8 - Yellow
        (0, 255, 0),  # 9 - Green
        (255, 128, 0),  # 10 - Orange
        (128, 0, 255),  # 11 - Purple
        (0, 128, 128),  # 12 - Teal
        (128, 128, 0),  # 13 - Olive
        (128, 128, 128),  # 14 - Gray
        (192, 192, 192),  # 15 - Light gray
    ]

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
        vram_data = f.read(0x4000)

    # Parse original palettes for metadata
    palettes = parse_cgram(cgram_file)

    # Calculate dimensions
    bytes_per_tile = 32
    rows = (tile_count + tiles_per_row - 1) // tiles_per_row
    sheet_width = tiles_per_row * 8
    sheet_height = rows * 8

    # Create RGB image first, then convert to indexed
    rgb_sheet = Image.new("RGB", (sheet_width, sheet_height), (0, 0, 0))

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
        "extraction_mode": "pixel_editor_ready",
        "editor_palette": editor_palette,
        "index_mapping": {
            "description": "4bpp indices mapped to editor colors",
            "transparent": 0,
        },
    }

    # Store original palette colors for reinsertion
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

        # Create tile using editor palette
        for py in range(8):
            for px in range(8):
                pixel_idx = py * 8 + px
                color_idx = pixels[pixel_idx]

                # Use editor palette color for this index
                r, g, b = editor_palette[color_idx]
                rgb_sheet.putpixel((section_x + px, section_y + py), (r, g, b))

        # Store tile metadata
        metadata["tile_info"][i] = {
            "original_tile_idx": tile_idx,
            "palette": oam_pal,
            "cgram_palette": cgram_pal,
            "empty": False,
            "section_x": section_x,
            "section_y": section_y,
        }

    # Convert to indexed mode using the editor's palette
    indexed_sheet = rgb_sheet.convert("P", palette=Image.ADAPTIVE, colors=16)

    # Force the exact editor palette
    palette_data = []
    for r, g, b in editor_palette:
        palette_data.extend([r, g, b])
    # Fill remaining slots with black
    while len(palette_data) < 768:  # 256 * 3
        palette_data.extend([0, 0, 0])

    indexed_sheet.putpalette(palette_data)

    # Save files
    indexed_sheet.save(output_png)

    metadata_file = output_png.replace(".png", "_metadata.json")
    with open(metadata_file, "w") as f:
        json.dump(metadata, f, indent=2)

    # Create color reference
    _create_color_reference(editor_palette, output_png.replace(".png", "_colors.png"))

    print(f"Pixel editor ready sprite sheet: {output_png}")
    print(f"Metadata saved to: {metadata_file}")
    print(f"Section: tiles {start_tile}-{start_tile + tile_count - 1}")
    print(f"Extracted tiles with data: {extracted_tiles}/{tile_count}")
    print(f"Section dimensions: {sheet_width}x{sheet_height} pixels")
    print("\\nColor mapping:")
    for i, (r, g, b) in enumerate(editor_palette):
        if i == 0:
            print(f"  Index {i}: RGB({r},{g},{b}) - Transparent")
        else:
            print(f"  Index {i}: RGB({r},{g},{b})")

    return metadata


def _create_color_reference(palette, output_file):
    """Create visual color reference for the editor palette"""
    ref_width = 200
    ref_height = 16 * 25  # 16 colors, 25 pixels each

    ref_img = Image.new("RGB", (ref_width, ref_height), (40, 40, 40))

    # Draw color swatches
    for i, (r, g, b) in enumerate(palette):
        y_start = i * 25

        # Color swatch
        for y in range(20):
            for x in range(100):
                ref_img.putpixel((10 + x, y_start + y + 2), (r, g, b))

    ref_img.save(output_file)
    print(f"Color reference saved to: {output_file}")


if __name__ == "__main__":
    vram_file = "Cave.SnesVideoRam.dmp"
    cgram_file = "Cave.SnesCgRam.dmp"
    mapping_file = "archive/analysis/final_palette_mapping.json"

    if all(os.path.exists(f) for f in [vram_file, cgram_file]):
        print("Extracting sprites for indexed pixel editor...")

        # Small focused section - easier to work with
        extract_for_pixel_editor(
            vram_file,
            cgram_file,
            mapping_file,
            start_tile=0,
            tile_count=32,  # 8x4 grid
            tiles_per_row=8,
            output_png="kirby_editor_ready_ultrathink.png",
        )
    else:
        print("Required dump files not found!")
