#!/usr/bin/env python3
"""
Run tests in groups to avoid Qt application conflicts
This separates GUI tests from non-GUI tests for better stability
"""

import os
import subprocess
import sys


def run_command(cmd, description):
    """Run a command and report results"""
    print(f"\n{'='*60}")
    print(f"Running: {description}")
    print(f"Command: {' '.join(cmd)}")
    print("="*60)

    # Set Qt environment for all tests
    env = {
        **os.environ,
        "QT_QPA_PLATFORM": "offscreen",
        "QT_LOGGING_RULES": "*.debug=false",
        "QT_QUICK_BACKEND": "software"
    }

    result = subprocess.run(cmd, env=env, check=False)
    return result.returncode


def main():
    """Run tests in groups"""
    python = sys.executable
    failed_groups = []

    # Group 1: Unit tests (no Qt)
    print("\n\nGROUP 1: Unit tests (no Qt dependencies)")
    cmd = [python, "-m", "pytest", "-m", "unit", "--cov=sprite_editor", "--cov-append"]
    if run_command(cmd, "Unit tests") != 0:
        failed_groups.append("Unit tests")

    # Group 2: Integration tests without GUI
    print("\n\nGROUP 2: Integration tests (no GUI)")
    cmd = [python, "-m", "pytest", "-m", "integration and not gui", "--cov=sprite_editor", "--cov-append"]
    if run_command(cmd, "Integration tests without GUI") != 0:
        failed_groups.append("Integration tests")

    # Group 3: GUI tests (run separately)
    print("\n\nGROUP 3: GUI tests")
    cmd = [python, "-m", "pytest", "-m", "gui", "--cov=sprite_editor", "--cov-append"]
    if run_command(cmd, "GUI tests") != 0:
        failed_groups.append("GUI tests")

    # Group 4: Unmarked tests
    print("\n\nGROUP 4: Other tests (unmarked)")
    cmd = [python, "-m", "pytest", "-m", "not unit and not integration and not gui",
           "--cov=sprite_editor", "--cov-append"]
    if run_command(cmd, "Other tests") != 0:
        failed_groups.append("Other tests")

    # Final coverage report
    print("\n\nFINAL COVERAGE REPORT")
    print("="*60)
    subprocess.run([python, "-m", "coverage", "report"], check=False)

    # Summary
    print("\n\nTEST SUMMARY")
    print("="*60)
    if failed_groups:
        print(f"❌ Failed groups: {', '.join(failed_groups)}")
        return 1
    print("✅ All test groups passed!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
