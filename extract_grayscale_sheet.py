#!/usr/bin/env python3
"""
Extract sprite sheet in indexed grayscale mode for easier editing
"""

import json
import os

from PIL import Image

from sprite_edit_helpers import decode_4bpp_tile, parse_cgram


def extract_grayscale_sheet(vram_file, cgram_file, mapping_file=None,
                           oam_file=None, offset=0xC000, size=0x4000,
                           output_png="grayscale_sprite_sheet.png"):
    """Extract sprite sheet in indexed grayscale mode"""

    # Try to load OAM mapper if available
    oam_mapper = None
    try:
        from sprite_editor.oam_palette_mapper import OAMPaletteMapper
        if oam_file and os.path.exists(oam_file):
            print("Loading OAM data for palette mapping...")
            oam_mapper = OAMPaletteMapper()
            oam_mapper.parse_oam_dump(oam_file)
            oam_mapper.build_vram_palette_map(offset // 2)  # Convert byte to word offset
            oam_mapper.get_palette_usage_stats()
    except ImportError:
        print("OAM mapper not available, using fallback palette selection")

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
        vram_data = f.read(size)

    # Parse palettes (needed for metadata)
    palettes = parse_cgram(cgram_file)

    # Calculate dimensions
    bytes_per_tile = 32
    total_tiles = size // bytes_per_tile
    tiles_per_row = 16
    rows = (total_tiles + tiles_per_row - 1) // tiles_per_row

    sheet_width = tiles_per_row * 8
    sheet_height = rows * 8

    # Create indexed sheet directly with indices 0-15
    indexed_sheet = Image.new("P", (sheet_width, sheet_height), 0)

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
        "extraction_mode": "indexed_grayscale",
        "grayscale_mapping": {
            "description": "Palette indices mapped to grayscale values",
            "transparent": 0,
            "color_mapping": {}
        }
    }

    # Create simple index mapping: indices 0-15 map to themselves
    index_mapping = {}
    for i in range(16):
        index_mapping[i] = i

    metadata["grayscale_mapping"]["color_mapping"] = index_mapping

    # Store original palette colors for reinsertion
    for pal_idx in range(16):
        colors = []
        for color_idx in range(16):
            color = palettes[pal_idx][color_idx]
            colors.append(list(color))
        metadata["palette_colors"][pal_idx] = colors

    # Process tiles
    non_empty_tiles = 0
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

        # Calculate position
        x = (tile_idx % tiles_per_row) * 8
        y = (tile_idx // tiles_per_row) * 8

        # Create grayscale tile
        for py in range(8):
            for px in range(8):
                pixel_idx = py * 8 + px
                color_idx = pixels[pixel_idx]

                # Use palette index directly (0-15)
                indexed_sheet.putpixel((x + px, y + py), color_idx)

        # Store tile metadata
        metadata["tile_info"][tile_idx] = {
            "palette": oam_pal if oam_pal is not None else 0,
            "cgram_palette": cgram_pal,
            "empty": False,
            "x": x,
            "y": y,
            "source": "oam" if oam_mapper and oam_pal is not None else "json"
        }

    # Create grayscale palette for indices 0-15
    palette_data = []
    for i in range(256):
        if i < 16:
            # Map indices 0-15 to evenly spaced gray values
            if i == 0:
                gray = 0  # Transparent/black
            else:
                gray = int(17 + (i-1) * (255-17) / 14)
            palette_data.extend([gray, gray, gray])
        else:
            # Fill unused slots with black
            palette_data.extend([0, 0, 0])

    # Apply grayscale palette
    indexed_sheet.putpalette(palette_data)

    # Save the indexed grayscale sheet
    indexed_sheet.save(output_png)

    # Save metadata
    metadata_file = output_png.replace(".png", "_metadata.json")
    with open(metadata_file, "w") as f:
        json.dump(metadata, f, indent=2)

    # Create companion palette file
    palette_file = _create_companion_palette_file(palettes, metadata, output_png)

    # Create editing guide
    _create_grayscale_guide(indexed_sheet, index_mapping,
                           output_png.replace(".png", "_editing_guide.png"))

    print(f"Indexed grayscale sprite sheet extracted to: {output_png}")
    print(f"Metadata saved to: {metadata_file}")
    if palette_file:
        print(f"Companion palette saved to: {palette_file}")
    print(f"Non-empty tiles: {non_empty_tiles}/{total_tiles}")
    print(f"Sheet dimensions: {sheet_width}x{sheet_height}")
    print("\\nIndex to grayscale display mapping:")
    for i in range(16):
        if i == 0:
            gray = 0
            desc = " (transparent/black)"
        else:
            gray = int(17 + (i-1) * (255-17) / 14)
            desc = ""
        print(f"  Index {i}: Gray {gray}{desc}")

    print("\\n🎨 Workflow: Load the .png file in the indexed pixel editor")
    print("   and it will automatically offer to load the .pal.json palette!")

    return metadata

def _create_companion_palette_file(palettes, metadata, output_png):
    """Create companion .pal.json file for the grayscale sheet"""

    # Determine which palette to use based on OAM data if available
    best_palette_idx = 8  # Default to Kirby's palette

    # Check if we have OAM source info
    oam_file = metadata.get("source_oam")
    oam_stats = None

    if oam_file and os.path.exists(oam_file):
        try:
            from sprite_editor.oam_palette_mapper import OAMPaletteMapper
            mapper = OAMPaletteMapper()
            mapper.parse_oam_dump(oam_file)
            oam_stats = mapper.get_palette_usage_stats()

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
                # Check for pink/purple/red colors typical of Kirby
                # Palette 8 has purple/magenta colors (high red, low green, high blue)
                has_purple = any(r > 200 and g < 100 and b > 200 for r, g, b in colors)
                has_pink = any(r > 200 and g < 150 and b < 200 for r, g, b in colors)
                has_red = any(r > 180 and g < 100 and b < 100 for r, g, b in colors)

                if has_purple or has_pink or has_red:
                    kirby_palettes.append(pal_idx)

            # Choose the Kirby palette with most usage
            if kirby_palettes:
                best_palette_idx = max(kirby_palettes, key=lambda p: sprite_palette_usage.get(p, 0))
            elif sprite_palette_usage:
                # Fallback to most used sprite palette
                best_palette_idx = max(sprite_palette_usage, key=sprite_palette_usage.get)
        except ImportError:
            pass

    # Fallback to tile usage analysis if no OAM data
    if oam_stats is None:
        tile_info = metadata.get("tile_info", {})
        if tile_info:
            palette_usage = {}
            for tile in tile_info.values():
                pal_idx = tile.get("cgram_palette", 8)
                palette_usage[pal_idx] = palette_usage.get(pal_idx, 0) + 1

            # Find most used sprite palette (8-15)
            sprite_palettes = {k: v for k, v in palette_usage.items() if 8 <= k <= 15}
            if sprite_palettes:
                best_palette_idx = max(sprite_palettes, key=sprite_palettes.get)

    # Create palette data in .pal.json format
    palette_colors = palettes[best_palette_idx]

    palette_data = {
        "format_version": "1.0",
        "format_description": "Indexed Pixel Editor Palette File",
        "source": {
            "cgram_file": metadata.get("source_cgram", "unknown"),
            "palette_index": best_palette_idx,
            "extraction_tool": "extract_grayscale_sheet.py",
            "companion_image": os.path.basename(output_png)
        },
        "palette": {
            "name": f"Extracted Sprite Palette {best_palette_idx}",
            "colors": [list(color) for color in palette_colors],
            "color_count": len(palette_colors),
            "format": "RGB888"
        },
        "usage_hints": {
            "transparent_index": 0,
            "typical_use": "sprite",
            "kirby_palette": best_palette_idx == 8,
            "extraction_mode": "grayscale_companion"
        },
        "editor_compatibility": {
            "indexed_pixel_editor": True,
            "supports_grayscale_mode": True,
            "auto_loadable": True,
            "companion_to": os.path.basename(output_png)
        }
    }

    # Save palette file with .pal.json extension
    palette_file = output_png.replace(".png", ".pal.json")
    with open(palette_file, "w") as f:
        json.dump(palette_data, f, indent=2)

    print(f"Companion palette file created: {palette_file}")
    print(f"Using palette {best_palette_idx} (most common sprite palette)")

    return palette_file

def _create_grayscale_guide(sheet, index_mapping, output_file):
    """Create editing guide showing grayscale values"""
    guide_width = sheet.width + 200
    guide_height = sheet.height + 100

    guide = Image.new("RGB", (guide_width, guide_height), (40, 40, 40))

    # Paste the sprite sheet
    guide.paste(sheet.convert("RGB"), (10, 10))

    # Add grayscale reference
    ref_x = sheet.width + 20
    ref_y = 10

    # Create color swatches
    for idx in range(16):
        gray = 0 if idx == 0 else int(17 + (idx - 1) * (255 - 17) / 14)
        swatch = Image.new("RGB", (30, 30), (gray, gray, gray))
        guide.paste(swatch, (ref_x, ref_y + idx * 35))

    guide.save(output_file)
    print(f"Editing guide saved to: {output_file}")

if __name__ == "__main__":
    # Extract grayscale sprite sheet
    vram_file = "Cave.SnesVideoRam.dmp"
    cgram_file = "Cave.SnesCgRam.dmp"
    oam_file = "Cave.SnesSpriteRam.dmp"
    mapping_file = "archive/analysis/final_palette_mapping.json"

    if all(os.path.exists(f) for f in [vram_file, cgram_file]):
        extract_grayscale_sheet(
            vram_file, cgram_file, mapping_file, oam_file,
            output_png="kirby_sprites_grayscale_ultrathink.png"
        )
    else:
        print("Required dump files not found!")
