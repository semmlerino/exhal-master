#!/usr/bin/env python3
"""
Simple test to check sprite display directly.
"""

import sys
from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton
from PyQt6.QtCore import Qt
from PIL import Image
import numpy as np

from ui.widgets.sprite_preview_widget import SpritePreviewWidget
from core.default_palette_loader import DefaultPaletteLoader


def create_test_sprite_data():
    """Create test sprite data that should be visible."""
    # Create a simple 64x64 sprite with a pattern
    data = []
    for y in range(64):
        for x in range(64):
            # Create a checkerboard pattern with different palette indices
            if (x // 8 + y // 8) % 2 == 0:
                pixel = 5  # Mid-range palette index
            else:
                pixel = 10  # Different palette index
            data.append(pixel)
    return bytes(data)


def test_sprite_widget():
    """Test the sprite preview widget directly."""
    app = QApplication.instance() or QApplication(sys.argv)
    
    # Create main window
    window = QMainWindow()
    window.setWindowTitle("Sprite Display Test")
    window.resize(800, 600)
    
    # Create central widget
    central = QWidget()
    layout = QVBoxLayout()
    
    # Create sprite preview widget
    preview = SpritePreviewWidget("Test Preview")
    layout.addWidget(preview)
    
    # Create test button
    test_btn = QPushButton("Load Test Sprite")
    layout.addWidget(test_btn)
    
    def load_test_sprite():
        print("\n=== Loading Test Sprite ===")
        
        # Create test data
        test_data = create_test_sprite_data()
        print(f"Created test data: {len(test_data)} bytes")
        
        # Check current state
        print(f"Current palette index: {preview.current_palette_index}")
        print(f"Palettes loaded: {len(preview.palettes) if preview.palettes else 0}")
        
        # Load sprite
        preview.load_sprite_from_4bpp(test_data, 64, 64, "test_sprite")
        
        # Check result
        app.processEvents()
        
        pixmap = preview.preview_label.pixmap()
        if pixmap and not pixmap.isNull():
            print(f"✅ Pixmap loaded: {pixmap.width()}x{pixmap.height()}")
        else:
            print("❌ No pixmap loaded!")
            label_text = preview.preview_label.text()
            if label_text:
                print(f"   Label shows: '{label_text}'")
        
        print(f"Palette index after load: {preview.current_palette_index}")
        print(f"Palettes after load: {len(preview.palettes) if preview.palettes else 0}")
        
        # Run diagnostic
        print("\n=== Diagnostic Output ===")
        diagnostic = preview.diagnose_display_issue()
        
    test_btn.clicked.connect(load_test_sprite)
    
    # Create button to test with grayscale
    gray_btn = QPushButton("Load Grayscale Test")
    layout.addWidget(gray_btn)
    
    def load_grayscale():
        print("\n=== Loading Grayscale Test ===")
        
        # Create a grayscale image directly
        img = Image.new('L', (64, 64))
        for y in range(64):
            for x in range(64):
                # Create gradient
                value = (x + y) % 16  # 4-bit values
                img.putpixel((x, y), value)
        
        # Load as grayscale
        preview._load_grayscale_sprite(img, "grayscale_test")
        
        app.processEvents()
        
        pixmap = preview.preview_label.pixmap()
        if pixmap and not pixmap.isNull():
            print(f"✅ Pixmap loaded: {pixmap.width()}x{pixmap.height()}")
        else:
            print("❌ No pixmap loaded!")
    
    gray_btn.clicked.connect(load_grayscale)
    
    # Test palette reset issue
    reset_btn = QPushButton("Test Palette Reset")
    layout.addWidget(reset_btn)
    
    def test_palette_reset():
        print("\n=== Testing Palette Reset ===")
        
        # Set palette index to 8
        preview.current_palette_index = 8
        print(f"Set palette index to: {preview.current_palette_index}")
        
        # Load default palettes
        loader = DefaultPaletteLoader()
        palettes = loader.get_all_kirby_palettes()
        if palettes:
            palette_list = []
            for palette in palettes.values():
                if isinstance(palette, list):
                    palette_list.append(palette)
            preview.palettes = palette_list
            print(f"Loaded {len(preview.palettes)} palettes")
        
        print(f"Palette index after loading palettes: {preview.current_palette_index}")
        
        # Now load sprite data
        test_data = create_test_sprite_data()
        preview.load_sprite_from_4bpp(test_data, 64, 64, "palette_test")
        
        print(f"Palette index after loading sprite: {preview.current_palette_index}")
        
    reset_btn.clicked.connect(test_palette_reset)
    
    central.setLayout(layout)
    window.setCentralWidget(central)
    window.show()
    
    # Load initial sprite
    load_test_sprite()
    
    return app.exec()


if __name__ == "__main__":
    print("=" * 60)
    print("Sprite Display Simple Test")
    print("=" * 60)
    
    result = test_sprite_widget()
    print(f"\nTest completed with result: {result}")