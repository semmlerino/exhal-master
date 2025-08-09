#!/usr/bin/env python3
"""
Test script to verify manual offset slider preview functionality.
This script can be run at any git commit to check if the preview works.
"""
import sys
import os
import tempfile
import subprocess
from pathlib import Path
from PyQt6.QtWidgets import QApplication, QVBoxLayout, QWidget, QPushButton, QLabel
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QPixmap

# Add the spritepal directory to sys.path
spritepal_dir = Path(__file__).parent
sys.path.insert(0, str(spritepal_dir))

def test_manual_offset_preview(rom_path: str = None) -> bool:
    """
    Test if manual offset preview is working.
    Returns True if working, False if broken.
    """
    try:
        # Try to import the necessary components - handle different versions
        dialog_class = None
        try:
            from ui.dialogs.manual_offset_unified_integrated import UnifiedManualOffsetDialog
            dialog_class = UnifiedManualOffsetDialog
            print("✓ Successfully imported UnifiedManualOffsetDialog")
        except ImportError:
            try:
                from ui.dialogs.manual_offset_dialog import ManualOffsetDialog
                dialog_class = ManualOffsetDialog  
                print("✓ Successfully imported ManualOffsetDialog (older version)")
            except ImportError:
                # Try with spritepal prefix
                try:
                    from spritepal.ui.dialogs.manual_offset_dialog import ManualOffsetDialog
                    dialog_class = ManualOffsetDialog
                    print("✓ Successfully imported ManualOffsetDialog (with spritepal prefix)")
                except ImportError:
                    print("✗ Could not import any manual offset dialog")
                    return False
        
        if not dialog_class:
            return False
        
        if not rom_path:
            # Create a minimal test ROM or use existing one
            test_roms = [
                "/tmp/test.smc",
                "test_data/test.smc",
                "../test_roms/test.smc"
            ]
            
            for test_rom in test_roms:
                if os.path.exists(test_rom):
                    rom_path = test_rom
                    break
            
            if not rom_path:
                print("⚠ No test ROM found, creating minimal test")
                # Create minimal ROM for testing
                rom_path = "/tmp/minimal_test.smc"
                with open(rom_path, "wb") as f:
                    # Create minimal SNES ROM structure (1MB)
                    f.write(b'\x00' * (1024 * 1024))
        
        print(f"✓ Using ROM: {rom_path}")
        
        # Try to create the manual offset dialog
        app = QApplication.instance()
        if not app:
            app = QApplication(sys.argv)
        
        # Try to initialize the session manager if available
        try:
            try:
                from core.managers.registry import ManagerRegistry
                registry_path = "core.managers.registry"
            except ImportError:
                from spritepal.core.managers.registry import ManagerRegistry
                registry_path = "spritepal.core.managers.registry"
            
            print(f"✓ Attempting to initialize managers from {registry_path}")
            registry = ManagerRegistry()
            registry.initialize_managers("SpritePalTest")
            print("✓ Managers initialized")
        except Exception as e:
            print(f"⚠ Could not initialize managers: {e}")
            print("Continuing with test anyway...")
        
        dialog = dialog_class()
        print("✓ Manual offset dialog created")
        
        # Check if preview widget exists and is properly connected
        if hasattr(dialog, 'preview_widget'):
            print("✓ Preview widget found")
            
            # Debug: List all attributes that contain 'slider'
            slider_attrs = [attr for attr in dir(dialog) if 'slider' in attr.lower()]
            print(f"Debug: Found slider-related attributes: {slider_attrs}")
            
            # Also check tab structure
            if hasattr(dialog, 'browse_tab'):
                browse_slider_attrs = [attr for attr in dir(dialog.browse_tab) if 'slider' in attr.lower()]
                print(f"Debug: Browse tab slider attributes: {browse_slider_attrs}")
            
            # Test if slider updates trigger preview updates
            slider_attr = None
            if hasattr(dialog, 'position_slider'):
                slider_attr = 'position_slider'
                print("✓ Position slider found (dialog level)")
            elif hasattr(dialog, 'browse_tab') and hasattr(dialog.browse_tab, 'position_slider'):
                slider_attr = 'browse_tab.position_slider'
                print("✓ Position slider found (browse tab level)")
            
            if slider_attr:
                # Get the actual slider object
                if slider_attr == 'position_slider':
                    slider = dialog.position_slider
                elif slider_attr == 'browse_tab.position_slider':
                    slider = dialog.browse_tab.position_slider
                else:
                    print("✗ Unknown slider attribute format - BROKEN")
                    return False
                
                # Simulate slider value change
                original_offset = slider.value()
                test_offset = original_offset + 100
                
                print(f"Testing slider change: {original_offset} -> {test_offset}")
                
                # Check if preview updates when slider changes
                slider.setValue(test_offset)
                
                # Give some time for signals to process
                app.processEvents()
                
                # Check if preview has content (not just black)
                if hasattr(dialog.preview_widget, 'pixmap') and dialog.preview_widget.pixmap():
                    pixmap = dialog.preview_widget.pixmap()
                    if not pixmap.isNull():
                        print("✓ Preview pixmap is not null")
                        
                        # Check if pixmap has actual content (not all black)
                        image = pixmap.toImage()
                        has_non_black_pixels = False
                        
                        # Sample a few pixels to check for content
                        width = min(image.width(), 16)
                        height = min(image.height(), 16)
                        
                        for x in range(0, width, 2):
                            for y in range(0, height, 2):
                                pixel = image.pixel(x, y)
                                # Check if pixel is not black (allows for transparency)
                                if pixel != 0 and (pixel & 0xFF000000) != 0:
                                    has_non_black_pixels = True
                                    break
                            if has_non_black_pixels:
                                break
                        
                        if has_non_black_pixels:
                            print("✓ Preview has non-black content - WORKING!")
                            return True
                        else:
                            print("✗ Preview is all black - BROKEN")
                            return False
                    else:
                        print("✗ Preview pixmap is null - BROKEN")
                        return False
                else:
                    print("✗ Preview widget has no pixmap - BROKEN")
                    return False
            else:
                print("✗ Position slider not found at any level - BROKEN")
                return False
        else:
            print("✗ Preview widget not found - BROKEN")
            return False
            
    except ImportError as e:
        print(f"✗ Import error: {e} - Cannot test at this commit")
        return False
    except Exception as e:
        print(f"✗ Error during testing: {e} - BROKEN")
        return False

def get_current_commit() -> str:
    """Get the current git commit hash."""
    try:
        result = subprocess.run(['git', 'rev-parse', '--short', 'HEAD'], 
                              capture_output=True, text=True, check=True)
        return result.stdout.strip()
    except subprocess.CalledProcessError:
        return "unknown"

def main():
    """Main test function."""
    current_commit = get_current_commit()
    print(f"Testing manual offset preview at commit: {current_commit}")
    print("-" * 60)
    
    # Initialize Qt application
    app = QApplication(sys.argv)
    
    # Run the test
    is_working = test_manual_offset_preview()
    
    print("-" * 60)
    if is_working:
        print(f"✓ RESULT: Manual offset preview is WORKING at commit {current_commit}")
        sys.exit(0)
    else:
        print(f"✗ RESULT: Manual offset preview is BROKEN at commit {current_commit}")
        sys.exit(1)

if __name__ == "__main__":
    main()