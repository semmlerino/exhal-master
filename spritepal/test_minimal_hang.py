#!/usr/bin/env python3
"""
Minimal test reproduction to debug hanging
"""

import sys
import time
import pytest
from pathlib import Path

# Import exactly like the hanging test does
current_dir = Path(__file__).parent
parent_dir = current_dir.parent
sys.path.insert(0, str(parent_dir))
sys.path.insert(0, str(current_dir))

def test_minimal_hang():
    """Minimal reproduction of hanging test"""
    print("=== MINIMAL HANG REPRODUCTION ===")
    
    # Import real testing infrastructure exactly like hanging test
    from tests.infrastructure import (
        TestApplicationFactory,
        qt_widget_test,
    )
    from spritepal.core.managers import (
        initialize_managers, 
        cleanup_managers,
    )
    from spritepal.ui.main_window import MainWindow

    # Follow exact same pattern as hanging test
    try:
        print("Step 1: Get Qt application...")
        qt_app = TestApplicationFactory.get_application()
        print("✓ Got Qt application")
        
        print("Step 2: Initialize managers...")
        initialize_managers(app_name="SpritePal-Test")
        print("✓ Managers initialized")
        
        print("Step 3: Create MainWindow with qt_widget_test...")
        start_time = time.time()
        
        with qt_widget_test(MainWindow) as main_window:
            elapsed = time.time() - start_time
            print(f"✓ MainWindow created in {elapsed:.3f}s")
            
            # Do something basic like the hanging test
            assert main_window is not None
            print("✓ MainWindow validation passed")
        
        print("=== SUCCESS: Test completed ===")
        
    except Exception as e:
        print(f"✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        cleanup_managers()

if __name__ == "__main__":
    test_minimal_hang()