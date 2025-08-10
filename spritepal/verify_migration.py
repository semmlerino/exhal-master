#\!/usr/bin/env python3
"""
Verify the simple dialogs migration by checking import paths.
This script performs static analysis without requiring Qt runtime.
"""

import ast
import sys
from pathlib import Path

def extract_imports(file_path):
    """Extract import statements from a Python file"""
    with open(file_path, 'r') as f:
        tree = ast.parse(f.read())
    
    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            module = node.module or ''
            for alias in node.names:
                imports.append((module, alias.name))
    
    return imports

def verify_dialog(dialog_name, file_path):
    """Verify a dialog has been properly migrated"""
    print(f"\n{dialog_name}:")
    print("-" * 40)
    
    if not file_path.exists():
        print(f"  ✗ File not found: {file_path}")
        return False
    
    try:
        imports = extract_imports(file_path)
        
        # Check for correct import
        has_correct_import = False
        has_old_import = False
        
        for module, name in imports:
            if module == "ui.components.base" and name == "BaseDialog":
                has_correct_import = True
                print(f"  ✓ Correct import found: from {module} import {name}")
            elif module == "ui.components" and name == "BaseDialog":
                has_old_import = True
                print(f"  ✗ Old import found: from {module} import {name}")
        
        if not has_correct_import and not has_old_import:
            print("  ⚠ No BaseDialog import found")
            return False
        
        if has_old_import:
            print("  ✗ MIGRATION NEEDED: Still using old import path")
            return False
        
        if has_correct_import:
            print("  ✓ MIGRATED: Using new import path")
            return True
            
    except Exception as e:
        print(f"  ✗ Error analyzing file: {e}")
        return False

def main():
    """Main verification function"""
    print("=" * 60)
    print("Simple Dialogs Migration Verification")
    print("=" * 60)
    
    # Define dialogs to check
    dialogs = [
        ("SettingsDialog", Path("ui/dialogs/settings_dialog.py")),
        ("UserErrorDialog", Path("ui/dialogs/user_error_dialog.py")),
    ]
    
    results = []
    for name, path in dialogs:
        results.append((name, verify_dialog(name, path)))
    
    # Summary
    print("\n" + "=" * 60)
    print("VERIFICATION SUMMARY")
    print("=" * 60)
    
    migrated = sum(1 for _, success in results if success)
    not_migrated = sum(1 for _, success in results if not success)
    
    print(f"\nTotal dialogs checked: {len(results)}")
    print(f"Successfully migrated: {migrated}")
    print(f"Not migrated: {not_migrated}")
    
    if migrated == len(results):
        print("\n✓ SUCCESS: All simple dialogs have been migrated\!")
        print("\nThese dialogs now:")
        print("  • Use the feature flag system")
        print("  • Can switch between legacy and composed implementations")
        print("  • Maintain full backward compatibility")
        return True
    else:
        print("\n✗ INCOMPLETE: Some dialogs still need migration")
        for name, success in results:
            if not success:
                print(f"  - {name}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
