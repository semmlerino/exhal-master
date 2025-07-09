#!/usr/bin/env python3
"""
Complete Kirby Sprite Editing Workflow
Demonstrates the full extraction -> edit -> injection process

Usage:
    python sprite_workflow.py <command> [options]

Commands:
    extract   - Extract sprites from VRAM for editing
    inject    - Inject edited sprites back into VRAM
    quick     - Quick inject with default settings
"""

import os
import subprocess
import sys


def run_command(cmd):
    """Run a command and print output."""
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, check=False, capture_output=True, text=True)
    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print(result.stderr)
    return result.returncode == 0


def extract_sprites():
    """Extract sprites for editing."""
    print("EXTRACTING SPRITES FOR EDITING")
    print("=" * 50)

    # Extract with grayscale
    cmd = [
        "python3",
        "sprite_extractor.py",
        "--offset",
        "0xC000",
        "--size",
        "0x4000",
        "--output",
        "sprites_to_edit.png",
    ]

    if run_command(cmd):
        print("\n✅ Sprites extracted to: sprites_to_edit.png")
        print("\nNEXT STEPS:")
        print("1. Open sprites_to_edit.png in your image editor")
        print("2. IMPORTANT: Keep it in indexed color mode!")
        print("3. Edit using only the existing palette colors")
        print("4. Save as PNG (indexed color)")
        print("5. Run: python sprite_workflow.py inject <your_edited.png>")

    # Also extract with color for reference
    print("\nExtracting colored reference...")
    cmd_color = cmd[:]
    cmd_color[-1] = "sprites_reference_colored.png"
    cmd_color.extend(["--palette", "8"])
    if run_command(cmd_color):
        print("✅ Color reference saved to: sprites_reference_colored.png")


def inject_sprites(png_file):
    """Inject edited sprites back into VRAM."""
    print("INJECTING EDITED SPRITES")
    print("=" * 50)

    if not os.path.exists(png_file):
        print(f"Error: File '{png_file}' not found")
        return False

    # Create output filename
    base_name = os.path.splitext(os.path.basename(png_file))[0]
    output_vram = f"VRAM_{base_name}.dmp"

    cmd = [
        "python3",
        "sprite_injector.py",
        png_file,
        "--output",
        output_vram,
        "--preview",
    ]

    if run_command(cmd):
        print(f"\n✅ SUCCESS! Modified VRAM saved to: {output_vram}")
        print(f"\nYou can now load '{output_vram}' in your emulator!")
    return None


def quick_inject(png_file):
    """Quick injection with minimal output."""
    if not os.path.exists(png_file):
        print(f"Error: File '{png_file}' not found")
        return

    cmd = ["python3", "sprite_injector.py", png_file]
    subprocess.run(cmd, check=False)


def show_help():
    """Show help message."""
    help_text = """
Kirby Sprite Editing Workflow
=============================

This tool automates sprite extraction and injection for Kirby Super Star.

COMMANDS:
    extract              Extract sprites from VRAM for editing
    inject <file.png>    Inject edited PNG back into VRAM
    quick <file.png>     Quick inject with default settings

FULL WORKFLOW:
    1. python sprite_workflow.py extract
       -> Creates sprites_to_edit.png

    2. Edit sprites_to_edit.png in your image editor
       -> MUST keep indexed color mode!
       -> Use only existing palette colors

    3. python sprite_workflow.py inject edited_sprites.png
       -> Creates VRAM_edited_sprites.dmp

    4. Load the .dmp file in your emulator

EXAMPLES:
    python sprite_workflow.py extract
    python sprite_workflow.py inject my_edit.png
    python sprite_workflow.py quick editedIndexed.png

IMPORTANT NOTES:
    - Always maintain indexed color mode when editing
    - Sprites are at VRAM $6000 (file offset 0xC000)
    - Default extraction size is 16KB (512 tiles)
"""
    print(help_text)


def main():
    if len(sys.argv) < 2:
        show_help()
        return

    command = sys.argv[1].lower()

    if command == "extract":
        extract_sprites()
    elif command == "inject":
        if len(sys.argv) < 3:
            print("Error: Please specify PNG file to inject")
            print("Usage: python sprite_workflow.py inject <file.png>")
        else:
            inject_sprites(sys.argv[2])
    elif command == "quick":
        if len(sys.argv) < 3:
            print("Error: Please specify PNG file")
        else:
            quick_inject(sys.argv[2])
    elif command in ["help", "-h", "--help"]:
        show_help()
    else:
        print(f"Unknown command: {command}")
        show_help()


if __name__ == "__main__":
    main()
