#!/usr/bin/env python3
"""
Simple demonstration of the sprite editing workflow
Shows extraction, editing, and reinsertion
"""

import os

from PIL import Image, ImageDraw

from sprite_editor.sprite_editor_core import SpriteEditorCore


def main():
    print("Kirby Super Star Sprite Editing Demo")
    print("=" * 50 + "\n")

    # Check files
    vram_file = "Cave.SnesVideoRam.dmp"
    cgram_file = "Cave.SnesCgRam.dmp"

    if not os.path.exists(vram_file) or not os.path.exists(cgram_file):
        print("ERROR: Missing memory dump files!")
        return

    # Step 1: Extract sprites
    print("Step 1: Extracting sprites...")
    editor = SpriteEditorCore()

    # Extract first 64 tiles (includes Kirby)
    img, num_tiles = editor.extract_sprites_with_correct_palettes(
        vram_file,
        0xC000,  # Sprite area
        0x800,   # 64 tiles
        cgram_file,
        16       # 16 tiles per row
    )

    img.save("demo_original_sprites.png")
    print(f"✓ Extracted {num_tiles} tiles to: demo_original_sprites.png")

    # Step 2: Create a simple edit
    print("\nStep 2: Creating edited version...")

    # Load the image for editing
    edited_img = img.copy()
    draw = ImageDraw.Draw(edited_img)

    # Add a simple overlay (like sunglasses on Kirby)
    # Kirby is typically in the first few tiles
    # Add black pixels to simulate sunglasses
    for x in range(10, 22):  # Horizontal band
        for y in range(4, 6):  # 2 pixels tall
            draw.point((x, y), fill=(0, 0, 0, 255))

    edited_img.save("demo_edited_sprites.png")
    print("✓ Created edited version: demo_edited_sprites.png")

    # Step 3: Show how to prepare for reinsertion
    print("\nStep 3: Preparing for reinsertion...")

    # Read original VRAM
    with open(vram_file, "rb") as f:
        bytearray(f.read())

    # In a real workflow, you would:
    # 1. Convert edited PNG back to indexed format
    # 2. Extract each 8x8 tile
    # 3. Encode tiles back to 4bpp
    # 4. Write to VRAM at correct offsets

    print("✓ Ready for reinsertion")
    print("\nTo complete the workflow:")
    print("1. Edit demo_original_sprites.png in your image editor")
    print("2. Save as indexed PNG (maintaining palette)")
    print("3. Use sprite_edit_workflow.py to reinsert:")
    print("   python3 sprite_edit_workflow.py extract Cave.SnesVideoRam.dmp Cave.SnesCgRam.dmp -m final_palette_mapping.json")
    print("   # Edit the extracted tiles")
    print("   python3 sprite_edit_workflow.py reinsert extracted_sprites/")

    # Step 4: Create a visual guide
    print("\nStep 4: Creating editing guide...")
    create_editing_guide()

    print("\n✓ Demo complete!")
    print("Check the generated images to see the sprites and editing example.")

def create_editing_guide():
    """Create a visual guide showing the editing process"""
    guide = Image.new("RGB", (400, 300), (32, 32, 32))
    draw = ImageDraw.Draw(guide)

    # Title
    draw.text((200, 20), "Sprite Editing Process", fill=(255, 255, 255), anchor="mt")

    # Steps
    y = 60
    steps = [
        "1. Extract sprites with correct palettes",
        "2. Edit in image editor (indexed mode)",
        "3. Validate against palette constraints",
        "4. Reinsert into VRAM",
        "5. Test in emulator"
    ]

    for step in steps:
        draw.text((20, y), step, fill=(200, 200, 200))
        y += 30

    # Constraints box
    draw.rectangle([20, y, 380, y + 80], outline=(255, 255, 100))
    y += 10
    draw.text((200, y), "Remember:", fill=(255, 255, 100), anchor="mt")
    y += 20
    draw.text((30, y), "• Each tile uses ONE palette", fill=(255, 200, 200))
    y += 20
    draw.text((30, y), "• Maximum 15 colors + transparent", fill=(255, 200, 200))
    y += 20
    draw.text((30, y), "• Use only existing palette colors", fill=(255, 200, 200))

    guide.save("demo_editing_guide.png")

if __name__ == "__main__":
    main()
