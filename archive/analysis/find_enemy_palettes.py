#!/usr/bin/env python3
"""
Find correct enemy palettes through visual inspection
Since Kirby is confirmed palette 8, let's test all palettes on enemy sprites
"""

import sys

sys.path.append("sprite_editor")

from PIL import Image, ImageDraw

from sprite_editor.palette_utils import read_cgram_palette
from sprite_editor.sprite_editor_core import SpriteEditorCore


def main():
    core = SpriteEditorCore()

    print("=== Finding Correct Enemy Palettes ===")
    print("Kirby confirmed: Palette 8 ✓")
    print("\nTesting all 16 palettes on enemy sprites...\n")

    # Enemy regions to test (based on visual inspection of VRAM)
    enemy_regions = [
        {
            "name": "Enemy Group 1",
            "offset": 0xD000,  # After Kirby area
            "size": 0x400,
            "tiles_per_row": 8
        },
        {
            "name": "Enemy Group 2",
            "offset": 0xD400,
            "size": 0x400,
            "tiles_per_row": 8
        },
        {
            "name": "Enemy Group 3",
            "offset": 0xD800,
            "size": 0x400,
            "tiles_per_row": 8
        }
    ]

    for region in enemy_regions:
        print(f"\nTesting {region['name']} (offset: 0x{region['offset']:04X})")

        # Extract base image
        img, tiles = core.extract_sprites(
            "VRAM.dmp",
            region["offset"],
            region["size"],
            region["tiles_per_row"]
        )

        # Test all 16 palettes
        palette_images = []

        for pal_num in range(16):
            palette = read_cgram_palette("CGRAM.dmp", pal_num)
            if palette:
                test_img = img.copy()
                test_img.putpalette(palette)

                # Scale for visibility
                scaled = test_img.resize(
                    (test_img.width * 2, test_img.height * 2),
                    resample=Image.NEAREST
                )

                palette_images.append((pal_num, scaled))

        # Create grid showing all palette options
        if palette_images:
            create_palette_grid(palette_images, region["name"])

    # Also create a focused test on specific enemy sprites
    create_enemy_palette_test()

def create_palette_grid(images, name):
    """Create a 4x4 grid showing all palette options"""

    cols = 4
    rows = 4
    cell_w = images[0][1].width
    cell_h = images[0][1].height
    padding = 5

    grid_w = cols * cell_w + (cols + 1) * padding
    grid_h = rows * cell_h + (rows + 1) * padding + 40

    grid = Image.new("RGB", (grid_w, grid_h), (32, 32, 32))
    draw = ImageDraw.Draw(grid)

    # Title
    draw.text((grid_w // 2, 10), f"{name} - All Palettes",
             fill=(255, 255, 255), anchor="mt")

    # Place images
    for idx, (pal_num, img) in enumerate(images):
        col = idx % cols
        row = idx // cols

        x = padding + col * (cell_w + padding)
        y = 30 + padding + row * (cell_h + padding)

        grid.paste(img, (x, y))

        # Label with palette number
        label_x = x + cell_w // 2
        label_y = y + cell_h - 10

        # Draw background for readability
        draw.rectangle(
            [(label_x - 15, label_y - 8), (label_x + 15, label_y + 8)],
            fill=(0, 0, 0)
        )

        draw.text((label_x, label_y), f"P{pal_num}",
                 fill=(255, 255, 255), anchor="mm")

    filename = f"demo_enemy_palettes_{name.lower().replace(' ', '_')}.png"
    grid.save(filename)
    print(f"✓ Saved: {filename}")

def create_enemy_palette_test():
    """Create focused comparison of likely enemy palettes"""

    core = SpriteEditorCore()

    # Extract a smaller region with clear enemy sprites
    img, _ = core.extract_sprites("VRAM.dmp", 0xD000, 0x200, 8)

    # Test likely enemy palettes based on typical SNES games
    # Usually enemies use mid-range palettes (4-7, 9-11)
    test_palettes = [3, 4, 5, 6, 7, 9, 10, 11]

    comparisons = []
    for pal_num in test_palettes:
        palette = read_cgram_palette("CGRAM.dmp", pal_num)
        if palette:
            test_img = img.copy()
            test_img.putpalette(palette)
            scaled = test_img.resize(
                (test_img.width * 3, test_img.height * 3),
                resample=Image.NEAREST
            )
            comparisons.append((pal_num, scaled))

    # Create comparison strip
    if comparisons:
        width = sum(c[1].width for c in comparisons) + len(comparisons) * 10 + 10
        height = comparisons[0][1].height + 60

        strip = Image.new("RGB", (width, height), (32, 32, 32))
        draw = ImageDraw.Draw(strip)

        draw.text((width // 2, 10), "Enemy Palette Test - Which Look Correct?",
                 fill=(255, 255, 255), anchor="mt")

        x = 10
        for pal_num, img in comparisons:
            strip.paste(img, (x, 30))

            # Draw border
            draw.rectangle(
                [(x - 1, 30 - 1), (x + img.width, 30 + img.height)],
                outline=(128, 128, 128)
            )

            # Label
            draw.text((x + img.width // 2, height - 15),
                     f"Palette {pal_num}",
                     fill=(255, 255, 255), anchor="mt")

            x += img.width + 10

        strip.save("demo_enemy_palette_comparison.png")
        print("\n✓ Created demo_enemy_palette_comparison.png")
        print("\nPlease check which palettes make the enemies look correct!")

if __name__ == "__main__":
    main()
