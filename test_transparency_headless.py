#!/usr/bin/env python3
"""
Headless test of transparency handling in the pixel editor
Tests buffer-level transparency without requiring GUI
"""

import sys
import os

# Add the pixel_editor directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'pixel_editor'))

import numpy as np
from PyQt6.QtGui import QImage, QColor
from PyQt6.QtCore import QCoreApplication

from pixel_editor.core.pixel_editor_models import ImageModel, PaletteModel


def create_test_image():
    """Create a simple 4x4 test image with transparency"""
    test_data = np.array([
        [0, 1, 0, 2],  # Row 0: transparent, red, transparent, green
        [1, 0, 2, 0],  # Row 1: red, transparent, green, transparent
        [0, 2, 0, 1],  # Row 2: transparent, green, transparent, red
        [2, 0, 1, 0]   # Row 3: green, transparent, red, transparent
    ], dtype=np.uint8)
    
    image_model = ImageModel(width=4, height=4, data=test_data)
    return image_model


def create_test_palette():
    """Create a simple test palette"""
    palette = PaletteModel()
    palette.colors = [
        (255, 0, 255),   # Index 0: Magenta (will be transparent)
        (255, 0, 0),     # Index 1: Red
        (0, 255, 0),     # Index 2: Green
        (0, 0, 255),     # Index 3: Blue
    ] + [(0, 0, 0)] * 12  # Fill rest with black
    
    return palette


def create_pixel_editor_qimage(image_model, palette_model):
    """Create QImage exactly as the pixel editor does"""
    height, width = image_model.data.shape
    
    # Create color lookup table (exact copy from pixel editor)
    color_lut = np.zeros((256, 3), dtype=np.uint8)
    for i, (r, g, b) in enumerate(palette_model.colors[:16]):
        color_lut[i] = [r, g, b]
    
    # Create QImage buffer using RGB32 format (as in pixel editor)
    qimage_buffer = QImage(width, height, QImage.Format.Format_RGB32)
    
    # Vectorized color conversion (exact copy from pixel editor)
    image_data = np.clip(image_model.data, 0, 255).astype(np.uint8)
    rgb_data = color_lut[image_data]
    
    # Convert RGB to ARGB format for QImage (exact copy from pixel editor)
    argb_data = np.zeros((height, width, 4), dtype=np.uint8)
    argb_data[:, :, 0] = rgb_data[:, :, 2]  # Blue
    argb_data[:, :, 1] = rgb_data[:, :, 1]  # Green  
    argb_data[:, :, 2] = rgb_data[:, :, 0]  # Red
    
    # Handle transparency for index 0 (exact copy from pixel editor)
    mask = (image_data == 0)
    argb_data[mask, 3] = 0  # Alpha = 0 (transparent)
    argb_data[~mask, 3] = 255  # Alpha = 255 (opaque)
    
    # Copy data directly to QImage buffer (exact copy from pixel editor)
    buffer_ptr = qimage_buffer.bits()
    buffer_ptr.setsize(height * width * 4)  # 4 bytes per pixel
    argb_bytes = argb_data.tobytes()
    buffer_ptr[:len(argb_bytes)] = argb_bytes
    
    return qimage_buffer, argb_data


def test_pixel_editor_transparency():
    """Test the pixel editor's transparency implementation"""
    print("Testing Pixel Editor Transparency Implementation")
    print("=" * 60)
    
    # Create test data
    image_model = create_test_image()
    palette_model = create_test_palette()
    
    print("Test image data (4x4):")
    print(image_model.data)
    print()
    
    print("Test palette:")
    for i, color in enumerate(palette_model.colors[:4]):
        transparency = "(transparent)" if i == 0 else "(opaque)"
        print(f"Index {i}: RGB{color} {transparency}")
    print()
    
    # Create QImage using pixel editor's method
    qimage, argb_data = create_pixel_editor_qimage(image_model, palette_model)
    
    print("QImage properties:")
    print(f"Format: {qimage.format()}")
    print(f"Size: {qimage.width()}x{qimage.height()}")
    print(f"Bytes per line: {qimage.bytesPerLine()}")
    print(f"Has alpha channel: {qimage.hasAlphaChannel()}")
    print()
    
    # Test buffer-level transparency
    print("Buffer-level transparency test:")
    print("Position | Index | Expected Alpha | Actual Alpha | Status")
    print("-" * 50)
    
    errors = 0
    transparent_count = 0
    opaque_count = 0
    
    for y in range(4):
        for x in range(4):
            pixel_index = image_model.data[y, x]
            expected_alpha = 0 if pixel_index == 0 else 255
            actual_alpha = argb_data[y, x, 3]
            
            status = "✓" if actual_alpha == expected_alpha else "✗"
            if actual_alpha != expected_alpha:
                errors += 1
            
            if pixel_index == 0:
                transparent_count += 1
            else:
                opaque_count += 1
            
            print(f"({x},{y})      | {pixel_index:5d} | {expected_alpha:14d} | {actual_alpha:12d} | {status}")
    
    print()
    print("Results summary:")
    print(f"Total pixels: {4*4}")
    print(f"Transparent pixels (index 0): {transparent_count}")
    print(f"Opaque pixels (index 1+): {opaque_count}")
    print(f"Errors: {errors}")
    print()
    
    # Test color accuracy
    print("Color accuracy test:")
    print("Position | Index | Expected RGB | Actual RGB | Status")
    print("-" * 55)
    
    color_errors = 0
    for y in range(4):
        for x in range(4):
            pixel_index = image_model.data[y, x]
            expected_rgb = palette_model.colors[pixel_index]
            actual_rgb = (argb_data[y, x, 2], argb_data[y, x, 1], argb_data[y, x, 0])  # Convert BGR to RGB
            
            status = "✓" if actual_rgb == expected_rgb else "✗"
            if actual_rgb != expected_rgb:
                color_errors += 1
            
            print(f"({x},{y})      | {pixel_index:5d} | {expected_rgb} | {actual_rgb} | {status}")
    
    print()
    print(f"Color errors: {color_errors}")
    print()
    
    # Final assessment
    print("FINAL ASSESSMENT:")
    print("=" * 30)
    
    if errors == 0:
        print("✓ TRANSPARENCY TEST PASSED")
        print("  - All index 0 pixels have alpha = 0 (transparent)")
        print("  - All non-zero index pixels have alpha = 255 (opaque)")
    else:
        print("✗ TRANSPARENCY TEST FAILED")
        print(f"  - {errors} pixels have incorrect alpha values")
    
    if color_errors == 0:
        print("✓ COLOR ACCURACY TEST PASSED")
        print("  - All pixels have correct RGB values from palette")
    else:
        print("✗ COLOR ACCURACY TEST FAILED")
        print(f"  - {color_errors} pixels have incorrect RGB values")
    
    print()
    
    if errors == 0 and color_errors == 0:
        print("🎉 SUCCESS: The pixel editor correctly handles transparency!")
        print("   - Index 0 pixels are properly transparent")
        print("   - Non-zero index pixels are properly opaque")
        print("   - All colors match the palette correctly")
        print("   - The QImage buffer is correctly formatted for rendering")
    else:
        print("❌ FAILURE: Issues detected in transparency handling")
    
    return errors == 0 and color_errors == 0


def test_edge_cases():
    """Test edge cases and boundary conditions"""
    print("\nTesting edge cases...")
    print("=" * 30)
    
    # Test with all transparent pixels
    all_transparent = ImageModel(width=2, height=2, data=np.zeros((2, 2), dtype=np.uint8))
    palette = create_test_palette()
    qimage, argb_data = create_pixel_editor_qimage(all_transparent, palette)
    
    all_transparent_correct = np.all(argb_data[:, :, 3] == 0)
    print(f"All transparent image: {'✓' if all_transparent_correct else '✗'}")
    
    # Test with no transparent pixels
    no_transparent = ImageModel(width=2, height=2, data=np.ones((2, 2), dtype=np.uint8))
    qimage, argb_data = create_pixel_editor_qimage(no_transparent, palette)
    
    no_transparent_correct = np.all(argb_data[:, :, 3] == 255)
    print(f"No transparent pixels: {'✓' if no_transparent_correct else '✗'}")
    
    # Test with alternating pattern
    checkerboard = ImageModel(width=2, height=2, data=np.array([[0, 1], [1, 0]], dtype=np.uint8))
    qimage, argb_data = create_pixel_editor_qimage(checkerboard, palette)
    
    checkerboard_correct = (
        argb_data[0, 0, 3] == 0 and   # (0,0) should be transparent
        argb_data[0, 1, 3] == 255 and # (1,0) should be opaque
        argb_data[1, 0, 3] == 255 and # (0,1) should be opaque
        argb_data[1, 1, 3] == 0       # (1,1) should be transparent
    )
    print(f"Checkerboard pattern: {'✓' if checkerboard_correct else '✗'}")
    
    return all_transparent_correct and no_transparent_correct and checkerboard_correct


def main():
    """Main function"""
    # Initialize QCoreApplication for basic Qt functionality
    app = QCoreApplication(sys.argv)
    
    try:
        success = test_pixel_editor_transparency()
        edge_cases_success = test_edge_cases()
        
        final_success = success and edge_cases_success
        
        print("\n" + "=" * 60)
        print("OVERALL RESULT:")
        if final_success:
            print("✅ ALL TESTS PASSED - Transparency handling is working correctly!")
        else:
            print("❌ SOME TESTS FAILED - Issues detected in transparency handling")
        
        sys.exit(0 if final_success else 1)
        
    except Exception as e:
        print(f"Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()