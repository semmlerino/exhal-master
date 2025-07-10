#!/usr/bin/env python3
"""
Analyze the new synchronized memory dumps to demonstrate automatic palette assignment
All three dumps (VRAM, CGRAM, OAM) are from the same exact game moment
"""

import os
import sys

sys.path.append("sprite_editor")

from PIL import Image, ImageDraw

from sprite_editor.oam_palette_mapper import OAMPaletteMapper
from sprite_editor.palette_utils import read_cgram_palette
from sprite_editor.sprite_editor_core import SpriteEditorCore


def find_new_dumps():
    """Find the newly added memory dump files"""
    # Look for new dump files - they might have different names
    possible_names = [
        ("VRAM2.dmp", "CGRAM2.dmp", "OAM2.dmp"),
        ("VRAM_new.dmp", "CGRAM_new.dmp", "OAM_new.dmp"),
        ("vram_sync.dmp", "cgram_sync.dmp", "oam_sync.dmp"),
    ]

    # Check current directory for any .dmp files
    dmp_files = [f for f in os.listdir(".") if f.endswith(".dmp")]
    print("Found .dmp files:", dmp_files)

    # Try to identify the new set
    vram_candidates = [f for f in dmp_files if "vram" in f.lower() and f != "VRAM.dmp"]
    cgram_candidates = [f for f in dmp_files if "cgram" in f.lower() and f != "CGRAM.dmp"]
    oam_candidates = [f for f in dmp_files if "oam" in f.lower() and f != "OAM.dmp"]

    if vram_candidates and cgram_candidates and oam_candidates:
        return vram_candidates[0], cgram_candidates[0], oam_candidates[0]

    # Check predefined names
    for vram, cgram, oam in possible_names:
        if os.path.exists(vram) and os.path.exists(cgram) and os.path.exists(oam):
            return vram, cgram, oam

    return None, None, None

def main():
    print("=== Analyzing New Synchronized Memory Dumps ===\n")

    # Find the new dumps
    vram_file, cgram_file, oam_file = find_new_dumps()

    if not all([vram_file, cgram_file, oam_file]):
        print("Could not find new dump files. Please check file names.")
        print("\nExpected one of these sets:")
        print("- VRAM2.dmp, CGRAM2.dmp, OAM2.dmp")
        print("- VRAM_new.dmp, CGRAM_new.dmp, OAM_new.dmp")
        print("- Or any VRAM/CGRAM/OAM files different from the originals")
        return

    print("Using new synchronized dumps:")
    print(f"- VRAM: {vram_file}")
    print(f"- CGRAM: {cgram_file}")
    print(f"- OAM: {oam_file}")

    # Initialize sprite editor
    core = SpriteEditorCore()

    # Load OAM mapping
    print(f"\nLoading OAM data from {oam_file}...")
    if not core.load_oam_mapping(oam_file):
        print("Failed to load OAM data!")
        return

    # Get palette usage stats
    palette_info = core._get_active_palette_info()
    print("\nPalettes used by sprites (from OAM):")
    for pal_num, count in sorted(palette_info.items()):
        print(f"  Palette {pal_num}: {count} sprites")

    # Analyze OAM entries in detail
    print("\nAnalyzing sprite locations...")
    mapper = OAMPaletteMapper()
    mapper.parse_oam_dump(oam_file)

    # Show first few visible sprites
    visible_sprites = [s for s in mapper.oam_entries if s["y"] < 224]
    print(f"\nFound {len(visible_sprites)} visible sprites")
    print("\nFirst 10 visible sprites:")
    for sprite in visible_sprites[:10]:
        print(f"  Sprite {sprite['index']:3d}: Pos({sprite['x']:3d},{sprite['y']:3d}) "
              f"Tile 0x{sprite['tile']:03X} Palette {sprite['palette']}")

    # Extract sprites with automatic OAM-based palette assignment
    print("\n=== Extracting with Automatic Palette Assignment ===")

    try:
        # Method 1: Extract with OAM-correct palettes
        print("\n1. Extracting full sheet with OAM-based palettes...")
        oam_correct_img, tiles = core.extract_sprites_with_correct_palettes(
            vram_file, 0xC000, 0x4000, cgram_file, tiles_per_row=16
        )
        oam_correct_img.save("new_dumps_oam_correct.png")

        # Scale for visibility
        scaled = oam_correct_img.resize(
            (oam_correct_img.width * 2, oam_correct_img.height * 2),
            resample=Image.NEAREST
        )
        scaled.save("new_dumps_oam_correct_2x.png")
        print(f"✓ Saved: new_dumps_oam_correct.png ({tiles} tiles)")

    except Exception as e:
        print(f"Error with OAM-correct extraction: {e}")

    # Method 2: Extract different regions to show palette variety
    print("\n2. Extracting specific regions...")
    extract_regions(core, vram_file, cgram_file)

    # Method 3: Create palette grid
    print("\n3. Creating palette grid preview...")
    try:
        grid_img, _ = core.create_palette_grid_preview(
            vram_file, 0xC000, 0x2000, cgram_file, tiles_per_row=16
        )
        grid_img.save("new_dumps_palette_grid.png")
        print("✓ Saved: new_dumps_palette_grid.png")
    except Exception as e:
        print(f"Error creating palette grid: {e}")

    # Method 4: Extract with multi-palette preview
    print("\n4. Creating multi-palette preview...")
    try:
        palette_images, _ = core.extract_sprites_multi_palette(
            vram_file, 0xC000, 0x1000, cgram_file, tiles_per_row=16
        )

        for name, img in palette_images.items():
            filename = f"new_dumps_{name}.png"
            img.save(filename)
            print(f"✓ Saved: {filename}")
    except Exception as e:
        print(f"Error with multi-palette extraction: {e}")

    # Create analysis summary
    create_analysis_summary(mapper, cgram_file)

    print("\n=== Analysis Complete! ===")
    print("\nThe synchronized dumps should show:")
    print("1. Sprites automatically using their correct palettes from OAM")
    print("2. Different sprite types with different colors")
    print("3. Proper multi-palette functionality")

def extract_regions(core, vram_file, cgram_file):
    """Extract specific regions to highlight different sprites"""

    regions = [
        ("First 64 tiles", 0xC000, 0x800, 8),
        ("Next 64 tiles", 0xC800, 0x800, 8),
        ("Mid region", 0xD000, 0x800, 8),
        ("Later region", 0xE000, 0x800, 8),
    ]

    for name, offset, size, tiles_per_row in regions:
        try:
            img, tiles = core.extract_sprites_with_correct_palettes(
                vram_file, offset, size, cgram_file, tiles_per_row
            )

            filename = f"new_dumps_region_{name.lower().replace(' ', '_')}.png"
            img.save(filename)
            print(f"  ✓ {name}: {tiles} tiles saved to {filename}")
        except Exception as e:
            print(f"  ✗ {name}: Error - {e}")

def create_analysis_summary(mapper, cgram_file):
    """Create a visual summary of the analysis"""

    # Create an image showing palette colors
    palette_preview = Image.new("RGB", (256, 256), (32, 32, 32))
    draw = ImageDraw.Draw(palette_preview)

    # Draw each palette's colors
    for pal_num in range(16):
        palette = read_cgram_palette(cgram_file, pal_num)
        if palette:
            x_base = (pal_num % 4) * 64
            y_base = (pal_num // 4) * 64

            # Draw 16 color swatches for this palette
            for color_idx in range(16):
                x = x_base + (color_idx % 4) * 16
                y = y_base + (color_idx // 4) * 16

                if color_idx * 3 + 2 < len(palette):
                    r = palette[color_idx * 3]
                    g = palette[color_idx * 3 + 1]
                    b = palette[color_idx * 3 + 2]

                    draw.rectangle([(x, y), (x + 15, y + 15)], fill=(r, g, b))
                    draw.rectangle([(x, y), (x + 15, y + 15)], outline=(64, 64, 64))

            # Label palette number
            draw.text((x_base + 32, y_base + 50), f"P{pal_num}",
                     fill=(255, 255, 255), anchor="mm")

    palette_preview.save("new_dumps_palette_colors.png")
    print("\n✓ Created palette color preview: new_dumps_palette_colors.png")

if __name__ == "__main__":
    main()
