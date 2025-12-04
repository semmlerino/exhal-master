#!/usr/bin/env python3
from __future__ import annotations

"""
Test script to validate fullscreen sprite viewer fixes.
Run this to test if the fullscreen viewer covers the entire screen.
"""

import sys
from pathlib import Path

# Add the project root to the path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from PySide6.QtWidgets import QApplication, QPushButton, QVBoxLayout, QWidget
from ui.widgets.fullscreen_sprite_viewer import FullscreenSpriteViewer
from utils.logging_config import setup_logging


class FullscreenTestWidget(QWidget):
    """Simple test widget to test fullscreen functionality."""

    def __init__(self):
        super().__init__()
        self.fullscreen_viewer = None
        self.setup_ui()

    def setup_ui(self):
        """Setup test UI."""
        self.setWindowTitle("Fullscreen Test")
        self.setGeometry(100, 100, 300, 200)

        layout = QVBoxLayout()

        # Test button
        test_button = QPushButton("Test Fullscreen Viewer")
        test_button.clicked.connect(self.test_fullscreen)
        layout.addWidget(test_button)

        # Instructions
        from PySide6.QtWidgets import QLabel
        instructions = QLabel(
            "Click the button to test fullscreen viewer.\n"
            "The viewer should cover the ENTIRE screen.\n"
            "Press ESC to close the fullscreen viewer.\n"
            "Check console for detailed logging."
        )
        instructions.setWordWrap(True)
        layout.addWidget(instructions)

        self.setLayout(layout)

    def test_fullscreen(self):
        """Test the fullscreen viewer."""
        print("Testing fullscreen viewer...")

        # Create test sprite data
        test_sprites = [
            {
                'offset': 0x1000,
                'name': 'Test Sprite 1',
                'decompressed_size': 256,
                'tile_count': 8
            },
            {
                'offset': 0x2000,
                'name': 'Test Sprite 2',
                'decompressed_size': 512,
                'tile_count': 16
            }
        ]

        # Create fullscreen viewer (no parent to avoid constraints)
        if not self.fullscreen_viewer:
            self.fullscreen_viewer = FullscreenSpriteViewer(None)
            self.fullscreen_viewer.viewer_closed.connect(self.on_viewer_closed)

        # Set test data and show
        if self.fullscreen_viewer.set_sprite_data(test_sprites, 0x1000, "", None):
            print("Showing fullscreen viewer...")
            self.fullscreen_viewer.show()
        else:
            print("Failed to initialize fullscreen viewer")

    def on_viewer_closed(self):
        """Handle viewer closed."""
        print("Fullscreen viewer closed")

def main():
    """Main test function."""
    # Setup logging to see debug output
    setup_logging()

    app = QApplication(sys.argv)

    # Create and show test widget
    test_widget = FullscreenTestWidget()
    test_widget.show()

    print("Fullscreen test application started.")
    print("Click 'Test Fullscreen Viewer' to test fullscreen functionality.")
    print("Check that the fullscreen viewer covers the ENTIRE screen.")

    return app.exec()

if __name__ == "__main__":
    sys.exit(main())
