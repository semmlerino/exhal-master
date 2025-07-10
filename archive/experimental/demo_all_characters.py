#!/usr/bin/env python3
"""
Extract and display all characters/enemies from VRAM with their correct palettes
Based on the documentation, different areas of VRAM contain different sprites
"""

import sys

sys.path.append("sprite_editor")

from PIL import Image, ImageDraw

from sprite_editor.palette_utils import read_cgram_palette
from sprite_editor.sprite_editor_core import SpriteEditorCore


def extract_vram_region(core, offset, size, name, tiles_per_row=16):
    """Extract a specific region of VRAM and return the base image"""
    print(f"\nExtracting {name} (offset: 0x{offset:04X}, size: 0x{size:04X})...")
    img, tiles = core.extract_sprites("VRAM.dmp", offset, size, tiles_per_row)
    print(f"  Found {tiles} tiles")
    return img, tiles

def create_palette_preview(base_img, palette_nums, name, output_name):
    """Create a preview showing sprites with specific palettes"""
    images = []

    for pal_num in palette_nums:
        palette = read_cgram_palette("CGRAM.dmp", pal_num)
        if palette:
            img = base_img.copy()
            img.putpalette(palette)
            images.append((pal_num, img))

    if not images:
        return

    # Create horizontal strip
    scale = 2
    img_height = images[0][1].height * scale
    img_width = images[0][1].width * scale
    total_width = len(images) * img_width + (len(images) + 1) * 10
    total_height = img_height + 60

    strip = Image.new("RGB", (total_width, total_height), (32, 32, 32))
    draw = ImageDraw.Draw(strip)

    # Title
    draw.text((total_width // 2, 5), name, fill=(255, 255, 255), anchor="mt")

    x = 10
    for pal_num, img in images:
        # Scale up
        scaled = img.resize((img_width, img_height), resample=Image.NEAREST)
        strip.paste(scaled, (x, 30))

        # Label
        label_x = x + img_width // 2
        label_y = 30 + img_height + 5
        draw.text((label_x, label_y), f"Palette {pal_num}", fill=(255, 255, 255), anchor="mt")

        x += img_width + 10

    strip.save(output_name)
    print(f"✓ Saved: {output_name}")

def main():
    core = SpriteEditorCore()

    print("=== Kirby Super Star - Complete Character Extraction ===")

    # Load OAM data
    print("\nLoading OAM data...")
    core.load_oam_mapping("OAM.dmp")
    palette_info = core._get_active_palette_info()
    print("Active palettes from OAM:", list(palette_info.keys()))

    # Based on documentation:
    # - Kirby (Beam): VRAM $6000 (0xC000), Palette 8
    # - Level Sprites/Enemies: VRAM $6800-$7000 (0xD000-0xE000)
    # - UI Elements: VRAM $7000+ (0xE000+)

    # 1. Beam Kirby (we already know this works)
    print("\n1. BEAM KIRBY")
    beam_kirby, _ = extract_vram_region(core, 0xC000, 0x1000, "Beam Kirby", 8)
    create_palette_preview(beam_kirby, [8], "Beam Kirby", "demo_char_beam_kirby.png")

    # 2. Enemies/Level sprites (after Kirby)
    print("\n2. ENEMIES AND LEVEL SPRITES")
    enemies, _ = extract_vram_region(core, 0xD000, 0x1000, "Enemies/Objects", 16)

    # According to docs, enemies use palettes 4, 5, 6
    create_palette_preview(enemies, [4, 5, 6], "Enemy Sprites", "demo_char_enemies.png")

    # 3. UI Elements
    print("\n3. UI ELEMENTS")
    ui, _ = extract_vram_region(core, 0xE000, 0x800, "UI Elements", 16)
    create_palette_preview(ui, [0, 2], "UI Elements", "demo_char_ui.png")

    # 4. Create a comprehensive view with OAM-correct palettes
    print("\n4. CREATING OAM-CORRECT FULL VIEW")

    # Extract larger region with OAM-correct palettes
    try:
        full_oam, _ = core.extract_sprites_with_correct_palettes(
            "VRAM.dmp", 0xC000, 0x4000, "CGRAM.dmp", tiles_per_row=16
        )
        full_oam.save("demo_char_full_oam_correct.png")

        # Create scaled version
        scaled = full_oam.resize((full_oam.width * 2, full_oam.height * 2), resample=Image.NEAREST)
        scaled.save("demo_char_full_oam_correct_2x.png")
        print("✓ Saved: demo_char_full_oam_correct.png and 2x version")
    except Exception as e:
        print(f"Error: {e}")

    # 5. Create individual character sheets
    print("\n5. EXTRACTING INDIVIDUAL CHARACTERS")

    # Extract specific character regions based on visual inspection
    character_regions = [
        (0xC000, 0x800, "Beam Kirby", [8], 8),      # First 64 tiles
        (0xC800, 0x400, "Kirby Effects", [8], 8),    # Effects/particles
        (0xD000, 0x400, "Enemy Set 1", [4], 8),      # Green/pink enemies
        (0xD400, 0x400, "Enemy Set 2", [5], 8),      # Blue/brown enemies
        (0xD800, 0x400, "Enemy Set 3", [6], 8),      # Purple enemies
        (0xE000, 0x400, "UI/Numbers", [0, 2], 16),  # UI elements
    ]

    for offset, size, name, palettes, tiles_per_row in character_regions:
        img, tiles = extract_vram_region(core, offset, size, name, tiles_per_row)

        for pal in palettes:
            palette = read_cgram_palette("CGRAM.dmp", pal)
            if palette:
                colored = img.copy()
                colored.putpalette(palette)
                filename = f"demo_char_{name.lower().replace(' ', '_').replace('/', '_')}_pal{pal}.png"
                colored.save(filename)

                # Create 4x version for main character
                if "kirby" in name.lower():
                    scaled = colored.resize((colored.width * 4, colored.height * 4), resample=Image.NEAREST)
                    scaled.save(filename.replace(".png", "_4x.png"))

    # 6. Create a summary grid showing different areas
    print("\n6. CREATING SUMMARY GRID")
    create_summary_grid()

    print("\n=== Extraction Complete! ===")
    print("\nFiles created:")
    print("- demo_char_beam_kirby.png - Beam Kirby with palette 8")
    print("- demo_char_enemies.png - Enemy sprites with palettes 4, 5, 6")
    print("- demo_char_ui.png - UI elements with palettes 0, 2")
    print("- demo_char_full_oam_correct.png - Full sheet with OAM-correct palettes")
    print("- Individual character files for each region")
    print("- demo_char_summary_grid.png - Overview of all characters")

def create_summary_grid():
    """Create a grid showing all the different character types"""
    core = SpriteEditorCore()

    # Define what to show in the grid
    grid_items = [
        (0xC000, 0x400, "Beam Kirby", 8, 8),
        (0xC800, 0x200, "Kirby Effects", 8, 8),
        (0xD000, 0x200, "Green Enemies", 4, 8),
        (0xD200, 0x200, "Pink Enemies", 4, 8),
        (0xD400, 0x200, "Blue Enemies", 5, 8),
        (0xD600, 0x200, "Brown Enemies", 5, 8),
        (0xD800, 0x200, "Purple Enemies", 6, 8),
        (0xDA00, 0x200, "Dark Enemies", 6, 8),
        (0xE000, 0x200, "UI Numbers", 0, 16),
        (0xE200, 0x200, "UI Elements", 2, 16),
        (0xE400, 0x200, "Effects 1", 7, 8),
        (0xE600, 0x200, "Effects 2", 9, 8),
    ]

    # Extract and color each region
    images = []
    for offset, size, name, pal_num, tiles_per_row in grid_items:
        try:
            img, _ = core.extract_sprites("VRAM.dmp", offset, size, tiles_per_row)
            palette = read_cgram_palette("CGRAM.dmp", pal_num)
            if palette:
                img.putpalette(palette)
            else:
                img.putpalette(core.get_grayscale_palette())

            # Crop to consistent size
            cropped = img.crop((0, 0, min(img.width, 64), min(img.height, 32)))
            scaled = cropped.resize((128, 64), resample=Image.NEAREST)
            images.append((name, scaled, pal_num))
        except Exception as e:
            print(f"  Could not extract {name}: {e}")

    # Create grid
    if images:
        cols = 4
        rows = (len(images) + cols - 1) // cols
        cell_w = 128
        cell_h = 64
        padding = 10
        label_h = 20

        grid_w = cols * cell_w + (cols + 1) * padding
        grid_h = rows * (cell_h + label_h) + (rows + 1) * padding + 30

        grid = Image.new("RGB", (grid_w, grid_h), (32, 32, 32))
        draw = ImageDraw.Draw(grid)

        # Title
        draw.text((grid_w // 2, 10), "Kirby Super Star - Character Overview",
                 fill=(255, 255, 255), anchor="mt")

        # Place images
        for idx, (name, img, pal_num) in enumerate(images):
            col = idx % cols
            row = idx // cols

            x = padding + col * (cell_w + padding)
            y = 40 + padding + row * (cell_h + label_h + padding)

            grid.paste(img, (x, y))

            # Label
            label = f"{name} (P{pal_num})"
            draw.text((x + cell_w // 2, y + cell_h + 2), label,
                     fill=(255, 255, 255), anchor="mt")

        grid.save("demo_char_summary_grid.png")
        print("✓ Created character summary grid")

if __name__ == "__main__":
    main()
