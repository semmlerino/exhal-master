#!/usr/bin/env python3
"""Find PAL ROM sprite locations by searching for VRAM patterns."""

import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

def find_all_compressed(rom_data: bytes) -> list[tuple[int, bytes]]:
    """
    Find all HAL-compressed blocks in ROM data.

    This function scans ROM data for HAL-compressed data blocks by looking for
    compression signatures and attempting decompression. HAL compression is used
    in Kirby Super Star and related games for sprite and tilemap data.

    Args:
        rom_data: Raw ROM data bytes to scan for compressed blocks

    Returns:
        List of tuples containing:
        - offset: Starting position of compressed block in ROM
        - decompressed_data: Decompressed bytes from that block

    Note:
        This is a placeholder implementation. The actual implementation would:
        1. Scan for HAL compression headers/signatures
        2. Attempt decompression using the exhal tool
        3. Validate decompressed data
        4. Return valid decompressed blocks
    """
    # TODO: Implement actual HAL compression detection and decompression
    # This would require integrating with the exhal tool or implementing
    # the HAL decompression algorithm directly
    print("WARNING: find_all_compressed is not yet implemented")
    return []


def search_for_vram_patterns(rom_path: str, vram_samples: list[bytes]):
    """Search ROM for patterns matching VRAM sprite data."""
    print(f"Searching ROM: {rom_path}")

    rom_path_obj = Path(rom_path)
    with rom_path_obj.open("rb") as f:
        rom_data = f.read()

    # Find all compressed blocks
    compressed_blocks = find_all_compressed(rom_data)
    print(f"Found {len(compressed_blocks)} compressed blocks")

    matches = []

    for i, (offset, decompressed) in enumerate(compressed_blocks):
        if i % 100 == 0:
            print(f"  Checking block {i}/{len(compressed_blocks)}...")

        # Check if this block contains any of our VRAM patterns
        for pattern_name, pattern_data in vram_samples:
            # Look for pattern at various offsets within the decompressed data
            for test_offset in [0, 512, 1024, 2048, 4096, 8192]:
                if test_offset + len(pattern_data) <= len(decompressed):
                    test_data = decompressed[test_offset:test_offset + len(pattern_data)]

                    # Calculate similarity
                    matching_bytes = sum(1 for a, b in zip(pattern_data, test_data) if a == b)
                    similarity = matching_bytes / len(pattern_data)

                    if similarity > 0.7:  # 70% match threshold
                        matches.append({
                            "rom_offset": offset,
                            "block_offset": test_offset,
                            "pattern": pattern_name,
                            "similarity": similarity,
                            "size": len(decompressed)
                        })
                        print(f"\n  MATCH! Offset 0x{offset:06X}+0x{test_offset:04X}: "
                              f"{pattern_name} ({similarity:.1%} similar)")

    return matches

def extract_vram_samples():
    """Extract sample patterns from VRAM dumps."""
    samples = []

    # Check for VRAM region files
    vram_files = list(Path().glob("vram_*_VRAM.dmp_*.bin"))

    for vram_file in vram_files:
        with vram_file.open("rb") as f:
            data = f.read()

        # Take first 256 bytes as sample (8 tiles)
        if len(data) >= 256:
            sample = data[:256]
            samples.append((vram_file.stem, sample))
            print(f"Loaded sample from {vram_file.name}")

    return samples

def main():
    # Find PAL ROM
    rom_files = list(Path().glob("*.sfc")) + list(Path().glob("*.smc"))
    pal_rom = None

    for rom_file in rom_files:
        if "Fun Pak" in rom_file.name or "PAL" in rom_file.name:
            pal_rom = rom_file
            break

    if not pal_rom:
        print("No PAL ROM found (looking for 'Fun Pak' or 'PAL' in filename)")
        return

    # Extract VRAM samples
    vram_samples = extract_vram_samples()

    if not vram_samples:
        print("No VRAM samples found. Run extract_vram_from_mss.py first.")
        return

    print(f"\nSearching with {len(vram_samples)} VRAM samples...")

    # Search ROM
    matches = search_for_vram_patterns(str(pal_rom), vram_samples)

    # Report results
    print(f"\n{'='*60}")
    print(f"RESULTS: Found {len(matches)} potential sprite locations")
    print("="*60)

    if matches:
        # Group by ROM offset
        by_offset = {}
        for match in matches:
            offset = match["rom_offset"]
            if offset not in by_offset:
                by_offset[offset] = []
            by_offset[offset].append(match)

        print("\nTop sprite locations:")
        for offset in sorted(by_offset.keys())[:10]:
            matches_at_offset = by_offset[offset]
            print(f"\n0x{offset:06X} (size: {matches_at_offset[0]['size']} bytes):")
            for match in matches_at_offset:
                print(f"  - {match['pattern']} at +0x{match['block_offset']:04X} "
                      f"({match['similarity']:.1%} match)")

        # Save results
        output_file = "pal_sprite_locations.txt"
        output_path = Path(output_file)
        with output_path.open("w") as f:
            f.write("PAL ROM Sprite Locations\n")
            f.write("========================\n\n")

            for offset in sorted(by_offset.keys()):
                matches_at_offset = by_offset[offset]
                f.write(f"Offset 0x{offset:06X}:\n")
                for match in matches_at_offset:
                    f.write(f"  {match['pattern']} at +0x{match['block_offset']:04X} "
                           f"({match['similarity']:.1%} match)\n")
                f.write("\n")

        print(f"\nResults saved to {output_file}")

if __name__ == "__main__":
    main()
