#!/usr/bin/env python3
"""
Parse Mesen-S savestate (.mss) files to extract PPU state, OAM data, and palette mappings.

Mesen-S savestate format:
- Header: "MSS" + version info
- Compressed data (likely zlib or similar)
"""

import gzip
import json
import struct
import zlib
from pathlib import Path


def parse_mss_header(data):
    """Parse the MSS file header"""
    if data[:3] != b"MSS":
        raise ValueError("Not a valid MSS file (missing MSS signature)")

    # Header structure (based on observation):
    # 0x00-0x02: "MSS" signature
    # 0x03: Version byte (0x01)
    # 0x04-0x0F: Unknown fields
    # 0x10-0x13: Decompressed size (little-endian)
    # 0x14-0x1F: Unknown fields
    # 0x20+: Compressed data (zlib)

    return {
        "signature": data[:3].decode("ascii"),
        "version": data[3],
        "decompressed_size": struct.unpack("<I", data[0x10:0x14])[0],
        "compressed_offset": 0x20  # Fixed offset where zlib data starts
    }



def decompress_mss_data(data, offset=0x20):
    """Try to decompress the savestate data"""
    compressed_data = data[offset:]

    # Try different compression methods
    decompressed = None

    # Try zlib
    try:
        decompressed = zlib.decompress(compressed_data)
        print("Successfully decompressed with zlib")
        return decompressed
    except:
        pass

    # Try zlib with different window bits (for raw deflate)
    for wbits in [-15, -8, 15, 31, 47]:
        try:
            decompressed = zlib.decompress(compressed_data, wbits)
            print(f"Successfully decompressed with zlib (wbits={wbits})")
            return decompressed
        except:
            pass

    # Try gzip
    try:
        decompressed = gzip.decompress(compressed_data)
        print("Successfully decompressed with gzip")
        return decompressed
    except:
        pass

    print("Could not decompress data, returning raw")
    return compressed_data


def find_snes_data_blocks(data):
    """Search for SNES hardware state blocks in the decompressed data"""
    blocks = {}

    # Common SNES memory sizes

    # Try to find blocks by searching for patterns or sizes
    print(f"\nTotal decompressed size: {len(data)} bytes")

    # Look for potential VRAM block (64KB of data)
    if len(data) >= 65536:
        print("\nSearching for VRAM block (64KB)...")
        # VRAM might be at a specific offset
        for offset in range(0, min(len(data) - 65536, 0x10000), 0x100):
            # Check if this looks like VRAM data (non-zero, varied data)
            candidate = data[offset:offset + 65536]
            non_zero = sum(1 for b in candidate[:1000] if b != 0)
            if non_zero > 500:  # At least 50% non-zero in first 1KB
                blocks["VRAM"] = (offset, candidate)
                print(f"Found potential VRAM at offset 0x{offset:X}")
                break

    # Look for CGRAM (palette data) - 512 bytes
    if len(data) >= 512:
        print("\nSearching for CGRAM block (512 bytes)...")
        for offset in range(0, min(len(data) - 512, 0x10000), 0x10):
            candidate = data[offset:offset + 512]
            # Palette data should have varied 16-bit values
            if is_palette_data(candidate):
                blocks["CGRAM"] = (offset, candidate)
                print(f"Found potential CGRAM at offset 0x{offset:X}")
                break

    # Look for OAM data - 544 bytes
    if len(data) >= 544:
        print("\nSearching for OAM block (544 bytes)...")
        for offset in range(0, min(len(data) - 544, 0x10000), 0x10):
            candidate = data[offset:offset + 544]
            if is_oam_data(candidate):
                blocks["OAM"] = (offset, candidate)
                print(f"Found potential OAM at offset 0x{offset:X}")
                break

    return blocks


def is_palette_data(data):
    """Check if data looks like SNES palette data (BGR555 format)"""
    if len(data) < 32:
        return False

    # Check first 16 colors (one palette)
    for i in range(0, 32, 2):
        color = struct.unpack("<H", data[i:i+2])[0]
        # BGR555 format: should not have high bit set
        if color & 0x8000:
            return False

    return True


def is_oam_data(data):
    """Check if data looks like OAM (sprite) data"""
    if len(data) < 544:
        return False

    # OAM has specific structure
    # First 512 bytes: 128 sprites * 4 bytes each
    # Last 32 bytes: high table (2 bits per sprite)

    # Check if sprite positions are reasonable
    reasonable_sprites = 0
    for i in range(0, 512, 4):
        x = data[i]
        y = data[i + 1]
        # Most sprites should be on-screen (0-255 range)
        if 0 <= x <= 255 and 0 <= y <= 224:
            reasonable_sprites += 1

    # At least some sprites should be on-screen
    return reasonable_sprites > 5


def extract_palette_mappings(oam_data):
    """Extract sprite-to-palette mappings from OAM data"""
    mappings = []

    # Parse main OAM table (first 512 bytes)
    for i in range(0, 512, 4):
        x = oam_data[i]
        y = oam_data[i + 1]
        tile = oam_data[i + 2]
        attrs = oam_data[i + 3]

        # Extract palette from attributes (bits 1-3)
        palette = (attrs >> 1) & 0x07

        # Get high bits from high table
        sprite_idx = i // 4
        high_byte_idx = 512 + (sprite_idx // 4)
        high_bit_shift = (sprite_idx % 4) * 2

        if high_byte_idx < len(oam_data):
            high_bits = oam_data[high_byte_idx]
            size_bit = (high_bits >> high_bit_shift) & 1
            x_msb = (high_bits >> (high_bit_shift + 1)) & 1

            # Adjust X position with MSB
            if x_msb:
                x |= 0x100
        else:
            size_bit = 0
            x_msb = 0

        mapping = {
            "sprite_index": sprite_idx,
            "x": x,
            "y": y,
            "tile": tile,
            "palette": palette + 8,  # Sprite palettes are 8-15
            "priority": (attrs >> 4) & 0x03,
            "h_flip": bool(attrs & 0x40),
            "v_flip": bool(attrs & 0x80),
            "size": size_bit,
            "visible": y < 224  # Sprite is visible if Y < 224
        }

        mappings.append(mapping)

    return mappings


def analyze_mss_savestate(filename):
    """Main function to analyze MSS savestate file"""
    print(f"Analyzing MSS savestate: {filename}")

    with open(filename, "rb") as f:
        data = f.read()

    # Parse header
    print("\n=== Header Information ===")
    try:
        header = parse_mss_header(data)
        for key, value in header.items():
            print(f"{key}: {value} (0x{value:X})" if isinstance(value, int) else f"{key}: {value}")
    except Exception as e:
        print(f"Error parsing header: {e}")
        return

    # Try to decompress
    print("\n=== Decompression ===")
    decompressed = decompress_mss_data(data, offset=header["compressed_offset"])

    # Find SNES data blocks
    print("\n=== Searching for SNES Data Blocks ===")
    blocks = find_snes_data_blocks(decompressed)

    # Save found blocks
    output_dir = Path(filename).parent

    for block_name, (offset, block_data) in blocks.items():
        output_file = output_dir / f"mss_{block_name}.dmp"
        with open(output_file, "wb") as f:
            f.write(block_data)
        print(f"\nSaved {block_name} to {output_file}")
        print(f"  Offset: 0x{offset:X}")
        print(f"  Size: {len(block_data)} bytes")

    # Extract palette mappings if OAM found
    if "OAM" in blocks:
        print("\n=== Sprite to Palette Mappings ===")
        _, oam_data = blocks["OAM"]
        mappings = extract_palette_mappings(oam_data)

        # Show active sprites
        active_sprites = [m for m in mappings if m["visible"] and m["tile"] != 0]
        print(f"\nFound {len(active_sprites)} active sprites:")

        for sprite in active_sprites[:10]:  # Show first 10
            print(f"  Sprite {sprite['sprite_index']:3d}: "
                  f"Tile 0x{sprite['tile']:02X} at ({sprite['x']:3d}, {sprite['y']:3d}) "
                  f"using Palette {sprite['palette']}")

        # Save mappings
        mappings_file = output_dir / "mss_palette_mappings.json"
        with open(mappings_file, "w") as f:
            json.dump(mappings, f, indent=2)
        print(f"\nSaved all mappings to {mappings_file}")

    # Show palette data if CGRAM found
    if "CGRAM" in blocks:
        print("\n=== Palette Data ===")
        _, cgram_data = blocks["CGRAM"]

        # Show first few palettes
        for pal_idx in range(min(4, 16)):
            print(f"\nPalette {pal_idx}:")
            colors = []
            for color_idx in range(16):
                offset = (pal_idx * 16 + color_idx) * 2
                if offset + 2 <= len(cgram_data):
                    bgr555 = struct.unpack("<H", cgram_data[offset:offset+2])[0]
                    r = ((bgr555 >> 0) & 0x1F) * 8
                    g = ((bgr555 >> 5) & 0x1F) * 8
                    b = ((bgr555 >> 10) & 0x1F) * 8
                    colors.append(f"({r:3d}, {g:3d}, {b:3d})")

            # Print colors in rows of 4
            for i in range(0, 16, 4):
                print(f"  {i:2d}-{i+3:2d}: " + " ".join(colors[i:i+4]))


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python parse_mss_savestate.py <savestate.mss>")
        sys.exit(1)

    analyze_mss_savestate(sys.argv[1])
