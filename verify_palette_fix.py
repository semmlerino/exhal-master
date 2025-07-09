#!/usr/bin/env python3
"""
Verify the palette fixes by creating visual comparisons
"""

import json
import os

from PIL import Image


def apply_palette_to_grayscale(png_file, palette_file, output_file):
    """Apply a palette from .pal.json to a grayscale indexed image"""
    # Load grayscale image
    img = Image.open(png_file)
    if img.mode != "P":
        raise ValueError(f"{png_file} is not in indexed mode")

    # Load palette data
    with open(palette_file) as f:
        palette_data = json.load(f)

    # Extract colors
    colors = palette_data["palette"]["colors"]

    # Create palette array
    palette_array = []
    for color in colors[:16]:  # First 16 colors
        palette_array.extend(color)

    # Pad to 256 colors
    while len(palette_array) < 768:
        palette_array.extend([0, 0, 0])

    # Apply palette
    img_copy = img.copy()
    img_copy.putpalette(palette_array)

    # Save result
    img_copy.save(output_file)
    print(f"Created: {output_file}")

    return img_copy

def create_comparison_strip():
    """Create a comparison strip showing original vs fixed palettes"""
    grayscale_file = "kirby_sprites_grayscale_ultrathink.png"

    if not os.path.exists(grayscale_file):
        print(f"Error: {grayscale_file} not found")
        return

    # Original palette
    original_palette = "kirby_sprites_grayscale_ultrathink.pal.json"

    # Fixed palettes
    fixed_palettes = [
        ("kirby_palette_14.pal.json", "Fixed Palette 14"),
        ("kirby_smart_palette_11.pal.json", "Smart Palette 11")
    ]

    # Create images
    images = []

    # Original
    if os.path.exists(original_palette):
        img = apply_palette_to_grayscale(grayscale_file, original_palette,
                                       "verify_original_palette.png")
        images.append((img, "Original (Palette 14)"))

    # Fixed versions
    for palette_file, label in fixed_palettes:
        if os.path.exists(palette_file):
            img = apply_palette_to_grayscale(grayscale_file, palette_file,
                                           f"verify_{palette_file.replace('.pal.json', '.png')}")
            images.append((img, label))

    # Create comparison strip
    if images:
        # Get dimensions
        width = images[0][0].width
        height = images[0][0].height

        # Create comparison image
        comparison = Image.new("RGB", (width * len(images), height + 30))

        # Paste images
        for i, (img, label) in enumerate(images):
            # Convert to RGB
            img_rgb = img.convert("RGB")
            comparison.paste(img_rgb, (i * width, 0))

        # Save comparison
        comparison.save("palette_fix_comparison.png")
        print("\nCreated comparison: palette_fix_comparison.png")
        print("This shows side-by-side comparison of palettes")

def main():
    print("🔍 Verifying Palette Fixes")
    print("=" * 40)

    # Create visual comparisons
    create_comparison_strip()

    # Also test on the focused Kirby sprite if available
    if os.path.exists("kirby_focused_test.png"):
        print("\nTesting on Kirby-focused sprite...")

        if os.path.exists("kirby_palette_14.pal.json"):
            apply_palette_to_grayscale("kirby_focused_test.png",
                                     "kirby_palette_14.pal.json",
                                     "kirby_focused_palette_14_applied.png")

        if os.path.exists("kirby_smart_palette_11.pal.json"):
            apply_palette_to_grayscale("kirby_focused_test.png",
                                     "kirby_smart_palette_11.pal.json",
                                     "kirby_focused_palette_11_applied.png")

    print("\n✅ Verification complete!")
    print("\nCheck these files:")
    print("- palette_fix_comparison.png - Side-by-side comparison")
    print("- verify_*.png - Individual palette applications")
    print("- kirby_focused_*.png - Focused Kirby sprite tests")

if __name__ == "__main__":
    main()
