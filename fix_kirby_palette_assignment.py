#!/usr/bin/env python3
"""
Fix Kirby palette assignment based on OAM analysis.

The issue: Kirby appears blue with palette 14 but should be pink with palette 8.
According to OAM analysis, Kirby uses OAM palette 0 (CGRAM palette 8).
"""

import json
import os
import shutil

from sprite_edit_helpers import parse_cgram


def fix_companion_palette(grayscale_png, correct_palette_idx=8):
    """Fix the companion palette file to use the correct Kirby palette"""

    # Get associated files
    metadata_file = grayscale_png.replace(".png", "_metadata.json")
    palette_file = grayscale_png.replace(".png", ".pal.json")

    if not os.path.exists(metadata_file):
        print(f"Error: Metadata file not found: {metadata_file}")
        return False

    # Load metadata
    with open(metadata_file) as f:
        metadata = json.load(f)

    cgram_file = metadata.get("source_cgram")
    if not cgram_file or not os.path.exists(cgram_file):
        print(f"Error: CGRAM file not found: {cgram_file}")
        return False

    # Parse palettes
    palettes = parse_cgram(cgram_file)

    # Create corrected palette data
    palette_colors = palettes[correct_palette_idx]

    palette_data = {
        "format_version": "1.0",
        "format_description": "Indexed Pixel Editor Palette File",
        "source": {
            "cgram_file": cgram_file,
            "palette_index": correct_palette_idx,
            "extraction_tool": "fix_kirby_palette_assignment.py",
            "companion_image": os.path.basename(grayscale_png),
            "fix_reason": "Corrected from palette 14 to palette 8 based on OAM analysis"
        },
        "palette": {
            "name": f"Kirby Sprite Palette {correct_palette_idx} (Corrected)",
            "colors": [list(color) for color in palette_colors],
            "color_count": len(palette_colors),
            "format": "RGB888"
        },
        "usage_hints": {
            "transparent_index": 0,
            "typical_use": "sprite",
            "kirby_palette": True,
            "oam_palette": 0,  # OAM palette 0 = CGRAM palette 8
            "extraction_mode": "grayscale_companion",
            "verified_by_oam": True
        },
        "editor_compatibility": {
            "indexed_pixel_editor": True,
            "supports_grayscale_mode": True,
            "auto_loadable": True,
            "companion_to": os.path.basename(grayscale_png)
        },
        "oam_analysis": {
            "kirby_tiles": {
                "primary": "0x00-0x1F use OAM palette 0 (CGRAM palette 8)",
                "powerup": "Some tiles use OAM palette 4 (CGRAM palette 12) for power-up states"
            }
        }
    }

    # Backup old palette file if it exists
    if os.path.exists(palette_file):
        backup_file = palette_file.replace(".pal.json", "_backup_pal14.pal.json")
        shutil.copy2(palette_file, backup_file)
        print(f"Backed up old palette to: {backup_file}")

    # Save corrected palette
    with open(palette_file, "w") as f:
        json.dump(palette_data, f, indent=2)

    print(f"Fixed companion palette file: {palette_file}")
    print(f"Changed from palette 14 to palette {correct_palette_idx}")
    print("\nPalette colors comparison:")

    # Show color comparison
    pal14_colors = palettes[14]
    pal8_colors = palettes[correct_palette_idx]

    print("\nPalette 14 (incorrect - shows blue):")
    for i, color in enumerate(pal14_colors[:8]):
        print(f"  Index {i}: RGB({color[0]:3}, {color[1]:3}, {color[2]:3})")

    print(f"\nPalette {correct_palette_idx} (correct - shows pink/purple):")
    for i, color in enumerate(pal8_colors[:8]):
        print(f"  Index {i}: RGB({color[0]:3}, {color[1]:3}, {color[2]:3})")

    return True

def create_oam_based_palette_mapping():
    """Create a palette mapping file based on OAM analysis"""

    # Based on the OAM analysis findings
    oam_palette_mapping = {
        "format_version": "1.0",
        "description": "OAM-based palette mapping for Kirby sprites",
        "source": "OAM analysis from multiple dump files",
        "mappings": {
            "kirby_normal": {
                "oam_palette": 0,
                "cgram_palette": 8,
                "tiles": ["0x00-0x1F", "0x64-0x67", "0x74"],
                "description": "Normal Kirby sprites (pink/purple)"
            },
            "kirby_powerup": {
                "oam_palette": 4,
                "cgram_palette": 12,
                "tiles": ["0x23", "0x24", "0x33"],
                "description": "Kirby with power-up or transformed state"
            },
            "effects": {
                "oam_palette": 6,
                "cgram_palette": 14,
                "tiles": ["0x19", "0x3C"],
                "description": "Effects and UI elements"
            }
        },
        "recommendations": {
            "default_kirby_palette": 8,
            "reason": "OAM analysis shows Kirby primarily uses OAM palette 0 (CGRAM 8)"
        }
    }

    output_file = "oam_based_palette_mapping.json"
    with open(output_file, "w") as f:
        json.dump(oam_palette_mapping, f, indent=2)

    print(f"Created OAM-based palette mapping: {output_file}")

if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        # Fix specific grayscale PNG
        grayscale_png = sys.argv[1]
        if os.path.exists(grayscale_png):
            fix_companion_palette(grayscale_png)
        else:
            print(f"File not found: {grayscale_png}")
    else:
        # Fix known problematic files
        problem_files = [
            "kirby_sprites_grayscale_ultrathink.png",
            "kirby_sprites_grayscale_fixed.png",
            "kirby_focused_test.png"
        ]

        for png_file in problem_files:
            if os.path.exists(png_file):
                print(f"\nFixing {png_file}...")
                fix_companion_palette(png_file)

        # Also create the OAM mapping reference
        create_oam_based_palette_mapping()

        print("\n✅ Palette assignment fix complete!")
        print("\nThe issue was:")
        print("- Kirby was being assigned palette 14 (which has blue colors)")
        print("- OAM analysis shows Kirby actually uses palette 8 (purple/pink)")
        print("- The color detection logic was failing due to palette 14's pink having high green values")
        print("\nNow Kirby should appear with correct pink/purple colors when using palette 8!")
