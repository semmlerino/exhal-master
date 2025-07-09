#!/usr/bin/env python3
"""
Show the actual palette colors in the editor to debug display issues
"""

import json
import os


def show_palette_colors():
    """Display palette colors from the companion file"""
    palette_file = "ultrathink/sprites/kirby_sprites.pal.json"

    if not os.path.exists(palette_file):
        print(f"Error: {palette_file} not found")
        return

    with open(palette_file) as f:
        data = json.load(f)

    colors = data["palette"]["colors"]
    name = data["palette"]["name"]

    print(f"\n🎨 Palette: {name}")
    print("=" * 50)

    for i, color in enumerate(colors):
        r, g, b = color
        # Create a colored block using ANSI escape codes
        block = f"\033[48;2;{r};{g};{b}m  \033[0m"

        # Determine if text should be white or black based on brightness
        (r + g + b) / 3

        print(f"Index {i:2d}: {block} RGB({r:3d}, {g:3d}, {b:3d}) #{r:02x}{g:02x}{b:02x}")

    print("\nIf the blocks above show colors, the palette data is correct.")
    print("If they're all black in the editor, there's a display issue.")

if __name__ == "__main__":
    show_palette_colors()
