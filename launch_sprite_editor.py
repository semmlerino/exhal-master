#!/usr/bin/env python3
"""
Launcher for the unified Kirby Super Star Sprite Editor
Checks dependencies and launches the main application
"""

import subprocess
import sys


def check_dependencies():
    """Check if required dependencies are installed"""
    missing = []

    # Check Python version

    # Check required packages
    try:
        import PyQt6
    except ImportError:
        missing.append("PyQt6")

    try:
        from PIL import Image
    except ImportError:
        missing.append("Pillow")

    if missing:
        print("Missing required packages:")
        for pkg in missing:
            print(f"  - {pkg}")
        print("\nInstall with:")
        print(f"  pip install {' '.join(missing)}")

        response = input("\nWould you like to install them now? (y/n): ")
        if response.lower() == "y":
            for pkg in missing:
                print(f"\nInstalling {pkg}...")
                subprocess.check_call([sys.executable, "-m", "pip", "install", pkg])
            print("\nDependencies installed! Launching editor...")
            return True
        return False

    return True

def main():
    """Main launcher"""
    print("Kirby Super Star Sprite Editor Launcher")
    print("=" * 40)

    # Check dependencies
    if not check_dependencies():
        print("\nPlease install required dependencies and try again.")
        return 1

    # Launch the unified editor
    try:
        # Try PyQt6 version first
        from sprite_editor_unified import main as run_unified
        print("\nLaunching unified sprite editor...")
        run_unified()
    except ImportError as e:
        print(f"\nError: Could not import unified editor: {e}")
        print("\nTrying alternative launch methods...")

        # Try running as subprocess
        try:
            subprocess.run([sys.executable, "sprite_editor_unified.py"], check=False)
        except Exception as e2:
            print(f"\nFailed to launch: {e2}")

            # Fallback to simple command-line interface
            print("\nFalling back to command-line tools:")
            print("\nAvailable tools:")
            print("  python3 sprite_edit_workflow.py --help")
            print("  python3 sprite_sheet_editor.py --help")
            print("  python3 demo_edit_and_reinsert.py")
            return 1

    return 0

if __name__ == "__main__":
    sys.exit(main())
