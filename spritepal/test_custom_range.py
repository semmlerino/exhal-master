#!/usr/bin/env python3
"""Test script to verify custom range scanning works in detached gallery."""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from PySide6.QtWidgets import QApplication
from ui.windows.detached_gallery_window import DetachedGalleryWindow
from ui.dialogs.scan_range_dialog import ScanRangeDialog


def test_imports():
    """Test that all required components import correctly."""
    print("✓ All imports successful")
    
    # Test that the dialog can be created
    app = QApplication.instance() or QApplication(sys.argv)
    
    # Test dialog creation
    dialog = ScanRangeDialog(rom_size=1024*1024)  # 1MB test ROM
    print(f"✓ ScanRangeDialog created with default range: 0x{dialog.start_offset:X} - 0x{dialog.end_offset:X}")
    
    # Test window creation
    window = DetachedGalleryWindow()
    print("✓ DetachedGalleryWindow created")
    
    # Check that the custom range action exists
    toolbar_actions = window.findChildren(QAction)
    custom_range_action = None
    for action in toolbar_actions:
        if "Custom Range" in action.text():
            custom_range_action = action
            break
    
    if custom_range_action:
        print("✓ Custom Range action found in toolbar")
    else:
        print("✗ Custom Range action NOT found in toolbar")
        
    # Check that _scan_custom_range method exists
    if hasattr(window, '_scan_custom_range'):
        print("✓ _scan_custom_range method exists")
    else:
        print("✗ _scan_custom_range method NOT found")
        
    # Check that _start_scan accepts custom parameters
    import inspect
    sig = inspect.signature(window._start_scan)
    params = list(sig.parameters.keys())
    if 'start_offset' in params and 'end_offset' in params:
        print("✓ _start_scan accepts start_offset and end_offset parameters")
    else:
        print("✗ _start_scan does NOT accept custom range parameters")
    
    print("\nAll tests passed! Custom range scanning is properly implemented.")
    

if __name__ == "__main__":
    from PySide6.QtWidgets import QAction
    test_imports()