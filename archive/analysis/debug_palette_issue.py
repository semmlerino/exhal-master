#!/usr/bin/env python3
"""
Debug why P0 sprites don't look like palette 0
"""

import sys

sys.path.append("sprite_editor")

from PIL import Image, ImageDraw

from sprite_editor.palette_utils import read_cgram_palette
from sprite_editor.sprite_editor_core import SpriteEditorCore


def main():
    print("=== Debugging Palette 0 Issue ===\n")

    # Check what colors are actually in palette 0
    cgram_file = "SnesCgRam.dmp"
    vram_file = "SnesVideoRam.VRAM.dmp"

    print("Checking Palette 0 colors:")
    palette_0 = read_cgram_palette(cgram_file, 0)
    if palette_0:
        print("First 8 colors in Palette 0 (RGB):")
        for i in range(8):
            if i * 3 + 2 < len(palette_0):
                r = palette_0[i * 3]
                g = palette_0[i * 3 + 1]
                b = palette_0[i * 3 + 2]
                print(f"  Color {i}: ({r:3d}, {g:3d}, {b:3d})")

    # Check what's actually being displayed
    core = SpriteEditorCore()

    # Extract a small region and apply different palettes manually
    print("\nExtracting first few tiles and testing palettes...")

    img, _ = core.extract_sprites(vram_file, 0xC000, 0x200, tiles_per_row=8)

    # Save with different palettes
    test_palettes = [0, 1, 2, 3, 4, 5, 6, 7, 8]

    comparison_images = []

    for pal_num in test_palettes:
        palette = read_cgram_palette(cgram_file, pal_num)
        if palette:
            test_img = img.copy()
            test_img.putpalette(palette)

            # Check first few colors of this palette
            colors = []
            for i in range(3):
                if i * 3 + 2 < len(palette):
                    r = palette[i * 3]
                    g = palette[i * 3 + 1]
                    b = palette[i * 3 + 2]
                    colors.append(f"({r},{g},{b})")

            print(f"\nPalette {pal_num} colors: {', '.join(colors)}")

            # Scale for visibility
            scaled = test_img.resize((test_img.width * 3, test_img.height * 3),
                                   resample=Image.NEAREST)
            comparison_images.append((pal_num, scaled, colors))

    # Create comparison grid
    if comparison_images:
        create_debug_grid(comparison_images)

    # Also check if the OAM mapping is correct
    print("\nChecking OAM tile mapping...")
    from sprite_editor.oam_palette_mapper import OAMPaletteMapper
    mapper = OAMPaletteMapper()
    mapper.parse_oam_dump("SnesSpriteRam.OAM.dmp")

    print("\nFirst few sprites using Palette 0:")
    pal0_sprites = [s for s in mapper.oam_entries if s["palette"] == 0 and s["y"] < 224]
    for sprite in pal0_sprites[:5]:
        print(f"  Tile 0x{sprite['tile']:03X} at position ({sprite['x']}, {sprite['y']})")

    # Check if there's a palette offset issue
    print("\nTesting if palettes are offset...")
    core.load_oam_mapping("SnesSpriteRam.OAM.dmp")

    # Extract with OAM mapping and see what we get
    oam_img, _ = core.extract_sprites_with_correct_palettes(
        vram_file, 0xC000, 0x400, cgram_file, tiles_per_row=8
    )
    oam_img.save("debug_oam_extraction.png")

    # Also save what we get with manual palette 0
    manual_img, _ = core.extract_sprites(vram_file, 0xC000, 0x400, tiles_per_row=8)
    manual_pal0 = read_cgram_palette(cgram_file, 0)
    if manual_pal0:
        manual_img.putpalette(manual_pal0)
        manual_img.save("debug_manual_palette0.png")

def create_debug_grid(images):
    """Create a grid showing the palette tests"""

    cols = 3
    rows = (len(images) + cols - 1) // cols

    cell_w = images[0][1].width
    cell_h = images[0][1].height
    padding = 10

    grid_w = cols * cell_w + (cols + 1) * padding
    grid_h = rows * cell_h + (rows + 1) * padding + 80

    grid = Image.new("RGB", (grid_w, grid_h), (32, 32, 32))
    draw = ImageDraw.Draw(grid)

    draw.text((grid_w // 2, 10), "Palette Debug - Which Shows Pink Kirby?",
             fill=(255, 255, 255), anchor="mt")

    for idx, (pal_num, img, colors) in enumerate(images):
        col = idx % cols
        row = idx // cols

        x = padding + col * (cell_w + padding)
        y = 40 + padding + row * (cell_h + padding)

        grid.paste(img, (x, y))

        # Label with palette number and first color
        label = f"P{pal_num}"
        if colors:
            label += f"\n{colors[0]}"

        draw.text((x + cell_w // 2, y + cell_h + 5),
                 label, fill=(255, 255, 255), anchor="mt")

    grid.save("debug_palette_grid.png")
    print("\n✓ Created debug_palette_grid.png")

if __name__ == "__main__":
    main()
