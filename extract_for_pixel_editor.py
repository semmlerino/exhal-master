#!/usr/bin/env python3
"""Extract sprites in grayscale with separate .pal.json files for pixel editor."""

import json
import sys
from pathlib import Path
from PIL import Image


def read_cgram_palette(cgram_file, palette_idx):
    """Read a specific palette from CGRAM dump."""
    with open(cgram_file, 'rb') as f:
        cgram_data = f.read()
    
    colors = []
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
            
            colors.append([r, g, b])
        else:
            colors.append([0, 0, 0])
    
    return colors


def create_palette_json(palette_colors, palette_name, output_file, source_info=None):
    """Create a .pal.json file for the pixel editor."""
    palette_data = {
        "format_version": "1.0",
        "format_description": "Indexed Pixel Editor Palette File",
        "palette": {
            "name": palette_name,
            "colors": palette_colors,
            "color_count": len(palette_colors),
            "format": "RGB888"
        },
        "usage_hints": {
            "transparent_index": 0,
            "typical_use": "sprite",
            "extraction_mode": "grayscale_companion"
        },
        "editor_compatibility": {
            "indexed_pixel_editor": True,
            "supports_grayscale_mode": True,
            "auto_loadable": True
        }
    }
    
    if source_info:
        palette_data["source"] = source_info
    
    with open(output_file, 'w') as f:
        json.dump(palette_data, f, indent=2)
    
    print(f"Created palette file: {output_file}")


def extract_sprites_grayscale(vram_file, output_file, offset=0xC000, size=0x4000, width=16):
    """Extract sprites as grayscale indexed image."""
    # Read VRAM data
    with open(vram_file, 'rb') as f:
        f.seek(offset)
        vram_data = f.read(size)
    
    # Calculate dimensions
    bytes_per_tile = 32  # 4bpp
    num_tiles = len(vram_data) // bytes_per_tile
    tiles_per_row = width
    rows = (num_tiles + tiles_per_row - 1) // tiles_per_row
    
    img_width = tiles_per_row * 8
    img_height = rows * 8
    
    # Create indexed image
    img = Image.new('P', (img_width, img_height))
    
    # Set grayscale palette
    grayscale_palette = []
    for i in range(256):
        gray = (i * 255) // 15 if i < 16 else 0
        grayscale_palette.extend([gray, gray, gray])
    img.putpalette(grayscale_palette)
    
    # Extract tiles
    for tile_idx in range(num_tiles):
        tile_x = (tile_idx % tiles_per_row) * 8
        tile_y = (tile_idx // tiles_per_row) * 8
        
        # Extract 4bpp tile
        tile_offset = tile_idx * 32
        tile_data = vram_data[tile_offset:tile_offset + 32]
        
        # Decode 4bpp to pixels
        for y in range(8):
            for x in range(8):
                # Get pixel from 4bpp data
                byte_offset = y * 2
                bit_offset = 7 - x
                
                pixel = 0
                if tile_data[byte_offset] & (1 << bit_offset):
                    pixel |= 1
                if tile_data[byte_offset + 1] & (1 << bit_offset):
                    pixel |= 2
                if tile_data[byte_offset + 16] & (1 << bit_offset):
                    pixel |= 4
                if tile_data[byte_offset + 17] & (1 << bit_offset):
                    pixel |= 8
                
                img.putpixel((tile_x + x, tile_y + y), pixel)
    
    img.save(output_file)
    print(f"Created grayscale sprites: {output_file}")
    print(f"  Extracted {num_tiles} tiles ({tiles_per_row}x{rows})")
    return num_tiles


def main():
    print("Sprite Extraction for Pixel Editor")
    print("==================================")
    
    # Determine which dumps to use
    if len(sys.argv) > 1:
        prefix = sys.argv[1]
    else:
        # Auto-detect dumps
        if Path("Cave.SnesVideoRam.dmp").exists():
            prefix = "cave"
            vram_file = "Cave.SnesVideoRam.dmp"
            cgram_file = "Cave.SnesCgRam.dmp"
            oam_file = "Cave.SnesSpriteRam.dmp"
        elif Path("Kirby Super Star (USA)_2_VRAM.dmp").exists():
            prefix = "kirby_mss"
            vram_file = "Kirby Super Star (USA)_2_VRAM.dmp"
            cgram_file = "Kirby Super Star (USA)_2_CGRAM.dmp"
            oam_file = "Kirby Super Star (USA)_2_OAM.dmp"
        else:
            print("Error: No memory dumps found!")
            print("Usage: python3 extract_for_pixel_editor.py [prefix]")
            return
    
    print(f"Using dump set: {prefix}")
    
    # Extract grayscale sprites
    output_base = f"{prefix}_sprites_editor"
    grayscale_file = f"{output_base}.png"
    num_tiles = extract_sprites_grayscale(vram_file, grayscale_file)
    
    # Create palette files for sprite palettes (8-15)
    print("\nCreating palette files...")
    
    # Define palette names and their typical usage
    palette_info = {
        8: ("Kirby (Pink)", "Main character palette"),
        9: ("Kirby Alt", "Alternative Kirby palette"),
        10: ("Helper", "Helper character palette"),
        11: ("Enemy 1", "Common enemy palette"),
        12: ("UI/HUD", "User interface elements"),
        13: ("Enemy 2", "Special enemy palette"),
        14: ("Boss/Enemy", "Boss and large enemy palette"),
        15: ("Effects", "Special effects palette")
    }
    
    # Create the main paired palette file (for auto-loading)
    default_palette_idx = 8  # Kirby palette as default
    palette_colors = read_cgram_palette(cgram_file, default_palette_idx)
    palette_name, description = palette_info[default_palette_idx]
    
    # Create main .pal.json file with same base name as image
    main_pal_file = f"{output_base}.pal.json"
    source_info = {
        "cgram_file": cgram_file,
        "palette_index": default_palette_idx,
        "extraction_tool": "extract_for_pixel_editor.py",
        "companion_image": grayscale_file,
        "description": description
    }
    create_palette_json(palette_colors, palette_name, main_pal_file, source_info)
    
    # Create individual palette files
    for pal_idx in range(8, 16):
        palette_colors = read_cgram_palette(cgram_file, pal_idx)
        palette_name, description = palette_info.get(pal_idx, (f"Palette {pal_idx}", "Sprite palette"))
        
        # Create .pal.json file
        pal_file = f"{output_base}_pal{pal_idx}.pal.json"
        
        source_info = {
            "cgram_file": cgram_file,
            "palette_index": pal_idx,
            "extraction_tool": "extract_for_pixel_editor.py",
            "companion_image": grayscale_file,
            "description": description
        }
        
        create_palette_json(palette_colors, palette_name, pal_file, source_info)
    
    # Create metadata file for palette switching
    print("\nCreating metadata file...")
    metadata = {
        "format_version": "1.0",
        "description": f"{prefix.title()} area sprite palettes for Kirby Super Star",
        "palettes": {},
        "default_palette": 8,
        "palette_info": {}
    }
    
    for pal_idx in range(8, 16):
        metadata["palettes"][str(pal_idx)] = f"{output_base}_pal{pal_idx}.pal.json"
        metadata["palette_info"][str(pal_idx)] = palette_info.get(pal_idx, (f"Palette {pal_idx}", "Sprite palette"))[1]
    
    metadata_file = f"{output_base}.metadata.json"
    with open(metadata_file, 'w') as f:
        json.dump(metadata, f, indent=2)
    print(f"Created metadata file: {metadata_file}")
    
    print("\n✓ Extraction complete!")
    print("\nTo edit interactively:")
    print(f"  python3 launch_pixel_editor.py {grayscale_file}")
    print("\nThe pixel editor will automatically load matching .pal.json files")
    print("Use number keys 0-7 to switch between palettes while editing")
    
    # Also create a convenience script
    launcher_file = f"edit_{prefix}_sprites.py"
    with open(launcher_file, 'w') as f:
        f.write(f'''#!/usr/bin/env python3
"""Launch pixel editor with {prefix} sprites and palettes."""
import subprocess
import sys

# Launch the pixel editor with the grayscale sprites
# It will auto-detect the .pal.json files
subprocess.run([
    sys.executable,
    "launch_pixel_editor.py",
    "{grayscale_file}"
])
''')
    
    import os
    os.chmod(launcher_file, 0o755)
    print(f"\nCreated launcher script: {launcher_file}")
    print(f"Run it with: python3 {launcher_file}")


if __name__ == "__main__":
    main()