#!/usr/bin/env python3
"""
Launch the indexed pixel editor with sprite files ready to load
This script helps with quick testing of the enhanced zoom functionality
"""

import os
import sys

from PIL import Image
from PyQt6.QtWidgets import QApplication, QMessageBox

from pixel_editor.core.indexed_pixel_editor import IndexedPixelEditor


def main():
    app = QApplication(sys.argv)

    # Create editor
    editor = IndexedPixelEditor()

    # Check for sprite files and offer to load them
    sprite_files = [
        "kirby_visual_friendly_ultrathink.png",
        "kirby_editor_ready_ultrathink.png",
        "kirby_focused_4bpp_ultrathink.png",
    ]

    available_files = [f for f in sprite_files if os.path.exists(f)]

    if available_files:
        msg = QMessageBox()
        msg.setWindowTitle("Load Sprite File?")
        msg.setText("Sprite files found! Which would you like to load for testing?")

        # Add buttons for each available file
        buttons = {}
        for filename in available_files:
            # Get file size for display
            size = os.path.getsize(filename)
            button_text = f"{filename} ({size:,} bytes)"
            button = msg.addButton(button_text, QMessageBox.ButtonRole.ActionRole)
            buttons[button] = filename

        # Add cancel button
        msg.addButton("Manual Load", QMessageBox.ButtonRole.RejectRole)

        msg.exec()
        clicked = msg.clickedButton()

        if clicked in buttons:
            filename = buttons[clicked]
            print(f"Loading {filename}...")

            # Try to load the file
            try:
                img = Image.open(filename)
                if img.mode == "P":
                    editor.canvas.load_image(img)
                    editor.current_file = filename
                    editor.setWindowTitle(
                        f"Indexed Pixel Editor - {os.path.basename(filename)}"
                    )
                    print(f"✓ Loaded {filename} successfully!")
                    print(f"  Size: {img.size}")
                    print(f"  Mode: {img.mode} (indexed)")
                    print(
                        f"  Colors: {len(img.getpalette())//3 if img.palette else 'unknown'}"
                    )
                else:
                    QMessageBox.warning(
                        editor,
                        "Format Error",
                        f"File {filename} is not in indexed mode. Please use an indexed PNG.",
                    )
            except Exception as e:
                QMessageBox.critical(
                    editor, "Load Error", f"Failed to load {filename}:\\n{e!s}"
                )

    editor.show()

    # Print usage instructions
    print("")
    print("=== Enhanced Indexed Pixel Editor ===")
    print("")
    print("🖱️  Mouse Controls:")
    print("  • Mouse Wheel Up/Down = Zoom In/Out")
    print("  • Middle Mouse + Drag = Pan Around")
    print("  • Ctrl + Mouse Wheel = Scroll (when needed)")
    print("  • Left Click = Draw")
    print("")
    print("⌨️  Keyboard Shortcuts:")
    print("  • Ctrl++ / Ctrl+- = Zoom In/Out")
    print("  • Ctrl+0 = Reset to 4x Zoom")
    print("  • Ctrl+Shift+0 = Zoom to Fit")
    print("  • Ctrl+1,2,4,8 = Quick Zoom Presets")
    print("")
    print("🎯 Zoom Levels: 1x, 2x, 4x, 8x, 16x, 32x, 64x")
    print("📁 Load any of these files to test:")
    for f in sprite_files:
        if os.path.exists(f):
            print(f"  ✓ {f}")
        else:
            print(f"  ✗ {f} (not found)")
    print("")
    print("🐛 Debug output will show in this console")
    print("")

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
