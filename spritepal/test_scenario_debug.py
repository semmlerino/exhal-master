#!/usr/bin/env python3
"""
Test Scenario Debug - Replicate exact test conditions that cause timeout
"""

import os
import sys
import time
import signal
import threading
import traceback
from pathlib import Path

# Set up environment
os.environ['QT_QPA_PLATFORM'] = 'offscreen'
sys.path.insert(0, str(Path(__file__).parent.parent))

class TestScenarioTracer:
    """Trace the exact test scenario that causes timeout"""
    
    def __init__(self, timeout_seconds=30):
        self.timeout_seconds = timeout_seconds
        self.start_time = None
        self.checkpoints = []
        self.is_running = False
    
    def checkpoint(self, name, details=None):
        """Record a checkpoint with timing"""
        if not self.is_running:
            return
            
        current_time = time.time()
        elapsed = current_time - self.start_time if self.start_time else 0
        
        checkpoint_info = {
            'name': name,
            'elapsed': elapsed,
            'details': details,
            'timestamp': current_time
        }
        self.checkpoints.append(checkpoint_info)
        
        details_str = f" ({details})" if details else ""
        print(f"[{elapsed:.2f}s] CHECKPOINT: {name}{details_str}")
    
    def timeout_handler(self, signum, frame):
        """Handle timeout by printing complete analysis"""
        print(f"\n{'='*80}")
        print(f"🚨 TIMEOUT AFTER {self.timeout_seconds}s - ANALYZING HANG")
        print(f"{'='*80}")
        
        # Analyze checkpoint progression
        print(f"\n📋 CHECKPOINT PROGRESSION:")
        for i, cp in enumerate(self.checkpoints):
            gap = ""
            if i > 0:
                time_gap = cp['elapsed'] - self.checkpoints[i-1]['elapsed']
                if time_gap > 2.0:  # Flag long gaps
                    gap = f" ⚠️  (+{time_gap:.2f}s GAP)"
            
            details = f" - {cp['details']}" if cp['details'] else ""
            print(f"  [{cp['elapsed']:.2f}s] {cp['name']}{details}{gap}")
        
        # Identify likely hang point
        if len(self.checkpoints) >= 2:
            last_checkpoint = self.checkpoints[-1]
            time_since_last = time.time() - last_checkpoint['timestamp']
            print(f"\n🎯 LIKELY HANG POINT:")
            print(f"   Last checkpoint: {last_checkpoint['name']}")
            print(f"   Time since last checkpoint: {time_since_last:.2f}s")
            print(f"   This suggests the hang occurs AFTER this checkpoint")
        
        # Print thread stacks
        print(f"\n🧵 THREAD STACK TRACES:")
        for thread_id, frame in sys._current_frames().items():
            print(f"\n--- Thread {thread_id} ---")
            traceback.print_stack(frame, limit=10)
        
        # Force exit
        print(f"\n💥 FORCED EXIT DUE TO TIMEOUT")
        os._exit(1)
    
    def start(self):
        """Start timeout monitoring"""
        self.start_time = time.time()
        self.is_running = True
        signal.signal(signal.SIGALRM, self.timeout_handler)
        signal.alarm(self.timeout_seconds)
        print(f"🔍 TEST SCENARIO TRACER STARTED (timeout: {self.timeout_seconds}s)")
    
    def stop(self):
        """Stop timeout monitoring"""
        self.is_running = False
        signal.alarm(0)
        
        total_time = time.time() - self.start_time if self.start_time else 0
        print(f"\n✅ TRACER COMPLETED - Total time: {total_time:.2f}s")
        return total_time

def replicate_failing_test_scenario():
    """Replicate the exact scenario from the failing integration test"""
    
    tracer = TestScenarioTracer(timeout_seconds=30)
    tracer.start()
    
    try:
        # Replicate TestRealControllerManagerIntegration.test_real_manager_state_synchronization_vs_mocked_state
        
        tracer.checkpoint("Setting up test infrastructure", "replicating test fixture setup")
        
        # Step 1: Import and set up Qt application (matching test)
        from spritepal.tests.infrastructure import TestApplicationFactory
        qt_app = TestApplicationFactory.get_application()
        
        tracer.checkpoint("Qt application factory initialized", f"app: {type(qt_app).__name__}")
        
        # Step 2: Set up manager fixture factory (matching test)
        from spritepal.tests.infrastructure import RealManagerFixtureFactory
        manager_factory = RealManagerFixtureFactory(qt_parent=qt_app)
        
        tracer.checkpoint("Manager fixture factory created", "real manager factory with Qt parent")
        
        # Step 3: Set up test data repository (matching test)
        from spritepal.tests.infrastructure import TestDataRepository
        test_data = TestDataRepository()
        
        tracer.checkpoint("Test data repository initialized", "test data factory ready")
        
        # Step 4: Set up Qt testing framework (matching test)
        from spritepal.tests.infrastructure import QtTestingFramework
        qt_framework = QtTestingFramework()
        
        tracer.checkpoint("Qt testing framework initialized", "framework ready for Qt tests")
        
        # Step 5: Initialize managers (matching test)
        from spritepal.core.managers import initialize_managers, cleanup_managers
        
        tracer.checkpoint("About to initialize managers", "this is a critical step from original test")
        
        initialize_managers(app_name="SpritePal-Test")
        
        tracer.checkpoint("Managers initialized successfully", "manager singleton registry ready")
        
        # Step 6: Import and use qt_widget_test context manager (matching test)
        from spritepal.tests.infrastructure import qt_widget_test
        from spritepal.ui.main_window import MainWindow
        
        tracer.checkpoint("About to enter qt_widget_test context", "this creates MainWindow with proper lifecycle")
        
        # This is the EXACT pattern from the failing test
        with qt_widget_test(MainWindow) as main_window:
            tracer.checkpoint("MainWindow created via qt_widget_test", "context manager active")
            
            # Step 7: Create controller (matching test)
            from spritepal.core.controller import ExtractionController
            
            tracer.checkpoint("About to create ExtractionController", "this accesses managers via registry")
            
            controller = ExtractionController(main_window)
            
            tracer.checkpoint("ExtractionController created", "controller has manager references")
            
            # Step 8: Get real managers (matching test)
            from spritepal.core.managers import get_extraction_manager, get_session_manager
            
            extraction_manager = get_extraction_manager()
            session_manager = get_session_manager()
            
            tracer.checkpoint("Retrieved real managers from registry", "managers accessible")
            
            # Step 9: Test manager state synchronization (the actual test logic)
            tracer.checkpoint("Testing state synchronization", "replicating exact test operations")
            
            # Simulate state change through controller (from original test)
            controller._on_progress(75, "Testing state synchronization")
            
            tracer.checkpoint("Progress method called", "state change simulated")
            
            # Test extraction completion state propagation (from original test)
            test_files = ["state_test.png", "state_test.pal.json"]
            controller._on_extraction_finished(test_files)
            
            tracer.checkpoint("Extraction finished method called", "completion state propagation tested")
            
            # Process events to allow state propagation (from original test)
            qt_app.processEvents()
            
            tracer.checkpoint("Qt events processed", "allowed for signal propagation")
            
            # Validate controller state updated correctly (from original test)
            assert controller.worker is None, "Worker should be cleaned up after completion"
            
            tracer.checkpoint("Controller state validated", "worker cleanup verified")
            
            # Test error state synchronization (from original test)
            controller.worker = object()  # Set fake worker to test cleanup
            controller._on_extraction_error("State synchronization test error")
            
            tracer.checkpoint("Error state method called", "error handling tested")
            
            # Validate error state cleanup (from original test)
            assert controller.worker is None, "Worker should be cleaned up after error"
            
            tracer.checkpoint("Error state cleanup validated", "error recovery verified")
            
            # Test that managers remain in consistent state (from original test)
            assert extraction_manager is not None, "ExtractionManager should remain accessible"
            assert session_manager is not None, "SessionManager should remain accessible"
            
            tracer.checkpoint("Manager consistency validated", "managers remain accessible after operations")
        
        # Step 10: Context manager exit and cleanup
        tracer.checkpoint("Exited qt_widget_test context", "MainWindow cleanup handled by context manager")
        
        # Step 11: Test cleanup (matching test teardown)
        manager_factory.cleanup()
        test_data.cleanup()
        cleanup_managers()
        
        tracer.checkpoint("Test cleanup completed", "all resources cleaned up")
        
        print(f"\n🎉 TEST SCENARIO COMPLETED SUCCESSFULLY")
        return True
        
    except Exception as e:
        tracer.checkpoint(f"ERROR: {type(e).__name__}: {e}", "exception occurred")
        print(f"\n❌ ERROR DURING TEST SCENARIO: {e}")
        traceback.print_exc()
        return False
    
    finally:
        total_time = tracer.stop()
        
        print(f"\n📊 FINAL ANALYSIS:")
        print(f"   Total execution time: {total_time:.2f}s")
        print(f"   Number of checkpoints: {len(tracer.checkpoints)}")
        if tracer.checkpoints:
            print(f"   Average time per checkpoint: {total_time/len(tracer.checkpoints):.3f}s")

def main():
    """Main function"""
    
    print("TEST SCENARIO TIMEOUT INVESTIGATION")
    print("=" * 60)
    print("Replicating exact conditions from failing integration test...")
    print("=" * 60)
    
    success = replicate_failing_test_scenario()
    
    if success:
        print(f"\n✅ NO TIMEOUT - Test scenario completed successfully!")
        print(f"   This suggests the timeout is environment-specific or intermittent.")
    else:
        print(f"\n❌ TIMEOUT OR ERROR - Successfully reproduced the issue!")
        print(f"   The timeout investigation captured the hang point.")
    
    return success

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print(f"\n⚠️  INTERRUPTED BY USER")
        sys.exit(130)