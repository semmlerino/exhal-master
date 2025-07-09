#!/usr/bin/env python3
"""
Quick test script to verify palette loading works correctly
"""

import os
import sys

from PyQt6.QtWidgets import QApplication


def test_palette_loading():
    """Test that palette loading doesn't crash"""

    print("🧪 Testing Palette Loading Fix...")

    # Check if we have test files
    if not os.path.exists("tiny_test.pal.json"):
        print("❌ No test palette file found. Run create_test_sprite_sheets.py first")
        return False

    try:
        # Import after ensuring we're in the right directory
        from indexed_pixel_editor import IndexedPixelEditor

        # Create QApplication
        QApplication(sys.argv)

        # Create editor (with startup disabled)
        editor = IndexedPixelEditor()

        # Test loading a palette file
        success = editor.load_palette_by_path("tiny_test.pal.json")

        if success:
            print("✅ Palette loading works!")
            print(f"✅ Loaded palette: {editor.current_palette_file}")
            print(f"✅ External palette colors: {len(editor.external_palette_colors)}")
            print(f"✅ Palette widget shows external: {editor.palette_widget.is_external_palette}")
            return True
        print("❌ Palette loading failed")
        return False

    except Exception as e:
        print(f"❌ Error testing palette loading: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_image_with_palette():
    """Test loading image and then palette"""

    print("\n🧪 Testing Image + Palette Loading...")

    if not all(os.path.exists(f) for f in ["tiny_test.png", "tiny_test.pal.json"]):
        print("❌ Test files not found")
        return False

    try:
        from indexed_pixel_editor import IndexedPixelEditor
        QApplication.instance() or QApplication(sys.argv)

        editor = IndexedPixelEditor()

        # Load image first
        print("📁 Loading image...")
        img_success = editor.load_file_by_path("tiny_test.png")

        if not img_success:
            print("❌ Failed to load image")
            return False

        print("✅ Image loaded")

        # Load palette
        print("🎨 Loading palette...")
        pal_success = editor.load_palette_by_path("tiny_test.pal.json")

        if not pal_success:
            print("❌ Failed to load palette")
            return False

        print("✅ Palette loaded")
        print(f"✅ Window title: {editor.windowTitle()}")

        return True

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🔧 Palette Loading Fix Test")
    print("=" * 30)

    test1 = test_palette_loading()
    test2 = test_image_with_palette()

    if test1 and test2:
        print("\n🎉 All tests passed! Palette loading is fixed.")
        print("\n🚀 Now you can safely run:")
        print("   python3 indexed_pixel_editor.py")
        print("   and load palette files without crashes!")
    else:
        print("\n❌ Some tests failed")

    # Don't show the GUI
    sys.exit(0)
