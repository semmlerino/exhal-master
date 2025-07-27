#!/usr/bin/env python
"""Debug test for controller signal flow"""

import sys
from pathlib import Path
from unittest.mock import Mock, patch

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from tests.fixtures.test_main_window_helper_simple import TestMainWindowHelperSimple

from spritepal.core.controller import ExtractionController
from spritepal.core.managers import cleanup_managers, initialize_managers


def test_controller_signal_flow():
    """Test controller signal flow with detailed debugging"""
    print("=== Starting Controller Signal Flow Debug ===")

    try:
        # Initialize managers
        initialize_managers("DebugTest")
        print("✓ Managers initialized")

        # Create test helper
        helper = TestMainWindowHelperSimple()
        helper.create_vram_extraction_scenario()
        print("✓ Test scenario created")

        # Create controller
        controller = ExtractionController(helper)
        print("✓ Controller created")

        # Mock the Qt components like the integration test does
        mock_pixmap_instance = Mock()
        mock_pixmap_instance.loadFromData = Mock(return_value=True)

        with (
            patch("spritepal.utils.image_utils.QPixmap") as mock_qpixmap_utils,
            patch("spritepal.core.controller.pil_to_qpixmap") as mock_pil_to_qpixmap,
            patch("spritepal.core.controller.QThread") as mock_qthread,
            patch("spritepal.core.controller.pyqtSignal") as mock_pyqt_signal,
        ):
            # Configure mocks like integration test
            mock_qpixmap_utils.return_value = mock_pixmap_instance
            mock_pil_to_qpixmap.return_value = mock_pixmap_instance
            mock_pyqt_signal.side_effect = lambda *args: Mock()

            # Mock QThread to run synchronously
            mock_qthread_instance = Mock()
            mock_qthread_instance.start = Mock()
            mock_qthread_instance.isRunning = Mock(return_value=False)
            mock_qthread_instance.quit = Mock()
            mock_qthread_instance.wait = Mock(return_value=True)
            mock_qthread.return_value = mock_qthread_instance

            print("Starting extraction...")
            controller.start_extraction()

            print(f"Worker created: {controller.worker is not None}")

            if controller.worker:
                print("Running worker synchronously...")

                # Debug: check signal connections
                print(f"Controller _on_progress method: {controller._on_progress}")

                # Test signal connection by manually calling _on_progress
                print("Testing controller _on_progress method directly...")
                controller._on_progress("Test message from controller")

                # Check if helper captured the message
                test_signals = helper.get_signal_emissions()
                print(f"After direct call, status messages: {test_signals['status_messages']}")

                # Run worker
                controller.worker.run()
                print("Worker completed")
            else:
                print("ERROR: No worker was created")
                return False

        # Get results
        signals = helper.get_signal_emissions()
        print(f"Status messages captured: {signals['status_messages']}")
        print(f"All signals: {signals}")

        # Check if we got expected messages
        expected_messages = [
            "Extracting sprites from VRAM...",
            "Creating preview...",
            "Extraction complete!"
        ]

        success = True
        for expected in expected_messages:
            if expected not in signals["status_messages"]:
                print(f"✗ Missing expected status message: {expected}")
                success = False

        if success:
            print("✓ All expected status messages captured")

        return success

    except Exception as e:
        print(f"✗ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        cleanup_managers()


if __name__ == "__main__":
    success = test_controller_signal_flow()
    if success:
        print("\n✓ Controller signal flow test PASSED")
    else:
        print("\n✗ Controller signal flow test FAILED")
