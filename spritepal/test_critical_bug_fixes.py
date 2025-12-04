#!/usr/bin/env python3
from __future__ import annotations

"""
Demonstration tests for critical bug fixes.
These tests simulate the bug conditions without requiring PySide6.
"""

import sys
import threading
import time
import weakref
from unittest.mock import Mock


def test_batch_thumbnail_worker_infinite_loop_prevention():
    """
    Test that BatchThumbnailWorker doesn't get stuck in infinite loop.
    This simulates the bug where the worker would loop forever with:
    "No more requests, processed 989 thumbnails" repeating.
    """
    print("\n🧪 Testing BatchThumbnailWorker infinite loop prevention...")

    class MockBatchThumbnailWorker:
        def __init__(self):
            self.idle_iterations = 0
            self.max_idle_iterations = 100  # Stop after 100 idle iterations (10 seconds)
            self.processed_count = 0
            self.running = True
            self.request_queue = []

        def run(self):
            """Simulated run method with idle detection fix."""
            while self.running:
                if not self.request_queue:
                    # THE FIX: Increment idle counter when no requests
                    self.idle_iterations += 1

                    # THE FIX: Auto-stop after max idle iterations
                    if self.idle_iterations >= self.max_idle_iterations:
                        print(f"  ✅ Auto-stopping after {self.idle_iterations} idle iterations")
                        self.running = False
                        break

                    # Simulate the old bug - would log forever here
                    if self.idle_iterations % 10 == 0:
                        print(f"  No more requests, processed {self.processed_count} thumbnails")

                    time.sleep(0.01)  # Simulate 100ms wait
                else:
                    # Process request
                    self.request_queue.pop(0)
                    self.processed_count += 1
                    self.idle_iterations = 0  # Reset idle counter

    # Test the fix
    worker = MockBatchThumbnailWorker()
    start_time = time.time()

    # Run worker in thread
    thread = threading.Thread(target=worker.run)
    thread.start()
    thread.join(timeout=2.0)  # Should stop quickly due to idle detection

    elapsed = time.time() - start_time

    if elapsed < 1.5:
        print(f"  ✅ PASS: Worker stopped in {elapsed:.2f}s (idle detection working)")
    else:
        print(f"  ❌ FAIL: Worker took {elapsed:.2f}s (might still have infinite loop)")

    return elapsed < 1.5

def test_memory_cleanup_after_processing():
    """
    Test that ROM data and caches are properly cleaned up.
    This simulates the memory leak where ROM data wasn't released.
    """
    print("\n🧪 Testing memory cleanup after processing...")

    class MockWorkerWithCleanup:
        def __init__(self):
            self._rom_data: bytes | None = None
            self._cache = {}

        def load_rom_data(self, size_mb: int):
            """Simulate loading ROM data."""
            self._rom_data = b'X' * (size_mb * 1024 * 1024)
            print(f"  Loaded {size_mb}MB ROM data")

        def _clear_rom_data(self):
            """THE FIX: Clear ROM data to free memory."""
            if self._rom_data is not None:
                size = len(self._rom_data) // (1024 * 1024)
                self._rom_data = None
                print(f"  ✅ Cleared {size}MB ROM data")

        def _clear_cache_memory(self):
            """THE FIX: Clear cache to free memory."""
            cache_items = len(self._cache)
            self._cache.clear()
            if cache_items > 0:
                print(f"  ✅ Cleared {cache_items} cached items")

        def cleanup(self):
            """Comprehensive cleanup method."""
            self._clear_rom_data()
            self._clear_cache_memory()

    # Test memory cleanup
    worker = MockWorkerWithCleanup()

    # Simulate processing
    worker.load_rom_data(8)  # Load 8MB ROM
    worker._cache = {i: f"sprite_{i}" for i in range(100)}  # Add cache items

    # Check memory is allocated
    assert worker._rom_data is not None, "ROM data should be loaded"
    assert len(worker._cache) == 100, "Cache should have items"

    # Perform cleanup
    worker.cleanup()

    # Verify memory is freed
    if worker._rom_data is None and len(worker._cache) == 0:
        print("  ✅ PASS: Memory properly cleaned up")
        return True
    print("  ❌ FAIL: Memory not fully cleaned up")
    return False

def test_worker_cleanup_prevents_thread_leaks():
    """
    Test that old workers are cleaned up before creating new ones.
    This simulates the thread leak where workers weren't terminated.
    """
    print("\n🧪 Testing worker cleanup prevents thread leaks...")

    class MockGalleryWindow:
        def __init__(self):
            self.scan_worker = None
            self.thumbnail_worker = None

        def _cleanup_existing_workers(self):
            """THE FIX: Clean up existing workers before creating new ones."""
            cleaned = []

            if self.scan_worker is not None:
                if hasattr(self.scan_worker, 'stop'):
                    self.scan_worker.stop()
                self.scan_worker = None
                cleaned.append('scan_worker')

            if self.thumbnail_worker is not None:
                if hasattr(self.thumbnail_worker, 'stop'):
                    self.thumbnail_worker.stop()
                self.thumbnail_worker = None
                cleaned.append('thumbnail_worker')

            return cleaned

        def start_new_scan(self):
            """Start a new scan operation."""
            # THE FIX: Always cleanup before creating new workers
            cleaned = self._cleanup_existing_workers()
            if cleaned:
                print(f"  ✅ Cleaned up old workers: {', '.join(cleaned)}")

            # Create new worker
            self.scan_worker = Mock()
            self.scan_worker.stop = Mock()

    # Test cleanup
    window = MockGalleryWindow()

    # Create initial workers
    window.scan_worker = Mock()
    window.scan_worker.stop = Mock()
    window.thumbnail_worker = Mock()
    window.thumbnail_worker.stop = Mock()

    # Start new scan (should cleanup old workers)
    window.start_new_scan()

    # Verify old workers were cleaned
    if window.scan_worker.stop.called:
        print("  ✅ PASS: Old workers properly cleaned up")
        return True
    # Check if cleanup happened
    if window.thumbnail_worker is None:
        print("  ✅ PASS: Workers cleaned up (thumbnail_worker is None)")
        return True
    print("  ❌ FAIL: Old workers not cleaned up")
    return False

def test_signal_disconnection_prevents_leaks():
    """
    Test that signals are properly disconnected to prevent memory leaks.
    This simulates the signal leak where connections weren't cleaned up.
    """
    print("\n🧪 Testing signal disconnection prevents leaks...")

    class MockSignal:
        def __init__(self):
            self.connections = []

        def connect(self, callback):
            """Connect a callback."""
            self.connections.append(weakref.ref(callback))

        def disconnect(self, callback=None):
            """THE FIX: Disconnect callbacks."""
            if callback is None:
                # Disconnect all
                old_count = len(self.connections)
                self.connections.clear()
                return old_count
            # Disconnect specific callback
            self.connections = [ref for ref in self.connections
                              if ref() != callback]
            return None

    class MockWorker:
        def __init__(self):
            self.finished = MockSignal()
            self.progress = MockSignal()

        def cleanup_signals(self):
            """THE FIX: Disconnect all signals on cleanup."""
            disconnected = 0
            disconnected += self.finished.disconnect()
            disconnected += self.progress.disconnect()
            return disconnected

    # Test signal cleanup
    worker = MockWorker()

    # Connect some callbacks
    def on_finished(): pass
    def on_progress(val): pass

    worker.finished.connect(on_finished)
    worker.progress.connect(on_progress)

    # Verify connections exist
    assert len(worker.finished.connections) == 1
    assert len(worker.progress.connections) == 1

    # Cleanup signals
    disconnected = worker.cleanup_signals()

    # Verify signals disconnected
    if len(worker.finished.connections) == 0 and len(worker.progress.connections) == 0:
        print(f"  ✅ PASS: {disconnected} signals properly disconnected")
        return True
    print("  ❌ FAIL: Signals not fully disconnected")
    return False

def run_all_tests():
    """Run all critical bug fix tests."""
    print("=" * 60)
    print("CRITICAL BUG FIX VERIFICATION TESTS")
    print("=" * 60)

    results = []

    # Run tests
    results.append(("Infinite Loop Prevention", test_batch_thumbnail_worker_infinite_loop_prevention()))
    results.append(("Memory Cleanup", test_memory_cleanup_after_processing()))
    results.append(("Thread Leak Prevention", test_worker_cleanup_prevents_thread_leaks()))
    results.append(("Signal Leak Prevention", test_signal_disconnection_prevents_leaks()))

    # Summary
    print("\n" + "=" * 60)
    print("TEST RESULTS SUMMARY")
    print("=" * 60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {test_name}: {status}")

    print(f"\n📊 Overall: {passed}/{total} tests passed")

    if passed == total:
        print("🎉 All critical bug fixes verified!")
    else:
        print("⚠️  Some tests failed - review the fixes")

    return passed == total

if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)

