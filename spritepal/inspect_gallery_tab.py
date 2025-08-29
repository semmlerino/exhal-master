#!/usr/bin/env python3
from __future__ import annotations

"""
Script to inspect the Gallery tab widget and its contents.
"""

import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget

# Add parent directory to path to import SpritePal modules
sys.path.insert(0, str(Path(__file__).parent))

from ui.tabs.sprite_gallery_tab import SpriteGalleryTab
from utils.logging_config import get_logger

logger = get_logger(__name__)

def inspect_gallery_tab():
    """Create and inspect the Gallery tab widget."""
    app = QApplication.instance() or QApplication(sys.argv)

    # Create main window to hold the gallery tab
    window = QMainWindow()
    window.setWindowTitle("Gallery Tab Inspector")
    window.resize(800, 600)

    # Create central widget with layout
    central = QWidget()
    layout = QVBoxLayout(central)

    # Create gallery tab
    gallery_tab = SpriteGalleryTab()
    layout.addWidget(gallery_tab)

    window.setCentralWidget(central)

    # Print information about the gallery tab
    print("\n=== Gallery Tab Structure ===")
    print(f"Gallery Tab Type: {type(gallery_tab).__name__}")

    # Check what widgets are in the gallery tab
    children = gallery_tab.findChildren(QWidget)
    print(f"Number of child widgets: {len(children)}")

    for i, child in enumerate(children[:10]):  # Show first 10 children
        print(f"  {i+1}. {type(child).__name__}: {child.objectName() or '(unnamed)'}")

    # Check layout
    layout = gallery_tab.layout()
    if layout:
        print(f"Layout type: {type(layout).__name__}")
        print(f"Layout item count: {layout.count()}")

        # Show items in layout
        for i in range(min(5, layout.count())):
            item = layout.itemAt(i)
            if item and item.widget():
                widget = item.widget()
                print(f"  Layout item {i}: {type(widget).__name__} - {widget.objectName() or '(unnamed)'}")

    # Check for specific gallery components
    print("\n=== Checking for Gallery Components ===")

    # Look for gallery viewer
    from ui.widgets.sprite_gallery_widget import SpriteGalleryWidget
    viewers = gallery_tab.findChildren(SpriteGalleryWidget)
    if viewers:
        print(f"Found SpriteGalleryWidget: {viewers[0]}")
    else:
        print("No SpriteGalleryWidget found")

    # Look for scroll area
    from PySide6.QtWidgets import QScrollArea
    scroll_areas = gallery_tab.findChildren(QScrollArea)
    if scroll_areas:
        print(f"Found {len(scroll_areas)} QScrollArea(s)")

    # Look for labels
    from PySide6.QtWidgets import QLabel
    labels = gallery_tab.findChildren(QLabel)
    if labels:
        print(f"Found {len(labels)} QLabel(s)")
        for label in labels[:3]:
            text = label.text()[:50] if label.text() else "(no text)"
            print(f"  - {text}")

    window.show()

    # Print final status
    print("\n=== Gallery Tab Status ===")
    print(f"Visible: {gallery_tab.isVisible()}")
    print(f"Size: {gallery_tab.size().width()}x{gallery_tab.size().height()}")

    sys.exit(app.exec())

if __name__ == "__main__":
    inspect_gallery_tab()
