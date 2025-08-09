#!/usr/bin/env python3
"""
Test script to trace the exact execution path when the slider is moved.
This helps debug why black boxes appear instead of actual sprite data.
"""

import sys
import os
import logging
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from PyQt6.QtWidgets import QApplication, QMainWindow, QPushButton, QVBoxLayout, QWidget, QSlider
from PyQt6.QtCore import Qt
from ui.dialogs.manual_offset_unified_integrated import UnifiedManualOffsetDialog
from core.extraction.extraction_manager import ExtractionManager

# Configure logging to see TRACE messages
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('slider_trace.log', mode='w')
    ]
)

class TestWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Slider Movement Trace Test")
        self.setGeometry(100, 100, 400, 200)
        
        widget = QWidget()
        layout = QVBoxLayout()
        
        # Button to open the dialog
        self.open_btn = QPushButton("Open Manual Offset Dialog")
        self.open_btn.clicked.connect(self.open_dialog)
        layout.addWidget(self.open_btn)
        
        # Test slider to simulate movements
        self.test_slider = QSlider(Qt.Orientation.Horizontal)
        self.test_slider.setRange(0, 0x100000)
        self.test_slider.valueChanged.connect(self.on_slider_changed)
        layout.addWidget(self.test_slider)
        
        widget.setLayout(layout)
        self.setCentralWidget(widget)
        
        self.dialog = None
        self.extraction_manager = None
        
    def open_dialog(self):
        """Open the manual offset dialog with a test ROM."""
        # Find a test ROM
        test_rom = None
        test_dir = project_root / "tests" / "fixtures" / "roms"
        if test_dir.exists():
            for rom_file in test_dir.glob("*.sfc"):
                test_rom = str(rom_file)
                break
        
        if not test_rom:
            # Try to find any ROM in the project
            for rom_file in project_root.rglob("*.sfc"):
                test_rom = str(rom_file)
                break
        
        if not test_rom:
            print("No test ROM found. Please place a .sfc file in tests/fixtures/roms/")
            return
        
        print(f"Using test ROM: {test_rom}")
        
        # Create extraction manager
        self.extraction_manager = ExtractionManager()
        
        # Load ROM
        try:
            rom_size = os.path.getsize(test_rom)
            print(f"ROM size: {rom_size} bytes")
        except Exception as e:
            print(f"Error loading ROM: {e}")
            return
        
        # Create and show dialog
        self.dialog = UnifiedManualOffsetDialog(self)
        self.dialog.set_rom_data(test_rom, rom_size, self.extraction_manager)
        self.dialog.show()
        
        print("Dialog opened. Now move the slider to trigger the trace.")
        
    def on_slider_changed(self, value):
        """Simulate slider changes on the dialog."""
        if self.dialog and self.dialog.browse_tab:
            print(f"\n=== SIMULATING SLIDER MOVE TO 0x{value:06X} ===")
            self.dialog.browse_tab.position_slider.setValue(value)

def main():
    app = QApplication(sys.argv)
    window = TestWindow()
    window.show()
    
    print("\nSlider Movement Trace Test")
    print("=" * 50)
    print("1. Click 'Open Manual Offset Dialog'")
    print("2. Move the test slider to simulate movements")
    print("3. Check slider_trace.log for detailed execution trace")
    print("=" * 50)
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()