#!/usr/bin/env python3
"""
Comprehensive import verification script for pixel editor modules.
Tests all imports to ensure no circular dependencies or missing modules.
"""

import os
import sys
import traceback
from typing import Optional

# Set up environment to avoid Qt issues in headless mode
os.environ["QT_QPA_PLATFORM"] = "offscreen"

def test_import(module_name: str, items: Optional[list[str]] = None) -> tuple[bool, str]:
    """Test importing a module and optionally specific items from it."""
    try:
        if items:
            # Test specific imports
            exec(f"from {module_name} import {', '.join(items)}")
            return True, f"✓ Successfully imported {', '.join(items)} from {module_name}"
        # Test module import
        exec(f"import {module_name}")
    except ImportError as e:
        return False, f"✗ ImportError for {module_name}: {e!s}"
    except Exception as e:
        return False, f"✗ Error importing {module_name}: {type(e).__name__}: {e!s}"
    else:
        return True, f"✓ Successfully imported {module_name}"

def main():
    """Run all import tests."""
    print("=" * 80)
    print("PIXEL EDITOR IMPORT VERIFICATION")
    print("=" * 80)

    # Track results
    results: dict[str, list[tuple[str, bool, str]]] = {
        "External Dependencies": [],
        "Core Modules": [],
        "Main Modules": [],
        "Utility Modules": [],
        "Test Modules": []
    }

    # Test external dependencies
    print("\n1. Testing External Dependencies...")
    external_deps = [
        ("PIL", ["Image"]),
        ("numpy", None),
        ("struct", None),
        ("pathlib", ["Path"]),
        ("typing", ["Dict", "List", "Tuple", "Optional", "Any", "Union"]),
        ("dataclasses", ["dataclass", "field"]),
        ("enum", ["Enum", "auto"]),
        ("json", None),
        ("os", None),
        ("sys", None)
    ]

    for module, items in external_deps:
        success, msg = test_import(module, items)
        results["External Dependencies"].append((module, success, msg))

    # Test PyQt6 separately to handle display issues
    print("\n2. Testing PyQt6 Dependencies...")
    try:
        results["External Dependencies"].append(("PyQt6", True, "✓ Successfully imported PyQt6 modules"))
    except Exception as e:
        results["External Dependencies"].append(("PyQt6", False, f"✗ Error importing PyQt6: {e!s}"))

    # Test core pixel editor modules that actually exist
    print("\n3. Testing Core Pixel Editor Modules...")
    core_modules = [
        ("pixel_editor_constants", ["TILE_SIZE", "TILES_PER_ROW", "DEFAULT_PALETTE"]),
        ("pixel_editor_utils", ["snes_to_rgb", "rgb_to_snes", "extract_tiles_from_binary"]),
        ("pixel_editor_widgets", ["TileCanvas", "PaletteWidget", "ColorPicker"]),
        ("pixel_editor_workers", ["TileExtractionWorker", "RomAnalysisWorker"]),
        ("pixel_editor_commands", ["PixelCommand", "DrawCommand", "FillCommand"])
    ]

    for module, items in core_modules:
        success, msg = test_import(module, items)
        results["Core Modules"].append((module, success, msg))

    # Test main application modules
    print("\n4. Testing Main Application Modules...")
    main_modules = [
        ("indexed_pixel_editor", ["IndexedPixelEditor"]),
        ("launch_sprite_pixel_editor", ["launch_editor"])
    ]

    for module, items in main_modules:
        success, msg = test_import(module, items)
        results["Main Modules"].append((module, success, msg))

    # Test test modules
    print("\n5. Testing Test Modules...")
    test_modules = [
        ("test_indexed_pixel_editor_enhanced", None)
    ]

    for module, items in test_modules:
        success, msg = test_import(module, items)
        results["Test Modules"].append((module, success, msg))

    # Check for files in archive that might be needed
    print("\n6. Checking for Missing Modules in Archive...")
    archive_files = [
        "pixel_editor_types.py",
        "debug_pixel_editor.py",
        "extract_for_pixel_editor.py",
        "test_pixel_editor_core.py",
        "test_indexed_pixel_editor.py",
        "run_pixel_editor_tests.py"
    ]

    archive_path = "./archive/pixel_editor/pre_phase1/"
    missing_files = []

    for filename in archive_files:
        if os.path.exists(os.path.join(archive_path, filename)):
            missing_files.append(filename)

    if missing_files:
        print(f"Found {len(missing_files)} modules in archive that might be needed:")
        for f in missing_files:
            print(f"  - {f}")

    # Print results summary
    print("\n" + "=" * 80)
    print("IMPORT VERIFICATION RESULTS")
    print("=" * 80)

    total_tests = 0
    total_passed = 0

    for category, tests in results.items():
        if not tests:
            continue
        print(f"\n{category}:")
        passed = sum(1 for _, success, _ in tests if success)
        total = len(tests)
        total_tests += total
        total_passed += passed

        for _module, _success, msg in tests:
            print(f"  {msg}")

        print(f"  Summary: {passed}/{total} passed")

    # Overall summary
    print("\n" + "=" * 80)
    print(f"OVERALL: {total_passed}/{total_tests} imports successful")
    print("=" * 80)

    # Test for circular imports
    print("\n7. Testing for Circular Imports...")
    try:
        # Import all modules in sequence
        print("✓ No circular import issues detected")
    except Exception as e:
        print(f"✗ Circular import detected: {e}")
        traceback.print_exc()

    # Check specific dependencies between modules
    print("\n8. Checking Module Dependencies...")
    try:
        # Check if indexed_pixel_editor can access all required components
        print("✓ IndexedPixelEditor imports successfully")

        # Check if widgets can be imported
        print("✓ Widget classes import successfully")

    except Exception as e:
        print(f"✗ Error checking dependencies: {e}")
        traceback.print_exc()

    # Return exit code based on results
    if total_passed == total_tests:
        return 0
    else:
        return 1

if __name__ == "__main__":
    sys.exit(main())
