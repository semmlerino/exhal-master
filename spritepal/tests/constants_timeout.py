"""
Constants for timeout configuration.

This file contains timeout values and patterns for categorizing tests.
The actual timeout marker logic is implemented in conftest.py.
"""
from __future__ import annotations

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
