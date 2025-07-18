#!/usr/bin/env python3
"""
Test to demonstrate the transparency color count issue.
When a PNG is saved with transparency=0, it may be counted as an extra color when loaded.
"""

import numpy as np
from PIL import Image
import tempfile
from pathlib import Path


def test_transparency_adds_color():
    """Test that transparency can add an extra color when counting"""
    
    # Create a simple 8x8 image with exactly 16 colors (indices 0-15)
    image_data = np.array([
        [0, 1, 2, 3, 4, 5, 6, 7],
        [8, 9, 10, 11, 12, 13, 14, 15],
        [0, 1, 2, 3, 4, 5, 6, 7],
        [8, 9, 10, 11, 12, 13, 14, 15],
        [0, 1, 2, 3, 4, 5, 6, 7],
        [8, 9, 10, 11, 12, 13, 14, 15],
        [0, 1, 2, 3, 4, 5, 6, 7],
        [8, 9, 10, 11, 12, 13, 14, 15],
    ], dtype=np.uint8)
    
    # Create a palette with 16 distinct colors
    palette = []
    for i in range(16):
        r = (i * 17) % 256
        g = (i * 33) % 256
        b = (i * 51) % 256
        palette.extend([r, g, b])
    
    # Pad palette to 256 colors (768 values)
    while len(palette) < 768:
        palette.extend([0, 0, 0])
    
    # Create indexed image
    img = Image.fromarray(image_data, mode='P')
    img.putpalette(palette)
    
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        
        # Test 1: Save without transparency
        path_no_trans = tmp_path / "test_no_transparency.png"
        img.save(path_no_trans, format='PNG', optimize=True)
        
        # Test 2: Save with transparency=0 (like pixel editor does)
        path_with_trans = tmp_path / "test_with_transparency.png"
        img.save(path_with_trans, format='PNG', optimize=True, transparency=0)
        
        # Load and count colors
        img_no_trans = Image.open(path_no_trans)
        img_with_trans = Image.open(path_with_trans)
        
        # Count unique pixel values
        colors_no_trans = len(set(img_no_trans.getdata()))
        colors_with_trans = len(set(img_with_trans.getdata()))
        
        print("Test Results:")
        print(f"Original image unique indices: {len(set(image_data.flatten()))}")
        print(f"Colors without transparency: {colors_no_trans}")
        print(f"Colors with transparency=0: {colors_with_trans}")
        
        # Check transparency info
        trans_info_no = img_no_trans.info.get('transparency', 'None')
        trans_info_with = img_with_trans.info.get('transparency', 'None')
        
        print(f"\nTransparency info without: {trans_info_no}")
        print(f"Transparency info with: {trans_info_with}")
        
        # Check if transparency might be causing the extra color
        if colors_with_trans > colors_no_trans:
            print("\n⚠️  ISSUE FOUND: Transparency is adding extra color(s)!")
            print(f"   Added {colors_with_trans - colors_no_trans} extra color(s)")
        
        # Additional check: See what getdata() returns
        print("\nDetailed analysis:")
        data_no_trans = list(img_no_trans.getdata())
        data_with_trans = list(img_with_trans.getdata())
        
        unique_no_trans = sorted(set(data_no_trans))
        unique_with_trans = sorted(set(data_with_trans))
        
        print(f"Unique values without transparency: {unique_no_trans}")
        print(f"Unique values with transparency: {unique_with_trans}")
        
        # Check for differences
        diff = set(unique_with_trans) - set(unique_no_trans)
        if diff:
            print(f"\nExtra values with transparency: {diff}")


if __name__ == "__main__":
    test_transparency_adds_color()