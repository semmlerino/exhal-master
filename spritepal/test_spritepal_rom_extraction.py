#!/usr/bin/env python3
"""Test ROM extraction in SpritePal with new sprite locations."""

import os
import sys
import traceback

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import numpy as np
from PIL import Image

from spritepal.core.rom_extractor import ROMExtractor
from spritepal.core.sprite_config_loader import SpriteConfigLoader


def test_rom_extraction():
    """Test extracting sprites from ROM using new locations."""
    print("Testing ROM extraction with new sprite locations...")
    print("=" * 60)

    # Find ROM
    rom_path = "Kirby's Fun Pak (Europe).sfc"
    if not os.path.exists(rom_path):
        print(f"ERROR: ROM not found: {rom_path}")
        return

    # Load sprite configuration
    SpriteConfigLoader()

    # Test each high-quality sprite location
    test_sprites = [
        ("High_Quality_Sprite_1", "0x200000", "Perfect quality (1.00)"),
        ("High_Quality_Sprite_2", "0x378000", "Very high quality (0.98)"),
        ("High_Quality_Sprite_3", "0x1D0002", "Excellent quality (0.96)"),
        ("High_Quality_Sprite_4", "0x1C0000", "High quality (0.94)")
    ]

    for sprite_name, offset, description in test_sprites:
        print(f"\nTesting: {sprite_name} at {offset} - {description}")
        print("-" * 40)

        try:
            # Create extractor
            extractor = ROMExtractor(rom_path)

            # Extract sprite data
            sprite_data = extractor.extract_sprite_at_offset(int(offset, 16))

            if sprite_data:
                print(f"  ✓ Successfully extracted {len(sprite_data)} bytes")

                # Check if it's valid 4bpp data
                if len(sprite_data) % 32 == 0:
                    num_tiles = len(sprite_data) // 32
                    print(f"  ✓ Valid 4bpp format: {num_tiles} tiles")
                else:
                    print("  ⚠ Size not multiple of 32 bytes")

                # Save as binary for inspection
                bin_file = f"spritepal_test_{sprite_name}.bin"
                with open(bin_file, "wb") as f:
                    f.write(sprite_data)
                print(f"  ✓ Saved raw data to {bin_file}")

                # Try to create image
                try:
                    # Simple 4bpp to grayscale conversion
                    pixels = []
                    for i in range(0, min(len(sprite_data), 512), 2):
                        byte1 = sprite_data[i] if i < len(sprite_data) else 0
                        byte2 = sprite_data[i+1] if i+1 < len(sprite_data) else 0
                        # Extract 4 pixels (2 bits each from both bytes)
                        for j in range(4):
                            pixel = ((byte1 >> (6-j*2)) & 3) | (((byte2 >> (6-j*2)) & 3) << 2)
                            pixels.append(pixel * 17)  # Scale 0-15 to 0-255

                    # Create small preview image
                    width = 64
                    height = min(len(pixels) // width, 64)
                    if height > 0:
                        img_data = np.array(pixels[:width*height]).reshape(height, width)
                        img = Image.fromarray(img_data.astype(np.uint8), mode="L")
                        png_file = f"spritepal_test_{sprite_name}.png"
                        img.save(png_file)
                        print(f"  ✓ Saved preview to {png_file}")
                except Exception as e:
                    print(f"  ⚠ Could not create preview: {e}")

            else:
                print("  ✗ Failed to extract sprite data")

        except Exception as e:
            print(f"  ✗ Error: {e}")
            traceback.print_exc()

    print("\n" + "=" * 60)
    print("Test complete! Check generated files.")
    print("\nNext step: Launch SpritePal GUI and test ROM extraction tab")
    print("with these sprite locations to see if they display correctly.")

if __name__ == "__main__":
    test_rom_extraction()
