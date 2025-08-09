#!/usr/bin/env python3
"""
Test script to verify the timing issue in manual offset preview.
"""

import os
import sys
import time
from pathlib import Path

# Add the spritepal directory to Python path
spritepal_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(spritepal_dir))

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer

from core.managers.registry import ManagerRegistry
from ui.dialogs.manual_offset_unified_integrated import UnifiedManualOffsetDialog
from core.managers.extraction_manager import ExtractionManager


def test_timing_issue():
    """Test if there's a timing issue with ROM data setting."""
    # Find a test ROM file
    test_rom_path = None
    possible_roms = [
        "test_files/test.smc",
        "test_files/test.sfc", 
        "../test.smc",
        "../test.sfc"
    ]
    
    for rom_path in possible_roms:
        if os.path.exists(rom_path):
            test_rom_path = rom_path
            break
    
    if not test_rom_path:
        print("No test ROM file found. Creating mock ROM...")
        test_rom_path = "mock_test.smc"
        with open(test_rom_path, "wb") as f:
            f.write(b'\x00' * 0x200000)  # 2MB ROM
        print(f"Created mock ROM: {test_rom_path}")
    
    print(f"Using ROM file: {test_rom_path}")
    
    # Initialize manager registry
    ManagerRegistry.initialize()
    
    # Create dialog
    print("Creating dialog...")
    dialog = UnifiedManualOffsetDialog(parent=None)
    
    # Test 1: Check initial state (should be empty)
    print("\n=== Test 1: Initial state ===")
    rom_data = dialog._get_rom_data_for_preview()
    print(f"Initial ROM data: (rom_path={bool(rom_data[0])}, extractor={bool(rom_data[1])}, cache={bool(rom_data[2])})")
    
    # Test 2: Set ROM data and check immediately
    print("\n=== Test 2: Set ROM data and check immediately ===")
    extraction_manager = ExtractionManager()
    rom_size = os.path.getsize(test_rom_path)
    
    dialog.set_rom_data(test_rom_path, rom_size, extraction_manager)
    
    rom_data = dialog._get_rom_data_for_preview()
    print(f"After set_rom_data: (rom_path={bool(rom_data[0])}, extractor={bool(rom_data[1])}, cache={bool(rom_data[2])})")
    print(f"ROM path value: {repr(rom_data[0])}")
    
    # Test 3: Try triggering preview request
    print("\n=== Test 3: Try preview request ===")
    try:
        if hasattr(dialog, 'browse_tab') and dialog.browse_tab:
            if hasattr(dialog.browse_tab, 'position_slider'):
                slider = dialog.browse_tab.position_slider
                print(f"Found position_slider: {slider}")
                
                # Set a test offset
                test_offset = 0x8000
                slider.setValue(test_offset)
                
                # Process events to let signals propagate
                QApplication.processEvents()
                time.sleep(0.1)  # Give time for signals
                QApplication.processEvents()
                
                # Check ROM data again
                rom_data = dialog._get_rom_data_for_preview()
                print(f"After slider move: (rom_path={bool(rom_data[0])}, extractor={bool(rom_data[1])}, cache={bool(rom_data[2])})")
            else:
                print("No position_slider found in browse_tab")
        else:
            print("No browse_tab found")
    except Exception as e:
        print(f"Error testing preview: {e}")
    
    print("\n=== Test Complete ===")
    dialog.close()
    
    # Clean up mock ROM if created
    if test_rom_path == "mock_test.smc":
        os.unlink(test_rom_path)
        print("Cleaned up mock ROM")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # Use a timer to run the test after the event loop starts
    QTimer.singleShot(100, test_timing_issue)
    QTimer.singleShot(2000, app.quit)  # Quit after 2 seconds
    
    app.exec()