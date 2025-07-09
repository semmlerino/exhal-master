#!/usr/bin/env python3
"""
Create a test sprite file in indexed format for testing the pixel editor
"""

from PIL import Image


def create_test_sprite():
    """Create a simple 8x8 test sprite with indexed colors"""

    # Create an 8x8 indexed image
    img = Image.new("P", (8, 8))

    # Create a simple 16-color palette
    palette = []
    colors = [
        (0, 0, 0),      # 0 - Black (transparent)
        (255, 255, 255), # 1 - White
        (255, 0, 0),     # 2 - Red
        (0, 255, 0),     # 3 - Green
        (0, 0, 255),     # 4 - Blue
        (255, 255, 0),   # 5 - Yellow
        (255, 0, 255),   # 6 - Magenta
        (0, 255, 255),   # 7 - Cyan
        (128, 128, 128), # 8 - Gray
        (255, 128, 0),   # 9 - Orange
        (128, 0, 255),   # 10 - Purple
        (0, 128, 128),   # 11 - Teal
        (128, 128, 0),   # 12 - Olive
        (128, 0, 128),   # 13 - Dark magenta
        (192, 192, 192), # 14 - Light gray
        (64, 64, 64),    # 15 - Dark gray
    ]

    for color in colors:
        palette.extend(color)

    # Pad to 256 colors
    while len(palette) < 768:
        palette.extend([0, 0, 0])

    img.putpalette(palette)

    # Create a simple pattern - a smiley face
    pattern = [
        [0, 1, 1, 1, 1, 1, 1, 0],  # Top border
        [1, 2, 2, 2, 2, 2, 2, 1],  # Red background
        [1, 2, 4, 2, 2, 4, 2, 1],  # Blue eyes
        [1, 2, 2, 2, 2, 2, 2, 1],  # Red background
        [1, 2, 4, 2, 2, 4, 2, 1],  # Blue nose
        [1, 2, 4, 4, 4, 4, 2, 1],  # Blue mouth
        [1, 2, 2, 2, 2, 2, 2, 1],  # Red background
        [0, 1, 1, 1, 1, 1, 1, 0],  # Bottom border
    ]

    # Convert to flat pixel data
    pixels = []
    for row in pattern:
        pixels.extend(row)

    img.putdata(pixels)
    return img

def create_kirby_test_sprite():
    """Create a simple Kirby-inspired test sprite"""

    img = Image.new("P", (16, 16))

    # Kirby-like palette
    palette = []
    colors = [
        (0, 0, 0),        # 0 - Black (transparent)
        (255, 183, 197),  # 1 - Kirby pink
        (255, 255, 255),  # 2 - White (highlight)
        (0, 0, 0),        # 3 - Black (outline)
        (255, 0, 0),      # 4 - Red
        (0, 0, 255),      # 5 - Blue (eyes)
        (255, 220, 220),  # 6 - Light pink
        (200, 120, 150),  # 7 - Dark pink
        (255, 255, 0),    # 8 - Yellow
        (0, 255, 0),      # 9 - Green
        (255, 128, 0),    # 10 - Orange
        (128, 0, 255),    # 11 - Purple
        (0, 128, 128),    # 12 - Teal
        (128, 128, 0),    # 13 - Olive
        (192, 192, 192),  # 14 - Light gray
        (64, 64, 64),     # 15 - Dark gray
    ]

    for color in colors:
        palette.extend(color)

    # Pad to 256 colors
    while len(palette) < 768:
        palette.extend([0, 0, 0])

    img.putpalette(palette)

    # Create a simple Kirby-like pattern
    pattern = [
        [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        [0, 0, 0, 3, 3, 3, 3, 3, 3, 3, 3, 0, 0, 0, 0, 0],
        [0, 0, 3, 1, 1, 1, 1, 1, 1, 1, 1, 3, 0, 0, 0, 0],
        [0, 3, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 3, 0, 0, 0],
        [0, 3, 1, 1, 5, 5, 1, 1, 5, 5, 1, 1, 3, 0, 0, 0],
        [0, 3, 1, 1, 5, 3, 1, 1, 5, 3, 1, 1, 3, 0, 0, 0],
        [0, 3, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 3, 0, 0, 0],
        [0, 3, 1, 1, 1, 1, 4, 4, 1, 1, 1, 1, 3, 0, 0, 0],
        [0, 3, 1, 1, 1, 4, 4, 4, 4, 1, 1, 1, 3, 0, 0, 0],
        [0, 3, 1, 1, 1, 1, 4, 4, 1, 1, 1, 1, 3, 0, 0, 0],
        [0, 3, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 3, 0, 0, 0],
        [0, 3, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 3, 0, 0, 0],
        [0, 0, 3, 1, 1, 1, 1, 1, 1, 1, 1, 3, 0, 0, 0, 0],
        [0, 0, 0, 3, 3, 3, 3, 3, 3, 3, 3, 0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    ]

    # Convert to flat pixel data
    pixels = []
    for row in pattern:
        pixels.extend(row)

    img.putdata(pixels)
    return img

if __name__ == "__main__":
    # Create test sprites
    print("Creating test sprites...")

    # 8x8 smiley face
    smiley = create_test_sprite()
    smiley.save("test_smiley_8x8.png")
    print("Created test_smiley_8x8.png")

    # 16x16 Kirby-like sprite
    kirby = create_kirby_test_sprite()
    kirby.save("test_kirby_16x16.png")
    print("Created test_kirby_16x16.png")

    print("Test sprites created successfully!")
