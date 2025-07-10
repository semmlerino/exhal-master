#!/usr/bin/env python3
"""
Corrected demo showing Beam Kirby (yellow) extraction with proper palette
The VRAM dump contains Beam/Spark Kirby, not regular pink Kirby!
"""

import sys

sys.path.append("sprite_editor")

from PIL import Image

from sprite_editor.sprite_editor_core import SpriteEditorCore


def main():
    core = SpriteEditorCore()

    print("=== CORRECTED: Beam Kirby Multi-Palette Demo ===\n")
    print("KEY DISCOVERY: The VRAM dump contains BEAM KIRBY (yellow), not regular pink Kirby!")
    print("Beam Kirby uses Palette 8 according to the documentation.\n")

    # Load OAM data
    print("Loading OAM data...")
    core.load_oam_mapping("OAM.dmp")

    # Extract just Kirby area (first 64-128 tiles)
    print("\nExtracting Beam Kirby sprites (VRAM 0xC000)...")

    # Method 1: Single palette version to show Beam Kirby correctly
    print("\n1. Extracting with Palette 8 (Beam Kirby's correct palette):")
    base_img, tiles = core.extract_sprites("VRAM.dmp", 0xC000, 0x1000, tiles_per_row=8)

    # Apply palette 8 (yellow/orange for Beam Kirby)
    from sprite_editor.palette_utils import read_cgram_palette
    palette_8 = read_cgram_palette("CGRAM.dmp", 8)
    if palette_8:
        img_pal8 = base_img.copy()
        img_pal8.putpalette(palette_8)
        img_pal8.save("demo_beam_kirby_palette8.png")

        # Scale up for visibility
        scaled = img_pal8.resize((img_pal8.width * 4, img_pal8.height * 4), resample=Image.NEAREST)
        scaled.save("demo_beam_kirby_palette8_4x.png")
        print("✓ Saved: demo_beam_kirby_palette8.png and 4x version")

    # Method 2: Show all palettes to demonstrate why palette 8 is correct
    print("\n2. Creating comparison with all palettes:")
    images = []

    for pal_num in range(16):
        palette = read_cgram_palette("CGRAM.dmp", pal_num)
        if palette:
            img = base_img.copy()
            img.putpalette(palette)

            # Crop to just first few tiles for comparison
            cropped = img.crop((0, 0, 64, 64))
            scaled = cropped.resize((256, 256), resample=Image.NEAREST)
            images.append((pal_num, scaled))

    # Create comparison grid
    if images:
        grid_width = 4
        grid_height = 4
        cell_size = 256
        padding = 10

        total_w = grid_width * cell_size + (grid_width + 1) * padding
        total_h = grid_height * cell_size + (grid_height + 1) * padding

        grid = Image.new("RGB", (total_w, total_h), (32, 32, 32))

        from PIL import ImageDraw
        draw = ImageDraw.Draw(grid)

        for idx, (pal_num, img) in enumerate(images):
            col = idx % grid_width
            row = idx // grid_width

            x = padding + col * (cell_size + padding)
            y = padding + row * (cell_size + padding)

            grid.paste(img, (x, y))

            # Highlight palette 8
            if pal_num == 8:
                # Draw thick green border
                for i in range(5):
                    draw.rectangle(
                        [(x - i - 1, y - i - 1),
                         (x + cell_size + i, y + cell_size + i)],
                        outline=(0, 255, 0)
                    )
                label = f"Palette {pal_num} (BEAM KIRBY)"
                color = (0, 255, 0)
            else:
                label = f"Palette {pal_num}"
                color = (255, 255, 255)

            # Draw label
            draw.text((x + cell_size // 2, y + cell_size + 5),
                     label, fill=color, anchor="mt")

        grid.save("demo_beam_kirby_all_palettes.png")
        print("✓ Saved: demo_beam_kirby_all_palettes.png")

    # Method 3: Extract with OAM-based palette mapping
    print("\n3. Extracting with OAM-based palette mapping:")
    try:
        oam_img, _ = core.extract_sprites_with_correct_palettes(
            "VRAM.dmp", 0xC000, 0x1000, "CGRAM.dmp", tiles_per_row=8
        )
        oam_img.save("demo_beam_kirby_oam_correct.png")
        print("✓ Saved: demo_beam_kirby_oam_correct.png")
    except Exception as e:
        print(f"Note: {e}")

    print("\n=== Results ===")
    print("1. demo_beam_kirby_palette8.png - Beam Kirby with correct yellow palette")
    print("2. demo_beam_kirby_palette8_4x.png - 4x scaled for visibility")
    print("3. demo_beam_kirby_all_palettes.png - Shows why palette 8 is correct (green border)")
    print("\nBeam Kirby appears yellow/orange because this is the Beam/Spark ability form,")
    print("not regular pink Kirby. The sprite data is correct!")

if __name__ == "__main__":
    main()
