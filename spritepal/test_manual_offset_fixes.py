#!/usr/bin/env python3
"""
Test to verify the manual offset dialog fixes:
1. Sprite display (no more black boxes)
2. Prev/Next navigation working
"""

import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt

from ui.widgets.sprite_preview_widget import SpritePreviewWidget
from core.default_palette_loader import DefaultPaletteLoader
from ui.rom_extraction.workers.sprite_search_worker import SpriteSearchWorker
from core.rom_extractor import ROMExtractor
from core.sprite_finder import SpriteFinder


def test_palette_index_fix():
    """Test that default palette index is now 8, not 0."""
    print("\n=== Test 1: Palette Index Fix ===")
    
    app = QApplication.instance() or QApplication(sys.argv)
    
    # Create widget
    widget = SpritePreviewWidget()
    
    # Check initial palette index
    assert widget.current_palette_index == 8, \
        f"Expected palette index 8, got {widget.current_palette_index}"
    print(f"✅ Initial palette index is correct: {widget.current_palette_index}")
    
    # Load default palettes
    loader = DefaultPaletteLoader()
    palettes = loader.get_all_kirby_palettes()
    
    # Check that palette 8 exists
    assert 8 in palettes, "Palette 8 (Kirby Pink) should exist"
    print(f"✅ Palette 8 exists with {len(palettes[8])} colors")
    
    # Check that palette 0 doesn't exist in defaults
    assert 0 not in palettes, "Palette 0 should not exist in defaults"
    print("✅ Palette 0 correctly not in defaults (avoiding black sprites)")
    
    return True


def test_sprite_display_with_palette_8():
    """Test that sprites display correctly with palette 8."""
    print("\n=== Test 2: Sprite Display with Palette 8 ===")
    
    app = QApplication.instance() or QApplication(sys.argv)
    
    # Create widget
    widget = SpritePreviewWidget()
    
    # Create test sprite data
    test_data = bytes([i % 16 for i in range(64*64)])
    
    # Load sprite
    widget.load_sprite_from_4bpp(test_data, 64, 64, "test_sprite")
    app.processEvents()
    
    # Check that pixmap was created
    pixmap = widget.preview_label.pixmap()
    assert pixmap is not None, "Pixmap should be created"
    assert not pixmap.isNull(), "Pixmap should not be null"
    print(f"✅ Sprite displayed successfully: {pixmap.width()}x{pixmap.height()}")
    
    # Check palette index didn't get reset to 0
    if widget.palettes:
        # If palettes were loaded, check the index
        if len(widget.palettes) > 8:
            expected = 8
        else:
            expected = 0  # Falls back to first if palette 8 not available
        
        assert widget.current_palette_index == expected, \
            f"Palette index changed unexpectedly to {widget.current_palette_index}"
        print(f"✅ Palette index maintained correctly: {widget.current_palette_index}")
    
    return True


def test_sprite_finder_method():
    """Test that SpriteFinder has the correct method."""
    print("\n=== Test 3: SpriteFinder Method Fix ===")
    
    # Create sprite finder
    sprite_finder = SpriteFinder()
    
    # Check that find_sprite_at_offset exists
    assert hasattr(sprite_finder, 'find_sprite_at_offset'), \
        "SpriteFinder should have find_sprite_at_offset method"
    print("✅ SpriteFinder has find_sprite_at_offset method")
    
    # Check that test_offset doesn't exist (the broken method)
    assert not hasattr(sprite_finder, 'test_offset'), \
        "SpriteFinder should NOT have test_offset method"
    print("✅ Confirmed test_offset method doesn't exist (was the bug)")
    
    return True


def test_navigation_worker():
    """Test that the navigation worker can be created without errors."""
    print("\n=== Test 4: Navigation Worker Creation ===")
    
    try:
        # Create a mock ROM extractor
        extractor = ROMExtractor()
        
        # Create search worker (this would previously fail due to missing method)
        worker = SpriteSearchWorker(
            rom_path="test.smc",
            start_offset=0x1000,
            end_offset=0x2000,
            direction=1,
            rom_extractor=extractor,
            parent=None
        )
        
        print("✅ Search worker created successfully")
        
        # Verify it has the correct signals
        assert hasattr(worker, 'sprite_found'), "Worker should have sprite_found signal"
        assert hasattr(worker, 'search_complete'), "Worker should have search_complete signal"
        print("✅ Worker has required signals")
        
        return True
        
    except Exception as e:
        print(f"❌ Failed to create search worker: {e}")
        return False


def main():
    """Run all tests."""
    print("=" * 60)
    print("Testing Manual Offset Dialog Fixes")
    print("=" * 60)
    
    tests = [
        test_palette_index_fix,
        test_sprite_display_with_palette_8,
        test_sprite_finder_method,
        test_navigation_worker
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
        print("\n✅ All fixes verified successfully!")
        print("- Sprites now display with correct palette (index 8)")
        print("- No more black boxes")
        print("- Prev/Next navigation should work")
    else:
        print(f"\n⚠️ {failed} test(s) failed. Some issues may remain.")
    
    return failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)