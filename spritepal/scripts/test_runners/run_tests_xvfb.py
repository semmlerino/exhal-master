#!/usr/bin/env python3
from __future__ import annotations

"""
Robust test runner for SpritePal with automatic environment detection and configuration.
Handles GUI testing across different platforms using pytest-xvfb.
"""

import importlib.util
import os
import shutil
import subprocess
import sys

class TestRunner:
    """Manages test execution with proper environment setup."""

    def __init__(self):
        self.detect_environment()
        self.check_dependencies()

    def detect_environment(self):
        """Detect the current environment."""
        self.is_wsl = self._detect_wsl()
        self.is_ci = bool(os.environ.get("CI"))
        self.has_display = bool(os.environ.get("DISPLAY"))
        self.has_xvfb = shutil.which("Xvfb") is not None
        self.platform = sys.platform

        print("Environment Detection:")
        print(f"  Platform: {self.platform}")
        print(f"  WSL: {self.is_wsl}")
        print(f"  CI: {self.is_ci}")
        print(f"  Display: {self.has_display}")
        print(f"  Xvfb available: {self.has_xvfb}")
        print()

    def _detect_wsl(self):
        """Detect if running in WSL."""
        if sys.platform != "linux":
            return False
        try:
            with open("/proc/version") as f:
                return "microsoft" in f.read().lower()
        except OSError:
            return False

    def check_dependencies(self):
        """Check for required dependencies."""
        missing_python = []
        missing_system = []

        # Check Python packages
        if importlib.util.find_spec("pytest") is None:
            missing_python.append("pytest")

        if importlib.util.find_spec("pytestqt") is None:
            missing_python.append("pytest-qt")

        if importlib.util.find_spec("pytest_xvfb") is None:
            missing_python.append("pytest-xvfb")

        # Check system dependencies on Linux
        if sys.platform.startswith("linux"):
            if not self.has_xvfb and not self.has_display:
                missing_system.append("xvfb")

        if missing_python:
            print("Missing Python packages:")
            print(f"  pip install {' '.join(missing_python)}")
            print()

        if missing_system:
            print("Missing system packages:")
            if sys.platform.startswith("linux"):
                print("  sudo apt-get install xvfb libxkbcommon-x11-0")
            print()

        if missing_python or (missing_system and not self.has_display):
            print("Please install missing dependencies and try again.")
            sys.exit(1)

    def run_tests(self, args):
        """Run tests with appropriate configuration."""
        env = os.environ.copy()

        # Platform-specific configuration
        if sys.platform == "darwin":  # macOS
            # macOS doesn't have Xvfb, use offscreen for GUI tests
            if not any(arg.startswith("-m") for arg in args):
                print(
                    "Note: macOS doesn't support Xvfb. GUI tests will use offscreen backend."
                )
                env["QT_QPA_PLATFORM"] = "offscreen"

        elif sys.platform == "win32":  # Windows
            # Windows: Use offscreen for headless testing
            if not self.has_display:
                print(
                    "Note: Windows headless environment detected. GUI tests will use offscreen backend."
                )
                env["QT_QPA_PLATFORM"] = "offscreen"
                if not any(arg.startswith("-m") for arg in args):
                    # Skip GUI tests on Windows without display
                    args = ["-m", "not gui", *args]

        # Linux: pytest-xvfb will handle Xvfb automatically
        elif self.has_xvfb:
            print("Using pytest-xvfb for automatic virtual display management.")
        elif self.has_display:
            print("Using existing display.")
        else:
            print("Warning: No display and no Xvfb available. GUI tests may fail.")
            env["QT_QPA_PLATFORM"] = "offscreen"

        # Build command
        cmd = [sys.executable, "-m", "pytest", *args]

        print(f"Running: {' '.join(cmd)}")
        print()

        # Run tests
        return subprocess.run(cmd, check=False, env=env).returncode

def main():
    """Main entry point."""
    args = sys.argv[1:]

    # Handle help
    if "-h" in args or "--help" in args:
        print(__doc__)
        print()
        print("Usage: python run_tests_xvfb.py [pytest args]")
        print()
        print("Examples:")
        print("  python run_tests_xvfb.py                    # Run all tests")
        print("  python run_tests_xvfb.py -m 'not gui'       # Run non-GUI tests only")
        print("  python run_tests_xvfb.py tests/test_extractor.py  # Run specific test")
        print(
            "  python run_tests_xvfb.py -k test_palette    # Run tests matching pattern"
        )
        print("  python run_tests_xvfb.py --no-xvfb          # Disable Xvfb")
        print()
        print("Special options:")
        print("  --install-deps    Install system dependencies (Linux only)")
        print()
        return 0

    # Handle special options
    if "--install-deps" in args:
        if sys.platform.startswith("linux"):
            print("Installing system dependencies...")
            subprocess.run(
                [
                    "sudo",
                    "apt-get",
                    "install",
                    "-y",
                    "xvfb",
                    "libxkbcommon-x11-0",
                    "libxcb-icccm4",
                    "libxcb-image0",
                    "libxcb-keysyms1",
                    "libxcb-randr0",
                    "libxcb-render-util0",
                    "libxcb-xinerama0",
                    "libxcb-xfixes0",
                    "x11-utils",
                ],
                check=False,
            )
        else:
            print("System dependency installation is only supported on Linux.")
        return 0

    # Run tests
    runner = TestRunner()
    return runner.run_tests(args)

if __name__ == "__main__":
    sys.exit(main())
