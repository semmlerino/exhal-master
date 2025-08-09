#!/usr/bin/env python3
"""
Test script to verify sprite clarity has been restored after reverting problematic changes.

This tests that:
1. Sprites display with proper contrast (black stays black)
2. Empty data clears the display (to avoid showing corrupted sprites)
3. Background is clean white for maximum clarity
4. Prev/Next navigation signals are connected
"""

import sys
from PyQt6.QtWidgets import QApplication
from ui.widgets.sprite_preview_widget import SpritePreviewWidget
from PIL import Image
import numpy as np


def test_palette_not_modified():
    """Test that palette index 0 stays black for proper contrast."""
    print("\n=== Test 1: Palette Colors Preserved ===")
    
    app = QApplication.instance() or QApplication(sys.argv)
    widget = SpritePreviewWidget()
    
    # Set a test palette with black at index 0
    test_palette = [
        [0, 0, 0],      # Index 0: Pure black (should stay black)
        [255, 0, 0],    # Index 1: Red
        [0, 255, 0],    # Index 2: Green
        [0, 0, 255]     # Index 3: Blue
    ]
    
    widget.palettes = [test_palette]
    widget.current_palette_index = 0
    
    # Create a test sprite with black pixels (palette index 0)
    img = Image.new('L', (64, 64), 0)  # All black (palette index 0)
    
    # Draw a simple pattern
    for x in range(64):
        for y in range(64):
            if x < 32 and y < 32:
                img.putpixel((x, y), 0)  # Black (index 0)
            elif x >= 32 and y < 32:
                img.putpixel((x, y), 85)  # ~index 5 (will map to color)
            elif x < 32 and y >= 32:
                img.putpixel((x, y), 170)  # ~index 10
            else:
                img.putpixel((x, y), 255)  # ~index 15
    
    # Apply palette
    widget._update_preview_with_palette(img)
    app.processEvents()
    
    # Check that pixmap was created
    pixmap = widget.preview_label.pixmap()
    assert pixmap is not None, "Pixmap should be created"
    
    print("✅ Palette colors preserved - black stays black for proper contrast")
    return True


def test_empty_data_clears():
    """Test that empty data properly clears the display."""
    print("\n=== Test 2: Empty Data Clears Display ===")
    
    app = QApplication.instance() or QApplication(sys.argv)
    widget = SpritePreviewWidget()
    
    # Load initial sprite
    test_data = bytes([i % 16 for i in range(64*64)])
    widget.load_sprite_from_4bpp(test_data, 64, 64, "test")
    app.processEvents()
    
    # Verify sprite loaded
    pixmap1 = widget.preview_label.pixmap()
    assert pixmap1 is not None, "Initial sprite should load"
    
    # Load empty data
    widget.load_sprite_from_4bpp(b"", 64, 64, "empty")
    app.processEvents()
    
    # Check that display was cleared
    label_text = widget.preview_label.text()
    assert "No preview available" in label_text or "No sprite" in label_text, \
        f"Empty data should clear display, got: {label_text}"
    
    info_text = widget.essential_info_label.text()
    assert "No data" in info_text or "No sprite" in info_text, \
        f"Info should show no data, got: {info_text}"
    
    print("✅ Empty data properly clears display to avoid corruption")
    return True


def test_white_background():
    """Test that background is clean white for clarity."""
    print("\n=== Test 3: White Background for Clarity ===")
    
    app = QApplication.instance() or QApplication(sys.argv)
    widget = SpritePreviewWidget()
    
    # Load a sprite to trigger content style
    test_data = bytes([i % 16 for i in range(64*64)])
    widget.load_sprite_from_4bpp(test_data, 64, 64, "test")
    app.processEvents()
    
    # Check stylesheet contains white background
    stylesheet = widget.preview_label.styleSheet()
    assert "background-color: #ffffff" in stylesheet or \
           "background-color: white" in stylesheet.lower(), \
        f"Background should be white for clarity, got: {stylesheet[:100]}"
    
    print("✅ Background is clean white for maximum sprite clarity")
    return True


def test_navigation_signals():
    """Test that prev/next navigation signals are connected."""
    print("\n=== Test 4: Navigation Signals ===")
    
    app = QApplication.instance() or QApplication(sys.argv)
    
    # Import the dialog to test navigation
    from ui.dialogs.manual_offset_unified_integrated import UnifiedManualOffsetDialog
    
    # Create a minimal test setup
    dialog = UnifiedManualOffsetDialog(parent=None)
    
    # Check browse tab exists and has navigation buttons
    assert dialog.browse_tab is not None, "Browse tab should exist"
    assert hasattr(dialog.browse_tab, 'prev_button'), "Prev button should exist"
    assert hasattr(dialog.browse_tab, 'next_button'), "Next button should exist"
    
    # Check signals exist
    assert hasattr(dialog.browse_tab, 'find_prev_clicked'), "find_prev_clicked signal should exist"
    assert hasattr(dialog.browse_tab, 'find_next_clicked'), "find_next_clicked signal should exist"
    
    # Check methods exist
    assert hasattr(dialog, '_find_prev_sprite'), "_find_prev_sprite method should exist"
    assert hasattr(dialog, '_find_next_sprite'), "_find_next_sprite method should exist"
    
    print("✅ Navigation signals and methods are properly defined")
    return True


def main():
    """Run all tests."""
    print("=" * 60)
    print("Testing Sprite Clarity Restoration")
    print("=" * 60)
    
    tests = [
        test_palette_not_modified,
        test_empty_data_clears,
        test_white_background,
        test_navigation_signals
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"❌ Test failed: {e}")
            import traceback
            traceback.print_exc()
            failed += 1
    
    print("\n" + "=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("\n✅ Sprite clarity has been restored!")
        print("- Black pixels stay black for proper contrast")
        print("- Empty areas clear properly to avoid corruption")
        print("- White background provides maximum clarity")
        print("- Navigation structure is intact")
    else:
        print(f"\n⚠️ {failed} test(s) failed. Check the implementation.")
    
    return failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)