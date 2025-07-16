#!/usr/bin/env python3
"""Extract and visualize palettes from CGRAM dump."""

import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

def read_cgram(cgram_file):
    """Read CGRAM dump and convert to RGB palettes."""
    with open(cgram_file, 'rb') as f:
        cgram_data = f.read()
    
    if len(cgram_data) != 512:
        print(f"Warning: CGRAM should be 512 bytes, got {len(cgram_data)}")
    
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

def create_palette_sheet(palettes, output_file):
    """Create a visual palette reference sheet."""
    # Settings
    swatch_size = 32
    padding = 4
    label_height = 20
    
    # Calculate image size
    img_width = (swatch_size * 16) + (padding * 17)
    img_height = (swatch_size + label_height) * 16 + padding * 17
    
    # Create image
    img = Image.new('RGB', (img_width, img_height), (64, 64, 64))
    draw = ImageDraw.Draw(img)
    
    # Draw palettes
    for pal_idx, palette in enumerate(palettes):
        y_base = pal_idx * (swatch_size + label_height + padding) + padding
        
        # Draw palette label
        label = f"Palette {pal_idx}"
        if pal_idx >= 8:
            label += f" (OAM {pal_idx - 8})"
        draw.text((padding, y_base), label, fill=(255, 255, 255))
        
        # Draw color swatches
        for color_idx, color in enumerate(palette):
            x = color_idx * (swatch_size + padding) + padding
            y = y_base + label_height
            
            # Draw swatch
            draw.rectangle([x, y, x + swatch_size, y + swatch_size], fill=color)
            
            # Draw color index
            text_color = (255, 255, 255) if sum(color) < 384 else (0, 0, 0)
            draw.text((x + 2, y + 2), str(color_idx), fill=text_color)
    
    img.save(output_file)
    print(f"Created palette sheet: {output_file}")

def create_indexed_palette_image(palettes, pal_idx, output_file):
    """Create an indexed color palette file for a specific palette."""
    if pal_idx >= len(palettes):
        print(f"Error: Palette {pal_idx} not found")
        return
    
    # Create a small indexed image with the palette
    img = Image.new('P', (16, 1))
    
    # Set the palette
    palette_data = []
    for color in palettes[pal_idx]:
        palette_data.extend(color)
    
    # Pad to 256 colors (PIL requirement)
    while len(palette_data) < 768:
        palette_data.extend([0, 0, 0])
    
    img.putpalette(palette_data)
    
    # Set each pixel to its color index
    for i in range(16):
        img.putpixel((i, 0), i)
    
    img.save(output_file)
    print(f"Created indexed palette file: {output_file}")

def main():
    # Use Cave CGRAM dump
    cgram_file = "Cave.SnesCgRam.dmp"
    
    if not Path(cgram_file).exists():
        print(f"Error: {cgram_file} not found")
        return
    
    # Read palettes
    palettes = read_cgram(cgram_file)
    
    # Create visual palette sheet
    create_palette_sheet(palettes, "cave_palettes_reference.png")
    
    # Create indexed palette files for sprite palettes (8-15)
    for oam_pal in range(8):
        cgram_pal = oam_pal + 8
        create_indexed_palette_image(palettes, cgram_pal, f"cave_palette_{cgram_pal}_indexed.png")
    
    # Show which palettes are used according to OAM
    print("\nPalettes used in Cave area (from OAM analysis):")
    print("  OAM Palette 0 → CGRAM Palette 8 (Kirby)")
    print("  OAM Palette 4 → CGRAM Palette 12 (UI elements)")
    print("  OAM Palette 6 → CGRAM Palette 14 (Cave enemies)")

if __name__ == "__main__":
    main()