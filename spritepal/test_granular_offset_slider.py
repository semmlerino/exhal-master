#!/usr/bin/env python3
"""
Test script to verify the granular offset slider implementation
"""

import sys

from PyQt6.QtWidgets import QApplication, QMainWindow, QPushButton, QVBoxLayout, QWidget

from spritepal.ui.extraction_panel import ExtractionPanel


def test_offset_slider():
    """Test the new granular offset slider features"""
    app = QApplication(sys.argv)

    # Create main window
    window = QMainWindow()
    window.setWindowTitle("Test Granular Offset Slider")
    window.resize(800, 600)

    # Create central widget
    central = QWidget()
    layout = QVBoxLayout(central)

    # Create extraction panel
    panel = ExtractionPanel()
    layout.addWidget(panel)

    # Add test button to switch to custom range
    test_btn = QPushButton("Switch to Custom Range Mode")
    def switch_to_custom():
        panel.preset_combo.setCurrentIndex(1)  # Custom Range
        print("Switched to Custom Range mode")
        print("\nTest Instructions:")
        print("1. The offset slider should now have fine granularity")
        print("2. Step size selector should default to '0x20 (1 tile)'")
        print("3. Try changing step sizes - slider should respond accordingly")
        print("4. Use Quick Jump dropdown to jump to common locations")
        print("5. Keyboard shortcuts:")
        print("   - Ctrl+Left/Right: Step by current step size")
        print("   - Page Up/Down: Jump by 0x1000")
        print("   - Number keys 1-9: Jump to 10%-90% of VRAM")
        print("\nOffset Display shows:")
        print("   - Hex value (e.g., 0xC000)")
        print("   - Tile number")
        print("   - Percentage of VRAM")

    test_btn.clicked.connect(switch_to_custom)
    layout.addWidget(test_btn)

    # Connect offset change signal for debugging
    def on_offset_changed(offset):
        print(f"Offset changed to: 0x{offset:04X} ({offset} bytes, Tile #{offset//32})")

    panel.offset_changed.connect(on_offset_changed)

    window.setCentralWidget(central)
    window.show()

    # Initial message
    print("Granular Offset Slider Test")
    print("=" * 40)
    print("Click 'Switch to Custom Range Mode' to test the new offset controls")

    return app.exec()

if __name__ == "__main__":
    sys.exit(test_offset_slider())
