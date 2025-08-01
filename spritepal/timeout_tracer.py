#!/usr/bin/env python3
"""
Timeout Tracer - Identify exact location of timeout in manager initialization
"""

import os
import sys
import time
import signal
import threading
import traceback
from pathlib import Path

# Set up environment and paths
os.environ['QT_QPA_PLATFORM'] = 'offscreen'
sys.path.insert(0, str(Path(__file__).parent.parent))

class TimeoutTracer:
    """Trace where exactly the code hangs during manager initialization"""
    
    def __init__(self, timeout_seconds=20):
        self.timeout_seconds = timeout_seconds
        self.start_time = None
        self.checkpoint_times = {}
        self.is_running = False
    
    def checkpoint(self, name):
        """Record a checkpoint with timing"""
        if not self.is_running:
            return
            
        current_time = time.time()
        elapsed = current_time - self.start_time if self.start_time else 0
        self.checkpoint_times[name] = elapsed
        print(f"[{elapsed:.2f}s] CHECKPOINT: {name}")
    
    def timeout_handler(self, signum, frame):
        """Handle timeout by printing stack traces"""
        print(f"\n{'='*60}")
        print(f"TIMEOUT AFTER {self.timeout_seconds}s - DUMPING STACK TRACES")
        print(f"{'='*60}")
        
        # Print checkpoint history
        print("\nCheckpoint History:")
        for name, elapsed in self.checkpoint_times.items():
            print(f"  [{elapsed:.2f}s] {name}")
        
        # Print all thread stack traces
        print(f"\nAll Thread Stack Traces:")
        for thread_id, frame in sys._current_frames().items():
            print(f"\n--- Thread {thread_id} ---")
            traceback.print_stack(frame)
        
        # Force exit
        print(f"\nFORCED EXIT DUE TO TIMEOUT")
        os._exit(1)
    
    def start(self):
        """Start timeout monitoring"""
        self.start_time = time.time()
        self.is_running = True
        signal.signal(signal.SIGALRM, self.timeout_handler)
        signal.alarm(self.timeout_seconds)
        print(f"TIMEOUT TRACER STARTED - Will timeout after {self.timeout_seconds}s")
    
    def stop(self):
        """Stop timeout monitoring"""
        self.is_running = False
        signal.alarm(0)
        
        total_time = time.time() - self.start_time if self.start_time else 0
        print(f"\nTIMEOUT TRACER STOPPED - Total time: {total_time:.2f}s")
        return total_time

def test_manager_initialization_with_tracing():
    """Test manager initialization with detailed tracing"""
    
    tracer = TimeoutTracer(timeout_seconds=25)
    tracer.start()
    
    try:
        tracer.checkpoint("Starting Qt application setup")
        
        # Step 1: Qt Application setup
        from PyQt6.QtWidgets import QApplication
        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        
        tracer.checkpoint("Qt application created")
        
        # Step 2: Import testing infrastructure
        from spritepal.tests.infrastructure import (
            TestApplicationFactory,
            RealManagerFixtureFactory,
            TestDataRepository,
            QtTestingFramework,
            qt_widget_test,
            validate_qt_object_lifecycle,
        )
        
        tracer.checkpoint("Testing infrastructure imported")
        
        # Step 3: Import manager components
        from spritepal.core.managers import (
            initialize_managers, 
            cleanup_managers, 
            get_extraction_manager,
            get_session_manager,
            get_injection_manager,
        )
        
        tracer.checkpoint("Manager components imported")
        
        # Step 4: Import UI components  
        from spritepal.ui.main_window import MainWindow
        from spritepal.core.controller import ExtractionController
        
        tracer.checkpoint("UI components imported")
        
        # Step 5: Initialize managers (SUSPECTED BLOCKING OPERATION)
        tracer.checkpoint("About to initialize managers - SUSPECTED HANG POINT")
        
        initialize_managers(app_name="TimeoutTracer-Test")
        
        tracer.checkpoint("Managers initialized successfully")
        
        # Step 6: Test manager access
        session_manager = get_session_manager()
        extraction_manager = get_extraction_manager()
        injection_manager = get_injection_manager()
        
        tracer.checkpoint("Manager access successful")
        
        # Step 7: Create MainWindow (ANOTHER SUSPECTED HANG POINT)
        tracer.checkpoint("About to create MainWindow - ANOTHER SUSPECTED HANG POINT")
        
        main_window = MainWindow()
        
        tracer.checkpoint("MainWindow created successfully")
        
        # Step 8: Create controller (FINAL SUSPECTED HANG POINT)
        tracer.checkpoint("About to create ExtractionController - FINAL SUSPECTED HANG POINT")
        
        controller = ExtractionController(main_window)
        
        tracer.checkpoint("ExtractionController created successfully")
        
        # Step 9: Test basic controller operations
        tracer.checkpoint("Testing controller operations")
        
        # Test the specific method from the failing test
        controller._on_progress(75, "Testing state synchronization")
        
        tracer.checkpoint("Controller progress method tested")
        
        # Test extraction completion state propagation  
        test_files = ["state_test.png", "state_test.pal.json"]
        controller._on_extraction_finished(test_files)
        
        tracer.checkpoint("Controller extraction finished method tested")
        
        # Clean up
        main_window.close()
        cleanup_managers()
        
        tracer.checkpoint("Cleanup completed")
        
        print(f"\n✅ ALL OPERATIONS COMPLETED SUCCESSFULLY")
        return True
        
    except Exception as e:
        tracer.checkpoint(f"ERROR: {e}")
        print(f"\n❌ ERROR DURING EXECUTION: {e}")
        traceback.print_exc()
        return False
    
    finally:
        total_time = tracer.stop()
        
        print(f"\nFinal Checkpoint Summary:")
        for name, elapsed in tracer.checkpoint_times.items():
            print(f"  [{elapsed:.2f}s] {name}")

def main():
    """Main function"""
    
    print("TIMEOUT TRACER INVESTIGATION")
    print("=" * 50)
    print("This will trace exactly where the manager initialization hangs")
    print("=" * 50)
    
    success = test_manager_initialization_with_tracing()
    
    if success:
        print(f"\n🎉 INVESTIGATION SUCCESSFUL - No timeout detected!")
    else:
        print(f"\n💥 INVESTIGATION FAILED - Timeout or error occurred!")
    
    return success

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print(f"\n⚠️  INTERRUPTED BY USER")
        sys.exit(130)