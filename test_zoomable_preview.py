#!/usr/bin/env python3
"""
Test the zoomable preview functionality in SpritePal
"""

import sys
import os
from PyQt6.QtWidgets import QApplication, QVBoxLayout, QWidget
from PyQt6.QtGui import QPixmap

# Add SpritePal to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from spritepal.ui.zoomable_preview import PreviewPanel


def test_zoomable_preview():
    """Test the zoomable preview widget"""
    app = QApplication(sys.argv)
    
    # Create test window
    window = QWidget()
    window.setWindowTitle("Zoomable Preview Test")
    window.resize(600, 500)
    
    layout = QVBoxLayout(window)
    
    # Create preview panel
    preview_panel = PreviewPanel()
    layout.addWidget(preview_panel)
    
    # Load test sprite if available
    test_files = [
        "test_sprites.png",
        "cave_sprites_editor.png",
        "kirby_sprites_grayscale.png"
    ]
    
    for test_file in test_files:
        if os.path.exists(test_file):
            print(f"Loading {test_file}...")
            pixmap = QPixmap(test_file)
            if not pixmap.isNull():
                preview_panel.set_preview(pixmap)
                print(f"✓ Loaded {test_file}")
                print(f"  Size: {pixmap.width()}x{pixmap.height()}")
                print()
                print("Controls:")
                print("  - Mouse wheel: Zoom in/out")
                print("  - Click and drag: Pan around")
                print("  - Right-click: Reset to 1:1")
                print("  - 'Fit' button: Fit to window")
                print("  - '1:1' button: Reset zoom")
                break
    else:
        print("No test sprite files found!")
        print("Please run test_spritepal_core.py first to generate test_sprites.png")
        return
    
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    test_zoomable_preview()