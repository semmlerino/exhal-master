#!/usr/bin/env python3
"""
Apply the exact Kirby palette from the sprite viewer
"""

import sys
from PIL import Image

def apply_exact_kirby_palette(img):
    """Apply the exact palette from the sprite viewer screenshot."""
    # Based on the palette shown in mesprite.png
    palette = []
    
    # Exact Kirby palette (16 colors)
    kirby_colors = [
        (0, 0, 0),        # 0: Transparent/black
        (248, 224, 248),  # 1: Light pink (body highlight)
        (248, 184, 232),  # 2: Pink (main body)
        (248, 144, 200),  # 3: Medium pink
        (240, 96, 152),   # 4: Dark pink (body shadow)
        (192, 48, 104),   # 5: Deep pink/red (outline)
        (248, 248, 248),  # 6: White (eyes, sparkle)
        (216, 216, 216),  # 7: Light gray
        (168, 168, 168),  # 8: Gray
        (120, 120, 120),  # 9: Dark gray
        (248, 144, 144),  # A: Light red/pink (cheeks)
        (248, 80, 80),    # B: Red (feet, cheeks)
        (216, 0, 0),      # C: Dark red
        (144, 0, 0),      # D: Deep red
        (80, 0, 0),       # E: Very dark red
        (40, 0, 0),       # F: Black-red
    ]
    
    for r, g, b in kirby_colors:
        palette.extend([r, g, b])
    
    # Fill rest of palette
    for i in range(16, 256):
        palette.extend([0, 0, 0])
    
    img.putpalette(palette)
    return img

def main():
    if len(sys.argv) < 3:
        print("Usage: python extract_exact_palette.py input.png output.png")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = sys.argv[2]
    
    img = Image.open(input_file)
    img = apply_exact_kirby_palette(img)
    img.save(output_file)
    
    print(f"Applied exact Kirby palette to {output_file}")

if __name__ == "__main__":
    main()