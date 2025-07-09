#!/usr/bin/env python3
"""
Comprehensive sprite editing workflow with palette validation
Provides extract -> edit -> validate -> reinsert pipeline
"""

import json
import os
import shutil
from datetime import datetime

from PIL import Image

from sprite_edit_helpers import (
    decode_4bpp_tile,
    encode_4bpp_tile,
    parse_cgram,
)
from sprite_editor.sprite_editor_core import SpriteEditorCore as SpriteEditor


class SpriteEditWorkflow:
    def __init__(self, palette_mapping_file=None):
        """Initialize workflow with optional palette mapping data"""
        self.editor = SpriteEditor()
        self.palette_mappings = {}
        self.tile_to_palette = {}

        if palette_mapping_file and os.path.exists(palette_mapping_file):
            self.load_palette_mappings(palette_mapping_file)

    def load_palette_mappings(self, mapping_file):
        """Load palette mappings from Mesen tracking data"""
        with open(mapping_file) as f:
            data = json.load(f)

        # Extract tile to palette mappings
        if "tile_mappings" in data:
            for tile_str, info in data["tile_mappings"].items():
                tile_idx = int(tile_str)
                self.tile_to_palette[tile_idx] = info["palette"]

        print(f"Loaded {len(self.tile_to_palette)} palette mappings")

    def extract_for_editing(self, vram_file, cgram_file, offset, size, output_dir, tiles_per_row=16):
        """Extract sprites with correct palettes for editing"""
        # Create output directory
        os.makedirs(output_dir, exist_ok=True)

        # Save metadata
        metadata = {
            "vram_file": os.path.abspath(vram_file),
            "cgram_file": os.path.abspath(cgram_file),
            "offset": offset,
            "size": size,
            "tiles_per_row": tiles_per_row,
            "extraction_time": datetime.now().isoformat(),
            "tile_palette_mappings": {}
        }

        # Read VRAM and CGRAM
        with open(vram_file, "rb") as f:
            f.seek(offset)
            vram_data = f.read(size)

        palettes = parse_cgram(cgram_file)

        # Extract individual tiles with their palettes
        bytes_per_tile = 32
        total_tiles = size // bytes_per_tile

        extracted_count = 0
        for tile_idx in range(total_tiles):
            tile_data = vram_data[tile_idx * bytes_per_tile:(tile_idx + 1) * bytes_per_tile]

            # Skip empty tiles
            if all(b == 0 for b in tile_data):
                continue

            # Get palette for this tile
            palette_num = self.tile_to_palette.get(tile_idx, 0)
            if palette_num > 7:
                palette_num = 0  # Default fallback

            # Apply OAM to CGRAM offset
            cgram_palette = palette_num + 8

            # Create tile image
            pixels = decode_4bpp_tile(tile_data)
            tile_img = Image.new("P", (8, 8))
            tile_img.putdata(pixels)

            # Set palette
            palette_rgb = []
            for color in palettes[cgram_palette]:
                # color is already (r, g, b) tuple from parse_cgram
                palette_rgb.extend(color)

            # Pad palette to 256 colors
            while len(palette_rgb) < 768:
                palette_rgb.extend([0, 0, 0])

            tile_img.putpalette(palette_rgb)

            # Save tile
            tile_filename = f"tile_{tile_idx:04d}_pal{palette_num}.png"
            tile_path = os.path.join(output_dir, tile_filename)
            tile_img.save(tile_path)

            # Store metadata
            metadata["tile_palette_mappings"][tile_idx] = {
                "filename": tile_filename,
                "palette": palette_num,
                "cgram_palette": cgram_palette,
                "offset_in_vram": offset + (tile_idx * bytes_per_tile)
            }

            extracted_count += 1

        # Save metadata
        metadata_path = os.path.join(output_dir, "extraction_metadata.json")
        with open(metadata_path, "w") as f:
            json.dump(metadata, f, indent=2)

        # Create sprite sheet for reference
        self._create_reference_sheet(output_dir, total_tiles, tiles_per_row, palettes)

        print(f"Extracted {extracted_count} tiles to {output_dir}")
        print(f"Metadata saved to {metadata_path}")

        return metadata

    def _create_reference_sheet(self, output_dir, total_tiles, tiles_per_row, palettes):
        """Create a reference sprite sheet showing all tiles"""
        # Load metadata
        metadata_path = os.path.join(output_dir, "extraction_metadata.json")
        with open(metadata_path) as f:
            metadata = json.load(f)

        # Calculate sheet dimensions
        rows = (total_tiles + tiles_per_row - 1) // tiles_per_row
        sheet_width = tiles_per_row * 8
        sheet_height = rows * 8

        # Create sheet
        sheet = Image.new("RGBA", (sheet_width, sheet_height), (0, 0, 0, 0))

        # Place tiles
        for tile_idx, tile_info in metadata["tile_palette_mappings"].items():
            tile_path = os.path.join(output_dir, tile_info["filename"])
            if os.path.exists(tile_path):
                tile_img = Image.open(tile_path)

                # Calculate position
                idx = int(tile_idx)
                x = (idx % tiles_per_row) * 8
                y = (idx // tiles_per_row) * 8

                sheet.paste(tile_img, (x, y))

        # Save reference sheet
        sheet_path = os.path.join(output_dir, "reference_sheet.png")
        sheet.save(sheet_path)
        print(f"Reference sheet saved to {sheet_path}")

    def validate_edited_sprites(self, edit_dir):
        """Validate edited sprites against palette constraints"""
        metadata_path = os.path.join(edit_dir, "extraction_metadata.json")
        if not os.path.exists(metadata_path):
            raise FileNotFoundError("No extraction metadata found")

        with open(metadata_path) as f:
            metadata = json.load(f)

        # Load CGRAM for validation
        palettes = parse_cgram(metadata["cgram_file"])

        validation_results = {
            "valid_tiles": [],
            "invalid_tiles": [],
            "warnings": []
        }

        for _tile_idx_str, tile_info in metadata["tile_palette_mappings"].items():
            tile_path = os.path.join(edit_dir, tile_info["filename"])

            if not os.path.exists(tile_path):
                validation_results["warnings"].append(f"Missing tile: {tile_info['filename']}")
                continue

            # Load and validate tile
            try:
                tile_img = Image.open(tile_path)

                # Check dimensions
                if tile_img.size != (8, 8):
                    validation_results["invalid_tiles"].append({
                        "tile": tile_info["filename"],
                        "error": f"Invalid dimensions: {tile_img.size}, expected (8, 8)"
                    })
                    continue

                # Check color mode
                if tile_img.mode != "P":
                    validation_results["invalid_tiles"].append({
                        "tile": tile_info["filename"],
                        "error": f"Invalid color mode: {tile_img.mode}, expected P (indexed)"
                    })
                    continue

                # Validate colors against palette
                pixels = list(tile_img.getdata())
                invalid_indices = [p for p in pixels if p >= 16]

                if invalid_indices:
                    validation_results["invalid_tiles"].append({
                        "tile": tile_info["filename"],
                        "error": f"Invalid color indices: {set(invalid_indices)}, must be 0-15"
                    })
                    continue

                # Check if colors match original palette (optional strict mode)
                cgram_pal = tile_info["cgram_palette"]
                tile_palette = tile_img.getpalette()

                if tile_palette:
                    # Compare first 16 colors
                    mismatched = False
                    for i in range(16):
                        expected_color = palettes[cgram_pal][i]
                        r_expected, g_expected, b_expected = expected_color

                        r_actual = tile_palette[i * 3]
                        g_actual = tile_palette[i * 3 + 1]
                        b_actual = tile_palette[i * 3 + 2]

                        # Allow small differences due to rounding
                        if abs(r_expected - r_actual) > 8 or \
                           abs(g_expected - g_actual) > 8 or \
                           abs(b_expected - b_actual) > 8:
                            mismatched = True
                            break

                    if mismatched:
                        validation_results["warnings"].append(
                            f"Palette mismatch in {tile_info['filename']} - colors may have changed"
                        )

                validation_results["valid_tiles"].append(tile_info["filename"])

            except Exception as e:
                validation_results["invalid_tiles"].append({
                    "tile": tile_info["filename"],
                    "error": str(e)
                })

        # Save validation report
        report_path = os.path.join(edit_dir, "validation_report.json")
        with open(report_path, "w") as f:
            json.dump(validation_results, f, indent=2)

        print("\nValidation Results:")
        print(f"Valid tiles: {len(validation_results['valid_tiles'])}")
        print(f"Invalid tiles: {len(validation_results['invalid_tiles'])}")
        print(f"Warnings: {len(validation_results['warnings'])}")

        if validation_results["invalid_tiles"]:
            print("\nInvalid tiles:")
            for invalid in validation_results["invalid_tiles"][:5]:
                print(f"  - {invalid['tile']}: {invalid['error']}")
            if len(validation_results["invalid_tiles"]) > 5:
                print(f"  ... and {len(validation_results['invalid_tiles']) - 5} more")

        return validation_results

    def reinsert_sprites(self, edit_dir, output_vram=None, backup=True):
        """Reinsert edited sprites back into VRAM"""
        # Load metadata
        metadata_path = os.path.join(edit_dir, "extraction_metadata.json")
        with open(metadata_path) as f:
            metadata = json.load(f)

        # Validate first
        print("Validating edited sprites...")
        validation = self.validate_edited_sprites(edit_dir)

        if validation["invalid_tiles"]:
            response = input(f"\n{len(validation['invalid_tiles'])} invalid tiles found. Continue? (y/n): ")
            if response.lower() != "y":
                print("Reinsertion cancelled")
                return None

        # Create backup
        vram_file = metadata["vram_file"]
        if backup:
            backup_path = vram_file + f".backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            shutil.copy2(vram_file, backup_path)
            print(f"Created backup: {backup_path}")

        # Read original VRAM
        with open(vram_file, "rb") as f:
            vram_data = bytearray(f.read())

        # Process each tile
        reinserted_count = 0
        for _tile_idx_str, tile_info in metadata["tile_palette_mappings"].items():
            tile_path = os.path.join(edit_dir, tile_info["filename"])

            if not os.path.exists(tile_path):
                continue

            if tile_info["filename"] not in validation["valid_tiles"]:
                continue

            try:
                # Load tile
                tile_img = Image.open(tile_path)
                pixels = list(tile_img.getdata())

                # Encode to 4bpp
                tile_data = encode_4bpp_tile(pixels)

                # Write to VRAM
                offset = tile_info["offset_in_vram"]
                vram_data[offset:offset + 32] = tile_data

                reinserted_count += 1

            except Exception as e:
                print(f"Error reinserting {tile_info['filename']}: {e}")

        # Save modified VRAM
        if output_vram is None:
            output_vram = vram_file.replace(".", "_edited.")

        with open(output_vram, "wb") as f:
            f.write(vram_data)

        print(f"\nReinserted {reinserted_count} tiles")
        print(f"Modified VRAM saved to: {output_vram}")

        # Create preview
        self._create_preview(output_vram, metadata)

        return output_vram

    def _create_preview(self, vram_file, metadata):
        """Create a preview of the modified sprites"""
        # Use the sprite editor to extract with palettes
        preview_path = vram_file.replace(".dmp", "_preview.png").replace(".bin", "_preview.png")

        try:
            preview = self.editor.extract_sprites_with_correct_palettes(
                vram_file,
                metadata["offset"],
                metadata["size"],
                metadata["cgram_file"],
                metadata["tiles_per_row"]
            )

            if preview:
                preview.save(preview_path)
                print(f"Preview saved to: {preview_path}")
        except Exception as e:
            print(f"Could not create preview: {e}")

def main():
    """Command-line interface for sprite editing workflow"""
    import argparse

    parser = argparse.ArgumentParser(description="Sprite editing workflow with palette support")
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # Extract command
    extract_parser = subparsers.add_parser("extract", help="Extract sprites for editing")
    extract_parser.add_argument("vram", help="VRAM dump file")
    extract_parser.add_argument("cgram", help="CGRAM dump file")
    extract_parser.add_argument("--offset", type=lambda x: int(x, 0), default=0xC000,
                               help="Offset in VRAM (default: 0xC000)")
    extract_parser.add_argument("--size", type=lambda x: int(x, 0), default=0x4000,
                               help="Size to extract (default: 0x4000)")
    extract_parser.add_argument("--output", "-o", default="extracted_sprites",
                               help="Output directory")
    extract_parser.add_argument("--mappings", "-m", help="Palette mapping JSON file")
    extract_parser.add_argument("--tiles-per-row", type=int, default=16,
                               help="Tiles per row in reference sheet")

    # Validate command
    validate_parser = subparsers.add_parser("validate", help="Validate edited sprites")
    validate_parser.add_argument("directory", help="Directory containing edited sprites")

    # Reinsert command
    reinsert_parser = subparsers.add_parser("reinsert", help="Reinsert edited sprites")
    reinsert_parser.add_argument("directory", help="Directory containing edited sprites")
    reinsert_parser.add_argument("--output", "-o", help="Output VRAM file")
    reinsert_parser.add_argument("--no-backup", action="store_true",
                                help="Skip creating backup")

    args = parser.parse_args()

    if args.command == "extract":
        workflow = SpriteEditWorkflow(args.mappings)
        workflow.extract_for_editing(
            args.vram, args.cgram, args.offset, args.size,
            args.output, args.tiles_per_row
        )

    elif args.command == "validate":
        workflow = SpriteEditWorkflow()
        workflow.validate_edited_sprites(args.directory)

    elif args.command == "reinsert":
        workflow = SpriteEditWorkflow()
        workflow.reinsert_sprites(
            args.directory, args.output, not args.no_backup
        )

    else:
        parser.print_help()

if __name__ == "__main__":
    main()
