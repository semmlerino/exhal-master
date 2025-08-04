#!/usr/bin/env python3
"""Test to verify that duplicate slider issue is fixed."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PyQt6.QtWidgets import QApplication, QSlider
from PyQt6.QtCore import QTimer

def test_no_duplicate_sliders():
    """Test that there are no duplicate sliders."""
    from core.managers import initialize_managers
    initialize_managers()
    
    app = QApplication(sys.argv)
    
    # Create main window
    from ui.main_window import MainWindow
    window = MainWindow()
    window.show()
    
    # Load test ROM
    test_rom = "/mnt/c/CustomScripts/KirbyMax/workshop/exhal-master/spritepal/tests/fixtures/test_rom.sfc"
    if os.path.exists(test_rom):
        window.rom_extraction_panel._load_rom_file(test_rom)
    
    def check_sliders():
        print("\n=== SLIDER CHECK ===")
        
        # Check all sliders in the application
        all_sliders = []
        for widget in QApplication.topLevelWidgets():
            if widget.isVisible():
                sliders = widget.findChildren(QSlider)
                for slider in sliders:
                    all_sliders.append({
                        'object_name': slider.objectName() or 'unnamed',
                        'parent': slider.parent().__class__.__name__,
                        'window': widget.windowTitle(),
                        'visible': slider.isVisible()
                    })
        
        print(f"Total sliders found: {len(all_sliders)}")
        for i, slider_info in enumerate(all_sliders, 1):
            print(f"\nSlider {i}:")
            print(f"  Object Name: {slider_info['object_name']}")
            print(f"  Parent: {slider_info['parent']}")
            print(f"  Window: {slider_info['window']}")
            print(f"  Visible: {slider_info['visible']}")
        
        # Check specific sliders
        vram_sliders = [s for s in all_sliders if 'vram' in s['object_name'].lower()]
        rom_sliders = [s for s in all_sliders if 'rom' in s['object_name'].lower() or 'manual' in s['object_name'].lower()]
        
        print(f"\nVRAM sliders: {len(vram_sliders)}")
        print(f"ROM/Manual offset sliders: {len(rom_sliders)}")
        
        # Verify expectations
        visible_sliders = [s for s in all_sliders if s['visible']]
        print(f"\nVisible sliders: {len(visible_sliders)}")
        
        # Check for duplicates
        if len(rom_sliders) > 1:
            print("\n⚠️ WARNING: Multiple ROM/Manual offset sliders detected!")
        else:
            print("\n✅ No duplicate ROM/Manual offset sliders")
        
        return all_sliders
    
    # Initial check
    QTimer.singleShot(500, check_sliders)
    
    # Open manual offset dialog
    def test_manual_dialog():
        print("\n>>> Opening Manual Offset Dialog...")
        window.rom_extraction_panel._open_manual_offset_dialog()
        QTimer.singleShot(500, lambda: check_and_close())
    
    def check_and_close():
        sliders = check_sliders()
        
        # Get the manual offset dialog
        from ui.rom_extraction_panel import ManualOffsetDialogSingleton
        dialog = ManualOffsetDialogSingleton.get_current_dialog()
        
        if dialog:
            print(f"\nManual Offset Dialog is open: {dialog.isVisible()}")
            print(f"Dialog ID: {getattr(dialog, '_debug_id', 'Unknown')}")
            
            # Check sliders in the dialog specifically
            dialog_sliders = dialog.findChildren(QSlider)
            print(f"Sliders in Manual Offset Dialog: {len(dialog_sliders)}")
            for i, slider in enumerate(dialog_sliders, 1):
                print(f"  Dialog Slider {i}: {slider.objectName() or 'unnamed'}")
        
        # Close after check
        QTimer.singleShot(1000, app.quit)
    
    QTimer.singleShot(1000, test_manual_dialog)
    
    sys.exit(app.exec())

if __name__ == "__main__":
    test_no_duplicate_sliders()