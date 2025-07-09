#!/usr/bin/env python3
"""
Test script to analyze palette application issues with Kirby sprites.
This script will:
1. Load a grayscale sprite image
2. Apply different palettes (8-15) from the CGRAM dump
3. Save the results to see which palette produces correct Kirby colors
4. Check if the palette indices in the metadata files match the actual OAM assignments
5. Verify if the "most common palette" logic is correct
"""

import json
import os

import numpy as np
from PIL import Image

from sprite_edit_helpers import parse_cgram
from sprite_editor.oam_palette_mapper import OAMPaletteMapper


def load_grayscale_sheet_and_metadata(png_file):
    """Load grayscale sheet and its metadata"""
    metadata_file = png_file.replace(".png", "_metadata.json")

    if not os.path.exists(metadata_file):
        print(f"Warning: No metadata file found for {png_file}")
        return None, None

    # Load image
    img = Image.open(png_file)

    # Load metadata
    with open(metadata_file) as f:
        metadata = json.load(f)

    return img, metadata

def analyze_oam_palette_usage(oam_file):
    """Analyze OAM palette usage for sprites"""
    mapper = OAMPaletteMapper()
    mapper.parse_oam_dump(oam_file)
    mapper.build_vram_palette_map(0x6000)  # Standard Kirby VRAM offset

    stats = mapper.get_palette_usage_stats()
    print("\nOAM Palette Usage Statistics:")
    print(f"Total sprites: {stats['total_sprites']}")
    print(f"Visible sprites: {stats['visible_sprites']}")
    print(f"Active palettes: {stats['active_palettes']}")
    print("\nPalette usage counts:")
    for pal, count in sorted(stats["palette_counts"].items()):
        print(f"  OAM Palette {pal}: {count} sprites (CGRAM palette {pal + 8})")

    return mapper, stats

def apply_palette_to_grayscale(grayscale_img, palette_colors, grayscale_mapping):
    """Apply a specific palette to a grayscale image"""
    # Convert to RGB
    img_array = np.array(grayscale_img)
    height, width = img_array.shape
    rgb_array = np.zeros((height, width, 3), dtype=np.uint8)

    # Get grayscale to index mapping
    gray_to_idx = {}
    for idx, gray in grayscale_mapping["color_mapping"].items():
        gray_to_idx[gray] = int(idx)

    # Apply palette
    for y in range(height):
        for x in range(width):
            gray_val = img_array[y, x]
            if gray_val in gray_to_idx:
                color_idx = gray_to_idx[gray_val]
                if color_idx < len(palette_colors):
                    rgb_array[y, x] = palette_colors[color_idx][:3]

    return Image.fromarray(rgb_array, "RGB")

def test_all_sprite_palettes(grayscale_file, cgram_file, oam_file, output_dir="palette_tests"):
    """Test all sprite palettes (8-15) on the grayscale image"""

    # Create output directory
    os.makedirs(output_dir, exist_ok=True)

    # Load grayscale image and metadata
    img, metadata = load_grayscale_sheet_and_metadata(grayscale_file)
    if not img or not metadata:
        print("Failed to load grayscale sheet or metadata")
        return

    # Parse CGRAM palettes
    palettes = parse_cgram(cgram_file)

    # Analyze OAM data
    mapper, oam_stats = analyze_oam_palette_usage(oam_file)

    # Get grayscale mapping info
    grayscale_mapping = metadata.get("grayscale_mapping", {})

    # Test each sprite palette (8-15)
    results = {}
    for pal_idx in range(8, 16):
        print(f"\nTesting palette {pal_idx}...")

        # Apply palette
        palette_colors = palettes[pal_idx]
        result_img = apply_palette_to_grayscale(img, palette_colors, grayscale_mapping)

        # Save result
        output_file = os.path.join(output_dir, f"palette_{pal_idx}_test.png")
        result_img.save(output_file)

        # Analyze palette colors
        results[pal_idx] = {
            "file": output_file,
            "colors": [list(c) for c in palette_colors],
            "oam_usage": oam_stats["palette_counts"].get(pal_idx - 8, 0),
            "is_kirby_palette": pal_idx == 8  # Kirby typically uses palette 8
        }

        # Check for typical Kirby colors (pink/red)
        has_pink = any(r > 200 and g < 150 and b < 150 for r, g, b in palette_colors)
        has_red = any(r > 180 and g < 100 and b < 100 for r, g, b in palette_colors)
        results[pal_idx]["has_kirby_colors"] = has_pink or has_red

        print(f"  Saved to: {output_file}")
        print(f"  OAM usage: {results[pal_idx]['oam_usage']} sprites")
        print(f"  Has Kirby colors: {results[pal_idx]['has_kirby_colors']}")

    # Check metadata palette assignments
    print("\n\nChecking metadata palette assignments:")
    tile_info = metadata.get("tile_info", {})
    metadata_palettes = {}
    for _tile_idx, info in tile_info.items():
        cgram_pal = info.get("cgram_palette", 8)
        metadata_palettes[cgram_pal] = metadata_palettes.get(cgram_pal, 0) + 1

    print("Metadata palette usage:")
    for pal, count in sorted(metadata_palettes.items()):
        print(f"  CGRAM Palette {pal}: {count} tiles")

    # Compare with OAM data
    print("\n\nComparing OAM vs Metadata palette assignments:")
    print("(OAM palettes 0-7 map to CGRAM palettes 8-15)")

    # Find discrepancies
    discrepancies = []
    for oam_pal in range(8):
        cgram_pal = oam_pal + 8
        oam_count = oam_stats["palette_counts"].get(oam_pal, 0)
        meta_count = metadata_palettes.get(cgram_pal, 0)

        if oam_count > 0 or meta_count > 0:
            print(f"  OAM Palette {oam_pal} (CGRAM {cgram_pal}): "
                  f"OAM={oam_count} sprites, Metadata={meta_count} tiles")

            if abs(oam_count - meta_count) > 10:  # Significant difference
                discrepancies.append((oam_pal, oam_count, meta_count))

    # Check "most common palette" logic
    print("\n\nChecking 'most common palette' logic:")
    companion_pal_file = grayscale_file.replace(".png", ".pal.json")
    if os.path.exists(companion_pal_file):
        with open(companion_pal_file) as f:
            pal_data = json.load(f)

        source_pal = pal_data["source"]["palette_index"]
        print(f"Companion palette file uses: CGRAM palette {source_pal}")

        # Find actual most common from OAM
        if oam_stats["palette_counts"]:
            most_common_oam = max(oam_stats["palette_counts"],
                                  key=oam_stats["palette_counts"].get)
            most_common_cgram = most_common_oam + 8
            print(f"Most common OAM palette: {most_common_oam} (CGRAM {most_common_cgram})")

            if most_common_cgram != source_pal:
                print(f"⚠️  WARNING: Companion palette ({source_pal}) doesn't match "
                      f"most common OAM palette ({most_common_cgram})")

    # Save analysis results
    analysis_file = os.path.join(output_dir, "palette_analysis_results.json")
    with open(analysis_file, "w") as f:
        json.dump({
            "test_results": results,
            "oam_statistics": oam_stats,
            "metadata_palettes": metadata_palettes,
            "discrepancies": discrepancies
        }, f, indent=2)

    print(f"\n\nAnalysis complete! Results saved to {analysis_file}")
    print(f"Test images saved in {output_dir}/")

    # Recommend best palette
    print("\n\nRECOMMENDATION:")
    best_palette = None

    # Check for Kirby colors in palettes with OAM usage
    for pal_idx in range(8, 16):
        if results[pal_idx]["has_kirby_colors"] and results[pal_idx]["oam_usage"] > 0:
            if best_palette is None or results[pal_idx]["oam_usage"] > results[best_palette]["oam_usage"]:
                best_palette = pal_idx

    if best_palette:
        print(f"✅ Use CGRAM palette {best_palette} - it has Kirby colors and "
              f"{results[best_palette]['oam_usage']} sprites use it in OAM")
    else:
        print("⚠️  No palette found with both Kirby colors and OAM usage. "
              "Check the test images manually.")

def main():
    """Run the palette analysis tests"""

    # File paths
    grayscale_file = "kirby_sprites_grayscale_ultrathink.png"
    cgram_file = "Cave.SnesCgRam.dmp"
    oam_file = "Cave.SnesSpriteRam.dmp"

    # Check if files exist
    required_files = [grayscale_file, cgram_file, oam_file]
    missing_files = [f for f in required_files if not os.path.exists(f)]

    if missing_files:
        print("Missing required files:")
        for f in missing_files:
            print(f"  - {f}")
        print("\nPlease ensure all required files are present.")
        return

    # Run the tests
    test_all_sprite_palettes(grayscale_file, cgram_file, oam_file)

if __name__ == "__main__":
    main()
