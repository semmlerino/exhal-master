#!/usr/bin/env python3
"""
Test script for visual similarity search integration.
Tests the context menu functionality and similarity search dialog.
"""

import os
import sys

from PyQt6.QtGui import QColor, QPainter, QPixmap
from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Test imports
try:
    from core.visual_similarity_search import SimilarityMatch, VisualSimilarityEngine
    from ui.dialogs.similarity_results_dialog import (
        SimilarityResultsDialog,
        SimilarityResultWidget,
    )
    from ui.widgets.sprite_preview_widget import SpritePreviewWidget
    print("All imports successful!")
except ImportError as e:
    print(f"Import error: {e}")
    sys.exit(1)

def create_test_pixmap(width=64, height=64, color=QColor(255, 0, 0)):
    """Create a test pixmap with given color."""
    pixmap = QPixmap(width, height)
    pixmap.fill(color)

    # Add some pattern to make it visually interesting
    painter = QPainter(pixmap)
    painter.setPen(QColor(255, 255, 255))
    painter.drawRect(10, 10, width-20, height-20)
    painter.drawLine(0, 0, width, height)
    painter.drawLine(width, 0, 0, height)
    painter.end()

    return pixmap

def test_similarity_widget():
    """Test the sprite preview widget with similarity search."""
    app = QApplication(sys.argv)

    # Create main window
    window = QMainWindow()
    window.setWindowTitle("Visual Similarity Search Test")
    window.resize(400, 300)

    # Create central widget
    central_widget = QWidget()
    layout = QVBoxLayout(central_widget)

    # Create sprite preview widget
    preview_widget = SpritePreviewWidget("Test Preview")
    layout.addWidget(preview_widget)

    # Set test sprite
    test_pixmap = create_test_pixmap()
    preview_widget.set_sprite(test_pixmap)
    preview_widget.set_current_offset(0x10000)

    # Connect similarity search signal
    def on_similarity_search(offset):
        print(f"Similarity search requested for offset: 0x{offset:06X}")

    preview_widget.similarity_search_requested.connect(on_similarity_search)

    window.setCentralWidget(central_widget)
    window.show()

    print("Test window created! Right-click on the sprite to see the context menu.")
    print("The 'Find Similar Sprites...' option should appear when you right-click.")

    return app, window

def test_similarity_results_dialog():
    """Test the similarity results dialog."""
    app = QApplication(sys.argv)

    # Create some test matches
    matches = [
        SimilarityMatch(offset=0x20000, similarity_score=0.95, hash_distance=5, metadata={"test": "match1"}),
        SimilarityMatch(offset=0x30000, similarity_score=0.87, hash_distance=12, metadata={"test": "match2"}),
        SimilarityMatch(offset=0x40000, similarity_score=0.82, hash_distance=18, metadata={"test": "match3"}),
    ]

    # Create results dialog
    dialog = SimilarityResultsDialog(matches, 0x10000)

    # Connect signal
    def on_sprite_selected(offset):
        print(f"Selected sprite at offset: 0x{offset:06X}")

    dialog.sprite_selected.connect(on_sprite_selected)

    print("Test similarity results dialog created!")
    dialog.exec()

    return app

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "results":
        print("Testing similarity results dialog...")
        app = test_similarity_results_dialog()
    else:
        print("Testing sprite preview widget with context menu...")
        app, window = test_similarity_widget()
        sys.exit(app.exec())
