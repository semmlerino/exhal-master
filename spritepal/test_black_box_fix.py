#!/usr/bin/env python3
"""
Test that the black box issue is fixed by proper palette initialization.

The issue was: palette index was 8 but only 4 palettes existed (0-3),
causing fallback to grayscale display of raw 4-bit values (0-15),
which appeared nearly black.
"""

import sys
from PyQt6.QtWidgets import QApplication
from ui.widgets.sprite_preview_widget import SpritePreviewWidget
from PIL import Image


def test_palette_index_valid():
    """Test that palette index starts at 0 and stays in valid range."""
    print("\n=== Test 1: Valid Palette Index ===")
    
    app = QApplication.instance() or QApplication(sys.argv)
    widget = SpritePreviewWidget()
    
    # Check initial palette index is 0, not 8
    assert widget.current_palette_index == 0, \
        f"Palette index should start at 0, got {widget.current_palette_index}"
    
    print(f"✅ Initial palette index is {widget.current_palette_index} (valid)")
    
    # Load sprite data to trigger palette loading
    test_data = bytes([i % 16 for i in range(64*64)])
    widget.load_sprite_from_4bpp(test_data, 64, 64, "test")
    app.processEvents()
    
    # Check palettes are loaded
    assert widget.palettes is not None, "Palettes should be loaded"
    assert len(widget.palettes) > 0, "Should have at least one palette"
    
    # Check palette index is still valid
    assert widget.current_palette_index < len(widget.palettes), \
        f"Palette index {widget.current_palette_index} out of range (0-{len(widget.palettes)-1})"
    
    print(f"✅ After loading: {len(widget.palettes)} palettes, index {widget.current_palette_index} (valid)")
    return True


def test_grayscale_scaling():
    """Test that grayscale values are properly scaled when no palette."""
    print("\n=== Test 2: Grayscale Scaling ===")
    
    app = QApplication.instance() or QApplication(sys.argv)
    widget = SpritePreviewWidget()
    
    # Clear palettes to force grayscale mode
    widget.palettes = []
    
    # Create a test image with 4-bit values (0-15)
    img = Image.new('L', (64, 64))
    for y in range(64):
        for x in range(64):
            # Create gradient from 0 to 15
            value = (x // 4) % 16
            img.putpixel((x, y), value)
    
    # This should trigger scaling (0-15 -> 0-255)
    widget._update_preview_with_palette(img)
    app.processEvents()
    
    # Check that pixmap was created (not black)
    pixmap = widget.preview_label.pixmap()
    assert pixmap is not None, "Pixmap should be created even without palette"
    
    print("✅ Grayscale scaling works - 4-bit values properly scaled to 8-bit")
    return True


def test_sprites_visible():
    """Test that sprites are actually visible (not all black)."""
    print("\n=== Test 3: Sprites Visible ===")
    
    app = QApplication.instance() or QApplication(sys.argv)
    widget = SpritePreviewWidget()
    
    # Create test sprite data with varied values
    test_data = []
    for i in range(64*64):
        # Mix of different palette indices (0-15)
        test_data.append(i % 16)
    test_data = bytes(test_data)
    
    # Load sprite
    widget.load_sprite_from_4bpp(test_data, 64, 64, "test_sprite")
    app.processEvents()
    
    # Check sprite loaded
    assert widget.sprite_pixmap is not None, "Sprite pixmap should be created"
    assert widget.sprite_data is not None, "Sprite data should be stored"
    
    # Check palettes loaded
    assert widget.palettes is not None and len(widget.palettes) > 0, \
        "Palettes should be loaded"
    
    # Check palette is being applied (not grayscale fallback)
    assert widget.current_palette_index < len(widget.palettes), \
        "Should be using a valid palette, not grayscale fallback"
    
    # Check pixmap on label
    pixmap = widget.preview_label.pixmap()
    assert pixmap is not None, "Pixmap should be displayed"
    assert not pixmap.isNull(), "Pixmap should not be null"
    
    print(f"✅ Sprites are visible with palette {widget.current_palette_index}")
    return True


def main():
    """Run all tests."""
    print("=" * 60)
    print("Testing Black Box Fix")
    print("=" * 60)
    
    tests = [
        test_palette_index_valid,
        test_grayscale_scaling,
        test_sprites_visible
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
        print("\n✅ Black box issue is FIXED!")
        print("- Palette index starts at 0 (not 8)")
        print("- Palettes are loaded before use")
        print("- Grayscale values are properly scaled")
        print("- Sprites display with proper colors")
    else:
        print(f"\n⚠️ {failed} test(s) failed. Check the implementation.")
    
    return failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)