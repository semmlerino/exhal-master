#!/usr/bin/env python3
"""
Simple test to verify the 16-color limit fix without Qt dependencies.
"""

import os
import sys
import tempfile
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PIL import Image
import numpy as np
from spritepal.core.injector import SpriteInjector


def create_test_image_with_many_colors(width=32, height=32, num_colors=256):
    """Create a test image with specified number of colors."""
    # Create an image with a gradient of colors
    img = Image.new('RGB', (width, height))
    pixels = img.load()
    
    color_index = 0
    for y in range(height):
        for x in range(width):
            # Create different colors
            r = (color_index * 7) % 256
            g = (color_index * 13) % 256
            b = (color_index * 17) % 256
            pixels[x, y] = (r, g, b)
            color_index += 1
    
    # Convert to indexed color mode with many colors
    img_indexed = img.convert('P', palette=Image.ADAPTIVE, colors=num_colors)
    return img_indexed


def test_color_conversion():
    """Test color conversion directly using PIL."""
    print("Testing 16-color conversion fix...")
    
    # Create temporary directory
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Test 1: Create image with many colors
        print("\n1. Creating test image with many colors...")
        test_image = create_test_image_with_many_colors(32, 32, 256)
        
        # Save with 256 colors
        path_256 = temp_path / "test_256_colors.png"
        test_image.save(str(path_256))
        
        # Check color count
        img_256 = Image.open(path_256)
        colors_256 = len(set(img_256.getdata()))
        print(f"   Original image: {colors_256} unique colors")
        
        # Test 2: Convert to 16 colors (simulating what pixel editor does)
        print("\n2. Converting to 16 colors...")
        img_16 = img_256.convert('RGB').convert('P', palette=Image.ADAPTIVE, colors=16)
        
        # Save 16-color version
        path_16 = temp_path / "test_16_colors.png" 
        img_16.save(str(path_16))
        
        # Check color count
        img_16_loaded = Image.open(path_16)
        colors_16 = len(set(img_16_loaded.getdata()))
        print(f"   Converted image: {colors_16} unique colors")
        
        # Test 3: Validate with SpriteInjector
        print("\n3. Validating with SpriteInjector...")
        injector = SpriteInjector()
        
        # Test 256-color image
        valid_256, msg_256 = injector.validate_sprite(str(path_256))
        print(f"   256-color validation: {'PASS' if valid_256 else 'FAIL'}")
        if not valid_256:
            print(f"   Error: {msg_256}")
        
        # Test 16-color image  
        valid_16, msg_16 = injector.validate_sprite(str(path_16))
        print(f"   16-color validation: {'PASS' if valid_16 else 'FAIL'}")
        if not valid_16:
            print(f"   Error: {msg_16}")
            
        # Test 4: Check palette size
        print("\n4. Checking palette data...")
        palette_256 = img_256.getpalette()
        palette_16 = img_16_loaded.getpalette()
        
        print(f"   256-color palette size: {len(palette_256) if palette_256 else 0} bytes")
        print(f"   16-color palette size: {len(palette_16) if palette_16 else 0} bytes")
        
        # Summary
        print("\n=== SUMMARY ===")
        print(f"✓ Color reduction: {colors_256} → {colors_16} colors")
        print(f"{'✓' if not valid_256 else '✗'} 256-color image validation")
        print(f"{'✓' if valid_16 else '✗'} 16-color image validation")
        
        if colors_16 <= 16 and not valid_256 and valid_16:
            print("\n✓ Fix is working correctly!")
        else:
            print("\n✗ Fix needs adjustment")


if __name__ == "__main__":
    test_color_conversion()