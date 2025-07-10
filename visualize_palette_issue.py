#!/usr/bin/env python3
"""
Create a visual comparison showing why Kirby appears blue with palette 14 vs pink with palette 8
"""

import json

from PIL import Image, ImageDraw, ImageFont


def create_palette_comparison():
    """Create visual comparison of palettes 8 and 14"""

    # Load the palette files
    with open("kirby_palette_8.pal.json") as f:
        pal8_data = json.load(f)

    with open("kirby_palette_14.pal.json") as f:
        pal14_data = json.load(f)

    # Create comparison image
    swatch_size = 40
    width = 600
    height = 800

    img = Image.new("RGB", (width, height), (50, 50, 50))
    draw = ImageDraw.Draw(img)

    # Try to load a font
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 16)
        small_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 12)
    except (OSError, IOError):
        font = ImageFont.load_default()
        small_font = font

    # Title
    draw.text((20, 20), "Kirby Palette Issue Explanation", fill=(255, 255, 255), font=font)

    # Palette 14 (incorrect)
    y_offset = 80
    draw.text((20, y_offset), "Palette 14 (Shows Kirby as BLUE):", fill=(255, 150, 150), font=font)
    y_offset += 30

    pal14_colors = pal14_data["palette"]["colors"]
    for i in range(8):
        x = 20 + (i % 4) * (swatch_size + 10)
        y = y_offset + (i // 4) * (swatch_size + 30)

        color = tuple(pal14_colors[i])
        draw.rectangle([x, y, x + swatch_size, y + swatch_size], fill=color, outline=(255, 255, 255))

        # Label
        label = f"#{i}"
        if i in {2, 3}:
            label += " (blue!)"
        elif i in {6, 7}:
            label += " (pink)"
        draw.text((x, y + swatch_size + 5), label, fill=(255, 255, 255), font=small_font)

    # Explanation for palette 14
    y_offset += 120
    draw.text((20, y_offset), "Problem: Kirby's main body uses indices 2-5", fill=(255, 200, 100), font=small_font)
    y_offset += 20
    draw.text((20, y_offset), "In palette 14, these are BLUE colors!", fill=(255, 200, 100), font=small_font)

    # Palette 8 (correct)
    y_offset += 60
    draw.text((20, y_offset), "Palette 8 (Shows Kirby as PINK/PURPLE - Correct!):", fill=(150, 255, 150), font=font)
    y_offset += 30

    pal8_colors = pal8_data["palette"]["colors"]
    for i in range(8):
        x = 20 + (i % 4) * (swatch_size + 10)
        y = y_offset + (i // 4) * (swatch_size + 30)

        color = tuple(pal8_colors[i])
        draw.rectangle([x, y, x + swatch_size, y + swatch_size], fill=color, outline=(255, 255, 255))

        # Label
        label = f"#{i}"
        if i >= 1 and i <= 5:
            label += " (pink!)"
        draw.text((x, y + swatch_size + 5), label, fill=(255, 255, 255), font=small_font)

    # Explanation for palette 8
    y_offset += 120
    draw.text((20, y_offset), "Correct: All indices 1-6 are shades of pink/purple", fill=(150, 255, 150), font=small_font)
    y_offset += 20
    draw.text((20, y_offset), "This matches Kirby's actual colors!", fill=(150, 255, 150), font=small_font)

    # OAM Analysis findings
    y_offset += 60
    draw.text((20, y_offset), "OAM Analysis Findings:", fill=(255, 255, 255), font=font)
    y_offset += 30
    draw.text((20, y_offset), "• Kirby sprites use OAM palette 0", fill=(200, 200, 200), font=small_font)
    y_offset += 20
    draw.text((20, y_offset), "• OAM palette 0 = CGRAM palette 8", fill=(200, 200, 200), font=small_font)
    y_offset += 20
    draw.text((20, y_offset), "• Some power-up sprites use OAM palette 4 (CGRAM 12)", fill=(200, 200, 200), font=small_font)

    # Save the comparison
    img.save("kirby_palette_issue_comparison.png")
    print("Created visual comparison: kirby_palette_issue_comparison.png")

if __name__ == "__main__":
    create_palette_comparison()
