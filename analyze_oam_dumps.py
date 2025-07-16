#!/usr/bin/env python3
"""
Analyze OAM dump files to understand palette assignments and identify Kirby sprites.

SNES OAM Format:
- 128 sprites total
- Each sprite has 4 bytes in low table (512 bytes total):
  Byte 0: X position (low 8 bits)
  Byte 1: Y position
  Byte 2: Tile number (low 8 bits)
  Byte 3: Attributes:
    Bit 0-2: Palette number (0-7)
    Bit 3: Priority (0 or 1)
    Bit 4-5: Priority (bits 0-1 of 4-level priority)
    Bit 6: X flip
    Bit 7: Y flip

- High table has 2 bits per sprite (32 bytes total):
  Bit 0: Size toggle
  Bit 1: X position (9th bit)
"""

import os
from collections import Counter, defaultdict


class OAMAnalyzer:
    def __init__(self):
        self.oam_files = []
        self.palette_usage = defaultdict(set)  # palette -> set of tile numbers
        self.tile_palettes = defaultdict(set)  # tile -> set of palettes used
        self.sprite_info = []

    def read_oam_dump(self, filename: str) -> bytes:
        """Read OAM dump file."""
        with open(filename, "rb") as f:
            data = f.read()
        print(f"\nReading {filename}: {len(data)} bytes")
        return data

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
        palette = attrs & 0x07  # Bits 0-2
        priority = (attrs >> 3) & 0x03  # Bits 3-4
        (attrs >> 4) & 0x03  # Bits 4-5 (overlaps)
        x_flip = bool(attrs & 0x40)  # Bit 6
        y_flip = bool(attrs & 0x80)  # Bit 7

        # Get high table data if available
        high_offset = 512 + (index // 4)
        high_bit_offset = (index % 4) * 2

        size_toggle = False
        x_high = 0

        if high_offset < len(data):
            high_byte = data[high_offset]
            size_toggle = bool((high_byte >> high_bit_offset) & 0x01)
            x_high = bool((high_byte >> (high_bit_offset + 1)) & 0x01)

        x = x_low | (x_high << 8)

        # Skip offscreen sprites
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
            "size_toggle": size_toggle,
            "attrs_raw": attrs,
        }

    def analyze_oam_file(self, filename: str):
        """Analyze a single OAM dump file."""
        data = self.read_oam_dump(filename)

        sprites = []
        palette_counts = Counter()
        tile_palette_map = defaultdict(set)

        # Parse all sprites in low table
        for i in range(min(128, len(data) // 4)):
            sprite = self.parse_oam_entry(data, i)
            if sprite and sprite["y"] < 240:  # Skip offscreen sprites
                sprites.append(sprite)
                palette_counts[sprite["palette"]] += 1
                tile_palette_map[sprite["tile"]].add(sprite["palette"])

                # Track global usage
                self.palette_usage[sprite["palette"]].add(sprite["tile"])
                self.tile_palettes[sprite["tile"]].add(sprite["palette"])

        print(f"\nAnalysis of {os.path.basename(filename)}:")
        print(f"Active sprites: {len(sprites)}")
        print(f"Palette usage: {dict(palette_counts)}")

        # Look for potential Kirby sprites
        # Kirby often uses tiles in certain ranges and specific palettes
        kirby_candidates = []
        for sprite in sprites:
            # Common Kirby tile ranges and characteristics
            if sprite["tile"] in range(0x40) or sprite[  # Common character tiles
                "tile"
            ] in range(
                0x80, 0xC0
            ):  # More character tiles
                if sprite["palette"] in [0, 1, 2, 3]:  # Kirby often uses lower palettes
                    kirby_candidates.append(sprite)

        if kirby_candidates:
            print(f"\nPotential Kirby sprites ({len(kirby_candidates)}):")
            # Group by position to find sprite clusters
            position_groups = defaultdict(list)
            for sprite in kirby_candidates:
                # Group sprites within 32 pixels of each other
                key = (sprite["x"] // 32, sprite["y"] // 32)
                position_groups[key].append(sprite)

            for pos, group in position_groups.items():
                if len(group) >= 2:  # Kirby is usually made of multiple sprites
                    print(f"  Cluster at ~({pos[0]*32}, {pos[1]*32}):")
                    for sprite in sorted(group, key=lambda s: (s["y"], s["x"])):
                        print(
                            f"    Sprite {sprite['index']}: Tile 0x{sprite['tile']:02X}, "
                            f"Palette {sprite['palette']}, Pos ({sprite['x']}, {sprite['y']})"
                        )

        # Show tile-palette mappings
        print("\nTiles using multiple palettes in this file:")
        multi_palette_tiles = {
            tile: pals for tile, pals in tile_palette_map.items() if len(pals) > 1
        }
        for tile, palettes in sorted(multi_palette_tiles.items())[:10]:
            print(f"  Tile 0x{tile:02X}: palettes {sorted(palettes)}")

        return sprites, palette_counts, tile_palette_map

    def analyze_all_files(self):
        """Analyze all OAM dump files found."""
        # Find all OAM files
        oam_files = [
            "OAM.dmp",
            "SnesSpriteRam.OAM.dmp",
            "Cave.SnesSpriteRam.dmp",
            "oam_from_savestate.dmp",
            "mss_OAM.dmp",
            "mss2_OAM.dmp",
            "Kirby Super Star (USA)_1_OAM.dmp",
            "Kirby Super Star (USA)_2_OAM.dmp",
        ]

        existing_files = []
        for filename in oam_files:
            if os.path.exists(filename):
                existing_files.append(filename)

        print(f"Found {len(existing_files)} OAM dump files")

        all_sprites = []
        for filename in existing_files:
            sprites, _, _ = self.analyze_oam_file(filename)
            all_sprites.extend([(filename, s) for s in sprites])

        # Global analysis
        print("\n" + "=" * 60)
        print("GLOBAL PALETTE ANALYSIS")
        print("=" * 60)

        print("\nPalettes by usage frequency:")
        palette_tile_counts = [
            (pal, len(tiles)) for pal, tiles in self.palette_usage.items()
        ]
        for palette, count in sorted(
            palette_tile_counts, key=lambda x: x[1], reverse=True
        ):
            print(f"  Palette {palette}: {count} unique tiles")
            # Show some example tiles
            example_tiles = sorted(self.palette_usage[palette])[:10]
            print(f"    Examples: {', '.join(f'0x{t:02X}' for t in example_tiles)}")

        print("\nTiles that use multiple palettes across all files:")
        multi_palette_tiles = [
            (tile, pals) for tile, pals in self.tile_palettes.items() if len(pals) > 1
        ]
        for tile, palettes in sorted(
            multi_palette_tiles, key=lambda x: len(x[1]), reverse=True
        )[:20]:
            print(f"  Tile 0x{tile:02X}: palettes {sorted(palettes)}")

        # Look for Kirby patterns
        print("\n" + "=" * 60)
        print("KIRBY SPRITE DETECTION")
        print("=" * 60)

        # Kirby sprites often appear in groups and use consistent palettes
        # Look for recurring tile patterns
        tile_positions = defaultdict(list)
        for filename, sprite in all_sprites:
            if sprite["palette"] in [0, 1, 2, 3]:  # Focus on lower palettes
                tile_positions[sprite["tile"]].append(
                    {
                        "file": os.path.basename(filename),
                        "x": sprite["x"],
                        "y": sprite["y"],
                        "palette": sprite["palette"],
                    }
                )

        print("\nFrequently used tiles (potential Kirby tiles):")
        frequent_tiles = [
            (tile, positions)
            for tile, positions in tile_positions.items()
            if len(positions) >= 3
        ]
        for tile, positions in sorted(
            frequent_tiles, key=lambda x: len(x[1]), reverse=True
        )[:15]:
            print(f"\nTile 0x{tile:02X} appears {len(positions)} times:")
            palette_counts = Counter(p["palette"] for p in positions)
            print(f"  Palette usage: {dict(palette_counts)}")
            # Show a few examples
            for pos in positions[:3]:
                print(
                    f"    {pos['file']}: ({pos['x']}, {pos['y']}) palette {pos['palette']}"
                )

        # Create tile-to-palette mapping
        print("\n" + "=" * 60)
        print("TILE TO PALETTE MAPPING")
        print("=" * 60)

        consistent_tiles = {}
        for tile, palettes in self.tile_palettes.items():
            if len(palettes) == 1:
                consistent_tiles[tile] = next(iter(palettes))

        print(
            f"\nTiles with consistent palette assignment ({len(consistent_tiles)} tiles):"
        )
        for palette in range(8):
            tiles = [t for t, p in consistent_tiles.items() if p == palette]
            if tiles:
                print(f"\nPalette {palette} ({len(tiles)} tiles):")
                print(f"  {', '.join(f'0x{t:02X}' for t in sorted(tiles)[:20])}")
                if len(tiles) > 20:
                    print(f"  ... and {len(tiles) - 20} more")

        # Save mapping to file
        with open("oam_palette_mapping.txt", "w") as f:
            f.write("OAM Palette Analysis Results\n")
            f.write("=" * 60 + "\n\n")

            f.write("Tile to Palette Mapping (consistent assignments):\n")
            for tile in sorted(consistent_tiles.keys()):
                f.write(f"Tile 0x{tile:02X} -> Palette {consistent_tiles[tile]}\n")

            f.write("\n\nTiles with variable palette assignments:\n")
            for tile, palettes in sorted(self.tile_palettes.items()):
                if len(palettes) > 1:
                    f.write(f"Tile 0x{tile:02X} -> Palettes {sorted(palettes)}\n")

        print("\nResults saved to oam_palette_mapping.txt")


if __name__ == "__main__":
    analyzer = OAMAnalyzer()
    analyzer.analyze_all_files()
