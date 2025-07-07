#!/usr/bin/env python3
"""
View SNES sprites at 2x or 4x zoom for easier identification
"""

import sys
from PIL import Image

def main():
    if len(sys.argv) < 3:
        print("Usage: python view_sprites_zoomed.py input.png zoom_factor")
        print("Example: python view_sprites_zoomed.py kirby.png 4")
        sys.exit(1)
    
    input_file = sys.argv[1]
    zoom = int(sys.argv[2])
    
    # Load and zoom
    img = Image.open(input_file)
    zoomed = img.resize((img.width * zoom, img.height * zoom), Image.NEAREST)
    
    output_file = input_file.replace('.png', f'_x{zoom}.png')
    zoomed.save(output_file)
    print(f"Saved zoomed image to {output_file}")

if __name__ == "__main__":
    main()