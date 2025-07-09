#!/usr/bin/env python3
"""Analyze pixel values in grayscale sprite image to diagnose index mapping issues."""

from collections import Counter

import numpy as np
from PIL import Image


def analyze_grayscale_image(image_path):
    """Analyze pixel value distribution in grayscale image."""
    # Load the image
    img = Image.open(image_path)

    # Convert to grayscale if needed (should already be)
    if img.mode != "L":
        img = img.convert("L")

    # Get pixel data
    pixels = np.array(img)

    # Get unique values and their counts
    unique_values, counts = np.unique(pixels, return_counts=True)
    value_counts = dict(zip(unique_values, counts))

    print(f"Image shape: {pixels.shape}")
    print(f"Image mode: {img.mode}")
    print(f"Pixel value range: {pixels.min()} - {pixels.max()}")
    print(f"Number of unique values: {len(unique_values)}")
    print("\nPixel value distribution:")

    total_pixels = pixels.size
    for value, count in sorted(value_counts.items()):
        percentage = (count / total_pixels) * 100
        print(f"  Value {value:3d}: {count:7d} pixels ({percentage:5.2f}%)")

    # Analyze sprite vs background
    # Assuming background is the most common value
    most_common_value = max(value_counts.items(), key=lambda x: x[1])[0]
    print(f"\nMost common value (likely background): {most_common_value}")

    # Check a small region to understand the pattern
    print("\nSample region (top-left 10x10):")
    sample = pixels[:10, :10]
    print(sample)

    # Print histogram info instead
    print("\nPixel value histogram (text representation):")
    for i in range(0, 256, 16):
        range_end = min(i + 15, 255)
        count = sum(value_counts.get(j, 0) for j in range(i, range_end + 1))
        if count > 0:
            bar_length = int((count / total_pixels) * 50)
            bar = "#" * bar_length
            print(f"  {i:3d}-{range_end:3d}: {bar} ({count} pixels)")

    # Analyze if values are inverted
    # In a typical indexed image, background would be 0 and sprites 1-15
    # But if sprites are white/light, they might have high values
    non_background_pixels = pixels[pixels != most_common_value]
    if len(non_background_pixels) > 0:
        print("\nNon-background pixel values:")
        non_bg_unique = np.unique(non_background_pixels)
        print(f"  Range: {non_bg_unique.min()} - {non_bg_unique.max()}")
        print(f"  Unique values: {non_bg_unique[:20]}...")  # Show first 20

    return pixels, value_counts, most_common_value

def create_corrected_indexed_image(image_path, output_path):
    """Create a corrected indexed image with proper palette indices."""
    img = Image.open(image_path)
    if img.mode != "L":
        img = img.convert("L")

    pixels = np.array(img)

    # Get value distribution
    unique_values = np.unique(pixels)
    value_counts = Counter(pixels.flatten())

    # Find background (most common value)
    background_value = value_counts.most_common(1)[0][0]

    print("\nCreating corrected indexed image...")
    print(f"Background value detected: {background_value}")

    # Create new indexed image
    corrected = np.zeros_like(pixels, dtype=np.uint8)

    # Map values to palette indices
    # If background is high value (e.g., 255), we need to invert
    if background_value > 128:
        # Background is light, sprites are dark - need to invert
        print("Detected inverted image (light background, dark sprites)")

        # Set background to index 0
        corrected[pixels == background_value] = 0

        # Map other values to indices 1-15
        sprite_values = [v for v in unique_values if v != background_value]
        sprite_values.sort()  # Sort from darkest to lightest

        for i, value in enumerate(sprite_values[:15]):  # Max 15 palette entries
            corrected[pixels == value] = i + 1
            print(f"  Mapping pixel value {value} -> palette index {i + 1}")
    else:
        # Background is dark, sprites are light - normal case
        print("Detected normal image (dark background, light sprites)")

        # Set background to index 0
        corrected[pixels == background_value] = 0

        # Map other values to indices 1-15
        sprite_values = [v for v in unique_values if v != background_value]
        sprite_values.sort(reverse=True)  # Sort from lightest to darkest

        for i, value in enumerate(sprite_values[:15]):  # Max 15 palette entries
            corrected[pixels == value] = i + 1
            print(f"  Mapping pixel value {value} -> palette index {i + 1}")

    # Save corrected image
    corrected_img = Image.fromarray(corrected, mode="L")
    corrected_img.save(output_path)
    print(f"\nCorrected indexed image saved as '{output_path}'")

    # Verify the correction
    corrected_unique = np.unique(corrected)
    print(f"Corrected image palette indices: {corrected_unique}")

    return corrected

if __name__ == "__main__":
    # Analyze the grayscale image
    print("Analyzing grayscale sprite image...")
    pixels, value_counts, bg_value = analyze_grayscale_image("kirby_sprites_grayscale_ultrathink.png")

    # Create corrected version
    corrected = create_corrected_indexed_image(
        "kirby_sprites_grayscale_ultrathink.png",
        "kirby_sprites_indexed_corrected.png"
    )
