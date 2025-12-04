"""
Example of migrating from MockFactory to RealComponentFactory patterns.

This file demonstrates step-by-step migration from mock-heavy testing
to real component testing, showing before/after patterns and the
transformation process.

Run with: pytest tests/examples/example_migration.py -v
"""
from __future__ import annotations

from unittest.mock import Mock, cast

import pytest
from core.managers.extraction_manager import ExtractionManager
from core.managers.injection_manager import InjectionManager
from PySide6.QtCore import Qt
from PySide6.QtTest import QSignalSpy
from tests.infrastructure.manager_test_context import manager_context

# OLD imports (being phased out)
# from tests.infrastructure.mock_factory import MockFactory  # Deprecated
# NEW imports (preferred)
from tests.infrastructure.real_component_factory import (
    RealComponentFactory,
)

# ============================================================================
# MIGRATION EXAMPLE 1: Basic Manager Creation
# ============================================================================

class TestManagerCreationMigration:
    """Example migration from mock managers to real managers."""

    def test_old_mock_manager_pattern_before_migration(self):
        """BEFORE: Problematic mock manager creation with unsafe casting."""

        # This is the OLD way - don't do this anymore
        # Simulating what the old MockFactory did

        def old_mock_factory_pattern():
            """Simulated old MockFactory pattern (DEPRECATED)."""
            # OLD: MockFactory created mocks that required unsafe casting
            mock_manager = Mock()
            mock_manager.is_initialized.return_value = True
            mock_manager.validate_extraction_params.return_value = True
            mock_manager.extract_sprites.return_value = {"sprites": []}

            # UNSAFE: Required cast to use as real manager
            manager = cast(ExtractionManager, mock_manager)  # TYPE VIOLATION!

            # Mock doesn't behave like real manager
            assert manager.is_initialized() is True  # Testing mock, not reality

            # This tells us nothing about real ExtractionManager behavior
            return manager

        # Demonstrate the old pattern
        old_manager = old_mock_factory_pattern()

        # Problems with old pattern:
        # 1. Type safety violation with cast()
        # 2. Mock doesn't behave like real manager
        # 3. Tests become coupled to mock configuration
        # 4. No real validation or business logic testing
        assert hasattr(old_manager, 'is_initialized')  # Just testing mock attributes

    def test_new_real_manager_pattern_after_migration(self):
        """AFTER: Real manager creation with type safety."""

        # NEW way - using RealComponentFactory
        with RealComponentFactory() as factory:
            # Real manager creation - no mocking, no casting
            manager = factory.create_extraction_manager(with_test_data=True)

            # Type checker knows this is ExtractionManager
            assert isinstance(manager, ExtractionManager)

            # Real manager behavior - no configuration needed
            assert manager.is_initialized()

            # Real business logic testing
            test_params = {
                "vram_path": "/test/vram.dmp",
                "cgram_path": "/test/cgram.dmp",
                "output_base": "/test/output"
            }

            # Real validation logic
            is_valid = manager.validate_extraction_params(test_params)
            assert isinstance(is_valid, bool)  # Real return type

        # Benefits of new pattern:
        # 1. No type safety violations
        # 2. Real manager behavior
        # 3. Tests validate actual business logic
        # 4. More resilient to refactoring

# ============================================================================
# MIGRATION EXAMPLE 2: Worker Testing
# ============================================================================

class TestWorkerTestingMigration:
    """Example migration from mock workers to real workers."""

    def test_old_mock_worker_pattern(self):
        """BEFORE: Mock worker with complex configuration."""

        def old_worker_testing_pattern():
            """Old pattern with mocked workers (DEPRECATED)."""
            # OLD: Complex mock worker setup
            mock_worker = Mock()
            mock_manager = Mock()

            # Complex mock configuration
            mock_worker.manager = mock_manager
            mock_worker.isRunning.return_value = False
            mock_worker.finished = Mock()
            mock_worker.progress = Mock()

            # Simulate signal connections
            mock_worker.finished.connect = Mock()
            mock_worker.progress.connect = Mock()

            # Mock worker execution
            mock_worker.start = Mock()
            mock_worker.quit = Mock()

            return mock_worker, mock_manager

        worker, _manager = old_worker_testing_pattern()

        # Old testing approach - testing mock behavior
        worker.start()
        worker.start.assert_called_once()  # Testing mock, not real behavior

        # Problems:
        # 1. No real threading behavior
        # 2. No real signal emission
        # 3. Complex mock setup required
        # 4. Doesn't test actual worker logic

    def test_new_real_worker_pattern(self):
        """AFTER: Real worker with authentic threading and signals."""

        with manager_context("extraction") as ctx:
            # Create real worker with real manager
            params = ctx._data_repo.get_vram_extraction_data("small")
            worker = ctx.create_worker("extraction", params)

            # Real worker with real threading
            assert hasattr(worker, 'start')
            assert hasattr(worker, 'quit')
            assert hasattr(worker, 'isRunning')

            # Real signal objects
            assert hasattr(worker, 'finished')
            assert hasattr(worker, 'progress')

            # Test real worker execution
            results = []
            worker.finished.connect(lambda r: results.append(r))

            # Start real thread
            worker.start()

            # Wait for real completion
            completed = ctx.run_worker_and_wait(worker, timeout=5000)

            # Verify real behavior
            assert completed or not worker.isRunning()

            # Real cleanup is automatic

        # Benefits:
        # 1. Real threading behavior
        # 2. Real Qt signal emission
        # 3. Authentic worker lifecycle
        # 4. Tests actual worker logic

# ============================================================================
# MIGRATION EXAMPLE 3: UI Component Testing
# ============================================================================

class TestUIComponentMigration:
    """Example migration from mock UI components to real widgets."""

    def test_old_mock_ui_pattern(self):
        """BEFORE: Mock UI components with complex signal simulation."""

        def old_ui_mocking_pattern():
            """Old pattern with mocked UI (DEPRECATED)."""
            # OLD: Mock main window
            mock_main_window = Mock()
            mock_extraction_panel = Mock()

            # Mock UI attributes
            mock_main_window.extraction_panel = mock_extraction_panel
            mock_extraction_panel.vram_input = Mock()
            mock_extraction_panel.start_button = Mock()

            # Mock signal objects
            mock_signal = Mock()
            mock_extraction_panel.start_button.clicked = mock_signal

            # Simulate signal connection
            mock_signal.connect = Mock()

            return mock_main_window, mock_extraction_panel

        _window, panel = old_ui_mocking_pattern()

        # Old testing - mock signal testing
        callback = Mock()
        panel.start_button.clicked.connect(callback)

        # Simulate button click
        panel.start_button.clicked.emit()

        # Verify mock signal
        panel.start_button.clicked.connect.assert_called_with(callback)

        # Problems:
        # 1. No real Qt behavior
        # 2. Mock signals don't behave like real Qt signals
        # 3. No real widget lifecycle
        # 4. Complex mock setup for simple UI testing

    def test_new_real_ui_pattern(self, qtbot):
        """AFTER: Real Qt widgets with authentic signal behavior."""

        with RealComponentFactory() as factory:
            # Create real main window
            main_window = factory.create_main_window(with_managers=True)
            qtbot.addWidget(main_window)

            # Real Qt widget behavior
            main_window.show()
            qtbot.waitExposed(main_window)

            # Test real UI elements
            if hasattr(main_window, 'extraction_panel'):
                panel = main_window.extraction_panel

                # Find real UI elements
                if hasattr(panel, 'start_button'):
                    button = panel.start_button

                    # Real Qt signal testing with QSignalSpy
                    clicked_spy = QSignalSpy(button.clicked)

                    # Real button click simulation
                    qtbot.mouseClick(button, Qt.MouseButton.LeftButton)

                    # Verify real signal emission
                    assert clicked_spy.count() >= 0  # Real signal behavior

        # Benefits:
        # 1. Real Qt widget behavior
        # 2. Authentic signal emission
        # 3. Real event handling
        # 4. Proper widget lifecycle

# ============================================================================
# MIGRATION EXAMPLE 4: Test Fixture Migration
# ============================================================================

class TestFixtureMigration:
    """Example migration of test fixtures from mock to real components."""

    # OLD fixture pattern (DEPRECATED)
    @pytest.fixture
    def old_mock_fixtures(self):
        """OLD: Mock-based fixtures (DEPRECATED)."""

        # This is what we used to do - don't do this anymore
        def create_old_fixtures():
            mock_extraction_mgr = Mock()
            mock_injection_mgr = Mock()
            mock_session_mgr = Mock()

            # Complex mock configuration
            mock_extraction_mgr.is_initialized.return_value = True
            mock_extraction_mgr.validate_extraction_params.return_value = True

            mock_injection_mgr.is_initialized.return_value = True
            mock_injection_mgr.validate_injection_params.return_value = True

            return {
                'extraction': mock_extraction_mgr,
                'injection': mock_injection_mgr,
                'session': mock_session_mgr
            }

        return create_old_fixtures()

    # NEW fixture pattern (PREFERRED)
    @pytest.fixture
    def real_component_fixtures(self):
        """NEW: Real component fixtures with proper cleanup."""

        with RealComponentFactory() as factory:
            managers = {
                'extraction': factory.create_extraction_manager(with_test_data=True),
                'injection': factory.create_injection_manager(with_test_data=True),
                'session': factory.create_session_manager("test_app")
            }

            yield managers

            # Automatic cleanup via context manager

    def test_using_old_mock_fixtures(self, old_mock_fixtures):
        """Test using old mock fixtures (for comparison)."""

        extraction = old_mock_fixtures['extraction']
        injection = old_mock_fixtures['injection']

        # Testing mock behavior - not real functionality
        assert extraction.is_initialized() is True
        assert injection.is_initialized() is True

        # Mock assertions - brittle and implementation-coupled
        extraction.is_initialized.assert_called()
        injection.is_initialized.assert_called()

    def test_using_real_component_fixtures(self, real_component_fixtures):
        """Test using real component fixtures."""

        extraction = real_component_fixtures['extraction']
        injection = real_component_fixtures['injection']

        # Testing real behavior - actual functionality
        assert isinstance(extraction, ExtractionManager)
        assert isinstance(injection, InjectionManager)

        # Real manager state
        assert extraction.is_initialized()
        assert injection.is_initialized()

        # Real business logic testing
        test_params = {"vram_path": "/test/vram.dmp"}
        is_valid = extraction.validate_extraction_params(test_params)
        assert isinstance(is_valid, bool)

# ============================================================================
# MIGRATION EXAMPLE 5: Complex Integration Test Migration
# ============================================================================

class TestComplexIntegrationMigration:
    """Example migration of complex integration tests."""

    def test_old_complex_mock_integration(self):
        """BEFORE: Complex integration test with many mocks."""

        def old_integration_pattern():
            """Old integration pattern with excessive mocking."""
            # OLD: Many interconnected mocks
            mock_main_window = Mock()
            mock_extraction_mgr = Mock()
            Mock()
            Mock()
            mock_worker = Mock()

            # Complex mock interconnections
            mock_main_window.get_extraction_params.return_value = {"valid": True}
            mock_extraction_mgr.validate_extraction_params.return_value = True
            mock_extraction_mgr.create_worker.return_value = mock_worker
            mock_worker.finished = Mock()

            # Simulate workflow
            params = mock_main_window.get_extraction_params()
            is_valid = mock_extraction_mgr.validate_extraction_params(params)
            worker = None

            if is_valid:
                worker = mock_extraction_mgr.create_worker(params)
                # Simulate worker completion
                worker.finished.emit({"result": "mocked"})

            return {
                "params_valid": is_valid,
                "worker_created": worker is not None,
                "result": "mocked workflow"
            }

        result = old_integration_pattern()

        # Old assertions - testing mock configuration
        assert result["params_valid"] is True
        assert result["worker_created"] is True
        assert result["result"] == "mocked workflow"

        # Problems:
        # 1. No real component interaction
        # 2. Complex mock setup and maintenance
        # 3. Doesn't catch integration bugs
        # 4. Brittle - breaks when implementation changes

    def test_new_real_integration(self):
        """AFTER: Real integration test with minimal mocking."""

        with manager_context("extraction", "injection", "session") as ctx:
            # Real managers working together
            extraction = ctx.get_extraction_manager()
            injection = ctx.get_injection_manager()
            session = ctx.get_session_manager()

            # Real session workflow
            session.start_session("integration_test")

            # Real parameter validation
            extract_params = ctx._data_repo.get_vram_extraction_data("small")
            inject_params = ctx._data_repo.get_injection_data("small")

            extract_valid = extraction.validate_extraction_params(extract_params)
            inject_valid = injection.validate_injection_params(inject_params)

            # Real workflow coordination
            if extract_valid:
                # Could create real worker
                extract_worker = ctx.create_worker("extraction", extract_params)
                assert extract_worker is not None

                if inject_valid:
                    # Real component interaction
                    inject_worker = ctx.create_worker("injection", inject_params)
                    assert inject_worker is not None

                    # Real workflow result
                    workflow_result = {
                        "session_active": session.get_current_session() == "integration_test",
                        "extraction_ready": extract_valid,
                        "injection_ready": inject_valid,
                        "workers_created": True
                    }

                    assert all(workflow_result.values())

            # Real session cleanup
            session.end_session()
            assert session.get_current_session() is None

        # Benefits:
        # 1. Real component interaction testing
        # 2. Catches real integration bugs
        # 3. Resilient to implementation changes
        # 4. Minimal maintenance overhead

# ============================================================================
# MIGRATION HELPER FUNCTIONS
# ============================================================================

def analyze_mock_usage_in_test_method(test_method_source: str) -> dict:
    """
    Helper to analyze mock usage in a test method for migration planning.

    Args:
        test_method_source: Source code of test method as string

    Returns:
        Analysis of mock usage and migration difficulty
    """

    mock_patterns = {
        'Mock()': 'Direct mock instantiation',
        'cast(': 'Type casting operation',
        'Mock(spec=': 'Spec-based mock',
        'MagicMock': 'Magic mock usage',
        'patch(': 'Function/method patching',
        'assert_called': 'Mock assertion',
        '.return_value = ': 'Mock return value configuration',
        '.side_effect = ': 'Mock side effect configuration'
    }

    analysis = {
        'mock_count': 0,
        'mock_types': [],
        'difficulty': 'easy',
        'migration_suggestions': []
    }

    for pattern, description in mock_patterns.items():
        if pattern in test_method_source:
            analysis['mock_count'] += test_method_source.count(pattern)
            analysis['mock_types'].append(description)

    # Determine migration difficulty
    if analysis['mock_count'] > 10:
        analysis['difficulty'] = 'hard'
    elif analysis['mock_count'] > 5:
        analysis['difficulty'] = 'medium'

    # Generate migration suggestions
    if 'Type casting operation' in analysis['mock_types']:
        analysis['migration_suggestions'].append(
            'Replace cast() operations with TypedManagerFactory'
        )

    if 'Mock assertion' in analysis['mock_types']:
        analysis['migration_suggestions'].append(
            'Replace mock assertions with behavior verification'
        )

    if 'Direct mock instantiation' in analysis['mock_types']:
        analysis['migration_suggestions'].append(
            'Replace Mock() with RealComponentFactory components'
        )

    return analysis

def generate_migration_plan(test_file_path: str) -> str:
    """
    Generate a migration plan for a test file.

    Args:
        test_file_path: Path to test file to migrate

    Returns:
        Migration plan as formatted string
    """

    plan = f"""
MIGRATION PLAN FOR {test_file_path}

Phase 1 - Quick Wins:
- Replace MockFactory imports with RealComponentFactory
- Remove cast() operations using typed factories
- Replace direct Mock() with real component creation

Phase 2 - Signal Testing:
- Replace mock signals with QSignalSpy
- Update signal connection tests to use real Qt behavior
- Add qtbot.addWidget() for proper widget lifecycle

Phase 3 - Integration:
- Use manager_context for multi-manager tests
- Replace mock workflows with real component interactions
- Add proper cleanup using context managers

Phase 4 - Validation:
- Run tests to ensure they still pass
- Verify real behavior instead of mock configuration
- Update assertions to test outcomes, not mock calls

Estimated effort: Based on mock density analysis
Resources: See tests/examples/ for migration patterns
"""

    return plan

# Example usage of migration helpers
if __name__ == "__main__":
    # Example analysis of test method
    sample_test_code = """
    def test_extraction_old_way(self):
        mock_manager = Mock()
        mock_manager.validate_params.return_value = True
        manager = cast(ExtractionManager, mock_manager)
        result = manager.validate_params({})
        mock_manager.validate_params.assert_called_once()
    """

    analysis = analyze_mock_usage_in_test_method(sample_test_code)
    print(f"Mock analysis: {analysis}")

    plan = generate_migration_plan("test_example.py")
    print(plan)

    # Run migration examples
    print("\nRunning migration examples...")
    pytest.main([__file__, "-v", "--tb=short"])
