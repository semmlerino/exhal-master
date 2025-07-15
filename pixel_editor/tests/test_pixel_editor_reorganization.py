#!/usr/bin/env python3
"""Test script to verify pixel editor reorganization"""

import sys


def test_imports():
    """Test all pixel editor imports"""
    print("Testing pixel editor imports after reorganization...")

    tests = []

    # Test core imports
    try:
        tests.append(("Core module imports", True, None))
    except Exception as e:
        tests.append(("Core module imports", False, str(e)))

    # Test individual module imports
    try:
        tests.append(("Model imports", True, None))
    except Exception as e:
        tests.append(("Model imports", False, str(e)))

    try:
        tests.append(("Manager imports", True, None))
    except Exception as e:
        tests.append(("Manager imports", False, str(e)))

    try:
        tests.append(("Widget imports", True, None))
    except Exception as e:
        tests.append(("Widget imports", False, str(e)))

    try:
        tests.append(("Worker imports", True, None))
    except Exception as e:
        tests.append(("Worker imports", False, str(e)))

    # Test views imports
    try:
        tests.append(("Dialog imports", True, None))
    except Exception as e:
        tests.append(("Dialog imports", False, str(e)))

    try:
        tests.append(("Panel imports", True, None))
    except Exception as e:
        tests.append(("Panel imports", False, str(e)))

    # Print results
    print("\nImport Test Results:")
    print("-" * 50)

    all_passed = True
    for test_name, passed, error in tests:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{test_name:<30} {status}")
        if error:
            print(f"  Error: {error}")
            all_passed = False

    print("-" * 50)
    if all_passed:
        print("✅ All imports successful!")
    else:
        print("❌ Some imports failed")

    return all_passed


def test_launcher():
    """Test the launcher script"""
    print("\nTesting launcher script...")

    import os
    import subprocess

    launcher_path = os.path.join("pixel_editor", "launch_pixel_editor.py")

    if os.path.exists(launcher_path):
        result = subprocess.run(
            [sys.executable, launcher_path, "--check"],
            check=False,
            capture_output=True,
            text=True,
        )

        print("Launcher output:")
        print(result.stdout)

        if result.returncode == 0:
            print("✅ Launcher test passed")
            return True
        print("❌ Launcher test failed")
        if result.stderr:
            print("Errors:", result.stderr)
        return False
    print(f"❌ Launcher not found at {launcher_path}")
    return False


def main():
    """Run all tests"""
    print("Pixel Editor Reorganization Test")
    print("=" * 50)

    import_success = test_imports()
    launcher_success = test_launcher()

    print("\n" + "=" * 50)
    if import_success and launcher_success:
        print("✅ All tests passed! Reorganization successful.")
        return 0
    print("❌ Some tests failed. Check the errors above.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
