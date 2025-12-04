#!/usr/bin/env python3
from __future__ import annotations

"""
Safe test runner for SpritePal that handles Qt testing in various environments.
Automatically detects and configures the best testing strategy.
"""

import os
import shutil
import subprocess
import sys


class TestEnvironment:
    """Detect and configure test environment"""

    def __init__(self):
        self.is_wsl = self._detect_wsl()
        self.is_ci = bool(os.environ.get("CI"))
        self.has_display = bool(os.environ.get("DISPLAY"))
        self.has_xvfb = shutil.which("xvfb-run") is not None
        self.qt_platform = os.environ.get("QT_QPA_PLATFORM", "")

    def _detect_wsl(self):
        """Detect if running in WSL"""
        if sys.platform != "linux":
            return False
        try:
            with open("/proc/version") as f:
                return "microsoft" in f.read().lower()
        except OSError:
            return False

    def get_strategy(self):
        """Determine best testing strategy"""
        if self.has_display and not self.is_ci:
            return "native"
        if self.has_xvfb:
            return "xvfb"
        return "offscreen"

    def __str__(self):
        return (
            f"TestEnvironment(\n"
            f"  WSL: {self.is_wsl}\n"
            f"  CI: {self.is_ci}\n"
            f"  Display: {self.has_display}\n"
            f"  Xvfb: {self.has_xvfb}\n"
            f"  Qt Platform: {self.qt_platform or 'not set'}\n"
            f"  Strategy: {self.get_strategy()}\n"
            f")"
        )

def run_tests_native(args):
    """Run tests with native display"""
    print("Running tests with native display...")
    env = os.environ.copy()
    # Don't override QT_QPA_PLATFORM if display is available
    if "QT_QPA_PLATFORM" in env:
        del env["QT_QPA_PLATFORM"]

    cmd = [sys.executable, "-m", "pytest", *args]
    return subprocess.run(cmd, check=False, env=env).returncode

def run_tests_xvfb(args):
    """Run tests with Xvfb virtual display"""
    print("Running tests with Xvfb virtual display...")

    # Configure Xvfb
    xvfb_args = [
        "xvfb-run",
        "-a",  # Auto-select display number
        "--server-args",
        "-screen 0 1280x1024x24",
    ]

    env = os.environ.copy()
    # Ensure Qt uses xcb platform with Xvfb
    env["QT_QPA_PLATFORM"] = "xcb"

    cmd = [*xvfb_args, sys.executable, "-m", "pytest", *args]
    return subprocess.run(cmd, check=False, env=env).returncode

def run_tests_offscreen(args):
    """Run tests with Qt offscreen platform"""
    print("Running tests with Qt offscreen platform...")
    print("WARNING: GUI tests will be skipped in offscreen mode")

    env = os.environ.copy()
    env["QT_QPA_PLATFORM"] = "offscreen"
    env["QT_QUICK_BACKEND"] = "software"
    env["QT_LOGGING_RULES"] = "*.debug=false"

    # Add marker to skip GUI tests
    if "-m" not in args:
        args = ["-m", "not gui", *args]

    cmd = [sys.executable, "-m", "pytest", *args]
    return subprocess.run(cmd, check=False, env=env).returncode

def install_xvfb_instructions():
    """Print instructions for installing Xvfb"""
    print("\nXvfb not found but recommended for GUI testing in headless environments.")
    print("To install Xvfb:")
    print("  Ubuntu/Debian: sudo apt-get install xvfb")
    print("  RHEL/CentOS:   sudo yum install xorg-x11-server-Xvfb")
    print("  Arch:          sudo pacman -S xorg-server-xvfb")
    print("\nAlternatively, you can run non-GUI tests only with:")
    print("  python run_tests_safe.py -m 'not gui'")

def main():
    """Main entry point"""
    args = sys.argv[1:]

    # Detect environment
    env = TestEnvironment()
    print(env)

    # Special handling for explicit strategies
    if "--native" in args:
        args.remove("--native")
        return run_tests_native(args)
    if "--xvfb" in args:
        args.remove("--xvfb")
        if not env.has_xvfb:
            print("ERROR: Xvfb not available")
            install_xvfb_instructions()
            return 1
        return run_tests_xvfb(args)
    if "--offscreen" in args:
        args.remove("--offscreen")
        return run_tests_offscreen(args)

    # Auto-select strategy
    strategy = env.get_strategy()

    if strategy == "native":
        return run_tests_native(args)
    if strategy == "xvfb":
        return run_tests_xvfb(args)
    # In headless without Xvfb, provide helpful message
    if not env.has_xvfb and "-m" not in args and "not gui" not in " ".join(args):
        print("\n" + "=" * 60)
        print("HEADLESS ENVIRONMENT DETECTED")
        print("=" * 60)
        install_xvfb_instructions()
        print("=" * 60 + "\n")
    return run_tests_offscreen(args)

if __name__ == "__main__":
    sys.exit(main())
