#!/usr/bin/env python3
"""
Create PNG files with correct palettes applied
"""

import json
import os

import numpy as np
from PIL import Image


def create_colored_png(grayscale_png, palette_file, output_file):
    """
    Apply a palette to a grayscale indexed image and save as RGB PNG
    """
    # Load grayscale image
    img = Image.open(grayscale_png)
    if img.mode != "P":
        print(f"Error: {grayscale_png} is not in indexed mode")
        return False

    # Load palette data
    with open(palette_file) as f:
        palette_data = json.load(f)

    # Extract colors
    colors = palette_data["palette"]["colors"]
    palette_name = palette_data["palette"]["name"]

    print(f"Applying {palette_name} to {grayscale_png}...")

    # Create reverse mapping from gray values to indices
    # Based on extract_grayscale_sheet.py mapping:
    # 0 → 0, 1 → 17, 2 → 34, 3 → 51, etc.
    gray_to_index = {}
    gray_to_index[0] = 0  # Transparent
    for i in range(1, 16):
        gray_value = int(17 + (i-1) * (255-17) / 14)
        gray_to_index[gray_value] = i

    # Create RGB image manually by mapping gray values to palette colors
    img_array = np.array(img)
    height, width = img_array.shape

    # Create RGB array
    rgb_array = np.zeros((height, width, 3), dtype=np.uint8)

    # Map each pixel
    for y in range(height):
        for x in range(width):
            gray_value = img_array[y, x]

            # Find closest gray value in our mapping
            if gray_value in gray_to_index:
                index = gray_to_index[gray_value]
            else:
                # Find closest match
                min_diff = 256
                index = 0
                for gv, idx in gray_to_index.items():
                    diff = abs(gray_value - gv)
                    if diff < min_diff:
                        min_diff = diff
                        index = idx

            # Apply color from palette
            if index == 0:
                # Transparent - use light gray
                rgb_array[y, x] = [240, 240, 240]
            else:
                rgb_array[y, x] = colors[index]

    # Create RGB image
    img_rgb = Image.fromarray(rgb_array, mode="RGB")

    # Save as PNG
    img_rgb.save(output_file)
    print(f"Created: {output_file}")

    return True

def main():
    print("🎨 Creating Colored PNG Files")
    print("=" * 50)

    # Define input/output pairs
    conversions = [
        # Main sprite sheet with different palettes
        ("kirby_sprites_grayscale_ultrathink.png", "kirby_palette_14.pal.json",
         "kirby_sprites_colored_palette14.png"),

        ("kirby_sprites_grayscale_ultrathink.png", "kirby_palette_8.pal.json",
         "kirby_sprites_colored_palette8.png"),

        ("kirby_sprites_grayscale_ultrathink.png", "kirby_smart_palette_11.pal.json",
         "kirby_sprites_colored_palette11.png"),

        # Tiny test with palettes
        ("tiny_test.png", "kirby_palette_14.pal.json",
         "tiny_test_colored_palette14.png"),

        ("tiny_test.png", "kirby_palette_8.pal.json",
         "tiny_test_colored_palette8.png"),

        # Kirby focused test
        ("kirby_focused_test.png", "kirby_palette_14.pal.json",
         "kirby_focused_colored_palette14.png"),

        ("kirby_focused_test.png", "kirby_palette_8.pal.json",
         "kirby_focused_colored_palette8.png"),
    ]

    success_count = 0

    for grayscale, palette, output in conversions:
        if os.path.exists(grayscale) and os.path.exists(palette):
            if create_colored_png(grayscale, palette, output):
                success_count += 1
        else:
            if not os.path.exists(grayscale):
                print(f"⚠️  Missing grayscale file: {grayscale}")
            if not os.path.exists(palette):
                print(f"⚠️  Missing palette file: {palette}")

    print(f"\n✅ Created {success_count} colored PNG files")

    # Create a comparison image showing the main sprite sheet with different palettes
    if all(os.path.exists(f) for f in ["kirby_sprites_colored_palette14.png",
                                        "kirby_sprites_colored_palette8.png",
                                        "kirby_sprites_colored_palette11.png"]):

        print("\nCreating palette comparison image...")

        # Load images
        img14 = Image.open("kirby_sprites_colored_palette14.png")
        img8 = Image.open("kirby_sprites_colored_palette8.png")
        img11 = Image.open("kirby_sprites_colored_palette11.png")

        # Create comparison
        width = img14.width
        height = img14.height

        comparison = Image.new("RGB", (width * 3, height + 40), (32, 32, 32))

        # Paste images
        comparison.paste(img14, (0, 20))
        comparison.paste(img8, (width, 20))
        comparison.paste(img11, (width * 2, 20))

        # Add labels (using PIL's basic drawing)
        from PIL import ImageDraw
        draw = ImageDraw.Draw(comparison)

        # Labels
        labels = ["Palette 14 (Pink)", "Palette 8 (Purple)", "Palette 11 (Yellow)"]
        for i, label in enumerate(labels):
            # Simple text placement
            x = i * width + 10
            y = 5
            # Note: Default font, white text
            draw.text((x, y), label, fill=(255, 255, 255))

        comparison.save("kirby_sprites_palette_comparison.png")
        print("Created: kirby_sprites_palette_comparison.png")

    print("\n📁 Output files:")
    print("- kirby_sprites_colored_palette14.png (Pink Kirby)")
    print("- kirby_sprites_colored_palette8.png (Purple Kirby)")
    print("- kirby_sprites_colored_palette11.png (Yellow/Brown)")
    print("- kirby_sprites_palette_comparison.png (Side-by-side)")
    print("\nThese files show the sprites with proper colors applied!")

if __name__ == "__main__":
    main()
