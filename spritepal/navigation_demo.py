#!/usr/bin/env python3
"""
Demo of the Enhanced Sprite Navigation System

This demo shows how the new navigation features improve the sprite discovery workflow:
1. Visual ROM map with sprite density heatmap
2. Smart navigation that skips empty regions
3. Thumbnail previews of nearby sprites
4. Keyboard-friendly navigation
5. Bookmark system for interesting finds
"""

import sys

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QApplication,
    QLabel,
    QMainWindow,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

DEMO_TEXT = """
SpritePal Enhanced Navigation System Demo
========================================

The new navigation system addresses key UX problems:

1. VISUAL ROM MAP
   - Shows sprite locations as colored markers
   - Green = high quality sprites
   - Yellow = medium quality
   - Red = low quality
   - Click anywhere on the map to jump to that location

2. SMART NAVIGATION
   - "Next/Previous Sprite" buttons skip empty ROM areas
   - Automatically finds valid sprites, not just empty data
   - Shows progress during search
   - Region-aware navigation groups related sprites

3. NEARBY SPRITES PREVIEW
   - Shows thumbnails of sprites near current position
   - Click any thumbnail to jump to that sprite
   - Quality indicators help identify best sprites

4. KEYBOARD SHORTCUTS
   - Arrow keys: Fine navigation (256 bytes)
   - Shift+Arrow: Large steps (64KB)
   - PageUp/PageDown: Jump to next/previous sprite
   - Ctrl+G: Go to specific offset
   - Ctrl+D: Bookmark current location
   - Ctrl+B: Show bookmarks menu

5. ENHANCED MANUAL OFFSET DIALOG
   - Mini ROM map shows current position
   - Bookmark system saves interesting locations
   - Region-aware navigation mode
   - Real-time preview updates while dragging

HOW TO USE:

1. Load a ROM file
2. Use the Sprite Navigator widget for exploration
3. Click on the ROM map or use keyboard shortcuts
4. Preview shows nearby sprites automatically
5. Bookmark interesting finds for later
6. Switch to Smart Mode for region-based navigation

The system makes sprite discovery intuitive and efficient,
removing the frustration of navigating vast empty regions.
"""


class NavigationDemoWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("SpritePal Navigation Enhancement Demo")
        self.setMinimumSize(800, 600)

        # Central widget
        central = QWidget()
        self.setCentralWidget(central)

        layout = QVBoxLayout(central)

        # Title
        title = QLabel("Enhanced Sprite Navigation Demo")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        # Demo text
        text_edit = QTextEdit()
        text_edit.setReadOnly(True)
        text_edit.setPlainText(DEMO_TEXT)
        text_font = QFont("Consolas", 10)
        text_edit.setFont(text_font)
        layout.addWidget(text_edit)

        # Status
        status = QLabel("This is a demonstration of the navigation features. "
                       "Run launch_spritepal.py to use the actual application.")
        status.setStyleSheet("background: #f0f0f0; padding: 10px; border: 1px solid #ccc;")
        layout.addWidget(status)


def main():
    app = QApplication(sys.argv)
    window = NavigationDemoWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
