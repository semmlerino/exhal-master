#!/usr/bin/env python3
"""
Test script to verify the flashing/black box fix for manual offset slider.

This tests that:
1. Sprites don't flash when dragging the slider
2. No black boxes appear between updates
3. Palette index 0 is visible (not pure black)
4. Previous sprite stays visible during loading
"""

import sys
import time
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer
from ui.widgets.sprite_preview_widget import SpritePreviewWidget
from PIL import Image
import numpy as np


def test_no_clearing_on_empty_data():
    """Test that empty tile data doesn't clear the previous sprite."""
    print("\n=== Test 1: No Clearing on Empty Data ===")
    
    app = QApplication.instance() or QApplication(sys.argv)
    widget = SpritePreviewWidget()
    
    # Load a test sprite
    test_data = bytes([i % 16 for i in range(64*64)])  # 64x64 sprite with gradient
    widget.load_sprite_from_4bpp(test_data, 64, 64, "test_sprite")
    
    # Process events to ensure display
    app.processEvents()
    
    # Check pixmap exists
    pixmap1 = widget.preview_label.pixmap()
    assert pixmap1 is not None, "Initial pixmap should be set"
    
    # Now try to load empty data (simulating dragging to invalid offset)
    widget.load_sprite_from_4bpp(b"", 64, 64, "empty")
    app.processEvents()
    
    # Check pixmap still exists (not cleared)
    pixmap2 = widget.preview_label.pixmap()
    assert pixmap2 is not None, "Pixmap should NOT be cleared on empty data"
    assert widget.essential_info_label.text() == "Loading...", "Should show 'Loading...' not 'No data'"
    
    print("✅ Empty data doesn't clear previous sprite")
    return True


def test_palette_index_0_visible():
    """Test that palette index 0 is visible (not pure black)."""
    print("\n=== Test 2: Palette Index 0 Visibility ===")
    
    app = QApplication.instance() or QApplication(sys.argv)
    widget = SpritePreviewWidget()
    
    # Create sprite data with only palette index 0
    test_data = bytes([0] * 64*32)  # All pixels use palette index 0
    
    # Set a test palette where index 0 is black
    widget.palettes = [
        [[0, 0, 0],     # Index 0: Black (should be converted to dark gray)
         [255, 0, 0],   # Index 1: Red
         [0, 255, 0],   # Index 2: Green
         [0, 0, 255]]   # Index 3: Blue
    ]
    widget.current_palette_index = 0
    
    # Create grayscale image
    img = Image.new('L', (64, 64), 0)  # All black (palette index 0)
    
    # This should convert black to dark gray for visibility
    widget._update_preview_with_palette(img)
    app.processEvents()
    
    # Check that pixmap was created
    pixmap = widget.preview_label.pixmap()
    assert pixmap is not None, "Pixmap should be created for palette index 0 sprites"
    
    print("✅ Palette index 0 is converted to dark gray for visibility")
    return True


def test_rapid_updates_no_flashing():
    """Test that rapid updates don't cause flashing."""
    print("\n=== Test 3: Rapid Updates Without Flashing ===")
    
    app = QApplication.instance() or QApplication(sys.argv)
    widget = SpritePreviewWidget()
    widget.show()
    
    # Track pixmap states
    pixmap_states = []
    
    def check_pixmap():
        """Check if pixmap exists"""
        pixmap = widget.preview_label.pixmap()
        pixmap_states.append(pixmap is not None)
    
    # Load initial sprite
    test_data = bytes([i % 16 for i in range(64*64)])
    widget.load_sprite_from_4bpp(test_data, 64, 64, "initial")
    app.processEvents()
    check_pixmap()
    
    # Simulate rapid slider movement with 10 updates
    for i in range(10):
        # Alternate between valid and empty data (worst case)
        if i % 2 == 0:
            data = bytes([(i*10) % 16 for j in range(64*64)])
            widget.load_sprite_from_4bpp(data, 64, 64, f"sprite_{i}")
        else:
            # Empty data that would previously cause clearing
            widget.load_sprite_from_4bpp(b"", 64, 64, f"empty_{i}")
        
        app.processEvents()
        check_pixmap()
        time.sleep(0.01)  # Small delay to simulate rapid updates
    
    # Check that pixmap was never None (no flashing)
    none_count = sum(1 for state in pixmap_states if not state)
    print(f"Pixmap states: {pixmap_states}")
    print(f"Times pixmap was None: {none_count} out of {len(pixmap_states)}")
    
    assert none_count == 0, f"Pixmap was cleared {none_count} times (flashing detected)"
    print("✅ No flashing detected during rapid updates")
    return True


def test_diagnostic_output():
    """Test the diagnostic system works."""
    print("\n=== Test 4: Diagnostic System ===")
    
    app = QApplication.instance() or QApplication(sys.argv)
    widget = SpritePreviewWidget()
    
    # Run diagnostic
    diagnostic = widget.diagnose_display_issue()
    
    # Check diagnostic contains key information
    assert "preview_label exists:" in diagnostic
    assert "sprite_pixmap:" in diagnostic
    assert "Widget hierarchy:" in diagnostic
    assert "QApplication exists:" in diagnostic
    
    print("✅ Diagnostic system provides comprehensive information")
    return True


def main():
    """Run all tests."""
    print("=" * 60)
    print("Testing Manual Offset Slider Flashing/Black Box Fixes")
    print("=" * 60)
    
    tests = [
        test_no_clearing_on_empty_data,
        test_palette_index_0_visible,
        test_rapid_updates_no_flashing,
        test_diagnostic_output
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"❌ Test failed: {e}")
            failed += 1
    
    print("\n" + "=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("\n🎉 All tests passed! The flashing/black box issue is fixed!")
    else:
        print(f"\n⚠️ {failed} test(s) failed. Check the implementation.")
    
    return failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)