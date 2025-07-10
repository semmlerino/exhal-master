#!/usr/bin/env python3
"""
Analyze the Mesen mapping coverage and identify gaps
"""

import json

# Load the mapping data
with open("final_palette_mapping.json") as f:
    data = json.load(f)

print("=== Mesen Mapping Analysis ===\n")

# Statistics
stats = data["metadata"]["statistics"]
print(f"Dumps analyzed: {stats['total_dumps']}")
print(f"Tiles seen: {stats['total_tiles_seen']} / 512 ({stats['total_tiles_seen']/512*100:.1f}%)")
print(f"Confident mappings: {stats['confident_mappings']}")
print(f"Ambiguous mappings: {stats['ambiguous_mappings']}")

# Palette breakdown
print("\n=== Palette Usage ===")
for pal, info in sorted(data["palette_usage"].items(), key=lambda x: int(x[0])):
    print(f"\nPalette {pal}: {info['tile_count']} tiles")
    print(f"  Ranges: {', '.join(info['tile_ranges'])}")

# Identify gaps
all_mapped = set()
for pal_data in data["palette_usage"].values():
    for range_str in pal_data["tile_ranges"]:
        if "-" in range_str:
            start, end = map(int, range_str.split("-"))
            for i in range(start, end + 1):
                all_mapped.add(i)
        else:
            all_mapped.add(int(range_str))

# Find unmapped regions
print("\n=== Unmapped Regions ===")
unmapped_ranges = []
current_start = None

for i in range(512):
    if i not in all_mapped:
        if current_start is None:
            current_start = i
    elif current_start is not None:
        if current_start == i - 1:
            unmapped_ranges.append(str(current_start))
        else:
            unmapped_ranges.append(f"{current_start}-{i-1}")
        current_start = None

# Handle end case
if current_start is not None:
    if current_start == 511:
        unmapped_ranges.append("511")
    else:
        unmapped_ranges.append(f"{current_start}-511")

print(f"Unmapped tile ranges: {', '.join(unmapped_ranges[:10])}")
if len(unmapped_ranges) > 10:
    print(f"... and {len(unmapped_ranges) - 10} more ranges")

# Palette analysis
print("\n=== Palette Patterns ===")
print("Palette 0: Kirby sprites (tiles 0-31)")
print("Palette 1: Large region (64-92, 352-511) - likely enemies/effects")
print("Palette 2: UI elements (tiles 32-54)")
print("Palette 3: Enemy sprites (tiles 160-191)")
print("Palette 4: Various (96-112, 192-223)")

print("\n=== Recommendations ===")
print("To improve coverage:")
print("1. The large gap at tiles 224-351 suggests unused sprite space")
print("2. Tiles 113-159 might be special effects or power-ups")
print("3. Continue playing to encounter more sprite variations")
print("4. Focus on areas with new enemies or power-ups")
