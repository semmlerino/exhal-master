#!/usr/bin/env python3
"""Create character sheets with proper palette mapping from memory dumps."""

import sys
from pathlib import Path
from PIL import Image

# Import the original functions
from create_character_sheet import (
    convert_4bpp_to_pixels, read_cgram_palettes, parse_oam_data,
    extract_tile, apply_palette_to_tile
)

def main():
    # Check for command line argument or use defaults
    if len(sys.argv) > 1:
        prefix = sys.argv[1]
    else:
        # Try different dump sets in order of preference
        if Path("Cave.SnesVideoRam.dmp").exists():
            prefix = "Cave"
            vram_file = "Cave.SnesVideoRam.dmp"
            cgram_file = "Cave.SnesCgRam.dmp"
            oam_file = "Cave.SnesSpriteRam.dmp"
        elif Path("Kirby Super Star (USA)_2_VRAM.dmp").exists():
            prefix = "Kirby Super Star (USA)_2"
            vram_file = "Kirby Super Star (USA)_2_VRAM.dmp"
            cgram_file = "Kirby Super Star (USA)_2_CGRAM.dmp"
            oam_file = "Kirby Super Star (USA)_2_OAM.dmp"
        else:
            print("Error: No memory dumps found!")
            print("Expected: Cave.*.dmp or Kirby Super Star (USA)_2_*.dmp")
            return
    
    print(f"Using dump set: {prefix}")
    
    # Read VRAM data
    with open(vram_file, "rb") as f:
        vram_data = f.read()
    
    # Read palettes
    palettes = read_cgram_palettes(cgram_file)
    
    # Parse OAM data
    try:
        oam_sprites = parse_oam_data(oam_file)
        print(f"Found {len(oam_sprites)} active sprites in OAM")
    except FileNotFoundError:
        print(f"Error: {oam_file} not found")
        return
    
    # Group sprites by palette
    sprites_by_palette = {}
    for sprite in oam_sprites:
        pal = sprite["palette"]
        if pal not in sprites_by_palette:
            sprites_by_palette[pal] = []
        sprites_by_palette[pal].append(sprite)
    
    # Report palette usage
    print("\nPalette usage:")
    for pal, sprites in sorted(sprites_by_palette.items()):
        print(f"  Palette {pal}: {len(sprites)} sprites")
        # Show first few tile numbers
        tiles = sorted(set(s["tile_num"] for s in sprites))[:10]
        print(f"    Tiles: {tiles}")
    
    # Create character sheets for each palette
    for pal_idx in sorted(sprites_by_palette.keys()):
        if pal_idx < 8:  # Skip background palettes
            continue
            
        sprites = sprites_by_palette[pal_idx]
        if not sprites:
            continue
            
        # Get unique tiles
        unique_tiles = sorted(set(s["tile_num"] for s in sprites))
        
        # Create sheet
        tiles_per_row = min(16, len(unique_tiles))
        rows = (len(unique_tiles) + tiles_per_row - 1) // tiles_per_row
        
        sheet_width = tiles_per_row * 8
        sheet_height = rows * 8
        
        sheet = Image.new('P', (sheet_width, sheet_height))
        
        # Set palette
        palette_data = []
        for color in palettes[pal_idx]:
            palette_data.extend(color)
        while len(palette_data) < 768:
            palette_data.extend([0, 0, 0])
        sheet.putpalette(palette_data)
        
        # Place tiles
        for i, tile_num in enumerate(unique_tiles):
            x = (i % tiles_per_row) * 8
            y = (i // tiles_per_row) * 8
            
            try:
                tile_data = extract_tile(vram_data, tile_num)
                pixels = convert_4bpp_to_pixels(tile_data)
                colored_tile = apply_palette_to_tile(pixels, palettes[pal_idx])
                
                # Convert to indexed mode for pasting
                indexed_tile = Image.new('P', (8, 8))
                indexed_tile.putpalette(palette_data)
                for py in range(8):
                    for px in range(8):
                        indexed_tile.putpixel((px, py), pixels[py][px])
                
                sheet.paste(indexed_tile, (x, y))
            except Exception as e:
                print(f"Error extracting tile {tile_num}: {e}")
        
        # Save sheet
        output_file = f"{prefix}_character_sheet_palette_{pal_idx}.png"
        sheet.save(output_file)
        print(f"\nSaved: {output_file} ({len(unique_tiles)} tiles)")
        
        # Also save a 4x scaled version
        sheet_4x = sheet.resize((sheet_width * 4, sheet_height * 4), Image.NEAREST)
        output_4x = f"{prefix}_character_sheet_palette_{pal_idx}_4x.png"
        sheet_4x.save(output_4x)
        print(f"Saved: {output_4x}")

if __name__ == "__main__":
    main()