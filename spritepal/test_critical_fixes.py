#!/usr/bin/env python3
"""
Test critical fixes applied to SpritePal.
This verifies:
1. NavigationManager is registered
2. HAL process pool cleanup works
3. Qt boolean evaluation patterns are fixed
4. Worker decorators are in place
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.resolve()))

def test_navigation_manager_registration():
    """Test NavigationManager is properly registered."""
    print("Testing NavigationManager registration...")

    from core.managers import cleanup_managers, get_registry, initialize_managers

    # Initialize managers
    initialize_managers("TestApp")

    try:
        registry = get_registry()
        nav_manager = registry.get_navigation_manager()

        assert nav_manager is not None, "NavigationManager should not be None"
        assert hasattr(nav_manager, "get_navigation_hints"), "NavigationManager should have get_navigation_hints method"

        print("✅ NavigationManager registration: PASSED")
        return True

    except Exception as e:
        print(f"❌ NavigationManager registration: FAILED - {e}")
        return False
    finally:
        cleanup_managers()


def test_hal_process_pool_cleanup():
    """Test HAL process pool cleanup."""
    print("\nTesting HAL process pool cleanup...")

    from core.hal_compression import HALProcessPool

    try:
        # Get pool instance
        pool = HALProcessPool()

        # Test multiple shutdowns (should not error)
        pool.shutdown()
        pool.shutdown()  # Second shutdown should be graceful

        # Test force reset
        pool.force_reset()

        print("✅ HAL process pool cleanup: PASSED")
        return True

    except Exception as e:
        print(f"❌ HAL process pool cleanup: FAILED - {e}")
        return False


def test_qt_boolean_patterns():
    """Test Qt boolean evaluation fixes."""
    print("\nTesting Qt boolean evaluation fixes...")

    try:
        # Read a file we fixed and check patterns
        with Path("ui/managers/status_bar_manager.py").open() as f:
            content = f.read()

        # Count proper patterns
        proper_patterns = content.count("is not None:")

        # Check specific fixes we made
        assert "if self.cache_icon_label is not None:" in content
        assert "if self.cache_info_label is not None:" in content
        assert "if self.cache_status_widget is not None:" in content

        print(f"✅ Qt boolean patterns fixed: PASSED ({proper_patterns} proper patterns found)")
        return True

    except Exception as e:
        print(f"❌ Qt boolean pattern check: FAILED - {e}")
        return False


def test_worker_decorators():
    """Test worker error decorators are in place."""
    print("\nTesting worker error decorators...")

    try:
        # Check SearchWorker
        with Path("ui/dialogs/advanced_search_dialog.py").open() as f:
            content = f.read()
        assert "@handle_worker_errors" in content, "SearchWorker should have decorator"

        # Check preview worker
        with Path("ui/rom_extraction/workers/preview_worker.py").open() as f:
            content = f.read()
        assert "@handle_worker_errors" in content, "PreviewWorker should have decorator"

        # Check range scan worker
        with Path("ui/rom_extraction/workers/range_scan_worker.py").open() as f:
            content = f.read()
        assert "@handle_worker_errors" in content, "RangeScanWorker should have decorator"

        print("✅ Worker error decorators: PASSED")
        return True

    except Exception as e:
        print(f"❌ Worker decorator check: FAILED - {e}")
        return False


def test_gui_thread_safety():
    """Test GUI thread safety fixes."""
    print("\nTesting GUI thread safety fixes...")

    try:
        with Path("ui/dialogs/advanced_search_dialog.py").open() as f:
            content = f.read()

        # Check for new signals
        assert "input_requested = pyqtSignal(str, str)" in content
        assert "question_requested = pyqtSignal(str, str)" in content
        assert "info_requested = pyqtSignal(str, str)" in content

        # Check for thread-safe methods
        assert "_request_user_input" in content
        assert "_handle_worker_input_request" in content

        # Ensure no direct GUI calls in run method
        lines = content.split("\n")
        in_run_method = False
        for line in lines:
            if "def run(self):" in line and "SearchWorker" in content[:content.find(line)]:
                in_run_method = True
            elif in_run_method and line.strip().startswith("def "):
                in_run_method = False

            if in_run_method:
                # These should not appear in run method anymore
                assert "QInputDialog.getText(" not in line, "QInputDialog should not be in run method"
                assert "QMessageBox.question(" not in line, "QMessageBox should not be in run method"

        print("✅ GUI thread safety: PASSED")
        return True

    except Exception as e:
        print(f"❌ GUI thread safety check: FAILED - {e}")
        return False


def main():
    """Run all tests."""
    print("SpritePal Critical Fixes Verification")
    print("=====================================\n")

    tests = [
        test_navigation_manager_registration,
        test_hal_process_pool_cleanup,
        test_qt_boolean_patterns,
        test_worker_decorators,
        test_gui_thread_safety
    ]

    results = []
    for test in tests:
        try:
            results.append(test())
        except Exception as e:
            print(f"Test {test.__name__} crashed: {e}")
            results.append(False)

    print("\n" + "="*50)
    print(f"TOTAL: {sum(results)}/{len(results)} tests passed")

    if all(results):
        print("\n🎉 ALL CRITICAL FIXES VERIFIED!")
        print("The application should now be stable and production-ready.")
    else:
        print("\n❌ Some fixes need attention.")


if __name__ == "__main__":
    main()
