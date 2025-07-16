#!/usr/bin/env python3
"""Extract specific sprites for focused editing."""

import sys
from pathlib import Path
from PIL import Image
from extract_for_pixel_editor import read_cgram_palette, create_palette_json


def extract_tiles(vram_file, tile_numbers, output_prefix, scale=4):
    """Extract specific tiles at a given scale."""
    # Read VRAM
    with open(vram_file, 'rb') as f:
        f.seek(0xC000)  # Sprite offset
        vram_data = f.read()
    
    # Create image for tiles
    tiles_per_row = min(len(tile_numbers), 8)
    rows = (len(tile_numbers) + tiles_per_row - 1) // tiles_per_row
    
    img_width = tiles_per_row * 8 * scale
    img_height = rows * 8 * scale
    
    # Create grayscale image
    img = Image.new('P', (img_width // scale, img_height // scale))
    
    # Set grayscale palette
    grayscale_palette = []
    for i in range(256):
        gray = (i * 255) // 15 if i < 16 else 0
        grayscale_palette.extend([gray, gray, gray])
    img.putpalette(grayscale_palette)
    
    # Extract specified tiles
    for idx, tile_num in enumerate(tile_numbers):
        x = (idx % tiles_per_row) * 8
        y = (idx // tiles_per_row) * 8
        
        # Get tile data
        tile_offset = tile_num * 32
        if tile_offset + 32 <= len(vram_data):
            tile_data = vram_data[tile_offset:tile_offset + 32]
            
            # Decode 4bpp tile
            for py in range(8):
                for px in range(8):
                    byte_offset = py * 2
                    bit_offset = 7 - px
                    
                    pixel = 0
                    if tile_data[byte_offset] & (1 << bit_offset):
                        pixel |= 1
                    if tile_data[byte_offset + 1] & (1 << bit_offset):
                        pixel |= 2
                    if tile_data[byte_offset + 16] & (1 << bit_offset):
                        pixel |= 4
                    if tile_data[byte_offset + 17] & (1 << bit_offset):
                        pixel |= 8
                    
                    img.putpixel((x + px, y + py), pixel)
    
    # Scale up
    if scale > 1:
        img = img.resize((img_width, img_height), Image.NEAREST)
    
    # Save
    output_file = f"{output_prefix}.png"
    img.save(output_file)
    print(f"Extracted {len(tile_numbers)} tiles to: {output_file}")
    return output_file


def main():
    if len(sys.argv) < 2:
        print("Extract Specific Sprites for Editing")
        print("===================================")
        print()
        print("Usage: python3 extract_specific_sprites.py <preset>")
        print()
        print("Presets:")
        print("  kirby     - Extract Kirby sprites (tiles 0-19)")
        print("  ui        - Extract UI elements (tiles 32-51)")
        print("  enemies   - Extract enemy sprites (tiles 160-179)")
        print("  custom    - Extract custom tile range")
        print()
        print("Or specify tile numbers directly:")
        print("  python3 extract_specific_sprites.py 0 2 3 4 18 19")
        return
    
    # Determine dumps to use
    if Path("Cave.SnesVideoRam.dmp").exists():
        vram_file = "Cave.SnesVideoRam.dmp"
        cgram_file = "Cave.SnesCgRam.dmp"
        prefix = "cave"
    else:
        print("Error: No Cave dumps found!")
        return
    
    # Parse arguments
    preset = sys.argv[1].lower()
    
    if preset == "kirby":
        tile_numbers = [0, 2, 3, 4, 18, 19]
        output_prefix = "kirby_sprites_edit"
        palette_idx = 8
        palette_name = "Kirby (Pink)"
    elif preset == "ui":
        tile_numbers = [32, 34, 35, 36, 50, 51]
        output_prefix = "ui_sprites_edit"
        palette_idx = 12
        palette_name = "UI/HUD"
    elif preset == "enemies":
        tile_numbers = list(range(160, 180))
        output_prefix = "enemy_sprites_edit"
        palette_idx = 14
        palette_name = "Boss/Enemy"
    elif preset == "custom":
        start = int(input("Start tile number: "))
        end = int(input("End tile number (inclusive): "))
        tile_numbers = list(range(start, end + 1))
        output_prefix = f"tiles_{start}-{end}_edit"
        palette_idx = int(input("Palette index (8-15): "))
        palette_name = f"Palette {palette_idx}"
    else:
        # Try to parse as tile numbers
        try:
            tile_numbers = [int(x) for x in sys.argv[1:]]
            output_prefix = f"tiles_{'_'.join(map(str, tile_numbers[:5]))}_edit"
            palette_idx = 8  # Default to Kirby palette
            palette_name = "Default"
        except ValueError:
            print(f"Unknown preset: {preset}")
            return
    
    print(f"Extracting tiles: {tile_numbers[:10]}{'...' if len(tile_numbers) > 10 else ''}")
    
    # Extract tiles
    img_file = extract_tiles(vram_file, tile_numbers, output_prefix, scale=4)
    
    # Create palette file
    palette_colors = read_cgram_palette(cgram_file, palette_idx)
    pal_file = f"{output_prefix}.pal.json"
    
    source_info = {
        "cgram_file": cgram_file,
        "palette_index": palette_idx,
        "tile_numbers": tile_numbers,
        "extraction_tool": "extract_specific_sprites.py"
    }
    
    create_palette_json(palette_colors, palette_name, pal_file, source_info)
    
    # Create additional palettes for testing
    print("\nCreating additional palette files for testing...")
    for pal_idx in range(8, 16):
        if pal_idx != palette_idx:  # Skip the one we already created
            colors = read_cgram_palette(cgram_file, pal_idx)
            pal_name = f"Palette {pal_idx}"
            test_pal_file = f"{output_prefix}_pal{pal_idx}.pal.json"
            create_palette_json(colors, pal_name, test_pal_file)
    
    print("\n✓ Extraction complete!")
    print(f"\nTo edit: python3 launch_pixel_editor.py {img_file}")
    print("The editor will auto-load the palette files")
    print("Use number keys 0-7 to switch palettes while editing")


if __name__ == "__main__":
    main()