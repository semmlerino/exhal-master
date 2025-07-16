#!/usr/bin/env python3
"""
Extract sprite palettes for the indexed pixel editor

This tool extracts individual palettes from CGRAM dumps and saves them
in a standardized format that the indexed pixel editor can load directly.
Creates .pal.json files that pair with grayscale sprite extractions.
"""

import argparse
import json
import os
from pathlib import Path
from typing import Any, Optional

from sprite_edit_helpers import parse_cgram


def extract_palette_for_editor(
    cgram_file: str, palette_index: int, output_file: Optional[str] = None
) -> dict[str, Any]:
    """
    Extract a specific 16-color palette from CGRAM for use in the indexed pixel editor.

    Args:
        cgram_file: Path to CGRAM dump file
        palette_index: Which palette to extract (0-15, typically 8-15 for sprites)
        output_file: Output .pal.json file path (auto-generated if None)

    Returns:
        Dictionary containing the palette data
    """

    # Parse all palettes from CGRAM
    palettes = parse_cgram(cgram_file)

    if palette_index < 0 or palette_index >= len(palettes):
        raise ValueError(
            f"Palette index {palette_index} out of range (0-{len(palettes)-1})"
        )

    # Get the specific palette
    palette_colors = palettes[palette_index]

    # Create palette data structure for the editor
    palette_data = {
        "format_version": "1.0",
        "format_description": "Indexed Pixel Editor Palette File",
        "source": {
            "cgram_file": os.path.abspath(cgram_file),
            "palette_index": palette_index,
            "extraction_tool": "extract_palette_for_editor.py",
        },
        "palette": {
            "name": f"CGRAM Palette {palette_index}",
            "colors": [
                list(color) for color in palette_colors
            ],  # Convert tuples to lists for JSON
            "color_count": len(palette_colors),
            "format": "RGB888",
        },
        "usage_hints": {
            "transparent_index": 0,
            "typical_use": "sprite" if palette_index >= 8 else "background",
            "kirby_palette": palette_index == 8,
        },
        "editor_compatibility": {
            "indexed_pixel_editor": True,
            "supports_grayscale_mode": True,
            "auto_loadable": True,
        },
    }

    # Generate output filename if not provided
    if output_file is None:
        cgram_stem = Path(cgram_file).stem
        output_file = f"{cgram_stem}_palette_{palette_index}.pal.json"

    # Ensure .pal.json extension
    if not output_file.endswith(".pal.json"):
        if output_file.endswith(".json"):
            output_file = output_file.replace(".json", ".pal.json")
        else:
            output_file += ".pal.json"

    # Save palette file
    with open(output_file, "w") as f:
        json.dump(palette_data, f, indent=2)

    return palette_data, output_file


def extract_all_sprite_palettes(
    cgram_file: str, output_dir: Optional[str] = None
) -> list[str]:
    """
    Extract all sprite palettes (8-15) from CGRAM file.

    Args:
        cgram_file: Path to CGRAM dump file
        output_dir: Directory to save palette files (uses same dir as cgram_file if None)

    Returns:
        List of created palette file paths
    """

    if output_dir is None:
        output_dir = Path(cgram_file).parent
    else:
        output_dir = Path(output_dir)
        output_dir.mkdir(exist_ok=True)

    created_files = []
    cgram_stem = Path(cgram_file).stem

    # Extract sprite palettes (8-15)
    for palette_idx in range(8, 16):
        output_file = output_dir / f"{cgram_stem}_palette_{palette_idx}.pal.json"

        try:
            palette_data, created_file = extract_palette_for_editor(
                cgram_file, palette_idx, str(output_file)
            )
            created_files.append(created_file)
            print(f"✓ Extracted palette {palette_idx}: {created_file}")

        except Exception as e:
            print(f"✗ Failed to extract palette {palette_idx}: {e}")

    return created_files


def create_kirby_palette_from_notes() -> dict[str, Any]:
    """
    Create Kirby's palette from the documented colors in SPRITE_EXTRACTION_NOTES.md
    This provides a fallback/reference palette when CGRAM data isn't available.
    """

    # Colors from SPRITE_EXTRACTION_NOTES.md
    kirby_colors = [
        [0, 0, 0],  # 0: Transparent/black
        [248, 224, 248],  # 1: Light pink (highlight)
        [248, 184, 232],  # 2: Pink (main body)
        [248, 144, 200],  # 3: Medium pink
        [240, 96, 152],  # 4: Dark pink (shadow)
        [192, 48, 104],  # 5: Deep pink/red (outline)
        [248, 248, 248],  # 6: White (eyes)
        [216, 216, 216],  # 7: Light gray
        [168, 168, 168],  # 8: Gray
        [120, 120, 120],  # 9: Dark gray
        [248, 144, 144],  # A: Light red/pink (cheeks)
        [248, 80, 80],  # B: Red (feet)
        [216, 0, 0],  # C: Dark red
        [144, 0, 0],  # D: Deep red
        [80, 0, 0],  # E: Very dark red
        [40, 0, 0],  # F: Black-red
    ]

    return {
        "format_version": "1.0",
        "format_description": "Indexed Pixel Editor Palette File",
        "source": {
            "cgram_file": "DOCUMENTED_REFERENCE",
            "palette_index": 8,
            "extraction_tool": "extract_palette_for_editor.py",
            "reference": "SPRITE_EXTRACTION_NOTES.md",
        },
        "palette": {
            "name": "Kirby Reference Palette",
            "colors": kirby_colors,
            "color_count": 16,
            "format": "RGB888",
        },
        "usage_hints": {
            "transparent_index": 0,
            "typical_use": "sprite",
            "kirby_palette": True,
        },
        "editor_compatibility": {
            "indexed_pixel_editor": True,
            "supports_grayscale_mode": True,
            "auto_loadable": True,
        },
    }


def create_reference_palette_file(output_file: str = "kirby_reference.pal.json"):
    """Create a reference Kirby palette file from documented colors"""

    palette_data = create_kirby_palette_from_notes()

    with open(output_file, "w") as f:
        json.dump(palette_data, f, indent=2)

    print(f"✓ Created reference Kirby palette: {output_file}")
    return output_file


def main():
    parser = argparse.ArgumentParser(
        description="Extract sprite palettes for the indexed pixel editor"
    )
    parser.add_argument("cgram_file", nargs="?", help="CGRAM dump file (.dmp)")
    parser.add_argument(
        "-p", "--palette", type=int, help="Extract specific palette index (0-15)"
    )
    parser.add_argument(
        "-a",
        "--all-sprites",
        action="store_true",
        help="Extract all sprite palettes (8-15)",
    )
    parser.add_argument("-o", "--output", help="Output file/directory")
    parser.add_argument(
        "--reference",
        action="store_true",
        help="Create reference Kirby palette from documented colors",
    )

    args = parser.parse_args()

    # Handle reference palette creation
    if args.reference:
        output_file = args.output if args.output else "kirby_reference.pal.json"
        create_reference_palette_file(output_file)
        return

    # Require CGRAM file for other operations
    if not args.cgram_file:
        print(
            "Error: CGRAM file required (or use --reference for documented Kirby palette)"
        )
        parser.print_help()
        return

    if not os.path.exists(args.cgram_file):
        print(f"Error: CGRAM file not found: {args.cgram_file}")
        return

    try:
        if args.all_sprites:
            # Extract all sprite palettes
            print(f"Extracting all sprite palettes from: {args.cgram_file}")
            created_files = extract_all_sprite_palettes(args.cgram_file, args.output)
            print(f"\n✓ Created {len(created_files)} palette files")

        elif args.palette is not None:
            # Extract specific palette
            print(f"Extracting palette {args.palette} from: {args.cgram_file}")
            palette_data, output_file = extract_palette_for_editor(
                args.cgram_file, args.palette, args.output
            )
            print(f"✓ Created palette file: {output_file}")

            # Show color preview
            print(f"\nPalette {args.palette} colors:")
            for i, color in enumerate(palette_data["palette"]["colors"]):
                r, g, b = color
                print(
                    f"  Index {i:2d}: RGB({r:3d},{g:3d},{b:3d}) #{r:02X}{g:02X}{b:02X}"
                )

        else:
            # Default: extract Kirby's palette (index 8)
            print(f"Extracting Kirby's palette (index 8) from: {args.cgram_file}")
            palette_data, output_file = extract_palette_for_editor(
                args.cgram_file, 8, args.output
            )
            print(f"✓ Created Kirby palette file: {output_file}")

    except Exception as e:
        print(f"Error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
