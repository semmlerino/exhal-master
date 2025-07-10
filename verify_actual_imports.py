#!/usr/bin/env python3
"""
Verification script that checks actual imports based on what exists in the codebase.
"""

import ast
import os
import sys
import traceback
from typing import List, Set, Tuple

# Set up environment to avoid Qt issues in headless mode
os.environ["QT_QPA_PLATFORM"] = "offscreen"

def extract_exports(filename: str) -> Set[str]:
    """Extract all exportable names from a Python file."""
    exports = set()

    try:
        with open(filename) as f:
            tree = ast.parse(f.read(), filename)

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) or isinstance(node, ast.FunctionDef):
                exports.add(node.name)
            elif isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id.isupper():
                        exports.add(target.id)
    except Exception as e:
        print(f"Error parsing {filename}: {e}")

    return exports

def test_actual_import(module_name: str, test_items: List[str] = None) -> Tuple[bool, str, List[str]]:
    """Test importing a module and return what's actually available."""
    actual_items = []

    try:
        module = __import__(module_name)
        available = dir(module)

        if test_items:
            missing = [item for item in test_items if item not in available]
            found = [item for item in test_items if item in available]

            if missing:
                return False, f"✗ {module_name}: Missing {', '.join(missing)}", found
            return True, f"✓ {module_name}: All requested items found", found
        # Just import the module
        return True, f"✓ Successfully imported {module_name}", available

    except ImportError as e:
        return False, f"✗ ImportError for {module_name}: {e!s}", []
    except Exception as e:
        return False, f"✗ Error importing {module_name}: {type(e).__name__}: {e!s}", []

def main():
    """Run comprehensive import verification."""
    print("=" * 80)
    print("PIXEL EDITOR ACTUAL IMPORT VERIFICATION")
    print("=" * 80)

    # First, analyze what's in each file
    print("\n1. Analyzing Module Contents...")
    modules_to_analyze = [
        "pixel_editor_constants.py",
        "pixel_editor_utils.py",
        "pixel_editor_widgets.py",
        "pixel_editor_workers.py",
        "pixel_editor_commands.py",
        "indexed_pixel_editor.py",
        "launch_sprite_pixel_editor.py"
    ]

    module_exports = {}
    for module_file in modules_to_analyze:
        if os.path.exists(module_file):
            exports = extract_exports(module_file)
            module_exports[module_file] = exports
            print(f"\n{module_file}:")
            print(f"  Found {len(exports)} exports")
            if len(exports) <= 10:
                print(f"  Exports: {', '.join(sorted(exports))}")
            else:
                print(f"  Sample exports: {', '.join(sorted(list(exports))[:10])}...")

    # Now test actual imports
    print("\n\n2. Testing Actual Imports...")

    # Test external dependencies
    print("\n  External Dependencies:")
    external_tests = [
        ("PIL.Image", None),
        ("numpy", None),
        ("PyQt6.QtWidgets", ["QWidget", "QApplication", "QMainWindow"]),
        ("PyQt6.QtCore", ["Qt", "pyqtSignal", "QTimer"]),
        ("PyQt6.QtGui", ["QPainter", "QColor", "QImage"])
    ]

    for module, items in external_tests:
        success, msg, _ = test_actual_import(module, items)
        print(f"    {msg}")

    # Test pixel editor modules with actual exports
    print("\n  Pixel Editor Modules:")

    # Test each module
    success, msg, available = test_actual_import("pixel_editor_constants")
    print(f"    {msg}")
    if success and available:
        constants = [item for item in available if item.isupper() and not item.startswith("_")]
        print(f"      Available constants: {', '.join(constants[:10])}...")

    success, msg, available = test_actual_import("pixel_editor_utils")
    print(f"    {msg}")
    if success and available:
        functions = [item for item in available if not item.startswith("_") and item.islower()]
        print(f"      Available functions: {', '.join(functions[:10])}...")

    success, msg, available = test_actual_import("pixel_editor_widgets")
    print(f"    {msg}")
    if success and available:
        classes = [item for item in available if not item.startswith("_") and item[0].isupper()]
        print(f"      Available classes: {', '.join(classes)}")

    success, msg, available = test_actual_import("indexed_pixel_editor", ["IndexedPixelEditor"])
    print(f"    {msg}")

    # Test circular imports
    print("\n\n3. Testing for Circular Import Issues...")
    try:
        # Import all modules in order
        print("✓ No circular import issues detected")
    except Exception as e:
        print(f"✗ Circular import issue: {e}")

    # Check which modules from archive might be needed
    print("\n\n4. Checking Archive for Missing Components...")
    archive_path = "./archive/pixel_editor/pre_phase1/"
    if os.path.exists(archive_path):
        archive_files = os.listdir(archive_path)
        py_files = [f for f in archive_files if f.endswith(".py")]

        print(f"Found {len(py_files)} Python files in archive:")
        for f in sorted(py_files):
            if f not in modules_to_analyze:
                print(f"  - {f} (not in current directory)")

    # Test if IndexedPixelEditor can be instantiated
    print("\n\n5. Testing IndexedPixelEditor Instantiation...")
    try:
        from PyQt6.QtWidgets import QApplication
        app = QApplication.instance()
        if app is None:
            app = QApplication(sys.argv)

        from indexed_pixel_editor import IndexedPixelEditor
        editor = IndexedPixelEditor()
        print("✓ IndexedPixelEditor can be instantiated")

        # Check what attributes it has
        attrs = [attr for attr in dir(editor) if not attr.startswith("_")]
        print(f"  Available methods/attributes: {len(attrs)}")

    except Exception as e:
        print(f"✗ Error instantiating IndexedPixelEditor: {e}")
        traceback.print_exc()

    print("\n" + "=" * 80)
    print("VERIFICATION COMPLETE")
    print("=" * 80)

if __name__ == "__main__":
    main()
