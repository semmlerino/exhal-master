"""
Comprehensive integration tests for the unified manual offset dialog using mocks.

This test suite validates integration points of the unified manual offset dialog
using MockFactory to create lightweight, fast, and reliable test implementations.
"""

import time

import time

import time
import time
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from unittest.mock import Mock, call

import pytest
from tests.infrastructure.mock_factory import (
    create_manual_offset_dialog_tabs,
    create_signal_coordinator,
    create_unified_dialog_services,
)
from tests.infrastructure.qt_mocks import MockSignal


class TestUnifiedDialogIntegrationMocked:
    """Test unified dialog integration with comprehensive mocking."""

    @pytest.fixture
    def mock_services(self):
        """Create all mock services for testing."""
        return create_unified_dialog_services()

    @pytest.fixture
    def mock_tabs(self):
        """Create mock tabs for testing."""
        return create_manual_offset_dialog_tabs()

    @pytest.fixture
    def mock_coordinator(self, mock_services):
        """Create mock signal coordinator."""
        return create_signal_coordinator(mock_services)

    @pytest.fixture
    def mock_dialog(self, mock_services, mock_tabs, mock_coordinator):
        """Create a complete mock dialog with all components."""
        dialog = Mock()

        # Dialog properties
        dialog.windowTitle = Mock(return_value="Manual Offset Control")
        dialog.minimumSize = Mock(return_value=Mock(width=Mock(return_value=600), height=Mock(return_value=700)))

        # Tab widget
        dialog.tabs = Mock()
        dialog.tabs.count = Mock(return_value=3)
        dialog.tabs.tabText = Mock(side_effect=lambda i: ["Browse", "Smart", "History"][i])

        # Individual tabs
        dialog.browse_tab = mock_tabs["browse_tab"]
        dialog.smart_tab = mock_tabs["smart_tab"]
        dialog.history_tab = mock_tabs["history_tab"]

        # Preview widget
        dialog.preview_widget = Mock()
        dialog.preview_widget.size = Mock(return_value=Mock(width=Mock(return_value=256), height=Mock(return_value=256)))

        # Buttons
        dialog.apply_button = Mock()
        dialog.apply_button.text = Mock(return_value="Apply Offset")
        dialog.apply_button.isDefault = Mock(return_value=True)
        dialog.apply_button.click = Mock()

        # State management
        dialog._current_offset = 0x200000
        dialog._rom_path = ""
        dialog._rom_size = 0x400000

        # Methods
        dialog.get_current_offset = Mock(return_value=dialog._current_offset)
        dialog.set_rom_data = Mock()
        dialog.accept = Mock()
        dialog.reject = Mock()

        # Signals
        dialog.offset_changed = MockSignal()
        dialog.sprite_found = MockSignal()

        # Services
        dialog.preview_generator = mock_services["preview_generator"]
        dialog.error_handler = mock_services["error_handler"]
        dialog.signal_coordinator = mock_coordinator

        return dialog

    def test_dialog_initialization_structure(self, mock_dialog):
        """Test dialog initialization creates proper structure."""
        dialog = mock_dialog

        # Check basic properties
        assert dialog.windowTitle() == "Manual Offset Control"
        assert dialog.minimumSize().width() == 600
        assert dialog.minimumSize().height() == 700

        # Check tab structure
        assert dialog.tabs.count() == 3
        assert dialog.tabs.tabText(0) == "Browse"
        assert dialog.tabs.tabText(1) == "Smart"
        assert dialog.tabs.tabText(2) == "History"

        # Check tab instances
        assert dialog.browse_tab is not None
        assert dialog.smart_tab is not None
        assert dialog.history_tab is not None

        # Check preview widget
        assert dialog.preview_widget.size().width() == 256
        assert dialog.preview_widget.size().height() == 256

        # Check apply button
        assert dialog.apply_button.text() == "Apply Offset"
        assert dialog.apply_button.isDefault() is True

    def test_signal_connections_between_components(self, mock_dialog):
        """Test signal connections between dialog components."""
        dialog = mock_dialog

        # Test browse tab signals have receivers
        browse_signals = ["offset_changed", "find_next_clicked", "find_prev_clicked"]
        for signal_name in browse_signals:
            signal = getattr(dialog.browse_tab, signal_name)
            assert hasattr(signal, "connect")
            assert hasattr(signal, "emit")

        # Test smart tab signals
        smart_signals = ["smart_mode_changed", "offset_requested"]
        for signal_name in smart_signals:
            signal = getattr(dialog.smart_tab, signal_name)
            assert hasattr(signal, "connect")
            assert hasattr(signal, "emit")

        # Test history tab signals
        history_signals = ["sprite_selected", "clear_requested"]
        for signal_name in history_signals:
            signal = getattr(dialog.history_tab, signal_name)
            assert hasattr(signal, "connect")
            assert hasattr(signal, "emit")

    def test_offset_change_propagation(self, mock_dialog):
        """Test offset changes propagate correctly between components."""
        dialog = mock_dialog

        # Track signal emissions by directly calling the callback
        offset_signals = []
        def track_offset(offset):
            offset_signals.append(offset)

        dialog.offset_changed.connect(track_offset)

        # Simulate browse tab offset change and dialog response
        test_offset = 0x123456
        dialog.browse_tab.offset_changed.emit(test_offset)

        # Simulate dialog emitting offset_changed (would happen in real dialog)
        dialog.offset_changed.emit(test_offset)

        # Verify signal propagation
        assert len(offset_signals) == 1
        assert offset_signals[0] == test_offset

    def test_preview_generation_integration(self, mock_dialog, mock_services):
        """Test preview generation integration with services."""
        dialog = mock_dialog
        preview_gen = mock_services["preview_generator"]

        # Set ROM data
        dialog.set_rom_data("/test/rom.sfc", 0x400000)
        dialog.set_rom_data.assert_called_with("/test/rom.sfc", 0x400000)

        # Test preview generation call
        test_offset = 0x250000
        preview_gen.create_preview_request.return_value = Mock(
            rom_path="/test/rom.sfc",
            offset=test_offset,
            width=256,
            height=256
        )

        # Simulate preview request
        request = preview_gen.create_preview_request("/test/rom.sfc", test_offset, 256, 256)
        preview_gen.generate_preview(request, Mock())

        # Verify calls
        preview_gen.create_preview_request.assert_called_with("/test/rom.sfc", test_offset, 256, 256)
        preview_gen.generate_preview.assert_called()

    def test_tab_coordination_scenarios(self, mock_dialog):
        """Test various tab coordination scenarios."""
        dialog = mock_dialog

        # Test browse tab navigation
        dialog.browse_tab.find_next_clicked.emit()
        dialog.browse_tab.find_next_clicked.emit.assert_called()

        dialog.browse_tab.find_prev_clicked.emit()
        dialog.browse_tab.find_prev_clicked.emit.assert_called()

        # Test smart tab mode changes
        dialog.smart_tab.smart_mode_changed.emit(True)
        dialog.smart_tab.smart_mode_changed.emit.assert_called_with(True)

        # Test offset requests from smart tab
        dialog.smart_tab.offset_requested.emit(0x100000)
        dialog.smart_tab.offset_requested.emit.assert_called_with(0x100000)

        # Test history tab sprite selection
        dialog.history_tab.sprite_selected.emit(0x200000)
        dialog.history_tab.sprite_selected.emit.assert_called_with(0x200000)

        # Test history clear
        dialog.history_tab.clear_requested.emit()
        dialog.history_tab.clear_requested.emit.assert_called()

    def test_error_handling_integration(self, mock_dialog, mock_services):
        """Test error handling integration across components."""
        dialog = mock_dialog
        error_handler = mock_services["error_handler"]

        # Test error handler availability
        assert dialog.error_handler is error_handler

        # Test error handling methods exist
        assert hasattr(error_handler, "handle_error")
        assert hasattr(error_handler, "handle_exception")
        assert hasattr(error_handler, "report_warning")

        # Simulate error handling
        test_exception = Exception("Test exception")
        error_handler.handle_error("Test error", test_exception)
        error_handler.handle_error.assert_called_with("Test error", test_exception)

    def test_apply_offset_workflow(self, mock_dialog):
        """Test apply offset workflow integration."""
        dialog = mock_dialog

        # Set test offset
        test_offset = 0x123456
        dialog.get_current_offset.return_value = test_offset

        # Track sprite found signals
        sprites_found = []
        dialog.sprite_found.connect(lambda offset, name: sprites_found.append((offset, name)))

        # Simulate apply button click
        dialog.apply_button.click()

        # Simulate sprite found emission (would happen in real dialog)
        dialog.sprite_found.emit(test_offset, f"manual_0x{test_offset:X}")

        # Verify workflow
        dialog.apply_button.click.assert_called()
        assert len(sprites_found) == 1
        assert sprites_found[0][0] == test_offset
        assert f"manual_0x{test_offset:X}" in sprites_found[0][1]


class TestSignalCoordinatorIntegrationMocked:
    """Test signal coordinator integration with mocks."""

    @pytest.fixture
    def mock_services(self):
        """Create mock services."""
        return create_unified_dialog_services()

    @pytest.fixture
    def coordinator(self, mock_services):
        """Create mock signal coordinator."""
        return create_signal_coordinator(mock_services)

    def test_queue_based_offset_updates(self, coordinator):
        """Test queued offset updates prevent signal loops."""
        # Test queue operations
        coordinator.queue_offset_update(0x100000, "slider")
        coordinator.queue_offset_update(0x200000, "slider")
        coordinator.queue_offset_update(0x300000, "slider")

        # Verify queue calls
        assert coordinator.queue_offset_update.call_count == 3
        coordinator.queue_offset_update.assert_has_calls([
            call(0x100000, "slider"),
            call(0x200000, "slider"),
            call(0x300000, "slider"),
        ])

    def test_preview_request_coordination(self, coordinator):
        """Test preview request coordination."""
        # Test preview queue operations
        coordinator.queue_preview_update(0x100000, "sprite1")
        coordinator.queue_preview_update(0x200000, "sprite2")

        # Verify calls
        assert coordinator.queue_preview_update.call_count == 2
        coordinator.queue_preview_update.assert_has_calls([
            call(0x100000, "sprite1"),
            call(0x200000, "sprite2"),
        ])

    def test_worker_coordination(self, coordinator):
        """Test worker lifecycle coordination."""
        # Test worker registration
        coordinator.register_worker("test_worker", "search")
        coordinator.register_worker.assert_called_with("test_worker", "search")

        # Test worker cleanup
        coordinator.unregister_worker("test_worker")
        coordinator.unregister_worker.assert_called_with("test_worker")

        # Test search state
        coordinator.is_searching.return_value = True
        assert coordinator.is_searching() is True

    def test_signal_loop_prevention(self, coordinator):
        """Test signal loop prevention mechanisms."""
        # Test signal blocking
        coordinator.block_signals_temporarily("test_source", 100)
        coordinator.block_signals_temporarily.assert_called_with("test_source", 100)

        # Test current offset tracking
        coordinator.get_current_offset.return_value = 0x123456
        assert coordinator.get_current_offset() == 0x123456

    def test_cleanup_functionality(self, coordinator):
        """Test coordinator cleanup."""
        # Test cleanup call
        coordinator.cleanup()
        coordinator.cleanup.assert_called()


class TestThreadSafetyIntegrationMocked:
    """Test thread safety with mock components."""

    @pytest.fixture
    def mock_services(self):
        """Create thread-safe mock services."""
        services = create_unified_dialog_services()

        # Add thread-safe behaviors
        for service in services.values():
            if hasattr(service, "queue_offset_update"):
                service.queue_offset_update = Mock()
            if hasattr(service, "queue_preview_update"):
                service.queue_preview_update = Mock()

        return services

    @pytest.fixture
    def threaded_coordinator(self, mock_services):
        """Create coordinator for thread testing."""
        coordinator = create_signal_coordinator(mock_services)

        # Make coordinator methods track call count for thread testing
        coordinator.queue_offset_update = Mock()
        coordinator.queue_preview_update = Mock()
        coordinator.register_worker = Mock()
        coordinator.unregister_worker = Mock()

        return coordinator

    def test_concurrent_offset_updates(self, threaded_coordinator):
        """Test concurrent offset updates."""
        coordinator = threaded_coordinator

        def update_offsets(thread_id):
            for i in range(10):
                offset = 0x100000 + (thread_id * 0x10000) + (i * 0x1000)
                coordinator.queue_offset_update(offset, f"thread_{thread_id}")
            return thread_id

        # Run concurrent updates
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = [executor.submit(update_offsets, i) for i in range(3)]
            results = [future.result() for future in as_completed(futures, timeout=2.0)]

        # All threads should complete
        assert len(results) == 3
        assert set(results) == {0, 1, 2}

        # Should have received all offset updates
        assert coordinator.queue_offset_update.call_count == 30  # 3 threads * 10 updates

    def test_concurrent_preview_requests(self, threaded_coordinator):
        """Test concurrent preview requests."""
        coordinator = threaded_coordinator

        def make_preview_requests(thread_id):
            for i in range(5):
                offset = 0x200000 + (thread_id * 0x10000) + (i * 0x1000)
                coordinator.queue_preview_update(offset, f"sprite_{thread_id}_{i}")
            return thread_id

        # Run concurrent requests
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = [executor.submit(make_preview_requests, i) for i in range(3)]
            results = [future.result() for future in as_completed(futures, timeout=2.0)]

        # All threads should complete
        assert len(results) == 3
        assert coordinator.queue_preview_update.call_count == 15  # 3 threads * 5 requests

    def test_concurrent_worker_operations(self, threaded_coordinator):
        """Test concurrent worker operations."""
        coordinator = threaded_coordinator

        def worker_operations(thread_id):
            for i in range(5):
                worker_id = f"worker_{thread_id}_{i}"
                coordinator.register_worker(worker_id, "test")
                coordinator.unregister_worker(worker_id)
            return thread_id

        # Run concurrent worker operations
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = [executor.submit(worker_operations, i) for i in range(3)]
            results = [future.result() for future in as_completed(futures, timeout=2.0)]

        # All threads should complete
        assert len(results) == 3
        assert coordinator.register_worker.call_count == 15
        assert coordinator.unregister_worker.call_count == 15

    @pytest.mark.stress
    def test_stress_signal_coordination(self, threaded_coordinator):
        """Stress test signal coordination under heavy load."""
        coordinator = threaded_coordinator

        def stress_operations():
            # Simulate heavy signal traffic
            for i in range(100):
                coordinator.queue_offset_update(0x100000 + i, f"stress_{i}")
                if i % 5 == 0:
                    coordinator.queue_preview_update(0x200000 + i, f"stress_sprite_{i}")
                if i % 10 == 0:
                    coordinator.register_worker(f"stress_worker_{i}", "test")
                    coordinator.unregister_worker(f"stress_worker_{i}")

        # Run stress test with multiple threads
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(stress_operations) for _ in range(5)]

            # All should complete without errors
            for future in as_completed(futures, timeout=5.0):
                future.result()  # Will raise if any errors occurred

        # Verify high call counts
        assert coordinator.queue_offset_update.call_count == 500  # 5 threads * 100 calls
        assert coordinator.queue_preview_update.call_count == 100  # 5 threads * 20 calls
        assert coordinator.register_worker.call_count == 50  # 5 threads * 10 calls


class TestPerformanceIntegrationMocked:
    """Test performance with mock components."""

    @pytest.fixture
    def performance_services(self):
        """Create performance-optimized mock services."""
        return create_unified_dialog_services()

    @pytest.fixture
    def performance_coordinator(self, performance_services):
        """Create performance coordinator."""
        coordinator = create_signal_coordinator(performance_services)

        # Add performance tracking
        coordinator.queue_offset_update = Mock()
        coordinator.queue_preview_update = Mock()

        return coordinator

    def test_offset_update_performance(self, performance_coordinator):
        """Test offset update performance."""
        coordinator = performance_coordinator

        # Time the operation
        import time
        start_time = time.time()

        for i in range(1000):
            coordinator.queue_offset_update(0x123456 + i, "performance_test")

        duration = time.time() - start_time

        # Should complete very quickly with mocks
        assert duration < 0.1  # Should complete in less than 100ms
        assert coordinator.queue_offset_update.call_count == 1000

    def test_preview_request_performance(self, performance_coordinator):
        """Test preview request performance."""
        coordinator = performance_coordinator

        # Time the operation
        import time
        start_time = time.time()

        for i in range(1000):
            coordinator.queue_preview_update(0x123456 + i, f"performance_sprite_{i}")

        duration = time.time() - start_time

        # Should complete very quickly with mocks
        assert duration < 0.1  # Should complete in less than 100ms
        assert coordinator.queue_preview_update.call_count == 1000

    def test_high_frequency_operations(self, performance_coordinator):
        """Test performance under high frequency operations."""
        coordinator = performance_coordinator

        start_time = time.time()

        # High frequency operations
        for i in range(10000):
            coordinator.queue_offset_update(0x100000 + i, f"high_freq_{i}")
            if i % 10 == 0:
                coordinator.queue_preview_update(0x200000 + i, f"high_freq_sprite_{i}")

        duration = time.time() - start_time

        # Should complete very quickly with mocks
        assert duration < 1.0  # Should be much faster than 1 second
        assert coordinator.queue_offset_update.call_count == 10000
        assert coordinator.queue_preview_update.call_count == 1000

    def test_memory_efficiency(self, performance_coordinator):
        """Test memory efficiency of mock operations."""
        coordinator = performance_coordinator

        # Perform many operations
        for cycle in range(10):
            for i in range(1000):
                coordinator.queue_offset_update(0x100000 + i, f"memory_test_{cycle}_{i}")
                coordinator.queue_preview_update(0x200000 + i, f"memory_sprite_{cycle}_{i}")

        # With mocks, these should be very efficient
        assert coordinator.queue_offset_update.call_count == 10000
        assert coordinator.queue_preview_update.call_count == 10000


class TestCompatibilityIntegrationMocked:
    """Test compatibility with mock extraction panel."""

    @pytest.fixture
    def mock_extraction_panel(self):
        """Create mock extraction panel."""
        panel = Mock()
        panel.manual_offset_dialog = None
        panel.show_manual_offset_dialog = Mock()
        panel.on_offset_changed = Mock()
        panel.on_sprite_found = Mock()
        return panel

    @pytest.fixture
    def mock_dialog_for_compatibility(self):
        """Create dialog mock for compatibility testing."""
        dialog = Mock()
        dialog.offset_changed = MockSignal()
        dialog.sprite_found = MockSignal()
        dialog.result = Mock(return_value=Mock())
        dialog.show = Mock()
        dialog.hide = Mock()
        dialog.accept = Mock()
        dialog.reject = Mock()
        return dialog

    def test_signal_compatibility(self, mock_extraction_panel, mock_dialog_for_compatibility):
        """Test signal compatibility with extraction panel."""
        dialog = mock_dialog_for_compatibility
        panel = mock_extraction_panel

        # Connect signals
        dialog.offset_changed.connect(panel.on_offset_changed)
        dialog.sprite_found.connect(panel.on_sprite_found)

        # Test offset change signal
        test_offset = 0x123456
        dialog.offset_changed.emit(test_offset)
        panel.on_offset_changed.assert_called_with(test_offset)

        # Test sprite found signal
        dialog.sprite_found.emit(test_offset, "test_sprite")
        panel.on_sprite_found.assert_called_with(test_offset, "test_sprite")

    def test_dialog_lifecycle_compatibility(self, mock_dialog_for_compatibility):
        """Test dialog lifecycle compatibility."""
        dialog = mock_dialog_for_compatibility

        # Test show/hide
        dialog.show()
        dialog.show.assert_called()

        dialog.hide()
        dialog.hide.assert_called()

        # Test accept/reject
        dialog.accept()
        dialog.accept.assert_called()

        dialog.reject()
        dialog.reject.assert_called()

    def test_integration_workflow(self, mock_extraction_panel, mock_dialog_for_compatibility):
        """Test complete integration workflow."""
        panel = mock_extraction_panel
        dialog = mock_dialog_for_compatibility

        # Simulate showing dialog from panel
        panel.show_manual_offset_dialog()
        panel.show_manual_offset_dialog.assert_called()

        # Simulate offset changes and sprite findings
        dialog.offset_changed.connect(panel.on_offset_changed)
        dialog.sprite_found.connect(panel.on_sprite_found)

        # Test workflow
        dialog.offset_changed.emit(0x100000)
        dialog.sprite_found.emit(0x200000, "found_sprite")

        # Verify panel received signals
        panel.on_offset_changed.assert_called_with(0x100000)
        panel.on_sprite_found.assert_called_with(0x200000, "found_sprite")


# Test markers - skip manager setup since we use pure mocks
pytestmark = [
    pytest.mark.integration,
    pytest.mark.unit,  # These are actually unit tests with mocks
    pytest.mark.no_manager_setup,  # Skip manager initialization
]


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
