#!/usr/bin/env python3
"""Check sprites at the Kirby location in MSS savestate VRAM"""

import struct

from PIL import Image

# Read extracted VRAM
with open("mss_extracted_vram.bin", "rb") as f:
    vram = f.read()

# Read extracted CGRAM
with open("mss_extracted_cgram.bin", "rb") as f:
    cgram = f.read()

# Read OAM to find which sprites point to Kirby tiles
with open("mss_extracted_oam.bin", "rb") as f:
    oam = f.read()

print("=== Checking Kirby sprite area ===")
print("VRAM $6000 (byte offset 0xC000)")

# Kirby sprites should be at VRAM $6000 (0xC000 bytes)
kirby_offset = 0xC000
kirby_size = 0x800  # 64 tiles worth

# Check if there's data there
kirby_data = vram[kirby_offset:kirby_offset + kirby_size]
non_zero = sum(1 for b in kirby_data if b != 0)
print(f"Non-zero bytes in Kirby area: {non_zero}/{kirby_size} ({non_zero*100//kirby_size}%)")

# Find which OAM entries use tiles from this area
# Tiles at VRAM $6000 = tile numbers 0x00-0x3F (for 4bpp)
print("\n=== OAM entries using Kirby tiles (0x00-0x3F) ===")

kirby_sprites = []
for i in range(0, 512, 4):
    x = oam[i]
    y = oam[i + 1]
    tile = oam[i + 2]
    attr = oam[i + 3]

    # Check if this uses a Kirby tile
    if tile >= 0x00 and tile <= 0x3F and y < 240:
        palette = (attr >> 1) & 0x07
        kirby_sprites.append({
            "index": i // 4,
            "x": x,
            "y": y,
            "tile": tile,
            "palette": palette + 8
        })

print(f"Found {len(kirby_sprites)} sprites using Kirby tiles")
for sprite in kirby_sprites[:10]:
    print(f"  Sprite {sprite['index']}: Tile 0x{sprite['tile']:02X} at ({sprite['x']},{sprite['y']}) using Palette {sprite['palette']}")

# Check what palettes are being used
palettes_used = {s["palette"] for s in kirby_sprites}
print(f"\nPalettes used by Kirby sprites: {sorted(palettes_used)}")

# Extract and show these palettes
print("\n=== Palettes used by Kirby ===")
for pal_idx in sorted(palettes_used):
    print(f"\nPalette {pal_idx}:")
    colors = []
    for color_idx in range(16):
        offset = (pal_idx * 16 + color_idx) * 2
        bgr555 = struct.unpack("<H", cgram[offset:offset+2])[0]
        r = ((bgr555 >> 0) & 0x1F) * 8
        g = ((bgr555 >> 5) & 0x1F) * 8
        b = ((bgr555 >> 10) & 0x1F) * 8
        colors.append((r, g, b))

    # Print in rows of 4
    for i in range(0, 16, 4):
        print(f"  Colors {i:2d}-{i+3:2d}: ", end="")
        for j in range(4):
            r, g, b = colors[i + j]
            print(f"({r:3d},{g:3d},{b:3d}) ", end="")
        print()

# Create a visual of Kirby sprites with correct palette
print("\n=== Creating Kirby sprite visualization ===")

# Extract first few Kirby tiles
img_width = 256
img_height = 256
img = Image.new("RGB", (img_width, img_height), (64, 64, 64))

# Function to decode a 4bpp tile
def decode_tile(tile_data):
    pixels = []
    for row in range(8):
        row_pixels = []
        bp0 = tile_data[row * 2]
        bp1 = tile_data[row * 2 + 1]
        bp2 = tile_data[row * 2 + 16]
        bp3 = tile_data[row * 2 + 17]

        for col in range(8):
            bit = 7 - col
            pixel = ((bp0 >> bit) & 1) | \
                    (((bp1 >> bit) & 1) << 1) | \
                    (((bp2 >> bit) & 1) << 2) | \
                    (((bp3 >> bit) & 1) << 3)
            row_pixels.append(pixel)
        pixels.append(row_pixels)
    return pixels

# Draw Kirby tiles in a grid
tiles_per_row = 16
tile_size = 8
scale = 2

for tile_num in range(min(0x40, 0x40)):  # First 64 tiles
    tile_offset = kirby_offset + tile_num * 32
    tile_data = vram[tile_offset:tile_offset + 32]

    if any(tile_data):  # Skip empty tiles
        pixels = decode_tile(tile_data)

        # Get tile position in grid
        grid_x = (tile_num % tiles_per_row) * tile_size * scale
        grid_y = (tile_num // tiles_per_row) * tile_size * scale

        # Draw with first found palette
        if palettes_used:
            pal_idx = sorted(palettes_used)[0]

            # Get palette colors
            palette_colors = []
            for i in range(16):
                offset = (pal_idx * 16 + i) * 2
                bgr555 = struct.unpack("<H", cgram[offset:offset+2])[0]
                r = ((bgr555 >> 0) & 0x1F) * 8
                g = ((bgr555 >> 5) & 0x1F) * 8
                b = ((bgr555 >> 10) & 0x1F) * 8
                palette_colors.append((r, g, b))

            # Draw the tile
            for y in range(8):
                for x in range(8):
                    pixel_idx = pixels[y][x]
                    color = palette_colors[pixel_idx] if pixel_idx > 0 else (0, 0, 0)

                    # Draw scaled pixel
                    for sy in range(scale):
                        for sx in range(scale):
                            img.putpixel((grid_x + x * scale + sx, grid_y + y * scale + sy), color)

img.save("mss_kirby_sprites.png")
print("Saved Kirby sprites to mss_kirby_sprites.png")
