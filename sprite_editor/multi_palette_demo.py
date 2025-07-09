#!/usr/bin/env python3
"""
Demo script showing the multi-palette functionality of the sprite editor.
Shows how sprites with different palettes in one sheet are properly handled.
"""

from sprite_editor_core import SpriteEditorCore


def demo_multi_palette():
    """Demonstrate the multi-palette functionality"""

    # Initialize the sprite editor
    core = SpriteEditorCore()

    # Load OAM data to map sprites to their correct palettes
    print("Loading OAM data...")
    if core.load_oam_mapping("OAM.dmp"):
        print("✓ OAM data loaded successfully")

        # Get palette usage statistics
        stats = core._get_active_palette_info()
        print(f"\nActive palettes found: {list(stats.keys())}")
        for pal_num, count in stats.items():
            print(f"  Palette {pal_num}: {count} sprites")
    else:
        print("✗ No OAM data available, will use default palette")

    print("\n--- Multi-Palette Extraction Methods ---")

    # Method 1: Extract sprites with OAM-correct palettes
    # Each tile uses its assigned palette from OAM data
    print("\n1. extract_sprites_with_correct_palettes():")
    print("   - Creates a single image where each tile uses its OAM-assigned palette")
    print("   - Perfect for seeing sprites as they appear in-game")

    # Method 2: Extract sprites with multiple palette previews
    # Shows the same sprites with different palettes
    print("\n2. extract_sprites_multi_palette():")
    print("   - Returns multiple images, one for each active palette")
    print("   - Includes an 'oam_correct' version if OAM data is available")
    print("   - Useful for seeing how sprites look with different palettes")

    # Method 3: Create palette grid preview
    # Shows all 16 palettes in a 4x4 grid
    print("\n3. create_palette_grid_preview():")
    print("   - Creates a 4x4 grid showing sprites with all 16 palettes")
    print("   - Active palettes (used by sprites) have green borders")
    print("   - Inactive palettes have gray borders")
    print("   - Each cell is labeled with palette number and usage count")

    print("\n--- Example Usage ---")
    print(
        """
# Extract sprites with correct palettes based on OAM
img, tiles = core.extract_sprites_with_correct_palettes(
    "VRAM.dmp", 0xC000, 0x4000, "CGRAM.dmp"
)
img.save("sprites_oam_correct.png")

# Get multiple palette versions
images, tiles = core.extract_sprites_multi_palette(
    "VRAM.dmp", 0xC000, 0x4000, "CGRAM.dmp"
)
for name, img in images.items():
    img.save(f"sprites_{name}.png")

# Create palette grid
grid, tiles = core.create_palette_grid_preview(
    "VRAM.dmp", 0xC000, 0x4000, "CGRAM.dmp"
)
grid.save("palette_grid.png")
"""
    )


if __name__ == "__main__":
    demo_multi_palette()
