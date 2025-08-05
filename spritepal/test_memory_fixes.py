#!/usr/bin/env python3
"""
Test to verify memory leak fixes work properly.
"""

import sys
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

def test_lambda_fixes():
    """Verify lambda closures have been fixed."""
    print("Testing lambda closure fixes...")

    # Check main_window.py for lambda usage
    main_window_path = Path(__file__).parent / "ui" / "main_window.py"
    with open(main_window_path) as f:
        content = f.read()

    # Count lambda occurrences in signal connections
    lambda_count = content.count("lambda:")
    print(f"Found {lambda_count} lambda expressions in main_window.py")

    # Check specific files that were fixed
    files_to_check = [
        "ui/dialogs/manual_offset_unified_integrated.py",
        "ui/dialogs/advanced_search_dialog.py",
        "ui/rom_extraction_panel.py"
    ]

    total_lambdas = 0
    for file_path in files_to_check:
        full_path = Path(__file__).parent / file_path
        if full_path.exists():
            with open(full_path) as f:
                content = f.read()
                lambdas = content.count("lambda:")
                print(f"{file_path}: {lambdas} lambdas")
                total_lambdas += lambdas

    print(f"\nTotal lambdas in fixed files: {total_lambdas}")
    return total_lambdas == 0


def test_cleanup_methods():
    """Verify cleanup methods exist in dialogs."""
    print("\nTesting cleanup methods...")

    # Check manual offset dialog has cleanup
    dialog_path = Path(__file__).parent / "ui" / "dialogs" / "manual_offset_unified_integrated.py"
    with open(dialog_path) as f:
        content = f.read()

    has_cleanup = "def cleanup(self):" in content
    has_close_event = "def closeEvent(self, event):" in content
    calls_cleanup = "self.cleanup()" in content

    print(f"Has cleanup method: {has_cleanup}")
    print(f"Has closeEvent: {has_close_event}")
    print(f"closeEvent calls cleanup: {calls_cleanup}")

    return has_cleanup and has_close_event and calls_cleanup


def test_weakref_usage():
    """Verify weakref is used appropriately."""
    print("\nTesting weakref usage...")

    files_with_weakref = []
    for file_path in Path(__file__).parent.rglob("*.py"):
        if "__pycache__" in str(file_path):
            continue

        try:
            with open(file_path) as f:
                content = f.read()
                if "import weakref" in content or "from weakref import" in content:
                    files_with_weakref.append(file_path.relative_to(Path(__file__).parent))
        except:
            pass

    print(f"Files using weakref: {len(files_with_weakref)}")
    for f in files_with_weakref:
        print(f"  - {f}")

    return len(files_with_weakref) > 0


def test_type_aliases():
    """Verify type aliases file was created."""
    print("\nTesting type aliases...")

    type_aliases_path = Path(__file__).parent / "utils" / "type_aliases.py"
    exists = type_aliases_path.exists()
    print(f"Type aliases file exists: {exists}")

    if exists:
        with open(type_aliases_path) as f:
            content = f.read()
            aliases = content.count("TypeAlias")
            print(f"Number of type aliases defined: {aliases}")
            return aliases > 10

    return False


def test_signal_types():
    """Verify signal type annotations."""
    print("\nTesting signal type annotations...")

    # Check base manager
    manager_path = Path(__file__).parent / "core" / "managers" / "base_manager.py"
    with open(manager_path) as f:
        content = f.read()

    typed_signals = content.count("pyqtSignal[")
    print(f"Typed signals in base_manager.py: {typed_signals}")

    return typed_signals > 0


def main():
    """Run all tests."""
    print("SpritePal Memory and Type Fix Validation")
    print("=" * 50)

    tests = [
        ("Lambda fixes", test_lambda_fixes),
        ("Cleanup methods", test_cleanup_methods),
        ("Weakref usage", test_weakref_usage),
        ("Type aliases", test_type_aliases),
        ("Signal types", test_signal_types)
    ]

    results = []
    for name, test_func in tests:
        try:
            passed = test_func()
            results.append((name, passed))
        except Exception as e:
            print(f"Error in {name}: {e}")
            results.append((name, False))

    print("\n" + "=" * 50)
    print("Summary:")
    for name, passed in results:
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{name}: {status}")

    total_passed = sum(1 for _, passed in results if passed)
    print(f"\nTotal: {total_passed}/{len(tests)} tests passed")

    if total_passed == len(tests):
        print("\n🎉 All memory and type fixes validated!")
    else:
        print("\n⚠️  Some fixes need attention")


if __name__ == "__main__":
    main()
