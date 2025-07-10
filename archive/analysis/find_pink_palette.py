#!/usr/bin/env python3
"""
Find which palette contains pink colors for Kirby
"""

import sys

sys.path.append("sprite_editor")

from PIL import Image, ImageDraw

from sprite_editor.palette_utils import read_cgram_palette
from sprite_editor.sprite_editor_core import SpriteEditorCore


def main():
    print("=== Finding Pink Kirby Palette ===\n")

    cgram_file = "SnesCgRam.dmp"
    vram_file = "SnesVideoRam.VRAM.dmp"

    # Check all palettes for pink colors
    print("Analyzing all 16 palettes for pink colors:")

    pink_candidates = []

    for pal_num in range(16):
        palette = read_cgram_palette(cgram_file, pal_num)
        if palette:
            # Look for pink colors (high red, medium-high green/blue)
            has_pink = False
            pink_colors = []

            for i in range(1, 16):  # Skip transparent color 0
                if i * 3 + 2 < len(palette):
                    r = palette[i * 3]
                    g = palette[i * 3 + 1]
                    b = palette[i * 3 + 2]

                    # Check if this could be pink
                    if r > 200 and g > 100 and g < 220 and b > 100 and b < 220:
                        has_pink = True
                        pink_colors.append((i, r, g, b))

            if has_pink:
                pink_candidates.append(pal_num)
                print(f"\nPalette {pal_num} has pink colors:")
                for idx, r, g, b in pink_colors[:3]:
                    print(f"  Color {idx}: RGB({r}, {g}, {b})")

    print(f"\nPalettes with pink colors: {pink_candidates}")

    # Test these palettes on Kirby sprites
    core = SpriteEditorCore()
    img, _ = core.extract_sprites(vram_file, 0xC000, 0x400, tiles_per_row=8)

    # Create comparison of pink palette candidates
    comparison_images = []

    # Also test some other palettes that might work
    test_palettes = [*pink_candidates, 8, 9, 10, 11, 12, 13, 14, 15]
    test_palettes = list(set(test_palettes))[:12]  # Limit to 12 for grid

    for pal_num in test_palettes:
        palette = read_cgram_palette(cgram_file, pal_num)
        if palette:
            test_img = img.copy()
            test_img.putpalette(palette)

            scaled = test_img.resize((test_img.width * 2, test_img.height * 2),
                                   resample=Image.NEAREST)
            comparison_images.append((pal_num, scaled))

    # Create comparison grid
    if comparison_images:
        create_comparison_grid(comparison_images)

    # Also check the actual OAM assignments
    print("\nChecking actual palette assignments in OAM:")
    core.load_oam_mapping("SnesSpriteRam.OAM.dmp")

    # Try extracting with shifted palette indices
    print("\nTesting if there's a palette index offset...")
    test_palette_shift(core, vram_file, cgram_file)

def create_comparison_grid(images):
    """Create grid showing different palettes"""

    cols = 4
    rows = (len(images) + cols - 1) // cols

    cell_w = images[0][1].width
    cell_h = images[0][1].height
    padding = 10

    grid_w = cols * cell_w + (cols + 1) * padding
    grid_h = rows * cell_h + (rows + 1) * padding + 40

    grid = Image.new("RGB", (grid_w, grid_h), (32, 32, 32))
    draw = ImageDraw.Draw(grid)

    draw.text((grid_w // 2, 10), "Finding Pink Kirby - Which Palette?",
             fill=(255, 255, 255), anchor="mt")

    for idx, (pal_num, img) in enumerate(images):
        col = idx % cols
        row = idx // cols

        x = padding + col * (cell_w + padding)
        y = 30 + padding + row * (cell_h + padding)

        grid.paste(img, (x, y))

        draw.text((x + cell_w // 2, y + cell_h + 2),
                 f"Palette {pal_num}", fill=(255, 255, 255), anchor="mt")

    grid.save("find_pink_palette.png")
    print("\n✓ Created find_pink_palette.png")

def test_palette_shift(core, vram_file, cgram_file):
    """Test if palettes are shifted or remapped"""

    # Maybe the OAM palette indices don't directly map to CGRAM indices?
    # Try different mappings

    print("\nTesting palette remapping...")

    # Common SNES palette remappings
    remappings = [
        ("Direct", lambda x: x),
        ("Offset by 8", lambda x: (x + 8) % 16),
        ("Sprite palettes only", lambda x: x + 8 if x < 8 else x),
        ("Swapped", lambda x: x ^ 8),
    ]

    for name, remap_func in remappings[:2]:  # Test first two
        print(f"\nTrying {name} mapping...")

        # Manually extract and remap palettes
        img, _ = core.extract_sprites(vram_file, 0xC000, 0x200, tiles_per_row=8)

        # For sprites that should use palette 0, try the remapped palette
        remapped_pal = remap_func(0)
        palette = read_cgram_palette(cgram_file, remapped_pal)
        if palette:
            img.putpalette(palette)
            filename = f"test_remap_{name.lower().replace(' ', '_')}.png"
            img.save(filename)
            print(f"  Saved {filename} using palette {remapped_pal}")

if __name__ == "__main__":
    main()
