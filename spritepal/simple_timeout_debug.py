#!/usr/bin/env python3
"""
Simple timeout debug - Focus on manager initialization
"""

import sys
import time
import os
from pathlib import Path

# Set up Python path properly
sys.path.insert(0, str(Path(__file__).parent.parent))  # Add exhal-master directory

def debug_manager_initialization():
    """Debug the manager initialization process step by step"""
    
    print("=== MANAGER INITIALIZATION DEBUG ===")
    
    try:
        # Step 1: Set up Qt application
        print("[1] Setting up Qt application...")
        start_time = time.time()
        
        # Force QT_QPA_PLATFORM to offscreen to avoid display issues
        os.environ['QT_QPA_PLATFORM'] = 'offscreen'
        
        from PyQt6.QtWidgets import QApplication
        from PyQt6.QtCore import QCoreApplication
        
        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        
        print(f"[1] Qt setup complete in {time.time() - start_time:.2f}s")
        
        # Step 2: Import manager registry 
        print("[2] Importing manager registry...")
        start_time = time.time()
        
        from spritepal.core.managers.registry import (
            initialize_managers,
            get_session_manager,
            get_extraction_manager,
            get_injection_manager,
            are_managers_initialized
        )
        
        print(f"[2] Manager imports complete in {time.time() - start_time:.2f}s")
        
        # Step 3: Check current state
        print("[3] Checking initialization state...")
        start_time = time.time()
        
        initialized = are_managers_initialized()
        print(f"[3] Managers initialized: {initialized} (checked in {time.time() - start_time:.2f}s)")
        
        if not initialized:
            # Step 4: Initialize managers
            print("[4] Initializing managers...")
            start_time = time.time()
            
            # This is the suspected blocking operation
            initialize_managers(app_name="TimeoutDebug")
            
            print(f"[4] Manager initialization complete in {time.time() - start_time:.2f}s")
        
        # Step 5: Test manager access
        print("[5] Testing manager access...")
        start_time = time.time()
        
        session_mgr = get_session_manager()
        extraction_mgr = get_extraction_manager()
        injection_mgr = get_injection_manager()
        
        print(f"[5] Manager access complete in {time.time() - start_time:.2f}s")
        print(f"  - SessionManager: {type(session_mgr).__name__}")
        print(f"  - ExtractionManager: {type(extraction_mgr).__name__}")
        print(f"  - InjectionManager: {type(injection_mgr).__name__}")
        
        print("\n=== SUCCESS: All manager operations completed ===")
        return True
        
    except Exception as e:
        print(f"\n=== ERROR: {e} ===")
        import traceback
        traceback.print_exc()
        return False

def debug_controller_creation():
    """Debug controller creation"""
    
    print("\n=== CONTROLLER CREATION DEBUG ===")
    
    try:
        # Step 1: Import MainWindow
        print("[1] Importing MainWindow...")
        start_time = time.time()
        
        from spritepal.ui.main_window import MainWindow
        
        print(f"[1] MainWindow import complete in {time.time() - start_time:.2f}s")
        
        # Step 2: Create MainWindow
        print("[2] Creating MainWindow...")
        start_time = time.time()
        
        main_window = MainWindow()
        
        print(f"[2] MainWindow creation complete in {time.time() - start_time:.2f}s")
        
        # Step 3: Import controller
        print("[3] Importing ExtractionController...")  
        start_time = time.time()
        
        from spritepal.core.controller import ExtractionController
        
        print(f"[3] Controller import complete in {time.time() - start_time:.2f}s")
        
        # Step 4: Create controller (this is where timeout likely occurs)
        print("[4] Creating ExtractionController...")
        start_time = time.time()
        
        controller = ExtractionController(main_window)
        
        print(f"[4] Controller creation complete in {time.time() - start_time:.2f}s")
        
        # Clean up
        main_window.close()
        
        print("\n=== SUCCESS: Controller creation completed ===")
        return True
        
    except Exception as e:
        print(f"\n=== ERROR: {e} ===")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main debug function with timeout handling"""
    
    print("SIMPLE TIMEOUT DEBUG STARTED")
    print("=" * 40)
    
    overall_start = time.time()
    
    try:
        # Test 1: Manager initialization
        if not debug_manager_initialization():
            return False
        
        # Test 2: Controller creation  
        if not debug_controller_creation():
            return False
        
        print(f"\n=== ALL TESTS PASSED ===")
        print(f"Total time: {time.time() - overall_start:.2f}s")
        return True
        
    except KeyboardInterrupt:
        print(f"\n=== INTERRUPTED ===")
        print(f"Time elapsed: {time.time() - overall_start:.2f}s")
        return False
    
    except Exception as e:
        print(f"\n=== UNEXPECTED ERROR: {e} ===")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)