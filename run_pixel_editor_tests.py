#!/usr/bin/env python3
"""
Run all pixel editor tests with coverage reporting
"""

import os
import subprocess
import sys


def run_tests():
    """Run the test suite with coverage"""

    print("Running Pixel Editor Test Suite with Coverage...")
    print("=" * 60)

    # Set environment variable for Qt platform
    env = os.environ.copy()
    env["QT_QPA_PLATFORM"] = "offscreen"

    # Run tests with coverage
    cmd = [
        sys.executable, "-m", "pytest",
        "test_indexed_pixel_editor.py",
        "test_indexed_pixel_editor_enhanced.py",
        "-v",
        "--tb=short",
        "--cov=indexed_pixel_editor",
        "--cov=pixel_editor_widgets",
        "--cov-report=term-missing",
        "--cov-report=html:htmlcov_pixel_editor",
        "-x"  # Stop on first failure
    ]

    try:
        result = subprocess.run(cmd, env=env, check=False)

        print("\n" + "=" * 60)
        if result.returncode == 0:
            print("✅ All tests passed!")
            print("\nCoverage report generated in htmlcov_pixel_editor/")
            print("Open htmlcov_pixel_editor/index.html to view detailed coverage")
        else:
            print("❌ Some tests failed!")
            sys.exit(1)

    except Exception as e:
        print(f"Error running tests: {e}")
        sys.exit(1)


if __name__ == "__main__":
    run_tests()
