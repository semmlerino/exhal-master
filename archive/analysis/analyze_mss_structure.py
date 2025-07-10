#!/usr/bin/env python3
"""Analyze the structure of decompressed MSS savestate data"""

import json
import struct

# Read decompressed data
with open("mss_decompressed.bin", "rb") as f:
    data = f.read()

print(f"Total decompressed size: {len(data)} bytes (0x{len(data):X})")

# Known SNES memory sizes
VRAM_SIZE = 65536    # 64KB
CGRAM_SIZE = 512     # 256 colors * 2 bytes
OAM_SIZE = 544       # 128 sprites * 4 bytes + 32 bytes
WRAM_SIZE = 131072   # 128KB

# Try to identify sections by looking for patterns
print("\n=== Searching for memory blocks ===")

# Method 1: Look for specific offsets that might contain these blocks
possible_offsets = []

# VRAM is likely early in the savestate
if len(data) >= VRAM_SIZE:
    print("\nChecking for VRAM (64KB)...")
    # VRAM at offset 0?
    vram_candidate = data[0:VRAM_SIZE]
    non_zero = sum(1 for b in vram_candidate if b != 0)
    print(f"  Offset 0x0000: {non_zero}/{VRAM_SIZE} non-zero bytes ({non_zero*100//VRAM_SIZE}%)")

    # Check some known VRAM patterns
    # Look for tile data (repeating patterns every 32 bytes for 8x8 4bpp tiles)
    tile_like = 0
    for i in range(0, min(0x8000, len(vram_candidate)), 32):
        tile = vram_candidate[i:i+32]
        if any(tile) and not all(b == tile[0] for b in tile):
            tile_like += 1
    print(f"  Tile-like patterns: {tile_like}")

# Search for OAM (544 bytes) - sprite data with specific structure
print("\nSearching for OAM (544 bytes)...")
for offset in range(0, len(data) - OAM_SIZE, 16):
    oam_candidate = data[offset:offset + OAM_SIZE]

    # Check if this looks like OAM data
    # First 512 bytes: sprite entries (x, y, tile, attr)
    valid_sprites = 0
    for i in range(0, 512, 4):
        x = oam_candidate[i]
        y = oam_candidate[i + 1]
        tile = oam_candidate[i + 2]
        attr = oam_candidate[i + 3]

        # Count sprites that look valid (on-screen positions)
        if y < 240:  # Y should be < 240 for visible sprites
            valid_sprites += 1

    # If we have a reasonable number of valid sprites
    if valid_sprites > 10:
        print(f"  Possible OAM at offset 0x{offset:X} ({valid_sprites} valid sprites)")
        possible_offsets.append(("OAM", offset, OAM_SIZE))

        # Show first few sprites
        print("    First 5 sprites:")
        for i in range(0, min(20, 512), 4):
            x = oam_candidate[i]
            y = oam_candidate[i + 1]
            tile = oam_candidate[i + 2]
            attr = oam_candidate[i + 3]
            pal = (attr >> 1) & 7
            print(f"      Sprite {i//4}: pos=({x},{y}) tile=0x{tile:02X} pal={pal+8}")
        break

# Search for CGRAM (512 bytes) - palette data
print("\nSearching for CGRAM (512 bytes)...")
for offset in range(0, len(data) - CGRAM_SIZE, 16):
    cgram_candidate = data[offset:offset + CGRAM_SIZE]

    # Check if this looks like palette data (BGR555 format)
    valid_colors = 0
    for i in range(0, CGRAM_SIZE, 2):
        color = struct.unpack("<H", cgram_candidate[i:i+2])[0]
        # BGR555: bit 15 should be 0
        if (color & 0x8000) == 0:
            valid_colors += 1

    # If most values are valid BGR555
    if valid_colors > 240:  # At least 240/256 valid colors
        print(f"  Possible CGRAM at offset 0x{offset:X} ({valid_colors}/256 valid colors)")
        possible_offsets.append(("CGRAM", offset, CGRAM_SIZE))

        # Show first palette
        print("    Palette 0:")
        for i in range(0, 32, 2):
            bgr555 = struct.unpack("<H", cgram_candidate[i:i+2])[0]
            r = ((bgr555 >> 0) & 0x1F) * 8
            g = ((bgr555 >> 5) & 0x1F) * 8
            b = ((bgr555 >> 10) & 0x1F) * 8
            print(f"      Color {i//2}: RGB({r:3d}, {g:3d}, {b:3d})")
        break

# Method 2: Look at specific offsets based on common savestate layouts
print("\n=== Checking common savestate layout patterns ===")

# Common pattern: VRAM, CGRAM, OAM, then other data
offset = 0

# Check if VRAM is at start
if len(data) >= VRAM_SIZE:
    print(f"\nVRAM at offset 0x{offset:X}? Checking...")
    vram_data = data[offset:offset + VRAM_SIZE]

    # Look for Kirby sprites at VRAM $6000 (0xC000 in bytes)
    kirby_offset = 0xC000
    if kirby_offset + 0x800 <= len(vram_data):
        kirby_area = vram_data[kirby_offset:kirby_offset + 0x800]
        non_zero = sum(1 for b in kirby_area if b != 0)
        print(f"  Kirby sprite area (VRAM $6000): {non_zero}/2048 non-zero bytes")

        if non_zero > 100:
            print("  -> Likely contains sprite data!")

            # Save VRAM
            with open("mss_extracted_vram.bin", "wb") as f:
                f.write(vram_data)
            print("  Saved to mss_extracted_vram.bin")

    offset += VRAM_SIZE

# Check for CGRAM after VRAM
if offset + CGRAM_SIZE <= len(data):
    print(f"\nCGRAM at offset 0x{offset:X}? Checking...")
    cgram_data = data[offset:offset + CGRAM_SIZE]

    # Validate as palette data
    valid = True
    for i in range(0, CGRAM_SIZE, 2):
        color = struct.unpack("<H", cgram_data[i:i+2])[0]
        if color & 0x8000:  # Invalid BGR555
            valid = False
            break

    if valid:
        print("  -> Valid CGRAM data!")
        with open("mss_extracted_cgram.bin", "wb") as f:
            f.write(cgram_data)
        print("  Saved to mss_extracted_cgram.bin")

        # Show sprite palettes (8-15)
        print("  Sprite palettes:")
        for pal in range(8, 16):
            print(f"    Palette {pal}:", end="")
            for col in range(4):  # Show first 4 colors
                idx = (pal * 16 + col) * 2
                bgr555 = struct.unpack("<H", cgram_data[idx:idx+2])[0]
                r = ((bgr555 >> 0) & 0x1F) * 8
                g = ((bgr555 >> 5) & 0x1F) * 8
                b = ((bgr555 >> 10) & 0x1F) * 8
                print(f" ({r},{g},{b})", end="")
            print()

    offset += CGRAM_SIZE

# Check for OAM after CGRAM
if offset + OAM_SIZE <= len(data):
    print(f"\nOAM at offset 0x{offset:X}? Checking...")
    oam_data = data[offset:offset + OAM_SIZE]

    # Count valid sprites
    valid_sprites = 0
    active_sprites = []
    for i in range(0, 512, 4):
        x = oam_data[i]
        y = oam_data[i + 1]
        tile = oam_data[i + 2]
        attr = oam_data[i + 3]

        if y < 240 and tile != 0:  # Visible and has a tile
            valid_sprites += 1
            pal = (attr >> 1) & 7
            active_sprites.append({
                "index": i // 4,
                "x": x, "y": y,
                "tile": tile,
                "palette": pal + 8
            })

    print(f"  Found {valid_sprites} active sprites")
    if valid_sprites > 0:
        print("  -> Valid OAM data!")
        with open("mss_extracted_oam.bin", "wb") as f:
            f.write(oam_data)
        print("  Saved to mss_extracted_oam.bin")

        # Save sprite mappings
        with open("mss_sprite_mappings.json", "w") as f:
            json.dump(active_sprites, f, indent=2)
        print("  Saved sprite mappings to mss_sprite_mappings.json")

        # Show some active sprites
        print("  Sample active sprites:")
        for sprite in active_sprites[:5]:
            print(f"    Sprite {sprite['index']}: Tile 0x{sprite['tile']:02X} at ({sprite['x']},{sprite['y']}) using Palette {sprite['palette']}")

print("\n=== Summary ===")
print("Savestate appears to contain:")
print("  VRAM:  0x00000-0x0FFFF (64KB)")
print("  CGRAM: 0x10000-0x101FF (512 bytes)")
print("  OAM:   0x10200-0x1041F (544 bytes)")
print(f"  Other: 0x10420-0x{len(data):X} ({len(data)-0x10420} bytes)")
