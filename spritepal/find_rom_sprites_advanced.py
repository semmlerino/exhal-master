#!/usr/bin/env python3
"""Advanced ROM sprite finder using VRAM patterns and HAL decompression."""

import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path


def decompress_at_offset(rom_path: str, offset: int, exhal_path: str) -> bytes:
    """Decompress data at a specific ROM offset using exhal."""
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        tmp_path = tmp.name

    try:
        # Run exhal to decompress
        cmd = [exhal_path, rom_path, hex(offset), tmp_path]
        result = subprocess.run(cmd, check=False, capture_output=True, text=True)

        if result.returncode == 0 and os.path.exists(tmp_path):
            with open(tmp_path, "rb") as f:
                return f.read()
    except Exception:
        pass
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)

    return b""

def find_exhal_tool():
    """Find the exhal executable."""
    # Check various locations
    search_paths = [
        "../archive/obsolete_test_images/ultrathink/exhal",
        "../archive/obsolete_test_images/ultrathink/exhal.exe",
        "../exhal",
        "../exhal.exe",
        "./exhal",
        "./exhal.exe"
    ]

    for path in search_paths:
        if os.path.exists(path):
            return os.path.abspath(path)

    # Try system PATH
    exhal = shutil.which("exhal")
    if exhal:
        return exhal

    print("ERROR: Could not find exhal tool!")
    print("Searched in:", search_paths)
    return None

def analyze_sprite_quality(data: bytes) -> float:
    """Analyze if data looks like sprite tiles."""
    if len(data) < 32:  # Less than one tile
        return 0.0

    score = 0.0
    bytes_per_tile = 32
    num_tiles = min(len(data) // bytes_per_tile, 16)  # Check first 16 tiles

    for tile_idx in range(num_tiles):
        tile_start = tile_idx * bytes_per_tile
        tile_data = data[tile_start:tile_start + bytes_per_tile]

        # Check for valid 4bpp patterns
        non_zero = sum(1 for b in tile_data if b != 0)
        non_ff = sum(1 for b in tile_data if b != 0xFF)

        if 8 <= non_zero <= 28 and non_ff >= 8:  # Good distribution
            score += 1.0

        # Check for repeating patterns (common in sprites)
        patterns = set()
        for i in range(0, 32, 2):
            if i + 1 < len(tile_data):
                patterns.add((tile_data[i], tile_data[i+1]))

        if 2 <= len(patterns) <= 12:  # Some variety but not random
            score += 0.5

    return score / (num_tiles * 1.5) if num_tiles > 0 else 0.0

def compare_to_vram(decompressed: bytes, vram_pattern: bytes, offsets: list[int]) -> tuple[float, int]:
    """Compare decompressed data to VRAM pattern at various offsets."""
    best_match = 0.0
    best_offset = 0

    pattern_len = min(len(vram_pattern), 256)  # Compare first 256 bytes

    for offset in offsets:
        if offset + pattern_len <= len(decompressed):
            test_data = decompressed[offset:offset + pattern_len]

            # Calculate similarity
            matches = sum(1 for a, b in zip(vram_pattern, test_data) if a == b)
            similarity = matches / pattern_len

            if similarity > best_match:
                best_match = similarity
                best_offset = offset

    return best_match, best_offset

def scan_rom_comprehensively(rom_path: str, exhal_path: str):
    """Scan ROM for sprite data using multiple techniques."""
    print(f"Scanning ROM: {rom_path}")

    with open(rom_path, "rb") as f:
        rom_data = f.read()

    rom_size = len(rom_data)
    print(f"ROM size: {rom_size:,} bytes")

    # Load VRAM patterns if available
    vram_patterns = []
    for vram_file in Path(".").glob("vram_*_VRAM.dmp_*.bin"):
        with open(vram_file, "rb") as f:
            pattern = f.read()[:256]  # First 256 bytes as pattern
            vram_patterns.append((vram_file.stem, pattern))

    print(f"Loaded {len(vram_patterns)} VRAM patterns for comparison")

    # Common offsets to check within decompressed blocks
    inner_offsets = [0, 512, 1024, 2048, 4096, 8192, 16384]

    # Results storage
    results = []

    # Scan ROM in chunks
    chunk_size = 0x10000  # 64KB chunks
    for chunk_start in range(0, rom_size, chunk_size // 2):  # Overlap by half
        if chunk_start % 0x100000 == 0:
            print(f"Progress: {chunk_start / rom_size * 100:.1f}%")

        # Try decompressing at various alignments
        for align in [0, 1, 2, 3]:  # HAL compression can start at any byte
            offset = chunk_start + align
            if offset >= rom_size:
                continue

            # Try to decompress
            decompressed = decompress_at_offset(rom_path, offset, exhal_path)

            if len(decompressed) >= 1024:  # At least 1KB decompressed
                # Check sprite quality
                quality = analyze_sprite_quality(decompressed)

                if quality > 0.3:  # Decent sprite-like data
                    result = {
                        "offset": offset,
                        "size": len(decompressed),
                        "quality": quality,
                        "matches": []
                    }

                    # Compare to VRAM patterns
                    for pattern_name, pattern in vram_patterns:
                        similarity, inner_offset = compare_to_vram(
                            decompressed, pattern, inner_offsets
                        )
                        if similarity > 0.5:
                            result["matches"].append({
                                "pattern": pattern_name,
                                "similarity": similarity,
                                "inner_offset": inner_offset
                            })

                    if result["matches"] or quality > 0.5:
                        results.append(result)
                        print(f"\nFound potential sprites at 0x{offset:06X}:")
                        print(f"  Size: {len(decompressed)} bytes")
                        print(f"  Quality: {quality:.2f}")
                        if result["matches"]:
                            print("  VRAM matches:")
                            for match in result["matches"]:
                                print(f"    {match['pattern']}: {match['similarity']:.1%} at +{match['inner_offset']}")

    return results

def update_sprite_locations(results: list[tuple[int, float, int]], rom_path: str):
    """Update sprite_locations.json with findings."""
    config_path = "config/sprite_locations.json"

    # Load existing config
    with open(config_path) as f:
        json.load(f)

    # Determine ROM type
    rom_name = Path(rom_path).stem

    # Get best results
    best_results = sorted(results,
                         key=lambda x: len(x["matches"]) + x["quality"],
                         reverse=True)[:20]

    print(f"\nBest {len(best_results)} sprite locations:")
    for i, result in enumerate(best_results):
        print(f"{i+1}. 0x{result['offset']:06X} - "
              f"Quality: {result['quality']:.2f}, "
              f"VRAM matches: {len(result['matches'])}")

    # Create new sprite entries
    new_sprites = []
    for i, result in enumerate(best_results[:10]):  # Top 10
        sprite_entry = {
            "name": f"Sprite_Found_{i+1}",
            "offset": f"0x{result['offset']:06X}",
            "expected_size": min(result["size"], 8192),  # Cap at 8KB
            "notes": f"Quality: {result['quality']:.2f}"
        }

        if result["matches"]:
            match_info = ", ".join(
                f"{m['pattern']} ({m['similarity']:.0%})"
                for m in result["matches"][:3]
            )
            sprite_entry["notes"] += f", Matches: {match_info}"

        new_sprites.append(sprite_entry)

    # Save results
    output_file = f"sprite_scan_results_{rom_name}.json"
    with open(output_file, "w") as f:
        json.dump({
            "rom": rom_name,
            "scan_results": results,
            "recommended_sprites": new_sprites
        }, f, indent=2)

    print(f"\nResults saved to {output_file}")
    print("\nRecommended sprite_locations.json entries:")
    print(json.dumps(new_sprites, indent=2))

def main():
    # Find exhal tool
    exhal_path = find_exhal_tool()
    if not exhal_path:
        return

    print(f"Using exhal: {exhal_path}")

    # Find ROM files
    rom_files = list(Path(".").glob("*.sfc")) + list(Path(".").glob("*.smc"))

    if not rom_files:
        print("No ROM files found!")
        return

    # Let user choose or scan all
    print("\nAvailable ROMs:")
    for i, rom in enumerate(rom_files):
        print(f"{i+1}. {rom.name}")

    # For now, scan the PAL ROM if available
    pal_rom = None
    for rom in rom_files:
        if "Fun Pak" in rom.name or "PAL" in rom.name:
            pal_rom = rom
            break

    if not pal_rom:
        pal_rom = rom_files[0]

    print(f"\nScanning: {pal_rom.name}")

    # Run comprehensive scan
    results = scan_rom_comprehensively(str(pal_rom), exhal_path)

    # Update sprite locations
    if results:
        update_sprite_locations(results, str(pal_rom))
    else:
        print("\nNo sprite data found!")

if __name__ == "__main__":
    main()
