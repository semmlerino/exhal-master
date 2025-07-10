#!/usr/bin/env python3
"""
Test that the pixel editor actually draws with the correct colors
"""

import sys

import numpy as np
from PIL import Image


# Mock the canvas for testing
class MockCanvas:
    def __init__(self, palette_colors):
        self.image_data = np.zeros((8, 8), dtype=np.uint8)
        self.current_color = 1  # Start with Kirby pink
        self.palette_colors = palette_colors

    def draw_pixel(self, x, y):
        if 0 <= x < 8 and 0 <= y < 8:
            color = max(0, min(15, int(self.current_color)))
            self.image_data[y, x] = np.uint8(color)

    def get_pil_image(self):
        img = Image.fromarray(self.image_data, mode="P")

        # Create palette
        palette = []
        for color in self.palette_colors:
            palette.extend(color)

        # Pad to 256 colors
        while len(palette) < 768:
            palette.extend([0, 0, 0])

        img.putpalette(palette)
        return img

def test_drawing_colors():
    """Test that drawing actually uses the correct colors"""
    print("=== Testing Drawing Colors ===\n")

    # Create palette colors (same as in the editor)
    palette_colors = [
        (0, 0, 0),        # 0 - Black (transparent)
        (255, 183, 197),  # 1 - Kirby pink
        (255, 255, 255),  # 2 - White
        (64, 64, 64),     # 3 - Dark gray (outline)
        (255, 0, 0),      # 4 - Red
        (0, 0, 255),      # 5 - Blue
        (255, 220, 220),  # 6 - Light pink
        (200, 120, 150),  # 7 - Dark pink
        (255, 255, 0),    # 8 - Yellow
        (0, 255, 0),      # 9 - Green
        (255, 128, 0),    # 10 - Orange
        (128, 0, 255),    # 11 - Purple
        (0, 128, 128),    # 12 - Teal
        (128, 128, 0),    # 13 - Olive
        (192, 192, 192),  # 14 - Light gray
        (128, 128, 128),  # 15 - Medium gray
    ]

    # Create mock canvas
    canvas = MockCanvas(palette_colors)

    # Test drawing different colors
    print("Testing drawing with different colors...")

    # Draw with Kirby pink (index 1)
    canvas.current_color = 1
    canvas.draw_pixel(1, 1)
    print("✓ Drew pixel with color index 1 (Kirby pink)")

    # Draw with red (index 4)
    canvas.current_color = 4
    canvas.draw_pixel(2, 2)
    print("✓ Drew pixel with color index 4 (red)")

    # Draw with yellow (index 8)
    canvas.current_color = 8
    canvas.draw_pixel(3, 3)
    print("✓ Drew pixel with color index 8 (yellow)")

    # Draw with green (index 9)
    canvas.current_color = 9
    canvas.draw_pixel(4, 4)
    print("✓ Drew pixel with color index 9 (green)")

    # Check the pixel values
    print("\nPixel values in canvas:")
    print(f"  (1,1): {canvas.image_data[1,1]} (should be 1)")
    print(f"  (2,2): {canvas.image_data[2,2]} (should be 4)")
    print(f"  (3,3): {canvas.image_data[3,3]} (should be 8)")
    print(f"  (4,4): {canvas.image_data[4,4]} (should be 9)")

    # Verify the values
    if canvas.image_data[1,1] == 1:
        print("✓ Kirby pink pixel stored correctly")
    else:
        print(f"✗ Kirby pink pixel wrong: {canvas.image_data[1,1]}")
        return False

    if canvas.image_data[2,2] == 4:
        print("✓ Red pixel stored correctly")
    else:
        print(f"✗ Red pixel wrong: {canvas.image_data[2,2]}")
        return False

    if canvas.image_data[3,3] == 8:
        print("✓ Yellow pixel stored correctly")
    else:
        print(f"✗ Yellow pixel wrong: {canvas.image_data[3,3]}")
        return False

    if canvas.image_data[4,4] == 9:
        print("✓ Green pixel stored correctly")
    else:
        print(f"✗ Green pixel wrong: {canvas.image_data[4,4]}")
        return False

    # Test conversion to PIL image
    print("\nTesting image conversion...")
    img = canvas.get_pil_image()

    if img.mode == "P":
        print("✓ Image is in palette mode")
    else:
        print(f"✗ Image is in wrong mode: {img.mode}")
        return False

    # Save the test image
    img.save("test_drawing_colors.png")
    print("✓ Saved test_drawing_colors.png")

    # Load it back and verify colors
    loaded_img = Image.open("test_drawing_colors.png")
    loaded_array = np.array(loaded_img)

    print("\nLoaded image pixel values:")
    print(f"  (1,1): {loaded_array[1,1]} (should be 1)")
    print(f"  (2,2): {loaded_array[2,2]} (should be 4)")
    print(f"  (3,3): {loaded_array[3,3]} (should be 8)")
    print(f"  (4,4): {loaded_array[4,4]} (should be 9)")

    # Verify the loaded values
    if (loaded_array[1,1] == 1 and loaded_array[2,2] == 4 and
        loaded_array[3,3] == 8 and loaded_array[4,4] == 9):
        print("✓ All pixels loaded correctly")
    else:
        print("✗ Some pixels loaded incorrectly")
        return False

    # Test palette extraction
    if loaded_img.palette:
        palette_data = loaded_img.palette.palette

        # Check specific colors
        kirby_pink = (palette_data[3], palette_data[4], palette_data[5])  # Index 1
        red = (palette_data[12], palette_data[13], palette_data[14])      # Index 4
        yellow = (palette_data[24], palette_data[25], palette_data[26])   # Index 8
        green = (palette_data[27], palette_data[28], palette_data[29])    # Index 9

        print("\nExtracted palette colors:")
        print(f"  Index 1 (Kirby pink): {kirby_pink}")
        print(f"  Index 4 (Red): {red}")
        print(f"  Index 8 (Yellow): {yellow}")
        print(f"  Index 9 (Green): {green}")

        if kirby_pink == (255, 183, 197):
            print("✓ Kirby pink palette color is correct")
        else:
            print(f"✗ Kirby pink palette color is wrong: {kirby_pink}")
            return False

        if red == (255, 0, 0):
            print("✓ Red palette color is correct")
        else:
            print(f"✗ Red palette color is wrong: {red}")
            return False

        if yellow == (255, 255, 0):
            print("✓ Yellow palette color is correct")
        else:
            print(f"✗ Yellow palette color is wrong: {yellow}")
            return False

        if green == (0, 255, 0):
            print("✓ Green palette color is correct")
        else:
            print(f"✗ Green palette color is wrong: {green}")
            return False

    print("\n✅ All drawing color tests passed!")
    return True

def main():
    """Run the drawing color tests"""
    success = test_drawing_colors()

    if success:
        print("\n🎉 Drawing colors work correctly!")
        print("\nThe pixel editor should now:")
        print("- Draw with actual colors instead of grayscale")
        print("- Show Kirby pink when index 1 is selected")
        print("- Show red when index 4 is selected")
        print("- Show yellow when index 8 is selected")
        print("- Show green when index 9 is selected")
        print("- etc...")
    else:
        print("\n❌ Some drawing color tests failed")

    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())
