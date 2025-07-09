#!/usr/bin/env python3
"""Diagnose palette issues in grayscale PNG files."""

import contextlib
import sys

import numpy as np
from PIL import Image


def inspect_png_palette(filename):
    """Inspect a PNG file's palette and pixel values."""
    print(f"\n=== Inspecting: {filename} ===")

    try:
        img = Image.open(filename)
        print(f"Mode: {img.mode}")
        print(f"Size: {img.size}")

        # Check if image has a palette
        if hasattr(img, "getpalette") and img.getpalette() is not None:
            palette = img.getpalette()
            print("Has palette: Yes")
            print(f"Palette length: {len(palette)} bytes ({len(palette)//3} colors)")

            # Show first few palette entries
            print("\nFirst 16 palette entries (RGB):")
            for i in range(min(16, len(palette)//3)):
                r = palette[i*3]
                g = palette[i*3+1]
                b = palette[i*3+2]
                print(f"  Color {i:2d}: RGB({r:3d}, {g:3d}, {b:3d}) - #{r:02x}{g:02x}{b:02x}")

            # Check if it's truly grayscale
            is_grayscale = True
            for i in range(len(palette)//3):
                r = palette[i*3]
                g = palette[i*3+1]
                b = palette[i*3+2]
                if r != g or g != b:
                    is_grayscale = False
                    break
            print(f"\nIs grayscale palette: {is_grayscale}")

            # Check for pink colors (high red, low green, high blue)
            pink_colors = []
            for i in range(len(palette)//3):
                r = palette[i*3]
                g = palette[i*3+1]
                b = palette[i*3+2]
                # Pink is typically high red and blue, low green
                if r > 200 and b > 200 and g < 150:
                    pink_colors.append((i, r, g, b))

            if pink_colors:
                print(f"\nFound {len(pink_colors)} pink-ish colors:")
                for idx, r, g, b in pink_colors[:5]:  # Show first 5
                    print(f"  Color {idx}: RGB({r}, {g}, {b})")
        else:
            print("Has palette: No")

        # Convert to numpy array to check pixel values
        pixels = np.array(img)
        print(f"\nPixel array shape: {pixels.shape}")
        print(f"Pixel dtype: {pixels.dtype}")
        print(f"Unique pixel values: {len(np.unique(pixels))}")
        print(f"Pixel value range: {pixels.min()} - {pixels.max()}")

        # Show histogram of pixel values
        unique, counts = np.unique(pixels, return_counts=True)
        print("\nMost common pixel values:")
        sorted_indices = np.argsort(counts)[::-1]
        for i in range(min(10, len(unique))):
            idx = sorted_indices[i]
            print(f"  Value {unique[idx]:3d}: {counts[idx]:6d} pixels ({counts[idx]/pixels.size*100:.1f}%)")

    except Exception as e:
        print(f"Error: {e}")

def main():
    # Test files
    test_files = [
        "kirby_sprites_grayscale_fixed.png",
        "kirby_sprites_grayscale_ultrathink.png",
        "test_grayscale_palette.png",
        "test_extraction_grayscale.png"
    ]

    for filename in test_files:
        if len(sys.argv) > 1:
            # Use command line argument
            inspect_png_palette(sys.argv[1])
            break
        with contextlib.suppress(Exception):
            inspect_png_palette(filename)

if __name__ == "__main__":
    main()
