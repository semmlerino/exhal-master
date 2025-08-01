#!/usr/bin/env python3
"""
Debug script to isolate MainWindow creation issues
"""

import sys
import time
from pathlib import Path

# Add the spritepal directory to path
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))
sys.path.insert(0, str(current_dir.parent))

from tests.infrastructure import TestApplicationFactory
from spritepal.core.managers import initialize_managers, cleanup_managers

def test_main_window_creation():
    """Test MainWindow creation in isolation"""
    print("=== Starting MainWindow creation test ===")
    
    try:
        # Step 1: Create Qt application
        print("Step 1: Creating Qt application...")
        app = TestApplicationFactory.get_application()
        print("✓ Qt application created successfully")
        
        # Step 2: Initialize managers
        print("Step 2: Initializing managers...")
        start_time = time.time()
        initialize_managers(app_name="SpritePal-Debug")
        elapsed = time.time() - start_time
        print(f"✓ Managers initialized in {elapsed:.3f}s")
        
        # Step 3: Try to create MainWindow
        print("Step 3: Creating MainWindow...")
        start_time = time.time()
        
        from spritepal.ui.main_window import MainWindow
        main_window = MainWindow()
        
        elapsed = time.time() - start_time
        print(f"✓ MainWindow created in {elapsed:.3f}s")
        
        # Step 4: Clean up
        print("Step 4: Cleaning up...")
        main_window.close()
        cleanup_managers()
        print("✓ Cleanup completed")
        
        print("=== SUCCESS: MainWindow creation test passed ===")
        
    except Exception as e:
        print(f"✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

if __name__ == "__main__":
    success = test_main_window_creation()
    sys.exit(0 if success else 1)