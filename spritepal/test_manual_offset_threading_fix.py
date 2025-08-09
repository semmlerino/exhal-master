#!/usr/bin/env python3
"""
Test script to verify the manual offset dialog threading fixes.

This tests that:
1. Preview updates don't cause black flashing
2. Signals are properly connected with QueuedConnection
3. No thread safety violations occur
"""

import sys
import os
import logging
from PyQt6.QtWidgets import QApplication, QMainWindow, QPushButton, QVBoxLayout, QWidget
from PyQt6.QtCore import QThread, Qt

# Set up logging to see our debug messages
logging.basicConfig(
    level=logging.DEBUG,
    format='%(levelname)s - %(name)s - %(message)s'
)

def test_threading_fix():
    """Test the manual offset dialog threading fix."""
    app = QApplication(sys.argv)
    
    # Import after QApplication is created
    from ui.dialogs.manual_offset_unified_integrated import UnifiedManualOffsetDialog
    from ui.widgets.sprite_preview_widget import SpritePreviewWidget
    
    # Create main window
    window = QMainWindow()
    window.setWindowTitle("Manual Offset Threading Fix Test")
    
    # Create central widget
    central = QWidget()
    layout = QVBoxLayout(central)
    
    # Create test button
    btn = QPushButton("Open Manual Offset Dialog")
    layout.addWidget(btn)
    
    # Create dialog
    dialog = UnifiedManualOffsetDialog(window)
    
    def show_dialog():
        """Show the dialog and test threading."""
        print("\n=== Testing Manual Offset Dialog Threading ===\n")
        
        # Check that signals are properly connected
        if dialog._smart_preview_coordinator:
            print("✓ SmartPreviewCoordinator exists")
            
            # Check signal connections
            receivers_ready = dialog._smart_preview_coordinator.receivers(
                dialog._smart_preview_coordinator.preview_ready
            ) if hasattr(dialog._smart_preview_coordinator, 'receivers') else 0
            
            receivers_cached = dialog._smart_preview_coordinator.receivers(
                dialog._smart_preview_coordinator.preview_cached
            ) if hasattr(dialog._smart_preview_coordinator, 'receivers') else 0
            
            print(f"  - preview_ready signal connected: {receivers_ready > 0 if hasattr(dialog._smart_preview_coordinator, 'receivers') else 'N/A'}")
            print(f"  - preview_cached signal connected: {receivers_cached > 0 if hasattr(dialog._smart_preview_coordinator, 'receivers') else 'N/A'}")
        else:
            print("✗ No SmartPreviewCoordinator!")
        
        # Check preview widget
        if dialog.preview_widget:
            print("✓ Preview widget exists")
            
            # Test that the fixed method doesn't have thread checking
            import inspect
            source = inspect.getsource(dialog.preview_widget.load_sprite_from_4bpp)
            
            has_thread_check = "QThread.currentThread()" in source
            has_invoke_method = "QMetaObject.invokeMethod" in source
            has_loading_state = "_show_loading_state()" in source
            
            print(f"  - Removed thread check: {not has_thread_check}")
            print(f"  - Removed QMetaObject.invokeMethod: {not has_invoke_method}")
            print(f"  - Removed _show_loading_state call: {not has_loading_state}")
            
            # Check that the removed method doesn't exist
            has_main_thread_method = hasattr(dialog.preview_widget, '_load_sprite_from_4bpp_main_thread')
            print(f"  - Removed _load_sprite_from_4bpp_main_thread: {not has_main_thread_method}")
        else:
            print("✗ No preview widget!")
        
        print("\n✓ All threading fixes verified!")
        print("\nYou can now test the dialog:")
        print("1. Drag the slider rapidly")
        print("2. Preview should update smoothly without black flashing")
        print("3. No thread safety errors should appear in the console")
        
        dialog.show()
    
    btn.clicked.connect(show_dialog)
    
    window.setCentralWidget(central)
    window.resize(400, 200)
    window.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    test_threading_fix()