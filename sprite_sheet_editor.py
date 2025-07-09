#!/usr/bin/env python3
"""
Batch sprite sheet editing with palette constraint validation
Allows editing entire sprite sheets while maintaining SNES constraints
"""

import json
import os

from PIL import Image, ImageDraw

from sprite_edit_helpers import (
    decode_4bpp_tile,
    encode_4bpp_tile,
    parse_cgram,
)


class SpriteSheetEditor:
    def __init__(self, palette_mapping_file=None):
        """Initialize with optional palette mappings"""
        self.tile_to_palette = {}
        self.palette_constraints = {}

        if palette_mapping_file and os.path.exists(palette_mapping_file):
            self.load_palette_mappings(palette_mapping_file)

    def load_palette_mappings(self, mapping_file):
        """Load Mesen palette mappings"""
        with open(mapping_file) as f:
            data = json.load(f)

        if "tile_mappings" in data:
            for tile_str, info in data["tile_mappings"].items():
                tile_idx = int(tile_str)
                self.tile_to_palette[tile_idx] = info["palette"]

    def extract_sheet_for_editing(self, vram_file, cgram_file, offset=0xC000,
                                 size=0x4000, output_png="sprite_sheet.png"):
        """Extract entire sprite sheet as editable PNG with palette layers"""
        # Read data
        with open(vram_file, "rb") as f:
            f.seek(offset)
            vram_data = f.read(size)

        palettes = parse_cgram(cgram_file)

        # Calculate dimensions
        bytes_per_tile = 32
        total_tiles = size // bytes_per_tile
        tiles_per_row = 16
        rows = (total_tiles + tiles_per_row - 1) // tiles_per_row

        sheet_width = tiles_per_row * 8
        sheet_height = rows * 8

        # Create main sheet and palette layer
        main_sheet = Image.new("RGBA", (sheet_width, sheet_height), (0, 0, 0, 0))
        palette_info = Image.new("L", (sheet_width, sheet_height), 0)

        # Create metadata
        metadata = {
            "source_vram": os.path.abspath(vram_file),
            "source_cgram": os.path.abspath(cgram_file),
            "offset": offset,
            "size": size,
            "tiles_per_row": tiles_per_row,
            "total_tiles": total_tiles,
            "tile_info": {},
            "palette_colors": {}
        }

        # Store palette colors
        for pal_idx in range(16):
            colors = []
            for color_idx in range(16):
                color = palettes[pal_idx][color_idx]
                # color is already (r, g, b) tuple from parse_cgram
                colors.append(list(color))
            metadata["palette_colors"][pal_idx] = colors

        # Process tiles
        for tile_idx in range(total_tiles):
            tile_data = vram_data[tile_idx * bytes_per_tile:(tile_idx + 1) * bytes_per_tile]

            # Skip empty tiles
            if all(b == 0 for b in tile_data):
                continue

            # Decode tile
            pixels = decode_4bpp_tile(tile_data)

            # Get palette
            oam_pal = self.tile_to_palette.get(tile_idx, 0)
            cgram_pal = oam_pal + 8

            # Calculate position
            x = (tile_idx % tiles_per_row) * 8
            y = (tile_idx // tiles_per_row) * 8

            # Create tile image with correct palette
            tile_img = Image.new("RGBA", (8, 8))
            for py in range(8):
                for px in range(8):
                    pixel_idx = py * 8 + px
                    color_idx = pixels[pixel_idx]

                    if color_idx == 0:  # Transparent
                        tile_img.putpixel((px, py), (0, 0, 0, 0))
                    else:
                        r, g, b = palettes[cgram_pal][color_idx]
                        tile_img.putpixel((px, py), (r, g, b, 255))

                    # Store palette info
                    palette_info.putpixel((x + px, y + py), oam_pal)

            # Paste to main sheet
            main_sheet.paste(tile_img, (x, y))

            # Store metadata
            metadata["tile_info"][tile_idx] = {
                "palette": oam_pal,
                "cgram_palette": cgram_pal,
                "empty": False,
                "x": x,
                "y": y
            }

        # Save sheet and metadata
        main_sheet.save(output_png)

        # Save palette info as separate layer
        palette_png = output_png.replace(".png", "_palettes.png")
        palette_info.save(palette_png)

        # Save metadata
        metadata_file = output_png.replace(".png", "_metadata.json")
        with open(metadata_file, "w") as f:
            json.dump(metadata, f, indent=2)

        # Create palette reference
        self._create_palette_reference(palettes, output_png.replace(".png", "_palette_ref.png"))

        print(f"Sprite sheet extracted to: {output_png}")
        print(f"Palette info saved to: {palette_png}")
        print(f"Metadata saved to: {metadata_file}")

        return metadata

    def _create_palette_reference(self, palettes, output_file):
        """Create visual palette reference"""
        # 16 palettes, 16 colors each
        ref_width = 16 * 16
        ref_height = 16 * 16

        ref_img = Image.new("RGB", (ref_width, ref_height))
        draw = ImageDraw.Draw(ref_img)

        for pal_idx in range(16):
            for color_idx in range(16):
                x = color_idx * 16
                y = pal_idx * 16

                r, g, b = palettes[pal_idx][color_idx]

                draw.rectangle([x, y, x + 15, y + 15], fill=(r, g, b))

        ref_img.save(output_file)

    def validate_edited_sheet(self, edited_png):
        """Validate an edited sprite sheet against SNES constraints"""
        # Load metadata
        metadata_file = edited_png.replace(".png", "_metadata.json")
        if not os.path.exists(metadata_file):
            # Try with original name
            metadata_file = edited_png.replace("_edited.png", "_metadata.json")

        if not os.path.exists(metadata_file):
            raise FileNotFoundError("No metadata found for sprite sheet")

        with open(metadata_file) as f:
            metadata = json.load(f)

        # Load edited sheet
        edited_img = Image.open(edited_png).convert("RGBA")

        # Load palette info if available
        palette_file = edited_png.replace(".png", "_palettes.png")
        if not os.path.exists(palette_file):
            palette_file = edited_png.replace("_edited.png", "_palettes.png")

        if os.path.exists(palette_file):
            Image.open(palette_file).convert("L")

        validation_results = {
            "valid": True,
            "errors": [],
            "warnings": [],
            "tile_issues": {}
        }

        # Check each tile
        for tile_idx_str, tile_info in metadata["tile_info"].items():
            tile_idx = int(tile_idx_str)
            x = tile_info["x"]
            y = tile_info["y"]
            expected_pal = tile_info["palette"]
            cgram_pal = tile_info["cgram_palette"]

            # Extract tile from edited sheet
            tile_box = (x, y, x + 8, y + 8)
            tile_img = edited_img.crop(tile_box)

            # Get unique colors
            colors = set()
            transparent_pixels = 0

            for py in range(8):
                for px in range(8):
                    pixel = tile_img.getpixel((px, py))
                    if len(pixel) == 4 and pixel[3] == 0:  # Transparent
                        transparent_pixels += 1
                    else:
                        colors.add((pixel[0], pixel[1], pixel[2]))

            # Check color count
            if len(colors) > 15:  # 15 + transparent
                validation_results["errors"].append(
                    f"Tile {tile_idx} has too many colors: {len(colors)} (max 15 + transparent)"
                )
                validation_results["tile_issues"][tile_idx] = "too_many_colors"
                validation_results["valid"] = False

            # Check if colors match expected palette
            if cgram_pal < len(metadata["palette_colors"]):
                expected_colors = metadata["palette_colors"][str(cgram_pal)]

                for color in colors:
                    # Find closest color in palette
                    min_dist = float("inf")
                    for pal_color in expected_colors[1:]:  # Skip transparent
                        dist = sum(abs(a - b) for a, b in zip(color, pal_color))
                        min_dist = min(min_dist, dist)

                    if min_dist > 24:  # Tolerance for SNES color precision
                        validation_results["warnings"].append(
                            f"Tile {tile_idx}: Color {color} not in original palette {expected_pal}"
                        )

        # Save validation report
        report_file = edited_png.replace(".png", "_validation.json")
        with open(report_file, "w") as f:
            json.dump(validation_results, f, indent=2)

        print("\nValidation Results:")
        print(f"Valid: {validation_results['valid']}")
        print(f"Errors: {len(validation_results['errors'])}")
        print(f"Warnings: {len(validation_results['warnings'])}")

        if validation_results["errors"]:
            print("\nErrors (first 5):")
            for error in validation_results["errors"][:5]:
                print(f"  - {error}")

        return validation_results

    def reinsert_sheet(self, edited_png, output_vram=None):
        """Convert edited sprite sheet back to VRAM format"""
        # Load metadata
        metadata_file = edited_png.replace(".png", "_metadata.json")
        if not os.path.exists(metadata_file):
            metadata_file = edited_png.replace("_edited.png", "_metadata.json")

        with open(metadata_file) as f:
            metadata = json.load(f)

        # Validate first
        print("Validating sprite sheet...")
        validation = self.validate_edited_sheet(edited_png)

        if not validation["valid"]:
            response = input("\nValidation failed. Continue anyway? (y/n): ")
            if response.lower() != "y":
                print("Reinsertion cancelled")
                return None

        # Load original VRAM
        with open(metadata["source_vram"], "rb") as f:
            vram_data = bytearray(f.read())

        # Load edited sheet
        edited_img = Image.open(edited_png).convert("RGBA")

        # Load palettes
        palettes = parse_cgram(metadata["source_cgram"])

        # Process each tile
        converted_tiles = 0
        for tile_idx_str, tile_info in metadata["tile_info"].items():
            tile_idx = int(tile_idx_str)
            x = tile_info["x"]
            y = tile_info["y"]
            cgram_pal = tile_info["cgram_palette"]

            # Extract tile
            tile_box = (x, y, x + 8, y + 8)
            tile_img = edited_img.crop(tile_box)

            # Convert to indexed format
            indexed_pixels = []
            for py in range(8):
                for px in range(8):
                    pixel = tile_img.getpixel((px, py))

                    if len(pixel) == 4 and pixel[3] == 0:  # Transparent
                        indexed_pixels.append(0)
                    else:
                        # Find closest color in palette
                        best_idx = 0
                        best_dist = float("inf")

                        for color_idx in range(1, 16):  # Skip transparent
                            pal_r, pal_g, pal_b = palettes[cgram_pal][color_idx]

                            dist = abs(pixel[0] - pal_r) + \
                                   abs(pixel[1] - pal_g) + \
                                   abs(pixel[2] - pal_b)

                            if dist < best_dist:
                                best_dist = dist
                                best_idx = color_idx

                        indexed_pixels.append(best_idx)

            # Encode tile
            tile_data = encode_4bpp_tile(indexed_pixels)

            # Write to VRAM
            offset = metadata["offset"] + (tile_idx * 32)
            vram_data[offset:offset + 32] = tile_data

            converted_tiles += 1

        # Save modified VRAM
        if output_vram is None:
            output_vram = metadata["source_vram"].replace(".", "_edited.")

        with open(output_vram, "wb") as f:
            f.write(vram_data)

        print(f"\nConverted {converted_tiles} tiles")
        print(f"Modified VRAM saved to: {output_vram}")

        return output_vram

    def create_editing_guide(self, sprite_sheet_png):
        """Create a visual guide showing palette constraints"""
        # Load metadata
        metadata_file = sprite_sheet_png.replace(".png", "_metadata.json")
        with open(metadata_file) as f:
            metadata = json.load(f)

        # Create guide image
        sheet_img = Image.open(sprite_sheet_png)
        guide_width = sheet_img.width + 300  # Extra space for palette info
        guide_img = Image.new("RGB", (guide_width, sheet_img.height), (32, 32, 32))

        # Paste sprite sheet
        guide_img.paste(sheet_img, (0, 0))

        # Draw palette info
        draw = ImageDraw.Draw(guide_img)
        x_offset = sheet_img.width + 10

        draw.text((x_offset, 10), "Palette Constraints", fill=(255, 255, 255))

        # Show active palettes
        y = 40
        used_palettes = set()
        for tile_info in metadata["tile_info"].values():
            used_palettes.add(tile_info["palette"])

        for pal_idx in sorted(used_palettes):
            cgram_pal = pal_idx + 8
            draw.text((x_offset, y), f"Palette {pal_idx}:", fill=(255, 255, 255))

            # Draw color swatches
            x = x_offset
            y += 20
            for color_idx in range(16):
                if str(cgram_pal) in metadata["palette_colors"]:
                    r, g, b = metadata["palette_colors"][str(cgram_pal)][color_idx]
                    draw.rectangle([x, y, x + 15, y + 15], fill=(r, g, b))
                    x += 16

            y += 25

        # Add instructions
        y += 20
        instructions = [
            "Editing Guidelines:",
            "1. Use only colors from assigned palette",
            "2. Maximum 15 colors + transparent per tile",
            "3. Color index 0 is always transparent",
            "4. Maintain 8x8 pixel tile boundaries",
            "5. Save as PNG with transparency"
        ]

        for instruction in instructions:
            draw.text((x_offset, y), instruction, fill=(200, 200, 200))
            y += 18

        # Save guide
        guide_file = sprite_sheet_png.replace(".png", "_editing_guide.png")
        guide_img.save(guide_file)
        print(f"Editing guide saved to: {guide_file}")

def main():
    """Command-line interface"""
    import argparse

    parser = argparse.ArgumentParser(description="Sprite sheet batch editor")
    subparsers = parser.add_subparsers(dest="command")

    # Extract command
    extract_parser = subparsers.add_parser("extract", help="Extract sprite sheet for editing")
    extract_parser.add_argument("vram", help="VRAM dump file")
    extract_parser.add_argument("cgram", help="CGRAM dump file")
    extract_parser.add_argument("--output", "-o", default="sprite_sheet.png",
                               help="Output PNG file")
    extract_parser.add_argument("--mappings", "-m", help="Palette mapping file")
    extract_parser.add_argument("--guide", action="store_true",
                               help="Create editing guide")

    # Validate command
    validate_parser = subparsers.add_parser("validate", help="Validate edited sheet")
    validate_parser.add_argument("sheet", help="Edited sprite sheet PNG")

    # Reinsert command
    reinsert_parser = subparsers.add_parser("reinsert", help="Convert sheet back to VRAM")
    reinsert_parser.add_argument("sheet", help="Edited sprite sheet PNG")
    reinsert_parser.add_argument("--output", "-o", help="Output VRAM file")

    args = parser.parse_args()

    if args.command == "extract":
        editor = SpriteSheetEditor(args.mappings)
        editor.extract_sheet_for_editing(args.vram, args.cgram,
                                        output_png=args.output)
        if args.guide:
            editor.create_editing_guide(args.output)

    elif args.command == "validate":
        editor = SpriteSheetEditor()
        editor.validate_edited_sheet(args.sheet)

    elif args.command == "reinsert":
        editor = SpriteSheetEditor()
        editor.reinsert_sheet(args.sheet, args.output)

    else:
        parser.print_help()

if __name__ == "__main__":
    main()
