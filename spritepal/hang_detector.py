#!/usr/bin/env python3
"""
Hang Detector - Use threading to capture exact hang location
"""

import os
import sys
import time
import threading
import traceback
from pathlib import Path

# Set up environment
os.environ['QT_QPA_PLATFORM'] = 'offscreen'
sys.path.insert(0, str(Path(__file__).parent.parent))

class HangDetector:
    """Detect and analyze hangs using threading"""
    
    def __init__(self, check_interval=2.0, max_wait=15.0):
        self.check_interval = check_interval
        self.max_wait = max_wait
        self.last_checkpoint_time = None
        self.last_checkpoint_name = None
        self.is_monitoring = False
        self.main_thread = None
        self.monitor_thread = None
    
    def start_monitoring(self):
        """Start hang monitoring in background thread"""
        self.is_monitoring = True
        self.main_thread = threading.current_thread()
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        print(f"🔍 HANG DETECTOR: Started monitoring (check every {self.check_interval}s, max wait {self.max_wait}s)")
    
    def stop_monitoring(self):
        """Stop hang monitoring"""
        self.is_monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=1.0)
        print(f"✅ HANG DETECTOR: Stopped monitoring")
    
    def checkpoint(self, name):
        """Update checkpoint - call this from main thread"""
        current_time = time.time()
        self.last_checkpoint_time = current_time
        self.last_checkpoint_name = name
        
        elapsed = current_time - getattr(self, 'start_time', current_time)
        print(f"[{elapsed:.2f}s] CHECKPOINT: {name}")
    
    def _monitor_loop(self):
        """Monitor loop running in background thread"""
        self.start_time = time.time()
        
        while self.is_monitoring:
            time.sleep(self.check_interval)
            
            if not self.is_monitoring:
                break
            
            current_time = time.time()
            
            if self.last_checkpoint_time:
                time_since_checkpoint = current_time - self.last_checkpoint_time
                
                if time_since_checkpoint > self.max_wait:
                    print(f"\n{'='*80}")
                    print(f"🚨 HANG DETECTED!")
                    print(f"{'='*80}")
                    print(f"Last checkpoint: {self.last_checkpoint_name}")
                    print(f"Time since last checkpoint: {time_since_checkpoint:.2f}s")
                    print(f"Total elapsed time: {current_time - self.start_time:.2f}s")
                    
                    # Get main thread stack trace
                    print(f"\n🧵 MAIN THREAD STACK TRACE:")
                    
                    # Get the frame of the main thread
                    main_frame = sys._current_frames().get(self.main_thread.ident)
                    if main_frame:
                        traceback.print_stack(main_frame)
                    else:
                        print("Could not get main thread frame")
                    
                    print(f"\n🔍 ALL THREAD STACK TRACES:")
                    for thread_id, frame in sys._current_frames().items():
                        thread_name = "Unknown"
                        for thread in threading.enumerate():
                            if thread.ident == thread_id:
                                thread_name = thread.name
                                break
                        
                        print(f"\n--- Thread {thread_id} ({thread_name}) ---")
                        traceback.print_stack(frame, limit=15)
                    
                    print(f"\n💥 EXITING DUE TO HANG DETECTION")
                    os._exit(1)

def test_with_hang_detection():
    """Run the test scenario with hang detection"""
    
    detector = HangDetector(check_interval=1.0, max_wait=10.0)
    
    try:
        detector.start_monitoring()
        detector.checkpoint("Starting test scenario with hang detection")
        
        # Import components step by step
        detector.checkpoint("Importing test infrastructure")
        from spritepal.tests.infrastructure import (
            TestApplicationFactory,
            RealManagerFixtureFactory, 
            TestDataRepository,
            QtTestingFramework,
            qt_widget_test
        )
        
        detector.checkpoint("Creating Qt application")
        qt_app = TestApplicationFactory.get_application()
        
        detector.checkpoint("Creating manager fixture factory")
        manager_factory = RealManagerFixtureFactory(qt_parent=qt_app)
        
        detector.checkpoint("Creating test data repository")
        test_data = TestDataRepository()
        
        detector.checkpoint("Creating Qt testing framework")
        qt_framework = QtTestingFramework()
        
        detector.checkpoint("Importing and initializing managers")
        from spritepal.core.managers import initialize_managers, cleanup_managers
        initialize_managers(app_name="HangDetector-Test")
        
        detector.checkpoint("Importing UI components")
        from spritepal.ui.main_window import MainWindow
        from spritepal.core.controller import ExtractionController
        
        detector.checkpoint("About to enter qt_widget_test context - SUSPECTED HANG POINT")
        
        # This is likely where the hang occurs
        with qt_widget_test(MainWindow) as main_window:
            detector.checkpoint("MainWindow created successfully")
            
            detector.checkpoint("Creating ExtractionController")
            controller = ExtractionController(main_window)
            
            detector.checkpoint("Testing controller operations")
            controller._on_progress(50, "Test operation")
            
            detector.checkpoint("Processing Qt events")
            qt_app.processEvents()
            
            detector.checkpoint("Completing controller tests")
        
        detector.checkpoint("Exited qt_widget_test context")
        
        # Cleanup
        detector.checkpoint("Cleaning up")
        manager_factory.cleanup()
        test_data.cleanup()
        cleanup_managers()
        
        detector.checkpoint("Test completed successfully")
        
        print(f"\n✅ TEST COMPLETED WITHOUT HANG")
        return True
        
    except Exception as e:
        detector.checkpoint(f"ERROR: {e}")
        print(f"\n❌ ERROR: {e}")
        traceback.print_exc()
        return False
    
    finally:
        detector.stop_monitoring()

def main():
    """Main function"""
    
    print("HANG DETECTOR INVESTIGATION")
    print("=" * 50)
    print("Using threading to detect and analyze hangs...")
    print("=" * 50)
    
    success = test_with_hang_detection()
    
    if success:
        print(f"\n🎉 SUCCESS: No hang detected")
    else:
        print(f"\n💥 FAILURE: Hang or error occurred")
    
    return success

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print(f"\n⚠️  INTERRUPTED BY USER")
        sys.exit(130)