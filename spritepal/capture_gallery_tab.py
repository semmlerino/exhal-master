#!/usr/bin/env python3
"""
Script to capture a screenshot of the Gallery tab using Qt's built-in functionality.
Works with xvfb for headless environments.
"""

import sys
import time
from pathlib import Path

from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QApplication

# Add parent directory to path to import SpritePal modules
sys.path.insert(0, str(Path(__file__).parent))

from ui.dialogs.manual_offset_unified_integrated import UnifiedManualOffsetDialog
from utils.logging_config import get_logger

logger = get_logger(__name__)

def capture_gallery_tab():
    """Capture a screenshot of the Gallery tab."""
    app = QApplication.instance() or QApplication(sys.argv)
    
    # Create the manual offset dialog
    dialog = UnifiedManualOffsetDialog()
    dialog.resize(1000, 700)  # Set a good size for the screenshot
    
    # Switch to Gallery tab
    if dialog.tab_widget:
        for i in range(dialog.tab_widget.count()):
            if dialog.tab_widget.tabText(i) == "Gallery":
                dialog.tab_widget.setCurrentIndex(i)
                print(f"Switched to Gallery tab (index {i})")
                break
    
    # Show the dialog
    dialog.show()
    
    def take_screenshot():
        """Take the screenshot after a delay to ensure rendering is complete."""
        try:
            # Use Qt's grab() method which works in headless environments
            pixmap = dialog.grab()
            
            # Save the screenshot
            output_path = Path("/tmp/gallery_tab_screenshot.png")
            if pixmap.save(str(output_path), "PNG"):
                print(f"✓ Screenshot saved to: {output_path}")
                
                # Also try to save to a Windows-accessible location
                try:
                    windows_path = Path("/mnt/c/temp/gallery_tab_screenshot.png")
                    windows_path.parent.mkdir(parents=True, exist_ok=True)
                    if pixmap.save(str(windows_path), "PNG"):
                        print(f"✓ Also saved to Windows path: {windows_path}")
                except Exception as e:
                    print(f"Note: Could not save to Windows path: {e}")
                
                # Save a second screenshot focused on just the gallery tab widget
                if dialog.gallery_tab:
                    tab_pixmap = dialog.gallery_tab.grab()
                    tab_output = Path("/tmp/gallery_tab_widget.png")
                    if tab_pixmap.save(str(tab_output), "PNG"):
                        print(f"✓ Gallery tab widget saved to: {tab_output}")
            else:
                print("✗ Failed to save screenshot")
                
        except Exception as e:
            print(f"✗ Error taking screenshot: {e}")
            logger.error(f"Screenshot error: {e}")
        finally:
            # Exit after screenshot
            app.quit()
    
    # Take screenshot after a short delay to ensure rendering
    QTimer.singleShot(1000, take_screenshot)
    
    # Run the application
    return app.exec()

if __name__ == "__main__":
    sys.exit(capture_gallery_tab())