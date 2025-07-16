#!/usr/bin/env python3
"""
Test the color picker functionality in the pixel editor
"""

import os
import subprocess
import sys


def test_color_picker():
    """Launch pixel editor with a test sprite to test color picker"""

    # Check if test sprites exist
    test_sprite = "test_sprites/test_sprite_blocks.png"
    test_palette = "test_sprites/test_sprite_blocks.pal.json"

    if not os.path.exists(test_sprite):
        print("Test sprites not found. Please run create_test_sprites.py first.")
        return 1

    print("Launching pixel editor with test sprite...")
    print("\nTo test the color picker:")
    print("1. Press 'I' to switch to the color picker tool")
    print("2. Click on any color in the sprite")
    print("3. The tool should automatically switch back to pencil mode")
    print("4. The picked color should be selected in the palette panel")
    print("\nAlso test:")
    print("- 'G' key toggles grid visibility (should be off by default)")
    print("- 'C' key toggles between grayscale and color mode")
    print("- 'P' key opens palette switcher (if multiple palettes)")
    print()

    # Launch the pixel editor with the test sprite
    cmd = [sys.executable, "launch_pixel_editor.py", test_sprite, "-p", test_palette]

    try:
        result = subprocess.run(
            cmd, check=False, cwd=os.path.dirname(os.path.abspath(__file__))
        )
        return result.returncode
    except Exception as e:
        print(f"Error launching pixel editor: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(test_color_picker())
