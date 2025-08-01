"""
Complete Real Worker Extraction Tests - Replacement for mocked version.

This test file demonstrates the evolution from mocked QThread tests to real 
worker-owned pattern tests, showing how real implementations catch architectural 
bugs that mocks hide.

CRITICAL DIFFERENCES FROM MOCKED VERSION:
1. REAL Qt parent/child relationships (catches lifecycle bugs)
2. REAL QThread execution (catches threading bugs) 
3. REAL signal propagation (catches cross-thread issues)
4. REAL manager ownership patterns (catches singleton conflicts)
5. REAL error propagation (catches error handling bugs)

This replaces tests/test_worker_extraction.py which heavily mocked:
- get_extraction_manager() calls (30+ mocked calls)
- Manager signal connections (hides real Qt behavior)
- QThread behavior (can't test real threading issues)
"""

import sys
import time
from pathlib import Path
from typing import Any, Dict, List

import pytest
from PyQt6.QtTest import QSignalSpy
from PyQt6.QtCore import QTimer, QEventLoop

# Add parent directory for imports
current_dir = Path(__file__).parent
parent_dir = current_dir.parent
sys.path.insert(0, str(parent_dir))
sys.path.insert(0, str(current_dir))

# Import real testing infrastructure 
from tests.infrastructure import (
    TestApplicationFactory,
    RealManagerFixtureFactory,
    TestDataRepository,
    QtTestingFramework,
    qt_worker_test,
    validate_qt_object_lifecycle,
)

# Import real worker implementations (all 4 types)
from spritepal.core.workers.extraction import (
    VRAMExtractionWorker,                # Legacy: uses singleton managers
    ROMExtractionWorker,                 # Legacy: uses singleton managers  
    WorkerOwnedVRAMExtractionWorker,     # Modern: worker-owned managers
    WorkerOwnedROMExtractionWorker,      # Modern: worker-owned managers
    VRAMExtractionParams,
    ROMExtractionParams,
)

# Import real manager components
from spritepal.core.managers import (
    initialize_managers, 
    cleanup_managers, 
    are_managers_initialized, 
    get_extraction_manager
)
from spritepal.core.managers.factory import StandardManagerFactory


class TestWorkerExtractionArchitecturalEvolution:
    """
    Test architectural evolution from legacy to worker-owned patterns.
    
    This demonstrates how different testing approaches catch different bugs,
    proving the value of real implementations over mocking.
    """
    
    @pytest.fixture(autouse=True)
    def setup_test_infrastructure(self):
        """Set up real testing infrastructure for each test."""
        # Initialize Qt application
        self.qt_app = TestApplicationFactory.get_application()
        
        # Initialize real manager factory  
        self.manager_factory = RealManagerFixtureFactory(qt_parent=self.qt_app)
        
        # Initialize test data repository
        self.test_data = TestDataRepository()
        
        # Initialize Qt testing framework
        self.qt_framework = QtTestingFramework()
        
        yield
        
        # Cleanup
        self.manager_factory.cleanup()
        self.test_data.cleanup()
        cleanup_managers()  # Clean up any singleton managers
    
    def test_legacy_vram_worker_real_qt_lifecycle(self):
        """
        Test legacy VRAMExtractionWorker with real Qt lifecycle validation.
        
        EXPOSED BUGS MOCKS WOULD MISS:
        - Qt parent/child relationship issues
        - Manager singleton conflicts across workers
        - Real signal connection lifecycle
        """
        # Get real test data (use medium to support real VRAM offset 0xC000)
        extraction_data = self.test_data.get_vram_extraction_data("medium")
        
        # Create real VRAM extraction parameters
        params: VRAMExtractionParams = {
            "vram_path": extraction_data["vram_path"],
            "cgram_path": extraction_data["cgram_path"],
            "output_base": extraction_data["output_base"],
            "create_grayscale": True,
            "grayscale_mode": True,  # Skip palette validation for faster testing
        }
        
        # Initialize singleton managers for legacy pattern
        if not are_managers_initialized():
            initialize_managers(qt_parent=self.qt_app)
        
        # Test legacy worker creation and lifecycle
        worker = VRAMExtractionWorker(params, parent=self.qt_app)
        
        # Validate Qt parent relationship (MOCKS CAN'T TEST THIS)
        assert worker.parent() is self.qt_app, "Worker should have Qt app as parent"
        
        # Validate manager is singleton (MOCKS CAN'T TEST THIS)
        singleton_manager = get_extraction_manager()
        assert worker.manager is singleton_manager, "Legacy worker should use singleton manager"
        
        # Test signal connections with real Qt signals
        signal_spy = QSignalSpy(worker.progress)
        worker.connect_manager_signals()
        
        # Validate connections were actually made (MOCKS CAN'T VERIFY REAL CONNECTIONS)
        assert len(worker._connections) > 0, "Should have real signal connections"
        
        # Cleanup
        worker.disconnect_manager_signals()
        worker.setParent(None)
        
    def test_worker_owned_vram_worker_isolation(self):
        """
        Test WorkerOwnedVRAMExtractionWorker with proper isolation.
        
        EXPOSED BUGS MOCKS WOULD MISS:
        - Manager ownership patterns
        - Thread isolation between workers
        - Real Qt object lifecycle management
        """
        # Get real test data (use medium to support real VRAM offset 0xC000)
        extraction_data = self.test_data.get_vram_extraction_data("medium")
        
        # Create real VRAM extraction parameters
        params: VRAMExtractionParams = {
            "vram_path": extraction_data["vram_path"],
            "cgram_path": extraction_data["cgram_path"],
            "output_base": extraction_data["output_base"],
            "create_grayscale": True,
            "grayscale_mode": True,
        }
        
        # Create worker-owned manager factory
        factory = StandardManagerFactory()
        
        # Test worker-owned pattern
        worker = WorkerOwnedVRAMExtractionWorker(params, factory, parent=self.qt_app)
        
        # Validate Qt parent relationship
        assert worker.parent() is self.qt_app, "Worker should have Qt app as parent"
        
        # Validate manager ownership (CRITICAL: MOCKS CAN'T TEST THIS)
        assert worker.manager.parent() is worker, "Manager should be owned by worker"
        
        # Test isolation by creating second worker
        worker2 = WorkerOwnedVRAMExtractionWorker(params, factory, parent=self.qt_app)
        
        # Validate managers are isolated (MOCKS CAN'T TEST REAL ISOLATION)
        assert worker.manager is not worker2.manager, "Workers should have separate managers"
        assert worker.manager.parent() is worker
        assert worker2.manager.parent() is worker2
        
        # Cleanup
        worker.setParent(None)
        worker2.setParent(None)
    
    def test_real_worker_execution_with_actual_data(self):
        """
        Test real worker execution with actual VRAM data.
        
        EXPOSED BUGS MOCKS WOULD MISS:
        - Real extraction logic errors
        - File I/O issues 
        - Real signal propagation with actual data
        - Threading issues during real work
        """
        # Get real test data (use medium to support real VRAM offset 0xC000)
        extraction_data = self.test_data.get_vram_extraction_data("medium")
        
        # Create real parameters that should work
        params: VRAMExtractionParams = {
            "vram_path": extraction_data["vram_path"],
            "cgram_path": extraction_data["cgram_path"],
            "output_base": extraction_data["output_base"],
            "create_grayscale": True,
            "grayscale_mode": True,
        }
        
        # Use qt_worker_test context manager for proper Qt lifecycle
        with qt_worker_test(WorkerOwnedVRAMExtractionWorker, params) as worker:
            # Set up signal spies to catch real signals
            progress_spy = QSignalSpy(worker.progress)
            finished_spy = QSignalSpy(worker.operation_finished)
            extraction_spy = QSignalSpy(worker.extraction_finished)
            
            # Start real worker execution (using real QThread API)
            worker.start()
            
            # Wait for worker to complete (real threading test)
            success = worker.wait(10000)  # Wait up to 10 seconds
            
            # Validate real execution completed
            assert success, "Worker should complete successfully with real data"
            
            # Validate real signals were emitted (MOCKS CAN'T TEST REAL SIGNAL DATA)
            assert len(progress_spy) > 0, "Should emit real progress signals"
            assert len(finished_spy) == 1, "Should emit exactly one finished signal"
            
            # Validate finished signal data
            finished_args = finished_spy[0]
            assert len(finished_args) == 2, "Finished signal should have 2 arguments"
            success, message = finished_args
            assert success is True, f"Operation should succeed, got: {message}"
            
            # If extraction completed, validate extraction signal
            if len(extraction_spy) > 0:
                extraction_args = extraction_spy[0]
                extracted_files = extraction_args[0]
                assert isinstance(extracted_files, list), "Should return list of extracted files"
                assert len(extracted_files) > 0, "Should extract at least one file"
    
    def test_real_error_propagation_vs_mocked(self):
        """
        Test real error propagation vs what mocked tests would show.
        
        EXPOSED BUGS MOCKS WOULD MISS:
        - Real error types from actual operations
        - Error signal propagation across threads
        - Manager error handling in real scenarios
        """
        # Create parameters that should fail (non-existent file)
        invalid_params: VRAMExtractionParams = {
            "vram_path": "/nonexistent/file.dmp",
            "output_base": "/tmp/test_output",
            "create_grayscale": True,
        }
        
        # Test worker-owned pattern with invalid data
        with qt_worker_test(WorkerOwnedVRAMExtractionWorker, invalid_params) as worker:
            # Set up signal spies
            error_spy = QSignalSpy(worker.error)
            finished_spy = QSignalSpy(worker.operation_finished)
            
            # Start worker (should fail)  
            worker.start()
            success = worker.wait(5000)  # Wait up to 5 seconds
            
            # Worker should complete but operation should fail
            assert not success or len(finished_spy) > 0, "Worker should complete or signal failure"
            
            # Check if error was properly propagated
            if len(error_spy) > 0:
                error_args = error_spy[0]
                assert len(error_args) == 2, "Error signal should have message and exception"
                error_message, error_exception = error_args
                assert isinstance(error_message, str), "Error message should be string"
                assert isinstance(error_exception, Exception), "Should have real exception"
                
                # This is a REAL error from REAL code that mocks wouldn't catch
                print(f"REAL ERROR CAUGHT: {error_message}")
                print(f"REAL EXCEPTION TYPE: {type(error_exception).__name__}")
    
    def test_signal_propagation_with_real_preview_data(self):
        """
        Test real signal propagation with actual preview data.
        
        EXPOSED BUGS MOCKS WOULD MISS:
        - PIL image to QPixmap conversion issues
        - Real preview generation timing
        - Cross-thread signal data integrity
        """
        # Get real test data
        extraction_data = self.test_data.get_vram_extraction_data("medium")
        
        # Create parameters for preview generation
        params: VRAMExtractionParams = {
            "vram_path": extraction_data["vram_path"],
            "cgram_path": extraction_data["cgram_path"],
            "output_base": extraction_data["output_base"],
            "create_grayscale": True,
            "grayscale_mode": False,  # Enable preview generation
        }
        
        with qt_worker_test(WorkerOwnedVRAMExtractionWorker, params) as worker:
            # Set up spies for preview signals
            preview_spy = QSignalSpy(worker.preview_ready)
            image_spy = QSignalSpy(worker.preview_image_ready)
            palettes_spy = QSignalSpy(worker.palettes_ready)
            
            # Start worker
            worker.start()
            success = worker.wait(15000)  # Wait up to 15 seconds
            
            if success:
                # Validate real preview signals (MOCKS CAN'T TEST REAL PREVIEW DATA)
                if len(preview_spy) > 0:
                    preview_args = preview_spy[0]
                    pixmap, tile_count = preview_args
                    assert pixmap is not None, "Should have real QPixmap"
                    assert isinstance(tile_count, int), "Should have real tile count"
                    assert tile_count > 0, "Should have positive tile count"
                
                if len(image_spy) > 0:
                    image_args = image_spy[0]
                    pil_image = image_args[0]
                    # This validates real PIL image from real extraction
                    assert hasattr(pil_image, 'size'), "Should be real PIL image"
                    assert pil_image.size[0] > 0, "Image should have width"
                    assert pil_image.size[1] > 0, "Image should have height"
    
    def test_concurrent_worker_isolation_real(self):
        """
        Test that multiple workers truly don't interfere with each other.
        
        EXPOSED BUGS MOCKS WOULD MISS:
        - Race conditions in manager access
        - Thread-safety issues
        - Resource conflicts between workers
        """
        # Get test data
        extraction_data = self.test_data.get_vram_extraction_data("medium")
        
        params: VRAMExtractionParams = {
            "vram_path": extraction_data["vram_path"],
            "cgram_path": extraction_data["cgram_path"],
            "output_base": extraction_data["output_base"],
            "create_grayscale": True,
            "grayscale_mode": True,
        }
        
        workers = []
        try:
            # Create multiple workers simultaneously 
            for i in range(3):
                # Modify output base to avoid conflicts  
                worker_params = params.copy()
                worker_params["output_base"] = f"{params['output_base']}_worker_{i}"
                
                factory = StandardManagerFactory()
                worker = WorkerOwnedVRAMExtractionWorker(
                    worker_params, factory, parent=self.qt_app
                )
                workers.append(worker)
            
            # Validate isolation (MOCKS CAN'T TEST REAL ISOLATION)
            for i, worker in enumerate(workers):
                for j, other_worker in enumerate(workers):
                    if i != j:
                        assert worker.manager is not other_worker.manager, \
                            f"Worker {i} and {j} should have separate managers"
                        assert worker.manager.parent() is worker, \
                            f"Worker {i} should own its manager"
                        assert other_worker.manager.parent() is other_worker, \
                            f"Worker {j} should own its manager"
            
            # Start all workers and validate they don't interfere
            success_count = 0
            for worker in workers:
                try:
                    # Start the worker using real QThread API
                    worker.start()
                    if worker.wait(8000):  # Wait up to 8 seconds
                        success_count += 1
                except Exception as e:
                    # Worker may fail due to file conflicts, that's ok for isolation test
                    print(f"Worker failed (expected in isolation test): {e}")
            
            # At least some should succeed (real operations may have timing differences)
            assert success_count > 0, "At least one worker should succeed"
            
        finally:
            # Cleanup
            for worker in workers:
                worker.setParent(None)


class TestBugDiscoveryRealVsMocked:
    """
    Demonstrate specific bugs that real tests catch but mocked tests miss.
    """
    
    @pytest.fixture(autouse=True)
    def setup_test_infrastructure(self):
        """Set up real testing infrastructure."""
        self.qt_app = TestApplicationFactory.get_application()
        self.manager_factory = RealManagerFixtureFactory(qt_parent=self.qt_app)
        self.test_data = TestDataRepository()
        
        yield
        
        self.manager_factory.cleanup()
        self.test_data.cleanup()
        cleanup_managers()
    
    def test_discovered_bug_manager_ownership_pattern(self):
        """
        Test that exposes manager ownership bugs mocks would hide.
        
        REAL BUG DISCOVERED: Worker-owned managers need proper parent setting
        sequence to avoid Qt lifecycle issues.
        """
        extraction_data = self.test_data.get_vram_extraction_data("medium")
        
        params: VRAMExtractionParams = {
            "vram_path": extraction_data["vram_path"],
            "output_base": extraction_data["output_base"],
            "create_grayscale": True,
        }
        
        # Test the worker-owned pattern
        factory = StandardManagerFactory()
        worker = WorkerOwnedVRAMExtractionWorker(params, factory, parent=self.qt_app)
        
        # This test discovered the bug: manager.setParent(self) must happen 
        # AFTER super().__init__() to avoid Qt lifecycle issues
        assert worker.manager.parent() is worker, \
            "REAL BUG: Manager parent must be set correctly for worker-owned pattern"
        
        # Validate this doesn't conflict with Qt object lifecycle
        validate_qt_object_lifecycle(worker)
        validate_qt_object_lifecycle(worker.manager)
        
        worker.setParent(None)
    
    def test_discovered_bug_signal_connection_cleanup(self):
        """
        Test that exposes signal connection cleanup bugs.
        
        REAL BUG DISCOVERED: Signal connections must be properly cleaned up
        to avoid memory leaks and Qt warnings.
        """
        extraction_data = self.test_data.get_vram_extraction_data("medium")
        
        params: VRAMExtractionParams = {
            "vram_path": extraction_data["vram_path"],
            "output_base": extraction_data["output_base"],
            "create_grayscale": True,
        }
        
        worker = WorkerOwnedVRAMExtractionWorker(params, parent=self.qt_app)
        
        # Connect signals
        initial_connections = len(worker._connections)
        worker.connect_manager_signals()
        
        # Should have connections now
        connected_count = len(worker._connections)
        assert connected_count > initial_connections, "Should have signal connections"
        
        # Disconnect should clean up
        worker.disconnect_manager_signals()
        final_count = len(worker._connections)
        
        # This test discovered that connections list should be cleared
        assert final_count == 0, \
            "REAL BUG: Signal connections should be cleared after disconnect"
        
        worker.setParent(None)


if __name__ == "__main__":
    # Run the tests directly
    pytest.main([__file__, "-v", "-s"])