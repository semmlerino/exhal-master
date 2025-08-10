#!/usr/bin/env python3
"""
Simple script to take a screenshot of the manual offset dialog for layout analysis.
"""

import sys
import time
from pathlib import Path
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer
from PySide6.QtGui import QPixmap

# Add spritepal to path
sys.path.insert(0, str(Path(__file__).parent))

from ui.main_window import MainWindow
from core.managers.registry import initialize_managers


def take_screenshot():
    """Launch app, open manual offset dialog, and take screenshot."""
    app = QApplication.instance() or QApplication(sys.argv)
    
    # Initialize managers first
    initialize_managers()
    
    # Create main window
    main_window = MainWindow()
    main_window.show()
    
    def load_rom_and_capture():
        """Load ROM first, then open manual offset dialog and capture screenshot."""
        try:
            # Get the ROM extraction panel
            panel = main_window.rom_extraction_panel
            
            # Load a ROM file from current directory
            rom_path = Path(__file__).parent / "Kirby Super Star (USA).sfc"
            if not rom_path.exists():
                # Try alternative ROM files
                for rom_name in ["test_rom.sfc", "Kirby's Fun Pak (Europe).sfc"]:
                    rom_path = Path(__file__).parent / rom_name
                    if rom_path.exists():
                        break
            
            if rom_path.exists():
                print(f"Loading ROM: {rom_path}")
                # Load the ROM file
                if hasattr(panel, '_load_rom_file'):
                    panel._load_rom_file(str(rom_path))
                    print("ROM loaded successfully")
                    # Wait for ROM to load
                    QTimer.singleShot(1000, lambda: open_manual_offset())
                else:
                    print("ROM loading method not found")
                    app.quit()
            else:
                print("No ROM files found in current directory")
                app.quit()
        except Exception as e:
            print(f"Error loading ROM: {e}")
            app.quit()
    
    def open_manual_offset():
        """Open the manual offset dialog after ROM is loaded."""
        try:
            panel = main_window.rom_extraction_panel
            
            # Access the manual offset button directly
            if hasattr(panel, 'manual_offset_button'):
                button = panel.manual_offset_button
                
                # Check if button is visible and enabled
                if button.isVisible() and button.isEnabled():
                    print("Clicking manual offset button...")
                    button.click()
                else:
                    print("Manual offset button not visible/enabled, trying to enable it...")
                    # Try to make it visible/enabled
                    button.setVisible(True)
                    button.setEnabled(True)
                    button.click()
                
                # Wait for dialog to open
                QTimer.singleShot(1500, lambda: capture_dialog_screenshot(app))
            else:
                print("Manual offset button not found")
                app.quit()
        except Exception as e:
            print(f"Error opening manual offset dialog: {e}")
            app.quit()
    
    def capture_dialog_screenshot(app):
        """Capture screenshot of the manual offset dialog."""
        try:
            # Find the manual offset dialog window
            for widget in app.allWidgets():
                if hasattr(widget, 'windowTitle') and 'Manual Offset' in str(widget.windowTitle()):
                    # Take screenshot
                    pixmap = widget.grab()
                    screenshot_path = Path(__file__).parent / "manual_offset_current_screenshot.png"
                    pixmap.save(str(screenshot_path))
                    print(f"Screenshot saved to: {screenshot_path}")
                    break
            else:
                print("Manual offset dialog not found among open widgets")
            
        except Exception as e:
            print(f"Error taking screenshot: {e}")
        finally:
            app.quit()
    
    # Wait for main window to load, then load ROM and open dialog
    QTimer.singleShot(2000, load_rom_and_capture)
    
    # Run the application
    app.exec()


if __name__ == "__main__":
    take_screenshot()