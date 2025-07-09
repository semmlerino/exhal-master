#!/usr/bin/env python3
"""
Fix the palette inversion issue by properly handling index 0 as transparent
"""

import os

import numpy as np
from PIL import Image

from sprite_editor.palette_utils import read_cgram_palette


def get_corrected_grayscale_palette():
    """
    Get a corrected grayscale palette where index 0 is white (background)
    and other indices are darker for better visualization
    """
    palette = []
    for i in range(256):
        if i == 0:
            # Index 0 should be white/light for transparent background
            gray = 255
        elif i < 16:
            # Indices 1-15 map to darker values for sprites
            # Invert the mapping: 1->238, 2->221, ..., 15->17
            gray = 255 - (i * 17)
        else:
            # Rest are black
            gray = 0
        palette.extend([gray, gray, gray])
    return palette

def fix_grayscale_sheet(input_path, output_path):
    """Fix a grayscale sprite sheet to have proper index visualization"""
    img = Image.open(input_path)

    if img.mode != "P":
        print(f"Skipping {input_path} - not indexed color mode")
        return

    # Apply corrected grayscale palette
    corrected_palette = get_corrected_grayscale_palette()
    img.putpalette(corrected_palette)

    img.save(output_path)
    print(f"Fixed: {input_path} -> {output_path}")

def apply_palette_with_transparent_bg(input_path, cgram_file, palette_num, output_path):
    """Apply a color palette but handle index 0 as transparent/background"""
    img = Image.open(input_path)

    if img.mode != "P":
        print(f"Skipping {input_path} - not indexed color mode")
        return

    # Get the color palette
    palette = read_cgram_palette(cgram_file, palette_num)
    if not palette:
        print(f"Failed to read palette {palette_num}")
        return

    # Create a modified palette where index 0 is a neutral background color
    palette.copy()

    # Option 1: Make index 0 transparent (requires RGBA conversion)
    # Convert to RGBA for transparency
    img = img.convert("RGBA")
    np.array(img)

    # Make index 0 pixels transparent
    img_indexed = Image.open(input_path)  # Re-open to get indexed version
    indexed_pixels = np.array(img_indexed)

    # Create alpha channel - 0 where index is 0, 255 elsewhere
    alpha = np.where(indexed_pixels == 0, 0, 255).astype(np.uint8)

    # Apply the color palette to non-transparent pixels
    color_img = img_indexed.copy()
    color_img.putpalette(palette)
    color_array = np.array(color_img.convert("RGBA"))

    # Set alpha channel
    color_array[:, :, 3] = alpha

    # Create final image
    result = Image.fromarray(color_array, "RGBA")
    result.save(output_path)
    print(f"Applied palette {palette_num} with transparency: {output_path}")

    # Option 2: Use a specific background color for index 0
    output_path2 = output_path.replace(".png", "_bgcolor.png")
    img_indexed = Image.open(input_path)

    # Modify palette to use a specific background color for index 0
    bg_palette = palette.copy()
    # Use a light gray background instead of the palette's index 0 color
    bg_palette[0] = 240  # R
    bg_palette[1] = 240  # G
    bg_palette[2] = 240  # B

    img_indexed.putpalette(bg_palette)
    img_indexed.save(output_path2)
    print(f"Applied palette {palette_num} with gray background: {output_path2}")

def create_proper_preview_function():
    """Create a function that generates proper palette previews"""
    code = '''def apply_palette_for_preview(base_image, palette, handle_transparency=True):
    """
    Apply a palette to an indexed image for preview purposes.

    Args:
        base_image: PIL Image in mode 'P'
        palette: List of RGB values (768 values)
        handle_transparency: If True, make index 0 transparent or use neutral color

    Returns:
        PIL Image with palette applied
    """
    if not isinstance(base_image, Image.Image) or base_image.mode != 'P':
        raise ValueError("Image must be in indexed color mode")

    if handle_transparency:
        # Option 1: Convert to RGBA with transparency
        img_rgba = base_image.convert('RGBA')
        pixels = np.array(base_image)

        # Create alpha channel - 0 where index is 0, 255 elsewhere
        alpha = np.where(pixels == 0, 0, 255).astype(np.uint8)

        # Apply palette and convert to RGBA
        img_colored = base_image.copy()
        img_colored.putpalette(palette)
        color_array = np.array(img_colored.convert('RGBA'))

        # Set alpha channel
        color_array[:, :, 3] = alpha

        return Image.fromarray(color_array, 'RGBA')
    else:
        # Option 2: Just apply palette directly
        img_copy = base_image.copy()
        img_copy.putpalette(palette)
        return img_copy
'''

    with open("palette_preview_fix.py", "w") as f:
        f.write(code)
    print("Created palette_preview_fix.py with improved preview function")

def main():
    # Fix grayscale sheets
    sheets = [
        ("Kirby_sheet.png", "Kirby_sheet_fixed.png"),
        ("Level_Sprites_sheet.png", "Level_Sprites_sheet_fixed.png"),
        ("UI_Elements_sheet.png", "UI_Elements_sheet_fixed.png"),
        ("Effects_sheet.png", "Effects_sheet_fixed.png")
    ]

    print("Fixing grayscale sprite sheets...")
    for input_file, output_file in sheets:
        if os.path.exists(input_file):
            fix_grayscale_sheet(input_file, output_file)

    # Test color palette application with proper transparency handling
    cgram_file = "SnesCgRam.dmp"
    if os.path.exists(cgram_file) and os.path.exists("Kirby_sheet.png"):
        print("\nTesting palette application with transparency...")
        apply_palette_with_transparent_bg(
            "Kirby_sheet.png",
            cgram_file,
            8,  # Kirby's palette
            "Kirby_sheet_pal8_transparent.png"
        )

    # Create improved preview function
    create_proper_preview_function()

    print("\nTo fix the issue in the sprite editor:")
    print("1. Update the grayscale palette generation to use white for index 0")
    print("2. When applying color palettes, handle index 0 as transparent/background")
    print("3. Consider using RGBA mode for proper transparency support")

if __name__ == "__main__":
    main()
