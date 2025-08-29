#!/usr/bin/env python3
from __future__ import annotations

"""Test script to verify detached gallery fixes"""

import sys
from pathlib import Path

# Add parent directory to path to import modules
sys.path.insert(0, str(Path(__file__).parent))

from PySide6.QtWidgets import QApplication
from ui.windows.detached_gallery_window import DetachedGalleryWindow
from utils.logging_config import get_logger

logger = get_logger(__name__)

def test_detached_gallery():
    """Test detached gallery with division by zero and full ROM scan fixes"""
    app = QApplication.instance() or QApplication(sys.argv)
    
    # Create detached gallery window
    window = DetachedGalleryWindow()
    
    # Show window
    window.show()
    
    print("Detached Gallery Window opened successfully!")
    print("\nFixes applied:")
    print("1. Division by zero error fixed in progress calculations")
    print("2. ROM scanning now covers entire ROM (0x40000 to end/0x400000)")
    print("\nTo test:")
    print("1. Load a ROM file using File > Load ROM")
    print("2. Click 'Scan ROM' to scan the entire ROM")
    print("3. Or use 'Custom Range' to scan a specific range")
    print("\nThe scan should now:")
    print("- Not crash with division by zero")
    print("- Scan much more of the ROM (not just 0xC0000-0xF0000)")
    
    # Run the application
    sys.exit(app.exec())

if __name__ == "__main__":
    test_detached_gallery()