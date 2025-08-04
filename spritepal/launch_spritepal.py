#!/usr/bin/env python3
"""
SpritePal - Modern Sprite Extraction Tool
Simplifies sprite extraction with automatic palette association
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.managers import cleanup_managers, initialize_managers, validate_manager_dependencies
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QPalette
from PyQt6.QtWidgets import QApplication
from ui.common.error_handler import get_error_handler
from ui.main_window import MainWindow
from utils.error_display_adapter import ErrorHandlerAdapter
from utils.logging_config import get_logger, setup_logging
from utils.unified_error_handler import set_global_error_display


def handle_exception(exc_type, exc_value, exc_traceback):
    """Global exception handler to log unhandled exceptions"""
    if issubclass(exc_type, KeyboardInterrupt):
        # Allow KeyboardInterrupt to work normally
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return

    # Get logger (setup_logging should have been called by now)
    logger = get_logger("global_exception_handler")

    # Log the unhandled exception
    logger.critical("Unhandled exception occurred!", exc_info=(exc_type, exc_value, exc_traceback))
    logger.critical(f"Exception type: {exc_type.__name__}")
    logger.critical(f"Exception value: {exc_value}")
    logger.critical("=" * 80)
    logger.critical("CRASH DETECTED - Application will likely terminate")
    logger.critical("=" * 80)

    # Call the default handler to maintain normal behavior
    sys.__excepthook__(exc_type, exc_value, exc_traceback)


class SpritePalApp(QApplication):
    """Main application class for SpritePal"""

    def __init__(self, argv):
        super().__init__(argv)

        # Set application metadata
        self.setApplicationName("SpritePal")
        self.setOrganizationName("KirbySpriteTools")
        self.setApplicationDisplayName("SpritePal - Sprite Extraction Tool")

        # Apply modern dark theme
        self._apply_dark_theme()

        # Create main window
        self.main_window = MainWindow()

    def _apply_dark_theme(self):
        """Apply a modern dark theme to the application"""
        # Create dark palette
        dark_palette = QPalette()

        # Window colors
        dark_palette.setColor(QPalette.ColorRole.Window, QColor(45, 45, 48))
        dark_palette.setColor(QPalette.ColorRole.WindowText, Qt.GlobalColor.white)

        # Base colors (for input widgets)
        dark_palette.setColor(QPalette.ColorRole.Base, QColor(30, 30, 30))
        dark_palette.setColor(QPalette.ColorRole.AlternateBase, QColor(50, 50, 52))

        # Text colors
        dark_palette.setColor(QPalette.ColorRole.Text, Qt.GlobalColor.white)
        dark_palette.setColor(QPalette.ColorRole.BrightText, Qt.GlobalColor.red)

        # Button colors
        dark_palette.setColor(QPalette.ColorRole.Button, QColor(55, 55, 58))
        dark_palette.setColor(QPalette.ColorRole.ButtonText, Qt.GlobalColor.white)

        # Highlight colors
        dark_palette.setColor(QPalette.ColorRole.Highlight, QColor(0, 122, 204))
        dark_palette.setColor(QPalette.ColorRole.HighlightedText, Qt.GlobalColor.white)

        # Other colors
        dark_palette.setColor(QPalette.ColorRole.Link, QColor(0, 162, 232))
        dark_palette.setColor(QPalette.ColorRole.LinkVisited, QColor(128, 128, 255))

        # Disabled colors
        dark_palette.setColor(
            QPalette.ColorGroup.Disabled,
            QPalette.ColorRole.WindowText,
            QColor(127, 127, 127),
        )
        dark_palette.setColor(
            QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text, QColor(127, 127, 127)
        )
        dark_palette.setColor(
            QPalette.ColorGroup.Disabled,
            QPalette.ColorRole.ButtonText,
            QColor(127, 127, 127),
        )

        self.setPalette(dark_palette)

        # Set application-wide stylesheet for additional styling
        self.setStyleSheet(
            """
            QToolTip {
                color: white;
                background-color: #2b2b2b;
                border: 1px solid #555;
                padding: 4px;
            }

            QGroupBox {
                border: 1px solid #555;
                border-radius: 4px;
                margin-top: 8px;
                padding-top: 8px;
                font-weight: bold;
            }

            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }

            QPushButton {
                padding: 6px 12px;
                border-radius: 4px;
                border: 1px solid #555;
                min-width: 80px;
            }

            QPushButton:hover {
                background-color: #484848;
                border-color: #0078d4;
            }

            QPushButton:pressed {
                background-color: #383838;
            }

            QPushButton:disabled {
                background-color: #2d2d2d;
                color: #666;
            }

            QLineEdit {
                padding: 4px;
                border: 1px solid #555;
                border-radius: 4px;
                background-color: #2b2b2b;
            }

            QLineEdit:focus {
                border-color: #0078d4;
            }

            QComboBox {
                padding: 4px;
                border: 1px solid #555;
                border-radius: 4px;
                background-color: #2b2b2b;
                min-width: 100px;
            }

            QComboBox:hover {
                border-color: #0078d4;
            }

            QComboBox::drop-down {
                border: none;
                width: 20px;
            }

            QComboBox::down-arrow {
                image: none;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-top: 5px solid #999;
                margin-right: 5px;
            }

            QProgressBar {
                border: 1px solid #555;
                border-radius: 4px;
                text-align: center;
                background-color: #2b2b2b;
            }

            QProgressBar::chunk {
                background-color: #0078d4;
                border-radius: 3px;
            }

            QTabWidget::pane {
                border: 1px solid #555;
                background-color: #2d2d30;
            }

            QTabBar::tab {
                background-color: #383838;
                color: white;
                padding: 8px 16px;
                margin-right: 2px;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
            }

            QTabBar::tab:selected {
                background-color: #2d2d30;
                border-bottom: 2px solid #0078d4;
            }

            QTabBar::tab:hover {
                background-color: #484848;
            }

            QStatusBar {
                background-color: #007acc;
                color: white;
            }
        """
        )

    def show(self):
        """Show the main window"""
        self.main_window.show()


def main():
    """Main entry point"""
    # Initialize logging (will use SPRITEPAL_DEBUG env var if set)
    logger = setup_logging()
    logger.info(f"Python version: {sys.version}")
    logger.info(f"Platform: {sys.platform}")

    # Install global exception handler to catch unhandled crashes
    sys.excepthook = handle_exception
    logger.info("Global exception handler installed")

    # Initialize managers with enhanced error handling
    logger.info("Initializing managers...")
    try:
        initialize_managers("SpritePal")
        logger.info("Managers initialized successfully")

        # Validate manager dependencies
        if validate_manager_dependencies():
            logger.info("Manager dependencies validated successfully")
        else:
            logger.warning("Manager dependency validation failed - some features may not work correctly")

    except Exception as e:
        logger.critical(f"Failed to initialize managers: {e}")
        logger.critical("Application cannot start without properly initialized managers")
        sys.exit(1)

    # Set up error handler integration (breaks circular dependency)
    logger.info("Setting up error handler integration...")
    ui_error_handler = get_error_handler()
    adapter = ErrorHandlerAdapter(ui_error_handler)
    set_global_error_display(adapter)
    logger.info("Error handler integration complete")

    try:
        # Create application
        app = SpritePalApp(sys.argv)

        # Show main window
        app.show()

        # Run event loop
        result = app.exec()
    finally:
        # Cleanup managers on exit
        logger.info("Cleaning up managers...")
        cleanup_managers()
        logger.info("Managers cleaned up")

    sys.exit(result)


if __name__ == "__main__":
    main()
