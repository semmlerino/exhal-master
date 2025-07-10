#!/usr/bin/env python3
"""
Create a side-by-side comparison of different palette versions
to clearly show how sprites look with different palettes
"""

from PIL import Image, ImageDraw


def create_palette_comparison():
    """Create a comparison image showing different palette versions"""

    # Load the different palette versions
    palette_files = [
        ("OAM Correct", "demo_oam_correct.png"),
        ("Palette 0", "demo_palette_0.png"),
        ("Palette 2", "demo_palette_2.png"),
        ("Palette 3", "demo_palette_3.png"),
        ("Palette 4", "demo_palette_4.png"),
        ("Palette 6", "demo_palette_6.png"),
        ("Palette 7", "demo_palette_7.png")
    ]

    # Load just a portion of each image (first 128x128 pixels for visibility)
    crop_size = (128, 128)
    scale_factor = 2

    images = []
    for label, filename in palette_files:
        try:
            img = Image.open(filename)
            # Crop to show just the top-left portion
            cropped = img.crop((0, 0, crop_size[0], crop_size[1]))
            # Scale up for better visibility
            scaled = cropped.resize(
                (crop_size[0] * scale_factor, crop_size[1] * scale_factor),
                resample=Image.NEAREST
            )
            images.append((label, scaled))
        except Exception as e:
            print(f"Could not load {filename}: {e}")

    if not images:
        print("No images loaded!")
        return

    # Create comparison image
    img_width = images[0][1].width
    img_height = images[0][1].height
    padding = 10
    label_height = 30

    # Calculate grid dimensions
    cols = 4
    rows = (len(images) + cols - 1) // cols

    total_width = cols * img_width + (cols + 1) * padding
    total_height = rows * (img_height + label_height) + (rows + 1) * padding

    comparison = Image.new("RGB", (total_width, total_height), (32, 32, 32))
    draw = ImageDraw.Draw(comparison)

    # Place images in grid
    for idx, (label, img) in enumerate(images):
        col = idx % cols
        row = idx // cols

        x = padding + col * (img_width + padding)
        y = padding + row * (img_height + label_height + padding)

        # Paste image
        comparison.paste(img, (x, y))

        # Draw label
        label_x = x + img_width // 2
        label_y = y + img_height + 5

        # Draw text background for readability
        text_bbox = draw.textbbox((0, 0), label)
        text_width = text_bbox[2] - text_bbox[0]
        text_height = text_bbox[3] - text_bbox[1]

        draw.rectangle(
            [(label_x - text_width//2 - 3, label_y - 2),
             (label_x + text_width//2 + 3, label_y + text_height + 2)],
            fill=(0, 0, 0)
        )

        # Draw label text
        draw.text((label_x, label_y), label, fill=(255, 255, 255), anchor="mt")

        # Highlight OAM correct version
        if "OAM" in label:
            for i in range(3):
                draw.rectangle(
                    [(x - i, y - i),
                     (x + img_width + i, y + img_height + i)],
                    outline=(0, 255, 0)
                )

    # Add title
    title = "Kirby Sprite Palette Comparison"
    title_bbox = draw.textbbox((0, 0), title)
    title_bbox[2] - title_bbox[0]

    draw.text((total_width // 2, 5), title, fill=(255, 255, 255), anchor="mt")

    # Save comparison
    comparison.save("demo_palette_comparison.png")
    print("✓ Created demo_palette_comparison.png")

    # Also create a focused comparison of just Kirby
    create_kirby_comparison()

def create_kirby_comparison():
    """Create a comparison focusing on just Kirby sprites"""

    # Extract just Kirby portion from each palette version
    kirby_area = (0, 0, 64, 64)  # Top-left 8x8 tiles
    scale_factor = 4

    images = []
    for pal_num in [0, 2, 3, 4, 6, 7]:
        try:
            img = Image.open(f"demo_palette_{pal_num}.png")
            cropped = img.crop(kirby_area)
            scaled = cropped.resize(
                (kirby_area[2] * scale_factor, kirby_area[3] * scale_factor),
                resample=Image.NEAREST
            )
            images.append((f"Palette {pal_num}", scaled))
        except:
            pass

    # Add OAM correct version at the beginning
    try:
        img = Image.open("demo_oam_correct.png")
        cropped = img.crop(kirby_area)
        scaled = cropped.resize(
            (kirby_area[2] * scale_factor, kirby_area[3] * scale_factor),
            resample=Image.NEAREST
        )
        images.insert(0, ("OAM Correct", scaled))
    except:
        pass

    if not images:
        return

    # Create horizontal strip
    width = sum(img[1].width for img in images) + (len(images) + 1) * 10
    height = images[0][1].height + 50

    strip = Image.new("RGB", (width, height), (32, 32, 32))
    draw = ImageDraw.Draw(strip)

    x = 10
    for label, img in images:
        strip.paste(img, (x, 10))

        # Draw label
        label_x = x + img.width // 2
        label_y = img.height + 15

        # Highlight correct palette
        if "OAM" in label or "Palette 0" in label:
            color = (0, 255, 0)
            # Draw border
            for i in range(3):
                draw.rectangle(
                    [(x - i, 10 - i),
                     (x + img.width + i, 10 + img.height + i)],
                    outline=color
                )
        else:
            color = (255, 255, 255)

        draw.text((label_x, label_y), label, fill=color, anchor="mt")

        x += img.width + 10

    strip.save("demo_kirby_palette_strip.png")
    print("✓ Created demo_kirby_palette_strip.png")

if __name__ == "__main__":
    print("Creating palette comparison images...")
    create_palette_comparison()
    print("\nComparison images created!")
    print("- demo_palette_comparison.png: Grid comparison of all palette versions")
    print("- demo_kirby_palette_strip.png: Focused comparison of Kirby with different palettes")
