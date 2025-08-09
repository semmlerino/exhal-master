#!/usr/bin/env python3
"""
Test manual offset dialog with comprehensive debug logging.
"""

import sys
import os
import logging

# Add the parent directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Set up detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

from PyQt6.QtWidgets import QApplication, QFileDialog
from PyQt6.QtCore import QTimer
from core.managers.registry import initialize_managers
from ui.dialogs.manual_offset_unified_integrated import UnifiedManualOffsetDialog

def main():
    app = QApplication(sys.argv)
    
    # Initialize managers
    initialize_managers()
    
    # Create dialog
    dialog = UnifiedManualOffsetDialog()
    
    # Set a test ROM path if available
    test_rom = "Kirby Super Star (USA).sfc"
    if os.path.exists(test_rom):
        print(f"Loading ROM: {test_rom}")
        rom_size = os.path.getsize(test_rom)
        from core.managers.registry import get_extraction_manager
        extraction_manager = get_extraction_manager()
        dialog.set_rom_data(test_rom, rom_size, extraction_manager)
    else:
        print("No test ROM found, please load one manually")
    
    # Show dialog
    dialog.show()
    
    # Run the application
    sys.exit(app.exec())

if __name__ == "__main__":
    main()