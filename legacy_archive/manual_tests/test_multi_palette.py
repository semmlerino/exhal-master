#!/usr/bin/env python3
"""
Test script for multi-palette preview functionality
"""

import os
import sys

from sprite_editor_core import SpriteEditorCore


def test_multi_palette_extraction():
    """Test the multi-palette extraction functionality"""

    print("Testing Multi-Palette Preview System")
    print("="*50)

    # Initialize core
    core = SpriteEditorCore()

    # Test files
    vram_file = "VRAM.dmp"
    cgram_file = "CGRAM.dmp"
    oam_file = "OAM.dmp"

    # Check files exist
    for file in [vram_file, cgram_file, oam_file]:
        if not os.path.exists(file):
            print(f"Error: {file} not found")
            return False

    print("✓ All required files found")

    # Load OAM mapping
    print("\nLoading OAM data...")
    if core.load_oam_mapping(oam_file):
        print("✓ OAM data loaded successfully")

        # Get statistics
        stats = core.oam_mapper.get_palette_usage_stats()
        print(f"  Active palettes: {stats['active_palettes']}")
        print(f"  Total sprites: {stats['total_sprites']}")
        print(f"  Visible sprites: {stats['visible_sprites']}")
    else:
        print("✗ Failed to load OAM data")
        return False

    # Test multi-palette extraction
    print("\nTesting multi-palette extraction...")
    try:
        palette_images, total_tiles = core.extract_sprites_multi_palette(
            vram_file, 0xC000, 0x4000, cgram_file
        )

        print(f"✓ Extracted {len(palette_images)} palette variations")
        print(f"  Total tiles: {total_tiles}")

        for key in palette_images:
            print(f"  - {key}")
    except Exception as e:
        print(f"✗ Multi-palette extraction failed: {e}")
        return False

    # Test correct palette extraction
    print("\nTesting OAM-correct palette extraction...")
    try:
        correct_img, total_tiles = core.extract_sprites_with_correct_palettes(
            vram_file, 0xC000, 0x4000, cgram_file
        )

        print("✓ Extracted sprites with OAM-assigned palettes")
        print(f"  Image size: {correct_img.width}x{correct_img.height}")
        print(f"  Total tiles: {total_tiles}")

        # Save test output
        correct_img.save("test_oam_correct_palettes.png")
        print("  Saved to: test_oam_correct_palettes.png")

    except Exception as e:
        print(f"✗ OAM-correct extraction failed: {e}")
        return False

    # Test palette grid
    print("\nTesting palette grid generation...")
    try:
        grid_img, total_tiles = core.create_palette_grid_preview(
            vram_file, 0xC000, 0x4000, cgram_file
        )

        print("✓ Created palette grid preview")
        print(f"  Grid size: {grid_img.width}x{grid_img.height}")

        # Save test output
        grid_img.save("test_palette_grid.png")
        print("  Saved to: test_palette_grid.png")

    except Exception as e:
        print(f"✗ Palette grid generation failed: {e}")
        return False

    print("\n✓ All tests passed!")
    return True

if __name__ == "__main__":
    success = test_multi_palette_extraction()
    sys.exit(0 if success else 1)
