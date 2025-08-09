#!/usr/bin/env python3
"""
Simplified test script to verify ROM data setting in manual offset dialog.
"""

import os
import sys
from pathlib import Path

# Add the spritepal directory to Python path
spritepal_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(spritepal_dir))

# Set up headless Qt environment
os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PyQt6.QtWidgets import QApplication

# Initialize ManagerRegistry properly
from core.managers.registry import initialize_managers
initialize_managers()

from ui.dialogs.manual_offset_unified_integrated import UnifiedManualOffsetDialog
from core.managers.extraction_manager import ExtractionManager


def main():
    """Test ROM data setting."""
    app = QApplication(sys.argv)
    
    # Create mock ROM file
    test_rom_path = "mock_test.smc"
    with open(test_rom_path, "wb") as f:
        f.write(b'\x00' * 0x200000)  # 2MB ROM
    
    try:
        print(f"Using ROM file: {test_rom_path}")
        
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
        
        print(f"Setting ROM data: path={test_rom_path}, size={rom_size}")
        dialog.set_rom_data(test_rom_path, rom_size, extraction_manager)
        
        rom_data = dialog._get_rom_data_for_preview()
        print(f"After set_rom_data: (rom_path={bool(rom_data[0])}, extractor={bool(rom_data[1])}, cache={bool(rom_data[2])})")
        
        if rom_data[0]:
            print(f"ROM path value: {rom_data[0]}")
        else:
            print("ROM path is empty/None")
            
        if rom_data[1]:
            print(f"ROM extractor type: {type(rom_data[1])}")
        else:
            print("ROM extractor is empty/None")
            
        print(f"ROM cache available: {rom_data[2] is not None}")
        
        # Test 3: Try to manually trigger a preview request
        print("\n=== Test 3: Manual preview request ===")
        try:
            # Check if smart preview coordinator is available
            if hasattr(dialog, '_smart_preview_coordinator'):
                coordinator = dialog._smart_preview_coordinator
                print(f"Smart preview coordinator: {coordinator}")
                
                # Try requesting a preview
                test_offset = 0x8000
                coordinator.request_preview(test_offset, priority=10)
                print(f"Requested preview for offset 0x{test_offset:X}")
                
                # Process events
                app.processEvents()
                
            else:
                print("No smart preview coordinator found")
        
        except Exception as e:
            print(f"Error testing preview: {e}")
            import traceback
            traceback.print_exc()
        
        print("\n=== Test Complete ===")
        dialog.close()
        
    finally:
        # Clean up mock ROM
        if os.path.exists(test_rom_path):
            os.unlink(test_rom_path)
            print("Cleaned up mock ROM")


if __name__ == "__main__":
    main()