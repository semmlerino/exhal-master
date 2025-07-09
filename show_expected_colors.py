#!/usr/bin/env python3
"""
Show what the pixel editor colors should look like
Creates a visual reference for the expected colors
"""

import sys

from PIL import Image, ImageDraw, ImageFont


def create_color_reference():
    """Create a visual reference showing all the colors"""

    # SNES palette colors from the editor
    colors = [
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

    # Create a larger image to show all colors
    cell_size = 60
    cols = 4
    rows = 4
    margin = 10

    width = cols * cell_size + margin * 2
    height = rows * cell_size + margin * 2 + 100  # Extra space for title

    # Create RGB image
    img = Image.new("RGB", (width, height), (240, 240, 240))
    draw = ImageDraw.Draw(img)

    # Draw title
    title = "Expected Colors in Pixel Editor"
    try:
        # Try to use a nice font
        font = ImageFont.truetype("arial.ttf", 16)
    except:
        # Fallback to default font
        font = ImageFont.load_default()

    # Get title dimensions
    title_bbox = draw.textbbox((0, 0), title, font=font)
    title_width = title_bbox[2] - title_bbox[0]
    title_x = (width - title_width) // 2

    draw.text((title_x, 10), title, fill=(0, 0, 0), font=font)

    # Draw subtitle
    subtitle = "If you see grayscale, there's a display/Qt issue"
    subtitle_bbox = draw.textbbox((0, 0), subtitle, font=font)
    subtitle_width = subtitle_bbox[2] - subtitle_bbox[0]
    subtitle_x = (width - subtitle_width) // 2

    draw.text((subtitle_x, 35), subtitle, fill=(100, 100, 100), font=font)

    # Draw color grid
    for i, color in enumerate(colors):
        row = i // cols
        col = i % cols

        x = margin + col * cell_size
        y = margin + 60 + row * cell_size  # 60 for title space

        # Draw color square
        draw.rectangle([x, y, x + cell_size - 2, y + cell_size - 2], fill=color)

        # Draw border
        draw.rectangle([x, y, x + cell_size - 2, y + cell_size - 2], outline=(0, 0, 0), width=2)

        # Draw index number
        text_color = (255, 255, 255) if sum(color) < 384 else (0, 0, 0)

        # Center the text
        text = str(i)
        text_bbox = draw.textbbox((0, 0), text, font=font)
        text_width = text_bbox[2] - text_bbox[0]
        text_height = text_bbox[3] - text_bbox[1]
        text_x = x + (cell_size - text_width) // 2
        text_y = y + (cell_size - text_height) // 2

        draw.text((text_x, text_y), text, fill=text_color, font=font)

    # Add color descriptions
    descriptions = [
        "0: Black (transparent)",
        "1: Kirby pink (default)",
        "2: White",
        "3: Dark gray",
        "4: Red",
        "5: Blue",
        "6: Light pink",
        "7: Dark pink",
        "8: Yellow",
        "9: Green",
        "10: Orange",
        "11: Purple",
        "12: Teal",
        "13: Olive",
        "14: Light gray",
        "15: Medium gray"
    ]

    # Add descriptions at the bottom
    desc_y = margin + 60 + rows * cell_size + 20
    for i, desc in enumerate(descriptions):
        if i < 8:  # Left column
            x = margin
            y = desc_y + i * 20
        else:  # Right column
            x = margin + width // 2
            y = desc_y + (i - 8) * 20

        draw.text((x, y), desc, fill=(0, 0, 0), font=font)

    return img

def create_drawing_example():
    """Create an example of what drawing should look like"""

    # Create an indexed image with the palette
    img = Image.new("P", (64, 64))

    # Set the palette
    palette = []
    colors = [
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

    for color in colors:
        palette.extend(color)

    # Pad to 256 colors
    while len(palette) < 768:
        palette.extend([0, 0, 0])

    img.putpalette(palette)

    # Create a simple pattern
    pixels = []
    for y in range(64):
        for x in range(64):
            # Create a color gradient pattern
            if x < 16 and y < 16:
                pixels.append(1)  # Kirby pink
            elif x < 32 and y < 16:
                pixels.append(4)  # Red
            elif x < 48 and y < 16:
                pixels.append(8)  # Yellow
            elif x < 64 and y < 16:
                pixels.append(9)  # Green
            elif x < 16 and y < 32:
                pixels.append(5)  # Blue
            elif x < 32 and y < 32:
                pixels.append(11) # Purple
            elif x < 48 and y < 32:
                pixels.append(10) # Orange
            elif x < 64 and y < 32:
                pixels.append(12) # Teal
            else:
                pixels.append(0)  # Black

    img.putdata(pixels)

    # Convert to RGB for display
    return img.convert("RGB")

def main():
    """Create color reference images"""
    print("Creating color reference images...")

    # Create color palette reference
    palette_ref = create_color_reference()
    palette_ref.save("expected_palette_colors.png")
    print("✓ Created expected_palette_colors.png")

    # Create drawing example
    drawing_example = create_drawing_example()
    drawing_example.save("expected_drawing_colors.png")
    print("✓ Created expected_drawing_colors.png")

    print("\n🎨 Color reference images created!")
    print("\nIf the pixel editor is working correctly, you should see:")
    print("- expected_palette_colors.png: Shows all 16 colors with labels")
    print("- expected_drawing_colors.png: Shows what a colored drawing looks like")
    print("\nIf you're seeing grayscale instead of these colors, there may be:")
    print("- A Qt display issue")
    print("- A graphics driver problem")
    print("- A color depth/palette issue")
    print("- WSL display forwarding problems")

    return 0

if __name__ == "__main__":
    sys.exit(main())
