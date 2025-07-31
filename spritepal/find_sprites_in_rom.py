#!/usr/bin/env python3
"""
Search for VRAM sprite patterns in ROM
"""

import os
import sys
import tempfile

# Add parent directory to path for imports
parent_dir = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, parent_dir)

# Import after path setup
from spritepal.core.hal_compression import HALCompressor


def extract_kirby_patterns(vram_path: str):
    """Extract known Kirby sprite patterns from VRAM"""

    with open(vram_path, "rb") as f:
        vram_data = f.read()

    # Common Kirby sprite locations in VRAM
    kirby_offsets = [
        0xC000,  # Often Kirby's main sprites
        0xC800,  # Alternative location
        0xD000,  # Sometimes used for Kirby
    ]

    patterns = []
    for offset in kirby_offsets:
        if offset + 256 <= len(vram_data):  # Get 8 tiles (256 bytes)
            pattern = vram_data[offset:offset + 256]
            # Check if pattern has data
            non_zero = sum(1 for b in pattern if b != 0)
            if non_zero > 32:  # At least 1 tile worth of data
                patterns.append((offset, pattern))
                print(f"Extracted pattern from VRAM 0x{offset:04X} ({non_zero} non-zero bytes)")
                # Show first tile for debugging
                print(f"  First 16 bytes: {' '.join(f'{b:02X}' for b in pattern[:16])}")

    return patterns


def search_rom_compressed(rom_path: str, patterns: list[bytes]):
    """Search for patterns in compressed ROM data"""

    print(f"\nSearching ROM: {rom_path}")

    with open(rom_path, "rb") as f:
        rom_data = f.read()

    compressor = HALCompressor()

    # Focus on known sprite regions
    search_ranges = [
        (0xC0000, 0xD0000),  # Main sprite area
        (0xE0000, 0xF0000),  # Additional sprites
    ]

    found_locations = []

    for start, end in search_ranges:
        print(f"\nScanning range: 0x{start:06X}-0x{end:06X}")
        successful_decompressions = 0

        for offset in range(start, min(end, len(rom_data)), 0x100):
            if (offset - start) % 0x1000 == 0:
                print(f"  Progress: 0x{offset:06X}...")
            try:
                # Create temp file for decompression
                with tempfile.NamedTemporaryFile(delete=False) as tmp:
                    tmp.write(rom_data)
                    tmp_path = tmp.name

                # Try to decompress
                decompressed = compressor.decompress_from_rom(tmp_path, offset)
                os.unlink(tmp_path)

                if len(decompressed) > 256:
                    successful_decompressions += 1
                    # Search for each pattern
                    for vram_offset, pattern in patterns:
                        # Look for partial matches (first 16 bytes of tile)
                        pos = decompressed.find(pattern[:16])  # Half tile
                        if pos != -1:
                            # Verify it's a good match by checking more bytes
                            if pos + 32 <= len(decompressed):
                                match_quality = sum(1 for i in range(32) if decompressed[pos+i] == pattern[i])
                                if match_quality >= 16:  # At least 50% match
                                    print(f"  MATCH! ROM 0x{offset:06X} contains VRAM pattern from 0x{vram_offset:04X} at position +{pos} (quality: {match_quality}/32)")
                                    found_locations.append((offset, vram_offset, pos))

                        # Also check for pattern at common embedded offsets
                        for embed_offset in [512, 1024, 2048, 4096]:
                            if embed_offset + 32 <= len(decompressed):
                                if decompressed[embed_offset:embed_offset + 32] == pattern[:32]:
                                    print(f"  EMBEDDED MATCH! ROM 0x{offset:06X} contains VRAM 0x{vram_offset:04X} at +{embed_offset}")
                                    found_locations.append((offset, vram_offset, embed_offset))

            except Exception:
                # Decompression failed, continue
                continue

        print(f"  Successful decompressions in range: {successful_decompressions}")

    return found_locations


def main():
    if len(sys.argv) < 3:
        print("Usage: python find_sprites_in_rom.py <vram_dump> <rom_file>")
        return

    vram_path = sys.argv[1]
    rom_path = sys.argv[2]

    if not os.path.exists(vram_path):
        print(f"VRAM dump not found: {vram_path}")
        return

    if not os.path.exists(rom_path):
        print(f"ROM not found: {rom_path}")
        return

    # Extract patterns from VRAM
    patterns = extract_kirby_patterns(vram_path)
    print(f"\nExtracted {len(patterns)} patterns from VRAM")

    # Search ROM
    locations = search_rom_compressed(rom_path, patterns)

    print(f"\n{'='*60}")
    print(f"Summary: Found {len(locations)} matches")
    if locations:
        print("\nBest candidates for sprite locations:")
        for rom_offset, vram_offset, position in locations[:10]:
            print(f"  ROM 0x{rom_offset:06X} (VRAM 0x{vram_offset:04X} at +{position})")


if __name__ == "__main__":
    main()
