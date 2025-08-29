#!/usr/bin/env python3
from __future__ import annotations

"""
Simple import test for dialogs migration.
Tests that the dialogs can be imported with the new import path.
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

def test_imports():
    """Test that both dialogs can be imported"""
    print("Testing Simple Dialogs Migration - Import Test")
    print("=" * 60)
    
    results = []
    
    # Test SettingsDialog import
    try:
        from ui.dialogs.settings_dialog import SettingsDialog
        print("✓ SettingsDialog imported successfully")
        results.append(("SettingsDialog import", True))
    except ImportError as e:
        print(f"✗ Failed to import SettingsDialog: {e}")
        results.append(("SettingsDialog import", False))
    
    # Test UserErrorDialog import
    try:
        from ui.dialogs.user_error_dialog import UserErrorDialog
        print("✓ UserErrorDialog imported successfully")
        results.append(("UserErrorDialog import", True))
    except ImportError as e:
        print(f"✗ Failed to import UserErrorDialog: {e}")
        results.append(("UserErrorDialog import", False))
    
    # Test BaseDialog import path
    try:
        from ui.components.base import BaseDialog
        print("✓ BaseDialog imported from new path successfully")
        results.append(("BaseDialog new path", True))
    except ImportError as e:
        print(f"✗ Failed to import BaseDialog from new path: {e}")
        results.append(("BaseDialog new path", False))
    
    # Check if composed dialog components are available
    try:
        from ui.components.composed import ComposedDialog
        print("✓ ComposedDialog available for feature flag system")
        results.append(("ComposedDialog available", True))
    except ImportError as e:
        print(f"✗ ComposedDialog not available: {e}")
        results.append(("ComposedDialog available", False))
    
    # Summary
    print("\n" + "=" * 60)
    print("IMPORT TEST SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for _, success in results if success)
    failed = sum(1 for _, success in results if not success)
    
    print(f"Total tests: {len(results)}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    
    if failed > 0:
        print("\nFailed tests:")
        for name, success in results:
            if not success:
                print(f"  - {name}")
        return False
    else:
        print("\n✓ All import tests passed!")
        print("Both dialogs have been successfully migrated to use the new import path.")
        return True

if __name__ == "__main__":
    success = test_imports()
    sys.exit(0 if success else 1)