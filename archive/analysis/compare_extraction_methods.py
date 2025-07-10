#!/usr/bin/env python3
"""
Compare different sprite extraction methods to show the improvement
"""

from PIL import Image, ImageDraw

# Create comparison image
width = 800
height = 600
img = Image.new("RGB", (width, height), (32, 32, 32))
draw = ImageDraw.Draw(img)

# Title
draw.text((width // 2, 20), "Sprite Extraction Methods Comparison",
          fill=(255, 255, 255), anchor="mt")

# Method descriptions
y = 60
methods = [
    ("1. Single OAM Dump", "3.1%", (255, 100, 100)),
    ("2. Region Guessing", "~70%", (255, 200, 100)),
    ("3. Mesen Tracking", "43.2%", (100, 255, 100)),
    ("4. Full Coverage", "100%", (100, 200, 255)),
]

for method, coverage, color in methods:
    draw.text((50, y), method, fill=(255, 255, 255))
    draw.text((300, y), coverage, fill=color)

    # Progress bar
    bar_width = 200
    bar_height = 20
    bar_x = 400
    bar_y = y - 5

    # Background
    draw.rectangle([bar_x, bar_y, bar_x + bar_width, bar_y + bar_height],
                  outline=(128, 128, 128), fill=(64, 64, 64))

    # Fill
    if "%" in coverage:
        pct_str = coverage.replace("~", "").replace("%", "")
        pct = float(pct_str)
        fill_width = int(bar_width * pct / 100)
        draw.rectangle([bar_x, bar_y, bar_x + fill_width, bar_y + bar_height],
                      fill=color)

    y += 40

# Add details
y += 20
draw.text((50, y), "Your Progress:", fill=(255, 255, 100))
y += 25

details = [
    "✓ 32 memory dumps collected",
    "✓ 221 unique tiles mapped",
    "✓ 5 distinct palettes identified",
    "✓ Coverage: Kirby, UI, some enemies",
    "",
    "To reach 100% coverage:",
    "• Play more game areas",
    "• Encounter all enemy types",
    "• Use all power-ups",
    "• Visit bonus rooms"
]

for detail in details:
    if detail.startswith("✓"):
        color = (100, 255, 100)
    elif detail.startswith("•"):
        color = (200, 200, 200)
    else:
        color = (255, 255, 255)

    draw.text((70, y), detail, fill=color)
    y += 20

# Palette usage visualization
y = 380
draw.text((50, y), "Palette Distribution:", fill=(255, 255, 255))
y += 25

palette_data = [
    (0, 31, "Kirby", (255, 192, 255)),
    (1, 126, "Enemies/Effects", (255, 255, 192)),
    (2, 15, "UI", (192, 255, 255)),
    (3, 19, "Cave Enemies", (255, 192, 192)),
    (4, 24, "Various", (192, 255, 192)),
]

x_start = 50
for pal, count, _name, color in palette_data:
    width_pct = count / 215  # Total mapped tiles
    bar_w = int(width_pct * 600)

    draw.rectangle([x_start, y, x_start + bar_w, y + 30], fill=color)
    draw.text((x_start + bar_w // 2, y + 15), f"P{pal}\n{count}",
             fill=(0, 0, 0), anchor="mm")

    x_start += bar_w + 2

draw.text((50, y + 40), "Total: 215 mapped tiles across 5 palettes",
         fill=(200, 200, 200))

img.save("extraction_comparison.png")
print("Created extraction_comparison.png")

# Also create a simple coverage map
coverage_img = Image.new("RGB", (256, 256), (32, 32, 32))
draw = ImageDraw.Draw(coverage_img)

# Load mapping data
import json

with open("final_palette_mapping.json") as f:
    data = json.load(f)

# Color each tile
for y in range(32):
    for x in range(16):
        tile = y * 16 + x

        tile_x = x * 16
        tile_y = y * 8

        # Check if mapped
        if str(tile) in data.get("tile_mappings", {}):
            pal = data["tile_mappings"][str(tile)]["palette"]
            colors = [
                (255, 192, 255),  # 0 - Pink
                (255, 255, 192),  # 1 - Yellow
                (192, 255, 255),  # 2 - Cyan
                (255, 192, 192),  # 3 - Red
                (192, 255, 192),  # 4 - Green
            ]
            color = colors[pal % 5]
        else:
            color = (64, 64, 64)  # Unmapped

        draw.rectangle([tile_x, tile_y, tile_x + 15, tile_y + 7], fill=color)

coverage_img.save("mesen_coverage_map.png")
print("Created mesen_coverage_map.png")
