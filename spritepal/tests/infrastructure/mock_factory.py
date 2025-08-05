"""
Consolidated mock factory for SpritePal tests.

This module provides a single, comprehensive factory for creating all types of mocks
used across the test suite, eliminating duplication and inconsistencies.
"""

from typing import Any, Optional, cast
from unittest.mock import Mock

from .qt_mocks import (
    MockSignal,
    create_mock_signals,
)
from .test_protocols import (
    MockExtractionManagerProtocol,
    MockExtractionWorkerProtocol,
    MockInjectionManagerProtocol,
    MockMainWindowProtocol,
    MockSessionManagerProtocol,
    MockSignalCoordinatorProtocol,
)


class MockFactory:
    """
    Centralized factory for creating all types of mocks used in SpritePal tests.

    This replaces the various create_mock_* functions scattered across the test suite
    with a single, consistent interface.
    """

    @staticmethod
    def create_main_window(with_extraction_params: bool = True) -> MockMainWindowProtocol:
        """
        Create a comprehensive mock main window.

        Args:
            with_extraction_params: Whether to include default extraction parameters

        Returns:
            Mock main window configured for controller testing
        """
        window = Mock()

        # Signals
        window.extract_requested = MockSignal()
        window.open_in_editor_requested = MockSignal()
        window.arrange_rows_requested = MockSignal()
        window.arrange_grid_requested = MockSignal()
        window.inject_requested = MockSignal()

        # UI Components
        window.status_bar = Mock()
        window.status_bar.showMessage = Mock()
        window.sprite_preview = Mock()
        window.palette_preview = Mock()
        window.preview_info = Mock()
        window.output_name_edit = Mock()
        window.output_name_edit.text = Mock(return_value="test_output")

        # Methods
        if with_extraction_params:
            window.get_extraction_params = Mock(return_value={
                "vram_path": "/test/vram.dmp",
                "cgram_path": "/test/cgram.dmp",
                "output_base": "/test/output",
                "create_grayscale": True,
                "create_metadata": True,
                "oam_path": None,
            })
        else:
            window.get_extraction_params = Mock()

        window.extraction_complete = Mock()
        window.extraction_failed = Mock()
        window.show = Mock()
        window.close = Mock()

        return cast(MockMainWindowProtocol, window)

    @staticmethod
    def create_extraction_worker() -> MockExtractionWorkerProtocol:
        """
        Create a mock extraction worker with proper signal behavior.

        Returns:
            Mock worker with all extraction signals configured
        """
        worker = Mock()

        # Add all extraction signals
        signals = create_mock_signals()
        for signal_name, signal in signals.items():
            setattr(worker, signal_name, signal)

        # Worker control methods
        worker.start = Mock()
        worker.run = Mock()
        worker.quit = Mock()
        worker.wait = Mock(return_value=True)
        worker.isRunning = Mock(return_value=False)

        return cast(MockExtractionWorkerProtocol, worker)

    @staticmethod
    def create_extraction_manager() -> MockExtractionManagerProtocol:
        """
        Create a mock extraction manager.

        Returns:
            Mock extraction manager with core methods
        """
        manager = Mock()
        manager.extract_sprites = Mock()
        manager.get_rom_extractor = Mock()
        manager.validate_extraction_params = Mock(return_value=True)
        manager.create_worker = Mock()

        # Add signals
        signals = create_mock_signals()
        for signal_name, signal in signals.items():
            setattr(manager, signal_name, signal)

        return cast(MockExtractionManagerProtocol, manager)

    @staticmethod
    def create_injection_manager() -> MockInjectionManagerProtocol:
        """
        Create a mock injection manager.

        Returns:
            Mock injection manager with core methods
        """
        manager = Mock()
        manager.inject_sprite = Mock()
        manager.validate_injection_params = Mock(return_value=True)
        manager.create_worker = Mock()

        # Standard signals
        manager.injection_started = MockSignal()
        manager.injection_progress = MockSignal()
        manager.injection_complete = MockSignal()
        manager.injection_failed = MockSignal()

        return cast(MockInjectionManagerProtocol, manager)

    @staticmethod
    def create_session_manager() -> MockSessionManagerProtocol:
        """
        Create a mock session manager.

        Returns:
            Mock session manager with persistence methods
        """
        manager = Mock()
        manager.save_settings = Mock()
        manager.load_settings = Mock(return_value={})
        manager.get_recent_files = Mock(return_value=[])
        manager.add_recent_file = Mock()

        return cast(MockSessionManagerProtocol, manager)

    @staticmethod
    def create_file_dialogs() -> dict[str, Mock]:
        """
        Create mock file dialog functions.

        Returns:
            Dictionary of mock file dialog functions
        """
        return {
            "getOpenFileName": Mock(return_value=("test_file.dmp", "Memory dump (*.dmp)")),
            "getSaveFileName": Mock(return_value=("output.png", "PNG files (*.png)")),
            "getExistingDirectory": Mock(return_value="/test/directory"),
        }

    @staticmethod
    def create_qimage(width: int = 128, height: int = 128) -> Mock:
        """
        Create a mock QImage for image processing tests.

        Args:
            width: Image width
            height: Image height

        Returns:
            Mock QImage with specified dimensions
        """
        qimage = Mock()
        qimage.width = Mock(return_value=width)
        qimage.height = Mock(return_value=height)
        qimage.format = Mock(return_value=Mock())
        qimage.bits = Mock(return_value=b"\x00" * (width * height))
        qimage.save = Mock(return_value=True)
        qimage.load = Mock(return_value=True)
        qimage.isNull = Mock(return_value=False)
        return qimage

    @staticmethod
    def create_drag_drop_event(file_paths: Optional[list[str | None]] = None) -> Mock:
        """
        Create a mock drag and drop event.

        Args:
            file_paths: List of file paths to simulate dropping

        Returns:
            Mock drag drop event
        """
        if file_paths is None:
            file_paths = ["/test/file.dmp"]

        event = Mock()
        event.mimeData = Mock()
        event.mimeData().hasUrls = Mock(return_value=True)
        event.mimeData().urls = Mock(return_value=[
            Mock(toLocalFile=Mock(return_value=path)) for path in file_paths
        ])
        event.accept = Mock()
        event.ignore = Mock()
        return event

    @staticmethod
    def create_rom_cache() -> Mock:
        """
        Create a mock ROM cache for testing.

        Returns:
            Mock ROM cache with standard methods
        """
        cache = Mock()
        cache.get_cache_status = Mock(return_value="no_cache")
        cache.get_cached_results = Mock(return_value=None)
        cache.cache_results = Mock()
        cache.clear_cache = Mock()
        cache.is_cache_valid = Mock(return_value=False)

        return cache

    @staticmethod
    def create_unified_dialog_services() -> dict[str, Mock]:
        """
        Create mock services for unified manual offset dialog testing.

        Returns:
            Dictionary of mock services implementing dialog protocols
        """
        # Preview generator
        preview_generator = Mock()
        preview_generator.create_preview_request = Mock()
        preview_generator.generate_preview = Mock()
        preview_generator.preview_ready = MockSignal()
        preview_generator.preview_error = MockSignal()

        # Error handler
        error_handler = Mock()
        error_handler.handle_error = Mock()
        error_handler.handle_exception = Mock()
        error_handler.report_warning = Mock()

        # Offset navigator
        offset_navigator = Mock()
        offset_navigator.offset_changed = MockSignal()
        offset_navigator.navigation_bounds_changed = MockSignal()
        offset_navigator.step_size_changed = MockSignal()
        offset_navigator.get_current_state = Mock()
        offset_navigator.set_offset = Mock(return_value=True)
        offset_navigator.set_rom_size = Mock()
        offset_navigator.set_step_size = Mock()
        offset_navigator.move_forward = Mock(return_value=True)
        offset_navigator.move_backward = Mock(return_value=True)
        offset_navigator.validate_offset = Mock(return_value=(True, ""))
        offset_navigator.get_valid_range = Mock(return_value=(0, 0x400000))

        # Preview coordinator
        preview_coordinator = Mock()
        preview_coordinator.preview_requested = MockSignal()
        preview_coordinator.preview_ready = MockSignal()
        preview_coordinator.preview_error = MockSignal()
        preview_coordinator.preview_cleared = MockSignal()
        preview_coordinator.request_preview = Mock()
        preview_coordinator.request_preview_with_debounce = Mock()
        preview_coordinator.clear_preview = Mock()
        preview_coordinator.cancel_pending_previews = Mock()
        preview_coordinator.set_preview_widget = Mock()
        preview_coordinator.cleanup_workers = Mock()

        # Sprites registry
        sprites_registry = Mock()
        sprites_registry.sprite_added = MockSignal()
        sprites_registry.sprite_removed = MockSignal()
        sprites_registry.sprites_cleared = MockSignal()
        sprites_registry.sprites_imported = MockSignal()
        sprites_registry.add_sprite = Mock(return_value=True)
        sprites_registry.remove_sprite = Mock(return_value=True)
        sprites_registry.get_sprite = Mock(return_value=None)
        sprites_registry.get_all_sprites = Mock(return_value=[])
        sprites_registry.get_sprite_count = Mock(return_value=0)
        sprites_registry.clear_sprites = Mock()
        sprites_registry.import_sprites = Mock(return_value=0)
        sprites_registry.export_sprites = Mock(return_value=[])
        sprites_registry.has_sprite_at = Mock(return_value=False)
        sprites_registry.get_sprites_in_range = Mock(return_value=[])

        # Worker manager
        worker_manager = Mock()
        worker_manager.worker_started = MockSignal()
        worker_manager.worker_finished = MockSignal()
        worker_manager.worker_error = MockSignal()
        worker_manager.create_worker = Mock(return_value="test_worker_123")
        worker_manager.cleanup_worker = Mock(return_value=True)
        worker_manager.cleanup_all_workers = Mock(return_value=0)
        worker_manager.get_active_workers = Mock(return_value=[])

        return {
            "preview_generator": preview_generator,
            "error_handler": error_handler,
            "offset_navigator": offset_navigator,
            "preview_coordinator": preview_coordinator,
            "sprites_registry": sprites_registry,
            "worker_manager": worker_manager,
        }

    @staticmethod
    def create_signal_coordinator(services: Optional[dict[str, Mock | None]] = None) -> MockSignalCoordinatorProtocol:
        """
        Create a mock signal coordinator for dialog testing.

        Args:
            services: Optional dictionary of mock services to use

        Returns:
            Mock signal coordinator with all required signals and methods
        """
        coordinator = Mock()

        # External compatibility signals
        coordinator.offset_changed = MockSignal()
        coordinator.sprite_found = MockSignal()
        coordinator.preview_requested = MockSignal()
        coordinator.search_started = MockSignal()
        coordinator.search_completed = MockSignal()

        # Internal coordination signals
        coordinator.tab_switch_requested = MockSignal()
        coordinator.update_title_requested = MockSignal()
        coordinator.status_message = MockSignal()
        coordinator.navigation_enabled = MockSignal()
        coordinator.step_size_synchronized = MockSignal()
        coordinator.preview_update_queued = MockSignal()
        coordinator.preview_generation_started = MockSignal()
        coordinator.preview_generation_completed = MockSignal()

        # Methods
        coordinator.queue_offset_update = Mock()
        coordinator.queue_preview_update = Mock()
        coordinator.coordinate_preview_update = Mock()
        coordinator.block_signals_temporarily = Mock()
        coordinator.register_worker = Mock()
        coordinator.unregister_worker = Mock()
        coordinator.is_searching = Mock(return_value=False)
        coordinator.get_current_offset = Mock(return_value=0x200000)
        coordinator.cleanup = Mock()

        return cast(MockSignalCoordinatorProtocol, coordinator)

    @staticmethod
    def create_manual_offset_dialog_tabs() -> dict[str, Mock]:
        """
        Create mock tabs for manual offset dialog testing.

        Returns:
            Dictionary containing mock tabs for browse, smart, and history
        """
        # Browse tab
        browse_tab = Mock()
        browse_tab.offset_changed = MockSignal()
        browse_tab.find_next_clicked = MockSignal()
        browse_tab.find_prev_clicked = MockSignal()
        browse_tab.get_offset = Mock(return_value=0x200000)
        browse_tab.set_offset = Mock()
        browse_tab.set_rom_size = Mock()
        browse_tab.slider = Mock()
        browse_tab.slider.setValue = Mock()
        browse_tab.slider.value = Mock(return_value=0x200000)
        browse_tab.slider.maximum = Mock(return_value=0x400000)

        # Smart tab
        smart_tab = Mock()
        smart_tab.smart_mode_changed = MockSignal()
        smart_tab.offset_requested = MockSignal()
        smart_tab.smart_checkbox = Mock()
        smart_tab.smart_checkbox.setChecked = Mock()
        smart_tab.smart_checkbox.isChecked = Mock(return_value=False)
        smart_tab.locations_combo = Mock()
        smart_tab.locations_combo.setCurrentIndex = Mock()
        smart_tab.locations_combo.currentIndex = Mock(return_value=0)

        # History tab
        history_tab = Mock()
        history_tab.sprite_selected = MockSignal()
        history_tab.clear_requested = MockSignal()
        history_tab.add_sprite = Mock()
        history_tab.clear_sprites = Mock()
        history_tab.list_widget = Mock()
        history_tab.list_widget.count = Mock(return_value=0)
        history_tab.list_widget.item = Mock(return_value=Mock())
        history_tab.summary_label = Mock()
        history_tab.summary_label.text = Mock(return_value="No sprites found yet")
        history_tab.clear_button = Mock()
        history_tab.clear_button.isEnabled = Mock(return_value=False)
        history_tab.clear_button.click = Mock()

        return {
            "browse_tab": browse_tab,
            "smart_tab": smart_tab,
            "history_tab": history_tab,
        }


# Convenience functions for backward compatibility
def create_mock_main_window(**kwargs: Any) -> MockMainWindowProtocol:
    """Backward compatibility function."""
    return MockFactory.create_main_window(**kwargs)


def create_mock_extraction_worker() -> MockExtractionWorkerProtocol:
    """Backward compatibility function."""
    return MockFactory.create_extraction_worker()


def create_mock_extraction_manager() -> MockExtractionManagerProtocol:
    """Backward compatibility function."""
    return MockFactory.create_extraction_manager()


def create_unified_dialog_services() -> dict[str, Mock]:
    """Convenience function for unified dialog service mocks."""
    return MockFactory.create_unified_dialog_services()


def create_signal_coordinator(services: Optional[dict[str, Mock | None]] = None) -> MockSignalCoordinatorProtocol:
    """Convenience function for signal coordinator mock."""
    return MockFactory.create_signal_coordinator(services)


def create_manual_offset_dialog_tabs() -> dict[str, Mock]:
    """Convenience function for dialog tab mocks."""
    return MockFactory.create_manual_offset_dialog_tabs()
