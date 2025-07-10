#!/usr/bin/env python3
"""
Analyze multiple Mesen dumps to create comprehensive sprite palette mappings.
Combines data from multiple gameplay sessions to build complete mapping database.
"""

import glob
import json
import os
from collections import defaultdict


def find_mesen_dumps(directory: str = ".") -> list[dict]:
    """Find all Mesen dump sets in the directory"""
    dumps = []

    # Look for dump sets (VRAM, CGRAM, OAM, mappings)
    mapping_files = glob.glob(os.path.join(directory, "*_mappings.json"))

    for mapping_file in mapping_files:
        base_name = mapping_file.replace("_mappings.json", "")

        # Check if all required files exist
        vram_file = base_name + "_VRAM.dmp"
        cgram_file = base_name + "_CGRAM.dmp"
        oam_file = base_name + "_OAM.dmp"

        if all(os.path.exists(f) for f in [vram_file, cgram_file, oam_file]):
            dumps.append({
                "base_name": base_name,
                "vram": vram_file,
                "cgram": cgram_file,
                "oam": oam_file,
                "mappings": mapping_file,
                "timestamp": os.path.basename(base_name).split("_")[-2:]
            })

    return sorted(dumps, key=lambda x: x["base_name"])

def load_mapping_data(mapping_file: str) -> dict:
    """Load mapping data from JSON file"""
    try:
        with open(mapping_file) as f:
            return json.load(f)
    except:
        return {}

def combine_mappings(dump_sets: list[dict]) -> dict[int, dict[int, int]]:
    """Combine mappings from multiple dumps to build confidence"""
    combined = defaultdict(lambda: defaultdict(int))

    for dump in dump_sets:
        data = load_mapping_data(dump["mappings"])

        if "detailedCounts" in data:
            for tile_str, palettes in data["detailedCounts"].items():
                tile = int(tile_str)
                for pal_str, count in palettes.items():
                    pal = int(pal_str)
                    combined[tile][pal] += count

    return dict(combined)

def determine_best_palette(palette_counts: dict[int, int], min_confidence: int = 3) -> tuple[int, float]:
    """Determine the most likely palette for a tile"""
    if not palette_counts:
        return -1, 0.0

    total = sum(palette_counts.values())
    best_pal = max(palette_counts.items(), key=lambda x: x[1])

    if best_pal[1] >= min_confidence:
        confidence = best_pal[1] / total if total > 0 else 0
        return best_pal[0], confidence

    return -1, 0.0

def analyze_dumps(directory: str = ".", output_file: str = "final_palette_mapping.json"):
    """Analyze all dumps and create final mapping"""
    print(f"Scanning directory: {directory}")

    # Find all dump sets
    dumps = find_mesen_dumps(directory)
    print(f"Found {len(dumps)} dump sets")

    if not dumps:
        print("No dump sets found!")
        return

    # List dumps
    print("\nDump sets found:")
    for dump in dumps:
        print(f"  - {os.path.basename(dump['base_name'])}")

    # Combine all mappings
    print("\nCombining mappings...")
    combined = combine_mappings(dumps)

    # Analyze combined data
    final_mappings = {}
    confident_mappings = 0
    ambiguous_mappings = 0

    for tile, palette_counts in combined.items():
        best_pal, confidence = determine_best_palette(palette_counts)

        if best_pal >= 0:
            final_mappings[tile] = {
                "palette": best_pal,
                "confidence": confidence,
                "counts": dict(palette_counts)
            }

            if confidence >= 0.8:
                confident_mappings += 1
            else:
                ambiguous_mappings += 1

    # Generate statistics
    stats = {
        "total_dumps": len(dumps),
        "total_tiles_seen": len(combined),
        "confident_mappings": confident_mappings,
        "ambiguous_mappings": ambiguous_mappings,
        "unmapped_tiles": 512 - len(combined)  # Assuming 512 tiles in sprite area
    }

    # Identify palette usage patterns
    palette_usage = defaultdict(list)
    for tile, data in final_mappings.items():
        palette_usage[data["palette"]].append(tile)

    # Save final mapping
    output_data = {
        "metadata": {
            "dumps_analyzed": len(dumps),
            "analysis_date": os.popen("date").read().strip(),
            "statistics": stats
        },
        "palette_usage": {
            str(pal): {
                "tile_count": len(tiles),
                "tile_ranges": identify_ranges(tiles)
            } for pal, tiles in palette_usage.items()
        },
        "tile_mappings": {
            str(tile): data for tile, data in final_mappings.items()
        }
    }

    with open(output_file, "w") as f:
        json.dump(output_data, f, indent=2)

    print("\nAnalysis complete!")
    print("Statistics:")
    print(f"  - Total dumps analyzed: {stats['total_dumps']}")
    print(f"  - Unique tiles seen: {stats['total_tiles_seen']}")
    print(f"  - Confident mappings: {stats['confident_mappings']}")
    print(f"  - Ambiguous mappings: {stats['ambiguous_mappings']}")
    print(f"  - Unmapped tiles: {stats['unmapped_tiles']}")
    print("\nPalette usage:")
    for pal, tiles in palette_usage.items():
        print(f"  - Palette {pal}: {len(tiles)} tiles")
    print(f"\nResults saved to: {output_file}")

    # Also create a simple text mapping
    create_simple_mapping(final_mappings, "tile_palette_mapping.txt")

def identify_ranges(tiles: list[int]) -> list[str]:
    """Identify continuous ranges in tile list"""
    if not tiles:
        return []

    tiles = sorted(tiles)
    ranges = []
    start = tiles[0]
    end = tiles[0]

    for tile in tiles[1:]:
        if tile == end + 1:
            end = tile
        else:
            if start == end:
                ranges.append(str(start))
            else:
                ranges.append(f"{start}-{end}")
            start = tile
            end = tile

    # Add final range
    if start == end:
        ranges.append(str(start))
    else:
        ranges.append(f"{start}-{end}")

    return ranges

def create_simple_mapping(mappings: dict, output_file: str):
    """Create a simple text file with tile->palette mappings"""
    with open(output_file, "w") as f:
        f.write("# Kirby Super Star - Tile to Palette Mapping\n")
        f.write("# Format: tile_number palette_number confidence\n")
        f.write("# Confidence: 0.0-1.0 (1.0 = always seen with this palette)\n\n")

        for tile in sorted(mappings.keys()):
            data = mappings[tile]
            f.write(f"{tile} {data['palette']} {data['confidence']:.2f}\n")

    print(f"Simple mapping saved to: {output_file}")

def main():
    import argparse

    parser = argparse.ArgumentParser(description="Analyze Mesen sprite dumps")
    parser.add_argument("directory", nargs="?", default=".",
                       help="Directory containing dump files (default: current directory)")
    parser.add_argument("-o", "--output", default="final_palette_mapping.json",
                       help="Output file for mapping data")
    parser.add_argument("-m", "--min-confidence", type=int, default=3,
                       help="Minimum times a mapping must be seen to be confident")

    args = parser.parse_args()

    analyze_dumps(args.directory, args.output)

if __name__ == "__main__":
    main()
