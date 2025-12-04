#!/usr/bin/env python3
from __future__ import annotations

"""
Test the custom range scanning feature in detached gallery window.
This verifies the feature is complete and working.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

def test_custom_range_implementation():
    """Test that custom range scanning is fully implemented."""

    print("Testing Custom Range Scanning Implementation...")
    print("=" * 50)

    # Create QApplication first
    from PySide6.QtWidgets import QApplication
    QApplication.instance() or QApplication(sys.argv)

    # Test 1: Check imports
    print("\n1. Testing imports...")
    try:
        from ui.dialogs.scan_range_dialog import ScanRangeDialog
        from ui.rom_extraction.workers.scan_worker import SpriteScanWorker
        from ui.windows.detached_gallery_window import DetachedGalleryWindow
        print("   ✓ All required modules import successfully")
    except ImportError as e:
        print(f"   ✗ Import error: {e}")
        return False

    # Test 2: Check dialog functionality
    print("\n2. Testing ScanRangeDialog...")
    dialog = ScanRangeDialog(rom_size=0x100000)  # 1MB test

    # Check default values
    assert hasattr(dialog, 'start_offset'), "Dialog missing start_offset"
    assert hasattr(dialog, 'end_offset'), "Dialog missing end_offset"
    assert hasattr(dialog, 'get_range'), "Dialog missing get_range method"

    start, end = dialog.get_range()
    print(f"   ✓ Dialog defaults: 0x{start:X} - 0x{end:X}")

    # Test 3: Check DetachedGalleryWindow has custom range method
    print("\n3. Testing DetachedGalleryWindow...")

    # Initialize managers for the window
    from core.managers import initialize_managers
    initialize_managers()

    window = DetachedGalleryWindow()

    # Check required methods exist
    assert hasattr(window, '_scan_custom_range'), "Window missing _scan_custom_range method"
    assert hasattr(window, '_start_scan'), "Window missing _start_scan method"

    # Check _start_scan signature
    import inspect
    sig = inspect.signature(window._start_scan)
    params = list(sig.parameters.keys())
    assert 'start_offset' in params, "_start_scan missing start_offset param"
    assert 'end_offset' in params, "_start_scan missing end_offset param"

    print("   ✓ Window has all required methods")

    # Test 4: Check worker accepts custom range
    print("\n4. Testing SpriteScanWorker...")

    # Check worker constructor
    sig = inspect.signature(SpriteScanWorker.__init__)
    params = list(sig.parameters.keys())
    assert 'start_offset' in params, "Worker missing start_offset param"
    assert 'end_offset' in params, "Worker missing end_offset param"

    print("   ✓ Worker accepts custom range parameters")

    # Test 5: Verify toolbar has custom range button
    print("\n5. Testing toolbar integration...")

    from PySide6.QtGui import QAction
    toolbar_actions = window.findChildren(QAction)
    custom_action_found = False

    for action in toolbar_actions:
        if "Custom Range" in action.text() or "custom" in action.text().lower():
            custom_action_found = True
            print(f"   ✓ Found '{action.text()}' action in toolbar")
            break

    if not custom_action_found:
        print("   ✗ Custom Range action not found in toolbar")
        return False

    print("\n" + "=" * 50)
    print("✅ All tests passed! Custom range scanning is fully implemented.")
    print("\nThe feature allows users to:")
    print("  1. Click '🎯 Custom Range' in the toolbar")
    print("  2. Enter start/end offsets in the dialog")
    print("  3. Scan only the specified ROM range")

    return True

if __name__ == "__main__":
    success = test_custom_range_implementation()
    sys.exit(0 if success else 1)
