#!/usr/bin/env python3
from __future__ import annotations

"""Visualize VRAM sprite regions as PNG images."""

from pathlib import Path

import numpy as np
from PIL import Image


def decode_4bpp_tiles(data: bytes, tiles_per_row: int = 16) -> np.ndarray:
    """Decode 4bpp SNES tile data to pixel array."""
    bytes_per_tile = 32  # 8x8 tile in 4bpp
    num_tiles = len(data) // bytes_per_tile

    if num_tiles == 0:
        return np.zeros((8, 8), dtype=np.uint8)

    # Calculate image dimensions
    rows = (num_tiles + tiles_per_row - 1) // tiles_per_row
    width = tiles_per_row * 8
    height = rows * 8

    # Create output array
    pixels = np.zeros((height, width), dtype=np.uint8)

    for tile_idx in range(num_tiles):
        tile_data = data[tile_idx * bytes_per_tile:(tile_idx + 1) * bytes_per_tile]

        # Calculate tile position
        tile_x = (tile_idx % tiles_per_row) * 8
        tile_y = (tile_idx // tiles_per_row) * 8

        # Decode the tile
        for y in range(8):
            # Get the two bitplanes for this row
            plane0 = tile_data[y * 2]
            plane1 = tile_data[y * 2 + 1]
            plane2 = tile_data[16 + y * 2]
            plane3 = tile_data[16 + y * 2 + 1]

            for x in range(8):
                bit_pos = 7 - x

                # Extract bits from each plane
                bit0 = (plane0 >> bit_pos) & 1
                bit1 = (plane1 >> bit_pos) & 1
                bit2 = (plane2 >> bit_pos) & 1
                bit3 = (plane3 >> bit_pos) & 1

                # Combine to get pixel value (0-15)
                pixel = bit0 | (bit1 << 1) | (bit2 << 2) | (bit3 << 3)

                pixels[tile_y + y, tile_x + x] = pixel

    return pixels

def create_grayscale_image(pixels: np.ndarray) -> Image.Image:
    """Convert pixel array to grayscale image."""
    # Scale 0-15 values to 0-255
    scaled = (pixels * 17).astype(np.uint8)
    return Image.fromarray(scaled, mode="L")

def main():
    # Find all VRAM region files
    region_files = list(Path().glob("vram_*_VRAM.dmp_*.bin"))

    if not region_files:
        print("No VRAM region files found")
        return

    for region_file in sorted(region_files):
        print(f"\nProcessing: {region_file}")

        # Read the data
        with region_file.open("rb") as f:
            data = f.read()

        print(f"  Size: {len(data)} bytes ({len(data) // 32} tiles)")

        # Decode and visualize
        pixels = decode_4bpp_tiles(data)
        img = create_grayscale_image(pixels)

        # Save as PNG
        output_name = region_file.stem + ".png"
        img.save(output_name)
        print(f"  Saved: {output_name}")

        # Also save a scaled version for better visibility
        scaled_img = img.resize((img.width * 2, img.height * 2), Image.Resampling.NEAREST)
        scaled_name = region_file.stem + "_scaled.png"
        scaled_img.save(scaled_name)
        print(f"  Saved scaled: {scaled_name}")

if __name__ == "__main__":
    main()
