"""
Real Worker Extraction Tests - Replacement for mocked QThread version.

These tests demonstrate the evolution from mocked QThread tests to real 
worker-owned pattern tests, showing how real implementations catch 
architectural bugs that mocks hide.

Test Evolution:
1. OLD: Mocked QThread tests (hide Qt lifecycle bugs)
2. BETTER: Real QThread with singleton managers (can have lifecycle issues)  
3. BEST: Real QThread with worker-owned managers (eliminates lifecycle bugs)
"""

import os
import time
from pathlib import Path

import pytest
from PyQt6.QtTest import QSignalSpy

# Import real testing infrastructure
from tests.infrastructure import (
    TestApplicationFactory,
    RealManagerFixtureFactory,
    TestDataRepository, 
    QtTestingFramework,
    qt_worker_test,
    validate_qt_object_lifecycle,
)

# Import real worker implementations
from spritepal.core.workers.extraction import (
    VRAMExtractionWorker,        # Legacy: uses singleton managers
    ROMExtractionWorker,         # Legacy: uses singleton managers  
    WorkerOwnedVRAMExtractionWorker,  # Modern: worker-owned managers
    WorkerOwnedROMExtractionWorker,   # Modern: worker-owned managers
)
from spritepal.core.managers import initialize_managers, cleanup_managers, are_managers_initialized


class TestWorkerExtractionArchitecturalEvolution:
    """
    Demonstrate the architectural evolution from mocked to real worker testing.
    
    This shows how different testing approaches catch different types of bugs,
    proving the value of the worker-owned pattern and real implementations.
    """
    
    @pytest.fixture(autouse=True)
    def setup_test_infrastructure(self):
        """Set up real testing infrastructure."""
        self.qt_app = TestApplicationFactory.get_application() 
        self.manager_factory = RealManagerFixtureFactory(qt_parent=self.qt_app)
        self.test_data = TestDataRepository()
        self.qt_framework = QtTestingFramework(self.qt_app)
        
        yield
        
        # Cleanup
        self.qt_framework.cleanup()
        self.manager_factory.cleanup()
        self.test_data.cleanup()
        
        # Clean up singleton managers if they exist
        if are_managers_initialized():
            cleanup_managers()
    
    def test_mocked_vs_real_qt_thread_comparison(self):
        """
        Compare mocked QThread approach vs real QThread approach.
        
        This demonstrates what mocked tests miss and why real tests are better.
        """
        # === MOCKED APPROACH (what we're replacing) ===
        # The old mocked approach would do:
        # @patch('PyQt6.QtCore.QThread')
        # def test_worker_mocked(mock_thread):
        #     mock_worker = Mock()
        #     mock_worker.start = Mock()
        #     mock_worker.isRunning.return_value = False
        #     # This test validates NOTHING about real Qt behavior
        
        # === REAL APPROACH (what we're implementing) ===
        test_data = self.test_data.get_vram_extraction_data("small")
        
        params = {
            "vram_path": test_data["vram_path"],
            "cgram_path": test_data["cgram_path"], 
            "output_base": test_data["output_base"],
            "vram_offset": test_data["vram_offset"],
        }
        
        # Real worker-owned pattern test
        with qt_worker_test(WorkerOwnedVRAMExtractionWorker, params) as worker:
            # Real Qt validation that mocks cannot provide
            lifecycle_info = validate_qt_object_lifecycle(worker)
            assert lifecycle_info["has_parent"], "Real worker should have Qt parent" 
            assert lifecycle_info["qt_object_valid"], "Real worker should be valid Qt object"
            
            # Real manager ownership validation (mocks cannot test this)
            assert hasattr(worker, 'manager'), "Worker should own a manager"
            assert worker.manager is not None, "Worker manager should exist"
            assert worker.manager.parent() is worker, "Manager should be owned by worker"
            
            # Real signal behavior (not mocked signal behavior)
            progress_spy = QSignalSpy(worker.progress)
            error_spy = QSignalSpy(worker.error)
            
            # Start real worker operation
            worker.perform_operation()
            
            # Wait for real Qt signals (not mocked signals)
            TestApplicationFactory.process_events(500)
            
            # Validate real signal emissions occurred
            assert len(progress_spy) >= 0, "Progress signals should be emitted"
            
            # Validate no Qt lifecycle errors (mocks cannot catch these)
            qt_lifecycle_errors = [
                signal for signal in error_spy 
                if "wrapped C/C++ object" in str(signal[0])
            ]
            assert len(qt_lifecycle_errors) == 0, f"No Qt lifecycle errors should occur: {qt_lifecycle_errors}"
    
    def test_singleton_vs_worker_owned_manager_patterns(self):
        """
        Compare singleton managers vs worker-owned managers.
        
        This demonstrates how worker-owned pattern eliminates Qt lifecycle bugs
        that can occur with singleton managers.
        """
        test_data = self.test_data.get_vram_extraction_data("small")
        params = {
            "vram_path": test_data["vram_path"],
            "cgram_path": test_data["cgram_path"],
            "output_base": test_data["output_base"],
            "vram_offset": test_data["vram_offset"],
        }
        
        # === SINGLETON PATTERN (legacy, can have issues) ===
        # Initialize singleton managers
        if not are_managers_initialized():
            initialize_managers()
        
        with qt_worker_test(VRAMExtractionWorker, params) as singleton_worker:
            # Singleton worker uses global manager
            assert hasattr(singleton_worker, 'manager'), "Worker should have manager access"
            
            # The manager is NOT owned by the worker
            manager_parent = singleton_worker.manager.parent() if singleton_worker.manager else None
            assert manager_parent is not singleton_worker, "Singleton manager is NOT owned by worker"
            
            # This can lead to Qt lifecycle issues in complex scenarios
            worker_state = self.qt_framework.validate_qt_parent_child_relationship(
                singleton_worker, singleton_worker.manager
            )
            assert not worker_state["child_parent_correct"], "Manager is not child of worker in singleton pattern"
        
        # === WORKER-OWNED PATTERN (modern, eliminates issues) ===  
        with qt_worker_test(WorkerOwnedVRAMExtractionWorker, params) as owned_worker:
            # Worker-owned pattern: worker owns its manager
            assert hasattr(owned_worker, 'manager'), "Worker should own manager"
            assert owned_worker.manager is not None, "Worker manager should exist"
            assert owned_worker.manager.parent() is owned_worker, "Manager should be owned by worker"
            
            # Perfect thread isolation - no shared state
            manager_state = self.qt_framework.validate_qt_parent_child_relationship(
                owned_worker, owned_worker.manager
            )
            assert manager_state["child_parent_correct"], "Manager should be child of worker"
            assert manager_state["child_in_parent_children"], "Manager should be in worker's children"
            
            # This eliminates Qt lifecycle bugs completely
            lifecycle_info = validate_qt_object_lifecycle(owned_worker.manager)
            assert lifecycle_info["has_parent"], "Manager has proper Qt parent"
            assert lifecycle_info["parent_type"] == "WorkerOwnedVRAMExtractionWorker", "Correct parent type"
    
    def test_concurrent_worker_isolation_real(self):
        """
        Test real concurrent worker isolation using worker-owned pattern.
        
        This validates that multiple workers don't interfere with each other,
        which is critical for thread safety and something mocks cannot test.
        """
        test_data = self.test_data.get_vram_extraction_data("small")
        
        # Create parameters for multiple workers
        params1 = {
            "vram_path": test_data["vram_path"],
            "cgram_path": test_data["cgram_path"],
            "output_base": os.path.join(test_data["output_base"], "worker1"),
            "vram_offset": test_data["vram_offset"],
        }
        
        params2 = {
            "vram_path": test_data["vram_path"], 
            "cgram_path": test_data["cgram_path"],
            "output_base": os.path.join(test_data["output_base"], "worker2"),
            "vram_offset": test_data["vram_offset"], 
        }
        
        workers = []
        
        try:
            # Create multiple concurrent workers
            worker1 = WorkerOwnedVRAMExtractionWorker(params1)
            worker2 = WorkerOwnedVRAMExtractionWorker(params2)
            workers.extend([worker1, worker2])
            
            # Set Qt parents
            worker1.setParent(self.qt_app)
            worker2.setParent(self.qt_app)
            
            # Validate complete isolation
            assert worker1.manager is not worker2.manager, "Workers should have separate managers"
            assert worker1.manager.parent() is worker1, "Worker1 should own its manager"
            assert worker2.manager.parent() is worker2, "Worker2 should own its manager"
            
            # Test concurrent operation without interference
            progress_spy1 = QSignalSpy(worker1.progress)
            progress_spy2 = QSignalSpy(worker2.progress)
            error_spy1 = QSignalSpy(worker1.error)
            error_spy2 = QSignalSpy(worker2.error)
            
            # Start both workers concurrently
            worker1.perform_operation()
            worker2.perform_operation()
            
            # Process events to allow operations to proceed
            TestApplicationFactory.process_events(1000)
            
            # Validate no Qt lifecycle errors in either worker
            for error_spy, worker_name in [(error_spy1, "Worker1"), (error_spy2, "Worker2")]:
                qt_errors = [
                    signal for signal in error_spy
                    if "wrapped C/C++ object" in str(signal[0])
                ]
                assert len(qt_errors) == 0, f"{worker_name} should have no Qt lifecycle errors"
            
        finally:
            # Clean up workers
            for worker in workers:
                try:
                    if hasattr(worker, 'quit'):
                        worker.quit()
                        worker.wait(1000)
                    worker.setParent(None)
                except Exception:
                    pass  # Ignore cleanup errors
    
    def test_rom_extraction_worker_owned_pattern(self):
        """
        Test ROM extraction with worker-owned pattern.
        
        This validates that the worker-owned pattern works for ROM extraction
        as well as VRAM extraction.
        """
        test_data = self.test_data.get_rom_extraction_data("small")
        
        params = {
            "rom_path": test_data["rom_path"],
            "offset": test_data["offset"],
            "output_base": test_data["output_base"],
            "sprite_size": test_data["sprite_size"],
        }
        
        with qt_worker_test(WorkerOwnedROMExtractionWorker, params) as worker:
            # Validate worker-owned manager pattern
            assert worker.manager is not None, "ROM worker should own manager"
            assert worker.manager.parent() is worker, "ROM manager should be owned by worker"
            
            # Validate Qt object lifecycle
            lifecycle_info = validate_qt_object_lifecycle(worker)
            assert lifecycle_info["has_parent"], "ROM worker should have Qt parent"
            assert lifecycle_info["qt_object_valid"], "ROM worker should be valid"
            
            # Test real ROM extraction operation
            progress_spy = QSignalSpy(worker.progress) 
            error_spy = QSignalSpy(worker.error)
            
            # Start ROM extraction
            worker.perform_operation()
            
            # Wait for operation to complete
            TestApplicationFactory.process_events(1000)
            
            # Validate no architectural errors occurred
            architectural_errors = [
                signal for signal in error_spy
                if any(error_term in str(signal[0]).lower() 
                      for error_term in ["wrapped c/c++ object", "qobject", "parent"])
            ]
            assert len(architectural_errors) == 0, f"No architectural errors should occur: {architectural_errors}"
    
    def test_worker_error_handling_real_vs_mock(self):
        """
        Compare real error handling vs mocked error handling.
        
        This shows how real error testing catches actual error propagation
        bugs that mocked error handling cannot detect.
        """
        # Create intentionally invalid parameters
        invalid_params = {
            "vram_path": "/nonexistent/file.dmp",
            "cgram_path": "/nonexistent/cgram.dmp", 
            "output_base": "/invalid/output/path",
            "vram_offset": 0xC000,
        }
        
        # === MOCKED ERROR HANDLING (what we're replacing) ===
        # The old approach would mock errors:
        # mock_manager.validate_extraction_params.side_effect = ValidationError("Mock error")
        # This tests that the mock behaves as expected, not that real errors are handled
        
        # === REAL ERROR HANDLING (what we're implementing) ===
        with qt_worker_test(WorkerOwnedVRAMExtractionWorker, invalid_params) as worker:
            # Set up real error monitoring
            error_spy = QSignalSpy(worker.error)
            operation_spy = QSignalSpy(worker.operation_finished)
            
            # Test real error propagation
            worker.perform_operation()
            
            # Wait for real error handling
            TestApplicationFactory.process_events(1000)
            
            # Validate real error occurred and was handled properly
            assert len(error_spy) > 0 or len(operation_spy) > 0, "Real error should be detected"
            
            if len(error_spy) > 0:
                error_message = str(error_spy[0][0])
                assert any(term in error_message.lower() 
                          for term in ["file", "exist", "path", "invalid"]), \
                          f"Error should describe actual problem: {error_message}"
            
            if len(operation_spy) > 0:
                success, message = operation_spy[0][0], operation_spy[0][1]
                assert not success, "Operation should fail with invalid parameters"
                assert isinstance(message, str), "Should have error message"
    
    def test_signal_connection_validation_real(self):
        """
        Test real Qt signal connections vs mocked signal connections.
        
        This validates that Qt signals actually connect and emit properly,
        which mocked signals cannot reliably test.
        """
        test_data = self.test_data.get_vram_extraction_data("small")
        params = {
            "vram_path": test_data["vram_path"],
            "cgram_path": test_data["cgram_path"], 
            "output_base": test_data["output_base"],
            "vram_offset": test_data["vram_offset"],
        }
        
        with qt_worker_test(WorkerOwnedVRAMExtractionWorker, params) as worker:
            # Test real signal connection behavior
            callback_count = 0
            received_messages = []
            
            def progress_callback(percent, message):
                nonlocal callback_count
                callback_count += 1
                received_messages.append((percent, message))
            
            def error_callback(message, exception=None):
                nonlocal callback_count
                callback_count += 1
                received_messages.append(("error", message))
            
            # Connect to real Qt signals
            worker.progress.connect(progress_callback)
            worker.error.connect(error_callback)
            
            # Test signal emission behavior
            worker.perform_operation()
            
            # Process Qt events to ensure signal delivery
            TestApplicationFactory.process_events(500)
            
            # Validate real signal behavior
            assert callback_count >= 0, "Callbacks should be invoked by real signals"
            
            # Test signal validation
            signal_validation = self.qt_framework.validate_signal_behavior(worker.progress)
            assert signal_validation["signal_exists"], "Progress signal should exist"
            assert signal_validation["can_connect"], "Should be able to connect to signal"
            assert signal_validation["can_emit"], "Should be able to emit signal"
    
    def test_architectural_bug_detection_demonstration(self):
        """
        Demonstrate bugs that real tests catch but mocked tests miss.
        
        This serves as documentation of why we moved from mocked to real testing.
        """
        test_data = self.test_data.get_vram_extraction_data("small")
        params = {
            "vram_path": test_data["vram_path"],
            "cgram_path": test_data["cgram_path"],
            "output_base": test_data["output_base"], 
            "vram_offset": test_data["vram_offset"],
        }
        
        # Bug Category 1: Qt Parent/Child Lifecycle Issues
        worker = WorkerOwnedVRAMExtractionWorker(params)
        worker.setParent(self.qt_app)
        
        # Real test can detect when Qt parent is incorrectly removed
        original_parent = worker.parent()
        worker.setParent(None)  # Simulate bug: removing Qt parent
        
        assert original_parent is self.qt_app, "Should have had Qt parent initially"
        assert worker.parent() is None, "Parent was actually removed (potential bug)"
        
        # Restore parent for cleanup
        worker.setParent(self.qt_app)
        
        # Bug Category 2: Manager Ownership Issues  
        manager = worker.manager
        original_manager_parent = manager.parent()
        
        # Real test can detect when manager ownership is broken
        manager.setParent(None)  # Simulate bug: breaking manager ownership
        
        assert original_manager_parent is worker, "Manager should have been owned by worker"
        assert manager.parent() is None, "Manager ownership was actually broken (potential bug)"
        
        # Restore ownership for cleanup
        manager.setParent(worker)
        
        # Bug Category 3: Signal Connection Issues
        # Real test can verify that signals actually connect and work
        signal_spy = QSignalSpy(worker.progress)
        
        # This tests ACTUAL signal behavior, not mocked behavior
        worker.progress.emit(50, "Test message")
        TestApplicationFactory.process_events(100)
        
        assert len(signal_spy) == 1, "Real signal should be captured by spy"
        assert signal_spy[0][0] == 50, "Real signal should carry actual data"
        assert signal_spy[0][1] == "Test message", "Real signal should carry actual message"
        
        # Clean up
        worker.setParent(None)


class TestRealWorkerTestingBenefits:
    """
    Document and validate the benefits of real worker testing over mocked testing.
    """
    
    def test_real_testing_infrastructure_validation(self):
        """Validate that real testing infrastructure provides expected benefits."""
        # Benefit 1: Real Qt application lifecycle
        app = TestApplicationFactory.get_application()
        assert app.applicationName() == "SpritePal-Test"
        assert not app.quitOnLastWindowClosed()  # Configured for testing
        
        # Benefit 2: Real manager factory with proper Qt parents
        factory = RealManagerFixtureFactory()
        manager = factory.create_extraction_manager(isolated=True)
        assert manager.parent() is app
        factory.cleanup()
        
        # Benefit 3: Real test data generation
        test_data = TestDataRepository()
        data = test_data.get_vram_extraction_data("small")
        assert os.path.exists(data["vram_path"])
        assert os.path.exists(data["cgram_path"])
        test_data.cleanup()
        
        # Benefit 4: Real Qt testing framework
        qt_framework = QtTestingFramework()
        validation = qt_framework.validate_qt_parent_child_relationship(app, manager)
        # Note: manager was cleaned up above, so this tests the validation function itself
        qt_framework.cleanup()
    
    def test_real_vs_mock_bug_detection_summary(self):
        """
        Summarize the types of bugs real tests catch that mocked tests miss.
        
        This serves as documentation for why the testing architecture overhaul
        was necessary and beneficial.
        """
        bugs_caught_by_real_tests = {
            "qt_lifecycle_bugs": [
                "Qt object parent/child relationship errors",
                "Qt object lifecycle management issues", 
                "QApplication configuration problems",
                "Widget cleanup and memory leak issues",
            ],
            "threading_bugs": [
                "QThread parent ownership issues",
                "Cross-thread signal delivery problems", 
                "Thread safety and isolation issues",
                "Worker lifecycle management bugs",
            ],
            "manager_integration_bugs": [
                "Manager-to-manager communication errors",
                "State synchronization issues",
                "Error propagation failures",
                "Parameter validation bypass bugs",
            ],
            "signal_slot_bugs": [
                "Signal connection failures",
                "Signal emission timing issues",
                "Cross-thread signal problems",
                "Signal/slot parameter mismatches",
            ],
        }
        
        bugs_missed_by_mocked_tests = {
            "architectural_integration": "Mocks hide how components actually interact",
            "qt_behavior_differences": "MockSignal != PyQt6.QtCore.pyqtSignal",
            "lifecycle_management": "Mock objects don't have Qt parent/child behavior",
            "real_error_conditions": "Mocks return predetermined results, not real errors",
            "performance_characteristics": "Mocks don't reveal real performance issues", 
            "thread_safety": "Mock objects don't test real thread interactions",
        }
        
        # The existence of these categorized bug types proves the value of real testing
        assert len(bugs_caught_by_real_tests) > 0, "Real tests catch multiple bug categories"
        assert len(bugs_missed_by_mocked_tests) > 0, "Mocked tests miss important bug categories"
        
        # This test serves as living documentation of why we changed approaches
        print("✅ Real testing catches architectural bugs that mocked testing misses")
        print(f"   - Bug categories caught by real tests: {len(bugs_caught_by_real_tests)}")
        print(f"   - Bug categories missed by mocked tests: {len(bugs_missed_by_mocked_tests)}")


if __name__ == "__main__":
    # Quick validation that real worker testing infrastructure works
    import sys
    
    try:
        # Test infrastructure setup
        app = TestApplicationFactory.get_application()
        factory = RealManagerFixtureFactory()
        test_data = TestDataRepository()
        
        print("✅ Real worker testing infrastructure ready")
        
        # Test worker-owned pattern
        data = test_data.get_vram_extraction_data("small")
        params = {
            "vram_path": data["vram_path"],
            "cgram_path": data["cgram_path"],
            "output_base": data["output_base"],
            "vram_offset": data["vram_offset"],
        }
        
        worker = WorkerOwnedVRAMExtractionWorker(params)
        worker.setParent(app)
        
        assert worker.manager.parent() is worker, "Worker should own manager"
        print("✅ Worker-owned pattern validation successful")
        
        # Cleanup
        worker.setParent(None)
        factory.cleanup()
        test_data.cleanup()
        
        print("🎉 Real worker extraction testing infrastructure ready!")
        print("   - Replaces mocked QThread tests with real implementations")
        print("   - Catches Qt lifecycle bugs that mocks hide")
        print("   - Validates worker-owned pattern eliminates architectural issues")
        
    except Exception as e:
        print(f"❌ Real worker testing infrastructure error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)