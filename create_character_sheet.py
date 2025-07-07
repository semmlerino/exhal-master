#!/usr/bin/env python3
"""
Create a character sheet showing different sprites with their correct palettes
Based on OAM data to properly map each sprite to its assigned palette
"""

import struct
from PIL import Image
import os
import sys

# We're using direct OAM parsing instead of the sprite_editor module

def read_cgram_palettes(cgram_file):
    """Read all 16 palettes from CGRAM dump."""
    with open(cgram_file, 'rb') as f:
        cgram_data = f.read()
    
    palettes = []
    for pal_num in range(16):
        palette = []
        for color_num in range(16):
            offset = (pal_num * 16 + color_num) * 2
            if offset < len(cgram_data):
                color_word = struct.unpack_from('<H', cgram_data, offset)[0]
                b = ((color_word >> 10) & 0x1F) << 3
                g = ((color_word >> 5) & 0x1F) << 3
                r = (color_word & 0x1F) << 3
                palette.extend([r, g, b])
            else:
                palette.extend([0, 0, 0])
        palettes.append(palette)
    return palettes

def decode_4bpp_tile(tile_data):
    """Decode a single 4bpp SNES tile (32 bytes) to pixel indices."""
    pixels = []
    
    for row in range(8):
        # Get the 4 bytes for this row
        low1 = tile_data[row * 2]
        high1 = tile_data[row * 2 + 1]
        low2 = tile_data[row * 2 + 16]
        high2 = tile_data[row * 2 + 17]
        
        # Decode 8 pixels for this row
        for bit in range(7, -1, -1):
            pixel = ((low1 >> bit) & 1) | \
                    (((high1 >> bit) & 1) << 1) | \
                    (((low2 >> bit) & 1) << 2) | \
                    (((high2 >> bit) & 1) << 3)
            pixels.append(pixel)
    
    return pixels

def create_tile_image(tile_data, palette):
    """Create an 8x8 image from tile data with palette applied."""
    pixels = decode_4bpp_tile(tile_data)
    
    # Create image
    img = Image.new('P', (8, 8))
    img.putdata(pixels)
    img.putpalette(palette)
    
    # Convert to RGBA to preserve colors when compositing
    return img.convert('RGBA')

def parse_oam_data(oam_file):
    """Parse OAM dump to get sprite information"""
    with open(oam_file, 'rb') as f:
        oam_data = f.read()
    
    sprites = []
    
    # Parse main OAM table (128 entries, 4 bytes each)
    for i in range(128):
        offset = i * 4
        if offset + 4 <= len(oam_data):
            x_pos = oam_data[offset]
            y_pos = oam_data[offset + 1]
            tile_low = oam_data[offset + 2]
            attributes = oam_data[offset + 3]
            
            # Extract attributes
            palette = attributes & 0x07
            priority = (attributes >> 3) & 0x03
            h_flip = (attributes >> 6) & 0x01
            v_flip = (attributes >> 7) & 0x01
            
            # Get size and X position high bit from high table
            high_table_offset = 512 + (i // 4)
            if high_table_offset < len(oam_data):
                high_byte = oam_data[high_table_offset]
                bit_offset = (i % 4) * 2
                size_x_high = (high_byte >> bit_offset) & 0x01
                size_bit = (high_byte >> (bit_offset + 1)) & 0x01
                x_full = x_pos | (size_x_high << 8)
            else:
                x_full = x_pos
                size_bit = 0
            
            # For now, use just the low byte as tile number
            # The high bit depends on PPU register settings
            tile_num = tile_low
            
            # Check if sprite is active (on-screen)
            if y_pos < 0xE0:  # Y < 224 means on-screen
                sprites.append({
                    'index': i,
                    'x': x_full,
                    'y': y_pos,
                    'tile_num': tile_num,
                    'palette': palette,
                    'priority': priority,
                    'h_flip': bool(h_flip),
                    'v_flip': bool(v_flip),
                    'large': bool(size_bit)
                })
    
    return sprites

def main():
    # Read VRAM data
    with open('VRAM.dmp', 'rb') as f:
        vram_data = f.read()
    
    # Read palettes
    palettes = read_cgram_palettes('CGRAM.dmp')
    
    # Parse OAM data
    try:
        oam_sprites = parse_oam_data('OAM.dmp')
        print(f"Found {len(oam_sprites)} active sprites in OAM")
    except FileNotFoundError:
        print("Error: OAM.dmp not found")
        return
    
    # Group sprites by palette
    sprites_by_palette = {}
    for sprite in oam_sprites:
        pal = sprite['palette']
        if pal not in sprites_by_palette:
            sprites_by_palette[pal] = []
        sprites_by_palette[pal].append(sprite)
    
    # Report palette usage
    print("\nPalette usage:")
    for pal, sprites in sorted(sprites_by_palette.items()):
        print(f"  Palette {pal}: {len(sprites)} sprites")
    
    # Create character sheet organized by palette
    tiles_per_row = 16
    tile_size = 8
    
    # Collect unique tiles with their palettes
    unique_tiles = {}  # (tile_num, palette) -> tile_data
    
    for sprite in oam_sprites:
        key = (sprite['tile_num'], sprite['palette'])
        if key not in unique_tiles:
            # Extract tile from VRAM based on tile number
            # SNES sprites use tile numbers that map to VRAM addresses
            # Based on docs: tile $00 is at VRAM $6000 (word addr) = 0xC000 (byte addr)
            # So tile number N is at offset 0xC000 + (N * 32)
            # However, the exact base depends on the sprite configuration register
            
            # For Kirby Super Star, tiles appear to be based at VRAM $6000
            # Tile numbers in OAM are relative to this base
            vram_offset = 0xC000 + sprite['tile_num'] * 32
            
            if vram_offset + 32 <= len(vram_data):
                tile_data = vram_data[vram_offset:vram_offset + 32]
                unique_tiles[key] = tile_data
    
    print(f"\nFound {len(unique_tiles)} unique tile/palette combinations")
    
    # Debug: Show first few tile numbers
    print("\nFirst 10 unique tiles found:")
    for i, (tile_num, pal) in enumerate(list(unique_tiles.keys())[:10]):
        print(f"  Tile ${tile_num:02X} with palette {pal}")
    
    # Calculate sheet dimensions
    total_tiles = len(unique_tiles)
    rows_needed = (total_tiles + tiles_per_row - 1) // tiles_per_row
    
    sheet_width = tiles_per_row * tile_size
    sheet_height = rows_needed * tile_size
    
    # Create character sheet
    sheet = Image.new('RGBA', (sheet_width, sheet_height), (32, 32, 32, 255))
    
    # Place tiles grouped by palette
    tile_idx = 0
    for pal_num in sorted(sprites_by_palette.keys()):
        print(f"\nProcessing palette {pal_num} sprites...")
        
        # Get all unique tiles for this palette
        tiles_for_palette = [(k, v) for k, v in unique_tiles.items() if k[1] == pal_num]
        
        for (tile_num, palette), tile_data in tiles_for_palette:
            if palette < len(palettes):
                # Create tile image with correct palette
                tile_img = create_tile_image(tile_data, palettes[palette])
                
                # Calculate position
                x = (tile_idx % tiles_per_row) * tile_size
                y = (tile_idx // tiles_per_row) * tile_size
                
                # Paste into sheet
                sheet.paste(tile_img, (x, y))
                
                tile_idx += 1
    
    # Save the OAM-based character sheet
    output_file = 'character_sheet_oam_based.png'
    sheet.save(output_file)
    print(f"\nCreated {output_file} - {len(unique_tiles)} unique sprites with their correct palettes")
    
    # Also create separate sheets for each palette
    for pal_num, sprites in sprites_by_palette.items():
        if pal_num < len(palettes):
            # Get unique tiles for this palette
            tiles_for_palette = [(k, v) for k, v in unique_tiles.items() if k[1] == pal_num]
            
            if tiles_for_palette:
                # Create sheet for this palette
                pal_tiles = len(tiles_for_palette)
                pal_rows = (pal_tiles + tiles_per_row - 1) // tiles_per_row
                
                pal_sheet = Image.new('RGBA', 
                                    (tiles_per_row * tile_size, pal_rows * tile_size),
                                    (32, 32, 32, 255))
                
                for idx, ((tile_num, _), tile_data) in enumerate(tiles_for_palette):
                    tile_img = create_tile_image(tile_data, palettes[pal_num])
                    x = (idx % tiles_per_row) * tile_size
                    y = (idx // tiles_per_row) * tile_size
                    pal_sheet.paste(tile_img, (x, y))
                
                pal_sheet.save(f'sprites_palette_{pal_num}_only.png')
                print(f"Created sprites_palette_{pal_num}_only.png - {pal_tiles} tiles")
    
    # Also create a palette reference sheet
    print("\nPalette Reference:")
    print("Palette 0: Kirby (pink/white/red)")
    print("Palette 1-3: Environment/backgrounds") 
    print("Palette 4-8: Enemies and effects")
    print("Palette 9-15: UI and special effects")

if __name__ == "__main__":
    main()