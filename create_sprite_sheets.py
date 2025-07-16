#!/usr/bin/env python3
"""Create sprite sheets with accurate palette mapping from memory dumps."""

import sys
from pathlib import Path
from PIL import Image


def decode_4bpp_tile(tile_data):
    """Decode a 4bpp (16-color) SNES tile to pixel indices."""
    pixels = []
    
    # 4bpp SNES format: 32 bytes per 8x8 tile
    # Each pair of bytes represents one row
    for y in range(8):
        row = []
        # Get the 4 bytes for this row
        b0 = tile_data[y * 2]
        b1 = tile_data[y * 2 + 1]
        b2 = tile_data[y * 2 + 16]
        b3 = tile_data[y * 2 + 17]
        
        # Decode each pixel in the row
        for x in range(8):
            bit = 7 - x
            pixel = 0
            if b0 & (1 << bit): pixel |= 1
            if b1 & (1 << bit): pixel |= 2
            if b2 & (1 << bit): pixel |= 4
            if b3 & (1 << bit): pixel |= 8
            row.append(pixel)
        pixels.append(row)
    
    return pixels


def read_cgram_palettes(cgram_file):
    """Read 16 palettes from CGRAM dump."""
    with open(cgram_file, 'rb') as f:
        cgram_data = f.read()
    
    palettes = []
    for pal_idx in range(16):
        palette = []
        for color_idx in range(16):
            offset = (pal_idx * 16 + color_idx) * 2
            if offset + 1 < len(cgram_data):
                color_low = cgram_data[offset]
                color_high = cgram_data[offset + 1]
                snes_color = (color_high << 8) | color_low
                
                # Convert BGR555 to RGB888
                b = ((snes_color >> 10) & 0x1F) * 8
                g = ((snes_color >> 5) & 0x1F) * 8
                r = (snes_color & 0x1F) * 8
                
                palette.append((r, g, b))
            else:
                palette.append((0, 0, 0))
        palettes.append(palette)
    
    return palettes


def parse_oam_data(oam_file):
    """Parse OAM data to find active sprites and their palettes."""
    with open(oam_file, 'rb') as f:
        oam_data = f.read()
    
    sprites = []
    
    # Parse main OAM table (first 512 bytes)
    for i in range(0, 512, 4):
        x_low = oam_data[i]
        y_pos = oam_data[i + 1]
        tile_low = oam_data[i + 2]
        attrs = oam_data[i + 3]
        
        # Extract attributes
        palette = attrs & 0x07  # Lower 3 bits
        priority = (attrs >> 4) & 0x03
        h_flip = attrs & 0x40
        v_flip = attrs & 0x80
        
        # Get high bits from extended OAM table
        sprite_num = i // 4
        high_byte_idx = 512 + (sprite_num // 4)
        high_bit_pos = (sprite_num % 4) * 2
        
        high_byte = oam_data[high_byte_idx]
        size_bit = (high_byte >> high_bit_pos) & 1
        x_high = (high_byte >> (high_bit_pos + 1)) & 1
        
        x_full = x_low | (x_high << 8)
        
        # Map OAM palette to CGRAM palette
        cgram_palette = palette + 8
        
        # Check if sprite is active (on-screen)
        if y_pos < 0xE0:  # Y < 224 means on-screen
            sprites.append({
                "index": sprite_num,
                "x": x_full,
                "y": y_pos,
                "tile_num": tile_low,
                "palette": cgram_palette,
                "priority": priority,
                "h_flip": bool(h_flip),
                "v_flip": bool(v_flip),
                "large": bool(size_bit)
            })
    
    return sprites


def extract_tile(vram_data, tile_num, base_offset=0xC000):
    """Extract a single 8x8 tile from VRAM."""
    # Each tile is 32 bytes
    offset = base_offset + (tile_num * 32)
    
    if offset + 32 > len(vram_data):
        raise ValueError(f"Tile {tile_num} out of range")
    
    return vram_data[offset:offset + 32]


def create_sprite_sheet(vram_data, palettes, sprites, pal_idx, output_prefix):
    """Create a sprite sheet for a specific palette."""
    # Get sprites using this palette
    pal_sprites = [s for s in sprites if s["palette"] == pal_idx]
    if not pal_sprites:
        return
    
    # Get unique tiles
    unique_tiles = sorted(set(s["tile_num"] for s in pal_sprites))
    
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
            pixels = decode_4bpp_tile(tile_data)
            
            # Create indexed tile
            for py in range(8):
                for px in range(8):
                    sheet.putpixel((x + px, y + py), pixels[py][px])
                    
        except Exception as e:
            print(f"  Warning: Could not extract tile {tile_num}: {e}")
    
    # Save sheet
    output_file = f"{output_prefix}_palette_{pal_idx}.png"
    sheet.save(output_file)
    print(f"Created: {output_file} ({len(unique_tiles)} tiles)")
    
    # Also save 4x scaled version
    sheet_4x = sheet.resize((sheet_width * 4, sheet_height * 4), Image.NEAREST)
    output_4x = f"{output_prefix}_palette_{pal_idx}_4x.png"
    sheet_4x.save(output_4x)
    print(f"Created: {output_4x}")


def main():
    # Check for command line argument or use defaults
    if len(sys.argv) > 1:
        prefix = sys.argv[1]
        vram_file = f"{prefix}_VRAM.dmp"
        cgram_file = f"{prefix}_CGRAM.dmp"
        oam_file = f"{prefix}_OAM.dmp"
    else:
        # Try different dump sets in order of preference
        if Path("Cave.SnesVideoRam.dmp").exists():
            prefix = "cave_sprites"
            vram_file = "Cave.SnesVideoRam.dmp"
            cgram_file = "Cave.SnesCgRam.dmp"
            oam_file = "Cave.SnesSpriteRam.dmp"
        elif Path("Kirby Super Star (USA)_2_VRAM.dmp").exists():
            prefix = "kirby_sprites"
            vram_file = "Kirby Super Star (USA)_2_VRAM.dmp"
            cgram_file = "Kirby Super Star (USA)_2_CGRAM.dmp"
            oam_file = "Kirby Super Star (USA)_2_OAM.dmp"
        else:
            print("Error: No memory dumps found!")
            print("Expected: Cave.*.dmp or Kirby Super Star (USA)_2_*.dmp")
            print("\nUsage: python3 create_sprite_sheets.py [prefix]")
            return
    
    print(f"Using dump files: {prefix}")
    print(f"  VRAM: {vram_file}")
    print(f"  CGRAM: {cgram_file}")
    print(f"  OAM: {oam_file}")
    
    # Read data
    try:
        with open(vram_file, "rb") as f:
            vram_data = f.read()
        print(f"Loaded VRAM: {len(vram_data)} bytes")
        
        palettes = read_cgram_palettes(cgram_file)
        print(f"Loaded {len(palettes)} palettes")
        
        sprites = parse_oam_data(oam_file)
        print(f"Found {len(sprites)} active sprites")
        
    except FileNotFoundError as e:
        print(f"Error: {e}")
        return
    
    # Analyze palette usage
    sprites_by_palette = {}
    for sprite in sprites:
        pal = sprite["palette"]
        if pal not in sprites_by_palette:
            sprites_by_palette[pal] = []
        sprites_by_palette[pal].append(sprite)
    
    print("\nPalette usage:")
    for pal, spr_list in sorted(sprites_by_palette.items()):
        print(f"  Palette {pal}: {len(spr_list)} sprites")
        # Show first few tile numbers
        tiles = sorted(set(s["tile_num"] for s in spr_list))[:10]
        tiles_str = ", ".join(str(t) for t in tiles)
        if len(tiles) < len(set(s["tile_num"] for s in spr_list)):
            tiles_str += "..."
        print(f"    Tiles: {tiles_str}")
    
    print("\nCreating sprite sheets...")
    
    # Create sheets for sprite palettes (8-15)
    for pal_idx in range(8, 16):
        if pal_idx in sprites_by_palette:
            create_sprite_sheet(vram_data, palettes, sprites, pal_idx, prefix)
    
    print("\n✓ Sprite sheet creation complete!")


if __name__ == "__main__":
    main()