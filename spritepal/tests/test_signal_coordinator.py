"""Tests for SignalCoordinator - thread-safe signal coordination."""

import pytest

# Skip all tests in this module since the SignalCoordinator component has been removed
# during the manual offset dialog consolidation cleanup
pytestmark = pytest.mark.skip(reason="SignalCoordinator component removed during cleanup")


def test_placeholder():
    """Placeholder test to prevent empty test module issues."""
