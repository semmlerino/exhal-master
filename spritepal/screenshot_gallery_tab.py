#!/usr/bin/env python3
from __future__ import annotations

"""
Script to launch SpritePal, open manual offset dialog, switch to Gallery tab and take a screenshot.
"""

import sys
from pathlib import Path

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication, QMessageBox

# Add parent directory to path to import SpritePal modules
sys.path.insert(0, str(Path(__file__).parent))

from ui.main_window import MainWindow
from utils.logging_config import get_logger

logger = get_logger(__name__)

def take_screenshot_of_gallery():
    """Take a screenshot of the Gallery tab in the manual offset dialog."""
    app = QApplication.instance() or QApplication(sys.argv)

    # Create and show main window
    main_window = MainWindow()
    main_window.show()

    def open_manual_offset_and_screenshot():
        """Open manual offset dialog and switch to Gallery tab."""
        try:
            # Find the extraction panel
            extraction_panel = main_window.extraction_panel
            if not extraction_panel:
                logger.error("Could not find extraction panel")
                QMessageBox.critical(None, "Error", "Could not find extraction panel")
                app.quit()
                return

            # Open manual offset dialog
            extraction_panel._open_manual_offset_dialog()

            # Get the dialog
            from ui.dialogs.manual_offset_unified_integrated import (
                UnifiedManualOffsetDialog,
            )
            dialogs = [w for w in app.topLevelWidgets() if isinstance(w, UnifiedManualOffsetDialog)]

            if not dialogs:
                logger.error("Manual offset dialog not found")
                QMessageBox.critical(None, "Error", "Could not open manual offset dialog")
                app.quit()
                return

            dialog = dialogs[0]

            # Switch to Gallery tab
            if dialog.tab_widget:
                # Find Gallery tab index
                for i in range(dialog.tab_widget.count()):
                    if dialog.tab_widget.tabText(i) == "Gallery":
                        dialog.tab_widget.setCurrentIndex(i)
                        break

                # Give UI time to update
                QTimer.singleShot(500, lambda: capture_screenshot(dialog))
            else:
                logger.error("Tab widget not found in dialog")
                QMessageBox.critical(None, "Error", "Tab widget not found")
                app.quit()

        except Exception as e:
            logger.error(f"Error opening manual offset dialog: {e}")
            QMessageBox.critical(None, "Error", f"Failed to open dialog: {e}")
            app.quit()

    def capture_screenshot(dialog):
        """Capture screenshot of the dialog."""
        try:
            # Take screenshot of the dialog
            screen = dialog.screen()
            if screen:
                pixmap = screen.grabWindow(dialog.winId())

                # Save screenshot
                screenshot_path = Path("/tmp/gallery_tab_screenshot.png")
                if pixmap.save(str(screenshot_path)):
                    logger.info(f"Screenshot saved to {screenshot_path}")
                    print(f"Screenshot saved to {screenshot_path}")

                    # Also save to a Windows-accessible path
                    windows_path = Path("/mnt/c/temp/gallery_tab_screenshot.png")
                    windows_path.parent.mkdir(parents=True, exist_ok=True)
                    if pixmap.save(str(windows_path)):
                        print(f"Screenshot also saved to {windows_path}")
                else:
                    logger.error("Failed to save screenshot")
                    print("Failed to save screenshot")
            else:
                logger.error("Could not get screen for dialog")
                print("Could not get screen for dialog")

        except Exception as e:
            logger.error(f"Error taking screenshot: {e}")
            print(f"Error taking screenshot: {e}")
        finally:
            # Close after screenshot
            QTimer.singleShot(1000, app.quit)

    # Open dialog after main window is shown
    QTimer.singleShot(500, open_manual_offset_and_screenshot)

    # Run application
    sys.exit(app.exec())

if __name__ == "__main__":
    take_screenshot_of_gallery()
