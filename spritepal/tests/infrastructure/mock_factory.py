"""
Consolidated mock factory for SpritePal tests.

This module provides a single, comprehensive factory for creating all types of mocks
used across the test suite, eliminating duplication and inconsistencies.
"""

import warnings
from typing import Any, Optional, cast
from unittest.mock import Mock

from .qt_mocks import (
    QT_AVAILABLE,
    MockSignal,
    TestMainWindow,
    create_mock_signals,
    create_signal_holder,
)

if QT_AVAILABLE:
    from PyQt6.QtCore import pyqtSignal
else:
    pyqtSignal = MockSignal
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

    .. deprecated:: 2.0
        MockFactory is deprecated in favor of RealComponentFactory which provides:
        - Type-safe component creation without unsafe cast() operations
        - Real managers with test data injection
        - Better integration testing capabilities
        - Elimination of mock-related bugs

        Migration guide:
        - Replace MockFactory.create_main_window() with RealComponentFactory.create_main_window()
        - Replace MockFactory.create_extraction_manager() with RealComponentFactory.create_extraction_manager()
        - See tests/infrastructure/migration_helpers.py for automated migration tools

    This factory still works but emits deprecation warnings to guide migration.
    """

    @staticmethod
    def create_main_window(with_extraction_params: bool = True) -> MockMainWindowProtocol:
        """
        Create a comprehensive mock main window.

        .. deprecated:: 2.0
            Use RealComponentFactory.create_main_window() instead:

            # Old (deprecated):
            window = MockFactory.create_main_window()

            # New (recommended):
            from tests.infrastructure.real_component_factory import RealComponentFactory
            factory = RealComponentFactory()
            window = factory.create_main_window()

        Args:
            with_extraction_params: Whether to include default extraction parameters

        Returns:
            Mock main window configured for controller testing
        """
        warnings.warn(
            "MockFactory.create_main_window() is deprecated. "
            "Use RealComponentFactory.create_main_window() for type-safe testing. "
            "Run 'python tests/infrastructure/migration_helpers.py analyze' to find all mock usage.",
            DeprecationWarning,
            stacklevel=2
        )
        if QT_AVAILABLE:
            # Use QObject-based test double with real signals
            window = TestMainWindow()

            # Override extraction params if needed
            if not with_extraction_params:
                window.get_extraction_params = Mock()

            return cast(MockMainWindowProtocol, window)
        # Fallback for non-Qt environments - use pure Mock
        window = Mock()

        # Add mock signals
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

        # Create mock extraction panel
        window.extraction_panel = Mock()
        window.extraction_panel.offset_changed = MockSignal()
        window.extraction_panel.get_vram_path = Mock(return_value="/test/vram.dmp")
        window.extraction_panel.get_cgram_path = Mock(return_value="/test/cgram.dmp")
        window.extraction_panel.get_oam_path = Mock(return_value=None)
        window.extraction_panel.get_output_base = Mock(return_value="/test/output")
        window.extraction_panel.get_vram_offset = Mock(return_value=0xC000)

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

        .. deprecated:: 2.0
            Use RealComponentFactory.create_extraction_worker() instead.

        Returns:
            Mock worker with all extraction signals configured
        """
        warnings.warn(
            "MockFactory.create_extraction_worker() is deprecated. "
            "Use RealComponentFactory.create_extraction_worker() for real worker testing.",
            DeprecationWarning,
            stacklevel=2
        )
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
    def create_real_extraction_manager_with_mocked_io() -> Any:
        """
        Create a real ExtractionManager with only I/O operations mocked.

        This provides better test coverage by using real business logic
        while still maintaining test isolation from the file system.

        Returns:
            Real ExtractionManager with mocked I/O operations
        """
        from unittest.mock import Mock

        from core.managers import ExtractionManager

        # Create real manager
        manager = ExtractionManager()

        # Mock only the I/O operations
        manager._load_vram_data = Mock(return_value=bytearray(0x10000))  # 64KB VRAM
        manager._load_cgram_data = Mock(return_value=bytearray(512))     # 512B CGRAM
        manager._save_sprite_image = Mock(return_value=True)
        manager._save_metadata = Mock(return_value=True)

        # Keep real validation and extraction logic
        return manager

    @staticmethod
    def create_extraction_manager() -> MockExtractionManagerProtocol:
        """
        Create a mock extraction manager.

        .. deprecated:: 2.0
            Use RealComponentFactory.create_extraction_manager() instead.

        Returns:
            Mock extraction manager with core methods
        """
        warnings.warn(
            "MockFactory.create_extraction_manager() is deprecated. "
            "Use RealComponentFactory.create_extraction_manager() for real manager testing.",
            DeprecationWarning,
            stacklevel=2
        )
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
    def create_real_injection_manager_with_mocked_io() -> Any:
        """
        Create a real InjectionManager with only I/O operations mocked.

        Returns:
            Real InjectionManager with mocked I/O operations
        """
        from unittest.mock import Mock

        from core.managers import InjectionManager

        # Create real manager
        manager = InjectionManager()

        # Mock only the I/O operations
        manager._load_sprite_image = Mock(return_value=Mock())  # Mock PIL Image
        manager._load_metadata = Mock(return_value={})
        manager._save_vram_file = Mock(return_value=True)
        manager._save_rom_file = Mock(return_value=True)

        return manager

    @staticmethod
    def create_injection_manager() -> MockInjectionManagerProtocol:
        """
        Create a mock injection manager.

        .. deprecated:: 2.0
            Use RealComponentFactory.create_injection_manager() instead.

        Returns:
            Mock injection manager with core methods
        """
        warnings.warn(
            "MockFactory.create_injection_manager() is deprecated. "
            "Use RealComponentFactory.create_injection_manager() for real manager testing.",
            DeprecationWarning,
            stacklevel=2
        )
        manager = Mock()
        manager.inject_sprite = Mock()
        manager.validate_injection_params = Mock(return_value=True)
        manager.create_worker = Mock()

        # Standard signals
        if QT_AVAILABLE:
            signal_holder = create_signal_holder(
                injection_started=pyqtSignal(),
                injection_progress=pyqtSignal(int),
                injection_complete=pyqtSignal(object),
                injection_failed=pyqtSignal(str)
            )
            manager.injection_started = signal_holder.injection_started
            manager.injection_progress = signal_holder.injection_progress
            manager.injection_complete = signal_holder.injection_complete
            manager.injection_failed = signal_holder.injection_failed
        else:
            manager.injection_started = MockSignal()
            manager.injection_progress = MockSignal()
            manager.injection_complete = MockSignal()
            manager.injection_failed = MockSignal()

        return cast(MockInjectionManagerProtocol, manager)

    @staticmethod
    def create_real_session_manager_with_mocked_io() -> Any:
        """
        Create a real SessionManager with only I/O operations mocked.

        Returns:
            Real SessionManager with mocked I/O operations
        """
        from unittest.mock import Mock

        from core.managers import SessionManager

        # Create real manager with test app name
        manager = SessionManager("TestApp")

        # Mock only the file I/O operations
        manager._save_to_file = Mock(return_value=True)
        manager._load_from_file = Mock(return_value={})

        return manager

    @staticmethod
    def create_session_manager() -> MockSessionManagerProtocol:
        """
        Create a mock session manager.

        .. deprecated:: 2.0
            Use RealComponentFactory.create_session_manager() instead.

        Returns:
            Mock session manager with persistence methods
        """
        warnings.warn(
            "MockFactory.create_session_manager() is deprecated. "
            "Use RealComponentFactory.create_session_manager() for real manager testing.",
            DeprecationWarning,
            stacklevel=2
        )
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

        .. deprecated:: 2.0
            File dialogs should be tested with real Qt components when possible.

        Returns:
            Dictionary of mock file dialog functions
        """
        warnings.warn(
            "MockFactory.create_file_dialogs() is deprecated. "
            "Consider using real Qt components with test data instead.",
            DeprecationWarning,
            stacklevel=2
        )
        return {
            "getOpenFileName": Mock(return_value=("test_file.dmp", "Memory dump (*.dmp)")),
            "getSaveFileName": Mock(return_value=("output.png", "PNG files (*.png)")),
            "getExistingDirectory": Mock(return_value="/test/directory"),
        }

    @staticmethod
    def create_qimage(width: int = 128, height: int = 128) -> Mock:
        """
        Create a mock QImage for image processing tests.

        .. deprecated:: 2.0
            Use real QImage objects for more accurate testing.

        Args:
            width: Image width
            height: Image height

        Returns:
            Mock QImage with specified dimensions
        """
        warnings.warn(
            "MockFactory.create_qimage() is deprecated. "
            "Use real QImage objects from PyQt6.QtGui for accurate image testing.",
            DeprecationWarning,
            stacklevel=2
        )
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

        .. deprecated:: 2.0
            Use RealComponentFactory.create_rom_cache() instead.

        Returns:
            Mock ROM cache with standard methods
        """
        warnings.warn(
            "MockFactory.create_rom_cache() is deprecated. "
            "Use RealComponentFactory.create_rom_cache() for real cache testing.",
            DeprecationWarning,
            stacklevel=2
        )
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

        .. deprecated:: 2.0
            Dialog services should use real components for better integration testing.

        Returns:
            Dictionary of mock services implementing dialog protocols
        """
        warnings.warn(
            "MockFactory.create_unified_dialog_services() is deprecated. "
            "Consider using real dialog components with test data injection.",
            DeprecationWarning,
            stacklevel=2
        )
        # Preview generator
        preview_generator = Mock()
        preview_generator.create_preview_request = Mock()
        preview_generator.generate_preview = Mock()
        if QT_AVAILABLE:
            pg_signals = create_signal_holder(
                preview_ready=pyqtSignal(bytes, int, int, str),
                preview_error=pyqtSignal(str)
            )
            preview_generator.preview_ready = pg_signals.preview_ready
            preview_generator.preview_error = pg_signals.preview_error
        else:
            preview_generator.preview_ready = MockSignal()
            preview_generator.preview_error = MockSignal()

        # Error handler
        error_handler = Mock()
        error_handler.handle_error = Mock()
        error_handler.handle_exception = Mock()
        error_handler.report_warning = Mock()

        # Offset navigator
        offset_navigator = Mock()
        if QT_AVAILABLE:
            on_signals = create_signal_holder(
                offset_changed=pyqtSignal(int),
                navigation_bounds_changed=pyqtSignal(int, int),
                step_size_changed=pyqtSignal(int)
            )
            offset_navigator.offset_changed = on_signals.offset_changed
            offset_navigator.navigation_bounds_changed = on_signals.navigation_bounds_changed
            offset_navigator.step_size_changed = on_signals.step_size_changed
        else:
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
        if QT_AVAILABLE:
            pc_signals = create_signal_holder(
                preview_requested=pyqtSignal(int),
                preview_ready=pyqtSignal(bytes, int, int, str),
                preview_error=pyqtSignal(str),
                preview_cleared=pyqtSignal()
            )
            preview_coordinator.preview_requested = pc_signals.preview_requested
            preview_coordinator.preview_ready = pc_signals.preview_ready
            preview_coordinator.preview_error = pc_signals.preview_error
            preview_coordinator.preview_cleared = pc_signals.preview_cleared
        else:
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
        if QT_AVAILABLE:
            sr_signals = create_signal_holder(
                sprite_added=pyqtSignal(int, object),
                sprite_removed=pyqtSignal(int),
                sprites_cleared=pyqtSignal(),
                sprites_imported=pyqtSignal(int)
            )
            sprites_registry.sprite_added = sr_signals.sprite_added
            sprites_registry.sprite_removed = sr_signals.sprite_removed
            sprites_registry.sprites_cleared = sr_signals.sprites_cleared
            sprites_registry.sprites_imported = sr_signals.sprites_imported
        else:
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
        if QT_AVAILABLE:
            wm_signals = create_signal_holder(
                worker_started=pyqtSignal(str),
                worker_finished=pyqtSignal(str),
                worker_error=pyqtSignal(str, object)
            )
            worker_manager.worker_started = wm_signals.worker_started
            worker_manager.worker_finished = wm_signals.worker_finished
            worker_manager.worker_error = wm_signals.worker_error
        else:
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

        .. deprecated:: 2.0
            Signal coordinators should use real Qt signals for accurate testing.

        Args:
            services: Optional dictionary of mock services to use

        Returns:
            Mock signal coordinator with all required signals and methods
        """
        warnings.warn(
            "MockFactory.create_signal_coordinator() is deprecated. "
            "Use real signal coordination with Qt's signal/slot mechanism.",
            DeprecationWarning,
            stacklevel=2
        )
        coordinator = Mock()

        if QT_AVAILABLE:
            # External compatibility signals
            ext_signals = create_signal_holder(
                offset_changed=pyqtSignal(int),
                sprite_found=pyqtSignal(int, object),
                preview_requested=pyqtSignal(int),
                search_started=pyqtSignal(),
                search_completed=pyqtSignal(int)
            )
            coordinator.offset_changed = ext_signals.offset_changed
            coordinator.sprite_found = ext_signals.sprite_found
            coordinator.preview_requested = ext_signals.preview_requested
            coordinator.search_started = ext_signals.search_started
            coordinator.search_completed = ext_signals.search_completed

            # Internal coordination signals
            int_signals = create_signal_holder(
                tab_switch_requested=pyqtSignal(int),
                update_title_requested=pyqtSignal(str),
                status_message=pyqtSignal(str),
                navigation_enabled=pyqtSignal(bool),
                step_size_synchronized=pyqtSignal(int),
                preview_update_queued=pyqtSignal(int),
                preview_generation_started=pyqtSignal(),
                preview_generation_completed=pyqtSignal()
            )
            coordinator.tab_switch_requested = int_signals.tab_switch_requested
            coordinator.update_title_requested = int_signals.update_title_requested
            coordinator.status_message = int_signals.status_message
            coordinator.navigation_enabled = int_signals.navigation_enabled
            coordinator.step_size_synchronized = int_signals.step_size_synchronized
            coordinator.preview_update_queued = int_signals.preview_update_queued
            coordinator.preview_generation_started = int_signals.preview_generation_started
            coordinator.preview_generation_completed = int_signals.preview_generation_completed
        else:
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

        .. deprecated:: 2.0
            Dialog tabs should use real Qt widgets for accurate UI testing.

        Returns:
            Dictionary containing mock tabs for browse, smart, and history
        """
        warnings.warn(
            "MockFactory.create_manual_offset_dialog_tabs() is deprecated. "
            "Use real dialog components for better UI testing.",
            DeprecationWarning,
            stacklevel=2
        )
        # Browse tab
        browse_tab = Mock()
        if QT_AVAILABLE:
            browse_signals = create_signal_holder(
                offset_changed=pyqtSignal(int),
                find_next_clicked=pyqtSignal(),
                find_prev_clicked=pyqtSignal()
            )
            browse_tab.offset_changed = browse_signals.offset_changed
            browse_tab.find_next_clicked = browse_signals.find_next_clicked
            browse_tab.find_prev_clicked = browse_signals.find_prev_clicked
        else:
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
        if QT_AVAILABLE:
            smart_signals = create_signal_holder(
                smart_mode_changed=pyqtSignal(bool),
                offset_requested=pyqtSignal(int)
            )
            smart_tab.smart_mode_changed = smart_signals.smart_mode_changed
            smart_tab.offset_requested = smart_signals.offset_requested
        else:
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
        if QT_AVAILABLE:
            history_signals = create_signal_holder(
                sprite_selected=pyqtSignal(int),
                clear_requested=pyqtSignal()
            )
            history_tab.sprite_selected = history_signals.sprite_selected
            history_tab.clear_requested = history_signals.clear_requested
        else:
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
    """Backward compatibility function.

    .. deprecated:: 2.0
        Use RealComponentFactory.create_main_window() instead.
    """
    warnings.warn(
        "create_mock_main_window() is deprecated. "
        "Use RealComponentFactory.create_main_window() instead.",
        DeprecationWarning,
        stacklevel=2
    )
    return MockFactory.create_main_window(**kwargs)


def create_mock_extraction_worker() -> MockExtractionWorkerProtocol:
    """Backward compatibility function.

    .. deprecated:: 2.0
        Use RealComponentFactory.create_extraction_worker() instead.
    """
    warnings.warn(
        "create_mock_extraction_worker() is deprecated. "
        "Use RealComponentFactory.create_extraction_worker() instead.",
        DeprecationWarning,
        stacklevel=2
    )
    return MockFactory.create_extraction_worker()


def create_mock_extraction_manager() -> MockExtractionManagerProtocol:
    """Backward compatibility function.

    .. deprecated:: 2.0
        Use RealComponentFactory.create_extraction_manager() instead.
    """
    warnings.warn(
        "create_mock_extraction_manager() is deprecated. "
        "Use RealComponentFactory.create_extraction_manager() instead.",
        DeprecationWarning,
        stacklevel=2
    )
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
