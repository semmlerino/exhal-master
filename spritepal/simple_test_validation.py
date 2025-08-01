#!/usr/bin/env python3
"""
Simple validation of testing infrastructure without pytest.

This test validates that the key components work before attempting
to run the full pytest suite.
"""

import sys
import os
from pathlib import Path

# Add parent directory for imports
current_dir = Path(__file__).parent
parent_dir = current_dir.parent
sys.path.insert(0, str(parent_dir))
sys.path.insert(0, str(current_dir))

print("Testing infrastructure validation...")
print(f"Current directory: {current_dir}")
print(f"Parent directory: {parent_dir}")

try:
    # Test 1: Basic Qt application creation
    print("\n1. Testing Qt application creation...")
    from PyQt6.QtWidgets import QApplication
    import sys
    
    # Create Qt application
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    app.setApplicationDisplayName("SpritePal-Test")
    print("✅ Qt application created successfully")
    
    # Test 2: Test manager imports
    print("\n2. Testing manager imports...")
    
    # Try to import managers directly
    try:
        # Add spritepal to path for spritepal-style imports
        sys.path.insert(0, str(parent_dir))
        
        # Now try importing a manager
        from spritepal.core.managers.extraction_manager import ExtractionManager
        print("✅ ExtractionManager imported successfully")
        
        # Try creating a manager
        manager = ExtractionManager(parent=app)
        print("✅ ExtractionManager created successfully")
        print(f"   Manager parent: {type(manager.parent()).__name__}")
        
        # Test basic validation method that we fixed
        test_params = {
            "vram_path": "/tmp/test.dmp",  # Non-existent file (should fail validation)
            "output_base": "test_output"
        }
        
        try:
            result = manager.validate_extraction_params(test_params)
            print(f"❌ Validation should have failed, but returned: {result}")
        except Exception as e:
            print(f"✅ Validation correctly failed: {type(e).__name__}")
        
        # Cleanup
        manager.setParent(None)
        
    except Exception as e:
        print(f"❌ Manager import/creation failed: {e}")
        import traceback
        traceback.print_exc()
        
    # Test 3: Test infrastructure components
    print("\n3. Testing infrastructure components...")
    
    try:
        # Try to import and use TestApplicationFactory
        from tests.infrastructure.qt_application_factory import TestApplicationFactory
        
        # Use the existing application
        TestApplicationFactory._application_instance = app
        test_app = TestApplicationFactory.get_application()
        
        print("✅ TestApplicationFactory works")
        print(f"   App name: {test_app.applicationDisplayName()}")
        
    except Exception as e:
        print(f"❌ TestApplicationFactory failed: {e}")
        
    print("\nValidation complete!")
    
except Exception as e:
    print(f"❌ Critical error during validation: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)