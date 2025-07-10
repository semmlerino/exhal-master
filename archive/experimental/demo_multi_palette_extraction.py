#!/usr/bin/env python3
"""
Demonstration of multi-palette sprite extraction from Kirby Super Star
Shows how different sprites in the same sheet have different palettes
"""

import sys

sys.path.append("sprite_editor")

from sprite_editor.sprite_editor_core import SpriteEditorCore


def main():
    # Initialize sprite editor
    core = SpriteEditorCore()

    print("=== Kirby Super Star Multi-Palette Sprite Extraction Demo ===\n")

    # Step 1: Load OAM data to understand sprite-to-palette mappings
    print("Step 1: Loading OAM data to map sprites to palettes...")
    if core.load_oam_mapping("OAM.dmp"):
        print("✓ OAM data loaded successfully")

        # Show palette usage statistics
        palette_info = core._get_active_palette_info()
        print("\nActive palettes found in OAM data:")
        for pal_num, count in sorted(palette_info.items()):
            print(f"  Palette {pal_num}: {count} sprites")
    else:
        print("✗ Failed to load OAM data")
        return

    # Step 2: Extract sprites with OAM-correct palettes
    print("\nStep 2: Extracting sprites with OAM-correct palettes...")
    print("This creates a single image where each tile uses its assigned palette from OAM")

    try:
        img, tiles = core.extract_sprites_with_correct_palettes(
            "VRAM.dmp", 0xC000, 0x4000, "CGRAM.dmp", tiles_per_row=16
        )
        img.save("demo_oam_correct_palettes.png")
        print(f"✓ Saved: demo_oam_correct_palettes.png ({tiles} tiles)")
    except Exception as e:
        print(f"✗ Error: {e}")

    # Step 3: Extract sprites with multiple palette versions
    print("\nStep 3: Creating multiple palette versions...")
    print("This shows the same sprites with different palettes")

    try:
        images, tiles = core.extract_sprites_multi_palette(
            "VRAM.dmp", 0xC000, 0x4000, "CGRAM.dmp", tiles_per_row=16
        )

        print(f"Generated {len(images)} palette versions:")
        for name, img in images.items():
            filename = f"demo_{name}.png"
            img.save(filename)
            print(f"  ✓ {filename}")
    except Exception as e:
        print(f"✗ Error: {e}")

    # Step 4: Create palette grid preview
    print("\nStep 4: Creating 4x4 palette grid preview...")
    print("This shows all 16 palettes with active ones highlighted")

    try:
        grid, tiles = core.create_palette_grid_preview(
            "VRAM.dmp", 0xC000, 0x2000, "CGRAM.dmp", tiles_per_row=8  # Smaller size for clarity
        )
        grid.save("demo_palette_grid.png")
        print("✓ Saved: demo_palette_grid.png")
        print("  - Green borders = Active palettes (used by sprites)")
        print("  - Gray borders = Inactive palettes")
        print("  - Labels show palette number and usage count")
    except Exception as e:
        print(f"✗ Error: {e}")

    # Step 5: Extract specific character sprites (Kirby)
    print("\nStep 5: Extracting just Kirby sprites (first 64 tiles)...")

    try:
        # Extract just the first 64 tiles (Kirby area)
        img, tiles = core.extract_sprites_with_correct_palettes(
            "VRAM.dmp", 0xC000, 0x800, "CGRAM.dmp", tiles_per_row=8
        )
        img.save("demo_kirby_only.png")
        print(f"✓ Saved: demo_kirby_only.png ({tiles} tiles)")

        # Also create versions with individual palettes
        images, _ = core.extract_sprites_multi_palette(
            "VRAM.dmp", 0xC000, 0x800, "CGRAM.dmp", tiles_per_row=8
        )

        # Save just the OAM-correct version at 4x scale for visibility
        if "oam_correct" in images:
            scaled = images["oam_correct"].resize(
                (images["oam_correct"].width * 4, images["oam_correct"].height * 4),
                resample=0  # Nearest neighbor for pixel art
            )
            scaled.save("demo_kirby_only_4x.png")
            print("✓ Saved: demo_kirby_only_4x.png (4x scaled)")
    except Exception as e:
        print(f"✗ Error: {e}")

    print("\n=== Demo Complete ===")
    print("\nFiles created:")
    print("1. demo_oam_correct_palettes.png - Full sprite sheet with correct palettes")
    print("2. demo_palette_*.png - Individual palette versions")
    print("3. demo_oam_correct.png - OAM-based correct palette version")
    print("4. demo_palette_grid.png - 4x4 grid showing all palettes")
    print("5. demo_kirby_only.png - Just Kirby sprites")
    print("6. demo_kirby_only_4x.png - Kirby sprites at 4x scale")

    print("\nKey observations:")
    print("- Different sprites use different palettes (e.g., Kirby vs enemies)")
    print("- The OAM data correctly maps each sprite to its intended palette")
    print("- The palette grid shows which palettes are actively used")

if __name__ == "__main__":
    main()
