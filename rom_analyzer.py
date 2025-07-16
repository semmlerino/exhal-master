#!/usr/bin/env python3
"""
Analyze Kirby Super Star ROM structure based on documentation
"""

import struct
import sys


def snes_to_pc(addr):
    """Convert SNES address to PC offset."""
    bank = (addr >> 16) & 0xFF
    offset = addr & 0xFFFF
    if offset < 0x8000:
        return None
    return ((bank & 0x7F) << 15) | (offset & 0x7FFF)


def pc_to_snes(pc):
    """Convert PC offset to SNES address."""
    return ((pc & 0x7F8000) << 1) | (pc & 0x7FFF) | 0x8000


def read_pointer_table(rom_data, table_offset, num_entries, pointer_size=3):
    """Read a table of SNES pointers."""
    pointers = []
    for i in range(num_entries):
        offset = table_offset + (i * pointer_size * 4)  # 4 pointers per entry
        entry = []
        for j in range(4):
            ptr_offset = offset + (j * pointer_size)
            if pointer_size == 3:
                ptr = (
                    struct.unpack_from("<I", rom_data + b"\x00", ptr_offset)[0]
                    & 0xFFFFFF
                )
                entry.append(ptr)
        pointers.append(entry)
    return pointers


def main():
    if len(sys.argv) < 2:
        print("Usage: python rom_analyzer.py 'Kirby Super Star (USA).sfc'")
        sys.exit(1)

    rom_file = sys.argv[1]

    with open(rom_file, "rb") as f:
        rom_data = f.read()

    print(f"ROM size: {len(rom_data):,} bytes ({len(rom_data)//1024//1024} MB)")
    print()

    # Master pointer tables at bank $FF
    print("=== Master Pointer Tables (Bank $FF) ===")
    room_ptr_table = 0x3F0000  # Direct PC offset for $FF:0000
    gfx_ptr_table = 0x3F0002  # Direct PC offset for $FF:0002
    level_ptr_table = 0x3F000C  # Direct PC offset for $FF:000C

    print(f"Room pointer table:     PC 0x{room_ptr_table:06X}")
    print(f"GFX/Palette ptr table:  PC 0x{gfx_ptr_table:06X}")
    print(f"Level pointer table:    PC 0x{level_ptr_table:06X}")
    print()

    # Read some sprite GFX indices
    print("=== Sample Sprite GFX Indices ===")
    indices = [0x4E, 0x57, 0x15, 0x03]  # From Green Greens

    for idx in indices:
        offset = gfx_ptr_table + (idx * 12)  # 4 pointers × 3 bytes
        print(f"\nIndex 0x{idx:02X}:")
        for i in range(4):
            ptr_bytes = rom_data[offset + i * 3 : offset + i * 3 + 3]
            ptr = struct.unpack("<I", ptr_bytes + b"\x00")[0] & 0xFFFFFF
            pc_offset = snes_to_pc(ptr)
            print(f"  Pointer {i+1}: ${ptr:06X} -> PC 0x{pc_offset:06X}")

    # Known sprite locations
    print("\n=== Known Sprite Locations ===")
    print("Default Kirby sprites:  PC 0x26B400 (Bank $9B)")
    print("Mike/Ball abilities:    Bank $8C (PC 0x060000)")
    print("UFO Kirby:             Bank $C6 (PC 0x230000)")

    # Check compression at known location
    print("\n=== Compression Check ===")
    offset = 0x26B400
    header = struct.unpack_from("<H", rom_data, offset)[0]
    print(f"Data at 0x{offset:06X}: 0x{header:04X}")
    print("(HAL compression typically starts with size header)")


if __name__ == "__main__":
    main()
