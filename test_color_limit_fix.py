#!/usr/bin/env python3
"""
Test script to verify the 16-color limit fix for sprite injection.
Tests that sprites are properly limited to 16 colors for SNES compatibility.
"""

import os
import sys
import tempfile
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PIL import Image
import numpy as np

# Import the components we need to test
from spritepal.core.injector import SpriteInjector
from pixel_editor.core.pixel_editor_workers import FileLoadWorker


def create_test_image_with_many_colors(width=32, height=32, num_colors=256):
    """Create a test image with specified number of colors."""
    # Create an array with a gradient of colors
    img_array = np.zeros((height, width), dtype=np.uint8)
    
    # Fill with different color indices
    color_index = 0
    for y in range(height):
        for x in range(width):
            img_array[y, x] = color_index % num_colors
            color_index += 1
    
    # Create indexed image
    img = Image.fromarray(img_array, mode='P')
    
    # Create a palette with the specified number of colors
    palette = []
    for i in range(256):
        # Create different colors by varying RGB values
        r = (i * 7) % 256
        g = (i * 13) % 256
        b = (i * 17) % 256
        palette.extend([r, g, b])
    
    img.putpalette(palette)
    return img


def test_color_limit_fix():
    """Test that the pixel editor properly limits colors to 16."""
    print("Testing 16-color limit fix for SNES sprite compatibility...")
    
    # Create temporary directory for test files
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Test 1: Create an image with 256 colors
        print("\n1. Creating test image with 256 colors...")
        test_image = create_test_image_with_many_colors(32, 32, 256)
        test_image_path = temp_path / "test_256_colors.png"
        test_image.save(str(test_image_path))
        print(f"   Saved test image to: {test_image_path}")
        
        # Verify it has 256 unique colors
        loaded_img = Image.open(test_image_path)
        unique_colors = len(set(loaded_img.getdata()))
        print(f"   Original image has {unique_colors} unique colors")
        
        # Test 2: Load the image with FileLoadWorker (simulated)
        print("\n2. Testing FileLoadWorker color reduction...")
        # We'll directly test the _convert_to_indexed method
        from PyQt6.QtCore import QObject
        
        class MockWorker(FileLoadWorker):
            def __init__(self):
                # Initialize without parent to avoid Qt app requirement
                self._file_path = test_image_path
                self._is_cancelled = False
        
        worker = MockWorker()
        
        # Test the conversion
        converted_img = worker._convert_to_indexed(loaded_img)
        
        if converted_img:
            # Count colors in converted image
            converted_colors = len(set(converted_img.getdata()))
            print(f"   Converted image has {converted_colors} unique colors")
            
            # Save the converted image
            converted_path = temp_path / "test_16_colors.png"
            converted_img.save(str(converted_path))
            
            # Test 3: Validate with SpriteInjector
            print("\n3. Testing SpriteInjector validation...")
            injector = SpriteInjector()
            
            # Test the 256-color image (should fail)
            valid_256, msg_256 = injector.validate_sprite(str(test_image_path))
            print(f"   256-color image validation: {valid_256}")
            print(f"   Message: {msg_256}")
            
            # Test the 16-color image (should pass)
            valid_16, msg_16 = injector.validate_sprite(str(converted_path))
            print(f"   16-color image validation: {valid_16}")
            print(f"   Message: {msg_16}")
            
            # Summary
            print("\n=== TEST SUMMARY ===")
            if not valid_256 and "too many colors" in msg_256.lower():
                print("✓ 256-color image correctly rejected")
            else:
                print("✗ 256-color image should have been rejected")
                
            if valid_16:
                print("✓ 16-color image correctly accepted")
            else:
                print("✗ 16-color image should have been accepted")
                
            if converted_colors <= 16:
                print("✓ Color reduction working correctly")
            else:
                print("✗ Color reduction not working correctly")
        else:
            print("✗ Failed to convert image")


if __name__ == "__main__":
    try:
        test_color_limit_fix()
    except ImportError as e:
        print(f"Import error: {e}")
        print("Make sure to run this from the exhal-master directory")
    except Exception as e:
        print(f"Test failed with error: {e}")
        import traceback
        traceback.print_exc()