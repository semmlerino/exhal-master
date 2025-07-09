#!/usr/bin/env python3
"""Analyze CGRAM palettes to find the correct Kirby palette"""

from sprite_edit_helpers import parse_cgram


def analyze_palettes(cgram_file):
    """Analyze all palettes in CGRAM to find Kirby-like colors"""
    palettes = parse_cgram(cgram_file)

    print(f"Analyzing palettes in: {cgram_file}")
    print("=" * 60)

    # Expected Kirby palette characteristics:
    # - First color is usually black (0,0,0) or very dark
    # - Contains multiple pink shades
    # - Has white for eyes

    for pal_idx in range(16):
        palette = palettes[pal_idx]

        # Analyze palette characteristics
        first_color = palette[0]
        has_black = sum(first_color) < 50

        # Count color types
        pink_count = 0
        has_white = False
        has_red = False

        for i, (r, g, b) in enumerate(palette[:16]):
            # Check for pink (high red, lower green, high blue)
            if r > 200 and 100 < g < 230 and b > 150:
                pink_count += 1

            # Check for white
            if r > 240 and g > 240 and b > 240:
                has_white = True

            # Check for red (feet color)
            if r > 200 and g < 100 and b < 100:
                has_red = True

        # Print analysis
        if pal_idx >= 8 or pink_count > 2:  # Focus on sprite palettes or pink palettes
            print(f'\nPalette {pal_idx} {"(Sprite)" if pal_idx >= 8 else "(BG)"}:')
            print(f'  First color: RGB{first_color} {"[BLACK/TRANSPARENT]" if has_black else ""}')
            print(f"  Pink colors: {pink_count}")
            print(f"  Has white: {has_white}")
            print(f"  Has red: {has_red}")

            if pink_count >= 3 or (has_black and pink_count >= 2):
                print("  *** POSSIBLE KIRBY PALETTE ***")

            print("  First 6 colors:")
            for i in range(6):
                r, g, b = palette[i]
                print(f"    {i}: RGB({r:3}, {g:3}, {b:3})")

def compare_with_reference():
    """Compare CGRAM palettes with the reference Kirby palette"""
    import json

    # Load reference palette
    with open("kirby_reference.pal.json") as f:
        ref_data = json.load(f)
    ref_colors = ref_data["palette"]["colors"]

    print("\n\nReference Kirby Palette:")
    print("=" * 40)
    for i, color in enumerate(ref_colors[:8]):
        print(f"  {i}: RGB{tuple(color)}")

    # Load actual CGRAM
    palettes = parse_cgram("Cave.SnesCgRam.dmp")

    print("\n\nCave CGRAM - Palette 8 vs Reference:")
    print("=" * 40)
    print("Index | CGRAM Pal 8        | Reference Kirby")
    print("-" * 50)
    for i in range(8):
        cgram_color = palettes[8][i]
        ref_color = tuple(ref_colors[i])
        match = cgram_color == ref_color
        print(f'  {i}   | RGB{cgram_color:<16} | RGB{ref_color!s:<16} {"✓" if match else "✗"}')

if __name__ == "__main__":
    # Analyze Cave CGRAM
    analyze_palettes("Cave.SnesCgRam.dmp")

    # Compare with reference
    compare_with_reference()

    print("\n\nConclusion:")
    print("The Cave.SnesCgRam.dmp file appears to be from a different game state")
    print("where Kirby's normal pink palette is not loaded. The colors in palette 8")
    print("are purple/magenta instead of the expected pink shades.")
    print("\nRecommendation: Use the kirby_reference.pal.json for accurate Kirby colors!")
