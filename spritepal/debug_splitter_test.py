#!/usr/bin/env python3
"""Debug script to understand splitter hierarchy in RowArrangementDialog"""

import sys
import tempfile
from PIL import Image

from PyQt6.QtWidgets import QApplication
from ui.row_arrangement_dialog import RowArrangementDialog


def main():
    app = QApplication(sys.argv)
    
    # Create a test image
    test_image = Image.new("L", (128, 128), 0)
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as temp_file:
        test_image.save(temp_file.name)
        temp_path = temp_file.name
    
    # Create dialog
    dialog = RowArrangementDialog(temp_path)
    
    # Debug output
    print("=== RowArrangementDialog Splitter Structure ===")
    print(f"main_splitter: {dialog.main_splitter}")
    print(f"main_splitter type: {type(dialog.main_splitter)}")
    if dialog.main_splitter:
        print(f"main_splitter orientation: {dialog.main_splitter.orientation()}")
        print(f"main_splitter count: {dialog.main_splitter.count()}")
        for i in range(dialog.main_splitter.count()):
            widget = dialog.main_splitter.widget(i)
            print(f"  Widget {i}: {widget} (type: {type(widget).__name__})")
    
    # Check main_layout
    print(f"\nmain_layout: {dialog.main_layout}")
    print(f"main_layout count: {dialog.main_layout.count()}")
    for i in range(dialog.main_layout.count()):
        item = dialog.main_layout.itemAt(i)
        widget = item.widget() if item else None
        print(f"  Item {i}: {widget} (type: {type(widget).__name__ if widget else 'None'})")
    
    # Clean up
    import os
    os.unlink(temp_path)


if __name__ == "__main__":
    main()