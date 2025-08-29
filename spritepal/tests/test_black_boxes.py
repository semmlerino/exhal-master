
from __future__ import annotations

import pytest

pytestmark = [
    pytest.mark.gui,
    pytest.mark.requires_display,
    pytest.mark.rom_data,
]
#!/usr/bin/env python3
"""
Test why we're seeing black boxes in the preview.
"""

import sys
import os
import logging

# Add the parent directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Set up detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s.%(msecs)03d - %(name)s - %(levelname)s - %(message)s',
    datefmt='%H:%M:%S'
)

from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout
from PySide6.QtCore import QTimer
from core.managers.registry import initialize_managers, get_extraction_manager
from ui.widgets.sprite_preview_widget import SpritePreviewWidget

def test_preview_widget():
    """Test the preview widget directly with raw tile data."""
    
    # Initialize managers
    print("Initializing managers...")
    initialize_managers()
    
    # Create a simple window
    window = QWidget()
    window.setWindowTitle("Test Preview Widget")
    layout = QVBoxLayout()
    window.setLayout(layout)
    
    # Create preview widget
    print("Creating preview widget...")
    preview_widget = SpritePreviewWidget("Test Preview")
    layout.addWidget(preview_widget)
    
    # Show window
    window.show()
    
    # Load test ROM data
    test_rom = "Kirby Super Star (USA).sfc"
    if os.path.exists(test_rom):
        print(f"Loading ROM: {test_rom}")
        
        # Read raw tile data from a known good offset
        with open(test_rom, "rb") as f:
            f.seek(0x250000)  # Known offset with sprite data
            tile_data = f.read(4096)  # Read 4KB of raw tile data
        
        print(f"Read {len(tile_data)} bytes of tile data")
        print(f"First 20 bytes (hex): {tile_data[:20].hex()}")
        
        # Load into preview widget
        print("Loading tile data into preview widget...")
        preview_widget.load_sprite_from_4bpp(
            tile_data,
            128,  # width
            64,   # height
            "manual_0x250000"
        )
        
        # Check if preview is showing
        QTimer.singleShot(1000, lambda: check_preview(preview_widget))
        
    else:
        print("ERROR: Test ROM not found!")
        return
    
    return window

def check_preview(widget):
    """Check if the preview is displaying correctly."""
    print("\n=== PREVIEW CHECK ===")
    
    # Check if pixmap exists
    label = widget.preview_label
    pixmap = label.pixmap()
    
    if pixmap:
        print(f"Pixmap exists: {pixmap.width()}x{pixmap.height()}")
        print(f"Pixmap is null: {pixmap.isNull()}")
        
        # Check if it's all black
        image = pixmap.toImage()
        all_black = True
        for y in range(min(10, image.height())):
            for x in range(min(10, image.width())):
                color = image.pixelColor(x, y)
                if color.red() > 0 or color.green() > 0 or color.blue() > 0:
                    all_black = False
                    break
            if not all_black:
                break
        
        if all_black:
            print("WARNING: Pixmap appears to be all black!")
        else:
            print("SUCCESS: Pixmap contains non-black pixels")
    else:
        print("ERROR: No pixmap set on label")
    
    # Check sprite data
    if hasattr(widget, 'sprite_data') and widget.sprite_data:
        print(f"Sprite data exists: {len(widget.sprite_data)} bytes")
        # Check if data is all zeros
        non_zero = sum(1 for b in widget.sprite_data[:100] if b != 0)
        print(f"Non-zero bytes in first 100: {non_zero}")
    else:
        print("ERROR: No sprite data stored")
    
    print("===================")

def main():
    app = QApplication(sys.argv)
    
    window = test_preview_widget()
    
    # Auto-close after 3 seconds
    QTimer.singleShot(3000, app.quit)
    
    return app.exec()

if __name__ == "__main__":
    sys.exit(main())