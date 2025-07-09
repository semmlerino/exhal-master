#!/usr/bin/env python3
"""
Launch script for the indexed pixel editor
Handles different environments and provides helpful error messages
"""

import os
import subprocess
import sys


def check_dependencies():
    """Check if all required dependencies are available"""
    print("Checking dependencies...")

    try:
        from PIL import Image
        print("✓ PIL (Pillow) available")
    except ImportError:
        print("✗ PIL (Pillow) not available. Install with: pip install Pillow")
        return False

    try:
        import numpy as np
        print("✓ NumPy available")
    except ImportError:
        print("✗ NumPy not available. Install with: pip install numpy")
        return False

    try:
        from PyQt6.QtWidgets import QApplication
        print("✓ PyQt6 available")
        return True
    except ImportError:
        print("✗ PyQt6 not available. Install with: pip install PyQt6")
        print("  Note: PyQt6 may not work in headless environments (like WSL without X11)")
        return False

def check_display():
    """Check if display is available for GUI applications"""
    if os.name == "nt":  # Windows
        return True

    # Check for X11 display
    if "DISPLAY" in os.environ:
        return True

    # Check for Wayland
    return "WAYLAND_DISPLAY" in os.environ

def run_headless_test():
    """Run headless tests of the pixel editor"""
    print("Running headless pixel editor tests...")

    # Test basic functionality
    if os.path.exists("test_pixel_editor_core.py"):
        result = subprocess.run([sys.executable, "test_pixel_editor_core.py"],
                              capture_output=True, text=True, check=False)
        print(result.stdout)
        if result.stderr:
            print("Errors:", result.stderr)
        return result.returncode == 0
    print("✗ test_pixel_editor_core.py not found")
    return False

def launch_gui():
    """Launch the GUI version of the pixel editor"""
    print("Launching GUI pixel editor...")

    if not check_display():
        print("✗ No display available. Cannot launch GUI.")
        print("  For WSL: Install and configure X11 server (like VcXsrv)")
        print("  Or use headless testing mode")
        return False

    try:
        from PyQt6.QtWidgets import QApplication

        from indexed_pixel_editor import IndexedPixelEditor

        app = QApplication(sys.argv)
        editor = IndexedPixelEditor()
        editor.show()
        return app.exec()
    except Exception as e:
        print(f"✗ Failed to launch GUI: {e}")
        return False

def show_usage():
    """Show usage information"""
    print("""
Indexed Pixel Editor for SNES Sprites

Usage:
  python launch_sprite_pixel_editor.py [options]

Options:
  --gui      Launch GUI version (default)
  --test     Run headless tests only
  --check    Check dependencies and environment
  --help     Show this help message

Examples:
  python launch_sprite_pixel_editor.py --gui
  python launch_sprite_pixel_editor.py --test
  python launch_sprite_pixel_editor.py --check

Files:
  indexed_pixel_editor.py     - Main GUI application
  test_pixel_editor_core.py   - Core functionality tests
  test_smiley_8x8.png        - Test sprite (8x8 pixels)
  test_kirby_16x16.png       - Test sprite (16x16 pixels)

Features:
  ✓ 4bpp indexed color editing
  ✓ SNES palette support (16 colors)
  ✓ Drawing tools (pencil, fill, color picker)
  ✓ Zoom and grid view
  ✓ Undo/redo functionality
  ✓ PNG import/export
""")

def main():
    """Main function"""
    args = sys.argv[1:]

    if "--help" in args or "-h" in args:
        show_usage()
        return 0

    if "--check" in args:
        print("=== Dependency Check ===")
        deps_ok = check_dependencies()
        display_ok = check_display()

        print(f"\nDependencies: {'✓' if deps_ok else '✗'}")
        print(f"Display: {'✓' if display_ok else '✗'}")

        if deps_ok and display_ok:
            print("✅ Ready to launch GUI")
        elif deps_ok:
            print("⚠ Can run headless tests only")
        else:
            print("❌ Missing dependencies")

        return 0 if deps_ok else 1

    if "--test" in args:
        print("=== Headless Test Mode ===")
        if not check_dependencies():
            return 1

        success = run_headless_test()
        return 0 if success else 1

    # Default: try to launch GUI
    print("=== GUI Launch Mode ===")
    if not check_dependencies():
        print("\nTrying headless test mode instead...")
        success = run_headless_test()
        return 0 if success else 1

    return launch_gui()

if __name__ == "__main__":
    sys.exit(main())
