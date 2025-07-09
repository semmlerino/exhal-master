#!/usr/bin/env python3
"""
Fix the palette selection logic in extract_grayscale_sheet.py to use OAM data
for more accurate palette assignment.
"""

import json
import os

from PIL import Image

from sprite_edit_helpers import decode_4bpp_tile, parse_cgram
from sprite_editor.oam_palette_mapper import OAMPaletteMapper


def extract_grayscale_sheet_with_oam(vram_file, cgram_file, oam_file=None,
                                     mapping_file=None, offset=0xC000, size=0x4000,
                                     output_png="grayscale_sprite_sheet.png"):
    """Extract sprite sheet in indexed grayscale mode with OAM-based palette mapping"""

    # Load OAM palette mappings if available
    oam_mapper = None
    oam_stats = None
    if oam_file and os.path.exists(oam_file):
        print("Loading OAM data for palette mapping...")
        oam_mapper = OAMPaletteMapper()
        oam_mapper.parse_oam_dump(oam_file)
        oam_mapper.build_vram_palette_map(offset // 2)  # Convert byte to word offset
        oam_stats = oam_mapper.get_palette_usage_stats()

        print("OAM Palette usage:")
        for pal, count in sorted(oam_stats["palette_counts"].items()):
            print(f"  OAM Palette {pal} (CGRAM {pal + 8}): {count} sprites")

    # Load palette mappings from JSON if available (as fallback)
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
        vram_data = f.read(size)

    # Parse palettes
    palettes = parse_cgram(cgram_file)

    # Calculate dimensions
    bytes_per_tile = 32
    total_tiles = size // bytes_per_tile
    tiles_per_row = 16
    rows = (total_tiles + tiles_per_row - 1) // tiles_per_row

    sheet_width = tiles_per_row * 8
    sheet_height = rows * 8

    # Create grayscale sheet
    grayscale_sheet = Image.new("L", (sheet_width, sheet_height), 0)

    # Create metadata
    metadata = {
        "source_vram": os.path.abspath(vram_file),
        "source_cgram": os.path.abspath(cgram_file),
        "source_oam": os.path.abspath(oam_file) if oam_file else None,
        "offset": offset,
        "size": size,
        "tiles_per_row": tiles_per_row,
        "total_tiles": total_tiles,
        "tile_info": {},
        "palette_colors": {},
        "extraction_mode": "indexed_grayscale_oam",
        "grayscale_mapping": {
            "description": "Palette indices mapped to grayscale values",
            "transparent": 0,
            "color_mapping": {}
        }
    }

    # Create grayscale mapping
    gray_levels = {}
    gray_levels[0] = 0  # Transparent
    for i in range(1, 16):
        gray_levels[i] = int(17 + (i-1) * (255-17) / 14)

    metadata["grayscale_mapping"]["color_mapping"] = gray_levels

    # Store all palette colors
    for pal_idx in range(16):
        colors = []
        for color_idx in range(16):
            color = palettes[pal_idx][color_idx]
            colors.append(list(color))
        metadata["palette_colors"][pal_idx] = colors

    # Process tiles
    non_empty_tiles = 0
    tile_palette_assignments = {}

    for tile_idx in range(total_tiles):
        tile_data = vram_data[tile_idx * bytes_per_tile:(tile_idx + 1) * bytes_per_tile]

        # Skip empty tiles
        if all(b == 0 for b in tile_data):
            continue

        non_empty_tiles += 1

        # Decode tile
        pixels = decode_4bpp_tile(tile_data)

        # Get palette assignment
        # First try OAM mapper
        oam_pal = None
        cgram_pal = None

        if oam_mapper:
            # Calculate VRAM offset for this tile
            vram_offset = offset + (tile_idx * bytes_per_tile)
            oam_pal = oam_mapper.get_palette_for_vram_offset(vram_offset)
            if oam_pal is not None:
                cgram_pal = oam_pal + 8

        # Fallback to JSON mapping
        if cgram_pal is None:
            json_pal = tile_to_palette.get(tile_idx, 0)
            cgram_pal = json_pal + 8
            oam_pal = json_pal

        # Store assignment
        tile_palette_assignments[tile_idx] = cgram_pal

        # Calculate position
        x = (tile_idx % tiles_per_row) * 8
        y = (tile_idx // tiles_per_row) * 8

        # Create grayscale tile
        for py in range(8):
            for px in range(8):
                pixel_idx = py * 8 + px
                color_idx = pixels[pixel_idx]
                gray_value = gray_levels[color_idx]
                grayscale_sheet.putpixel((x + px, y + py), gray_value)

        # Store tile metadata
        metadata["tile_info"][tile_idx] = {
            "palette": oam_pal if oam_pal is not None else 0,
            "cgram_palette": cgram_pal,
            "empty": False,
            "x": x,
            "y": y,
            "source": "oam" if oam_pal is not None else "json"
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

    # Save the indexed grayscale sheet
    indexed_sheet.save(output_png)

    # Save metadata
    metadata_file = output_png.replace(".png", "_metadata.json")
    with open(metadata_file, "w") as f:
        json.dump(metadata, f, indent=2)

    # Create companion palette file with better logic
    palette_file = _create_smart_companion_palette(palettes, metadata, tile_palette_assignments,
                                                   oam_stats, output_png)

    print(f"\\nIndexed grayscale sprite sheet extracted to: {output_png}")
    print(f"Metadata saved to: {metadata_file}")
    if palette_file:
        print(f"Companion palette saved to: {palette_file}")
    print(f"Non-empty tiles: {non_empty_tiles}/{total_tiles}")
    print(f"Sheet dimensions: {sheet_width}x{sheet_height}")

    return metadata

def _create_smart_companion_palette(palettes, metadata, tile_assignments, oam_stats, output_png):
    """Create companion palette file with smarter selection logic"""

    # Determine best palette based on multiple factors
    best_palette_idx = 8  # Default to Kirby's palette

    if oam_stats and oam_stats["palette_counts"]:
        # Find sprite palette (8-15) with most OAM usage that has Kirby colors
        sprite_palette_usage = {}
        for oam_pal, count in oam_stats["palette_counts"].items():
            cgram_pal = oam_pal + 8
            if 8 <= cgram_pal <= 15:
                sprite_palette_usage[cgram_pal] = count

        # Check for Kirby colors in each palette
        kirby_palettes = []
        for pal_idx in sprite_palette_usage:
            colors = palettes[pal_idx]
            # Check for pink/red colors typical of Kirby
            has_pink = any(r > 200 and g < 150 and b < 150 for r, g, b in colors)
            has_red = any(r > 180 and g < 100 and b < 100 for r, g, b in colors)

            if has_pink or has_red:
                kirby_palettes.append(pal_idx)

        # Choose the Kirby palette with most usage
        if kirby_palettes:
            best_palette_idx = max(kirby_palettes, key=lambda p: sprite_palette_usage.get(p, 0))
        elif sprite_palette_usage:
            # Fallback to most used sprite palette
            best_palette_idx = max(sprite_palette_usage, key=sprite_palette_usage.get)

    # Create palette data
    palette_colors = palettes[best_palette_idx]

    palette_data = {
        "format_version": "1.0",
        "format_description": "Indexed Pixel Editor Palette File",
        "source": {
            "cgram_file": metadata.get("source_cgram", "unknown"),
            "oam_file": metadata.get("source_oam", "none"),
            "palette_index": best_palette_idx,
            "extraction_tool": "fix_palette_selection.py",
            "companion_image": os.path.basename(output_png),
            "selection_method": "oam_based" if oam_stats else "default"
        },
        "palette": {
            "name": f"Smart Selected Sprite Palette {best_palette_idx}",
            "colors": [list(color) for color in palette_colors],
            "color_count": len(palette_colors),
            "format": "RGB888"
        },
        "usage_hints": {
            "transparent_index": 0,
            "typical_use": "sprite",
            "kirby_palette": best_palette_idx == 8,
            "oam_sprite_count": oam_stats["palette_counts"].get(best_palette_idx - 8, 0) if oam_stats else 0,
            "extraction_mode": "oam_smart_selection"
        },
        "editor_compatibility": {
            "indexed_pixel_editor": True,
            "supports_grayscale_mode": True,
            "auto_loadable": True,
            "companion_to": os.path.basename(output_png)
        }
    }

    # Save palette file
    palette_file = output_png.replace(".png", ".pal.json")
    with open(palette_file, "w") as f:
        json.dump(palette_data, f, indent=2)

    usage_count = oam_stats["palette_counts"].get(best_palette_idx - 8, 0) if oam_stats else 0
    print(f"\\nCompanion palette file created: {palette_file}")
    print(f"Selected palette {best_palette_idx} (OAM usage: {usage_count} sprites)")

    return palette_file

def main():
    """Extract grayscale sheet with improved palette selection"""

    # File paths
    vram_file = "Cave.SnesVideoRam.dmp"
    cgram_file = "Cave.SnesCgRam.dmp"
    oam_file = "Cave.SnesSpriteRam.dmp"
    mapping_file = "archive/analysis/final_palette_mapping.json"

    # Check if files exist
    required_files = [vram_file, cgram_file]
    missing_files = [f for f in required_files if not os.path.exists(f)]

    if missing_files:
        print("Missing required files:")
        for f in missing_files:
            print(f"  - {f}")
        return

    if not os.path.exists(oam_file):
        print(f"Warning: OAM file '{oam_file}' not found. Using fallback palette selection.")
        oam_file = None

    # Extract with improved logic
    extract_grayscale_sheet_with_oam(
        vram_file, cgram_file, oam_file, mapping_file,
        output_png="kirby_sprites_grayscale_fixed.png"
    )

if __name__ == "__main__":
    main()
