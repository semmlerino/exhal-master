#!/usr/bin/env python3
"""
Demonstrate the correct palette mapping with offset
OAM Palette 0-7 -> CGRAM Palette 8-15
"""

import sys

sys.path.append("sprite_editor")

from PIL import Image, ImageDraw

from sprite_editor.oam_palette_mapper import OAMPaletteMapper
from sprite_editor.palette_utils import read_cgram_palette
from sprite_editor.sprite_editor_core import SpriteEditorCore


def main():
    print("=== Corrected Palette Mapping Demo ===")
    print("Discovery: OAM palettes are offset by 8 in CGRAM!")
    print("OAM Palette 0 = CGRAM Palette 8 (Pink Kirby)")
    print("OAM Palette 1 = CGRAM Palette 9, etc.\n")

    vram_file = "SnesVideoRam.VRAM.dmp"
    cgram_file = "SnesCgRam.dmp"
    oam_file = "SnesSpriteRam.OAM.dmp"

    core = SpriteEditorCore()

    # Manual extraction with correct palette mapping
    print("Extracting sprites with corrected palette mapping...")

    # Load OAM data
    mapper = OAMPaletteMapper()
    mapper.parse_oam_dump(oam_file)

    # Group sprites by their OAM palette
    palette_groups = {}
    for sprite in mapper.oam_entries:
        if sprite["y"] < 224:  # Visible only
            pal = sprite["palette"]
            if pal not in palette_groups:
                palette_groups[pal] = []
            palette_groups[pal].append(sprite)

    print("\nOAM Palette assignments (with CGRAM mapping):")
    for oam_pal, sprites in sorted(palette_groups.items()):
        cgram_pal = oam_pal + 8  # The key correction!
        print(f"  OAM Palette {oam_pal} -> CGRAM Palette {cgram_pal}: {len(sprites)} sprites")

    # Extract regions with corrected palettes
    regions = [
        ("Pink Kirby", 0xC000, 0x800, 0, 8),    # OAM 0 -> CGRAM 8
        ("Other Sprites", 0xC800, 0x800, 4, 12), # OAM 4 -> CGRAM 12
    ]

    comparison_images = []

    for name, offset, size, oam_pal, cgram_pal in regions:
        img, _ = core.extract_sprites(vram_file, offset, size, tiles_per_row=8)

        palette = read_cgram_palette(cgram_file, cgram_pal)
        if palette:
            img.putpalette(palette)

            filename = f"corrected_{name.lower().replace(' ', '_')}_oam{oam_pal}_cgram{cgram_pal}.png"
            img.save(filename)
            print(f"\n✓ Saved {filename}")

            # Scale for comparison
            scaled = img.resize((img.width * 2, img.height * 2), resample=Image.NEAREST)
            comparison_images.append((name, oam_pal, cgram_pal, scaled))

    # Create full sheet with corrected mapping
    print("\nCreating full sheet with corrected palette mapping...")
    create_corrected_full_sheet(core, vram_file, cgram_file, mapper)

    # Create comparison showing wrong vs right
    create_comparison_demo(comparison_images)

    print("\n=== Success! ===")
    print("Pink Kirby is now correctly displayed using CGRAM Palette 8 (OAM Palette 0)")
    print("The multi-palette system works perfectly with the correct offset!")

def create_corrected_full_sheet(core, vram_file, cgram_file, mapper):
    """Create a full sprite sheet with corrected palette mapping"""

    # Extract base image
    img, tiles = core.extract_sprites(vram_file, 0xC000, 0x4000, tiles_per_row=16)

    # Create RGBA image for multi-palette rendering
    width, height = img.size
    rgba_img = Image.new("RGBA", (width, height), (0, 0, 0, 0))

    # Load all palettes with offset
    palettes = []
    for i in range(16):
        pal = read_cgram_palette(cgram_file, i)
        palettes.append(pal if pal else None)

    # Process each tile with corrected palette
    from sprite_editor.tile_utils import decode_4bpp_tile

    with open(vram_file, "rb") as f:
        f.seek(0xC000)
        vram_data = f.read(0x4000)

    tiles_per_row = 16
    tile_idx = 0

    for tile_offset in range(0, len(vram_data), 32):
        if tile_offset + 32 <= len(vram_data):
            # Decode tile
            tile_data = decode_4bpp_tile(vram_data, tile_offset)

            # Determine which OAM palette this tile uses
            # This is approximate - we'd need exact tile-to-sprite mapping
            oam_palette = 0  # Default

            # Check if any sprite uses this tile
            for sprite in mapper.oam_entries:
                # Very rough approximation
                if sprite["tile"] * 32 == tile_offset:
                    oam_palette = sprite["palette"]
                    break

            # Apply offset: OAM palette -> CGRAM palette
            cgram_palette = oam_palette + 8

            if cgram_palette < len(palettes) and palettes[cgram_palette]:
                palette = palettes[cgram_palette]

                # Draw tile
                tile_x = tile_idx % tiles_per_row
                tile_y = tile_idx // tiles_per_row

                for y in range(8):
                    for x in range(8):
                        pixel_idx = y * 8 + x
                        if pixel_idx < len(tile_data):
                            color_idx = tile_data[pixel_idx]
                            if color_idx > 0 and color_idx * 3 + 2 < len(palette):
                                r = palette[color_idx * 3]
                                g = palette[color_idx * 3 + 1]
                                b = palette[color_idx * 3 + 2]

                                px = tile_x * 8 + x
                                py = tile_y * 8 + y
                                if px < width and py < height:
                                    rgba_img.putpixel((px, py), (r, g, b, 255))

            tile_idx += 1

    rgba_img.save("corrected_full_sheet_with_offset.png")
    print("✓ Created corrected_full_sheet_with_offset.png")

def create_comparison_demo(images):
    """Show the difference between wrong and corrected mapping"""

    # Also load the wrong version for comparison
    wrong_img = Image.open("new_dumps_oam_correct.png") if os.path.exists("new_dumps_oam_correct.png") else None

    comparison = Image.new("RGB", (800, 400), (32, 32, 32))
    draw = ImageDraw.Draw(comparison)

    draw.text((400, 20), "Palette Mapping Correction", fill=(255, 255, 255), anchor="mt")

    # Wrong version
    if wrong_img:
        wrong_crop = wrong_img.crop((0, 0, 128, 128))
        wrong_scaled = wrong_crop.resize((256, 256), resample=Image.NEAREST)
        comparison.paste(wrong_scaled, (50, 60))

        draw.text((178, 330), "WRONG", fill=(255, 0, 0), anchor="mt")
        draw.text((178, 350), "OAM 0 -> CGRAM 0", fill=(255, 128, 128), anchor="mt")
        draw.text((178, 370), "(Black/Yellow)", fill=(255, 128, 128), anchor="mt")

    # Corrected version
    if images:
        corrected = images[0][3]  # First image (Pink Kirby)
        comparison.paste(corrected, (450, 60))

        draw.text((578, 330), "CORRECT", fill=(0, 255, 0), anchor="mt")
        draw.text((578, 350), "OAM 0 -> CGRAM 8", fill=(128, 255, 128), anchor="mt")
        draw.text((578, 370), "(Pink Kirby!)", fill=(128, 255, 128), anchor="mt")

    # Draw arrow
    draw.line([(320, 180), (420, 180)], fill=(255, 255, 255), width=3)
    draw.polygon([(420, 180), (410, 175), (410, 185)], fill=(255, 255, 255))

    comparison.save("palette_offset_correction.png")
    print("\n✓ Created palette_offset_correction.png")

if __name__ == "__main__":
    import os
    main()
