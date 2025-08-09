#!/usr/bin/env python3
"""Test script to verify the threading fix for black flashing boxes."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton, QLabel
from PyQt6.QtCore import QTimer
from ui.dialogs.manual_offset_unified_integrated import UnifiedManualOffsetDialog
from core.managers import initialize_managers

def test_rapid_slider_movements():
    """Test rapid slider movements to check for black flashing."""
    app = QApplication(sys.argv)
    
    # Initialize managers
    try:
        initialize_managers()
    except Exception as e:
        print(f"Warning: Could not initialize managers: {e}")
    
    # Create main window to host the dialog
    main_window = QMainWindow()
    main_window.setWindowTitle("Threading Fix Test")
    main_window.resize(800, 600)
    
    # Create central widget
    central = QWidget()
    layout = QVBoxLayout(central)
    
    status_label = QLabel("Testing manual offset dialog slider...")
    layout.addWidget(status_label)
    
    # Create dialog
    dialog = UnifiedManualOffsetDialog(main_window)
    
    # Create test button
    test_button = QPushButton("Test Rapid Slider Movement")
    layout.addWidget(test_button)
    
    def run_test():
        """Simulate rapid slider movements."""
        if not dialog.browse_tab:
            status_label.setText("ERROR: browse_tab not found")
            return
            
        slider = dialog.browse_tab.position_slider
        offsets = [0x200000, 0x201000, 0x202000, 0x203000, 0x204000,
                   0x205000, 0x206000, 0x207000, 0x208000, 0x209000]
        
        def move_slider():
            if offsets:
                offset = offsets.pop(0)
                slider.setValue(offset)
                status_label.setText(f"Moved slider to 0x{offset:06X}")
                # Schedule next movement
                QTimer.singleShot(50, move_slider)  # 50ms between movements
            else:
                status_label.setText("Test completed! Check for black flashing.")
                
        # Start the test
        dialog.show()
        move_slider()
    
    test_button.clicked.connect(run_test)
    
    # Add button to show dialog
    show_button = QPushButton("Show Manual Offset Dialog")
    show_button.clicked.connect(dialog.show)
    layout.addWidget(show_button)
    
    main_window.setCentralWidget(central)
    main_window.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    test_rapid_slider_movements()