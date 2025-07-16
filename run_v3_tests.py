#!/usr/bin/env python3
"""
Test runner for V3 pixel editor components
Runs all unit tests and generates coverage report
"""

import subprocess
import sys


def run_tests():
    """Run all V3 tests with coverage"""

    test_files = [
        "pixel_editor/tests/test_pixel_editor_models.py",
        "pixel_editor/tests/test_pixel_editor_managers.py",
        "pixel_editor/tests/test_pixel_editor_controller_v3.py",
        "pixel_editor/tests/test_pixel_editor_canvas_v3.py",
    ]

    # Source files to measure coverage for
    source_files = [
        "pixel_editor/core/pixel_editor_models.py",
        "pixel_editor/core/pixel_editor_managers.py",
        "pixel_editor/core/pixel_editor_controller_v3.py",
        "pixel_editor/core/pixel_editor_canvas_v3.py",
        "pixel_editor/core/pixel_editor_utils.py",
        "pixel_editor/core/pixel_editor_workers.py",
        "pixel_editor/core/pixel_editor_settings_adapter.py",
    ]

    # Build coverage command
    cmd = [
        "python",
        "-m",
        "pytest",
        "-v",  # Verbose
        "--tb=short",  # Short traceback
        "--cov=" + ",".join(source_files),  # Coverage for source files
        "--cov-report=term-missing",  # Show missing lines
        "--cov-report=html:htmlcov_v3",  # HTML report
        "--cov-report=xml:coverage_v3.xml",  # XML report
    ] + test_files

    print("Running V3 component tests...")
    print(f"Command: {' '.join(cmd)}")
    print("-" * 80)

    try:
        result = subprocess.run(cmd, check=False)

        if result.returncode == 0:
            print("\n" + "=" * 80)
            print("✅ All tests passed!")
            print("📊 Coverage report: htmlcov_v3/index.html")
        else:
            print("\n" + "=" * 80)
            print("❌ Some tests failed!")
            sys.exit(1)

    except FileNotFoundError:
        print("❌ Error: pytest not found. Install with: pip install pytest pytest-cov")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error running tests: {e}")
        sys.exit(1)


def run_specific_test(test_name):
    """Run a specific test file or test case"""
    cmd = ["python", "-m", "pytest", "-v", "--tb=short", test_name]

    print(f"Running specific test: {test_name}")
    print("-" * 80)

    subprocess.run(cmd, check=False)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        # Run specific test
        run_specific_test(sys.argv[1])
    else:
        # Run all tests
        run_tests()
