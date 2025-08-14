"""
Comprehensive environment detection for SpritePal test suite.

This module provides centralized environment detection and test control
decorators to ensure tests only run in appropriate execution contexts.
Prevents segfaults by detecting headless environments and configuring
Qt properly.

Environment Detection:
- CI/CD systems (GitHub Actions, Jenkins, GitLab CI, etc.)
- Headless environments (no display available)
- WSL/WSL2 environments
- Docker containers
- Local environments with display
- xvfb availability

Skip Decorators:
- @skip_if_no_display: Skip tests requiring display
- @skip_in_ci: Skip tests that shouldn't run in CI
- @requires_display: Explicitly require display
- @headless_safe: Mark tests safe for headless
- @ci_safe: Mark tests safe for CI environments
- @requires_real_qt: Skip if Qt mocking is active

Usage:
    from tests.infrastructure.environment_detection import (
        skip_if_no_display,
        requires_display,
        get_environment_report
    )

    @skip_if_no_display
    def test_gui_functionality():
        pass

    @requires_display
    def test_widget_rendering():
        pass
"""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable

import pytest


class EnvironmentInfo:
    """Container for comprehensive environment information."""

    def __init__(self) -> None:
        # Basic platform info
        self.platform = sys.platform
        self.python_version = sys.version
        self.architecture = platform.machine()

        # Qt detection first (needed by other checks)
        self.pyside6_available = self._detect_pyside6()
        self.qt_info = self._gather_qt_info()

        # Environment detection
        self.is_ci = self._detect_ci()
        self.is_wsl = self._detect_wsl()
        self.is_docker = self._detect_docker()
        self.has_display = self._detect_display()
        self.xvfb_available = self._detect_xvfb()

        # Headless detection depends on Qt and other environment info
        self.is_headless = self._detect_headless()

        # CI system identification
        self.ci_system = self._identify_ci_system()

        # Recommended configuration
        self.recommended_qt_platform = self._recommend_qt_platform()
        self.should_use_xvfb = self._should_use_xvfb()

    def _detect_ci(self) -> bool:
        """Detect if running in any CI environment."""
        ci_indicators = [
            'CI', 'CONTINUOUS_INTEGRATION', 'BUILD_NUMBER',
            'GITHUB_ACTIONS', 'GITLAB_CI', 'JENKINS_URL',
            'TRAVIS', 'CIRCLECI', 'APPVEYOR', 'BUILDKITE',
            'AZURE_HTTP_USER_AGENT', 'TF_BUILD'
        ]
        return any(os.environ.get(var) for var in ci_indicators)

    def _detect_headless(self) -> bool:
        """Detect headless environment with comprehensive checks."""
        # Explicit headless indicators
        if os.environ.get('HEADLESS') == '1':
            return True

        if os.environ.get('QT_QPA_PLATFORM') == 'offscreen':
            return True

        # CI environments are typically headless
        if self.is_ci:
            return True

        # No display on Unix-like systems
        if sys.platform.startswith(('linux', 'darwin')) and not os.environ.get('DISPLAY'):
            return True

        # Try Qt detection if available
        if self.pyside6_available:
            try:
                from PySide6.QtWidgets import QApplication
                app = QApplication.instance() or QApplication([])
                if not app.primaryScreen():
                    return True
            except Exception:
                return True

        return False

    def _detect_wsl(self) -> bool:
        """Detect Windows Subsystem for Linux."""
        if sys.platform != 'linux':
            return False

        try:
            # Check uname for Microsoft kernel
            uname = os.uname().release.lower()
            if 'microsoft' in uname or 'wsl' in uname:
                return True

            # Check /proc/version for WSL indicators
            if Path('/proc/version').exists():
                version = Path('/proc/version').read_text().lower()
                return 'microsoft' in version or 'wsl' in version

        except (OSError, AttributeError):
            pass

        return False

    def _detect_docker(self) -> bool:
        """Detect Docker container environment."""
        # Check for .dockerenv file
        if Path('/.dockerenv').exists():
            return True

        # Check cgroup for docker
        try:
            if Path('/proc/1/cgroup').exists():
                cgroup = Path('/proc/1/cgroup').read_text()
                if 'docker' in cgroup or 'containerd' in cgroup:
                    return True
        except (OSError, PermissionError):
            pass

        # Check environment variables
        return bool(os.environ.get('DOCKER_CONTAINER'))

    def _detect_display(self) -> bool:
        """Detect if display is available."""
        # Windows always has display available to apps
        if sys.platform == 'win32':
            return True

        # Check DISPLAY environment variable
        if not os.environ.get('DISPLAY'):
            return False

        # Try to connect to display on Unix
        if sys.platform.startswith('linux'):
            try:
                # Try xdpyinfo if available
                result = subprocess.run(
                    ['xdpyinfo'],
                    check=False, capture_output=True,
                    timeout=5
                )
                return result.returncode == 0
            except (subprocess.SubprocessError, FileNotFoundError):
                # Fallback: assume DISPLAY variable is valid
                return True

        return True

    def _detect_xvfb(self) -> bool:
        """Detect if xvfb is available for headless testing."""
        return shutil.which('Xvfb') is not None

    def _identify_ci_system(self) -> str | None:
        """Identify specific CI system."""
        ci_systems = {
            'GITHUB_ACTIONS': 'GitHub Actions',
            'GITLAB_CI': 'GitLab CI',
            'JENKINS_URL': 'Jenkins',
            'TRAVIS': 'Travis CI',
            'CIRCLECI': 'CircleCI',
            'APPVEYOR': 'AppVeyor',
            'BUILDKITE': 'Buildkite',
            'TF_BUILD': 'Azure DevOps'
        }

        for env_var, system_name in ci_systems.items():
            if os.environ.get(env_var):
                return system_name

        return 'Unknown CI' if self.is_ci else None

    def _detect_pyside6(self) -> bool:
        """Check if PySide6 is available."""
        try:
            import PySide6.QtCore  # noqa: F401
            return True
        except ImportError:
            return False

    def _gather_qt_info(self) -> dict[str, Any]:
        """Gather Qt-specific information."""
        info = {
            'available': self.pyside6_available,
            'version': None,
            'platform_plugin': os.environ.get('QT_QPA_PLATFORM'),
            'app_exists': False,
            'primary_screen_available': False,
        }

        if not self.pyside6_available:
            return info

        try:
            from PySide6.QtWidgets import QApplication

            # Try to get Qt version - different ways in different PySide6 versions
            try:
                from PySide6.QtCore import QT_VERSION_STR
                info['version'] = QT_VERSION_STR
            except ImportError:
                try:
                    from PySide6 import QtCore
                    info['version'] = getattr(QtCore, 'qVersion', lambda: 'Unknown')()
                except Exception:
                    info['version'] = 'Unknown'

            app = QApplication.instance()
            if app:
                info['app_exists'] = True
                info['primary_screen_available'] = bool(app.primaryScreen())
                if hasattr(app, 'platformName'):
                    info['platform_name'] = app.platformName()

        except Exception as e:
            info['qt_detection_error'] = str(e)

        return info

    def _recommend_qt_platform(self) -> str | None:
        """Recommend Qt platform plugin based on environment."""
        if not self.pyside6_available:
            return None

        if self.is_headless or not self.has_display:
            return 'offscreen'

        if self.is_ci and not self.xvfb_available:
            return 'offscreen'

        if sys.platform == 'linux' and self.has_display:
            return 'xcb'

        return None  # Use Qt default

    def _should_use_xvfb(self) -> bool:
        """Determine if xvfb should be used for GUI tests."""
        return (
            self.is_headless and
            self.xvfb_available and
            sys.platform.startswith('linux') and
            not self.is_docker  # Docker might have limitations
        )


# Global environment instance
_environment_info: EnvironmentInfo | None = None


def get_environment_info() -> EnvironmentInfo:
    """Get cached environment information."""
    global _environment_info
    if _environment_info is None:
        _environment_info = EnvironmentInfo()
    return _environment_info


# Convenience functions for common checks
def is_headless_environment() -> bool:
    """Check if running in headless environment."""
    return get_environment_info().is_headless


def is_ci_environment() -> bool:
    """Check if running in CI environment."""
    return get_environment_info().is_ci


def is_wsl_environment() -> bool:
    """Check if running in WSL environment."""
    return get_environment_info().is_wsl


def is_docker_environment() -> bool:
    """Check if running in Docker container."""
    return get_environment_info().is_docker


def has_display_available() -> bool:
    """Check if display is available for GUI tests."""
    return get_environment_info().has_display


def is_xvfb_available() -> bool:
    """Check if xvfb is available for virtual display."""
    return get_environment_info().xvfb_available


def get_recommended_qt_platform() -> str | None:
    """Get recommended Qt platform plugin."""
    return get_environment_info().recommended_qt_platform


# Skip decorators for test control
def skip_if_no_display(reason: str = "Test requires display but none available") -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Skip test if no display is available."""
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        return pytest.mark.skipif(
            not has_display_available(),
            reason=reason
        )(func)
    return decorator


def skip_in_ci(reason: str = "Test should not run in CI environment") -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Skip test when running in CI environment."""
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        return pytest.mark.skipif(
            is_ci_environment(),
            reason=reason
        )(func)
    return decorator


def requires_display(func: Callable[..., Any]) -> Callable[..., Any]:
    """Require display for test - skip if headless."""
    return pytest.mark.skipif(
        is_headless_environment(),
        reason="Test requires display but running in headless environment"
    )(func)


def headless_safe(func: Callable[..., Any]) -> Callable[..., Any]:
    """Mark test as safe for headless environments.

    This is primarily for documentation purposes.
    """
    return pytest.mark.headless(func)


def ci_safe(func: Callable[..., Any]) -> Callable[..., Any]:
    """Mark test as safe for CI environments.

    This is primarily for documentation purposes.
    """
    return pytest.mark.ci_safe(func)


def requires_real_qt(func: Callable[..., Any]) -> Callable[..., Any]:
    """Require real Qt components - skip if mocked."""
    return pytest.mark.skipif(
        is_headless_environment() and not is_xvfb_available(),
        reason="Test requires real Qt but running headless without xvfb"
    )(func)


def skip_if_wsl(reason: str = "Test has known issues on WSL") -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Skip test if running on WSL."""
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        return pytest.mark.skipif(
            is_wsl_environment(),
            reason=reason
        )(func)
    return decorator


def skip_if_docker(reason: str = "Test has known issues in Docker") -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Skip test if running in Docker container."""
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        return pytest.mark.skipif(
            is_docker_environment(),
            reason=reason
        )(func)
    return decorator


# Configuration helpers
def configure_qt_for_environment() -> None:
    """Configure Qt environment variables based on detected environment."""
    env_info = get_environment_info()

    if not env_info.pyside6_available:
        return

    recommended_platform = env_info.recommended_qt_platform
    if recommended_platform and not os.environ.get('QT_QPA_PLATFORM'):
        os.environ['QT_QPA_PLATFORM'] = recommended_platform

    # Set other Qt environment variables for headless testing
    if env_info.is_headless:
        os.environ.setdefault('QT_LOGGING_RULES', '*.debug=false')
        os.environ.setdefault('QT_QPA_FONTDIR', '/usr/share/fonts')


def get_environment_report() -> str:
    """Generate comprehensive environment report for debugging."""
    env_info = get_environment_info()

    lines = [
        "\n=== SpritePal Test Environment Report ===",
        f"Platform: {env_info.platform} ({env_info.architecture})",
        f"Python: {env_info.python_version.split()[0]}",
        "",
        "Environment Detection:",
        f"  Headless: {'Yes' if env_info.is_headless else 'No'}",
        f"  CI: {'Yes' if env_info.is_ci else 'No'} ({env_info.ci_system or 'N/A'})",
        f"  WSL: {'Yes' if env_info.is_wsl else 'No'}",
        f"  Docker: {'Yes' if env_info.is_docker else 'No'}",
        f"  Display Available: {'Yes' if env_info.has_display else 'No'}",
        f"  xvfb Available: {'Yes' if env_info.xvfb_available else 'No'}",
        "",
        "Qt Configuration:",
        f"  PySide6 Available: {'Yes' if env_info.pyside6_available else 'No'}",
    ]

    if env_info.pyside6_available:
        qt_info = env_info.qt_info
        lines.extend([
            f"  Qt Version: {qt_info.get('version', 'Unknown')}",
            f"  Platform Plugin: {qt_info.get('platform_plugin') or 'Default'}",
            f"  Recommended Plugin: {env_info.recommended_qt_platform or 'Default'}",
            f"  QApplication Exists: {'Yes' if qt_info.get('app_exists') else 'No'}",
            f"  Primary Screen: {'Yes' if qt_info.get('primary_screen_available') else 'No'}",
        ])

        if 'qt_detection_error' in qt_info:
            lines.append(f"  Detection Error: {qt_info['qt_detection_error']}")

    lines.extend([
        "",
        "Test Configuration:",
        f"  Should use xvfb: {'Yes' if env_info.should_use_xvfb else 'No'}",
        f"  GUI tests will be: {'Skipped' if env_info.is_headless and not env_info.xvfb_available else 'Run'}",
        "=========================================\n",
    ])

    return "\n".join(lines)


def print_environment_report() -> None:
    """Print environment report to stdout."""
    print(get_environment_report())


# Legacy compatibility functions
def is_pyside6_available() -> bool:
    """Legacy compatibility function."""
    return get_environment_info().pyside6_available


class HeadlessModeError(RuntimeError):
    """Raised when Qt functionality is accessed in headless mode."""

    def __init__(self, feature: str) -> None:
        super().__init__(
            f"Qt feature '{feature}' is not available in headless mode. "
            f"Install PySide6 and ensure a display is available, or use "
            f"non-Qt testing functionality."
        )


def require_qt(feature: str) -> None:
    """Raise an error if Qt is not available.

    Args:
        feature: Name of the Qt feature being accessed

    Raises:
        HeadlessModeError: If Qt is not available
    """
    env_info = get_environment_info()
    if not env_info.pyside6_available or (env_info.is_headless and not env_info.xvfb_available):
        raise HeadlessModeError(feature)
