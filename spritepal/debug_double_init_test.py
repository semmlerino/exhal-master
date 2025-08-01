#!/usr/bin/env python3
"""
Debug script to test double manager initialization
"""

import sys
import time
from pathlib import Path

# Add paths
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))
sys.path.insert(0, str(current_dir.parent))

from tests.infrastructure import TestApplicationFactory, qt_widget_test
from spritepal.core.managers import initialize_managers, cleanup_managers

def test_double_initialization():
    """Test what happens with double manager initialization"""
    print("=== Testing double manager initialization ===")
    
    try:
        # Step 1: Create Qt application
        print("Step 1: Creating Qt application...")
        app = TestApplicationFactory.get_application()
        print("✓ Qt application created")
        
        # Step 2: Initialize managers first time
        print("Step 2: First manager initialization...")
        start_time = time.time()
        initialize_managers(app_name="SpritePal-Test")
        elapsed = time.time() - start_time
        print(f"✓ First initialization completed in {elapsed:.3f}s")
        
        # Step 3: Initialize managers second time (simulate test scenario)
        print("Step 3: Second manager initialization...")
        start_time = time.time()
        initialize_managers(app_name="SpritePal-Test")  # This might hang or cause issues
        elapsed = time.time() - start_time
        print(f"✓ Second initialization completed in {elapsed:.3f}s")
        
        # Step 4: Try qt_widget_test (simulate hanging test)
        print("Step 4: Creating MainWindow with qt_widget_test...")
        start_time = time.time()
        
        from spritepal.ui.main_window import MainWindow
        with qt_widget_test(MainWindow) as main_window:
            elapsed = time.time() - start_time
            print(f"✓ MainWindow created in {elapsed:.3f}s")
            print(f"✓ MainWindow type: {type(main_window)}")
        
        print("=== SUCCESS: Double initialization test passed ===")
        return True
        
    except Exception as e:
        elapsed = time.time() - start_time
        print(f"✗ ERROR after {elapsed:.3f}s: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        cleanup_managers()

if __name__ == "__main__":
    success = test_double_initialization()
    sys.exit(0 if success else 1)