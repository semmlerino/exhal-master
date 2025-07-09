#!/usr/bin/env python3
"""
Pytest-based test runner for Kirby Super Star Sprite Editor
Provides convenient test running with various options
"""

import argparse
import subprocess
import sys
from pathlib import Path


def run_pytest(args):
    """Run pytest with the given arguments"""
    import os

    # Set up environment for headless Qt testing
    env = os.environ.copy()
    # Always use offscreen in test environments to avoid display issues
    env["QT_QPA_PLATFORM"] = env.get("QT_QPA_PLATFORM", "offscreen")

    # Base pytest command
    cmd = [sys.executable, "-m", "pytest"]

    # Add arguments
    cmd.extend(args)

    # Run pytest
    result = subprocess.run(cmd, cwd=Path(__file__).parent, env=env, check=False)
    return result.returncode


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Run sprite editor tests with pytest",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run all tests
  python run_tests_pytest.py

  # Run with coverage report
  python run_tests_pytest.py --cov

  # Run only unit tests
  python run_tests_pytest.py -m unit

  # Run specific test file
  python run_tests_pytest.py sprite_editor/tests/test_project_management.py

  # Run specific test
  python run_tests_pytest.py -k test_new_project_creation

  # Run in parallel (requires pytest-xdist)
  python run_tests_pytest.py -n auto

  # Run with minimal output
  python run_tests_pytest.py -q

  # Stop on first failure
  python run_tests_pytest.py -x
"""
    )

    # Common options
    parser.add_argument("tests", nargs="*", help="Specific tests to run")
    parser.add_argument("-m", "--mark", help="Run tests matching given mark (e.g., unit, integration, gui)")
    parser.add_argument("-k", "--keyword", help="Run tests matching given keyword expression")
    parser.add_argument("-x", "--exitfirst", action="store_true", help="Exit on first failure")
    parser.add_argument("-v", "--verbose", action="store_true", help="Increase verbosity")
    parser.add_argument("-q", "--quiet", action="store_true", help="Decrease verbosity")
    parser.add_argument("-s", "--capture", action="store_true", help="Disable output capturing")
    parser.add_argument("--pdb", action="store_true", help="Drop into debugger on failures")

    # Coverage options
    parser.add_argument("--cov", action="store_true", help="Run with coverage report")
    parser.add_argument("--cov-html", action="store_true", help="Generate HTML coverage report")

    # Performance options
    parser.add_argument("-n", "--numprocesses", help="Number of processes for parallel testing")
    parser.add_argument("--durations", type=int, metavar="N", help="Show N slowest test durations")

    # GUI test options
    parser.add_argument("--no-qt-log", action="store_true", help="Disable Qt logging")
    parser.add_argument("--headed", action="store_true", help="Run GUI tests with visible windows")

    args = parser.parse_args()

    # Build pytest arguments
    pytest_args = []

    # Add test paths
    if args.tests:
        pytest_args.extend(args.tests)

    # Add markers
    if args.mark:
        pytest_args.extend(["-m", args.mark])

    # Add keyword filter
    if args.keyword:
        pytest_args.extend(["-k", args.keyword])

    # Add flags
    if args.exitfirst:
        pytest_args.append("-x")

    if args.verbose:
        pytest_args.append("-vv")
    elif args.quiet:
        pytest_args.append("-q")

    if args.capture:
        pytest_args.append("-s")

    if args.pdb:
        pytest_args.append("--pdb")

    # Coverage options
    if args.cov:
        # These are already in pytest.ini, but we can override
        pass
    elif args.cov_html:
        pytest_args.extend(["--cov-report=html", "--cov-report="])
    else:
        # Disable coverage if not requested
        pytest_args.extend(["--no-cov"])

    # Parallel testing
    if args.numprocesses:
        pytest_args.extend(["-n", args.numprocesses])

    # Show slowest tests
    if args.durations:
        pytest_args.extend([f"--durations={args.durations}"])

    # Qt options
    if args.no_qt_log:
        pytest_args.append("--no-qt-log")

    if args.headed:
        # For GUI tests to show windows
        import os
        os.environ["QT_QPA_PLATFORM"] = "xcb"

    # Run pytest
    return run_pytest(pytest_args)


if __name__ == "__main__":
    sys.exit(main())
