#!/usr/bin/env python3
"""
Test script to check palette display issues in the sprite editor GUI
"""

import os
import sys

from PyQt6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

# Add sprite_editor directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "sprite_editor"))

from palette_utils import get_grayscale_palette, read_cgram_palette
from sprite_editor_core import SpriteEditorCore
from sprite_viewer_widget import SpriteViewerWidget


class PaletteTestWindow(QMainWindow):
    """Test window for checking palette display"""

    def __init__(self):
        super().__init__()
        self.core = SpriteEditorCore()
        self.current_image = None
        self.cgram_file = None
        self.setup_ui()

    def setup_ui(self):
        """Setup the test UI"""
        self.setWindowTitle("Palette Display Test")
        self.setGeometry(100, 100, 800, 600)

        # Central widget
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        # Info label
        self.info_label = QLabel("Load a VRAM file to test palette display")
        layout.addWidget(self.info_label)

        # Buttons
        button_layout = QHBoxLayout()

        load_vram_btn = QPushButton("Load VRAM")
        load_vram_btn.clicked.connect(self.load_vram)
        button_layout.addWidget(load_vram_btn)

        load_cgram_btn = QPushButton("Load CGRAM")
        load_cgram_btn.clicked.connect(self.load_cgram)
        button_layout.addWidget(load_cgram_btn)

        # Palette buttons
        for i in range(4):
            pal_btn = QPushButton(f"Palette {i}")
            pal_btn.clicked.connect(lambda checked, p=i: self.apply_palette(p))
            button_layout.addWidget(pal_btn)

        grayscale_btn = QPushButton("Grayscale")
        grayscale_btn.clicked.connect(self.apply_grayscale)
        button_layout.addWidget(grayscale_btn)

        layout.addLayout(button_layout)

        # Sprite viewer
        self.viewer = SpriteViewerWidget()
        layout.addWidget(self.viewer)

    def load_vram(self):
        """Load and display VRAM data"""
        # Find a VRAM file
        vram_files = ["vram_from_savestate.dmp", "SnesVideoRam.VRAM.dmp", "mss2_VRAM.dmp"]
        vram_file = None
        for f in vram_files:
            if os.path.exists(f):
                vram_file = f
                break

        if not vram_file:
            self.info_label.setText("No VRAM file found!")
            return

        try:
            # Extract sprites
            image, tile_count = self.core.extract_sprites(
                vram_file=vram_file,
                offset=0x6000,
                size=0x800,  # 64 tiles
                tiles_per_row=8
            )

            self.current_image = image
            self.viewer.set_image(image)

            self.info_label.setText(f"Loaded {tile_count} tiles from {vram_file}")

            # Check image properties
            print(f"Image mode: {image.mode}")
            print(f"Image size: {image.size}")
            if hasattr(image, "getpalette"):
                pal = image.getpalette()
                if pal:
                    print(f"Palette length: {len(pal)}")
                    print(f"First few colors: {pal[:12]}")
                else:
                    print("No palette data!")

        except Exception as e:
            self.info_label.setText(f"Error: {e}")
            import traceback
            traceback.print_exc()

    def load_cgram(self):
        """Load CGRAM file"""
        cgram_files = ["SnesCgRam.dmp", "cgram_from_savestate.dmp", "mss2_CGRAM.dmp"]
        for f in cgram_files:
            if os.path.exists(f):
                self.cgram_file = f
                self.info_label.setText(f"Loaded CGRAM: {f}")
                return

        self.info_label.setText("No CGRAM file found!")

    def apply_palette(self, palette_num):
        """Apply a specific palette"""
        if not self.current_image:
            self.info_label.setText("Load VRAM first!")
            return

        if not self.cgram_file:
            self.info_label.setText("Load CGRAM first!")
            return

        try:
            palette = read_cgram_palette(self.cgram_file, palette_num)
            if palette:
                # Create a copy of the image
                img_copy = self.current_image.copy()

                print(f"\nApplying palette {palette_num}:")
                print(f"Palette data available: {len(palette)} bytes")
                print(f"First color: RGB({palette[0]}, {palette[1]}, {palette[2]})")

                # Apply palette
                img_copy.putpalette(palette)

                # Update viewer
                self.viewer.set_image(img_copy)

                self.info_label.setText(f"Applied palette {palette_num}")
            else:
                self.info_label.setText(f"Failed to load palette {palette_num}")

        except Exception as e:
            self.info_label.setText(f"Error applying palette: {e}")
            import traceback
            traceback.print_exc()

    def apply_grayscale(self):
        """Apply grayscale palette"""
        if not self.current_image:
            self.info_label.setText("Load VRAM first!")
            return

        try:
            # Create a copy of the image
            img_copy = self.current_image.copy()

            # Apply grayscale palette
            grayscale_pal = get_grayscale_palette()
            img_copy.putpalette(grayscale_pal)

            # Update viewer
            self.viewer.set_image(img_copy)

            self.info_label.setText("Applied grayscale palette")

        except Exception as e:
            self.info_label.setText(f"Error: {e}")
            import traceback
            traceback.print_exc()


def main():
    """Run the palette test"""
    app = QApplication(sys.argv)

    window = PaletteTestWindow()
    window.show()

    print("=" * 60)
    print("PALETTE DISPLAY TEST")
    print("=" * 60)
    print("1. Click 'Load VRAM' to load sprite data")
    print("2. Click 'Load CGRAM' to load palette data")
    print("3. Click palette buttons to test different palettes")
    print("4. Check if colors display correctly")
    print("=" * 60)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
