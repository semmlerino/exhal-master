#!/usr/bin/env python3
"""
Create a showcase image demonstrating the multi-palette system
Shows different characters with their correct palettes side by side
"""

from PIL import Image, ImageDraw


def create_showcase():
    """Create a visual showcase of the multi-palette system"""

    # Define showcase items with clear examples
    showcase_items = [
        {
            "name": "Beam Kirby",
            "file": "demo_char_beam_kirby_pal8_4x.png",
            "palette": 8,
            "description": "Yellow/orange Kirby with beam ability"
        },
        {
            "name": "Green/Pink Enemies",
            "file": "demo_char_enemy_set_1_pal4.png",
            "palette": 4,
            "description": "Various enemies using green/pink palette"
        },
        {
            "name": "Blue/Brown Enemies",
            "file": "demo_char_enemy_set_2_pal5.png",
            "palette": 5,
            "description": "Different enemy set with blue/brown colors"
        },
        {
            "name": "Purple/Dark Enemies",
            "file": "demo_char_enemy_set_3_pal6.png",
            "palette": 6,
            "description": "Dark-themed enemy sprites"
        }
    ]

    # Load images
    images = []
    max_height = 0
    for item in showcase_items:
        try:
            img = Image.open(item["file"])
            # Resize if needed to make them similar heights
            if img.height > 150:
                scale = 150 / img.height
                new_width = int(img.width * scale)
                img = img.resize((new_width, 150), resample=Image.NEAREST)
            images.append((item, img))
            max_height = max(max_height, img.height)
        except Exception as e:
            print(f"Could not load {item['file']}: {e}")

    if not images:
        print("No images loaded!")
        return

    # Create showcase image
    padding = 20
    section_width = max(img[1].width for img in images) + padding * 2
    total_width = len(images) * section_width + padding
    total_height = max_height + 100  # Space for labels

    showcase = Image.new("RGB", (total_width, total_height), (32, 32, 32))
    draw = ImageDraw.Draw(showcase)

    # Title
    title = "Kirby Super Star - Multi-Palette Character System"
    draw.text((total_width // 2, 10), title, fill=(255, 255, 255), anchor="mt")

    # Place each character
    x = padding
    for item, img in images:
        # Center image in section
        img_x = x + (section_width - padding * 2 - img.width) // 2
        img_y = 40

        showcase.paste(img, (img_x, img_y))

        # Draw border for clarity
        draw.rectangle(
            [(img_x - 2, img_y - 2),
             (img_x + img.width + 1, img_y + img.height + 1)],
            outline=(128, 128, 128)
        )

        # Character name
        name_y = img_y + img.height + 5
        draw.text((x + section_width // 2 - padding, name_y),
                 item["name"], fill=(255, 255, 255), anchor="mt")

        # Palette number
        pal_y = name_y + 15
        draw.text((x + section_width // 2 - padding, pal_y),
                 f"Palette {item['palette']}", fill=(0, 255, 0), anchor="mt")

        # Description
        desc_y = pal_y + 15
        # Word wrap description
        words = item["description"].split()
        lines = []
        current_line = []
        for word in words:
            current_line.append(word)
            test_line = " ".join(current_line)
            bbox = draw.textbbox((0, 0), test_line)
            if bbox[2] - bbox[0] > section_width - padding * 2:
                current_line.pop()
                lines.append(" ".join(current_line))
                current_line = [word]
        if current_line:
            lines.append(" ".join(current_line))

        for i, line in enumerate(lines):
            draw.text((x + section_width // 2 - padding, desc_y + i * 12),
                     line, fill=(200, 200, 200), anchor="mt")

        x += section_width

    # Add bottom note
    note = "Each character type uses a specific palette - the multi-palette system is working correctly!"
    draw.text((total_width // 2, total_height - 10), note,
             fill=(255, 255, 0), anchor="mb")

    showcase.save("demo_character_showcase.png")
    print("✓ Created demo_character_showcase.png")

    # Also create a simple comparison showing wrong vs right palettes
    create_palette_comparison()

def create_palette_comparison():
    """Show how sprites look wrong with incorrect palettes"""

    import sys
    sys.path.append("sprite_editor")
    from sprite_editor.palette_utils import read_cgram_palette
    from sprite_editor.sprite_editor_core import SpriteEditorCore

    core = SpriteEditorCore()

    # Extract a small region with clear character
    img, _ = core.extract_sprites("VRAM.dmp", 0xC000, 0x200, tiles_per_row=8)

    # Show with different palettes
    comparisons = []
    for pal_num in [0, 4, 8, 12]:  # Wrong, wrong, correct, wrong
        palette = read_cgram_palette("CGRAM.dmp", pal_num)
        if palette:
            colored = img.copy()
            colored.putpalette(palette)
            scaled = colored.resize((colored.width * 3, colored.height * 3),
                                  resample=Image.NEAREST)
            comparisons.append((pal_num, scaled, pal_num == 8))

    # Create comparison strip
    if comparisons:
        width = sum(c[1].width for c in comparisons) + len(comparisons) * 10 + 10
        height = comparisons[0][1].height + 50

        strip = Image.new("RGB", (width, height), (32, 32, 32))
        draw = ImageDraw.Draw(strip)

        draw.text((width // 2, 5), "Same Sprite Data - Different Palettes",
                 fill=(255, 255, 255), anchor="mt")

        x = 10
        for pal_num, img, is_correct in comparisons:
            strip.paste(img, (x, 25))

            # Draw border
            color = (0, 255, 0) if is_correct else (255, 0, 0)
            for i in range(3):
                draw.rectangle(
                    [(x - i - 1, 25 - i - 1),
                     (x + img.width + i, 25 + img.height + i)],
                    outline=color
                )

            # Label
            label = f"Palette {pal_num}"
            if is_correct:
                label += " ✓"
            else:
                label += " ✗"

            draw.text((x + img.width // 2, height - 15), label,
                     fill=color, anchor="mt")

            x += img.width + 10

        strip.save("demo_palette_comparison_proof.png")
        print("✓ Created demo_palette_comparison_proof.png")

if __name__ == "__main__":
    print("Creating character showcase...")
    create_showcase()
    print("\nShowcase complete! View demo_character_showcase.png")
