"""
View State Manager

Handles window state management for ManualOffsetDialog including fullscreen mode
and position persistence. Extracted from ManualOffsetDialog to separate window
management concerns from business logic.
"""

import os
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from PyQt6.QtWidgets import QWidget

from PyQt6.QtCore import QObject, QRect, Qt, pyqtSignal
from PyQt6.QtGui import QGuiApplication

from spritepal.utils.logging_config import get_logger
from spritepal.utils.settings_manager import get_settings_manager

logger = get_logger(__name__)


class ViewStateManager(QObject):
    """
    Manages window state for ManualOffsetDialog.

    Responsibilities:
    - Fullscreen mode toggle
    - Window position save/restore
    - Size constraints and parent centering
    - Window title management
    """

    # Signals for state changes
    fullscreen_toggled = pyqtSignal(bool)  # is_fullscreen
    title_changed = pyqtSignal(str)  # new_title

    def __init__(self, dialog_widget: "QWidget", parent=None) -> None:
        super().__init__(parent)

        self.dialog_widget = dialog_widget

        # Fullscreen state
        self._is_fullscreen = False
        self._normal_geometry: QRect | None = None
        self._original_window_flags = dialog_widget.windowFlags()

        # Base titles
        self._base_title = "Manual Offset Control - SpritePal"
        self._fullscreen_title = "Manual Offset Control - SpritePal (Fullscreen - F11 or Esc to exit)"

    def toggle_fullscreen(self) -> None:
        """Toggle between fullscreen and normal window mode"""
        if self._is_fullscreen:
            self._exit_fullscreen()
        else:
            self._enter_fullscreen()

    def _enter_fullscreen(self) -> None:
        """Enter fullscreen mode"""
        if self._is_fullscreen:
            return

        # Save current geometry
        self._normal_geometry = self.dialog_widget.geometry()

        # Use clean window flags for true fullscreen
        self.dialog_widget.setWindowFlags(Qt.WindowType.Window)
        self.dialog_widget.showFullScreen()

        self._is_fullscreen = True
        self.dialog_widget.setWindowTitle(self._fullscreen_title)

        self.fullscreen_toggled.emit(True)
        self.title_changed.emit(self._fullscreen_title)
        logger.debug("Entered fullscreen mode")

    def _exit_fullscreen(self) -> None:
        """Exit fullscreen mode"""
        if not self._is_fullscreen:
            return

        # Restore original window flags and geometry
        self.dialog_widget.setWindowFlags(self._original_window_flags)
        self.dialog_widget.showNormal()

        if self._normal_geometry:
            self.dialog_widget.setGeometry(self._normal_geometry)

        self._is_fullscreen = False
        self.dialog_widget.setWindowTitle(self._base_title)

        self.fullscreen_toggled.emit(False)
        self.title_changed.emit(self._base_title)
        logger.debug("Exited fullscreen mode")

    def is_fullscreen(self) -> bool:
        """Check if currently in fullscreen mode"""
        return self._is_fullscreen

    def update_title_with_rom(self, rom_path: str) -> None:
        """Update window title with ROM name"""
        if rom_path:
            rom_name = os.path.basename(rom_path)
            title = f"Manual Offset Control - {rom_name}"
        else:
            title = self._base_title

        self._base_title = title

        # Update current title if not in fullscreen
        if not self._is_fullscreen:
            self.dialog_widget.setWindowTitle(title)
            self.title_changed.emit(title)

    def save_window_position(self) -> None:
        """Save the current window position to settings"""
        if self._is_fullscreen:
            # Don't save position in fullscreen mode
            return

        try:
            settings_manager = get_settings_manager()
            pos = self.dialog_widget.pos()
            size = self.dialog_widget.size()

            settings_manager.set("manual_offset_dialog", "x", pos.x())
            settings_manager.set("manual_offset_dialog", "y", pos.y())
            settings_manager.set("manual_offset_dialog", "width", size.width())
            settings_manager.set("manual_offset_dialog", "height", size.height())

            logger.debug(f"Saved window position: {pos.x()},{pos.y()} size: {size.width()}x{size.height()}")
        except Exception as e:
            logger.warning(f"Failed to save window position: {e}")

    def _is_position_on_screen(self, x: int, y: int, width: int, height: int) -> bool:
        """Check if a window position is reasonably visible on any screen"""
        window_rect = QRect(x, y, width, height)

        # Check if window intersects with any available screen
        for screen in QGuiApplication.screens():
            screen_geometry = screen.availableGeometry()
            if window_rect.intersects(screen_geometry):
                intersection = window_rect.intersected(screen_geometry)

                # Require at least 80% of the dialog to be visible to avoid "too high" positioning
                required_width = int(width * 0.8)
                required_height = int(height * 0.8)

                if (intersection.width() >= required_width and
                    intersection.height() >= required_height):

                    # Additional check: ensure the dialog isn't positioned too high
                    # The top of the dialog should be at least 50px from the top of screen
                    if y >= screen_geometry.y() + 50:
                        return True
                    logger.debug(f"Dialog positioned too high: y={y}, screen_top={screen_geometry.y()}")

        return False

    def restore_window_position(self) -> bool:
        """
        Restore window position from settings with screen bounds validation.

        TEMPORARILY DISABLED: Always returns False to force safe positioning
        until positioning issues are resolved.

        Returns:
            True if position was restored, False otherwise
        """
        # TEMPORARY FIX: Disable position restoration to prevent off-screen positioning
        logger.debug("Position restoration temporarily disabled - using safe positioning")
        return False


    def center_on_screen(self) -> None:
        """Center the dialog on the primary screen as a safe fallback"""
        try:
            primary_screen = QGuiApplication.primaryScreen()
            if primary_screen:
                screen_geometry = primary_screen.availableGeometry()
                dialog_width = self.dialog_widget.width()
                dialog_height = self.dialog_widget.height()

                # Check if dialog is larger than available screen space
                if dialog_width > screen_geometry.width() or dialog_height > screen_geometry.height():
                    # Resize dialog to fit screen with some margin
                    max_width = max(800, screen_geometry.width() - 100)  # At least 800px wide, with 100px margin
                    max_height = max(600, screen_geometry.height() - 100)  # At least 600px high, with 100px margin

                    new_width = min(dialog_width, max_width)
                    new_height = min(dialog_height, max_height)

                    self.dialog_widget.resize(new_width, new_height)
                    logger.debug(f"Resized dialog to fit screen: {new_width}x{new_height}")

                    # Update dimensions after resize
                    dialog_width = new_width
                    dialog_height = new_height

                # Calculate center position
                center_x = screen_geometry.x() + (screen_geometry.width() - dialog_width) // 2
                center_y = screen_geometry.y() + (screen_geometry.height() - dialog_height) // 2

                # Ensure dialog stays within screen bounds with extra safety margins
                margin = 50  # Extra safety margin
                center_x = max(screen_geometry.x() + margin, min(center_x, screen_geometry.x() + screen_geometry.width() - dialog_width - margin))
                center_y = max(screen_geometry.y() + margin, min(center_y, screen_geometry.y() + screen_geometry.height() - dialog_height - margin))

                # Extra safety: never allow negative or zero positions
                center_x = max(100, center_x)
                center_y = max(100, center_y)

                self.dialog_widget.move(center_x, center_y)
                logger.debug(f"Centered dialog on screen at {center_x},{center_y} (screen: {screen_geometry.width()}x{screen_geometry.height()})")
            else:
                # Last resort - move to top-left with small offset
                self.dialog_widget.move(100, 100)
                logger.debug("No screen found, positioned dialog at 100,100")
        except Exception as e:
            logger.warning(f"Failed to center on screen: {e}")
            # Ultimate fallback
            self.dialog_widget.move(100, 100)

    def center_on_parent(self) -> bool:
        """
        Center the dialog on its parent window.

        Returns:
            True if successfully centered on parent, False otherwise
        """
        if not self.dialog_widget.parent():
            return False

        try:
            parent_window = self.dialog_widget.parent().window()
            if not parent_window.isVisible():
                return False

            parent_rect = parent_window.frameGeometry()

            # Validate parent geometry is reasonable
            if parent_rect.width() <= 0 or parent_rect.height() <= 0:
                return False

            center_x = parent_rect.x() + (parent_rect.width() - self.dialog_widget.width()) // 2
            center_y = parent_rect.y() + (parent_rect.height() - self.dialog_widget.height()) // 2

            # Validate the calculated position is on screen
            if self._is_position_on_screen(center_x, center_y, self.dialog_widget.width(), self.dialog_widget.height()):
                self.dialog_widget.move(center_x, center_y)
                logger.debug(f"Centered dialog on parent at {center_x},{center_y}")
                return True
            logger.debug(f"Calculated parent center position {center_x},{center_y} is off-screen")
            return False

        except Exception as e:
            logger.warning(f"Failed to center on parent: {e}")
            return False

    def handle_show_event(self) -> None:
        """Handle dialog show event with robust positioning fallbacks"""
        # TEMPORARY: Skip saved position restoration for now to avoid "too high" issues
        # This ensures all dialogs use proper centering logic after the positioning fixes
        # TODO: Remove this skip after a few releases when old bad positions are cleared

        # Position restoration temporarily disabled to prevent off-screen issues

        # Try to center on parent window
        if self.center_on_parent():
            return

        # Final fallback - center on screen (will always work)
        self.center_on_screen()

    def handle_hide_event(self) -> None:
        """Handle dialog hide event - save current position"""
        self.save_window_position()

    def reset_to_safe_position(self) -> None:
        """Reset dialog to a safe visible position - useful for debugging positioning issues"""
        logger.info("Resetting dialog to safe position")
        self.center_on_screen()

    def handle_escape_key(self) -> bool:
        """
        Handle escape key press.

        Returns:
            True if the key was handled (fullscreen exit), False otherwise
        """
        if self._is_fullscreen:
            self.toggle_fullscreen()
            return True
        return False
