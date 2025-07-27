#!/usr/bin/env python
"""Simple test to debug signal emission"""

import sys
from pathlib import Path

# Use pytest's path setup
sys.path.insert(0, str(Path(__file__).parent.parent))

from spritepal.core.managers import (
    cleanup_managers,
    get_extraction_manager,
    initialize_managers,
)


def test_manager_signal_emission():
    """Test if manager emits signals correctly"""
    try:
        # Initialize managers
        initialize_managers("DebugTest")
        manager = get_extraction_manager()

        # Track signal emissions
        signals_received = []

        def capture_signal(msg):
            signals_received.append(msg)
            print(f"Signal received: {msg}")

        # Connect signal
        manager.extraction_progress.connect(capture_signal)

        # Emit test signal
        manager.extraction_progress.emit("Test signal")

        print(f"Total signals received: {len(signals_received)}")
        print(f"Signals: {signals_received}")

        # Verify signal was received
        assert len(signals_received) == 1
        assert signals_received[0] == "Test signal"

        print("✓ Manager signal emission works correctly")

    finally:
        cleanup_managers()


if __name__ == "__main__":
    test_manager_signal_emission()
