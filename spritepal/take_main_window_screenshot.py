#!/usr/bin/env python3
"""
Script to take a screenshot of the main window for layout analysis.
"""

import sys
from pathlib import Path

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

# Add spritepal to path
sys.path.insert(0, str(Path(__file__).parent))

from core.managers.registry import initialize_managers
from ui.main_window import MainWindow


def take_main_window_screenshot():
    """Launch app and take screenshot of main window."""
    app = QApplication.instance() or QApplication(sys.argv)

    # Initialize managers first
    initialize_managers()

    # Create main window
    main_window = MainWindow()
    main_window.show()

    def load_rom_and_capture():
        """Load ROM and capture main window screenshot."""
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
                    QTimer.singleShot(1000, lambda: capture_screenshot())
                else:
                    print("ROM loading method not found")
                    capture_screenshot()
            else:
                print("No ROM files found, capturing without ROM")
                capture_screenshot()
        except Exception as e:
            print(f"Error loading ROM: {e}")
            capture_screenshot()

    def capture_screenshot():
        """Capture screenshot of the main window."""
        try:
            # Take screenshot with incrementing number
            pixmap = main_window.grab()

            # Find the next available screenshot number
            screenshot_num = 1
            while True:
                screenshot_path = Path(__file__).parent / f"main_window_screenshot_{screenshot_num}.png"
                if not screenshot_path.exists():
                    break
                screenshot_num += 1

            pixmap.save(str(screenshot_path))
            print(f"Screenshot saved to: {screenshot_path}")

            # Also save as "current" for easy access
            current_path = Path(__file__).parent / "main_window_current_screenshot.png"
            pixmap.save(str(current_path))
            print(f"Also saved as current: {current_path}")

        except Exception as e:
            print(f"Error taking screenshot: {e}")
        finally:
            app.quit()

    # Wait for main window to load, then capture
    QTimer.singleShot(2000, load_rom_and_capture)

    # Run the application
    app.exec()


if __name__ == "__main__":
    take_main_window_screenshot()
