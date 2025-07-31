#!/usr/bin/env python
"""Debug script to test signal emission chain"""

import sys
import tempfile
from pathlib import Path

# Add parent directory to path to find spritepal module
sys.path.insert(0, "..")
sys.path.insert(0, ".")

from PyQt6.QtCore import QObject
from PyQt6.QtWidgets import QApplication
from tests.fixtures.test_main_window_helper_simple import TestMainWindowHelperSimple

from spritepal.core.controller import ExtractionController, ExtractionWorker

# Import the actual classes
from spritepal.core.managers import get_extraction_manager, initialize_managers


class DebugReceiver(QObject):
    """Debug receiver to track signal emissions"""

    def __init__(self):
        super().__init__()
        self.messages = []

    def on_progress(self, msg):
        self.messages.append(msg)
        print(f"✓ Received signal: {msg}")


def test_direct_manager_signals():
    """Test if manager emits signals directly"""
    print("=== Testing Direct Manager Signals ===")

    # Initialize managers
    initialize_managers("DebugTest")
    manager = get_extraction_manager()

    # Create receiver
    receiver = DebugReceiver()
    _ = manager.extraction_progress.connect(receiver.on_progress)

    # Test signal emission
    manager.extraction_progress.emit("Test message")
    print(f"Messages received: {receiver.messages}")

    return len(receiver.messages) > 0


def test_extraction_worker_signals():
    """Test if extraction worker properly relays signals"""
    print("\n=== Testing ExtractionWorker Signal Relay ===")

    # Create temp files
    temp_dir = Path(tempfile.mkdtemp())

    # Create minimal test files
    vram_file = temp_dir / "test.vram"
    vram_file.write_bytes(b"\x00" * 0x10000)  # 64KB of zeros

    cgram_file = temp_dir / "test.cgram"
    cgram_file.write_bytes(b"\x00" * 512)  # 512 bytes of zeros

    # Create extraction parameters
    params = {
        "vram_path": str(vram_file),
        "cgram_path": str(cgram_file),
        "output_base": str(temp_dir / "test_output"),
        "create_grayscale": True,
        "create_metadata": True,
        "grayscale_mode": False,
    }

    # Create worker
    worker = ExtractionWorker(params)

    # Create receiver
    receiver = DebugReceiver()
    _ = worker.progress.connect(receiver.on_progress)

    print("Running worker...")
    try:
        worker.run()
        print(f"Worker completed. Messages received: {receiver.messages}")
        return len(receiver.messages) > 0
    except Exception as e:
        print(f"Worker failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_controller_integration():
    """Test full controller integration"""
    print("\n=== Testing Controller Integration ===")

    # Create Qt application if needed
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)

    # Create helper
    helper = TestMainWindowHelperSimple()

    # Set up extraction parameters
    helper.create_vram_extraction_scenario()

    # Create controller
    controller = ExtractionController(helper)

    print("Starting extraction...")
    try:
        controller.start_extraction()

        # If worker exists, run it synchronously
        if controller.worker:
            print("Running worker synchronously...")
            controller.worker.run()

        # Check results
        signals = helper.get_signal_emissions()
        print(f"Status messages: {signals['status_messages']}")
        print(f"All signals: {signals}")

        return len(signals["status_messages"]) > 0

    except Exception as e:
        print(f"Controller test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("Starting signal chain debug tests...")

    test1 = test_direct_manager_signals()
    test2 = test_extraction_worker_signals()
    test3 = test_controller_integration()

    print("\n=== Results ===")
    print(f"Direct manager signals: {'PASS' if test1 else 'FAIL'}")
    print(f"Worker signal relay: {'PASS' if test2 else 'FAIL'}")
    print(f"Controller integration: {'PASS' if test3 else 'FAIL'}")

    if test1 and test2 and test3:
        print("✓ All tests passed - signal chain is working")
    else:
        print("✗ Some tests failed - signal chain has issues")
