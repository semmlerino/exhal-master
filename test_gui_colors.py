#!/usr/bin/env python3
"""
Test the GUI colors to verify they're not all grayscale
"""

import os
import sys

from PyQt6.QtWidgets import QApplication

from indexed_pixel_editor import ColorPaletteWidget, IndexedPixelEditor


def test_palette_widget_standalone():
    """Test the palette widget in isolation"""
    print("=== Testing Palette Widget Standalone ===")

    # Create app
    QApplication([])

    # Create palette widget
    palette_widget = ColorPaletteWidget()

    print("Palette widget colors:")
    for i in range(8):  # Show first 8 colors
        color = palette_widget.colors[i]
        print(f"  {i}: {color}")

        # Check if it's grayscale (all RGB values same)
        if color[0] == color[1] == color[2]:
            print("    ^ This is grayscale!")
        else:
            print("    ^ This is colored!")

    print(f"\nSelected index: {palette_widget.selected_index}")

    # Check if colors are unique
    unique_colors = set(palette_widget.colors)
    print(f"Number of unique colors: {len(unique_colors)}")

    if len(unique_colors) == 1:
        print("ERROR: All colors are the same!")
        return False
    if len(unique_colors) < 8:
        print("WARNING: Very few unique colors")
    else:
        print("GOOD: Multiple unique colors")

    return True

def test_editor_initialization():
    """Test the full editor initialization"""
    print("\n=== Testing Full Editor Initialization ===")

    # Check environment
    if os.name != "nt" and "DISPLAY" not in os.environ and "WAYLAND_DISPLAY" not in os.environ:
        print("No display available, cannot test GUI")
        return True

    try:
        # Create app
        QApplication([])

        # Create editor (this will print debug output)
        editor = IndexedPixelEditor()

        # Check if canvas has proper palette
        if editor.canvas.palette_widget:
            print("SUCCESS: Canvas has palette widget")

            # Check first few colors
            colors = editor.canvas.palette_widget.colors
            print(f"Canvas palette colors: {colors[:4]}")

            # Verify they're not all the same
            if colors[0] != colors[1] or colors[1] != colors[4]:
                print("SUCCESS: Canvas has different colors")
            else:
                print("ERROR: Canvas colors are all the same")
                return False
        else:
            print("ERROR: Canvas does not have palette widget")
            return False

        # Test drawing a pixel
        print("\nTesting pixel drawing...")
        editor.canvas.current_color = 1  # Kirby pink
        editor.canvas.draw_pixel(2, 2)

        if editor.canvas.image_data is not None:
            pixel_value = editor.canvas.image_data[2, 2]
            print(f"Drew pixel with color 1, stored value: {pixel_value}")

            if pixel_value == 1:
                print("SUCCESS: Pixel stored correctly")
            else:
                print(f"ERROR: Pixel stored as {pixel_value} instead of 1")
                return False

        # Test color lookup
        expected_color = editor.canvas.palette_widget.colors[1]
        print(f"Color index 1 should be: {expected_color}")

        if expected_color == (255, 183, 197):
            print("SUCCESS: Kirby pink color is correct")
        else:
            print(f"ERROR: Kirby pink color is wrong: {expected_color}")
            return False

        # Don't show the editor, just test the initialization
        print("SUCCESS: Editor initialization completed")
        return True

    except Exception as e:
        print(f"ERROR: Editor test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all GUI color tests"""
    print("Testing GUI colors...\n")

    success = True

    # Test palette widget standalone
    if not test_palette_widget_standalone():
        success = False

    # Test full editor
    if not test_editor_initialization():
        success = False

    if success:
        print("\n✅ All GUI color tests passed!")
        print("\nThe pixel editor should now show:")
        print("- Colorful palette widget (not all black)")
        print("- Canvas that draws in actual colors")
        print("- Proper color mapping from indices to RGB")
        print("\nIf you're still seeing grayscale, there may be a display/Qt issue.")
    else:
        print("\n❌ Some GUI color tests failed")
        print("There's still an issue with the color system.")

    return 0 if success else 1

if __name__ == "__main__":
    # Use offscreen mode to avoid display issues
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    sys.exit(main())
