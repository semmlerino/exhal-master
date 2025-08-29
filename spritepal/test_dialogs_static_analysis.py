#!/usr/bin/env python3
from __future__ import annotations

"""
Static analysis test for simple dialogs migration.
Verifies that the import statements have been correctly updated.
"""

import re
from pathlib import Path

def check_file_imports(file_path, expected_import):
    """Check if a file contains the expected import statement"""
    try:
        with open(file_path, 'r') as f:
            content = f.read()
            
        # Check for the expected import
        if expected_import in content:
            return True, f"Contains correct import: {expected_import}"
        
        # Check for old import (should not be present)
        old_import = "from ui.components import BaseDialog"
        if old_import in content:
            return False, f"Still contains old import: {old_import}"
            
        return False, f"Import not found: {expected_import}"
    except Exception as e:
        return False, f"Error reading file: {e}"

def main():
    """Run static analysis tests"""
    print("Simple Dialogs Migration - Static Analysis")
    print("=" * 60)
    
    # Define files to check
    dialog_files = [
        ("ui/dialogs/settings_dialog.py", "SettingsDialog"),
        ("ui/dialogs/user_error_dialog.py", "UserErrorDialog")
    ]
    
    expected_import = "from ui.components.base import BaseDialog"
    
    results = []
    
    # Check each dialog file
    for file_path, dialog_name in dialog_files:
        full_path = Path(file_path)
        if not full_path.exists():
            print(f"✗ {dialog_name}: File not found at {file_path}")
            results.append((dialog_name, False, "File not found"))
            continue
            
        success, message = check_file_imports(full_path, expected_import)
        
        if success:
            print(f"✓ {dialog_name}: {message}")
            results.append((dialog_name, True, message))
        else:
            print(f"✗ {dialog_name}: {message}")
            results.append((dialog_name, False, message))
    
    # Check that BaseDialog exists at new location
    base_dialog_path = Path("ui/components/base/__init__.py")
    if base_dialog_path.exists():
        # Check if BaseDialog is exported from the module
        with open(base_dialog_path, 'r') as f:
            content = f.read()
            if "BaseDialog" in content:
                print(f"✓ BaseDialog exported from: {base_dialog_path}")
                results.append(("BaseDialog location", True, "Module exports BaseDialog"))
            else:
                print(f"✗ BaseDialog not exported from: {base_dialog_path}")
                results.append(("BaseDialog location", False, "BaseDialog not exported"))
    else:
        print(f"✗ BaseDialog module not found at: {base_dialog_path}")
        results.append(("BaseDialog location", False, "Module not found"))
    
    # Check for composed dialog (optional)
    composed_path = Path("ui/components/composed.py")
    if composed_path.exists():
        print(f"✓ ComposedDialog exists at: {composed_path}")
        results.append(("ComposedDialog", True, "File exists"))
    else:
        print(f"ℹ ComposedDialog not found (optional): {composed_path}")
        # Not a failure - this is optional
    
    # Summary
    print("\n" + "=" * 60)
    print("STATIC ANALYSIS SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for _, success, _ in results if success)
    failed = sum(1 for _, success, _ in results if not success)
    
    print(f"Total checks: {len(results)}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    
    if failed > 0:
        print("\nFailed checks:")
        for name, success, message in results:
            if not success:
                print(f"  - {name}: {message}")
        return False
    else:
        print("\n✓ All static analysis checks passed!")
        print("\nMigration Status:")
        print("  1. SettingsDialog: ✓ Migrated")
        print("  2. UserErrorDialog: ✓ Migrated")
        print("  3. BaseDialog: ✓ Available at new location")
        print("\n  Total: 2/7 simple dialogs migrated to feature flag system")
        return True

if __name__ == "__main__":
    success = main()
    import sys
    sys.exit(0 if success else 1)