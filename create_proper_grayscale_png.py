#!/usr/bin/env python3
"""
Create properly indexed grayscale PNG files for the pixel editor.
The key is to use palette indices (0-15) as pixel values, not gray values.
"""

import json
import sys

import numpy as np
from PIL import Image


def create_proper_grayscale_png(input_file, output_file):
    """Convert a grayscale PNG to properly indexed format"""
    print(f"\nConverting to properly indexed grayscale: {input_file}")

    # Open the image
    img = Image.open(input_file)
    width, height = img.size

    # Get pixel data
    if img.mode == "P":
        pixels = np.array(img)
    else:
        # Convert to grayscale if needed
        img_gray = img.convert("L")
        pixels = np.array(img_gray)

    # Find unique values and create mapping
    unique_values = np.unique(pixels)
    print(f"Unique pixel values in source: {unique_values}")

    # Create mapping from gray values to indices
    # We'll map the unique gray values to indices 0-15
    value_to_index = {}

    # Special case for common grayscale mappings
    common_gray_values = [0, 17, 34, 51, 68, 85, 102, 119, 136, 153, 170, 187, 204, 221, 238, 255]

    if len(unique_values) <= 16:
        # Check if these are the standard grayscale values
        if all(v in common_gray_values for v in unique_values):
            # Map common gray values to their indices
            for i, gray in enumerate(common_gray_values):
                if gray in unique_values:
                    value_to_index[gray] = i
        else:
            # Just map in order
            for i, val in enumerate(unique_values):
                if i < 16:
                    value_to_index[val] = i

    print("\nValue to index mapping:")
    for val, idx in sorted(value_to_index.items()):
        print(f"  Gray {val:3d} -> Index {idx:2d}")

    # Create new indexed image with indices 0-15
    indexed_data = np.zeros_like(pixels, dtype=np.uint8)

    for old_val, new_idx in value_to_index.items():
        mask = pixels == old_val
        indexed_data[mask] = new_idx

    # Create indexed image
    indexed_img = Image.fromarray(indexed_data, mode="P")

    # Create proper grayscale palette
    # Map indices to gray values
    gray_levels = {}
    gray_levels[0] = 0  # Transparent/black
    for i in range(1, 16):
        # Map indices 1-15 to gray values 17-255
        gray_levels[i] = int(17 + (i-1) * (255-17) / 14)

    # Build palette
    palette_data = []
    for i in range(256):
        if i < 16:
            gray = gray_levels[i]
            palette_data.extend([gray, gray, gray])
        else:
            palette_data.extend([0, 0, 0])

    indexed_img.putpalette(palette_data)

    # Save the properly indexed image
    indexed_img.save(output_file, "PNG")

    print(f"\nProperly indexed grayscale saved to: {output_file}")
    print(f"Image dimensions: {width}x{height}")
    print(f"Unique index values: {np.unique(indexed_data)}")

    # Create metadata file if input has one
    input_metadata = input_file.replace(".png", "_metadata.json")
    if input_metadata.endswith("_v2_metadata.json"):
        input_metadata = input_metadata.replace("_v2_metadata.json", "_metadata.json")

    if sys.path.exists(input_metadata) if hasattr(sys, "path") else False:
        # Copy metadata with updated info
        try:
            with open(input_metadata) as f:
                metadata = json.load(f)

            metadata["properly_indexed"] = True
            metadata["index_mapping"] = {str(k): v for k, v in value_to_index.items()}

            output_metadata = output_file.replace(".png", "_metadata.json")
            with open(output_metadata, "w") as f:
                json.dump(metadata, f, indent=2)

            print(f"Metadata updated: {output_metadata}")
        except:
            pass

    return True

def main():
    """Convert common grayscale files"""
    files_to_convert = [
        ("kirby_sprites_grayscale_fixed.png", "kirby_sprites_indexed_grayscale.png"),
        ("kirby_sprites_grayscale_ultrathink.png", "kirby_sprites_indexed_grayscale_ultra.png"),
        ("kirby_sprites_grayscale_fixed_v2.png", "kirby_sprites_indexed_grayscale_v3.png"),
    ]

    for input_file, output_file in files_to_convert:
        try:
            create_proper_grayscale_png(input_file, output_file)
        except FileNotFoundError:
            print(f"File not found: {input_file}")
        except Exception as e:
            print(f"Error processing {input_file}: {e}")

    # Handle command line
    if len(sys.argv) > 1:
        input_file = sys.argv[1]
        output_file = sys.argv[2] if len(sys.argv) > 2 else input_file.replace(".png", "_indexed.png")
        create_proper_grayscale_png(input_file, output_file)

if __name__ == "__main__":
    main()
