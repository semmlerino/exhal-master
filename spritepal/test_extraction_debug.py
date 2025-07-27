#!/usr/bin/env python
"""Debug test for full extraction workflow"""

import sys
from pathlib import Path
from unittest.mock import Mock, patch

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from tests.fixtures.test_main_window_helper_simple import TestMainWindowHelperSimple

from spritepal.core.controller import ExtractionWorker
from spritepal.core.managers import (
    cleanup_managers,
    get_extraction_manager,
    initialize_managers,
)


def test_full_extraction_workflow():
    """Test full extraction workflow with detailed debugging"""
    print("=== Starting Full Extraction Workflow Debug ===")

    try:
        # Initialize managers
        initialize_managers("DebugTest")
        manager = get_extraction_manager()
        print("✓ Managers initialized")

        # Track signals
        manager_signals = []
        def capture_manager_signal(msg):
            manager_signals.append(msg)
            print(f"Manager signal: {msg}")

        manager.extraction_progress.connect(capture_manager_signal)

        # Create test helper with real files
        helper = TestMainWindowHelperSimple()
        params = helper.create_vram_extraction_scenario()
        print(f"✓ Test scenario created with params: {params}")

        # Create worker
        worker = ExtractionWorker(params)
        print("✓ Worker created")

        # Track worker signals
        worker_signals = []
        def capture_worker_signal(msg):
            worker_signals.append(msg)
            print(f"Worker signal: {msg}")

        worker.progress.connect(capture_worker_signal)

        # Mock the image creation parts that might fail
        with (
            patch("spritepal.utils.image_utils.QPixmap") as mock_pixmap,
            patch("spritepal.core.controller.pil_to_qpixmap") as mock_pil_to_qpixmap,
        ):
            mock_pixmap_instance = Mock()
            mock_pixmap_instance.loadFromData = Mock(return_value=True)
            mock_pixmap.return_value = mock_pixmap_instance
            mock_pil_to_qpixmap.return_value = mock_pixmap_instance

            print("Running worker...")
            try:
                worker.run()
                print("✓ Worker completed successfully")
            except Exception as e:
                print(f"✗ Worker failed: {e}")
                import traceback
                traceback.print_exc()
                return False

        print(f"Manager signals received: {manager_signals}")
        print(f"Worker signals received: {worker_signals}")

        # Verify we got the expected signals
        expected_signals = [
            "Extracting sprites from VRAM...",
            "Creating preview...",
            "Extraction complete!"
        ]

        success = True
        for expected in expected_signals:
            if expected not in manager_signals:
                print(f"✗ Missing expected manager signal: {expected}")
                success = False
            if expected not in worker_signals:
                print(f"✗ Missing expected worker signal: {expected}")
                success = False

        if success:
            print("✓ All expected signals received")

        return success

    except Exception as e:
        print(f"✗ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        cleanup_managers()


if __name__ == "__main__":
    success = test_full_extraction_workflow()
    if success:
        print("\n✓ Full extraction workflow test PASSED")
    else:
        print("\n✗ Full extraction workflow test FAILED")
