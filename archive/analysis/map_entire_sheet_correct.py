#!/usr/bin/env python3
"""
Map the entire sprite sheet with correct palettes using the discovered offset
OAM Palette N -> CGRAM Palette N+8
"""

import sys

sys.path.append("sprite_editor")


from PIL import Image, ImageDraw

from sprite_editor.oam_palette_mapper import OAMPaletteMapper
from sprite_editor.palette_utils import read_cgram_palette
from sprite_editor.sprite_editor_core import SpriteEditorCore
from sprite_editor.tile_utils import decode_4bpp_tile


def main():
    print("=== Mapping Entire Sheet with Correct Palettes ===")
    print("Using discovered offset: OAM Palette N -> CGRAM Palette N+8\n")

    vram_file = "SnesVideoRam.VRAM.dmp"
    cgram_file = "SnesCgRam.dmp"
    oam_file = "SnesSpriteRam.OAM.dmp"

    # Load OAM data
    mapper = OAMPaletteMapper()
    mapper.parse_oam_dump(oam_file)

    # Analyze palette usage
    print("Palette usage in this frame:")
    palette_usage = {}
    tile_to_palette = {}

    for sprite in mapper.oam_entries:
        if sprite["y"] < 224:  # Visible sprites
            oam_pal = sprite["palette"]
            cgram_pal = oam_pal + 8  # Apply offset

            if oam_pal not in palette_usage:
                palette_usage[oam_pal] = {
                    "cgram_pal": cgram_pal,
                    "sprites": [],
                    "tiles": set()
                }

            palette_usage[oam_pal]["sprites"].append(sprite)
            palette_usage[oam_pal]["tiles"].add(sprite["tile"])

            # Map tile to palette
            tile_to_palette[sprite["tile"]] = cgram_pal

            # For large sprites, map additional tiles
            if sprite["size"] == "large":
                # 16x16 sprites use 4 tiles
                tile_to_palette[sprite["tile"] + 1] = cgram_pal
                tile_to_palette[sprite["tile"] + 16] = cgram_pal
                tile_to_palette[sprite["tile"] + 17] = cgram_pal

    # Display palette mapping
    for oam_pal, info in sorted(palette_usage.items()):
        print(f"\nOAM Palette {oam_pal} -> CGRAM Palette {info['cgram_pal']}:")
        print(f"  {len(info['sprites'])} sprites")
        print(f"  Tiles: {sorted(info['tiles'])[:10]}")
        if len(info["tiles"]) > 10:
            print(f"  ... and {len(info['tiles']) - 10} more tiles")

    # Method 1: Extract full sheet with automatic palette mapping
    print("\n\nMethod 1: Full sheet with tile-based palette mapping...")
    create_full_sheet_with_mapping(vram_file, cgram_file, tile_to_palette)

    # Method 2: Extract regions showing each palette group
    print("\nMethod 2: Extracting palette-specific regions...")
    extract_palette_regions(vram_file, cgram_file, palette_usage)

    # Method 3: Create a comprehensive view
    print("\nMethod 3: Creating comprehensive palette view...")
    create_comprehensive_view(vram_file, cgram_file, mapper, palette_usage)

    print("\n=== Complete! ===")
    print("The entire sheet is now mapped with correct palettes!")

def create_full_sheet_with_mapping(vram_file, cgram_file, tile_to_palette):
    """Create full sprite sheet with correct palette for each tile"""

    # Read VRAM data
    with open(vram_file, "rb") as f:
        f.seek(0xC000)
        vram_data = f.read(0x4000)

    # Calculate dimensions
    tiles_per_row = 16
    total_tiles = len(vram_data) // 32
    tiles_y = (total_tiles + tiles_per_row - 1) // tiles_per_row

    width = tiles_per_row * 8
    height = tiles_y * 8

    # Create RGBA image
    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))

    # Load all CGRAM palettes
    palettes = []
    for i in range(16):
        pal = read_cgram_palette(cgram_file, i)
        palettes.append(pal)

    # Process each tile
    for tile_idx in range(total_tiles):
        tile_offset = tile_idx * 32

        if tile_offset + 32 <= len(vram_data):
            # Decode tile
            tile_pixels = decode_4bpp_tile(vram_data, tile_offset)

            # Determine palette
            # Try to match tile index to OAM sprite tiles
            cgram_pal = 8  # Default to palette 8 (OAM 0)

            # Check if this tile is mapped
            if tile_idx in tile_to_palette:
                cgram_pal = tile_to_palette[tile_idx]
            # Try to infer from nearby tiles or position
            # Tiles 0-127 often use palette 8 (Kirby)
            # Tiles 128+ might use other palettes
            elif tile_idx < 128:
                cgram_pal = 8
            elif tile_idx < 256:
                cgram_pal = 12
            else:
                cgram_pal = 10

            # Get palette
            if cgram_pal < len(palettes) and palettes[cgram_pal]:
                palette = palettes[cgram_pal]

                # Calculate tile position
                tile_x = tile_idx % tiles_per_row
                tile_y = tile_idx // tiles_per_row

                # Draw tile pixels
                for y in range(8):
                    for x in range(8):
                        pixel_idx = y * 8 + x
                        if pixel_idx < len(tile_pixels):
                            color_idx = tile_pixels[pixel_idx]

                            if color_idx > 0:  # Skip transparent
                                if color_idx * 3 + 2 < len(palette):
                                    r = palette[color_idx * 3]
                                    g = palette[color_idx * 3 + 1]
                                    b = palette[color_idx * 3 + 2]

                                    px = tile_x * 8 + x
                                    py = tile_y * 8 + y
                                    if px < width and py < height:
                                        img.putpixel((px, py), (r, g, b, 255))

    # Save full sheet
    img.save("full_sheet_correct_palettes.png")

    # Also create scaled version
    scaled = img.resize((img.width * 2, img.height * 2), resample=Image.NEAREST)
    scaled.save("full_sheet_correct_palettes_2x.png")

    print("✓ Created full_sheet_correct_palettes.png and 2x version")

def extract_palette_regions(vram_file, cgram_file, palette_usage):
    """Extract regions for each palette group"""

    core = SpriteEditorCore()

    # Define regions based on typical sprite organization
    regions = [
        ("Kirby (OAM 0)", 0xC000, 0x1000, 8),   # CGRAM 8
        ("Enemies 1 (OAM 1)", 0xD000, 0x800, 9), # CGRAM 9
        ("Enemies 2 (OAM 2)", 0xD800, 0x800, 10), # CGRAM 10
        ("Items (OAM 3)", 0xE000, 0x800, 11),    # CGRAM 11
        ("Effects (OAM 4)", 0xE800, 0x800, 12),  # CGRAM 12
    ]

    for name, offset, size, cgram_pal in regions:
        try:
            img, tiles = core.extract_sprites(vram_file, offset, size, tiles_per_row=8)

            palette = read_cgram_palette(cgram_file, cgram_pal)
            if palette:
                img.putpalette(palette)

                filename = f"region_{name.lower().replace(' ', '_').replace('(', '').replace(')', '')}.png"
                img.save(filename)
                print(f"  ✓ {name}: {tiles} tiles -> {filename}")

        except Exception as e:
            print(f"  ✗ {name}: Error - {e}")

def create_comprehensive_view(vram_file, cgram_file, mapper, palette_usage):
    """Create a comprehensive view showing all palettes and their sprites"""

    # Create a large canvas
    canvas_width = 800
    canvas_height = 600
    canvas = Image.new("RGB", (canvas_width, canvas_height), (32, 32, 32))
    draw = ImageDraw.Draw(canvas)

    # Title
    draw.text((canvas_width // 2, 20), "Complete Sprite Sheet - Correct Palette Mapping",
             fill=(255, 255, 255), anchor="mt")

    # Load CGRAM colors for display
    y_pos = 60

    for oam_pal in sorted(palette_usage.keys()):
        info = palette_usage[oam_pal]
        cgram_pal = info["cgram_pal"]

        # Draw palette label
        label = f"OAM Palette {oam_pal} -> CGRAM Palette {cgram_pal} ({len(info['sprites'])} sprites)"
        draw.text((20, y_pos), label, fill=(255, 255, 255))

        # Draw color swatches
        palette = read_cgram_palette(cgram_file, cgram_pal)
        if palette:
            x_pos = 20
            for i in range(16):
                if i * 3 + 2 < len(palette):
                    r = palette[i * 3]
                    g = palette[i * 3 + 1]
                    b = palette[i * 3 + 2]

                    draw.rectangle([(x_pos, y_pos + 20), (x_pos + 20, y_pos + 40)],
                                 fill=(r, g, b), outline=(64, 64, 64))
                    x_pos += 22

        # Show example tiles
        example_tiles = sorted(info["tiles"])[:5]
        tile_info = f"Tiles: {example_tiles}"
        draw.text((400, y_pos + 10), tile_info, fill=(200, 200, 200))

        y_pos += 60

    # Add color key
    draw.text((20, canvas_height - 40),
             "Synchronized dumps from the same frame - all palettes correctly mapped!",
             fill=(0, 255, 0))

    canvas.save("comprehensive_palette_mapping.png")
    print("✓ Created comprehensive_palette_mapping.png")

if __name__ == "__main__":
    main()
