#!/usr/bin/env python3
"""Analyze MSS savestate format to find memory regions."""

import os
import struct


def find_pattern(data, pattern, name):
    """Find a known pattern in the data."""
    found = []
    pattern_bytes = bytes(pattern)

    for i in range(len(data) - len(pattern_bytes)):
        if data[i:i+len(pattern_bytes)] == pattern_bytes:
            found.append(i)

    if found:
        print(f"{name} pattern found at offsets: {found[:5]}{'...' if len(found) > 5 else ''}")
    return found

def analyze_mss_structure(filename):
    """Analyze MSS file structure."""
    with open(filename, "rb") as f:
        data = f.read()

    print(f"File: {filename}")
    print(f"Total size: {len(data)} bytes (0x{len(data):X})")
    print()

    # Look for header
    print("=== Header Analysis ===")
    print(f"First 32 bytes: {data[:32].hex()}")

    # Try to find ASCII header
    header_text = ""
    for i in range(32):
        if 32 <= data[i] <= 126:
            header_text += chr(data[i])
        else:
            header_text += "."
    print(f"Header as text: {header_text}")

    # Look for known patterns
    print("\n=== Pattern Search ===")

    # Check if we have VRAM data by looking for known tile patterns
    # In VRAM, tiles are often aligned and have patterns

    # Check different offsets that might contain VRAM

    # Also scan for large aligned regions
    print("\n=== Scanning for large regions ===")

    # Find potential VRAM (65536 bytes)
    for offset in range(0, len(data) - 65536, 0x10):
        # Check if this looks like VRAM (has some structure)
        region = data[offset:offset+256]
        # VRAM often has patterns of zeros and non-zeros
        zero_count = sum(1 for b in region if b == 0)
        if 50 < zero_count < 200:  # Not all zeros, not all data
            print(f"Potential VRAM at 0x{offset:X}")
            if offset < 0x30000:  # Only check first few
                break

    # Look for CGRAM (512 bytes of color data)
    # CGRAM has 16-bit color values, often with patterns
    print("\n=== Looking for CGRAM ===")
    for offset in range(0, len(data) - 512, 0x10):
        region = data[offset:offset+32]
        # Check if it looks like color data (16-bit values)
        looks_like_colors = True
        for i in range(0, 32, 2):
            val = struct.unpack("<H", region[i:i+2])[0]
            # SNES colors use 15 bits (0x7FFF max)
            if val > 0x7FFF:
                looks_like_colors = False
                break

        if looks_like_colors and any(region):  # Not all zeros
            print(f"Potential CGRAM at 0x{offset:X}")
            # Show first few colors
            for i in range(0, 16, 2):
                val = struct.unpack("<H", data[offset+i:offset+i+2])[0]
                r = (val & 0x1F) << 3
                g = ((val >> 5) & 0x1F) << 3
                b = ((val >> 10) & 0x1F) << 3
                print(f"  Color {i//2}: RGB({r},{g},{b})")
            break

    # Look for OAM (544 bytes)
    print("\n=== Looking for OAM ===")
    # OAM has specific structure - 128 4-byte entries + 32 bytes high table
    for offset in range(0, len(data) - 544, 0x10):
        region = data[offset:offset+16]
        # Check if it looks like sprite data
        looks_like_oam = True
        for i in range(0, 16, 4):
            if i+3 < len(region):
                x = region[i]
                y = region[i+1]
                # Y coordinates > 224 are off-screen
                if y > 240 and y != 0xFF:
                    looks_like_oam = False
                    break

        if looks_like_oam and any(region):
            print(f"Potential OAM at 0x{offset:X}")
            # Show first few sprites
            for i in range(0, 16, 4):
                x = data[offset+i]
                y = data[offset+i+1]
                tile = data[offset+i+2]
                attrs = data[offset+i+3]
                palette = (attrs >> 1) & 0x07
                print(f"  Sprite {i//4}: X={x}, Y={y}, Tile={tile}, Palette={palette}")
            break

    # Try to identify structure based on file size
    print("\n=== Size-based Analysis ===")
    # Common MSS sizes and their meanings
    if len(data) == 122923:
        print("Size matches ZSNES savestate")
    elif len(data) == 197632:
        print("Size matches Snes9x savestate")
    elif len(data) == 187394:
        print("Size matches compact savestate format")

    # Check for compression
    print("\n=== Compression Check ===")
    # Look for zlib header
    if data[:2] == b"\x78\x9c" or data[:2] == b"\x78\xda":
        print("File appears to be zlib compressed")
    # Look for gzip header
    elif data[:2] == b"\x1f\x8b":
        print("File appears to be gzip compressed")
    else:
        print("No obvious compression detected")

def compare_dumps():
    """Compare the dump files we have."""
    print("\n=== Comparing Dump Files ===")

    dump_sets = [
        ("SnesVideoRam.VRAM.dmp", "SnesCgRam.dmp", "SnesSpriteRam.OAM.dmp"),
        ("Cave.SnesVideoRam.dmp", "Cave.SnesCgRam.dmp", "Cave.SnesSpriteRam.dmp"),
    ]

    for vram_file, cgram_file, oam_file in dump_sets:
        if os.path.exists(vram_file):
            print(f"\n{vram_file}: {os.path.getsize(vram_file)} bytes")
            with open(vram_file, "rb") as f:
                vram = f.read()
                # Show first few non-zero bytes
                for i in range(min(256, len(vram))):
                    if vram[i] != 0:
                        print(f"  First non-zero at 0x{i:X}: 0x{vram[i]:02X}")
                        break

        if os.path.exists(cgram_file):
            print(f"{cgram_file}: {os.path.getsize(cgram_file)} bytes")
            with open(cgram_file, "rb") as f:
                cgram = f.read()
                # Show first palette
                print("  First palette colors:")
                for i in range(0, 32, 2):
                    val = struct.unpack("<H", cgram[i:i+2])[0]
                    r = (val & 0x1F) << 3
                    g = ((val >> 5) & 0x1F) << 3
                    b = ((val >> 10) & 0x1F) << 3
                    print(f"    Color {i//2}: RGB({r},{g},{b})")

        if os.path.exists(oam_file):
            print(f"{oam_file}: {os.path.getsize(oam_file)} bytes")
            with open(oam_file, "rb") as f:
                oam = f.read()
                # Show first few sprites
                print("  First few sprites:")
                for i in range(0, min(20, len(oam)), 4):
                    if i+3 < len(oam):
                        x = oam[i]
                        y = oam[i+1]
                        tile = oam[i+2]
                        attrs = oam[i+3]
                        palette = (attrs >> 1) & 0x07
                        if y < 224:  # On screen
                            print(f"    Sprite {i//4}: X={x}, Y={y}, Tile=0x{tile:02X}, Palette={palette}")

if __name__ == "__main__":
    # Analyze MSS files
    for mss_file in ["Kirby Super Star (USA)_2.mss", "Kirby Super Star (USA)_1.mss"]:
        if os.path.exists(mss_file):
            analyze_mss_structure(mss_file)
            print("\n" + "="*60 + "\n")

    # Compare dump files
    compare_dumps()
