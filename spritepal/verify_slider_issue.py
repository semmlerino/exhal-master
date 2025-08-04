#!/usr/bin/env python3
"""
Verify the duplicate slider issue by checking all sliders in the application.
This will help determine if the user is seeing:
1. Two sliders in the manual offset dialog
2. The VRAM extraction slider + manual offset dialog slider
3. Or some other configuration issue
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PyQt6.QtWidgets import QApplication, QSlider, QWidget
from PyQt6.QtCore import QTimer

def find_all_sliders(widget, path=""):
    """Recursively find all QSlider instances in the widget tree."""
    sliders = []
    
    # Check if this widget is a slider
    if isinstance(widget, QSlider):
        parent_info = ""
        if widget.parent():
            parent_info = f" (parent: {widget.parent().__class__.__name__})"
        
        sliders.append({
            'widget': widget,
            'path': path,
            'parent_info': parent_info,
            'visible': widget.isVisible(),
            'value': widget.value(),
            'range': (widget.minimum(), widget.maximum())
        })
    
    # Recursively check children
    for child in widget.findChildren(QWidget):
        # Skip if we've already processed this widget
        if child.parent() == widget:
            child_path = f"{path}/{child.__class__.__name__}"
            if hasattr(child, 'objectName') and child.objectName():
                child_path += f"[{child.objectName()}]"
            sliders.extend(find_all_sliders(child, child_path))
    
    return sliders

def check_sliders():
    """Check all sliders in the application."""
    print("\n" + "="*60)
    print("SLIDER AUDIT REPORT")
    print("="*60)
    
    # Get all top-level widgets
    for window in QApplication.topLevelWidgets():
        if not window.isVisible():
            continue
            
        print(f"\nWindow: {window.__class__.__name__} - {window.windowTitle()}")
        print("-" * 40)
        
        sliders = find_all_sliders(window, window.__class__.__name__)
        
        if not sliders:
            print("  No sliders found")
        else:
            print(f"  Found {len(sliders)} slider(s):")
            for i, slider_info in enumerate(sliders, 1):
                print(f"\n  Slider {i}:")
                print(f"    Path: {slider_info['path']}")
                print(f"    Parent: {slider_info['parent_info']}")
                print(f"    Visible: {slider_info['visible']}")
                print(f"    Value: {slider_info['value']}")
                print(f"    Range: {slider_info['range'][0]} - {slider_info['range'][1]}")
    
    print("\n" + "="*60)
    print("SUMMARY:")
    total_sliders = sum(len(find_all_sliders(w)) for w in QApplication.topLevelWidgets() if w.isVisible())
    print(f"Total visible sliders in application: {total_sliders}")
    print("="*60 + "\n")

if __name__ == "__main__":
    # Import and initialize managers
    from core.managers import initialize_managers
    initialize_managers()
    
    app = QApplication(sys.argv)
    
    # Create main window
    from ui.main_window import MainWindow
    window = MainWindow()
    window.show()
    
    # Load a test ROM to enable manual offset dialog
    test_rom = "/mnt/c/CustomScripts/KirbyMax/workshop/exhal-master/spritepal/tests/fixtures/test_rom.sfc"
    if os.path.exists(test_rom):
        window.rom_extraction_panel._load_rom_file(test_rom)
    
    # Initial check
    QTimer.singleShot(500, check_sliders)
    
    # Open manual offset dialog after a delay
    def open_manual_dialog():
        print("\n>>> OPENING MANUAL OFFSET DIALOG...")
        window.rom_extraction_panel._open_manual_offset_dialog()
        QTimer.singleShot(500, check_sliders)
    
    QTimer.singleShot(1000, open_manual_dialog)
    
    # Switch to VRAM tab to show that slider too
    def switch_to_vram_tab():
        print("\n>>> SWITCHING TO VRAM TAB...")
        window.extraction_tabs.setCurrentIndex(1)
        QTimer.singleShot(500, check_sliders)
    
    QTimer.singleShot(3000, switch_to_vram_tab)
    
    # Exit after analysis
    QTimer.singleShot(5000, app.quit)
    
    sys.exit(app.exec())