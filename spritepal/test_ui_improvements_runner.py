#!/usr/bin/env python3
"""
Test runner for SpritePal UI improvements integration tests.

This script runs the comprehensive Qt integration tests for recent UI improvements,
handling both headless and GUI testing scenarios appropriately.

Usage:
    python3 test_ui_improvements_runner.py [--gui] [--headless] [--all]
    
Options:
    --gui       Run GUI tests (requires display/xvfb)
    --headless  Run headless tests only
    --all       Run all tests (default)
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path


def is_display_available() -> bool:
    """Check if display is available for GUI testing."""
    return bool(os.environ.get("DISPLAY"))


def run_headless_tests() -> int:
    """Run headless regression tests."""
    print("Running headless UI improvement tests...")
    
    cmd = [
        sys.executable, "-m", "pytest",
        "tests/test_recent_ui_improvements_integration.py::TestRegressionPrevention",
        "-v", "--tb=short", "-m", "not gui"
    ]
    
    return subprocess.run(cmd).returncode


def run_gui_tests() -> int:
    """Run GUI integration tests."""
    if not is_display_available():
        print("No display available. Attempting to run with xvfb...")
        # Try to use xvfb-run if available
        try:
            subprocess.run(["which", "xvfb-run"], check=True, capture_output=True)
            print("Using xvfb-run for GUI tests...")
            cmd = [
                "xvfb-run", "-a", "-s", "-screen 0 1920x1200x24",
                sys.executable, "-m", "pytest",
                "tests/test_recent_ui_improvements_integration.py",
                "-v", "--tb=short", "-m", "gui"
            ]
        except (subprocess.CalledProcessError, FileNotFoundError):
            print("xvfb-run not available. Skipping GUI tests.")
            return 0
    else:
        print("Running GUI tests with available display...")
        cmd = [
            sys.executable, "-m", "pytest",
            "tests/test_recent_ui_improvements_integration.py",
            "-v", "--tb=short", "-m", "gui"
        ]
    
    return subprocess.run(cmd).returncode


def run_validation_test() -> int:
    """Run a simple validation test to ensure the test file is working."""
    print("Validating test infrastructure...")
    
    validation_code = '''
import sys
sys.path.insert(0, ".")

try:
    # Test basic imports
    from tests.test_recent_ui_improvements_integration import TestRegressionPrevention
    from ui.styles.theme import COLORS, get_theme_style
    from ui.main_window import MAIN_WINDOW_MIN_SIZE
    
    # Test basic functionality
    test_instance = TestRegressionPrevention()
    
    # Test window size constant
    assert MAIN_WINDOW_MIN_SIZE == (1000, 650), f"Window size should be (1000, 650), got {MAIN_WINDOW_MIN_SIZE}"
    
    # Test theme colors
    assert COLORS['background'] == '#2d2d30', f"Background should be #2d2d30, got {COLORS['background']}"
    assert COLORS['preview_background'] == '#1e1e1e', f"Preview background should be #1e1e1e, got {COLORS['preview_background']}"
    
    # Test theme CSS generation
    theme_css = get_theme_style()
    assert isinstance(theme_css, str), "Theme CSS should be a string"
    assert len(theme_css) > 0, "Theme CSS should not be empty"
    assert COLORS['background'] in theme_css, "Theme CSS should contain background color"
    
    print("✓ Basic validation passed - test infrastructure is working")
    print("✓ Window size constants are correct (1000x650)")  
    print("✓ Dark theme colors are correct (#2d2d30, #1e1e1e)")
    print("✓ Theme CSS generation is working")
    
except Exception as e:
    print(f"✗ Validation failed: {e}")
    sys.exit(1)
'''
    
    result = subprocess.run([sys.executable, "-c", validation_code], capture_output=True, text=True)
    if result.returncode == 0:
        print(result.stdout)
    else:
        print("Validation failed:")
        print(result.stderr)
    
    return result.returncode


def main():
    """Main test runner function."""
    parser = argparse.ArgumentParser(description="Run SpritePal UI improvements integration tests")
    parser.add_argument("--gui", action="store_true", help="Run GUI tests")
    parser.add_argument("--headless", action="store_true", help="Run headless tests only")  
    parser.add_argument("--all", action="store_true", help="Run all tests")
    parser.add_argument("--validate", action="store_true", help="Run validation test only")
    
    args = parser.parse_args()
    
    # Default to validation if no specific option is chosen
    if not any([args.gui, args.headless, args.all, args.validate]):
        args.validate = True
    
    total_return_code = 0
    
    if args.validate:
        print("=== SpritePal UI Improvements Test Validation ===")
        return_code = run_validation_test()
        total_return_code += return_code
        return total_return_code
    
    if args.headless or args.all:
        print("\n=== Running Headless UI Improvement Tests ===")
        return_code = run_headless_tests()
        total_return_code += return_code
    
    if args.gui or args.all:
        print("\n=== Running GUI Integration Tests ===")
        return_code = run_gui_tests()
        total_return_code += return_code
    
    if total_return_code == 0:
        print("\n✓ All requested tests completed successfully!")
    else:
        print(f"\n✗ Some tests failed (return code: {total_return_code})")
    
    return total_return_code


if __name__ == "__main__":
    sys.exit(main())