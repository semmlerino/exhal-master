#!/usr/bin/env python3
"""
Analyze OAM (Object Attribute Memory) dump to understand sprite-palette assignments
"""

import sys


def analyze_oam(filename="OAM.dmp"):
    """Analyze OAM dump to understand sprite attributes and palette assignments"""

    with open(filename, "rb") as f:
        oam_data = f.read()

    print(f"OAM dump size: {len(oam_data)} bytes")
    print("Expected: 544 bytes (512 main + 32 high table)\n")

    # OAM structure (128 sprites, 4 bytes each in main table)
    # Byte 0: X position (low 8 bits)
    # Byte 1: Y position
    # Byte 2: Tile number (low 8 bits)
    # Byte 3: Attributes:
    #   bit 0-2: Palette number (0-7)
    #   bit 3-4: Priority
    #   bit 5: H-flip
    #   bit 6: V-flip
    #   bit 7: Tile number (bit 8)

    print("=== OAM Main Table Analysis ===")
    print("Sprite | X    Y  | Tile | Pal | Pri | H-Flip | V-Flip | Size")
    print("-------|----------|------|-----|-----|--------|--------|------")

    # Analyze main OAM table (first 512 bytes)
    palette_usage = {}
    active_sprites = 0

    for i in range(128):
        offset = i * 4
        if offset + 4 > len(oam_data):
            break

        x_pos = oam_data[offset]
        y_pos = oam_data[offset + 1]
        tile_low = oam_data[offset + 2]
        attributes = oam_data[offset + 3]

        # Extract attribute bits
        palette = attributes & 0x07  # bits 0-2
        priority = (attributes >> 3) & 0x03  # bits 3-4
        h_flip = (attributes >> 5) & 0x01  # bit 5
        v_flip = (attributes >> 6) & 0x01  # bit 6
        tile_high = (attributes >> 7) & 0x01  # bit 7

        tile_num = (tile_high << 8) | tile_low

        # Get size from high table
        high_table_offset = 512 + (i // 4)
        if high_table_offset < len(oam_data):
            high_byte = oam_data[high_table_offset]
            bit_offset = (i % 4) * 2
            size_x_high = (high_byte >> bit_offset) & 0x01
            size_bit = (high_byte >> (bit_offset + 1)) & 0x01

            # Combine with X position high bit
            x_full = x_pos | (size_x_high << 8)

            # Determine sprite size
            size = "Large" if size_bit else "Small"
        else:
            x_full = x_pos
            size = "?"

        # Check if sprite is active (not off-screen)
        if y_pos < 0xE0:  # Y < 224 means on-screen
            active_sprites += 1

            # Track palette usage
            if palette not in palette_usage:
                palette_usage[palette] = 0
            palette_usage[palette] += 1

            print(f"#{i:03d}  | {x_full:3d}, {y_pos:3d} | ${tile_num:03X} |  {palette}  |  {priority}  |   {'Y' if h_flip else 'N'}    |   {'Y' if v_flip else 'N'}    | {size}")

    print("\n=== Summary ===")
    print(f"Active sprites: {active_sprites}")
    print("\nPalette usage:")
    for pal, count in sorted(palette_usage.items()):
        print(f"  Palette {pal}: {count} sprites")

    # Analyze high table
    print("\n=== High Table (Size/X-high bits) ===")
    print("Bytes 512-543 contain size and X position high bits")
    print("Each byte contains data for 4 sprites:")

    for i in range(32):
        offset = 512 + i
        if offset < len(oam_data):
            byte = oam_data[offset]
            print(f"  Byte {offset}: ${byte:02X} = {byte:08b}")
            for j in range(4):
                sprite_num = i * 4 + j
                if sprite_num < 128:
                    bit_offset = j * 2
                    x_high = (byte >> bit_offset) & 0x01
                    size = (byte >> (bit_offset + 1)) & 0x01
                    print(f"    Sprite {sprite_num:3d}: X-high={x_high}, Size={'Large' if size else 'Small'}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        analyze_oam(sys.argv[1])
    else:
        analyze_oam()
