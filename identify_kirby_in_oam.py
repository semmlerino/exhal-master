#!/usr/bin/env python3
"""
Identify Kirby sprites in OAM dumps by analyzing sprite clusters and patterns.
"""

import os
from collections import Counter, defaultdict


class KirbyIdentifier:
    def __init__(self):
        # Known Kirby characteristics from previous analysis
        self.kirby_tile_ranges = [
            (0x00, 0x1F),  # Common Kirby body tiles
            (0x20, 0x3F),  # More Kirby tiles
            (0x80, 0x9F),  # Additional character tiles
        ]

        # Kirby usually uses palettes 0-3 for normal forms
        self.kirby_palettes = [0, 1, 2, 3]

        # Kirby sprite size is typically 16x16 or 16x24
        self.kirby_sizes = [(16, 16), (16, 24), (24, 24)]

    def read_oam_dump(self, filename: str) -> bytes:
        """Read OAM dump file."""
        with open(filename, "rb") as f:
            return f.read()

    def parse_oam_entry(self, data: bytes, index: int) -> dict:
        """Parse a single OAM entry."""
        offset = index * 4
        if offset + 4 > len(data):
            return None

        x_low = data[offset]
        y = data[offset + 1]
        tile_low = data[offset + 2]
        attrs = data[offset + 3]

        # Extract attribute bits
        palette = attrs & 0x07
        priority = (attrs >> 3) & 0x03
        x_flip = bool(attrs & 0x40)
        y_flip = bool(attrs & 0x80)

        # Get high table data
        high_offset = 512 + (index // 4)
        high_bit_offset = (index % 4) * 2

        size_toggle = False
        x_high = 0

        if high_offset < len(data):
            high_byte = data[high_offset]
            size_toggle = bool((high_byte >> high_bit_offset) & 0x01)
            x_high = bool((high_byte >> (high_bit_offset + 1)) & 0x01)

        x = x_low | (x_high << 8)

        # Skip clearly offscreen sprites
        if x >= 256 or y >= 224:
            return None

        return {
            "index": index,
            "x": x,
            "y": y,
            "tile": tile_low,
            "palette": palette,
            "priority": priority,
            "x_flip": x_flip,
            "y_flip": y_flip,
            "size_toggle": size_toggle
        }

    def find_sprite_clusters(self, sprites: list[dict], max_distance: int = 32) -> list[list[dict]]:
        """Find clusters of sprites that might form a character."""
        clusters = []
        used = set()

        for i, sprite in enumerate(sprites):
            if i in used:
                continue

            cluster = [sprite]
            used.add(i)

            # Find nearby sprites
            for j, other in enumerate(sprites):
                if j in used:
                    continue

                # Check if sprites are close enough
                dx = abs(sprite["x"] - other["x"])
                dy = abs(sprite["y"] - other["y"])

                if dx <= max_distance and dy <= max_distance:
                    cluster.append(other)
                    used.add(j)

            if len(cluster) >= 2:  # Characters usually have multiple sprites
                clusters.append(cluster)

        return clusters

    def analyze_cluster(self, cluster: list[dict]) -> dict:
        """Analyze a sprite cluster to determine if it might be Kirby."""
        # Get bounding box
        min_x = min(s["x"] for s in cluster)
        max_x = max(s["x"] for s in cluster)
        min_y = min(s["y"] for s in cluster)
        max_y = max(s["y"] for s in cluster)

        width = max_x - min_x + 8  # Assuming 8x8 tiles
        height = max_y - min_y + 8

        # Check palette usage
        palettes = Counter(s["palette"] for s in cluster)
        dominant_palette = palettes.most_common(1)[0][0]

        # Check tile ranges
        tiles = [s["tile"] for s in cluster]
        kirby_tiles = sum(1 for t in tiles for r in self.kirby_tile_ranges if r[0] <= t <= r[1])

        # Score the cluster
        score = 0

        # Palette score
        if dominant_palette in self.kirby_palettes:
            score += 3

        # Size score
        if (width, height) in self.kirby_sizes or (16 <= width <= 32 and 16 <= height <= 32):
            score += 2

        # Tile range score
        if kirby_tiles >= len(cluster) * 0.5:  # At least half tiles in Kirby ranges
            score += 3

        # Cluster size score
        if 4 <= len(cluster) <= 8:  # Typical Kirby sprite count
            score += 2

        return {
            "cluster": cluster,
            "bbox": (min_x, min_y, width, height),
            "dominant_palette": dominant_palette,
            "palettes": dict(palettes),
            "tiles": tiles,
            "score": score,
            "sprite_count": len(cluster)
        }

    def analyze_file(self, filename: str):
        """Analyze a single OAM dump file for Kirby sprites."""
        print(f"\n{'='*60}")
        print(f"Analyzing: {filename}")
        print("="*60)

        data = self.read_oam_dump(filename)

        # Parse all sprites
        sprites = []
        for i in range(min(128, len(data) // 4)):
            sprite = self.parse_oam_entry(data, i)
            if sprite and sprite["y"] < 240:
                sprites.append(sprite)

        print(f"Total active sprites: {len(sprites)}")

        # Find clusters
        clusters = self.find_sprite_clusters(sprites)
        print(f"Found {len(clusters)} sprite clusters")

        # Analyze each cluster
        kirby_candidates = []
        for cluster in clusters:
            analysis = self.analyze_cluster(cluster)
            if analysis["score"] >= 5:  # Threshold for likely Kirby
                kirby_candidates.append(analysis)

        # Sort by score
        kirby_candidates.sort(key=lambda x: x["score"], reverse=True)

        if kirby_candidates:
            print(f"\nLikely Kirby sprites found ({len(kirby_candidates)} candidates):")
            for i, candidate in enumerate(kirby_candidates[:3]):  # Top 3
                print(f"\nCandidate {i+1} (Score: {candidate['score']}/10):")
                print(f"  Position: ({candidate['bbox'][0]}, {candidate['bbox'][1]})")
                print(f"  Size: {candidate['bbox'][2]}x{candidate['bbox'][3]} pixels")
                print(f"  Sprites: {candidate['sprite_count']}")
                print(f"  Dominant palette: {candidate['dominant_palette']}")
                print(f"  All palettes: {candidate['palettes']}")
                print(f"  Tiles: {', '.join(f'0x{t:02X}' for t in sorted(set(candidate['tiles'])))}")

                # Show individual sprites
                print("  Sprite details:")
                for sprite in sorted(candidate["cluster"], key=lambda s: (s["y"], s["x"])):
                    print(f"    Sprite {sprite['index']}: Tile 0x{sprite['tile']:02X}, "
                          f"Pal {sprite['palette']}, Pos ({sprite['x']}, {sprite['y']})")

        return kirby_candidates

    def create_palette_assignment_report(self):
        """Create a comprehensive report of palette assignments for Kirby sprites."""
        oam_files = [
            "OAM.dmp",
            "SnesSpriteRam.OAM.dmp",
            "Cave.SnesSpriteRam.dmp",
            "mss_OAM.dmp",
            "Kirby Super Star (USA)_1_OAM.dmp",
        ]

        all_candidates = []
        tile_palette_map = defaultdict(Counter)

        for filename in oam_files:
            if os.path.exists(filename):
                candidates = self.analyze_file(filename)
                all_candidates.extend([(filename, c) for c in candidates])

                # Track tile-palette associations from high-scoring candidates
                for candidate in candidates:
                    if candidate["score"] >= 6:
                        for sprite in candidate["cluster"]:
                            tile_palette_map[sprite["tile"]][sprite["palette"]] += 1

        print("\n" + "="*60)
        print("KIRBY SPRITE PALETTE MAPPING SUMMARY")
        print("="*60)

        print("\nMost common tile-palette assignments for likely Kirby sprites:")

        # Sort tiles by frequency
        tile_freq = [(tile, sum(palettes.values())) for tile, palettes in tile_palette_map.items()]
        tile_freq.sort(key=lambda x: x[1], reverse=True)

        for tile, freq in tile_freq[:30]:
            palettes = tile_palette_map[tile]
            print(f"\nTile 0x{tile:02X} (used {freq} times):")
            for pal, count in sorted(palettes.items()):
                pct = (count / freq) * 100
                print(f"  Palette {pal}: {count} times ({pct:.1f}%)")

        # Save detailed report
        with open("kirby_palette_assignments.txt", "w") as f:
            f.write("Kirby Sprite Palette Assignments\n")
            f.write("="*60 + "\n\n")

            f.write("High-confidence Kirby tiles and their palette assignments:\n\n")

            for tile, freq in tile_freq:
                palettes = tile_palette_map[tile]
                f.write(f"Tile 0x{tile:02X}:\n")
                for pal, count in sorted(palettes.items()):
                    f.write(f"  Palette {pal}: {count} occurrences\n")
                f.write("\n")

            f.write("\nDetailed sprite clusters:\n")
            f.write("="*40 + "\n\n")

            for filename, candidate in all_candidates:
                if candidate["score"] >= 6:
                    f.write(f"File: {filename}\n")
                    f.write(f"Score: {candidate['score']}/10\n")
                    f.write(f"Position: ({candidate['bbox'][0]}, {candidate['bbox'][1]})\n")
                    f.write(f"Size: {candidate['bbox'][2]}x{candidate['bbox'][3]}\n")
                    f.write("Sprites:\n")
                    for sprite in sorted(candidate["cluster"], key=lambda s: (s["y"], s["x"])):
                        f.write(f"  Tile 0x{sprite['tile']:02X} -> Palette {sprite['palette']}\n")
                    f.write("\n")

        print("\nDetailed results saved to kirby_palette_assignments.txt")

if __name__ == "__main__":
    identifier = KirbyIdentifier()
    identifier.create_palette_assignment_report()
