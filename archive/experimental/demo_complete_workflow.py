#!/usr/bin/env python3
"""
Demonstration of complete sprite editing workflow
Shows extraction -> editing -> validation -> reinsertion
"""

import os

from PIL import Image, ImageDraw

from sprite_edit_workflow import SpriteEditWorkflow
from sprite_sheet_editor import SpriteSheetEditor


def create_example_edit(tile_path):
    """Create a simple edit to demonstrate the workflow"""
    # Load tile
    img = Image.open(tile_path)

    # Add a simple modification - invert colors
    pixels = list(img.getdata())
    img.getpalette()

    # Create inverted version (keeping palette indices valid)
    for i in range(len(pixels)):
        if pixels[i] > 0 and pixels[i] < 15:  # Don't change transparent or last color
            pixels[i] = 15 - pixels[i]

    # Save edited version
    img.putdata(pixels)
    img.save(tile_path)

    return True

def demo_individual_workflow():
    """Demonstrate individual tile editing workflow"""
    print("=== Individual Tile Editing Workflow Demo ===\n")

    # Check for required files
    vram_file = "sync3_vram.dmp"
    cgram_file = "sync3_cgram.dmp"
    mappings_file = "final_palette_mapping.json"

    if not all(os.path.exists(f) for f in [vram_file, cgram_file]):
        print("ERROR: Required dump files not found!")
        print("Please ensure you have sync3_vram.dmp and sync3_cgram.dmp")
        return

    # Initialize workflow
    workflow = SpriteEditWorkflow(mappings_file if os.path.exists(mappings_file) else None)

    # Step 1: Extract sprites
    print("Step 1: Extracting sprites for editing...")
    edit_dir = "demo_edit_workspace"
    workflow.extract_for_editing(
        vram_file, cgram_file,
        offset=0xC000, size=0x1000,  # Extract first 128 tiles
        output_dir=edit_dir,
        tiles_per_row=16
    )

    print(f"\nExtracted tiles to: {edit_dir}")
    print("You can now edit individual PNG files in this directory")

    # Step 2: Simulate editing
    print("\nStep 2: Simulating edits...")
    edited_count = 0
    for filename in os.listdir(edit_dir):
        if filename.startswith("tile_") and filename.endswith(".png"):
            tile_path = os.path.join(edit_dir, filename)
            # Edit only first 5 tiles as demo
            if edited_count < 5 and create_example_edit(tile_path):
                print(f"  - Edited {filename}")
                edited_count += 1

    # Step 3: Validate
    print("\nStep 3: Validating edited sprites...")
    validation = workflow.validate_edited_sprites(edit_dir)

    # Step 4: Reinsert
    if validation["valid_tiles"]:
        print("\nStep 4: Reinserting sprites...")
        output_vram = workflow.reinsert_sprites(edit_dir, backup=True)
        print(f"\nWorkflow complete! Modified VRAM: {output_vram}")
    else:
        print("\nNo valid tiles to reinsert!")

def demo_sheet_workflow():
    """Demonstrate sprite sheet editing workflow"""
    print("\n\n=== Sprite Sheet Editing Workflow Demo ===\n")

    # Check for required files
    vram_file = "sync3_vram.dmp"
    cgram_file = "sync3_cgram.dmp"
    mappings_file = "final_palette_mapping.json"

    if not all(os.path.exists(f) for f in [vram_file, cgram_file]):
        print("ERROR: Required dump files not found!")
        return

    # Initialize editor
    editor = SpriteSheetEditor(mappings_file if os.path.exists(mappings_file) else None)

    # Step 1: Extract sheet
    print("Step 1: Extracting sprite sheet...")
    sheet_file = "demo_sprite_sheet.png"
    editor.extract_sheet_for_editing(
        vram_file, cgram_file,
        output_png=sheet_file
    )

    # Create editing guide
    editor.create_editing_guide(sheet_file)

    print(f"\nExtracted sprite sheet to: {sheet_file}")
    print(f"Editing guide: {sheet_file.replace('.png', '_editing_guide.png')}")

    # Step 2: Create example edit
    print("\nStep 2: Creating example edit...")
    sheet_img = Image.open(sheet_file)
    draw = ImageDraw.Draw(sheet_img)

    # Add some text overlay as example edit
    draw.text((10, 10), "EDITED", fill=(255, 0, 0, 255))

    edited_file = sheet_file.replace(".png", "_edited.png")
    sheet_img.save(edited_file)
    print(f"Created edited sheet: {edited_file}")

    # Step 3: Validate
    print("\nStep 3: Validating edited sheet...")
    editor.validate_edited_sheet(edited_file)

    # Step 4: Reinsert
    print("\nStep 4: Converting back to VRAM format...")
    output_vram = editor.reinsert_sheet(edited_file)

    if output_vram:
        print(f"\nSheet workflow complete! Modified VRAM: {output_vram}")

def print_workflow_guide():
    """Print a guide for manual editing"""
    print("\n\n=== Sprite Editing Workflow Guide ===\n")

    print("COMPLETE WORKFLOW:")
    print("1. Extract sprites with correct palettes")
    print("2. Edit sprites in your favorite image editor")
    print("3. Validate edits against SNES constraints")
    print("4. Reinsert edited sprites back to VRAM")
    print("5. Test in emulator\n")

    print("INDIVIDUAL TILE WORKFLOW:")
    print("python sprite_edit_workflow.py extract sync3_vram.dmp sync3_cgram.dmp -m final_palette_mapping.json")
    print("# Edit PNG files in extracted_sprites/")
    print("python sprite_edit_workflow.py validate extracted_sprites/")
    print("python sprite_edit_workflow.py reinsert extracted_sprites/\n")

    print("SPRITE SHEET WORKFLOW:")
    print("python sprite_sheet_editor.py extract sync3_vram.dmp sync3_cgram.dmp -m final_palette_mapping.json --guide")
    print("# Edit sprite_sheet.png in image editor")
    print("python sprite_sheet_editor.py validate sprite_sheet_edited.png")
    print("python sprite_sheet_editor.py reinsert sprite_sheet_edited.png\n")

    print("CONSTRAINTS TO REMEMBER:")
    print("- Each 8x8 tile can use only ONE palette")
    print("- Maximum 15 colors + transparent per tile")
    print("- Color index 0 is always transparent")
    print("- Use only colors from the assigned palette")
    print("- Save as indexed PNG to preserve palette")
    print("\nTIPS:")
    print("- Use the editing guide to see available colors")
    print("- Test frequently with validation")
    print("- Keep backups of original files")
    print("- Use the preview images to verify results")

def main():
    """Run the demonstration"""
    print("Kirby Super Star Sprite Editing Workflow Demo")
    print("=" * 50)

    # Run demos
    demo_individual_workflow()
    demo_sheet_workflow()
    print_workflow_guide()

    print("\n✓ Demo complete! You can now edit sprites and reinsert them.")
    print("  The modified VRAM files can be tested in your emulator.")

if __name__ == "__main__":
    main()
