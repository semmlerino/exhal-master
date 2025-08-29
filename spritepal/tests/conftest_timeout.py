"""
Pytest configuration for timeout protection.

This adds automatic timeout markers to tests to prevent them from hanging indefinitely.
Tests are categorized by their expected duration and given appropriate timeouts.
"""
from __future__ import annotations

import pytest

# Default timeout values (in seconds)
TIMEOUT_UNIT = 10        # Fast unit tests
TIMEOUT_INTEGRATION = 30  # Integration tests
TIMEOUT_SLOW = 60        # Known slow tests
TIMEOUT_BENCHMARK = 120  # Performance benchmarks

# Patterns for identifying test types
SLOW_TEST_PATTERNS = [
    "benchmark",
    "performance",
    "stress",
    "memory_leak",
    "concurrent",
    "worker_lifecycle",
    "full_workflow",
    "comprehensive",
]

INTEGRATION_PATTERNS = [
    "integration",
    "real",
    "workflow",
    "e2e",
    "end_to_end",
]

def pytest_collection_modifyitems(config, items):
    """Add timeout markers to tests based on their type."""

    # Check if timeout plugin is available
    timeout_available = config.pluginmanager.has_plugin("timeout")
    if not timeout_available:
        return

    for item in items:
        # Skip if test already has a timeout marker
        if item.get_closest_marker("timeout"):
            continue

        test_id = item.nodeid.lower()
        test_name = getattr(item.function, "__name__", "").lower() if hasattr(item, "function") else ""

        # Determine timeout based on test patterns
        timeout = TIMEOUT_UNIT  # Default

        # Check for slow test patterns
        if any(pattern in test_id or pattern in test_name for pattern in SLOW_TEST_PATTERNS):
            timeout = TIMEOUT_SLOW
        # Check for integration patterns
        elif any(pattern in test_id or pattern in test_name for pattern in INTEGRATION_PATTERNS):
            timeout = TIMEOUT_INTEGRATION
        # Check for benchmark marker
        elif item.get_closest_marker("benchmark"):
            timeout = TIMEOUT_BENCHMARK
        # Check for slow marker
        elif item.get_closest_marker("slow"):
            timeout = TIMEOUT_SLOW

        # Add timeout marker
        item.add_marker(pytest.mark.timeout(timeout))

def pytest_configure(config):
    """Register timeout-related configuration."""
    config.addinivalue_line(
        "markers",
        "timeout(seconds): Set a timeout for test execution"
    )

    # Log timeout configuration if verbose
    if config.option.verbose >= 1:
        terminal_reporter = config.pluginmanager.get_plugin("terminalreporter")
        if terminal_reporter:
            terminal_reporter.write_line(
                "Timeout protection enabled: "
                f"unit={TIMEOUT_UNIT}s, integration={TIMEOUT_INTEGRATION}s, "
                f"slow={TIMEOUT_SLOW}s, benchmark={TIMEOUT_BENCHMARK}s"
            )
