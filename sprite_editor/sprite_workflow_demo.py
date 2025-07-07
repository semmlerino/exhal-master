#!/usr/bin/env python3
"""
Demonstrate the complete sprite editing workflow
"""

from PIL import Image, ImageDraw

def add_edit_guides(sprite_path, output_path):
    """Add guide marks to help with editing."""
    sprite = Image.open(sprite_path)

    # Create a 4x scaled version for easier editing
    scaled = sprite.resize((sprite.width * 4, sprite.height * 4), Image.NEAREST)

    # Add grid lines every 8 pixels (32 pixels in scaled version)
    draw = ImageDraw.Draw(scaled)

    # Draw tile boundaries
    for x in range(0, scaled.width, 32):
        draw.line([(x, 0), (x, scaled.height)], fill=(255, 0, 255, 128), width=1)
    for y in range(0, scaled.height, 32):
        draw.line([(0, y), (scaled.width, y)], fill=(255, 0, 255, 128), width=1)

    scaled.save(output_path)
    print(f"Created edit template: {output_path}")

def create_workflow_example():
    """Create a complete example of the sprite editing workflow."""

    print("=== Sprite Editing Workflow Demo ===\n")

    print("Step 1: Extract tiles and find Kirby sprites")
    print("  python3 find_kirby_sprites.py all_chars.png")
    print("  -> Creates individual Kirby sprites\n")

    print("Step 2: Choose a sprite to edit")
    print("  Available sprites:")
    print("  - kirby_kirby_stand_1.png (16x16 standing Kirby)")
    print("  - kirby_kirby_walk_1.png (16x16 walking Kirby)")
    print("  - kirby_kirby_beam_1.png (16x16 Kirby with ability)\n")

    print("Step 3: Edit the sprite")
    print("  IMPORTANT: Keep the image in indexed color mode!")
    print("  - Use an editor that preserves indexed color")
    print("  - Or edit in grayscale and convert back\n")

    print("Step 4: Split edited sprite back to tiles")
    print("  This will update the tileset with your changes\n")

    # Create an example edit
    try:
        # Load a Kirby sprite
        sprite = Image.open("kirby_kirby_stand_1.png")

        # Make a simple edit (add a dot to Kirby)
        edited = sprite.copy()
        pixels = edited.load()

        # Add a simple mark (if indexed mode)
        if edited.mode == 'P':
            # Find a non-background color
            used_colors = set()
            for y in range(edited.height):
                for x in range(edited.width):
                    used_colors.add(pixels[x, y])

            # Use a visible color
            mark_color = max(used_colors) if used_colors else 1

            # Add a small mark
            if edited.width >= 8 and edited.height >= 8:
                pixels[6, 6] = mark_color
                pixels[7, 6] = mark_color
                pixels[6, 7] = mark_color
                pixels[7, 7] = mark_color

        edited.save("kirby_edited_example.png")
        print("Created example edited sprite: kirby_edited_example.png")

        # Create scaled versions for viewing
        original_scaled = sprite.resize((sprite.width * 8, sprite.height * 8), Image.NEAREST)
        edited_scaled = edited.resize((edited.width * 8, edited.height * 8), Image.NEAREST)

        # Create comparison image
        comparison = Image.new('RGBA', (original_scaled.width * 2 + 10, original_scaled.height), (64, 64, 64, 255))
        comparison.paste(original_scaled.convert('RGBA'), (0, 0))
        comparison.paste(edited_scaled.convert('RGBA'), (original_scaled.width + 10, 0))
        comparison.save("kirby_edit_comparison.png")
        print("Created comparison image: kirby_edit_comparison.png")

    except FileNotFoundError:
        print("Note: Run find_kirby_sprites.py first to extract sprites")

    print("\n=== Complete Workflow Commands ===")
    print("1. Extract: python3 find_kirby_sprites.py all_chars.png")
    print("2. Edit: (use image editor on kirby_*.png files)")
    print("3. Update tileset: python3 sprite_disassembler.py all_chars.png kirby_edited.png updated_chars.png")
    print("4. Convert to SNES: python3 png_to_snes.py updated_chars.png")
    print("5. Insert to VRAM: python3 update_vram_sprites.py")

if __name__ == "__main__":
    create_workflow_example()

    # Create edit templates for all extracted sprites
    import os
    for f in os.listdir('.'):
        if f.startswith('kirby_kirby_') and f.endswith('.png'):
            output = f.replace('.png', '_edit_template.png')
            add_edit_guides(f, output)