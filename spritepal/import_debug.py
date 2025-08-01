#!/usr/bin/env python3
"""
Import debug - Trace which import causes Qt widget before QApplication issue
"""

import sys
import os
from pathlib import Path

# Set up Python path properly
sys.path.insert(0, str(Path(__file__).parent.parent))  # Add exhal-master directory

def test_imports_step_by_step():
    """Test imports step by step to find the problematic one"""
    
    print("=== IMPORT DEBUG - STEP BY STEP ===")
    
    # Force offscreen mode before any Qt imports
    os.environ['QT_QPA_PLATFORM'] = 'offscreen'
    print("[ENV] Set QT_QPA_PLATFORM=offscreen")
    
    try:
        # Step 1: Basic Qt imports
        print("[1] Importing PyQt6.QtCore...")
        from PyQt6.QtCore import QCoreApplication
        print("[1] ✓ PyQt6.QtCore imported")
        
        print("[2] Importing PyQt6.QtWidgets...")
        from PyQt6.QtWidgets import QApplication
        print("[2] ✓ PyQt6.QtWidgets imported")
        
        # Step 3: Create QApplication FIRST
        print("[3] Creating QApplication...")
        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        print("[3] ✓ QApplication created")
        
        # Step 4: Test manager imports one by one
        print("[4] Testing manager imports...")
        
        print("[4a] Importing base_manager...")
        from spritepal.core.managers.base_manager import BaseManager
        print("[4a] ✓ base_manager imported")
        
        print("[4b] Importing exceptions...")
        from spritepal.core.managers.exceptions import ManagerError
        print("[4b] ✓ exceptions imported")
        
        print("[4c] Importing session_manager...")
        from spritepal.core.managers.session_manager import SessionManager
        print("[4c] ✓ session_manager imported")
        
        print("[4d] Importing extraction_manager...")
        from spritepal.core.managers.extraction_manager import ExtractionManager
        print("[4d] ✓ extraction_manager imported")
        
        print("[4e] Importing injection_manager...")
        from spritepal.core.managers.injection_manager import InjectionManager
        print("[4e] ✓ injection_manager imported")
        
        print("[4f] Importing registry...")
        from spritepal.core.managers.registry import ManagerRegistry
        print("[4f] ✓ registry imported")
        
        # Step 5: Test controller import
        print("[5] Testing controller import...")
        from spritepal.core.controller import ExtractionController
        print("[5] ✓ controller imported")
        
        # Step 6: Test UI imports (these are likely problematic)
        print("[6] Testing UI imports...")
        
        print("[6a] Importing main_window...")
        from spritepal.ui.main_window import MainWindow
        print("[6a] ✓ main_window imported")
        
        print("\n=== ALL IMPORTS SUCCESSFUL ===")
        return True
        
    except Exception as e:
        print(f"\n=== IMPORT FAILED: {e} ===")
        import traceback
        traceback.print_exc()
        return False

def test_manager_instantiation():
    """Test manager instantiation"""
    
    print("\n=== MANAGER INSTANTIATION TEST ===")
    
    try:
        # Import required components
        from spritepal.core.managers.session_manager import SessionManager
        from spritepal.core.managers.extraction_manager import ExtractionManager
        from spritepal.core.managers.injection_manager import InjectionManager
        from PyQt6.QtWidgets import QApplication
        
        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        
        print("[1] Testing SessionManager creation...")
        session_mgr = SessionManager("TestApp")
        print("[1] ✓ SessionManager created")
        
        print("[2] Testing ExtractionManager creation...")
        extraction_mgr = ExtractionManager(parent=app)
        print("[2] ✓ ExtractionManager created")
        
        print("[3] Testing InjectionManager creation...")
        injection_mgr = InjectionManager(parent=app)
        print("[3] ✓ InjectionManager created")
        
        print("\n=== MANAGER INSTANTIATION SUCCESSFUL ===")
        return True
        
    except Exception as e:
        print(f"\n=== MANAGER INSTANTIATION FAILED: {e} ===")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main debug function"""
    
    print("IMPORT DEBUG STARTED")
    print("=" * 30)
    
    try:
        # Test 1: Step-by-step imports
        if not test_imports_step_by_step():
            print("❌ Import test failed")
            return False
        
        # Test 2: Manager instantiation
        if not test_manager_instantiation():
            print("❌ Manager instantiation failed")
            return False
        
        print("\n✅ ALL TESTS PASSED")
        return True
        
    except Exception as e:
        print(f"\n❌ UNEXPECTED ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)