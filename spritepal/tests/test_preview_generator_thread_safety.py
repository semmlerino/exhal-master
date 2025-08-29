"""
Test thread safety of PreviewGenerator singleton implementation.

This test module verifies:
1. Thread-safe singleton initialization
2. No race conditions during concurrent access
3. Proper cleanup handling
4. Cache thread safety
"""
from __future__ import annotations

import concurrent.futures
import os

# Import with proper path
import sys
import threading
import time
from unittest.mock import MagicMock, patch

import pytest

# Serial execution required: Thread safety concerns
pytestmark = [
    
    pytest.mark.serial,
    pytest.mark.thread_safety,
    pytest.mark.cache,
    pytest.mark.ci_safe,
    pytest.mark.headless,
    pytest.mark.worker_threads,
]

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.preview_generator import (
    PreviewGenerator,
    PreviewRequest,
    PreviewResult,
    cleanup_preview_generator,
    get_preview_generator,
)

class TestPreviewGeneratorThreadSafety:
    """Test thread safety of PreviewGenerator singleton."""

    def test_singleton_concurrent_initialization(self):
        """Test that concurrent initialization creates only one instance."""
        # Clean up any existing instance
        cleanup_preview_generator()

        instances = []
        init_count = 0
        lock = threading.Lock()

        # Patch PreviewGenerator.__init__ to count initializations
        original_init = PreviewGenerator.__init__

        def counted_init(self, *args, **kwargs):
            nonlocal init_count
            with lock:
                init_count += 1
            original_init(self, *args, **kwargs)

        with patch.object(PreviewGenerator, "__init__", counted_init):
            # Try to get instance from multiple threads simultaneously
            def get_instance():
                instance = get_preview_generator()
                instances.append(instance)
                return instance

            # Use ThreadPoolExecutor for concurrent access
            with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
                futures = [executor.submit(get_instance) for _ in range(100)]
                concurrent.futures.wait(futures)

            # Verify only one instance was created
            assert init_count == 1, f"Expected 1 initialization, got {init_count}"

            # Verify all threads got the same instance
            first_instance = instances[0]
            for instance in instances:
                assert instance is first_instance, "Multiple instances created!"

    def test_singleton_fast_path_performance(self):
        """Test that initialized singleton uses fast path without locking."""
        # Ensure instance exists
        instance = get_preview_generator()

        # Time multiple accesses
        start_time = time.time()
        for _ in range(10000):
            retrieved = get_preview_generator()
            assert retrieved is instance
        elapsed = time.time() - start_time

        # Should be very fast (no lock contention)
        assert elapsed < 0.1, f"Fast path too slow: {elapsed:.4f}s for 10000 accesses"

    def test_cache_concurrent_access(self):
        """Test LRU cache thread safety with concurrent reads/writes."""
        generator = get_preview_generator()
        cache = generator._cache

        # Clear cache
        cache.clear()

        errors = []

        def cache_writer(thread_id: int):
            """Write to cache from thread."""
            try:
                for i in range(100):
                    key = f"thread_{thread_id}_item_{i}"
                    result = PreviewResult(
                        pixmap=MagicMock(),
                        pil_image=MagicMock(),
                        tile_count=i,
                        sprite_name=f"sprite_{thread_id}_{i}",
                        generation_time=0.1
                    )
                    cache.put(key, result)
                    # Small delay to increase contention
                    time.sleep(0.0001)
            except Exception as e:
                errors.append(e)

        def cache_reader(thread_id: int):
            """Read from cache from thread."""
            try:
                for i in range(100):
                    # Try to read various keys
                    for tid in range(5):
                        key = f"thread_{tid}_item_{i}"
                        result = cache.get(key)
                        # Verify result if found
                        if result and not result.cached:
                            errors.append(ValueError("Result not marked as cached"))
            except Exception as e:
                errors.append(e)

        # Run concurrent readers and writers
        threads = []

        # Start writers
        for i in range(5):
            thread = threading.Thread(target=cache_writer, args=(i,))
            threads.append(thread)
            thread.start()

        # Start readers
        for i in range(5):
            thread = threading.Thread(target=cache_reader, args=(i,))
            threads.append(thread)
            thread.start()

        # Wait for all threads
        for thread in threads:
            thread.join()

        # Check for errors
        assert not errors, f"Thread safety errors: {errors}"

        # Verify cache statistics are consistent
        stats = cache.get_stats()
        assert stats["hits"] >= 0
        assert stats["misses"] >= 0
        assert stats["evictions"] >= 0
        assert stats["cache_size"] <= cache.max_size

    def test_cleanup_thread_safety(self):
        """Test thread-safe cleanup during concurrent access."""
        # Ensure instance exists
        get_preview_generator()

        cleanup_called = False
        errors = []

        def access_generator():
            """Try to access generator."""
            try:
                # This might get None if cleanup happens first
                gen = get_preview_generator()
                if gen is not None:
                    # Try to use it
                    gen.get_cache_stats()
            except Exception as e:
                errors.append(e)

        def cleanup_generator():
            """Clean up generator."""
            nonlocal cleanup_called
            try:
                cleanup_preview_generator()
                cleanup_called = True
            except Exception as e:
                errors.append(e)

        # Run cleanup and access concurrently
        threads = []

        # Multiple accessors
        for _ in range(10):
            thread = threading.Thread(target=access_generator)
            threads.append(thread)
            thread.start()

        # One cleanup thread
        thread = threading.Thread(target=cleanup_generator)
        threads.append(thread)
        thread.start()

        # More accessors after cleanup starts
        for _ in range(10):
            thread = threading.Thread(target=access_generator)
            threads.append(thread)
            thread.start()

        # Wait for all threads
        for thread in threads:
            thread.join()

        # Verify cleanup happened without errors
        assert cleanup_called
        assert not errors, f"Thread safety errors during cleanup: {errors}"

    def test_preview_generation_concurrent(self):
        """Test concurrent preview generation requests."""
        generator = get_preview_generator()

        # Mock the extraction manager
        mock_manager = MagicMock()
        mock_manager.generate_preview.return_value = (MagicMock(), 10)
        generator._extraction_manager_ref = lambda: mock_manager

        errors = []
        results = []

        def generate_preview(offset: int):
            """Generate preview from thread."""
            try:
                request = PreviewRequest(
                    source_type="vram",
                    data_path="/fake/path.bin",
                    offset=offset,
                    sprite_name=f"sprite_{offset}"
                )
                result = generator.generate_preview(request)
                if result:
                    results.append(result)
            except Exception as e:
                errors.append(e)

        # Generate previews concurrently
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [
                executor.submit(generate_preview, offset)
                for offset in range(0, 1000, 100)
            ]
            concurrent.futures.wait(futures)

        # Verify no errors
        assert not errors, f"Errors during concurrent generation: {errors}"

        # Verify results were generated
        assert len(results) > 0, "No results generated"

    def test_debounce_timer_thread_safety(self):
        """Test debounce timer handling across threads."""
        generator = get_preview_generator()

        # Mock the extraction manager
        mock_manager = MagicMock()
        mock_manager.generate_preview.return_value = (MagicMock(), 10)
        generator._extraction_manager_ref = lambda: mock_manager

        errors = []

        def async_request(offset: int):
            """Make async preview request."""
            try:
                request = PreviewRequest(
                    source_type="vram",
                    data_path="/fake/path.bin",
                    offset=offset
                )
                generator.generate_preview_async(request, use_debounce=True)
            except Exception as e:
                errors.append(e)

        # Make many rapid async requests from different threads
        threads = []
        for i in range(20):
            thread = threading.Thread(target=async_request, args=(i * 100,))
            threads.append(thread)
            thread.start()
            time.sleep(0.001)  # Small delay between requests

        # Wait for threads
        for thread in threads:
            thread.join()

        # Wait for debounce to complete
        time.sleep(0.2)

        # Verify no errors
        assert not errors, f"Errors during debounced requests: {errors}"

        # Cancel any pending requests
        generator.cancel_pending_requests()

@pytest.fixture(autouse=True)
def cleanup_singleton():
    """Ensure singleton is cleaned up after each test."""
    yield
    cleanup_preview_generator()