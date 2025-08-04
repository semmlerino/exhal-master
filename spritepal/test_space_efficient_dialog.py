#!/usr/bin/env python
"""
Test script to verify the space-efficient manual offset dialog layout.

This script creates and displays the dialog to verify:
1. Browse tab content fits within ~300px height
2. Status panel is collapsible and defaults to ~35px when collapsed
3. All controls are properly sized and visible
4. Dialog works at minimum size (800x500)
"""

import sys
import os
from pathlib import Path

# Add the spritepal directory to Python path
spritepal_dir = Path(__file__).parent
sys.path.insert(0, str(spritepal_dir))

try:
    from PyQt6.QtWidgets import QApplication, QVBoxLayout, QLabel, QWidget
    from PyQt6.QtCore import Qt
    from ui.dialogs.manual_offset_unified_integrated import UnifiedManualOffsetDialog
    
    def test_dialog_sizing():
        """Test the dialog sizing and layout."""
        app = QApplication(sys.argv)
        
        # Create the dialog
        dialog = UnifiedManualOffsetDialog()
        
        # Show the dialog
        dialog.show()
        
        # Print sizing information
        print("=== Dialog Size Information ===")
        print(f"Dialog size: {dialog.size().width()}x{dialog.size().height()}")
        print(f"Minimum size: {dialog.minimumSize().width()}x{dialog.minimumSize().height()}")
        
        # Check tab widget sizing
        if dialog.tab_widget:
            tab_size = dialog.tab_widget.size()
            print(f"Tab widget size: {tab_size.width()}x{tab_size.height()}")
            
            # Check browse tab content
            if dialog.browse_tab:
                browse_hint = dialog.browse_tab.sizeHint()
                print(f"Browse tab size hint: {browse_hint.width()}x{browse_hint.height()}")
        
        # Check status panel sizing
        if dialog.status_collapsible:
            status_size = dialog.status_collapsible.size()
            status_hint = dialog.status_collapsible.sizeHint()
            is_collapsed = dialog.status_collapsible.is_collapsed()
            print(f"Status panel size: {status_size.width()}x{status_size.height()}")
            print(f"Status panel size hint: {status_hint.width()}x{status_hint.height()}")
            print(f"Status panel collapsed: {is_collapsed}")
        
        # Set to minimum size to test constraints
        dialog.resize(800, 500)
        app.processEvents()  # Force layout update
        
        print("\n=== After resize to minimum (800x500) ===")
        print(f"Actual dialog size: {dialog.size().width()}x{dialog.size().height()}")
        
        if dialog.tab_widget:
            tab_size = dialog.tab_widget.size()
            print(f"Tab widget size: {tab_size.width()}x{tab_size.height()}")
        
        # Test expanding status panel
        if dialog.status_collapsible:
            print("\n=== Testing status panel expansion ===")
            dialog.status_collapsible.set_collapsed(False)
            app.processEvents()
            
            expanded_size = dialog.status_collapsible.size()
            expanded_hint = dialog.status_collapsible.sizeHint()
            print(f"Status panel expanded size: {expanded_size.width()}x{expanded_size.height()}")
            print(f"Status panel expanded hint: {expanded_hint.width()}x{expanded_hint.height()}")
            
            # Collapse it again
            dialog.status_collapsible.set_collapsed(True)
            app.processEvents()
            
            collapsed_size = dialog.status_collapsible.size()
            print(f"Status panel collapsed size: {collapsed_size.width()}x{collapsed_size.height()}")
        
        print("\n=== Layout Test Complete ===")
        print("Dialog is ready for interactive testing.")
        print("- Browse tab should fit comfortably in available space")
        print("- Status panel should be collapsed by default")
        print("- All controls should be visible and functional")
        print("- Dialog should work properly at 800x500 minimum size")
        
        # Run the application for interactive testing
        return app.exec()
    
    if __name__ == "__main__":
        sys.exit(test_dialog_sizing())
        
except ImportError as e:
    print(f"Import error: {e}")
    print("Make sure you're running this from the spritepal directory with all dependencies installed.")
    sys.exit(1)
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)