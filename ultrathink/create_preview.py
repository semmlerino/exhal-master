#!/usr/bin/env python3
"""
Create a preview showing the sprites with different palettes
"""

import json
import os
import sys

import numpy as np
from PIL import Image

# Add parent directory to path for imports
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)

def apply_palette(indexed_png, palette_json, output_file):
    """Apply a palette to the indexed PNG"""
    # Load indexed image
    img = Image.open(indexed_png)

    # Load palette
    with open(palette_json) as f:
        palette_data = json.load(f)

    colors = palette_data["palette"]["colors"]

    # Get image data
    img_array = np.array(img)
    height, width = img_array.shape

    # Create RGB array
    rgb_array = np.zeros((height, width, 3), dtype=np.uint8)

    # Apply palette
    for y in range(height):
        for x in range(width):
            idx = img_array[y, x]
            if idx == 0:
                rgb_array[y, x] = [240, 240, 240]  # Light gray for transparent
            elif idx < len(colors):
                rgb_array[y, x] = colors[idx]

    # Save
    img_rgb = Image.fromarray(rgb_array)
    img_rgb.save(output_file)

    return img_rgb

def main():
    print("🖼️  Creating palette preview...")

    # Apply different palettes
    base_img = "sprites/kirby_sprites.png"

    # Create previews
    previews = []

    # Grayscale (original)
    img_gray = Image.open(base_img).convert("RGB")
    previews.append((img_gray, "Grayscale (Index View)"))

    # Companion palette (should be palette 8 now)
    if os.path.exists("sprites/kirby_sprites.pal.json"):
        img_companion = apply_palette(base_img, "sprites/kirby_sprites.pal.json",
                                     "sprites/preview_companion.png")
        previews.append((img_companion, "Default (Companion Palette)"))

    # Purple palette
    if os.path.exists("sprites/kirby_palette_8.pal.json"):
        img_purple = apply_palette(base_img, "sprites/kirby_palette_8.pal.json",
                                  "sprites/preview_purple.png")
        previews.append((img_purple, "Purple Kirby (Palette 8)"))

    # Create comparison strip
    if len(previews) > 1:
        width = previews[0][0].width
        height = previews[0][0].height

        # Create comparison image with labels
        comp_width = width * len(previews)
        comp_height = height + 30

        comparison = Image.new("RGB", (comp_width, comp_height), (32, 32, 32))

        # Paste images
        for i, (img, label) in enumerate(previews):
            comparison.paste(img, (i * width, 20))

        comparison.save("sprites/palette_comparison.png")
        print("✅ Created: sprites/palette_comparison.png")
        print("\nThis shows the same sprites with different viewing modes:")
        for _, label in previews:
            print(f"  - {label}")

if __name__ == "__main__":
    main()
