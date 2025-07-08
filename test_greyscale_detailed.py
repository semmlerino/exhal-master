#!/usr/bin/env python3
"""
Detailed test for greyscale mode with better visualization
"""

import sys
import numpy as np
from PIL import Image
from PyQt6.QtWidgets import QApplication
from indexed_pixel_editor import ColorPaletteWidget, PixelCanvas

def test_greyscale_detailed():
    """Test greyscale mode with detailed visualization"""
    print("🎨 Testing Greyscale Mode - Detailed")
    
    # Create QApplication for Qt widgets
    app = QApplication(sys.argv)
    
    # Create a palette widget with colors
    palette_widget = ColorPaletteWidget()
    print(f"[TEST] Palette colors: {palette_widget.colors}")
    
    # Create a canvas with the palette
    canvas = PixelCanvas(palette_widget)
    
    # Create a 16x16 test image
    canvas.new_image(16, 16)
    print(f"[TEST] Created 16x16 image")
    
    # Draw a pattern with different colors
    for i in range(16):
        # Draw a diagonal line with different colors
        canvas.current_color = i
        canvas.draw_pixel(i, i)
        # Draw a horizontal line
        canvas.draw_pixel(i, 8)
        # Draw a vertical line
        canvas.draw_pixel(8, i)
    
    print(f"[TEST] Drew test pattern")
    
    # Test color mode
    print("\n--- Color Mode ---")
    canvas.greyscale_mode = False
    color_img = canvas.get_pil_image()
    if color_img:
        # Scale up for better visibility
        color_img_scaled = color_img.resize((160, 160), Image.NEAREST)
        color_img_scaled.save("test_color_detailed.png")
        print("✓ Saved test_color_detailed.png (160x160)")
        
        # Check colors
        print(f"Color at (0,0): {color_img.getpixel((0, 0))}")
        print(f"Color at (1,1): {color_img.getpixel((1, 1))}")
        print(f"Color at (2,2): {color_img.getpixel((2, 2))}")
    
    # Test greyscale mode
    print("\n--- Greyscale Mode ---")
    canvas.greyscale_mode = True
    grey_img = canvas.get_pil_image()
    if grey_img:
        # Scale up for better visibility
        grey_img_scaled = grey_img.resize((160, 160), Image.NEAREST)
        grey_img_scaled.save("test_greyscale_detailed.png")
        print("✓ Saved test_greyscale_detailed.png (160x160)")
        
        # Check colors - should be different shades of grey
        print(f"Grey at (0,0): {grey_img.getpixel((0, 0))}")
        print(f"Grey at (1,1): {grey_img.getpixel((1, 1))}")
        print(f"Grey at (2,2): {grey_img.getpixel((2, 2))}")
    
    # Test color preview (simulating the preview functionality)
    print("\n--- Color Preview ---")
    if canvas.image_data is not None:
        # Create indexed image with color palette
        img = Image.fromarray(canvas.image_data, mode='P')
        
        # Set palette using the actual palette colors
        palette = []
        for color in palette_widget.colors:
            palette.extend(color)
        
        # Pad to 256 colors
        while len(palette) < 768:
            palette.extend([0, 0, 0])
        
        img.putpalette(palette)
        
        # Scale up for better visibility
        img_scaled = img.resize((160, 160), Image.NEAREST)
        img_scaled.save("test_preview_detailed.png")
        print("✓ Saved test_preview_detailed.png (160x160)")
        
        # Check colors
        print(f"Preview at (0,0): {img.getpixel((0, 0))}")
        print(f"Preview at (1,1): {img.getpixel((1, 1))}")
        print(f"Preview at (2,2): {img.getpixel((2, 2))}")
    
    # Convert to RGB and check actual colors
    print("\n--- RGB Color Analysis ---")
    if color_img and grey_img:
        color_rgb = color_img.convert('RGB')
        grey_rgb = grey_img.convert('RGB')
        
        print(f"Color mode RGB at (1,1): {color_rgb.getpixel((1, 1))}")
        print(f"Grey mode RGB at (1,1): {grey_rgb.getpixel((1, 1))}")
        
        # Should be: color is pink (255, 183, 197), grey is ~17 (1*17)
        color_rgb_scaled = color_rgb.resize((160, 160), Image.NEAREST)
        grey_rgb_scaled = grey_rgb.resize((160, 160), Image.NEAREST)
        
        color_rgb_scaled.save("test_color_rgb_detailed.png")
        grey_rgb_scaled.save("test_grey_rgb_detailed.png")
        
        print("✓ Saved RGB versions for comparison")
    
    print("\n✅ Detailed greyscale mode test completed!")
    return True

if __name__ == "__main__":
    success = test_greyscale_detailed()
    sys.exit(0 if success else 1)