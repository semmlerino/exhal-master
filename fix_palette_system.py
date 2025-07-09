#!/usr/bin/env python3
"""
Fix the palette system to correctly identify and apply Kirby's palettes
Based on analysis of OAM data and actual sprite usage
"""

import json
import os

import numpy as np
from PIL import Image

from sprite_edit_helpers import parse_cgram


def parse_oam_correctly(oam_data):
    """Parse OAM data with correct bit extraction"""
    sprites = []

    # Parse main OAM table (512 bytes, 128 sprites)
    for i in range(0, 512, 4):
        x = oam_data[i]
        y = oam_data[i + 1]
        tile = oam_data[i + 2]
        attrs = oam_data[i + 3]

        # CORRECT palette extraction - lower 3 bits
        palette = attrs & 0x07  # This gives OAM palette 0-7
        cgram_palette = palette + 8  # Maps to CGRAM palette 8-15

        # Skip off-screen sprites
        if y < 240:
            sprites.append({
                "x": x,
                "y": y,
                "tile": tile,
                "oam_palette": palette,
                "cgram_palette": cgram_palette,
                "priority": (attrs >> 4) & 0x03,
                "h_flip": bool(attrs & 0x40),
                "v_flip": bool(attrs & 0x80)
            })

    return sprites

def analyze_palette_usage(oam_file, vram_offset=0xC000):
    """Analyze which palettes are actually used by sprites"""
    with open(oam_file, "rb") as f:
        oam_data = f.read()

    sprites = parse_oam_correctly(oam_data)

    # Count palette usage
    palette_usage = {}
    tile_to_palette = {}

    for sprite in sprites:
        pal = sprite["cgram_palette"]
        tile = sprite["tile"]

        palette_usage[pal] = palette_usage.get(pal, 0) + 1

        if tile not in tile_to_palette:
            tile_to_palette[tile] = []
        tile_to_palette[tile].append(pal)

    return palette_usage, tile_to_palette, sprites

def find_best_kirby_palette(cgram_file, oam_file=None):
    """Find the best palette for Kirby based on color analysis and usage"""
    palettes = parse_cgram(cgram_file)

    # If we have OAM data, analyze actual usage
    if oam_file and os.path.exists(oam_file):
        palette_usage, tile_to_palette, sprites = analyze_palette_usage(oam_file)
        print(f"Palette usage from OAM: {palette_usage}")
    else:
        palette_usage = {}

    # Analyze each sprite palette (8-15) for Kirby characteristics
    palette_scores = {}

    for pal_idx in range(8, 16):
        score = 0
        colors = palettes[pal_idx]

        # Check for black/transparent first color
        if sum(colors[0]) < 50:
            score += 10

        # Count pink/red colors (Kirby's main colors)
        pink_count = 0
        for r, g, b in colors[:8]:  # Check first 8 colors
            # Pink: high red, medium green, high blue
            if 200 < r < 255 and 100 < g < 230 and 150 < b < 255:
                pink_count += 1
                score += 5
            # Red (for feet): high red, low green/blue
            elif r > 200 and g < 100 and b < 100:
                score += 3

        # Check for white (eyes)
        for r, g, b in colors:
            if r > 240 and g > 240 and b > 240:
                score += 2
                break

        # Bonus for actual usage
        if pal_idx in palette_usage:
            score += palette_usage[pal_idx] * 2

        palette_scores[pal_idx] = score

        print(f"Palette {pal_idx}: Score={score}, Pink colors={pink_count}, Usage={palette_usage.get(pal_idx, 0)}")

    # Find best palette
    best_palette = max(palette_scores, key=palette_scores.get)

    return best_palette, palette_scores

def create_smart_palette_file(cgram_file, oam_file, output_file, force_palette=None):
    """Create a palette file using smart selection based on actual sprite data"""

    if force_palette is None:
        best_palette, scores = find_best_kirby_palette(cgram_file, oam_file)
        print(f"\nBest palette selected: {best_palette} (score: {scores[best_palette]})")
    else:
        best_palette = force_palette
        print(f"\nUsing forced palette: {best_palette}")

    palettes = parse_cgram(cgram_file)
    palette_colors = palettes[best_palette]

    # Create palette file
    palette_data = {
        "format_version": "1.0",
        "format_description": "Indexed Pixel Editor Palette File",
        "source": {
            "cgram_file": os.path.abspath(cgram_file),
            "oam_file": os.path.abspath(oam_file) if oam_file else None,
            "palette_index": best_palette,
            "extraction_tool": "fix_palette_system.py",
            "selection_method": "smart_oam_analysis"
        },
        "palette": {
            "name": f"Smart Kirby Palette {best_palette}",
            "colors": [list(color) for color in palette_colors],
            "color_count": 16,
            "format": "RGB888"
        },
        "usage_hints": {
            "transparent_index": 0,
            "typical_use": "sprite",
            "kirby_palette": True,
            "confidence": "high" if oam_file else "medium"
        },
        "editor_compatibility": {
            "indexed_pixel_editor": True,
            "supports_grayscale_mode": True,
            "auto_loadable": True
        }
    }

    with open(output_file, "w") as f:
        json.dump(palette_data, f, indent=2)

    print(f"Created smart palette file: {output_file}")
    return best_palette

def test_palette_on_sprites(png_file, cgram_file, output_prefix="test_palette"):
    """Test different palettes on a grayscale sprite sheet"""
    # Load grayscale image
    img = Image.open(png_file)
    if img.mode != "P":
        print(f"Error: {png_file} is not indexed mode")
        return

    # Get image data
    img_array = np.array(img)

    # Load all palettes
    palettes = parse_cgram(cgram_file)

    # Test each sprite palette
    for pal_idx in range(8, 16):
        # Create a copy of the image
        test_img = Image.fromarray(img_array, mode="P")

        # Apply palette
        palette_data = []
        for color in palettes[pal_idx]:
            palette_data.extend(color)
        # Pad to 256 colors
        while len(palette_data) < 768:
            palette_data.extend([0, 0, 0])

        test_img.putpalette(palette_data)

        # Save result
        output_file = f"{output_prefix}_palette_{pal_idx}.png"
        test_img.save(output_file)
        print(f"Saved: {output_file}")

def main():
    """Fix palette issues in existing sprite sheets"""

    print("🔧 Fixing Palette System")
    print("=" * 60)

    # Files to work with
    cgram_file = "Cave.SnesCgRam.dmp"
    oam_file = "Cave.SnesSpriteRam.dmp"

    if not os.path.exists(cgram_file):
        print(f"Error: {cgram_file} not found")
        return

    # Analyze palette usage
    print("\n1. Analyzing OAM palette usage...")
    if os.path.exists(oam_file):
        palette_usage, tile_to_palette, sprites = analyze_palette_usage(oam_file)
        print(f"Found {len(sprites)} active sprites")
        print("Palette usage (CGRAM indices):")
        for pal, count in sorted(palette_usage.items()):
            print(f"  Palette {pal}: {count} sprites")

    # Find best Kirby palette
    print("\n2. Finding best Kirby palette...")
    best_palette, scores = find_best_kirby_palette(cgram_file, oam_file if os.path.exists(oam_file) else None)

    # Create smart palette files
    print("\n3. Creating smart palette files...")

    # Create the optimal palette
    create_smart_palette_file(cgram_file, oam_file,
                            f"kirby_smart_palette_{best_palette}.pal.json")

    # Also create palette 14 which often has good Kirby colors
    if best_palette != 14:
        create_smart_palette_file(cgram_file, oam_file,
                                "kirby_palette_14.pal.json",
                                force_palette=14)

    # Test on existing sprite sheets
    print("\n4. Testing palettes on sprite sheets...")
    test_files = ["tiny_test.png", "kirby_focused_test.png"]

    for test_file in test_files:
        if os.path.exists(test_file):
            print(f"\nTesting on {test_file}...")
            test_palette_on_sprites(test_file, cgram_file,
                                  f"fixed_{test_file.replace('.png', '')}")

    print("\n✅ Palette system fixes complete!")
    print(f"Recommended palette: {best_palette}")
    print("\nNext steps:")
    print("1. Load your sprite sheet in the editor")
    print(f"2. Load kirby_smart_palette_{best_palette}.pal.json")
    print("3. Or try kirby_palette_14.pal.json for alternative colors")

if __name__ == "__main__":
    main()
