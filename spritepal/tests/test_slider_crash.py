#!/usr/bin/env python3
"""
Test slider interaction to reproduce crash.
"""

import sys
import os
import logging
import time

# Add the parent directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Set up detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s.%(msecs)03d - %(name)s - %(levelname)s - %(message)s',
    datefmt='%H:%M:%S'
)

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer
from core.managers.registry import initialize_managers, get_extraction_manager
from ui.dialogs.manual_offset_unified_integrated import UnifiedManualOffsetDialog

def simulate_slider_drag(dialog):
    """Simulate dragging the slider."""
    if not dialog.browse_tab:
        print("No browse tab!")
        return
        
    slider = dialog.browse_tab.position_slider
    print(f"Slider range: {slider.minimum()} to {slider.maximum()}")
    print(f"Current value: {slider}")
    
    # Simulate dragging from current position
    start_value = slider
    
    print("\n========== SIMULATING SLIDER DRAG ==========")
    print(f"Starting drag at value: 0x{start_value:06X}")
    
    # Simulate drag by changing values
    for i in range(5):
        new_value = start_value + (i * 0x1000)
        if new_value > slider.maximum():
            break
            
        print(f"\n--- Step {i+1}: Moving to 0x{new_value:06X} ---")
        slider.setValue(new_value)
        
        # Give Qt time to process events (but no processEvents!)
        QTimer.singleShot(100, lambda: None)
        time.sleep(0.1)  # Small delay between steps
    
    print("\n========== DRAG SIMULATION COMPLETE ==========")

def main():
    app = QApplication(sys.argv)
    
    # Initialize managers
    initialize_managers()
    
    # Create dialog
    print("Creating dialog...")
    dialog = UnifiedManualOffsetDialog()
    
    # Set a test ROM path if available
    test_rom = "Kirby Super Star (USA).sfc"
    if os.path.exists(test_rom):
        print(f"Loading ROM: {test_rom}")
        rom_size = os.path.getsize(test_rom)
        extraction_manager = get_extraction_manager()
        dialog.set_rom_data(test_rom, rom_size, extraction_manager)
    else:
        print("ERROR: Test ROM not found!")
        return 1
    
    # Show dialog
    dialog.show()
    
    # Simulate slider drag after a short delay
    QTimer.singleShot(1000, lambda: simulate_slider_drag(dialog))
    
    # Auto-close after 5 seconds to prevent hanging
    QTimer.singleShot(5000, app.quit)
    
    # Run the application
    return app.exec()

if __name__ == "__main__":
    sys.exit(main())