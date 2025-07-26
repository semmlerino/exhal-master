#!/usr/bin/env python3
"""Test newly discovered sprite locations by converting to PNG."""

import json
import os
import subprocess
import tempfile

import numpy as np
from PIL import Image


def decompress_rom_data(rom_path: str, offset: int, exhal_path: str) -> bytes:
    """Decompress data from ROM at given offset."""
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        tmp_path = tmp.name

    try:
        # Run exhal to decompress
        cmd = [exhal_path, rom_path, hex(offset), tmp_path]
        result = subprocess.run(cmd, check=False, capture_output=True, text=True)

        if result.returncode == 0 and os.path.exists(tmp_path):
            with open(tmp_path, "rb") as f:
                return f.read()
        else:
            print(f"Decompression failed at {hex(offset)}: {result.stderr}")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)

    return b""

def decode_4bpp_tiles(data: bytes, tiles_per_row: int = 16) -> np.ndarray:
    """Decode 4bpp SNES tile data to pixel array."""
    bytes_per_tile = 32  # 8x8 tile in 4bpp
    tile_width = 8
    tile_height = 8

    if len(data) < bytes_per_tile:
        return np.zeros((tile_height, tile_width), dtype=np.uint8)

    num_tiles = len(data) // bytes_per_tile
    tiles_height = ((num_tiles + tiles_per_row - 1) // tiles_per_row) * tile_height
    tiles_width = tiles_per_row * tile_width

    # Create output array
    pixels = np.zeros((tiles_height, tiles_width), dtype=np.uint8)

    for tile_idx in range(num_tiles):
        tile_start = tile_idx * bytes_per_tile
        tile_data = data[tile_start:tile_start + bytes_per_tile]

        # Calculate tile position
        tile_row = tile_idx // tiles_per_row
        tile_col = tile_idx % tiles_per_row

        # Decode the tile
        for y in range(tile_height):
            # Get the 4 bytes for this row (2 for low bits, 2 for high bits)
            low1 = tile_data[y * 2] if y * 2 < len(tile_data) else 0
            low2 = tile_data[y * 2 + 1] if y * 2 + 1 < len(tile_data) else 0
            high1 = tile_data[16 + y * 2] if 16 + y * 2 < len(tile_data) else 0
            high2 = tile_data[16 + y * 2 + 1] if 16 + y * 2 + 1 < len(tile_data) else 0

            # Decode pixels for this row
            for x in range(tile_width):
                bit_pos = 7 - x

                # Extract the 4 bits for this pixel
                bit0 = (low1 >> bit_pos) & 1
                bit1 = (low2 >> bit_pos) & 1
                bit2 = (high1 >> bit_pos) & 1
                bit3 = (high2 >> bit_pos) & 1

                # Combine into pixel value (0-15)
                pixel_value = bit0 | (bit1 << 1) | (bit2 << 2) | (bit3 << 3)

                # Place in output array
                out_y = tile_row * tile_height + y
                out_x = tile_col * tile_width + x

                if out_y < tiles_height and out_x < tiles_width:
                    pixels[out_y, out_x] = pixel_value

    return pixels

def save_sprite_png(data: bytes, output_path: str, tiles_per_row: int = 16):
    """Save sprite data as PNG."""
    pixels = decode_4bpp_tiles(data, tiles_per_row)

    # Convert to grayscale (0-15 to 0-255)
    pixels = (pixels * 17).astype(np.uint8)

    # Create image
    img = Image.fromarray(pixels, mode="L")
    img.save(output_path)
    print(f"Saved {output_path} - {img.size[0]}x{img.size[1]} pixels")

def main():
    # Find exhal tool
    exhal_paths = [
        "../archive/obsolete_test_images/ultrathink/exhal",
        "../archive/obsolete_test_images/ultrathink/exhal.exe"
    ]

    exhal_path = None
    for path in exhal_paths:
        if os.path.exists(path):
            exhal_path = os.path.abspath(path)
            break

    if not exhal_path:
        print("ERROR: Could not find exhal tool!")
        return

    print(f"Using exhal: {exhal_path}")

    # Load sprite scan results
    scan_results_file = "sprite_scan_results_Kirby's Fun Pak (Europe).json"
    if not os.path.exists(scan_results_file):
        print(f"ERROR: {scan_results_file} not found!")
        return

    with open(scan_results_file) as f:
        scan_data = json.load(f)

    # Find ROM
    rom_path = "Kirby's Fun Pak (Europe).sfc"
    if not os.path.exists(rom_path):
        print(f"ERROR: ROM not found: {rom_path}")
        return

    # Test top quality sprites
    print("\nTesting top quality sprite locations:")
    print("=" * 50)

    # Get top 10 results by quality
    top_results = sorted(scan_data["scan_results"],
                        key=lambda x: x["quality"],
                        reverse=True)[:10]

    for i, result in enumerate(top_results):
        offset = result["offset"]
        quality = result["quality"]
        size = result["size"]

        print(f"\n{i+1}. Offset: 0x{offset:06X}, Quality: {quality:.2f}, Size: {size} bytes")

        # Decompress data
        data = decompress_rom_data(rom_path, offset, exhal_path)

        if data:
            # Save as PNG
            output_file = f"sprite_test_{i+1:02d}_0x{offset:06X}_q{int(quality*100)}.png"
            save_sprite_png(data, output_file)

            # Also save raw decompressed data for inspection
            raw_file = f"sprite_test_{i+1:02d}_0x{offset:06X}.bin"
            with open(raw_file, "wb") as f:
                f.write(data)
            print(f"  Raw data saved to {raw_file}")

            # Try different tile arrangements
            for tiles_per_row in [8, 16, 32]:
                alt_file = f"sprite_test_{i+1:02d}_0x{offset:06X}_w{tiles_per_row}.png"
                save_sprite_png(data, alt_file, tiles_per_row)
        else:
            print("  Failed to decompress!")

    print("\nDone! Check the generated PNG files.")

if __name__ == "__main__":
    main()
