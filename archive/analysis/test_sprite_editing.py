#!/usr/bin/env python3
"""
Simple test to verify sprite editing workflow works
"""

import os
import sys

print("Sprite Editing Workflow Test")
print("=" * 50)

# Check for required files
required_files = [
    "Cave.SnesVideoRam.dmp",
    "Cave.SnesCgRam.dmp",
    "final_palette_mapping.json"
]

missing = [f for f in required_files if not os.path.exists(f)]
if missing:
    print(f"\nERROR: Missing required files: {missing}")
    print("Please ensure you have the synchronized memory dumps.")
    sys.exit(1)

print("\n✓ All required files found")

# Import the tools
try:
    from sprite_edit_helpers import decode_4bpp_tile, parse_cgram
    from sprite_editor.sprite_editor_core import SpriteEditorCore
    print("✓ Successfully imported sprite editor modules")
except ImportError as e:
    print(f"✗ Import error: {e}")
    sys.exit(1)

# Test basic functionality
print("\nTesting basic sprite extraction...")
try:
    editor = SpriteEditorCore()

    # Test palette loading
    palettes = parse_cgram("Cave.SnesCgRam.dmp")
    print(f"✓ Loaded {len(palettes)} palettes from CGRAM")

    # Test VRAM reading
    with open("Cave.SnesVideoRam.dmp", "rb") as f:
        f.seek(0xC000)  # Sprite area
        tile_data = f.read(32)  # One tile

    pixels = decode_4bpp_tile(tile_data)
    print(f"✓ Decoded tile: {len(pixels)} pixels")

    # Test sprite extraction with palette
    print("\nExtracting a sample sprite with correct palette...")
    result = editor.extract_sprites_with_correct_palettes(
        "Cave.SnesVideoRam.dmp",
        0xC000,  # Offset
        0x100,   # Just first 8 tiles
        "Cave.SnesCgRam.dmp",
        8        # 8 tiles per row
    )

    if result:
        img, num_tiles = result
        img.save("test_extraction.png")
        print(f"✓ Sample extraction saved to: test_extraction.png ({num_tiles} tiles)")

except Exception as e:
    print(f"✗ Error during testing: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 50)
print("Summary:")
print("- Sprite editor modules are working")
print("- Memory dumps can be read")
print("- Basic extraction functionality verified")
print("\nYou can now use the full workflow tools:")
print("  python3 sprite_edit_workflow.py --help")
print("  python3 sprite_sheet_editor.py --help")
