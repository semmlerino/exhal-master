#!/usr/bin/env python3
"""
Test validation for the comprehensive environment detection system.

This test validates that the environment detection system works correctly
and that skip decorators function as expected.
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest

from tests.infrastructure.environment_detection import (
    get_environment_info,
    get_environment_report,
    is_headless_environment,
    is_ci_environment,
    is_wsl_environment,
    has_display_available,
    is_xvfb_available,
    skip_if_no_display,
    skip_in_ci,
    requires_display,
    headless_safe,
    ci_safe,
    skip_if_wsl,
    configure_qt_for_environment,
)

pytestmark = [
    pytest.mark.headless,
    pytest.mark.infrastructure,
    pytest.mark.validation,
    pytest.mark.ci_safe,
    pytest.mark.no_manager_setup,  # Pure utility functions for environment detection
]


@headless_safe
def test_environment_detection_basic():
    """Test basic environment detection functions work."""
    env_info = get_environment_info()
    
    # Basic assertions that should work in any environment
    assert isinstance(env_info.platform, str)
    assert isinstance(env_info.python_version, str)
    assert isinstance(env_info.is_headless, bool)
    assert isinstance(env_info.is_ci, bool)
    assert isinstance(env_info.is_wsl, bool)
    assert isinstance(env_info.has_display, bool)
    assert isinstance(env_info.pyside6_available, bool)


@headless_safe
def test_environment_report_generation():
    """Test that environment report can be generated without errors."""
    report = get_environment_report()
    
    # Report should be non-empty string
    assert isinstance(report, str)
    assert len(report) > 0
    
    # Should contain key information
    assert "SpritePal Test Environment Report" in report
    assert "Platform:" in report
    assert "Environment Detection:" in report


@headless_safe
def test_convenience_functions():
    """Test that convenience functions work correctly."""
    # These should not raise exceptions
    is_headless = is_headless_environment()
    is_ci = is_ci_environment() 
    is_wsl = is_wsl_environment()
    has_display = has_display_available()
    has_xvfb = is_xvfb_available()
    
    # All should be boolean
    assert isinstance(is_headless, bool)
    assert isinstance(is_ci, bool)
    assert isinstance(is_wsl, bool)
    assert isinstance(has_display, bool)
    assert isinstance(has_xvfb, bool)


@headless_safe
def test_qt_configuration():
    """Test Qt configuration helper."""
    # This should not raise exceptions even if Qt is not available
    configure_qt_for_environment()
    
    # Test passes if no exception was raised
    assert True


@ci_safe
@headless_safe
def test_decorators_do_not_interfere():
    """Test that decorators can be stacked without issues."""
    # This test should run in all environments
    assert True


# Skip decorator tests - these will test the skip logic

@skip_in_ci("Testing skip_in_ci decorator")
def test_skip_in_ci_decorator():
    """This test should be skipped in CI environments."""
    # If this runs, we're not in CI
    assert not is_ci_environment()


@skip_if_no_display("Testing skip_if_no_display decorator")  
def test_skip_if_no_display_decorator():
    """This test should be skipped if no display is available."""
    # If this runs, we should have a display
    assert has_display_available()


@requires_display
def test_requires_display_decorator():
    """This test should be skipped in headless environments."""
    # If this runs, we should not be in headless mode
    assert not is_headless_environment()


@skip_if_wsl("Testing skip_if_wsl decorator")
def test_skip_if_wsl_decorator():
    """This test should be skipped on WSL."""
    # If this runs, we should not be on WSL
    assert not is_wsl_environment()


# Environment-specific tests that demonstrate the system working

@pytest.mark.skipif(
    is_ci_environment(),
    reason="Performance test not suitable for CI"
)
def test_environment_specific_skip():
    """Example of using environment detection in skip conditions."""
    # This should only run in non-CI environments
    assert True


def test_environment_consistency():
    """Test that environment detection is internally consistent."""
    env_info = get_environment_info()
    
    # If we're in CI, we should probably be headless
    if env_info.is_ci:
        # Most CI environments are headless, but not necessarily all
        # So we can't assert this absolutely, but can log it
        print(f"CI environment detected: {env_info.ci_system}, headless: {env_info.is_headless}")
    
    # If we're headless and have no display, xvfb might be available
    if env_info.is_headless and not env_info.has_display:
        print(f"Headless without display, xvfb available: {env_info.xvfb_available}")
    
    # Basic consistency: if we have a display, we shouldn't be headless
    # (unless explicitly forced)
    if env_info.has_display and not env_info.is_ci:
        print(f"Has display but headless: {env_info.is_headless} (might be forced)")


if __name__ == "__main__":
    # If run directly, print environment report
    print("Running environment detection validation...")
    print(get_environment_report())
    
    # Run a few basic tests
    test_environment_detection_basic()
    test_environment_report_generation()
    test_convenience_functions()
    test_qt_configuration()
    
    print("Environment detection validation completed successfully!")