"""
Mock Dialog Infrastructure for Testing

This module provides mock implementations of all dialogs to avoid metaclass
and Qt initialization issues during test collection, following Qt Testing Best Practices.

Key Patterns Applied:
- Pattern 1: Real components with mocked dependencies (QT_TESTING_BEST_PRACTICES.md:93-123)
- Pattern 2: Mock dialog exec() methods (QT_TESTING_BEST_PRACTICES.md:449-479)
- Pitfall 1: Qt Container Truthiness (QT_TESTING_BEST_PRACTICES.md:314-331)
"""

import threading
from typing import Any, Optional
from unittest.mock import MagicMock, Mock

from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QDialog, QWidget


class MockQDialog(QObject):
    """
    Mock QDialog that provides real Qt signals without requiring QApplication.

    Following Pattern 1 from Qt Testing Best Practices:
    Real Qt signals with mocked behavior.

    Inherits from QObject (not QDialog) to avoid QApplication requirement
    while still providing real Qt signals.
    """

    # Define signals that QDialog would have
    accepted = Signal()
    rejected = Signal()
    finished = Signal(int)

    def __init__(self, parent: Optional[QWidget] = None):
        # QObject doesn't require QApplication
        super().__init__()
        self.parent_widget = parent
        self.result_value = QDialog.DialogCode.Rejected
        self.visible = False
        self.modal = True
        self._window_title = ""

    def exec(self) -> int:
        """Mock exec() to prevent blocking (Pattern 2)."""
        return self.result_value

    def show(self) -> None:
        """Mock show() method."""
        self.visible = True

    def hide(self) -> None:
        """Mock hide() method."""
        self.visible = False

    def close(self) -> bool:
        """Mock close() method."""
        self.visible = False
        self.rejected.emit()
        return True

    def accept(self) -> None:
        """Mock accept() method."""
        self.result_value = QDialog.DialogCode.Accepted
        self.visible = False
        self.accepted.emit()
        self.finished.emit(QDialog.DialogCode.Accepted)

    def reject(self) -> None:
        """Mock reject() method."""
        self.result_value = QDialog.DialogCode.Rejected
        self.visible = False
        self.rejected.emit()
        self.finished.emit(QDialog.DialogCode.Rejected)

    def isVisible(self) -> bool:
        """Mock isVisible() method."""
        return self.visible

    def setWindowTitle(self, title: str) -> None:
        """Mock setWindowTitle() method."""
        self._window_title = title

    def windowTitle(self) -> str:
        """Mock windowTitle() method."""
        return self._window_title

    def setModal(self, modal: bool) -> None:
        """Mock setModal() method."""
        self.modal = modal

    def isModal(self) -> bool:
        """Mock isModal() method."""
        return self.modal


class MockUnifiedManualOffsetDialog(MockQDialog):
    """
    Mock implementation of UnifiedManualOffsetDialog.

    Provides all the signals and methods without triggering
    the DialogBase metaclass initialization issues.
    """

    # External signals for ROM extraction panel integration
    offset_changed = Signal(int)
    sprite_found = Signal(int, str)  # offset, name
    validation_failed = Signal(str)

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)

        # Mock UI components - initialized to Mock objects for initialization tests
        # Ensure these don't evaluate to False when empty (Qt container truthiness issue)
        self.tab_widget = Mock()
        self.tab_widget.__bool__ = lambda: True

        self.browse_tab = Mock()
        self.browse_tab.__bool__ = lambda: True

        self.smart_tab = Mock()
        self.smart_tab.__bool__ = lambda: True

        self.history_tab = Mock()
        self.history_tab.__bool__ = lambda: True

        self.preview_widget = Mock()
        self.preview_widget.__bool__ = lambda: True

        self.status_panel = Mock()
        self.status_panel.__bool__ = lambda: True

        self.status_collapsible = Mock()
        self.status_collapsible.__bool__ = lambda: True

        self.apply_btn = Mock()
        self.apply_btn.__bool__ = lambda: True

        self.mini_rom_map = Mock()
        self.mini_rom_map.__bool__ = lambda: True

        self.bookmarks_menu = Mock()
        self.bookmarks_menu.__bool__ = lambda: True
        self.bookmarks = []

        # Business logic state
        self.rom_path = ""
        self.rom_size = 0x400000

        # Mock manager references
        self.extraction_manager = None
        self.rom_extractor = None
        self._manager_mutex = Mock()

        # Mock ROM cache
        self.rom_cache = Mock()
        self.rom_cache.get_cache_stats.return_value = {"hits": 0, "misses": 0}
        self._cache_stats = {"hits": 0, "misses": 0, "total_requests": 0}
        self._adjacent_offsets_cache = set()

        # Mock workers
        self.preview_worker = None
        self.search_worker = None

        # Mock preview coordinator
        self.smart_preview_coordinator = Mock()

    def set_rom_data(self, rom_path: str, rom_size: int) -> None:
        """Mock method to set ROM data."""
        self.rom_path = rom_path
        self.rom_size = rom_size

    def set_managers(self, extraction_manager: Any, rom_extractor: Any) -> None:
        """Mock method to set managers."""
        self.extraction_manager = extraction_manager
        self.rom_extractor = rom_extractor

    def update_offset(self, offset: int) -> None:
        """Mock method to update offset."""
        self.offset_changed.emit(offset)

    def cleanup(self) -> None:
        """Mock cleanup method."""
        pass


class MockSettingsDialog(MockQDialog):
    """Mock implementation of SettingsDialog."""

    settings_changed = Signal(dict)

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.settings = {}
        self.setWindowTitle("SpritePal Settings")

        # Mock UI components for initialization tests
        # Ensure widgets don't evaluate to False when empty
        self.tab_widget = Mock()
        self.tab_widget.__bool__ = lambda: True
        # Set up tab widget mock to return expected values
        self.tab_widget.count.return_value = 2
        self.tab_widget.tabText.side_effect = lambda idx: ["General", "Cache"][idx] if idx < 2 else ""

        # Mock checkboxes
        self.restore_window_check = Mock()
        self.restore_window_check.__bool__ = lambda: True
        self.restore_window_check.isChecked.return_value = True
        self.restore_window_check.setChecked = Mock()

        self.auto_save_session_check = Mock()
        self.auto_save_session_check.__bool__ = lambda: True
        self.auto_save_session_check.isChecked.return_value = False
        self.auto_save_session_check.setChecked = Mock()

        # Mock line edits
        self.dumps_dir_edit = Mock()
        self.dumps_dir_edit.__bool__ = lambda: True
        self.dumps_dir_edit.text.return_value = "/test/dumps"
        self.dumps_dir_edit.setText = Mock()

        # Cache settings
        self.cache_enabled_check = Mock()
        self.cache_enabled_check.__bool__ = lambda: True
        self.cache_enabled_check.isChecked.return_value = False
        self.cache_enabled_check.setChecked = Mock()

        self.cache_location_edit = Mock()
        self.cache_location_edit.__bool__ = lambda: True
        self.cache_location_edit.text.return_value = "/custom/cache"
        self.cache_location_edit.setText = Mock()

        self.cache_size_spin = Mock()
        self.cache_size_spin.__bool__ = lambda: True
        self.cache_size_spin.value.return_value = 250
        self.cache_size_spin.setValue = Mock()

        self.cache_expiration_spin = Mock()
        self.cache_expiration_spin.__bool__ = lambda: True
        self.cache_expiration_spin.value.return_value = 14
        self.cache_expiration_spin.setValue = Mock()

        self.auto_cleanup_check = Mock()
        self.auto_cleanup_check.__bool__ = lambda: True
        self.auto_cleanup_check.isChecked.return_value = True
        self.auto_cleanup_check.setChecked = Mock()

        self.show_indicators_check = Mock()
        self.show_indicators_check.__bool__ = lambda: True
        self.show_indicators_check.isChecked.return_value = False
        self.show_indicators_check.setChecked = Mock()

    def get_settings(self) -> dict:
        """Get current settings."""
        return self.settings

    def set_settings(self, settings: dict) -> None:
        """Set settings."""
        self.settings = settings
        self.settings_changed.emit(settings)


class MockGridArrangementDialog(MockQDialog):
    """Mock implementation of GridArrangementDialog."""

    arrangement_changed = Signal(list)

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.tiles = []
        self.arrangement = []

        # Mock UI components
        self.preview_widget = Mock()
        self.preview_widget.__bool__ = lambda: True

        self.columns_slider = Mock()
        self.columns_slider.__bool__ = lambda: True
        self.columns_slider.value.return_value = 4

    def set_tiles(self, tiles: list) -> None:
        """Set tiles for arrangement."""
        self.tiles = tiles

    def get_arrangement(self) -> list:
        """Get current arrangement."""
        return self.arrangement


class MockRowArrangementDialog(MockQDialog):
    """Mock implementation of RowArrangementDialog."""

    arrangement_updated = Signal(list)

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.sprites = []
        self.arrangement = []

        # Mock UI components
        self.preview_widget = Mock()
        self.preview_widget.__bool__ = lambda: True

        self.preview_area = Mock()
        self.preview_area.__bool__ = lambda: True

        self.arrangement_list = Mock()
        self.arrangement_list.__bool__ = lambda: True

    def set_sprites(self, sprites: list) -> None:
        """Set sprites for arrangement."""
        self.sprites = sprites

    def get_arrangement(self) -> list:
        """Get current arrangement."""
        return self.arrangement


class MockAdvancedSearchDialog(MockQDialog):
    """Mock implementation of AdvancedSearchDialog."""

    search_requested = Signal(dict)
    result_selected = Signal(int)

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.search_params = {}
        self.results = []

    def set_search_params(self, params: dict) -> None:
        """Set search parameters."""
        self.search_params = params

    def add_result(self, offset: int, data: dict) -> None:
        """Add a search result."""
        self.results.append((offset, data))

    def clear_results(self) -> None:
        """Clear all results."""
        self.results = []


class MockResumeScanDialog(MockQDialog):
    """Mock implementation of ResumeScanDialog."""

    resume_requested = Signal(int)
    skip_requested = Signal()

    # Dialog result constants
    RESUME = "RESUME"
    START_FRESH = "START_FRESH"
    CANCEL = "CANCEL"

    def __init__(self, scan_info: Any = None, parent: Optional[QWidget] = None):
        # Handle both dict (scan_info) and parent widget parameters
        if isinstance(scan_info, dict):
            super().__init__(parent)
            self.scan_info = scan_info
            self.last_offset = scan_info.get("current_offset", 0)
            self.sprite_count = scan_info.get("total_found", 0)
        else:
            # scan_info might be the parent widget
            super().__init__(scan_info if scan_info is not None else parent)
            self.scan_info = {}
            self.last_offset = 0
            self.sprite_count = 0

        self.setWindowTitle("Resume Sprite Scan?")
        self.user_choice = self.CANCEL  # Default choice

        # Mock UI components - ensure they don't evaluate to False when empty
        self.message_label = Mock()
        self.message_label.__bool__ = lambda: True

        self.resume_button = Mock()
        self.resume_button.__bool__ = lambda: True
        self.resume_button.text = Mock(return_value="Resume Scan")
        self.resume_button.isDefault = Mock(return_value=True)
        self.resume_button.click = Mock()

        self.fresh_button = Mock()
        self.fresh_button.__bool__ = lambda: True
        self.fresh_button.text = Mock(return_value="Start Fresh")
        self.fresh_button.click = Mock()

        self.cancel_button = Mock()
        self.cancel_button.__bool__ = lambda: True
        self.cancel_button.text = Mock(return_value="Cancel")
        self.cancel_button.click = Mock()

        self.skip_button = Mock()
        self.skip_button.__bool__ = lambda: True

        # Connect button clicks to choice setting
        self.resume_button.click.side_effect = lambda: self._set_choice_and_accept(self.RESUME)
        self.fresh_button.click.side_effect = lambda: self._set_choice_and_accept(self.START_FRESH)
        self.cancel_button.click.side_effect = lambda: self._set_choice_and_reject(self.CANCEL)

    def _set_choice_and_accept(self, choice: str) -> None:
        """Set user choice and accept dialog."""
        self.user_choice = choice
        self.accept()

    def _set_choice_and_reject(self, choice: str) -> None:
        """Set user choice and reject dialog."""
        self.user_choice = choice
        self.reject()

    def set_scan_info(self, last_offset: int, sprite_count: int) -> None:
        """Set scan information."""
        self.last_offset = last_offset
        self.sprite_count = sprite_count

    def get_user_choice(self) -> str:
        """Get the user's choice."""
        return self.user_choice

    def _format_progress_info(self) -> str:
        """Format progress information for display."""
        if not self.scan_info:
            return "Progress: No scan data available\nSprites found: 0"

        # Calculate progress percentage
        scan_range = self.scan_info.get("scan_range", {})
        start = scan_range.get("start", 0)
        end = scan_range.get("end", 0)
        current = self.scan_info.get("current_offset", start)

        if end > start:
            progress = min(100.0, max(0.0, (current - start) / (end - start) * 100))
        else:
            progress = 0.0

        # Format the progress info
        total_found = self.scan_info.get("total_found", 0)
        lines = [
            f"Progress: {progress:.1f}% complete",
            f"Sprites found: {total_found}",
            f"Last position: 0x{current:06X}",
        ]

        if scan_range:
            lines.append(f"Scan range: 0x{start:06X} - 0x{end:06X}")

        return "\n".join(lines)

    @classmethod
    def show_resume_dialog(cls, scan_info: dict, parent: Optional[QWidget] = None) -> str:
        """Convenience method to show dialog and return user choice."""
        dialog = cls(scan_info, parent)
        dialog.exec()
        return dialog.get_user_choice()


class MockUserErrorDialog(MockQDialog):
    """Mock implementation of UserErrorDialog."""

    def __init__(self, error_message: str, technical_details: str = "", parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.error_message = error_message
        self.details = technical_details
        self._window_title = "Error"  # Default title

    def set_details(self, details: str) -> None:
        """Set error details."""
        self.details = details


class MockDialogSingleton:
    """
    Mock implementation of dialog singleton pattern.

    Avoids QtThreadSafeSingleton issues during testing.
    """
    _instance = None
    _destroyed = False
    _lock = threading.Lock()

    @classmethod
    def get_dialog(cls, parent=None):
        """Get or create the singleton dialog instance."""
        if cls._instance is not None:
            try:
                if cls._instance.isVisible():
                    return cls._instance
            except (RuntimeError, AttributeError):
                cls._instance = None

        with cls._lock:
            if cls._instance is None:
                cls._instance = cls._create_instance(parent)
            return cls._instance

    @classmethod
    def _create_instance(cls, parent=None):
        """Create a new dialog instance."""
        return MockUnifiedManualOffsetDialog(parent)

    @classmethod
    def is_dialog_open(cls):
        """Check if dialog is open."""
        if cls._instance is None:
            return False
        try:
            return cls._instance.isVisible()
        except (RuntimeError, AttributeError):
            return False

    @classmethod
    def get_current_dialog(cls):
        """Get current dialog if visible."""
        if cls.is_dialog_open():
            return cls._instance
        return None

    @classmethod
    def _cleanup_instance(cls, instance=None):
        """Cleanup the instance."""
        # Handle both calling patterns: _cleanup_instance() and _cleanup_instance(instance)
        cleanup_target = instance or cls._instance
        if cleanup_target:
            try:
                cleanup_target.close()
            except (RuntimeError, AttributeError):
                pass  # Widget might already be destroyed
        cls._instance = None
        cls._destroyed = True


def create_mock_dialog(dialog_class_name: str, parent: Optional[QWidget] = None) -> MockQDialog:
    """
    Factory function to create mock dialogs by class name.

    Args:
        dialog_class_name: Name of the dialog class to mock
        parent: Optional parent widget

    Returns:
        Mock dialog instance
    """
    dialog_map = {
        "UnifiedManualOffsetDialog": MockUnifiedManualOffsetDialog,
        "SettingsDialog": MockSettingsDialog,
        "GridArrangementDialog": MockGridArrangementDialog,
        "RowArrangementDialog": MockRowArrangementDialog,
        "AdvancedSearchDialog": MockAdvancedSearchDialog,
        "ResumeScanDialog": MockResumeScanDialog,
        "UserErrorDialog": MockUserErrorDialog,
    }

    dialog_class = dialog_map.get(dialog_class_name, MockQDialog)
    return dialog_class(parent)


def patch_dialog_imports():
    """
    Patch all dialog imports to use mock implementations.

    This should be called in test setup to prevent real dialog imports
    that trigger DialogBase metaclass issues.
    """
    import sys

    # Create mock modules for all dialog imports
    mock_modules = {
        'ui.dialogs.manual_offset_unified_integrated': MagicMock(
            UnifiedManualOffsetDialog=MockUnifiedManualOffsetDialog
        ),
        'ui.dialogs.settings_dialog': MagicMock(
            SettingsDialog=MockSettingsDialog
        ),
        'ui.dialogs.grid_arrangement_dialog': MagicMock(
            GridArrangementDialog=MockGridArrangementDialog
        ),
        'ui.dialogs.row_arrangement_dialog': MagicMock(
            RowArrangementDialog=MockRowArrangementDialog
        ),
        'ui.dialogs.advanced_search_dialog': MagicMock(
            AdvancedSearchDialog=MockAdvancedSearchDialog
        ),
        'ui.dialogs.resume_scan_dialog': MagicMock(
            ResumeScanDialog=MockResumeScanDialog
        ),
        'ui.dialogs.user_error_dialog': MagicMock(
            UserErrorDialog=MockUserErrorDialog
        ),
        # Also patch the ui.dialogs module itself for alias imports
        'ui.dialogs': MagicMock(
            UnifiedManualOffsetDialog=MockUnifiedManualOffsetDialog,
            SettingsDialog=MockSettingsDialog,
            ResumeScanDialog=MockResumeScanDialog,
            UserErrorDialog=MockUserErrorDialog,
        ),
    }

    # Patch sys.modules
    for module_name, mock_module in mock_modules.items():
        sys.modules[module_name] = mock_module

    return mock_modules
