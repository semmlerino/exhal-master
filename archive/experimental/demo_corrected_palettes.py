#!/usr/bin/env python3
"""
Corrected extraction using actual OAM palette data
The OAM data shows which palettes are REALLY being used
"""

import sys

sys.path.append("sprite_editor")

from PIL import Image, ImageDraw

from sprite_editor.palette_utils import read_cgram_palette
from sprite_editor.sprite_editor_core import SpriteEditorCore


def main():
    core = SpriteEditorCore()

    print("=== CORRECTED: Using Actual OAM Palette Data ===\n")

    # From OAM analysis:
    # - Tiles 0x000-0x01D use Palette 0 (likely Kirby/UI)
    # - Tiles 0x0A0-0x0BE use Palette 6 (enemies)
    # - Tiles around 0x080 use Palette 3
    # - Tiles around 0x020-0x040 use Palette 4

    print("Actual palette usage from OAM data:")
    print("- Palette 0: Early tiles (Kirby area?)")
    print("- Palette 6: Enemy tiles (0x0A0+)")
    print("- Palette 4: Mid-range tiles")
    print("- Palette 2, 3, 7: Other sprites\n")

    # Extract regions with their ACTUAL palettes from OAM
    extractions = [
        {
            "name": "Kirby/UI Area",
            "offset": 0xC000,
            "size": 0x400,  # First 32 tiles
            "palette": 0,    # OAM shows these use palette 0!
            "tiles_per_row": 8
        },
        {
            "name": "Enemy Area",
            "offset": 0xD400,  # Where tiles 0x0A0+ would be
            "size": 0x800,     # 64 tiles
            "palette": 6,      # OAM shows these use palette 6!
            "tiles_per_row": 8
        },
        {
            "name": "Mid Sprites",
            "offset": 0xC400,  # Where tiles 0x020+ would be
            "size": 0x800,
            "palette": 4,      # OAM shows palette 4
            "tiles_per_row": 8
        }
    ]

    images = []

    for region in extractions:
        print(f"\nExtracting {region['name']}...")

        # Extract base image
        img, tiles = core.extract_sprites(
            "VRAM.dmp",
            region["offset"],
            region["size"],
            region["tiles_per_row"]
        )

        # Apply the ACTUAL palette from OAM
        palette = read_cgram_palette("CGRAM.dmp", region["palette"])
        if palette:
            img.putpalette(palette)

            # Save individual file
            filename = f"demo_corrected_{region['name'].lower().replace(' ', '_').replace('/', '_')}_pal{region['palette']}.png"
            img.save(filename)
            print(f"✓ Saved: {filename}")

            # Scale for visibility
            scaled = img.resize((img.width * 2, img.height * 2), resample=Image.NEAREST)
            images.append((region["name"], region["palette"], scaled))

    # Create comparison image
    if images:
        create_comparison(images)

    # Also check what Beam Kirby looks like with different palettes
    print("\n\nChecking Beam Kirby theory...")
    check_beam_kirby()

def create_comparison(images):
    """Create a comparison showing the corrected palettes"""

    # Calculate dimensions
    max_width = max(img[2].width for img in images)
    total_height = sum(img[2].height for img in images) + len(images) * 40 + 60

    comparison = Image.new("RGB", (max_width + 40, total_height), (32, 32, 32))
    draw = ImageDraw.Draw(comparison)

    # Title
    draw.text((comparison.width // 2, 10),
             "CORRECTED: Using Actual OAM Palette Mappings",
             fill=(255, 255, 255), anchor="mt")

    y = 40
    for name, pal_num, img in images:
        # Center image
        x = (comparison.width - img.width) // 2

        comparison.paste(img, (x, y))

        # Draw border
        draw.rectangle(
            [(x - 2, y - 2), (x + img.width + 1, y + img.height + 1)],
            outline=(0, 255, 0), width=2
        )

        # Label
        label = f"{name} - Palette {pal_num} (from OAM data)"
        draw.text((comparison.width // 2, y + img.height + 5),
                 label, fill=(0, 255, 0), anchor="mt")

        y += img.height + 40

    comparison.save("demo_corrected_oam_palettes.png")
    print("\n✓ Created demo_corrected_oam_palettes.png")

def check_beam_kirby():
    """Check if the yellow Kirby is actually palette 0 with specific CGRAM"""

    core = SpriteEditorCore()

    # Extract first area
    img, _ = core.extract_sprites("VRAM.dmp", 0xC000, 0x400, 8)

    print("\nComparing palettes on Kirby area:")
    comparisons = []

    # Test different palettes
    for pal_num in [0, 8, 10, 12]:
        palette = read_cgram_palette("CGRAM.dmp", pal_num)
        if palette:
            test_img = img.copy()
            test_img.putpalette(palette)
            scaled = test_img.resize((test_img.width * 3, test_img.height * 3),
                                   resample=Image.NEAREST)
            comparisons.append((pal_num, scaled))

            # Check if this palette has yellow/orange colors
            # Look at first few colors (skip transparent)
            colors = []
            for i in range(1, 6):
                r = palette[i * 3]
                g = palette[i * 3 + 1]
                b = palette[i * 3 + 2]
                colors.append(f"({r},{g},{b})")
            print(f"  Palette {pal_num} first colors: {', '.join(colors)}")

    # Create comparison strip
    if comparisons:
        width = sum(c[1].width for c in comparisons) + len(comparisons) * 10 + 10
        height = comparisons[0][1].height + 50

        strip = Image.new("RGB", (width, height), (32, 32, 32))
        draw = ImageDraw.Draw(strip)

        draw.text((width // 2, 5), "Which Palette Makes Kirby Yellow?",
                 fill=(255, 255, 255), anchor="mt")

        x = 10
        for pal_num, img in comparisons:
            strip.paste(img, (x, 25))

            draw.text((x + img.width // 2, height - 15),
                     f"Palette {pal_num}",
                     fill=(255, 255, 255), anchor="mt")

            x += img.width + 10

        strip.save("demo_kirby_palette_test.png")
        print("\n✓ Created demo_kirby_palette_test.png")

if __name__ == "__main__":
    main()
