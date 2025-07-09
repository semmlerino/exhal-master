#!/usr/bin/env python3
"""
Analyze and compare the colors in different palette files
"""

import json
import os


def analyze_palette(palette_file):
    """Analyze colors in a palette file"""
    with open(palette_file) as f:
        data = json.load(f)

    colors = data["palette"]["colors"]
    name = data["palette"]["name"]

    print(f"\nb[1m{name}b[0m ({palette_file})")
    print("-" * 60)

    # Analyze each color
    for i, (r, g, b) in enumerate(colors):
        # Determine color type
        color_desc = ""

        if r == 0 and g == 0 and b == 0:
            color_desc = "BLACK/TRANSPARENT"
        elif r > 240 and g > 240 and b > 240:
            color_desc = "WHITE"
        elif r > 200 and g < 150 and b > 150:
            color_desc = "b[35mPINK/PURPLEb[0m"  # Magenta color
        elif r > 200 and g < 100 and b < 100:
            color_desc = "b[31mREDb[0m"  # Red color
        elif r > 200 and g > 150 and b < 100:
            color_desc = "b[33mORANGE/YELLOWb[0m"  # Yellow color
        elif r < 100 and g > 150 and b < 100:
            color_desc = "b[32mGREENb[0m"  # Green color
        elif r < 100 and g < 150 and b > 150:
            color_desc = "b[34mBLUEb[0m"  # Blue color
        elif r > 200 and 100 < g < 200 and 100 < b < 200:
            color_desc = "b[35mLIGHT PINKb[0m"  # Light pink

        print(f"  Color {i:2d}: RGB({r:3d}, {g:3d}, {b:3d}) {color_desc}")

    # Summary
    pink_count = sum(1 for r, g, b in colors if r > 200 and g < 200 and b > 150)
    red_count = sum(1 for r, g, b in colors if r > 200 and g < 100 and b < 100)

    print(f"\n  Summary: {pink_count} pink/purple colors, {red_count} red colors")

    return colors

def main():
    print("🎨 Palette Color Analysis")
    print("=" * 60)

    palette_files = [
        "kirby_sprites_grayscale_ultrathink.pal.json",  # Original
        "kirby_palette_14.pal.json",  # Fixed palette 14
        "kirby_smart_palette_11.pal.json"  # Smart selection
    ]

    all_palettes = {}

    for pf in palette_files:
        if os.path.exists(pf):
            colors = analyze_palette(pf)
            all_palettes[pf] = colors
        else:
            print(f"\n⚠️  {pf} not found")

    # Compare if multiple palettes loaded
    if len(all_palettes) > 1:
        print("\n" + "=" * 60)
        print("🔍 Color Differences:")

        files = list(all_palettes.keys())
        if "kirby_sprites_grayscale_ultrathink.pal.json" in files and \
           "kirby_palette_14.pal.json" in files:

            orig = all_palettes["kirby_sprites_grayscale_ultrathink.pal.json"]
            fixed = all_palettes["kirby_palette_14.pal.json"]

            different = False
            for i, (c1, c2) in enumerate(zip(orig, fixed)):
                if c1 != c2:
                    different = True
                    print(f"  Index {i}: {c1} → {c2}")

            if not different:
                print("  ✅ Palettes are identical")

    print("\n✨ Analysis complete!")

if __name__ == "__main__":
    main()
