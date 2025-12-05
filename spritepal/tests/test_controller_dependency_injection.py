"""
Test dependency injection functionality for ExtractionController.

These tests verify that:
1. Backward compatibility is maintained (using global registry)
2. Dependency injection works with custom managers
3. The controller properly uses injected managers
"""
from __future__ import annotations

from unittest.mock import Mock

import pytest
from core.controller import ExtractionController
from core.managers import ExtractionManager, InjectionManager, SessionManager

# Systematic pytest markers applied based on test content analysis
pytestmark = [
    pytest.mark.headless,
    pytest.mark.mock_only,
    pytest.mark.no_qt,
    pytest.mark.parallel_safe,
    pytest.mark.rom_data,
    pytest.mark.unit,
    pytest.mark.cache,
    pytest.mark.ci_safe,
    pytest.mark.signals_slots,
]

class TestControllerDependencyInjection:
    """Test dependency injection functionality for ExtractionController."""

    @pytest.mark.skip(reason="Requires managers to be initialized via initialize_managers() - global registry not available")
    def test_backward_compatibility_uses_global_registry(self):
        """Test that controller works without injected managers (backward compatibility)."""
        mock_main_window = Mock()

        # Create controller without injected managers
        controller = ExtractionController(mock_main_window)

        # Verify managers are from global registry
        assert isinstance(controller.extraction_manager, ExtractionManager)
        assert isinstance(controller.session_manager, SessionManager)
        assert isinstance(controller.injection_manager, InjectionManager)

    def test_dependency_injection_with_custom_managers(self):
        """Test that controller uses injected managers when provided."""
        mock_main_window = Mock()

        # Create mock managers that satisfy the protocol
        real_extraction_manager = Mock(spec=ExtractionManager)
        real_session_manager = Mock(spec=SessionManager)
        real_injection_manager = Mock(spec=InjectionManager)

        # Create controller with injected managers
        controller = ExtractionController(
            mock_main_window,
            extraction_manager=real_extraction_manager,
            session_manager=real_session_manager,
            injection_manager=real_injection_manager
        )

        # Verify the exact same objects are used
        assert controller.extraction_manager is real_extraction_manager
        assert controller.session_manager is real_session_manager
        assert controller.injection_manager is real_injection_manager

    @pytest.mark.skip(reason="Requires managers to be initialized via initialize_managers() - global registry not available")
    def test_partial_dependency_injection(self):
        """Test that controller can have some managers injected and others from registry."""
        mock_main_window = Mock()

        # Create only extraction manager mock
        real_extraction_manager = Mock(spec=ExtractionManager)

        # Create controller with only extraction manager injected
        controller = ExtractionController(
            mock_main_window,
            extraction_manager=real_extraction_manager
        )

        # Verify extraction manager is the injected one
        assert controller.extraction_manager is real_extraction_manager

        # Verify other managers are from global registry
        assert isinstance(controller.session_manager, SessionManager)
        assert isinstance(controller.injection_manager, InjectionManager)

    def test_controller_signals_connected_with_injected_managers(self):
        """Test that controller properly connects signals with injected managers."""
        mock_main_window = Mock()

        # Create mock managers with signal attributes
        real_extraction_manager = Mock(spec=ExtractionManager)
        real_injection_manager = Mock(spec=InjectionManager)
        real_session_manager = Mock(spec=SessionManager)

        # Set up signals as Mock objects
        real_extraction_manager.cache_operation_started = Mock()
        real_extraction_manager.cache_hit = Mock()
        real_extraction_manager.cache_miss = Mock()
        real_extraction_manager.cache_saved = Mock()

        real_injection_manager.injection_progress = Mock()
        real_injection_manager.injection_finished = Mock()
        real_injection_manager.cache_saved = Mock()

        # Create controller with injected managers
        ExtractionController(
            mock_main_window,
            extraction_manager=real_extraction_manager,
            session_manager=real_session_manager,
            injection_manager=real_injection_manager
        )

        # Verify signals were connected
        assert real_extraction_manager.cache_operation_started.connect.called
        assert real_extraction_manager.cache_hit.connect.called
        assert real_injection_manager.injection_progress.connect.called
        assert real_injection_manager.injection_finished.connect.called

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
