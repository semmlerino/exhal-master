#!/usr/bin/env python3
"""
Timeout Investigation Script - Minimal reproduction case
"""

import sys
import time
import threading
from pathlib import Path

# Add parent directory for imports
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

def test_qt_application_creation():
    """Test Qt application creation"""
    print("=== Testing Qt Application Creation ===")
    start_time = time.time()
    
    try:
        from PyQt6.QtWidgets import QApplication
        from PyQt6.QtCore import QTimer
        
        print(f"[{time.time() - start_time:.2f}s] Importing Qt modules...")
        
        # Check if QApplication already exists
        existing_app = QApplication.instance()
        if existing_app:
            print(f"[{time.time() - start_time:.2f}s] Existing QApplication found")
            return existing_app
        
        print(f"[{time.time() - start_time:.2f}s] Creating new QApplication...")
        
        # Create QApplication with minimal args
        app = QApplication([])
        
        print(f"[{time.time() - start_time:.2f}s] QApplication created successfully")
        
        # Test basic functionality
        timer = QTimer()
        timer.setSingleShot(True)
        timer.timeout.connect(lambda: print(f"[{time.time() - start_time:.2f}s] Timer test successful"))
        timer.start(100)
        
        # Process events briefly
        print(f"[{time.time() - start_time:.2f}s] Testing event processing...")
        app.processEvents()
        time.sleep(0.2)
        app.processEvents()
        
        print(f"[{time.time() - start_time:.2f}s] Qt Application setup complete")
        return app
        
    except Exception as e:
        print(f"[{time.time() - start_time:.2f}s] ERROR in Qt application setup: {e}")
        raise

def test_manager_imports():
    """Test manager imports"""
    print("\n=== Testing Manager Imports ===")
    start_time = time.time()
    
    try:
        print(f"[{time.time() - start_time:.2f}s] Importing core managers...")
        from core.managers import (
            initialize_managers, 
            cleanup_managers, 
            get_extraction_manager,
            get_session_manager,
            get_injection_manager,
        )
        print(f"[{time.time() - start_time:.2f}s] Manager imports successful")
        return True
        
    except Exception as e:
        print(f"[{time.time() - start_time:.2f}s] ERROR in manager imports: {e}")
        raise

def test_manager_initialization():
    """Test manager initialization"""
    print("\n=== Testing Manager Initialization ===")
    start_time = time.time()
    
    try:
        from core.managers import initialize_managers, are_managers_initialized
        
        print(f"[{time.time() - start_time:.2f}s] Checking if managers already initialized...")
        if are_managers_initialized():
            print(f"[{time.time() - start_time:.2f}s] Managers already initialized")
            return True
        
        print(f"[{time.time() - start_time:.2f}s] Initializing managers...")
        initialize_managers(app_name="TimeoutTest")
        
        print(f"[{time.time() - start_time:.2f}s] Checking initialization status...")
        if are_managers_initialized():
            print(f"[{time.time() - start_time:.2f}s] Manager initialization successful")
            return True
        else:
            print(f"[{time.time() - start_time:.2f}s] ERROR: Managers not properly initialized")
            return False
        
    except Exception as e:
        print(f"[{time.time() - start_time:.2f}s] ERROR in manager initialization: {e}")
        raise

def test_manager_access():
    """Test accessing individual managers"""
    print("\n=== Testing Manager Access ===")
    start_time = time.time()
    
    try:
        from core.managers import (
            get_extraction_manager,
            get_session_manager,
            get_injection_manager,
        )
        
        print(f"[{time.time() - start_time:.2f}s] Accessing session manager...")
        session_manager = get_session_manager()
        print(f"[{time.time() - start_time:.2f}s] Session manager: {type(session_manager).__name__}")
        
        print(f"[{time.time() - start_time:.2f}s] Accessing extraction manager...")
        extraction_manager = get_extraction_manager()
        print(f"[{time.time() - start_time:.2f}s] Extraction manager: {type(extraction_manager).__name__}")
        
        print(f"[{time.time() - start_time:.2f}s] Accessing injection manager...")
        injection_manager = get_injection_manager()
        print(f"[{time.time() - start_time:.2f}s] Injection manager: {type(injection_manager).__name__}")
        
        print(f"[{time.time() - start_time:.2f}s] All manager access successful")
        return True
        
    except Exception as e:
        print(f"[{time.time() - start_time:.2f}s] ERROR in manager access: {e}")
        raise

def test_controller_creation():
    """Test controller creation"""
    print("\n=== Testing Controller Creation ===")
    start_time = time.time()
    
    try:
        print(f"[{time.time() - start_time:.2f}s] Importing MainWindow...")
        from ui.main_window import MainWindow
        
        print(f"[{time.time() - start_time:.2f}s] Creating MainWindow...")
        main_window = MainWindow()
        
        print(f"[{time.time() - start_time:.2f}s] Importing ExtractionController...")
        from core.controller import ExtractionController
        
        print(f"[{time.time() - start_time:.2f}s] Creating ExtractionController...")
        controller = ExtractionController(main_window)
        
        print(f"[{time.time() - start_time:.2f}s] Controller creation successful")
        
        # Test basic controller functionality
        print(f"[{time.time() - start_time:.2f}s] Testing controller attributes...")
        print(f"[{time.time() - start_time:.2f}s] Controller main_window: {controller.main_window is not None}")
        print(f"[{time.time() - start_time:.2f}s] Controller session_manager: {controller.session_manager is not None}")
        print(f"[{time.time() - start_time:.2f}s] Controller extraction_manager: {controller.extraction_manager is not None}")
        
        # Cleanup
        main_window.close()
        main_window.deleteLater()
        
        print(f"[{time.time() - start_time:.2f}s] Controller test complete")
        return True
        
    except Exception as e:
        print(f"[{time.time() - start_time:.2f}s] ERROR in controller creation: {e}")
        raise

def timeout_handler():
    """Handle timeout by printing stack traces"""
    print("\n=== TIMEOUT HANDLER ACTIVATED ===")
    print("Current thread stack traces:")
    
    for thread_id, frame in sys._current_frames().items():
        print(f"\nThread {thread_id}:")
        import traceback
        traceback.print_stack(frame)

def main():
    """Main timeout investigation"""
    print("TIMEOUT INVESTIGATION STARTED")
    print("=" * 50)
    
    # Set up timeout handler
    timer = threading.Timer(25.0, timeout_handler)  # 25 second timeout
    timer.start()
    
    try:
        overall_start = time.time()
        
        # Test 1: Qt Application
        app = test_qt_application_creation()
        
        # Test 2: Manager Imports  
        test_manager_imports()
        
        # Test 3: Manager Initialization
        test_manager_initialization()
        
        # Test 4: Manager Access
        test_manager_access()
        
        # Test 5: Controller Creation
        test_controller_creation()
        
        print(f"\n=== INVESTIGATION COMPLETE ===")
        print(f"Total time: {time.time() - overall_start:.2f}s")
        print("All tests passed - no timeout issue detected!")
        
    except Exception as e:
        print(f"\n=== INVESTIGATION FAILED ===")
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        timer.cancel()
        
        # Cleanup
        try:
            from core.managers import cleanup_managers
            cleanup_managers()
            print("Managers cleaned up")
        except:
            pass

if __name__ == "__main__":
    main()