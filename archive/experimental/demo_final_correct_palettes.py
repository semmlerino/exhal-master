#!/usr/bin/env python3
"""
Final corrected palette mapping based on visual confirmation
Kirby = Palette 8 (confirmed by yellow beam hat)
Enemy Group 1 = Palette 12 (confirmed by user)
"""

import sys

sys.path.append("sprite_editor")

from PIL import Image, ImageDraw

from sprite_editor.palette_utils import read_cgram_palette
from sprite_editor.sprite_editor_core import SpriteEditorCore


def main():
    core = SpriteEditorCore()

    print("=== Final Correct Palette Mapping ===")
    print("✓ Kirby (Beam form): Palette 8")
    print("✓ Enemy Group 1: Palette 12")
    print("\nLet's also identify palettes for other enemy groups...\n")

    # Extract and display with confirmed palettes
    confirmed_regions = [
        {
            "name": "Beam Kirby",
            "offset": 0xC000,
            "size": 0x800,
            "palette": 8,
            "tiles_per_row": 8
        },
        {
            "name": "Enemy Group 1",
            "offset": 0xD000,
            "size": 0x400,
            "palette": 12,
            "tiles_per_row": 8
        }
    ]

    # Also test other enemy groups to find their palettes
    test_regions = [
        {
            "name": "Enemy Group 2",
            "offset": 0xD400,
            "size": 0x400,
            "palettes_to_test": [4, 5, 6, 7, 9, 10, 11, 13, 14, 15],
            "tiles_per_row": 8
        },
        {
            "name": "Enemy Group 3",
            "offset": 0xD800,
            "size": 0x400,
            "palettes_to_test": [4, 5, 6, 7, 9, 10, 11, 13, 14, 15],
            "tiles_per_row": 8
        }
    ]

    final_images = []

    # First, show confirmed correct palettes
    for region in confirmed_regions:
        img, tiles = core.extract_sprites(
            "VRAM.dmp",
            region["offset"],
            region["size"],
            region["tiles_per_row"]
        )

        palette = read_cgram_palette("CGRAM.dmp", region["palette"])
        if palette:
            img.putpalette(palette)

            # Save individual file
            filename = f"demo_final_{region['name'].lower().replace(' ', '_')}_pal{region['palette']}.png"
            img.save(filename)
            print(f"✓ Saved: {filename}")

            # Scale for display
            scaled = img.resize((img.width * 2, img.height * 2), resample=Image.NEAREST)
            final_images.append((region["name"], region["palette"], scaled, True))

    # Test other regions
    for region in test_regions:
        print(f"\nTesting palettes for {region['name']}...")

        img, _ = core.extract_sprites(
            "VRAM.dmp",
            region["offset"],
            region["size"],
            region["tiles_per_row"]
        )

        # Create comparison for this region
        test_images = []
        for pal_num in region["palettes_to_test"]:
            palette = read_cgram_palette("CGRAM.dmp", pal_num)
            if palette:
                test_img = img.copy()
                test_img.putpalette(palette)
                scaled = test_img.resize((test_img.width, test_img.height), resample=Image.NEAREST)
                test_images.append((pal_num, scaled))

        # Create test strip for this region
        if test_images:
            create_test_strip(test_images, region["name"])

    # Create final showcase with confirmed palettes
    create_final_showcase(final_images)

    # Also create a full VRAM view with multiple palettes
    create_multi_palette_vram_view(core)

def create_test_strip(images, name):
    """Create a test strip for identifying correct palette"""

    # Split into two rows if too many
    items_per_row = 5
    rows = (len(images) + items_per_row - 1) // items_per_row

    cell_w = images[0][1].width
    cell_h = images[0][1].height
    padding = 5

    strip_w = min(len(images), items_per_row) * (cell_w + padding) + padding
    strip_h = rows * (cell_h + padding) + padding + 40

    strip = Image.new("RGB", (strip_w, strip_h), (32, 32, 32))
    draw = ImageDraw.Draw(strip)

    draw.text((strip_w // 2, 10), f"{name} - Which Palette?",
             fill=(255, 255, 255), anchor="mt")

    for idx, (pal_num, img) in enumerate(images):
        col = idx % items_per_row
        row = idx // items_per_row

        x = padding + col * (cell_w + padding)
        y = 30 + padding + row * (cell_h + padding)

        strip.paste(img, (x, y))

        # Label
        draw.text((x + cell_w // 2, y + cell_h + 2),
                 f"P{pal_num}", fill=(255, 255, 255), anchor="mt")

    filename = f"demo_test_{name.lower().replace(' ', '_')}_palettes.png"
    strip.save(filename)
    print(f"✓ Created: {filename}")

def create_final_showcase(images):
    """Create showcase with confirmed correct palettes"""

    if not images:
        return

    # Calculate dimensions
    max_width = max(img[2].width for img in images)
    total_height = sum(img[2].height for img in images) + len(images) * 50 + 60

    showcase = Image.new("RGB", (max_width + 60, total_height), (32, 32, 32))
    draw = ImageDraw.Draw(showcase)

    # Title
    draw.text((showcase.width // 2, 10),
             "Kirby Super Star - Confirmed Correct Palettes",
             fill=(255, 255, 255), anchor="mt")

    y = 50
    for name, pal_num, img, confirmed in images:
        x = (showcase.width - img.width) // 2

        showcase.paste(img, (x, y))

        # Draw border (green for confirmed)
        color = (0, 255, 0) if confirmed else (255, 255, 0)
        for i in range(3):
            draw.rectangle(
                [(x - i - 1, y - i - 1),
                 (x + img.width + i, y + img.height + i)],
                outline=color
            )

        # Label
        label = f"{name} - Palette {pal_num}"
        if confirmed:
            label += " ✓"

        draw.text((showcase.width // 2, y + img.height + 10),
                 label, fill=color, anchor="mt")

        y += img.height + 50

    showcase.save("demo_final_showcase.png")
    print("\n✓ Created: demo_final_showcase.png")

def create_multi_palette_vram_view(core):
    """Create a view showing different VRAM regions with their correct palettes"""

    # Based on what we know so far
    regions = [
        ("Beam Kirby", 0xC000, 0x800, 8, 8),
        ("Enemy Type 1", 0xD000, 0x400, 12, 8),
        # We'll need to identify these from the test strips
        ("Enemy Type 2", 0xD400, 0x400, 5, 8),  # Placeholder
        ("Enemy Type 3", 0xD800, 0x400, 10, 8), # Placeholder
    ]

    combined_width = 0
    combined_height = 0
    images = []

    for name, offset, size, palette, tiles_per_row in regions:
        img, _ = core.extract_sprites("VRAM.dmp", offset, size, tiles_per_row)
        pal = read_cgram_palette("CGRAM.dmp", palette)
        if pal:
            img.putpalette(pal)

        images.append((name, img))
        combined_width = max(combined_width, img.width)
        combined_height += img.height

    # Create combined view
    combined = Image.new("RGB", (combined_width + 40, combined_height + len(images) * 30 + 40), (32, 32, 32))
    draw = ImageDraw.Draw(combined)

    draw.text((combined.width // 2, 10),
             "VRAM Regions with Correct Palettes",
             fill=(255, 255, 255), anchor="mt")

    y = 40
    for name, img in images:
        x = (combined.width - img.width) // 2
        combined.paste(img, (x, y))

        draw.text((combined.width // 2, y + img.height + 5),
                 name, fill=(255, 255, 255), anchor="mt")

        y += img.height + 30

    combined.save("demo_vram_regions_correct.png")
    print("✓ Created: demo_vram_regions_correct.png")

if __name__ == "__main__":
    main()
