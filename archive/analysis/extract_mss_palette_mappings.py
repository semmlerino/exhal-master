#!/usr/bin/env python3
"""
Extract and visualize sprite-to-palette mappings from MSS savestates.
This tool parses Mesen-S savestates to extract VRAM, CGRAM, and OAM data,
then visualizes which sprites use which palettes.
"""

import json
import struct
import zlib

from PIL import Image, ImageDraw, ImageFont


def parse_mss_savestate(filename):
    """Parse MSS savestate and extract VRAM, CGRAM, and OAM"""
    with open(filename, "rb") as f:
        data = f.read()

    # Check MSS signature
    if data[:3] != b"MSS":
        raise ValueError("Not a valid MSS file")

    # Find and decompress data (zlib starts at offset 0x23)
    compressed_data = data[0x23:]
    decompressed = zlib.decompress(compressed_data)

    # Extract memory blocks based on discovered layout
    vram = decompressed[0x00000:0x10000]      # 64KB VRAM
    cgram = decompressed[0x10000:0x10200]     # 512 bytes CGRAM
    oam = decompressed[0x10200:0x10420]       # 544 bytes OAM

    return vram, cgram, oam


def parse_oam_data(oam_data):
    """Parse OAM data and extract sprite information"""
    sprites = []

    # Parse main OAM table (first 512 bytes)
    for i in range(0, 512, 4):
        x = oam_data[i]
        y = oam_data[i + 1]
        tile = oam_data[i + 2]
        attr = oam_data[i + 3]

        # Skip inactive sprites
        if y >= 240 or tile == 0:
            continue

        # Extract attributes
        palette = (attr >> 1) & 0x07  # Bits 1-3
        priority = (attr >> 4) & 0x03  # Bits 4-5
        h_flip = bool(attr & 0x40)     # Bit 6
        v_flip = bool(attr & 0x80)     # Bit 7

        # Get high bits from high table
        sprite_idx = i // 4
        high_byte_idx = 512 + (sprite_idx // 4)
        high_bit_shift = (sprite_idx % 4) * 2

        high_bits = oam_data[high_byte_idx]
        size_bit = (high_bits >> high_bit_shift) & 1
        x_msb = (high_bits >> (high_bit_shift + 1)) & 1

        # Adjust X position with MSB
        if x_msb:
            x |= 0x100

        sprites.append({
            "index": sprite_idx,
            "x": x,
            "y": y,
            "tile": tile,
            "palette": palette + 8,  # Sprite palettes are 8-15
            "priority": priority,
            "h_flip": h_flip,
            "v_flip": v_flip,
            "size": "large" if size_bit else "small",
            "vram_addr": tile * 32  # Each tile is 32 bytes in 4bpp
        })

    return sprites


def parse_cgram_data(cgram_data):
    """Parse CGRAM data and extract palettes"""
    palettes = []

    for pal_idx in range(16):
        colors = []
        for color_idx in range(16):
            offset = (pal_idx * 16 + color_idx) * 2
            bgr555 = struct.unpack("<H", cgram_data[offset:offset+2])[0]

            # Convert BGR555 to RGB888
            r = ((bgr555 >> 0) & 0x1F) * 8
            g = ((bgr555 >> 5) & 0x1F) * 8
            b = ((bgr555 >> 10) & 0x1F) * 8

            colors.append((r, g, b))

        palettes.append(colors)

    return palettes


def extract_sprite_tile(vram_data, tile_num, is_4bpp=True):
    """Extract a single 8x8 tile from VRAM"""
    if is_4bpp:
        bytes_per_tile = 32
        tile_offset = tile_num * bytes_per_tile

        if tile_offset + bytes_per_tile > len(vram_data):
            return None

        tile_data = vram_data[tile_offset:tile_offset + bytes_per_tile]

        # Decode 4bpp SNES tile format
        pixels = []
        for row in range(8):
            row_pixels = []

            # Get the 4 bytes for this row
            bp0 = tile_data[row * 2]
            bp1 = tile_data[row * 2 + 1]
            bp2 = tile_data[row * 2 + 16]
            bp3 = tile_data[row * 2 + 17]

            # Extract each pixel
            for col in range(8):
                bit = 7 - col
                pixel = ((bp0 >> bit) & 1) | \
                        (((bp1 >> bit) & 1) << 1) | \
                        (((bp2 >> bit) & 1) << 2) | \
                        (((bp3 >> bit) & 1) << 3)
                row_pixels.append(pixel)

            pixels.append(row_pixels)

        return pixels

    return None


def create_palette_mapping_visualization(vram, cgram, oam, output_file):
    """Create a visualization showing sprites and their palette assignments"""
    sprites = parse_oam_data(oam)
    palettes = parse_cgram_data(cgram)

    # Create image to show sprite tiles with their palettes
    img_width = 800
    img_height = 600
    img = Image.new("RGB", (img_width, img_height), (32, 32, 32))
    draw = ImageDraw.Draw(img)

    # Try to load a font, fall back to default if not available
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 12)
        small_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 10)
    except:
        font = ImageFont.load_default()
        small_font = font

    # Draw title
    draw.text((10, 10), "MSS Savestate: Sprite to Palette Mapping", fill=(255, 255, 255), font=font)
    draw.text((10, 30), f"Active Sprites: {len(sprites)}", fill=(200, 200, 200), font=small_font)

    # Draw palette reference on the right side
    pal_x_start = 600
    draw.text((pal_x_start, 50), "Palettes:", fill=(255, 255, 255), font=font)

    for pal_idx in range(8, 16):  # Show sprite palettes
        y_pos = 70 + (pal_idx - 8) * 40
        draw.text((pal_x_start, y_pos), f"Pal {pal_idx}:", fill=(200, 200, 200), font=small_font)

        # Draw color swatches
        for color_idx in range(min(8, 16)):  # Show first 8 colors
            x = pal_x_start + 40 + color_idx * 20
            y = y_pos
            color = palettes[pal_idx][color_idx]
            draw.rectangle([x, y, x + 18, y + 18], fill=color, outline=(128, 128, 128))

    # Group sprites by palette
    sprites_by_palette = {}
    for sprite in sprites:
        pal = sprite["palette"]
        if pal not in sprites_by_palette:
            sprites_by_palette[pal] = []
        sprites_by_palette[pal].append(sprite)

    # Draw sprites grouped by palette
    y_offset = 80
    x_offset = 20

    for pal_idx in sorted(sprites_by_palette.keys()):
        if pal_idx < 8 or pal_idx > 15:  # Skip non-sprite palettes
            continue

        palette_sprites = sprites_by_palette[pal_idx]

        # Draw palette header
        draw.text((x_offset, y_offset), f"Palette {pal_idx} ({len(palette_sprites)} sprites):",
                  fill=(255, 200, 100), font=font)
        y_offset += 20

        # Draw up to 10 sprite tiles from this palette
        tile_x = x_offset
        for _i, sprite in enumerate(palette_sprites[:10]):
            # Skip if it would go off screen
            if tile_x + 40 > 580:
                break

            # Extract and draw the tile
            tile_pixels = extract_sprite_tile(vram, sprite["tile"])
            if tile_pixels:
                # Create a small image for this tile
                tile_img = Image.new("RGB", (8, 8))
                for y in range(8):
                    for x in range(8):
                        pixel_idx = tile_pixels[y][x]
                        color = palettes[pal_idx][pixel_idx] if pixel_idx > 0 else (0, 0, 0)
                        tile_img.putpixel((x, y), color)

                # Scale up the tile for better visibility
                tile_img = tile_img.resize((32, 32), Image.NEAREST)
                img.paste(tile_img, (tile_x, y_offset))

                # Draw tile info
                draw.text((tile_x, y_offset + 34), f"T:{sprite['tile']:02X}",
                         fill=(150, 150, 150), font=small_font)
                draw.text((tile_x, y_offset + 44), f"@{sprite['x']},{sprite['y']}",
                         fill=(150, 150, 150), font=small_font)

                tile_x += 40

        y_offset += 65

        # Don't let it run off the bottom
        if y_offset > 500:
            break

    # Save the image
    img.save(output_file)
    print(f"Saved palette mapping visualization to {output_file}")

    # Also save detailed mapping data
    mapping_data = {
        "sprites_by_palette": {
            str(pal): [
                {
                    "index": s["index"],
                    "tile": f"0x{s['tile']:02X}",
                    "position": f"({s['x']}, {s['y']})",
                    "size": s["size"]
                }
                for s in sprites
            ]
            for pal, sprites in sprites_by_palette.items()
        },
        "total_sprites": len(sprites),
        "palette_colors": {
            str(pal_idx): [
                f"#{r:02X}{g:02X}{b:02X}"
                for r, g, b in palettes[pal_idx][:8]  # First 8 colors
            ]
            for pal_idx in range(8, 16)
        }
    }

    json_file = output_file.replace(".png", "_data.json")
    with open(json_file, "w") as f:
        json.dump(mapping_data, f, indent=2)
    print(f"Saved detailed mapping data to {json_file}")


def main():
    import sys

    if len(sys.argv) < 2:
        print("Usage: python extract_mss_palette_mappings.py <savestate.mss> [output.png]")
        sys.exit(1)

    mss_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else "mss_palette_mapping.png"

    print(f"Extracting palette mappings from: {mss_file}")

    try:
        vram, cgram, oam = parse_mss_savestate(mss_file)
        print("Successfully extracted:")
        print(f"  VRAM: {len(vram)} bytes")
        print(f"  CGRAM: {len(cgram)} bytes")
        print(f"  OAM: {len(oam)} bytes")

        create_palette_mapping_visualization(vram, cgram, oam, output_file)

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
