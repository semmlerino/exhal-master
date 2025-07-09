#!/usr/bin/env python3
"""
Visual comparison of different preview sizes
"""

from PIL import Image, ImageDraw


def create_comparison():
    """Create a visual comparison of preview sizes"""

    # Create comparison image
    comparison = Image.new("RGB", (800, 400), (32, 32, 32))
    draw = ImageDraw.Draw(comparison)

    # Load preview images if they exist
    previews = [
        (
            "Full (512 tiles)",
            "test_palette_grid.png",
            "512 tiles = 128x256px\nHard to see details",
        ),
        (
            "Focused (64 tiles)",
            "preview_64_tiles.png",
            "64 tiles = 64x64px\nClear and visible",
        ),
        (
            "Minimal (32 tiles)",
            "preview_32_tiles.png",
            "32 tiles = 64x32px\nJust main sprites",
        ),
    ]

    x_offset = 20
    for _i, (title, filename, desc) in enumerate(previews):
        try:
            img = Image.open(filename)

            # Scale to fit
            max_height = 300
            if img.height > max_height:
                scale = max_height / img.height
                new_width = int(img.width * scale)
                img = img.resize((new_width, max_height), Image.Resampling.NEAREST)

            # Paste into comparison
            y_offset = 50
            comparison.paste(img, (x_offset, y_offset))

            # Add labels
            draw.text((x_offset, 20), title, fill=(255, 255, 255))
            draw.text(
                (x_offset, y_offset + img.height + 10), desc, fill=(200, 200, 200)
            )

            x_offset += img.width + 50

        except (FileNotFoundError, OSError):
            pass

    # Add title
    draw.text((20, 5), "Multi-Palette Preview Size Comparison", fill=(255, 255, 0))

    comparison.save("preview_size_comparison.png")
    print("Created preview_size_comparison.png")


if __name__ == "__main__":
    create_comparison()
