#!/usr/bin/env python3
"""
Test script to verify the delta-based undo system integration in pixel_editor_widgets.py
"""

import sys
import numpy as np
from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton, QLabel, QHBoxLayout
from PyQt6.QtCore import Qt

# Import the widgets with integrated delta undo system
from pixel_editor_widgets import PixelCanvas, ColorPaletteWidget


class TestWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Delta Undo System Test")
        self.setGeometry(100, 100, 800, 600)
        
        # Create central widget
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        
        # Create controls
        controls = QWidget()
        controls_layout = QHBoxLayout(controls)
        
        # Undo/redo buttons
        self.undo_btn = QPushButton("Undo")
        self.redo_btn = QPushButton("Redo")
        self.undo_btn.clicked.connect(self.on_undo)
        self.redo_btn.clicked.connect(self.on_redo)
        
        # Memory stats label
        self.stats_label = QLabel("Memory: 0 MB | Commands: 0")
        
        controls_layout.addWidget(self.undo_btn)
        controls_layout.addWidget(self.redo_btn)
        controls_layout.addWidget(self.stats_label)
        controls_layout.addStretch()
        
        layout.addWidget(controls)
        
        # Create canvas with palette
        self.palette = ColorPaletteWidget()
        self.canvas = PixelCanvas(self.palette)
        
        # Create a test image
        self.canvas.new_image(32, 32)
        
        # Connect signals
        self.palette.colorSelected.connect(self.on_color_selected)
        self.canvas.pixelChanged.connect(self.update_ui)
        
        # Add widgets to layout
        canvas_layout = QHBoxLayout()
        canvas_layout.addWidget(self.palette)
        canvas_layout.addWidget(self.canvas)
        canvas_layout.addStretch()
        
        layout.addLayout(canvas_layout)
        
        # Initial UI update
        self.update_ui()
        
    def on_undo(self):
        """Handle undo button click"""
        self.canvas.undo()
        self.update_ui()
        
    def on_redo(self):
        """Handle redo button click"""
        self.canvas.redo()
        self.update_ui()
        
    def on_color_selected(self, index):
        """Handle color selection"""
        self.canvas.current_color = index
        
    def update_ui(self):
        """Update UI elements based on current state"""
        # Update undo/redo button states
        undo_count = self.canvas.get_undo_count()
        redo_count = self.canvas.get_redo_count()
        
        self.undo_btn.setEnabled(undo_count > 0)
        self.redo_btn.setEnabled(redo_count > 0)
        
        self.undo_btn.setText(f"Undo ({undo_count})")
        self.redo_btn.setText(f"Redo ({redo_count})")
        
        # Update memory stats
        stats = self.canvas.get_undo_memory_stats()
        memory_mb = stats['total_mb']
        command_count = stats['command_count']
        compressed = stats['compressed_count']
        
        self.stats_label.setText(
            f"Memory: {memory_mb:.2f} MB | Commands: {command_count} | Compressed: {compressed}"
        )


def main():
    """Run the test application"""
    app = QApplication(sys.argv)
    
    # Create and show test window
    window = TestWindow()
    window.show()
    
    # Print instructions
    print("Delta Undo System Test")
    print("=====================")
    print("1. Draw some pixels with the pencil tool")
    print("2. Try flood fill to create larger changes")
    print("3. Use Undo/Redo buttons to test the system")
    print("4. Watch the memory usage in the status bar")
    print("5. Memory should be much lower than traditional full-image copies")
    print("\nThe system will automatically compress older commands to save memory.")
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()