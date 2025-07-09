#!/usr/bin/env python3
"""
Create a visual comparison of all palette test results to identify the correct Kirby palette.
"""

import os

from PIL import Image, ImageDraw, ImageFont


def create_palette_comparison():
    """Create a comparison image showing all palette test results"""

    # Load all test images
    test_dir = "palette_tests"
    palette_files = []

    for pal_idx in range(8, 16):
        file_path = os.path.join(test_dir, f"palette_{pal_idx}_test.png")
        if os.path.exists(file_path):
            palette_files.append((pal_idx, file_path))

    if not palette_files:
        print("No test images found!")
        return

    # Load first image to get dimensions
    sample_img = Image.open(palette_files[0][1])
    img_width, img_height = sample_img.size

    # Create comparison grid (2x4 layout)
    grid_cols = 2
    grid_rows = 4
    margin = 20
    label_height = 30

    grid_width = (img_width + margin) * grid_cols + margin
    grid_height = (img_height + label_height + margin) * grid_rows + margin

    comparison = Image.new("RGB", (grid_width, grid_height), (64, 64, 64))
    draw = ImageDraw.Draw(comparison)

    # Try to load a font (fallback to default if not available)
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf", 16)
    except:
        font = ImageFont.load_default()

    # OAM usage data
    oam_usage = {
        8: 6,
        9: 0,
        10: 0,
        11: 23,
        12: 5,
        13: 0,
        14: 10,
        15: 2
    }

    # Paste each test image with labels
    for idx, (pal_idx, file_path) in enumerate(palette_files):
        col = idx % grid_cols
        row = idx // grid_cols

        x = margin + col * (img_width + margin)
        y = margin + row * (img_height + label_height + margin)

        # Load and paste image
        test_img = Image.open(file_path)
        comparison.paste(test_img, (x, y + label_height))

        # Add label
        label = f"Palette {pal_idx}"
        if pal_idx == 8:
            label += " (Default Kirby)"

        # Add OAM usage info
        usage = oam_usage.get(pal_idx, 0)
        if usage > 0:
            label += f" - {usage} sprites"

        # Color-code based on recommendation
        if pal_idx == 8:
            text_color = (255, 255, 128)  # Yellow for default
        elif pal_idx == 14:
            text_color = (128, 255, 128)  # Green for recommended
        elif usage > 0:
            text_color = (255, 255, 255)  # White for used palettes
        else:
            text_color = (192, 192, 192)  # Gray for unused palettes

        draw.text((x, y), label, fill=text_color, font=font)

    # Add title and legend
    title = "Kirby Sprite Palette Comparison"
    draw.text((grid_width // 2 - 100, 5), title, fill=(255, 255, 255), font=font)

    # Save comparison
    comparison.save("kirby_palette_comparison.png")
    print("Saved comparison to: kirby_palette_comparison.png")

    # Also create a focused comparison of the most likely palettes
    create_focused_comparison()

def create_focused_comparison():
    """Create a focused comparison of the most likely Kirby palettes"""

    # Focus on palettes 8, 12, and 14 which have Kirby colors and OAM usage
    focused_palettes = [8, 12, 14]

    test_dir = "palette_tests"
    images = []

    for pal_idx in focused_palettes:
        file_path = os.path.join(test_dir, f"palette_{pal_idx}_test.png")
        if os.path.exists(file_path):
            img = Image.open(file_path)
            images.append((pal_idx, img))

    if not images:
        return

    # Extract a region with Kirby sprites (adjust coordinates as needed)
    # Looking for the area around tiles 384-404 based on the metadata
    tile_size = 8
    tiles_per_row = 16

    # Calculate region for tiles around 384-404 (Kirby area)
    start_tile = 384
    end_tile = 404

    start_row = start_tile // tiles_per_row
    start_col = start_tile % tiles_per_row
    end_row = end_tile // tiles_per_row
    end_col = end_tile % tiles_per_row

    # Define crop region
    crop_x1 = start_col * tile_size
    crop_y1 = start_row * tile_size
    crop_x2 = (end_col + 1) * tile_size
    crop_y2 = (end_row + 1) * tile_size

    # Create focused comparison
    crop_width = crop_x2 - crop_x1
    crop_height = crop_y2 - crop_y1
    scale = 4  # Scale up for better visibility

    focused_width = crop_width * scale * len(focused_palettes) + 20 * (len(focused_palettes) + 1)
    focused_height = crop_height * scale + 60

    focused = Image.new("RGB", (focused_width, focused_height), (64, 64, 64))
    draw = ImageDraw.Draw(focused)

    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf", 14)
    except:
        font = ImageFont.load_default()

    # OAM usage and descriptions
    descriptions = {
        8: "Default Kirby (6 sprites) - Pink/Purple",
        12: "Alt Palette (5 sprites) - Orange tones",
        14: "Recommended (10 sprites) - Red/Pink"
    }

    x_offset = 20
    for pal_idx, img in images:
        # Crop the region
        cropped = img.crop((crop_x1, crop_y1, crop_x2, crop_y2))

        # Scale up
        scaled = cropped.resize((crop_width * scale, crop_height * scale), Image.NEAREST)

        # Paste
        focused.paste(scaled, (x_offset, 40))

        # Add label
        desc = descriptions.get(pal_idx, f"Palette {pal_idx}")
        draw.text((x_offset, 10), desc, fill=(255, 255, 255), font=font)

        x_offset += crop_width * scale + 20

    # Save focused comparison
    focused.save("kirby_palette_focused.png")
    print("Saved focused comparison to: kirby_palette_focused.png")

if __name__ == "__main__":
    create_palette_comparison()
