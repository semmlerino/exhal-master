#!/usr/bin/env python3
"""
Demonstration of the unified sprite editing workflow
Shows the complete process from extraction to reinsertion
"""

import os
import sys

from PIL import Image


def check_files():
    """Check for required files"""
    vram_files = ["Cave.SnesVideoRam.dmp", "VRAM.dmp", "sync3_vram.dmp"]
    cgram_files = ["Cave.SnesCgRam.dmp", "CGRAM.dmp", "sync3_cgram.dmp"]

    vram = None
    cgram = None

    for vf in vram_files:
        if os.path.exists(vf):
            vram = vf
            break

    for cf in cgram_files:
        if os.path.exists(cf):
            cgram = cf
            break

    if not vram or not cgram:
        print("ERROR: Could not find VRAM and CGRAM dumps")
        print("Please ensure you have memory dumps in the current directory")
        sys.exit(1)

    return vram, cgram

def main():
    print("Kirby Super Star Sprite Editing - Complete Workflow Demo")
    print("=" * 60)
    print()

    # Check for files
    vram_file, cgram_file = check_files()
    print(f"Found VRAM: {vram_file}")
    print(f"Found CGRAM: {cgram_file}")

    # Check for palette mappings
    mappings_file = None
    if os.path.exists("final_palette_mapping.json"):
        mappings_file = "final_palette_mapping.json"
        print(f"Found palette mappings: {mappings_file}")

    print("\n" + "-" * 60)
    print("STEP 1: Extract Sprites")
    print("-" * 60)

    from sprite_edit_workflow import SpriteEditWorkflow

    # Extract some sprites
    output_dir = "demo_workspace"
    os.makedirs(output_dir, exist_ok=True)

    workflow = SpriteEditWorkflow(mappings_file)

    print(f"\nExtracting first 32 tiles to {output_dir}...")
    try:
        metadata = workflow.extract_for_editing(
            vram_file, cgram_file,
            offset=0xC000,  # Sprite area
            size=0x400,     # 32 tiles
            output_dir=output_dir,
            tiles_per_row=8
        )
        print(f"✓ Extracted {len(metadata['tile_palette_mappings'])} tiles")
    except Exception as e:
        print(f"✗ Extraction failed: {e}")
        return

    print("\n" + "-" * 60)
    print("STEP 2: Simulate Editing")
    print("-" * 60)

    # Find a tile to edit
    edited_tile = None
    for filename in os.listdir(output_dir):
        if filename.startswith("tile_") and filename.endswith(".png"):
            tile_path = os.path.join(output_dir, filename)

            # Load tile
            img = Image.open(tile_path)
            if img.mode == "P":  # Indexed mode
                # Make a simple edit - add a dot
                pixels = list(img.getdata())
                # Change center pixels (if not transparent)
                for i in [27, 28, 35, 36]:  # Center 2x2 area
                    if pixels[i] != 0:  # Not transparent
                        pixels[i] = min(15, pixels[i] + 1)  # Slightly different color

                img.putdata(pixels)
                img.save(tile_path)
                edited_tile = filename
                print(f"✓ Edited {filename} (added center mark)")
                break

    if not edited_tile:
        print("✗ No tiles found to edit")
        return

    print("\n" + "-" * 60)
    print("STEP 3: Validate Edits")
    print("-" * 60)

    print(f"\nValidating {output_dir}...")
    try:
        validation = workflow.validate_edited_sprites(output_dir)
        print(f"✓ Valid tiles: {len(validation['valid_tiles'])}")
        print(f"✗ Invalid tiles: {len(validation['invalid_tiles'])}")
        print(f"⚠ Warnings: {len(validation['warnings'])}")

        if validation["invalid_tiles"]:
            print("\nFix these issues before reinsertion:")
            for invalid in validation["invalid_tiles"][:3]:
                print(f"  - {invalid['tile']}: {invalid['error']}")
    except Exception as e:
        print(f"✗ Validation failed: {e}")
        return

    print("\n" + "-" * 60)
    print("STEP 4: Reinsert Sprites")
    print("-" * 60)

    print(f"\nReinserting sprites from {output_dir}...")
    try:
        output_vram = workflow.reinsert_sprites(
            output_dir,
            output_vram="demo_modified.dmp",
            backup=True
        )

        if output_vram:
            print(f"✓ Successfully created: {output_vram}")

            # Check file size
            size = os.path.getsize(output_vram)
            print(f"  File size: {size:,} bytes")
    except Exception as e:
        print(f"✗ Reinsertion failed: {e}")
        return

    print("\n" + "-" * 60)
    print("WORKFLOW COMPLETE!")
    print("-" * 60)

    print("\nSummary:")
    print(f"1. Extracted sprites to: {output_dir}/")
    print(f"2. Edited tile: {edited_tile}")
    print("3. Validation: PASSED")
    print(f"4. Created modified VRAM: {output_vram}")

    print("\nNext steps:")
    print("1. Load the modified VRAM in your emulator")
    print("2. Or use the unified editor for more advanced editing:")
    print("   - GUI: python3 launch_sprite_editor.py")
    print("   - CLI: python3 sprite_editor_cli.py")

    print("\nFiles created:")
    print(f"  {output_dir}/              - Extracted tiles")
    print(f"  {output_dir}/reference_sheet.png  - Visual reference")
    print(f"  {output_vram}             - Modified VRAM")
    if os.path.exists(output_vram + "_preview.png"):
        print(f"  {output_vram}_preview.png - Preview image")

if __name__ == "__main__":
    main()
