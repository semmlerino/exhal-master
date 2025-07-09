#!/usr/bin/env python3
"""
Quick launcher for the ultrathink sprite editor
"""

import os
import subprocess
import sys


def main():
    # Add parent directory to path
    parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.insert(0, parent_dir)

    # Default sprite sheet
    sprite_file = "sprites/kirby_sprites.png"

    print("🎨 ULTRATHINK Sprite Editor")
    print("=" * 40)
    print("\nAvailable options:")
    print("1. Edit with default palette (grayscale/color toggle)")
    print("2. Edit with pink Kirby palette")
    print("3. Edit with purple Kirby palette")
    print("\nPress Enter for default, or choose 1-3: ", end="")

    choice = input().strip()

    if choice in {"", "1"}:
        # Default - auto-detect palette
        cmd = ["python3", os.path.join(parent_dir, "indexed_pixel_editor.py"), sprite_file]
    elif choice == "2":
        # Pink Kirby
        cmd = ["python3", os.path.join(parent_dir, "indexed_pixel_editor.py"),
               sprite_file, "-p", "sprites/kirby_palette_14.pal.json"]
    elif choice == "3":
        # Purple Kirby
        cmd = ["python3", os.path.join(parent_dir, "indexed_pixel_editor.py"),
               sprite_file, "-p", "sprites/kirby_palette_8.pal.json"]
    else:
        print("Invalid choice")
        return

    print("\nLaunching editor...")
    print("Remember: Press 'C' to toggle color mode!")

    # Launch editor
    subprocess.run(cmd, check=False)

if __name__ == "__main__":
    main()
