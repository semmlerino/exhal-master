#!/usr/bin/env python3
"""
Universal screenshot capture script with incrementing filenames.
Works with xvfb for headless environments.
"""

import sys
from pathlib import Path
from typing import Optional

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication, QWidget

# Add parent directory to path to import SpritePal modules
sys.path.insert(0, str(Path(__file__).parent))

from utils.logging_config import get_logger

logger = get_logger(__name__)

def get_next_screenshot_number(base_dir: Path, prefix: str = "screenshot") -> int:
    """
    Find the next available screenshot number.

    Args:
        base_dir: Directory to check for existing screenshots
        prefix: Filename prefix for screenshots

    Returns:
        Next available number (starting from 1)
    """
    base_dir.mkdir(parents=True, exist_ok=True)

    # Find existing screenshot files
    existing = list(base_dir.glob(f"{prefix}_*.png"))

    if not existing:
        return 1

    # Extract numbers from filenames
    numbers = []
    for file in existing:
        try:
            # Extract number from filename like "screenshot_001.png"
            name = file.stem  # Get filename without extension
            if name.startswith(prefix + "_"):
                num_str = name[len(prefix) + 1:]
                numbers.append(int(num_str))
        except (ValueError, IndexError):
            continue

    # Return next number
    return max(numbers, default=0) + 1

def capture_widget_screenshot(widget: QWidget, name: str = "screenshot", description: str = "") -> bool:
    """
    Capture a screenshot of any Qt widget with auto-incrementing filename.

    Args:
        widget: The widget to capture
        name: Base name for the screenshot file
        description: Optional description to print

    Returns:
        True if successful, False otherwise
    """
    try:
        # Use Qt's grab() method which works in headless environments
        pixmap = widget.grab()

        # Get next available number
        output_dir = Path("/tmp")
        next_num = get_next_screenshot_number(output_dir, name)

        # Format filename with zero-padded number
        filename = f"{name}_{next_num:03d}.png"
        output_path = output_dir / filename

        if pixmap.save(str(output_path), "PNG"):
            print(f"✓ Screenshot saved to: {output_path}")
            if description:
                print(f"  Description: {description}")

            # Also try to save to Windows-accessible location with same numbering
            try:
                windows_dir = Path("/mnt/c/temp/screenshots")
                windows_dir.mkdir(parents=True, exist_ok=True)
                windows_path = windows_dir / filename

                if pixmap.save(str(windows_path), "PNG"):
                    print(f"✓ Also saved to Windows: {windows_path}")
            except Exception as e:
                print(f"Note: Could not save to Windows path: {e}")

            return True
        print(f"✗ Failed to save screenshot to {output_path}")
        return False

    except Exception as e:
        print(f"✗ Error taking screenshot: {e}")
        logger.error(f"Screenshot error: {e}")
        return False

def capture_manual_offset_dialog(tab_name: Optional[str] = None):
    """
    Capture screenshot of the manual offset dialog.

    Args:
        tab_name: Optional specific tab to switch to (e.g., "Gallery", "Browse", "Smart", "History")
    """
    from ui.dialogs.manual_offset_unified_integrated import UnifiedManualOffsetDialog

    app = QApplication.instance() or QApplication(sys.argv)

    # Create the manual offset dialog
    dialog = UnifiedManualOffsetDialog()
    dialog.resize(1000, 700)  # Set a good size for the screenshot

    # Switch to specific tab if requested
    if tab_name and dialog.tab_widget:
        for i in range(dialog.tab_widget.count()):
            if dialog.tab_widget.tabText(i) == tab_name:
                dialog.tab_widget.setCurrentIndex(i)
                print(f"Switched to {tab_name} tab (index {i})")
                break

    # Show the dialog
    dialog.show()

    def take_screenshot():
        """Take the screenshot after a delay to ensure rendering is complete."""
        # Capture full dialog
        base_name = f"manual_offset_{tab_name.lower()}" if tab_name else "manual_offset"
        capture_widget_screenshot(dialog, base_name, f"Manual Offset Dialog - {tab_name or 'Default'} Tab")

        # Also capture just the tab widget if specific tab was requested
        if tab_name:
            if tab_name == "Gallery" and dialog.gallery_tab:
                capture_widget_screenshot(dialog.gallery_tab, "gallery_tab", "Gallery Tab Widget Only")
            elif tab_name == "Browse" and dialog.browse_tab:
                capture_widget_screenshot(dialog.browse_tab, "browse_tab", "Browse Tab Widget Only")
            elif tab_name == "Smart" and dialog.smart_tab:
                capture_widget_screenshot(dialog.smart_tab, "smart_tab", "Smart Tab Widget Only")
            elif tab_name == "History" and dialog.history_tab:
                capture_widget_screenshot(dialog.history_tab, "history_tab", "History Tab Widget Only")

        # Exit after screenshot
        app.quit()

    # Take screenshot after a short delay to ensure rendering
    QTimer.singleShot(1000, take_screenshot)

    # Run the application
    return app.exec()

def capture_main_window():
    """Capture screenshot of the main SpritePal window."""
    from main_window import SpritePalMainWindow

    app = QApplication.instance() or QApplication(sys.argv)

    # Create and show main window
    main_window = SpritePalMainWindow()
    main_window.show()

    def take_screenshot():
        """Take the screenshot after a delay to ensure rendering is complete."""
        capture_widget_screenshot(main_window, "main_window", "SpritePal Main Window")
        app.quit()

    # Take screenshot after a short delay to ensure rendering
    QTimer.singleShot(1000, take_screenshot)

    # Run the application
    return app.exec()

def main():
    """Main entry point with command line argument handling."""
    import argparse

    parser = argparse.ArgumentParser(description="Capture SpritePal screenshots")
    parser.add_argument("target", nargs="?", default="gallery",
                       choices=["main", "gallery", "browse", "smart", "history", "manual"],
                       help="What to capture (default: gallery)")

    args = parser.parse_args()

    if args.target == "main":
        sys.exit(capture_main_window())
    elif args.target == "manual":
        sys.exit(capture_manual_offset_dialog())
    else:
        # Capture specific tab
        sys.exit(capture_manual_offset_dialog(args.target.capitalize()))

if __name__ == "__main__":
    main()
