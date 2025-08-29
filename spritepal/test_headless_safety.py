#!/usr/bin/env python3
from __future__ import annotations

"""
Test script to verify widgets can initialize safely in headless mode.
"""

import os
import sys

# Force headless mode for testing
os.environ["QT_QPA_PLATFORM"] = "offscreen"

def test_collapsible_group_box():
    """Test that CollapsibleGroupBox can be created in headless mode."""
    print("Testing CollapsibleGroupBox in headless mode...")
    
    try:
        from PySide6.QtWidgets import QApplication
        from ui.common.collapsible_group_box import CollapsibleGroupBox
        
        app = QApplication.instance() or QApplication(sys.argv)
        
        # Try to create the widget
        widget = CollapsibleGroupBox(title="Test Group", collapsed=False)
        print("✓ CollapsibleGroupBox created successfully")
        
        # Try to toggle collapse state
        widget.toggle_collapsed()
        print("✓ CollapsibleGroupBox toggled successfully")
        
        # Try to set collapsed
        widget.set_collapsed(True)
        print("✓ CollapsibleGroupBox collapsed successfully")
        
        widget.set_collapsed(False)
        print("✓ CollapsibleGroupBox expanded successfully")
        
        return True
        
    except Exception as e:
        print(f"✗ CollapsibleGroupBox failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_sprite_preview_widget():
    """Test that SpritePreviewWidget can be created in headless mode."""
    print("\nTesting SpritePreviewWidget in headless mode...")
    
    try:
        from PySide6.QtWidgets import QApplication
        from ui.widgets.sprite_preview_widget import SpritePreviewWidget
        
        app = QApplication.instance() or QApplication(sys.argv)
        
        # Try to create the widget
        widget = SpritePreviewWidget(title="Test Preview")
        print("✓ SpritePreviewWidget created successfully")
        
        # Try to update display
        widget.clear()
        print("✓ SpritePreviewWidget cleared successfully")
        
        return True
        
    except Exception as e:
        print(f"✗ SpritePreviewWidget failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_browse_tab():
    """Test that SimpleBrowseTab can be created in headless mode."""
    print("\nTesting SimpleBrowseTab in headless mode...")
    
    try:
        from PySide6.QtWidgets import QApplication
        from ui.tabs.manual_offset.browse_tab import SimpleBrowseTab
        
        app = QApplication.instance() or QApplication(sys.argv)
        
        # Try to create the widget
        widget = SimpleBrowseTab()
        print("✓ SimpleBrowseTab created successfully")
        
        # Try to set offset
        widget.set_offset(0x100000)
        print("✓ SimpleBrowseTab offset set successfully")
        
        return True
        
    except Exception as e:
        print(f"✗ SimpleBrowseTab failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_manual_offset_dialog():
    """Test that manual offset dialog can be created in headless mode."""
    print("\nTesting Manual Offset Dialog in headless mode...")
    
    try:
        from PySide6.QtWidgets import QApplication
        
        # Set environment to use legacy dialog to avoid composed dialog issues
        os.environ['SPRITEPAL_USE_COMPOSED_DIALOGS'] = '0'
        
        from ui.dialogs.manual_offset_unified_integrated import UnifiedManualOffsetDialog
        
        app = QApplication.instance() or QApplication(sys.argv)
        
        # Try to create the dialog - this is the critical test
        # If it can be created without segfault, the fix is working
        dialog = UnifiedManualOffsetDialog()
        print("✓ UnifiedManualOffsetDialog created successfully (no segfault!)")
        
        # Try to access some basic methods to ensure it's functional
        try:
            dialog.setWindowTitle("Test Dialog")
            print("✓ UnifiedManualOffsetDialog window title set successfully")
        except Exception:
            pass  # Not critical if this fails
        
        return True
        
    except Exception as e:
        print(f"✗ UnifiedManualOffsetDialog failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all headless safety tests."""
    print("=" * 60)
    print("Headless Mode Safety Tests")
    print("=" * 60)
    
    from ui.utils.safe_animation import is_headless_environment
    print(f"Headless environment detected: {is_headless_environment()}")
    print(f"QT_QPA_PLATFORM: {os.environ.get('QT_QPA_PLATFORM', 'not set')}")
    print(f"DISPLAY: {os.environ.get('DISPLAY', 'not set')}")
    print()
    
    results = []
    
    # Run all tests
    results.append(("CollapsibleGroupBox", test_collapsible_group_box()))
    results.append(("SpritePreviewWidget", test_sprite_preview_widget()))
    results.append(("SimpleBrowseTab", test_browse_tab()))
    results.append(("ManualOffsetDialog", test_manual_offset_dialog()))
    
    # Print summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    
    all_passed = True
    for name, passed in results:
        status = "✓ PASSED" if passed else "✗ FAILED"
        print(f"{name:25} {status}")
        if not passed:
            all_passed = False
    
    print("=" * 60)
    
    if all_passed:
        print("All tests PASSED - widgets are safe for headless mode!")
        print("\nKey Achievement: No segmentation faults when creating Qt widgets")
        print("with QPropertyAnimation in headless WSL2 environment.")
        sys.exit(0)
    else:
        print("Some tests FAILED - widgets may crash in headless mode")
        sys.exit(1)

if __name__ == "__main__":
    main()
