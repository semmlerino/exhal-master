#!/usr/bin/env python3
"""Prepare sprites for editing in indexed color mode with specific palettes."""

import sys
from pathlib import Path
from PIL import Image
import numpy as np

def read_cgram_palette(cgram_file, palette_idx):
    """Read a specific palette from CGRAM dump."""
    with open(cgram_file, 'rb') as f:
        cgram_data = f.read()
    
    palette = []
    for color_idx in range(16):
        offset = (palette_idx * 16 + color_idx) * 2
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
    
    return palette

def apply_palette_to_grayscale(grayscale_file, palette, output_file):
    """Apply a palette to a grayscale sprite sheet."""
    # Load grayscale image
    img = Image.open(grayscale_file)
    
    if img.mode != 'P':
        print(f"Converting {img.mode} image to indexed color mode...")
        img = img.convert('P')
    
    # Create palette data for PIL
    palette_data = []
    for color in palette:
        palette_data.extend(color)
    
    # Pad to 256 colors
    while len(palette_data) < 768:
        palette_data.extend([0, 0, 0])
    
    # Apply palette
    img.putpalette(palette_data)
    
    # Save with palette
    img.save(output_file)
    print(f"Created indexed sprite sheet: {output_file}")
    return img

def extract_single_sprite(sprite_sheet, tile_idx, tiles_per_row=16):
    """Extract a single 8x8 sprite from the sheet."""
    tile_x = (tile_idx % tiles_per_row) * 8
    tile_y = (tile_idx // tiles_per_row) * 8
    
    sprite = sprite_sheet.crop((tile_x, tile_y, tile_x + 8, tile_y + 8))
    return sprite

def create_editing_template(grayscale_file, cgram_file, palette_idx, sprite_tiles, output_prefix):
    """Create an editing template with specific sprites and palette."""
    # Read palette
    palette = read_cgram_palette(cgram_file, palette_idx)
    
    # Load grayscale sprites
    grayscale_img = Image.open(grayscale_file)
    if grayscale_img.mode != 'P':
        grayscale_img = grayscale_img.convert('P')
    
    # Create a template with selected sprites
    template_width = len(sprite_tiles) * 8 * 4  # 4x scale
    template_height = 8 * 4  # 4x scale
    
    template = Image.new('P', (template_width, template_height))
    template.putpalette(grayscale_img.getpalette())
    
    # Extract and place sprites
    for i, tile_idx in enumerate(sprite_tiles):
        sprite = extract_single_sprite(grayscale_img, tile_idx)
        sprite = sprite.resize((32, 32), Image.NEAREST)  # 4x scale
        template.paste(sprite, (i * 32, 0))
    
    # Apply palette
    palette_data = []
    for color in palette:
        palette_data.extend(color)
    while len(palette_data) < 768:
        palette_data.extend([0, 0, 0])
    template.putpalette(palette_data)
    
    # Save template
    template_file = f"{output_prefix}_tiles_{'_'.join(map(str, sprite_tiles))}_pal{palette_idx}.png"
    template.save(template_file)
    print(f"Created editing template: {template_file}")
    
    # Also save a reference with grid
    grid_img = template.convert('RGB')
    from PIL import ImageDraw
    draw = ImageDraw.Draw(grid_img)
    
    # Draw grid
    for i in range(len(sprite_tiles) + 1):
        x = i * 32
        draw.line([(x, 0), (x, 32)], fill=(128, 128, 128))
    draw.line([(0, 0), (template_width, 0)], fill=(128, 128, 128))
    draw.line([(0, 32), (template_width, 32)], fill=(128, 128, 128))
    
    grid_file = f"{output_prefix}_tiles_{'_'.join(map(str, sprite_tiles))}_pal{palette_idx}_grid.png"
    grid_img.save(grid_file)
    print(f"Created grid reference: {grid_file}")

def main():
    # Files
    grayscale_file = "cave_sprites_grayscale.png"
    cgram_file = "Cave.SnesCgRam.dmp"
    
    print("Sprite Editing Preparation Tool")
    print("==============================")
    
    # Create indexed versions with different palettes
    print("\nCreating indexed sprite sheets with game palettes...")
    
    # Kirby palette (OAM 0 = CGRAM 8)
    palette = read_cgram_palette(cgram_file, 8)
    apply_palette_to_grayscale(grayscale_file, palette, "cave_sprites_kirby_pal8.png")
    
    # UI palette (OAM 4 = CGRAM 12)
    palette = read_cgram_palette(cgram_file, 12)
    apply_palette_to_grayscale(grayscale_file, palette, "cave_sprites_ui_pal12.png")
    
    # Enemy palette (OAM 6 = CGRAM 14)
    palette = read_cgram_palette(cgram_file, 14)
    apply_palette_to_grayscale(grayscale_file, palette, "cave_sprites_enemy_pal14.png")
    
    # Create editing templates for common sprites
    print("\nCreating editing templates...")
    
    # Kirby sprites (tiles 0-19 based on OAM)
    create_editing_template(grayscale_file, cgram_file, 8, [0, 2, 3, 4, 18, 19], "kirby_edit")
    
    # UI elements (tiles 32-51 based on OAM)
    create_editing_template(grayscale_file, cgram_file, 12, [32, 34, 35, 36, 50, 51], "ui_edit")
    
    print("\n✓ Sprite editing preparation complete!")
    print("\nFiles created:")
    print("- cave_sprites_grayscale.png - Original grayscale sprites")
    print("- cave_sprites_kirby_pal8.png - Sprites with Kirby palette")
    print("- cave_sprites_ui_pal12.png - Sprites with UI palette")
    print("- cave_sprites_enemy_pal14.png - Sprites with enemy palette")
    print("- kirby_edit_*.png - Kirby sprite editing templates")
    print("- ui_edit_*.png - UI element editing templates")
    print("\nEditing workflow:")
    print("1. Open any indexed PNG in your image editor")
    print("2. Edit pixels using only the 16 colors in the palette")
    print("3. Save as indexed PNG to preserve palette")
    print("4. Use sprite_injector.py to reinsert edited sprites")

if __name__ == "__main__":
    main()