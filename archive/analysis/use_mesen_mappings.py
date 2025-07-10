#!/usr/bin/env python3
"""
Example of using Mesen-collected palette mappings with the sprite editor.
Shows how to extract sprites with accurate palettes based on gameplay data.
"""

import json
import sys

sys.path.append("sprite_editor")

import struct

from PIL import Image

from sprite_editor.tile_utils import decode_4bpp_tile


class MesenMappingExtractor:
    """Extract sprites using Mesen-collected palette mappings"""

    def __init__(self, mapping_file):
        """Load the Mesen mapping data"""
        with open(mapping_file) as f:
            self.mapping_data = json.load(f)

        # Extract tile mappings
        self.tile_to_palette = {}
        if "tile_mappings" in self.mapping_data:
            for tile_str, info in self.mapping_data["tile_mappings"].items():
                tile = int(tile_str)
                self.tile_to_palette[tile] = info["palette"]

        print(f"Loaded mappings for {len(self.tile_to_palette)} tiles")

        # Show palette usage
        if "palette_usage" in self.mapping_data:
            print("\nPalette usage summary:")
            for pal, info in self.mapping_data["palette_usage"].items():
                print(f"  Palette {pal}: {info['tile_count']} tiles")

    def get_palette_for_tile(self, tile_index, default=0):
        """Get the palette number for a specific tile"""
        return self.tile_to_palette.get(tile_index, default)

    def extract_with_mappings(self, vram_file, cgram_file, output_prefix="mesen_mapped"):
        """Extract sprites using the collected mappings"""
        print("\nExtracting sprites with Mesen mappings...")

        # Read VRAM
        with open(vram_file, "rb") as f:
            f.seek(0xC000)
            vram_data = f.read(0x4000)

        # Read all OBJ palettes
        obj_palettes = []
        for i in range(8):
            pal = self.read_obj_palette(cgram_file, i)
            obj_palettes.append(pal)

        # Create sprite sheet
        tiles_per_row = 16
        total_tiles = len(vram_data) // 32
        width = tiles_per_row * 8
        height = ((total_tiles + tiles_per_row - 1) // tiles_per_row) * 8

        img = Image.new("RGBA", (width, height), (0, 0, 0, 0))

        # Statistics
        mapped_tiles = 0
        unmapped_tiles = 0

        # Process each tile
        for tile_idx in range(total_tiles):
            tile_offset = tile_idx * 32

            if tile_offset + 32 <= len(vram_data):
                # Get palette from mapping
                pal_num = self.get_palette_for_tile(tile_idx)

                if tile_idx in self.tile_to_palette:
                    mapped_tiles += 1
                else:
                    unmapped_tiles += 1

                # Use the palette
                if pal_num < len(obj_palettes):
                    palette = obj_palettes[pal_num]

                    # Decode tile
                    tile_pixels = decode_4bpp_tile(vram_data, tile_offset)

                    tile_x = tile_idx % tiles_per_row
                    tile_y = tile_idx // tiles_per_row

                    # Draw pixels
                    for y in range(8):
                        for x in range(8):
                            pixel_idx = y * 8 + x
                            if pixel_idx < len(tile_pixels):
                                color_idx = tile_pixels[pixel_idx]

                                if color_idx > 0 and color_idx * 3 + 2 < len(palette):
                                    r = palette[color_idx * 3]
                                    g = palette[color_idx * 3 + 1]
                                    b = palette[color_idx * 3 + 2]

                                    px = tile_x * 8 + x
                                    py = tile_y * 8 + y
                                    if px < width and py < height:
                                        img.putpixel((px, py), (r, g, b, 255))

        # Save results
        img.save(f"{output_prefix}_sprites.png")
        img_2x = img.resize((img.width * 2, img.height * 2), resample=Image.NEAREST)
        img_2x.save(f"{output_prefix}_sprites_2x.png")
        img_4x = img.resize((img.width * 4, img.height * 4), resample=Image.NEAREST)
        img_4x.save(f"{output_prefix}_sprites_4x.png")

        print("\nExtraction complete:")
        print(f"  Mapped tiles: {mapped_tiles}")
        print(f"  Unmapped tiles: {unmapped_tiles}")
        print(f"  Coverage: {mapped_tiles / (mapped_tiles + unmapped_tiles) * 100:.1f}%")
        print(f"\nOutput: {output_prefix}_sprites.png (and 2x, 4x)")

        return img

    def read_obj_palette(self, cgram_file, obj_palette_num):
        """Read an OBJ palette from CGRAM"""
        with open(cgram_file, "rb") as f:
            cgram_index = 128 + (obj_palette_num * 16)
            f.seek(cgram_index * 2)

            palette = []
            for _i in range(16):
                data = f.read(2)
                if len(data) < 2:
                    break

                color = struct.unpack("<H", data)[0]
                b = ((color >> 10) & 0x1F) * 8
                g = ((color >> 5) & 0x1F) * 8
                r = (color & 0x1F) * 8

                palette.extend([r, g, b])

            return palette

    def create_coverage_report(self, output_file="coverage_report.png"):
        """Create a visual report showing mapping coverage"""
        width = 256
        height = 256
        img = Image.new("RGB", (width, height), (32, 32, 32))

        # Color code: Green = mapped, Red = unmapped
        for tile in range(512):
            x = (tile % 16) * 16
            y = (tile // 16) * 8

            if tile in self.tile_to_palette:
                # Mapped - color by palette
                pal = self.tile_to_palette[tile]
                colors = [
                    (255, 192, 255),  # Palette 0 - Pink
                    (192, 255, 192),  # Palette 1 - Green
                    (192, 192, 255),  # Palette 2 - Blue
                    (255, 255, 192),  # Palette 3 - Yellow
                    (255, 192, 192),  # Palette 4 - Red
                    (192, 255, 255),  # Palette 5 - Cyan
                    (255, 224, 192),  # Palette 6 - Orange
                    (224, 192, 255),  # Palette 7 - Purple
                ]
                color = colors[pal % len(colors)]
            else:
                # Unmapped
                color = (64, 64, 64)

            # Draw tile block
            for dy in range(8):
                for dx in range(16):
                    if x + dx < width and y + dy < height:
                        img.putpixel((x + dx, y + dy), color)

        img.save(output_file)
        print(f"\nCoverage report saved to: {output_file}")

def main():
    """Example usage"""
    import argparse

    parser = argparse.ArgumentParser(description="Extract sprites using Mesen mappings")
    parser.add_argument("mapping_file", help="Mesen mapping JSON file")
    parser.add_argument("vram_file", help="VRAM dump file")
    parser.add_argument("cgram_file", help="CGRAM dump file")
    parser.add_argument("-o", "--output", default="mesen_mapped",
                       help="Output prefix for extracted sprites")
    parser.add_argument("-c", "--coverage", action="store_true",
                       help="Generate coverage report")

    args = parser.parse_args()

    # Create extractor
    extractor = MesenMappingExtractor(args.mapping_file)

    # Extract sprites
    extractor.extract_with_mappings(args.vram_file, args.cgram_file, args.output)

    # Generate coverage report if requested
    if args.coverage:
        extractor.create_coverage_report()

if __name__ == "__main__":
    # If no arguments, show example
    if len(sys.argv) == 1:
        print("Example usage:")
        print("  python3 use_mesen_mappings.py final_palette_mapping.json Cave.SnesVideoRam.dmp Cave.SnesCgRam.dmp")
        print("\nOr with coverage report:")
        print("  python3 use_mesen_mappings.py final_palette_mapping.json Cave.SnesVideoRam.dmp Cave.SnesCgRam.dmp -c")
    else:
        main()
