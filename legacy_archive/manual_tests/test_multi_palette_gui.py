#!/usr/bin/env python3
"""
Quick test of the multi-palette GUI with better visibility
"""

import os

from PIL import Image
from sprite_editor_core import SpriteEditorCore


def test_focused_extraction():
    """Test extracting just Kirby sprites for better visibility"""

    print("Testing focused sprite extraction for multi-palette preview")
    print("="*60)

    core = SpriteEditorCore()

    # Load OAM if available
    if os.path.exists("OAM.dmp"):
        core.load_oam_mapping("OAM.dmp")
        print("✓ Loaded OAM mapping")

    # Extract just the first 64 tiles (where Kirby is)
    # This is 2KB instead of 16KB
    vram_file = "VRAM.dmp"
    cgram_file = "CGRAM.dmp"
    offset = 0xC000  # Kirby sprites location

    # Test different sizes
    test_sizes = [32, 64, 128]  # tiles

    for num_tiles in test_sizes:
        size = num_tiles * 32  # bytes
        tiles_per_row = 8  # Narrower layout

        print(f"\nExtracting {num_tiles} tiles ({size} bytes)...")

        try:
            # Extract sprites
            img, total = core.extract_sprites(vram_file, offset, size, tiles_per_row)
            print(f"  Image size: {img.width}x{img.height} pixels")

            # Apply palette 8 (Kirby's palette)
            if os.path.exists(cgram_file):
                palette = core.read_cgram_palette(cgram_file, 8)
                if palette:
                    img.putpalette(palette)

            # Save preview
            filename = f"preview_{num_tiles}_tiles.png"
            img.save(filename)
            print(f"  Saved: {filename}")

            # Also create a 2x zoom version for clarity
            img_2x = img.resize((img.width * 2, img.height * 2), Image.Resampling.NEAREST)
            img_2x.save(f"preview_{num_tiles}_tiles_2x.png")

        except Exception as e:
            print(f"  Error: {e}")

    # Create a palette grid with just 64 tiles
    print("\nCreating focused palette grid...")
    try:
        grid_img, total = core.create_palette_grid_preview(
            vram_file, offset, 64 * 32, cgram_file, tiles_per_row=8
        )

        # Save at different scales
        grid_img.save("palette_grid_focused.png")
        print(f"✓ Saved palette_grid_focused.png ({grid_img.width}x{grid_img.height})")

    except Exception as e:
        print(f"✗ Error: {e}")

if __name__ == "__main__":
    test_focused_extraction()
