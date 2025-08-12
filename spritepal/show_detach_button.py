#!/usr/bin/env python3
"""
Show where the Detach Gallery button is located.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication, QMainWindow, QTabWidget

from ui.tabs.sprite_gallery_tab import SpriteGalleryTab


def main():
    app = QApplication.instance() or QApplication(sys.argv)

    # Create main window
    window = QMainWindow()
    window.setWindowTitle("Sprite Gallery Tab - Look for Detach Button")
    window.resize(1200, 800)

    # Create tab widget
    tabs = QTabWidget()
    window.setCentralWidget(tabs)

    # Add sprite gallery tab
    gallery_tab = SpriteGalleryTab()
    tabs.addTab(gallery_tab, "Sprite Gallery")

    # Show window
    window.show()

    def highlight_button():
        print("\n" + "="*70)
        print("🎯 FINDING THE DETACH GALLERY BUTTON")
        print("="*70)

        print("\n📍 LOCATION:")
        print("The 'Detach Gallery' button is in the TOOLBAR at the top of the")
        print("Sprite Gallery tab. It's the LAST button on the right side.")

        print("\n🔍 BUTTON DETAILS:")
        print("Label: 🗖 Detach Gallery")
        print("Tooltip: Open gallery in separate window (fixes stretching)")

        print("\n📋 TOOLBAR BUTTONS (left to right):")
        for i, action in enumerate(gallery_tab.toolbar.actions(), 1):
            if action.text():
                marker = " <-- THIS ONE!" if "Detach" in action.text() else ""
                print(f"  {i}. {action.text()}{marker}")

        print("\n💡 HOW TO USE:")
        print("1. Load a ROM in SpritePal")
        print("2. Go to the 'Sprite Gallery' tab")
        print("3. Click '🔍 Scan ROM' to find sprites")
        print("4. Click '🗖 Detach Gallery' to open in new window")
        print("   (This fixes the stretching issue!)")

        print("\n✨ The button is visible RIGHT NOW in the window above!")
        print("="*70)

    # Highlight after window is shown
    QTimer.singleShot(100, highlight_button)

    return app.exec()

if __name__ == "__main__":
    sys.exit(main())
