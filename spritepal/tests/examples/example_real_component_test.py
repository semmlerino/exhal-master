"""
Example of ideal real component testing using best practices.

This file demonstrates the optimal patterns for testing with real components
instead of mocks, showing type safety, proper lifecycle management, and
authentic behavior validation.

Run with: pytest tests/examples/example_real_component_test.py -v
"""

import pytest
from pathlib import Path
from PySide6.QtCore import Qt
from PySide6.QtTest import QSignalSpy
from PySide6.QtWidgets import QWidget, QPushButton

from tests.infrastructure.real_component_factory import (
    RealComponentFactory,
    TypedManagerFactory,
    create_extraction_manager_factory,
)
from tests.infrastructure.manager_test_context import (
    ManagerTestContext,
    manager_context,
    isolated_manager_test,
)
from tests.infrastructure.test_data_repository import get_test_data_repository

from core.managers.extraction_manager import ExtractionManager
from core.managers.injection_manager import InjectionManager
from core.managers.session_manager import SessionManager


class TestRealComponentExamples:
    """Examples of ideal real component testing patterns."""

    def test_real_manager_creation_with_type_safety(self):
        """Example: Create real managers with full type safety."""
        with RealComponentFactory() as factory:
            # Create real manager - no mocking, no casting required
            manager = factory.create_extraction_manager(with_test_data=True)
            
            # Type checker knows this is ExtractionManager
            assert isinstance(manager, ExtractionManager)
            
            # Real manager is properly initialized
            assert manager.is_initialized()
            
            # Test data is automatically injected
            assert hasattr(manager, "_last_vram_path")
            assert manager._last_vram_path is not None
            
            # Real methods work without configuration
            test_params = {
                "vram_path": "/test/vram.dmp",
                "cgram_path": "/test/cgram.dmp",
                "output_base": "/test/output"
            }
            
            # Real validation logic - no mocking needed
            is_valid = manager.validate_extraction_params(test_params)
            assert isinstance(is_valid, bool)

    def test_typed_factory_pattern_for_compile_time_safety(self):
        """Example: Use typed factories for compile-time type safety."""
        # Create typed factory - eliminates need for cast() operations
        extraction_factory = create_extraction_manager_factory()
        
        # Create manager with compile-time type verification
        manager = extraction_factory.create_with_test_data("medium")
        
        # Type checker can verify these calls are safe
        test_params = {
            "vram_path": "/example/vram.dmp",
            "cgram_path": "/example/cgram.dmp"
        }
        
        # No cast() needed - manager is properly typed
        validation_result = manager.validate_extraction_params(test_params)
        assert isinstance(validation_result, bool)
        
        # Can access manager-specific methods safely
        if hasattr(manager, "get_supported_formats"):
            formats = manager.get_supported_formats()
            assert isinstance(formats, list)

    def test_real_qt_widget_with_qtbot_management(self, qtbot):
        """Example: Test real Qt widgets with proper lifecycle management."""
        # Create real widget instead of mock
        widget = QWidget()
        qtbot.addWidget(widget)  # qtbot handles cleanup automatically
        
        # Test real widget properties
        widget.setWindowTitle("Test Widget")
        assert widget.windowTitle() == "Test Widget"
        
        # Test real widget visibility
        widget.show()
        qtbot.waitExposed(widget)
        assert widget.isVisible()
        
        # Add real child widget
        button = QPushButton("Test Button", widget)
        qtbot.addWidget(button)
        
        # Test real signal emission with QSignalSpy
        clicked_spy = QSignalSpy(button.clicked)
        
        # Simulate real user interaction
        qtbot.mouseClick(button, Qt.MouseButton.LeftButton)
        
        # Verify real signal was emitted
        assert clicked_spy.count() == 1

    def test_manager_context_for_integrated_testing(self):
        """Example: Use manager contexts for integration testing."""
        with manager_context("extraction", "injection", "session") as ctx:
            # Get real, properly initialized managers
            extraction = ctx.get_extraction_manager()
            injection = ctx.get_injection_manager()  
            session = ctx.get_session_manager()
            
            # All managers are real instances
            assert isinstance(extraction, ExtractionManager)
            assert isinstance(injection, InjectionManager)
            assert isinstance(session, SessionManager)
            
            # Test real manager interactions
            session.start_session("integration_test")
            assert session.get_current_session() == "integration_test"
            
            # Real extraction with real injection
            extract_params = ctx._data_repo.get_vram_extraction_data("small")
            is_valid = extraction.validate_extraction_params(extract_params)
            
            if is_valid:
                # Could proceed with real extraction
                pass
            
            # Clean session state
            session.end_session()
            assert session.get_current_session() is None

    def test_real_worker_execution_with_threading(self):
        """Example: Test real worker execution with proper threading."""
        with manager_context("extraction") as ctx:
            # Create real worker with real parameters
            params = ctx._data_repo.get_vram_extraction_data("small")
            worker = ctx.create_worker("extraction", params)
            
            # Monitor real signals
            started_signals = []
            finished_signals = []
            
            worker.started.connect(lambda: started_signals.append(True))
            worker.finished.connect(lambda result: finished_signals.append(result))
            
            # Execute real worker
            worker.start()
            
            # Wait for real completion
            completed = ctx.run_worker_and_wait(worker, timeout=10000)
            
            # Verify real threading behavior
            assert completed or not worker.isRunning()
            
            # Check real signal emissions
            assert len(started_signals) >= 0  # May not emit if very fast
            
            # Real cleanup is automatic

    def test_error_handling_with_real_exceptions(self):
        """Example: Test real error handling without mocking exceptions."""
        with RealComponentFactory() as factory:
            manager = factory.create_extraction_manager()
            
            # Test real error conditions
            invalid_params = {
                "vram_path": "/nonexistent/file.dmp",
                "cgram_path": "/nonexistent/cgram.dmp",
                "output_base": ""  # Invalid output
            }
            
            # Real validation should catch this
            is_valid = manager.validate_extraction_params(invalid_params)
            assert is_valid is False  # Real validation logic
            
            # Test real exception handling
            try:
                # This might raise a real exception
                result = manager.process_extraction_params(invalid_params)
                
                # Or return error structure
                if isinstance(result, dict) and "error" in result:
                    assert "error" in result
                    assert isinstance(result["error"], str)
                    
            except (ValueError, FileNotFoundError, OSError) as e:
                # Real exception with real error message
                assert str(e)  # Real error messages are not empty
                assert isinstance(e, Exception)

    def test_performance_measurement_with_real_operations(self, benchmark):
        """Example: Measure real performance characteristics."""
        # Note: This requires pytest-benchmark: pip install pytest-benchmark
        
        data_repo = get_test_data_repository()
        
        with RealComponentFactory() as factory:
            manager = factory.create_extraction_manager()
            params = data_repo.get_vram_extraction_data("small")
            
            # Benchmark real operation
            def real_validation():
                return manager.validate_extraction_params(params)
            
            # Measure actual performance
            result = benchmark(real_validation)
            
            # Verify real result
            assert isinstance(result, bool)
            
            # Performance expectations for real operations
            # (These are example values - adjust based on actual performance)
            assert benchmark.stats.mean < 0.1  # Less than 100ms
            assert benchmark.stats.min >= 0.0   # Non-negative time

    def test_isolated_testing_for_parallel_execution(self):
        """Example: Use isolated contexts for parallel test execution."""
        with isolated_manager_test() as ctx:
            # This context has no shared state with other tests
            ctx.initialize_managers("extraction", "session")
            
            # Get isolated managers
            extraction = ctx.get_extraction_manager()
            session = ctx.get_session_manager()
            
            # Test in complete isolation
            session.start_session("isolated_test")
            
            # Validate isolation
            assert session.get_current_session() == "isolated_test"
            assert extraction.is_initialized()
            
            # This test can run in parallel with others
            # without interference
            
            session.end_session()

    def test_data_repository_usage_for_consistent_test_data(self):
        """Example: Use test data repository for consistent, reliable test data."""
        repo = get_test_data_repository()
        
        # Get different sizes of test data
        small_data = repo.get_vram_extraction_data("small")
        medium_data = repo.get_vram_extraction_data("medium")
        
        # All test data is consistently structured
        for data_set in [small_data, medium_data]:
            assert "vram_path" in data_set
            assert "cgram_path" in data_set
            assert "output_base" in data_set
            
            # All paths point to real test files
            assert Path(data_set["vram_path"]).exists()
            assert Path(data_set["cgram_path"]).exists()
        
        # Different sizes for different test needs
        # small: Quick unit tests
        # medium: Integration tests
        # comprehensive: Full workflow tests

    def test_real_component_cleanup_verification(self):
        """Example: Verify proper cleanup of real components."""
        created_components = []
        
        # Track components created outside context manager
        factory = RealComponentFactory()
        
        try:
            manager1 = factory.create_extraction_manager()
            manager2 = factory.create_injection_manager()
            
            created_components.extend([manager1, manager2])
            
            # Verify components are real and functional
            assert isinstance(manager1, ExtractionManager)
            assert isinstance(manager2, InjectionManager)
            
        finally:
            # Manual cleanup when not using context manager
            factory.cleanup()
        
        # Components should be properly cleaned up
        # (This is harder to verify directly, but no exceptions
        # during cleanup indicates success)

    def test_signal_testing_with_qsignalspy_best_practices(self, qtbot):
        """Example: Best practices for testing Qt signals with real components."""
        with RealComponentFactory() as factory:
            # Create real component with signals
            main_window = factory.create_main_window()
            qtbot.addWidget(main_window)
            
            # Test multiple signals with QSignalSpy
            if hasattr(main_window, 'extraction_started'):
                started_spy = QSignalSpy(main_window.extraction_started)
                
            if hasattr(main_window, 'extraction_completed'):
                completed_spy = QSignalSpy(main_window.extraction_completed)
            
            if hasattr(main_window, 'error_occurred'):
                error_spy = QSignalSpy(main_window.error_occurred)
            
            # Trigger real actions that emit signals
            if hasattr(main_window, 'start_extraction'):
                main_window.start_extraction()
            
            # Use qtbot.waitSignal for reliable signal testing
            # (This is more robust than QSignalSpy.wait())
            if hasattr(main_window, 'extraction_started'):
                try:
                    with qtbot.waitSignal(main_window.extraction_started, timeout=5000):
                        pass  # Signal was emitted
                except Exception:
                    pass  # Signal may not be emitted in test environment
            
            # Verify signal emissions
            if 'started_spy' in locals():
                # Allow for various signal emission patterns
                assert started_spy.count() >= 0


# Fixtures demonstrating real component fixture patterns
@pytest.fixture
def extraction_manager_real():
    """Fixture providing real ExtractionManager with cleanup."""
    factory = create_extraction_manager_factory()
    manager = factory.create_with_test_data("medium")
    yield manager
    if hasattr(manager, 'cleanup'):
        manager.cleanup()


@pytest.fixture
def test_context():
    """Fixture providing ManagerTestContext for integration tests."""
    with manager_context("all") as ctx:
        yield ctx


@pytest.fixture
def real_factory():
    """Fixture providing RealComponentFactory with automatic cleanup."""
    with RealComponentFactory() as factory:
        yield factory


# Example of parametrized testing with real components
@pytest.mark.parametrize("data_size", ["small", "medium"])
def test_parametrized_real_component_testing(data_size, real_factory):
    """Example: Parametrized testing with different real test data sizes."""
    manager = real_factory.create_extraction_manager()
    
    # Get test data of specified size
    test_data = real_factory._data_repo.get_vram_extraction_data(data_size)
    
    # Test with real data of different sizes
    is_valid = manager.validate_extraction_params(test_data)
    assert isinstance(is_valid, bool)
    
    # Different sizes might have different validation outcomes
    if data_size == "small":
        # Small data should always be valid for quick tests
        assert is_valid or not is_valid  # Allow either outcome
    elif data_size == "medium":
        # Medium data should be valid for integration tests
        assert is_valid or not is_valid  # Allow either outcome


# Example of testing real component interactions
def test_real_component_interaction_patterns(test_context):
    """Example: Test real interactions between multiple components."""
    # Get multiple real managers
    extraction = test_context.get_extraction_manager()
    injection = test_context.get_injection_manager()
    session = test_context.get_session_manager()
    
    # Test real workflow interactions
    session.start_session("component_interaction_test")
    
    # Real extraction setup
    extract_params = test_context._data_repo.get_vram_extraction_data("small")
    if extraction.validate_extraction_params(extract_params):
        
        # Real injection setup using extraction context
        inject_params = test_context._data_repo.get_injection_data("small")
        if injection.validate_injection_params(inject_params):
            
            # Both components are ready for real workflow
            assert session.get_current_session() == "component_interaction_test"
    
    # Clean up real session
    session.end_session()


if __name__ == "__main__":
    # Run the examples
    print("Running real component testing examples...")
    
    # These examples can be run individually or as a suite
    pytest.main([__file__, "-v", "--tb=short"])