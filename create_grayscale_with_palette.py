#!/usr/bin/env python3
"""
Create Grayscale Sprite with Palette Information
Generates grayscale sprite PNG with companion .pal.json file for pixel editor

Usage:
    python3 create_grayscale_with_palette.py [options]

Creates both:
    - Grayscale sprite in indexed color mode
    - Companion .pal.json file with correct palette
    - Files named for auto-loading in pixel editor
"""

import argparse
import os
import subprocess
import sys


def run_command(cmd, description=""):
    """Run a command and capture output"""
    print(f"Running: {description}")
    print(f"Command: {' '.join(cmd)}")

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        if result.stdout:
            print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error: {e}")
        if e.stderr:
            print(f"stderr: {e.stderr}")
        return False


def create_grayscale_with_palette(
    vram_file,
    cgram_file,
    output_name,
    palette_index=8,
    offset=0xC000,
    tile_count=64,
    tiles_per_row=8,
):
    """
    Create grayscale sprite with companion palette file

    Args:
        vram_file: Path to VRAM dump file
        cgram_file: Path to CGRAM dump file
        output_name: Base name for output files (without extension)
        palette_index: Which palette to extract (default 8 for Kirby)
        offset: VRAM offset in bytes (default 0xC000)
        tile_count: Number of tiles to extract (default 64)
        tiles_per_row: Tiles per row in output (default 8)
    """

    # Validate input files
    if not os.path.exists(vram_file):
        print(f"Error: VRAM file not found: {vram_file}")
        return False

    if not os.path.exists(cgram_file):
        print(f"Error: CGRAM file not found: {cgram_file}")
        return False

    # Calculate extraction size
    size_bytes = tile_count * 32  # 32 bytes per 4bpp tile

    # Output filenames
    sprite_file = f"{output_name}.png"
    palette_file = f"{output_name}.pal.json"

    print("Creating Grayscale Sprite with Palette Information")
    print("=" * 60)
    print(f"VRAM file: {vram_file}")
    print(f"CGRAM file: {cgram_file}")
    print(f"Output sprite: {sprite_file}")
    print(f"Output palette: {palette_file}")
    print(f"Extracting {tile_count} tiles from offset {hex(offset)}")
    print(f"Using palette {palette_index}")
    print()

    # Step 1: Extract grayscale sprite (WITHOUT applying color palette)
    print("Step 1: Extracting grayscale sprite...")
    sprite_cmd = [
        "python3",
        "sprite_editor/sprite_extractor.py",
        "--vram",
        vram_file,
        "--offset",
        hex(offset),
        "--size",
        hex(size_bytes),
        "--output",
        sprite_file,
        "--width",
        str(tiles_per_row),
        # NOTE: NOT using --palette here to keep it grayscale
    ]

    if not run_command(sprite_cmd, "Extract grayscale sprite"):
        return False

    # Step 2: Extract palette
    print("\nStep 2: Extracting palette...")
    palette_cmd = [
        "python3",
        "extract_palette_for_editor.py",
        cgram_file,
        "-p",
        str(palette_index),
        "-o",
        palette_file,
    ]

    if not run_command(palette_cmd, "Extract palette"):
        return False

    # Step 3: Verify files were created
    print("\nStep 3: Verifying output files...")

    if not os.path.exists(sprite_file):
        print(f"Error: Sprite file not created: {sprite_file}")
        return False

    if not os.path.exists(palette_file):
        print(f"Error: Palette file not created: {palette_file}")
        return False

    # Show file sizes
    sprite_size = os.path.getsize(sprite_file)
    palette_size = os.path.getsize(palette_file)

    print(f"✓ Created {sprite_file} ({sprite_size} bytes)")
    print(f"✓ Created {palette_file} ({palette_size} bytes)")

    print("\n" + "=" * 60)
    print("SUCCESS! Files ready for pixel editor:")
    print(
        f"  1. {sprite_file} - TRUE grayscale sprite (indexed with grayscale palette)"
    )
    print(f"  2. {palette_file} - Companion palette file for color preview")
    print()
    print("Usage in pixel editor:")
    print(f"  python3 pixel_editor/launch_pixel_editor.py {sprite_file}")
    print("  - Palette file will auto-load for color preview")
    print("  - Sprite remains grayscale for editing")
    print("  - Use palette preview toggle to see colors")
    print("  - Saves as indexed values (not colored pixels)")
    print()

    return True


def main():
    parser = argparse.ArgumentParser(
        description="Create grayscale sprite with palette information for pixel editor"
    )

    # Input files
    parser.add_argument(
        "--vram",
        default="Cave.SnesVideoRam.dmp",
        help="VRAM dump file (default: Cave.SnesVideoRam.dmp)",
    )
    parser.add_argument(
        "--cgram",
        default="Cave.SnesCgRam.dmp",
        help="CGRAM dump file (default: Cave.SnesCgRam.dmp)",
    )

    # Output options
    parser.add_argument(
        "-o",
        "--output",
        default="kirby_sprites_grayscale_for_editor",
        help="Output filename base (default: kirby_sprites_grayscale_for_editor)",
    )

    # Extraction options
    parser.add_argument(
        "-p",
        "--palette",
        type=int,
        default=8,
        help="Palette index to extract (default: 8)",
    )
    parser.add_argument(
        "--offset", default="0xC000", help="VRAM offset in hex (default: 0xC000)"
    )
    parser.add_argument(
        "--tiles", type=int, default=64, help="Number of tiles to extract (default: 64)"
    )
    parser.add_argument(
        "--width", type=int, default=8, help="Tiles per row (default: 8)"
    )

    # Presets
    parser.add_argument(
        "--kirby", action="store_true", help="Use Kirby preset (64 tiles, palette 8)"
    )
    parser.add_argument(
        "--ui", action="store_true", help="Use UI preset (32 tiles, palette 12)"
    )
    parser.add_argument(
        "--enemies",
        action="store_true",
        help="Use enemies preset (128 tiles, palette 14)",
    )

    args = parser.parse_args()

    # Apply presets
    if args.kirby:
        args.palette = 8
        args.tiles = 64
        args.width = 8
        args.output = "kirby_sprites_grayscale_for_editor"
    elif args.ui:
        args.palette = 12
        args.tiles = 32
        args.width = 8
        args.output = "ui_sprites_grayscale_for_editor"
    elif args.enemies:
        args.palette = 14
        args.tiles = 128
        args.width = 16
        args.output = "enemy_sprites_grayscale_for_editor"

    # Parse offset
    offset = int(args.offset, 16)

    # Create files
    success = create_grayscale_with_palette(
        args.vram, args.cgram, args.output, args.palette, offset, args.tiles, args.width
    )

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
