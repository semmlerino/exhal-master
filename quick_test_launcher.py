#!/usr/bin/env python3
"""
Quick launcher for testing the enhanced sprite editing workflow
Provides an easy way to test different sprite sheets and palettes
"""

import os
import sys
from pathlib import Path


def show_available_tests():
    """Show all available test files"""
    print("🎨 Available Test Sprite Sheets:")
    print("=" * 50)

    # Find all .png files with companion .pal.json files
    test_files = []

    for png_file in Path().glob("*.png"):
        if "test" in png_file.name.lower() or "kirby" in png_file.name.lower():
            pal_file = png_file.with_suffix(".pal.json")
            if pal_file.exists():
                # Get file size
                size_kb = png_file.stat().st_size / 1024
                test_files.append({
                    "png": str(png_file),
                    "pal": str(pal_file),
                    "size": f"{size_kb:.1f}KB"
                })

    if not test_files:
        print("❌ No test files found. Run create_test_sprite_sheets.py first!")
        return False

    for i, test in enumerate(test_files, 1):
        name = test["png"].replace(".png", "").replace("_", " ").title()
        print(f"{i:2d}. {name}")
        print(f"    📁 Image: {test['png']} ({test['size']})")
        print(f"    🎨 Palette: {test['pal']}")
        print()

    return test_files

def show_standalone_palettes():
    """Show available standalone palette files"""
    print("🎨 Available Standalone Palettes:")
    print("=" * 40)

    pal_files = list(Path().glob("*.pal.json"))

    for i, pal_file in enumerate(pal_files, 1):
        name = pal_file.name.replace(".pal.json", "").replace("_", " ").title()
        print(f"{i:2d}. {name}")
        print(f"    🎨 {pal_file.name}")

    print()

def launch_editor_with_instructions():
    """Launch the editor with helpful instructions"""
    print("🚀 Launching Enhanced Indexed Pixel Editor...")
    print("=" * 50)
    print()
    print("📋 Testing Instructions:")
    print("1. Load any test image file (File → Open)")
    print("2. Editor will auto-detect companion palette and offer to load it")
    print("3. Click 'Yes' to load the palette")
    print("4. Look for green border around palette = external palette loaded")
    print("5. Toggle 'Greyscale Mode' checkbox:")
    print("   ☑️ ON  = See index values (0-15) as grayscale")
    print("   ☐ OFF = See game-accurate colors using external palette")
    print("6. Try editing pixels and watch color preview update!")
    print("7. Test different palettes: File → Load Palette File...")
    print()
    print("🎯 What to Look For:")
    print("• Green border on palette widget = external palette active")
    print("• Window title shows palette name")
    print("• Color preview shows game-accurate colors")
    print("• Smooth switching between greyscale and color modes")
    print("• Settings remember recent files and palette associations")
    print()

    # Launch the editor
    import subprocess
    try:
        subprocess.run([sys.executable, "indexed_pixel_editor.py"], check=False)
    except KeyboardInterrupt:
        print("\n✅ Editor closed")
    except Exception as e:
        print(f"❌ Error launching editor: {e}")
        print("Try: python3 indexed_pixel_editor.py")

def create_quick_test_script():
    """Create a simple test script for immediate testing"""
    test_script = '''#!/usr/bin/env python3
"""Quick test of palette workflow"""

import os
import subprocess
import sys

def quick_test():
    """Run a quick test of the enhanced workflow"""

    print("🧪 Quick Enhanced Workflow Test")
    print("=" * 40)

    # Check if test files exist
    test_files = [
        'tiny_test.png',
        'tiny_test.pal.json'
    ]

    missing = [f for f in test_files if not os.path.exists(f)]
    if missing:
        print(f"❌ Missing files: {missing}")
        print("Run: python3 create_test_sprite_sheets.py")
        return False

    print("✅ Test files found")
    print("🚀 Launching editor...")
    print()
    print("📋 Test Steps:")
    print("1. Open 'tiny_test.png'")
    print("2. Accept palette loading when prompted")
    print("3. Toggle greyscale mode on/off")
    print("4. Edit some pixels")
    print("5. See color preview change!")
    print()

    try:
        subprocess.run([sys.executable, 'indexed_pixel_editor.py'])
        return True
    except:
        print("❌ Launch failed. Try: python3 indexed_pixel_editor.py")
        return False

if __name__ == "__main__":
    quick_test()
'''

    with open("quick_test.py", "w") as f:
        f.write(test_script)

    os.chmod("quick_test.py", 0o755)
    print("✅ Created quick_test.py for immediate testing")

def main():
    """Main launcher interface"""
    print("🎨 Enhanced Sprite Editing Workflow - Test Launcher")
    print("=" * 60)
    print()

    # Check if editor exists
    if not os.path.exists("indexed_pixel_editor.py"):
        print("❌ indexed_pixel_editor.py not found!")
        return

    # Show available test files
    test_files = show_available_tests()
    if not test_files:
        print("Run: python3 create_test_sprite_sheets.py")
        return

    # Show standalone palettes
    show_standalone_palettes()

    # Create quick test script
    create_quick_test_script()

    print("🚀 Choose how to test:")
    print("1. Launch editor with instructions (recommended)")
    print("2. Run quick automated test")
    print("3. Just show file list")
    print("4. Exit")
    print()

    try:
        choice = input("Enter choice (1-4): ").strip()

        if choice == "1":
            launch_editor_with_instructions()
        elif choice == "2":
            os.system(f"{sys.executable} quick_test.py")
        elif choice == "3":
            print("✅ File list shown above")
        elif choice == "4":
            print("👋 Goodbye!")
        else:
            print("❌ Invalid choice")

    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()
