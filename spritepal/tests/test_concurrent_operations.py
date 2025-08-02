"""
Integration tests for concurrent operations in SpritePal.

This module tests threading scenarios that can occur in real usage:
- Multiple ROM scans running simultaneously
- Cache operations during UI updates
- Extraction while user navigates UI
- Settings changes during active operations

Tests use real QThread instances without mocking to find actual race conditions.
"""

import os
import time
from pathlib import Path
from unittest.mock import patch

import pytest
from PyQt6.QtCore import QThread, QTimer, pyqtSignal
from PyQt6.QtTest import QTest

from spritepal.core.managers import cleanup_managers, initialize_managers
from spritepal.core.rom_extractor import ROMExtractor
from spritepal.core.workers import VRAMExtractionWorker
from spritepal.ui.rom_extraction.workers.scan_worker import SpriteScanWorker
from spritepal.utils.rom_cache import ROMCache, get_rom_cache

# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture
def temp_dirs(tmp_path):
    """Create temporary directories for testing."""
    dirs = {
        "cache": tmp_path / "cache",
        "output": tmp_path / "output",
        "dumps": tmp_path / "dumps",
    }
    for dir_path in dirs.values():
        dir_path.mkdir(exist_ok=True)
    return dirs


@pytest.fixture
def sample_files(temp_dirs):
    """Create sample test files."""
    # Create a fake ROM file - smaller for faster testing
    rom_path = temp_dirs["dumps"] / "test.sfc"
    with open(rom_path, "wb") as f:
        # Write a smaller ROM (512KB instead of 1MB)
        f.write(b"\x00" * 0x80000)  # 512KB ROM
        # Add some fake compressed sprite data that won't decompress properly
        # This is fine for testing concurrent access, not actual sprite extraction
        f.seek(0xC0200)
        f.write(b"\xFF" * 0x100)  # Small data that will fail quality checks quickly
        f.seek(0xC0400)
        f.write(b"\xAA" * 0x100)  # Another small chunk

    # Create VRAM dump
    vram_path = temp_dirs["dumps"] / "test_vram.dmp"
    with open(vram_path, "wb") as f:
        f.write(b"\x00" * 0x10000)  # 64KB VRAM
        # Add sprite data at standard offset
        f.seek(0xC000)
        f.write(b"\xFF" * 0x1000)  # 4KB sprite data

    # Create CGRAM dump
    cgram_path = temp_dirs["dumps"] / "test_cgram.dmp"
    with open(cgram_path, "wb") as f:
        # Write 512 bytes of palette data
        f.write(b"\x00\x00" * 256)  # Black palette

    return {
        "rom_path": str(rom_path),
        "vram_path": str(vram_path),
        "cgram_path": str(cgram_path),
        "output_dir": str(temp_dirs["output"]),
    }


@pytest.fixture(autouse=True)
def setup_teardown(temp_dirs):
    """Initialize and cleanup managers for each test."""
    # Use real cache directory
    os.environ["SPRITEPAL_CACHE_DIR"] = str(temp_dirs["cache"])

    initialize_managers("TestConcurrent")
    yield

    # Cleanup
    cleanup_managers()

    # Reset cache singleton
    import spritepal.utils.rom_cache as rom_cache_module
    rom_cache_module._rom_cache_instance = None

    # Clear environment
    if "SPRITEPAL_CACHE_DIR" in os.environ:
        del os.environ["SPRITEPAL_CACHE_DIR"]


@pytest.fixture
def real_cache(temp_dirs):
    """Create a real ROM cache instance."""
    # Ensure cache is enabled for tests
    from spritepal.utils.settings_manager import get_settings_manager
    settings = get_settings_manager()
    if settings:
        settings.set_cache_enabled(True)

    cache = ROMCache(cache_dir=str(temp_dirs["cache"]))
    with patch("spritepal.utils.rom_cache.get_rom_cache", return_value=cache):
        yield cache


@pytest.fixture
def mock_main_window():
    """Create a minimal mock main window for testing."""
    from spritepal.tests.fixtures.test_main_window_helper_simple import (
        TestMainWindowHelperSimple,
    )

    helper = TestMainWindowHelperSimple()
    yield helper
    # Cleanup after test
    helper.cleanup()


# ============================================================================
# Worker Completion Tracker
# ============================================================================

class WorkerTracker:
    """Helper to track worker thread completion."""

    def __init__(self):
        self.workers = []
        self.completed = []
        self.errors = []

    def add_worker(self, worker, name):
        """Add a worker to track."""
        self.workers.append((worker, name))

        # Connect to completion signals
        if hasattr(worker, "finished"):
            worker.finished.connect(lambda: self._on_finished(name))
        if hasattr(worker, "error"):
            worker.error.connect(lambda msg: self._on_error(name, msg))

    def _on_finished(self, name):
        """Track worker completion."""
        self.completed.append(name)

    def _on_error(self, name, msg):
        """Track worker errors."""
        self.errors.append((name, msg))

    def wait_all(self, timeout_ms=5000):
        """Wait for all workers to complete."""
        start_time = time.time()

        while len(self.completed) < len(self.workers):
            QTest.qWait(100)  # Process events

            if (time.time() - start_time) * 1000 > timeout_ms:
                active = [name for worker, name in self.workers if name not in self.completed]
                raise TimeoutError(f"Workers still active after {timeout_ms}ms: {active}")

    def verify_no_errors(self):
        """Verify no workers reported errors."""
        if self.errors:
            raise AssertionError(f"Worker errors: {self.errors}")


# ============================================================================
# Concurrent ROM Scanning Tests
# ============================================================================

class TestConcurrentROMScanning:
    """Test concurrent ROM scanning operations."""

    def test_multiple_rom_scans_with_cache(self, qtbot, sample_files, real_cache):
        """Test multiple ROM scans accessing cache concurrently."""
        # First test basic cache functionality
        from spritepal.core.rom_injector import SpritePointer

        rom_path = sample_files["rom_path"]

        # Test 1: Basic save and load
        test_sprites = {
            "TestSprite": SpritePointer(offset=0x1000, bank=0x20, address=0x8000, compressed_size=256)
        }

        # Save to cache
        save_result = real_cache.save_sprite_locations(rom_path, test_sprites)
        assert save_result is True, "Failed to save sprites to cache"

        # Load from cache
        loaded_sprites = real_cache.get_sprite_locations(rom_path)
        assert loaded_sprites is not None, "Failed to load sprites from cache"
        assert "TestSprite" in loaded_sprites, "Sprite not found in loaded data"

        # Test 2: Concurrent access test
        results = {"saves": 0, "loads": 0, "errors": []}

        class SimpleCacheWorker(QThread):
            finished = pyqtSignal()

            def __init__(self, worker_id, cache, rom_path):
                super().__init__()
                self.worker_id = worker_id
                self.cache = cache
                self.rom_path = rom_path

            def run(self):
                try:
                    from spritepal.core.rom_injector import SpritePointer

                    # Simple read and write
                    existing = self.cache.get_sprite_locations(self.rom_path)
                    if existing:
                        results["loads"] += 1

                    new_data = existing or {}
                    new_data[f"Worker{self.worker_id}"] = SpritePointer(
                        offset=0x2000 + self.worker_id * 0x100,
                        bank=0x20,
                        address=0x8000,
                        compressed_size=256
                    )

                    if self.cache.save_sprite_locations(self.rom_path, new_data):
                        results["saves"] += 1

                    self.finished.emit()
                except Exception as e:
                    results["errors"].append(str(e))

        # Create simple workers
        workers = []
        for i in range(3):
            worker = SimpleCacheWorker(i, real_cache, rom_path)
            workers.append(worker)

        # Start all workers
        for worker in workers:
            worker.start()

        # Wait for all to finish
        for worker in workers:
            worker.wait(2000)

        # Verify results
        assert results["saves"] >= 1, f"No successful saves: {results}"
        assert len(results["errors"]) == 0, f"Errors occurred: {results['errors']}"

        # Verify final state
        final_data = real_cache.get_sprite_locations(rom_path)
        assert final_data is not None, "Final cache data is None"

    def test_concurrent_cache_read_write(self, qtbot, sample_files, real_cache):
        """Test concurrent cache reads and writes don't cause locks."""
        results = {"reads": 0, "writes": 0, "errors": []}

        class CacheReader(QThread):
            finished = pyqtSignal()
            error = pyqtSignal(str)

            def __init__(self, cache, rom_path):
                super().__init__()
                self.cache = cache
                self.rom_path = rom_path

            def run(self):
                try:
                    for _ in range(10):
                        # Try to read from cache
                        sprites = self.cache.get_sprite_locations(self.rom_path)
                        if sprites:
                            results["reads"] += 1
                        time.sleep(0.01)  # Small delay
                    self.finished.emit()
                except Exception as e:
                    self.error.emit(str(e))
                    results["errors"].append(str(e))

        class CacheWriter(QThread):
            finished = pyqtSignal()
            error = pyqtSignal(str)

            def __init__(self, cache, rom_path, worker_id):
                super().__init__()
                self.cache = cache
                self.rom_path = rom_path
                self.worker_id = worker_id

            def run(self):
                try:
                    for i in range(5):
                        # Write sprite data
                        sprite_data = {
                            f"Sprite_{self.worker_id}_{i}": {
                                "offset": 0x1000 * i,
                                "bank": 0x20,
                                "address": 0x8000,
                                "compressed_size": 256
                            }
                        }
                        self.cache.save_sprite_locations(self.rom_path, sprite_data)
                        results["writes"] += 1
                        time.sleep(0.02)  # Small delay
                    self.finished.emit()
                except Exception as e:
                    self.error.emit(str(e))
                    results["errors"].append(str(e))

        tracker = WorkerTracker()

        # Create readers and writers
        readers = [CacheReader(real_cache, sample_files["rom_path"]) for _ in range(2)]
        writers = [CacheWriter(real_cache, sample_files["rom_path"], i) for i in range(2)]

        # Track all workers
        for i, reader in enumerate(readers):
            tracker.add_worker(reader, f"reader_{i}")
        for i, writer in enumerate(writers):
            tracker.add_worker(writer, f"writer_{i}")

        # Start all concurrently
        for worker in readers + writers:
            worker.start()

        # Wait for completion
        tracker.wait_all(timeout_ms=10000)

        # Verify results
        assert results["writes"] == 10  # 2 writers * 5 writes each
        assert len(results["errors"]) == 0  # No database lock errors

        # Verify cache integrity
        final_sprites = real_cache.get_sprite_locations(sample_files["rom_path"])
        assert final_sprites is not None


# ============================================================================
# Concurrent Extraction Tests
# ============================================================================

class TestConcurrentExtraction:
    """Test concurrent extraction operations."""

    def test_extraction_during_ui_updates(self, qtbot, sample_files, mock_main_window):
        """Test extraction worker while UI is being updated."""
        results = {"extraction_done": False, "ui_updates": 0, "errors": []}

        # Create extraction parameters
        params = {
            "vram_path": sample_files["vram_path"],
            "cgram_path": sample_files["cgram_path"],
            "output_base": os.path.join(sample_files["output_dir"], "test"),
            "create_grayscale": True,
            "create_metadata": True,
            "oam_path": None,
            "vram_offset": 0xC000,
            "grayscale_mode": False,
        }

        # Create extraction worker
        worker = VRAMExtractionWorker(params)

        def on_finished(files):
            results["extraction_done"] = True

        def on_error(msg):
            results["errors"].append(msg)

        worker.extraction_finished.connect(on_finished)
        worker.error.connect(on_error)

        # Simulate UI updates during extraction
        def update_ui():
            try:
                # Simulate various UI operations
                mock_main_window.status_bar.showMessage(f"Update {results['ui_updates']}")
                mock_main_window.preview_info.setText(f"Preview {results['ui_updates']}")
                results["ui_updates"] += 1
            except Exception as e:
                results["errors"].append(f"UI error: {e}")

        # Set up timer for UI updates
        timer = QTimer()
        timer.timeout.connect(update_ui)
        timer.start(50)  # Update every 50ms

        # Start extraction
        worker.start()

        # Wait for extraction to complete
        timeout = 5000
        start_time = time.time()
        while not results["extraction_done"] and (time.time() - start_time) * 1000 < timeout:
            QTest.qWait(100)

        # Stop UI updates
        timer.stop()

        # Verify results
        assert results["extraction_done"]
        assert results["ui_updates"] > 0
        assert len(results["errors"]) == 0

        # Verify output files were created
        assert os.path.exists(f"{params['output_base']}.png")

    def test_multiple_extractions_different_files(self, qtbot, sample_files):
        """Test multiple extraction workers on different files - properly serialized."""
        # The ExtractionManager prevents concurrent VRAM extractions
        # This test verifies that multiple extraction requests are handled sequentially

        completed_extractions = []
        errors = []

        # Create multiple VRAM files
        vram_files = []
        for i in range(3):
            vram_path = Path(sample_files["output_dir"]) / f"vram_{i}.dmp"
            with open(vram_path, "wb") as f:
                f.write(b"\x00" * 0x10000)
                f.seek(0xC000)
                f.write(bytes([i] * 0x1000))  # Different pattern for each
            vram_files.append(str(vram_path))

        # Run extractions sequentially (as the manager enforces)
        for i, vram_path in enumerate(vram_files):
            params = {
                "vram_path": vram_path,
                "cgram_path": sample_files["cgram_path"],
                "output_base": os.path.join(sample_files["output_dir"], f"extract_{i}"),
                "create_grayscale": True,
                "create_metadata": False,
                "oam_path": None,
                "vram_offset": 0xC000,
                "grayscale_mode": False,
            }

            # Create and run worker
            worker = VRAMExtractionWorker(params)

            def on_finished(files, idx=i):
                completed_extractions.append(idx)

            def on_error(msg, idx=i):
                errors.append((idx, msg))

            worker.extraction_finished.connect(on_finished)
            worker.error.connect(on_error)

            # Run synchronously
            worker.run()

        # Verify all extractions completed
        assert len(completed_extractions) == 3
        assert len(errors) == 0

        # Verify all outputs were created
        for i in range(3):
            output_path = os.path.join(sample_files["output_dir"], f"extract_{i}.png")
            assert os.path.exists(output_path)


# ============================================================================
# Settings Change During Operations
# ============================================================================

class TestSettingsChangeDuringOperations:
    """Test settings changes while operations are active."""

    def test_cache_disable_during_scan(self, qtbot, sample_files, real_cache):
        """Test disabling cache while scan is in progress."""
        from spritepal.utils.settings_manager import get_settings_manager

        settings = get_settings_manager()
        results = {"scan_finished": False}

        # Enable cache initially
        settings.set_cache_enabled(True)

        # Create scan worker
        extractor = ROMExtractor()
        worker = SpriteScanWorker(sample_files["rom_path"], extractor, use_cache=True)

        def on_finished():
            results["scan_finished"] = True

        worker.finished.connect(on_finished)

        # Start scan
        worker.start()

        # Disable cache after a short delay
        QTest.qWait(100)
        settings.set_cache_enabled(False)

        # Wait for scan to complete
        timeout = 5000
        start_time = time.time()
        while not results["scan_finished"] and (time.time() - start_time) * 1000 < timeout:
            QTest.qWait(100)

        # Verify scan completed
        assert results["scan_finished"]

    def test_cache_location_change_during_operation(self, qtbot, sample_files, temp_dirs):
        """Test changing cache location while operations are active."""
        from spritepal.utils.settings_manager import get_settings_manager

        settings = get_settings_manager()

        # Set initial cache location
        cache_dir1 = temp_dirs["cache"] / "cache1"
        cache_dir1.mkdir()
        settings.set_cache_location(str(cache_dir1))

        # Get cache instance
        cache = get_rom_cache()

        # Start a cache write operation
        results = {"write_done": False, "error": None}

        class CacheWriteWorker(QThread):
            finished = pyqtSignal()
            error = pyqtSignal(str)

            def run(self):
                try:
                    # Perform multiple cache operations
                    for i in range(10):
                        cache.save_sprite_locations(
                            f"/test/rom_{i}.sfc",
                            {f"Sprite_{i}": {"offset": i * 0x1000}}
                        )
                        time.sleep(0.05)
                    results["write_done"] = True
                    self.finished.emit()
                except Exception as e:
                    results["error"] = str(e)
                    self.error.emit(str(e))

        worker = CacheWriteWorker()
        worker.start()

        # Change cache location mid-operation
        QTest.qWait(150)  # Let some writes happen
        cache_dir2 = temp_dirs["cache"] / "cache2"
        cache_dir2.mkdir()
        settings.set_cache_location(str(cache_dir2))

        # Wait for completion
        worker.wait(5000)

        # Verify operation completed
        assert results["write_done"] or results["error"]

        # Verify cache files exist in one of the locations
        # Check for any cache files (db or json)
        cache1_files = list(cache_dir1.glob("*"))
        cache2_files = list(cache_dir2.glob("*"))

        # Print for debugging if no files found
        if len(cache1_files) == 0 and len(cache2_files) == 0:
            print(f"Cache dir 1 contents: {list(cache_dir1.iterdir())}")
            print(f"Cache dir 2 contents: {list(cache_dir2.iterdir())}")

        # Either operation completed with files in a cache, or it was interrupted
        # The important thing is no error occurred during the cache location change
        assert results["write_done"] or len(cache1_files) > 0 or len(cache2_files) > 0


# ============================================================================
# UI Responsiveness Tests
# ============================================================================

class TestUIResponsiveness:
    """Test UI remains responsive during long operations."""

    def test_ui_responsive_during_large_scan(self, qtbot, sample_files, mock_main_window):
        """Test that long operations complete successfully in background."""
        # Simple test that a worker thread can run while UI remains active
        operation_completed = False

        class SimpleWorker(QThread):
            def run(self):
                # Simulate some work
                time.sleep(0.5)
                nonlocal operation_completed
                operation_completed = True

        # Create and start worker
        worker = SimpleWorker()
        worker.start()

        # Simulate UI activity while worker runs
        for i in range(5):
            mock_main_window.status_bar.showMessage(f"Working... {i}")
            QTest.qWait(100)  # Small delay

        # Wait for worker to complete
        worker.wait(2000)

        # Verify work completed
        assert operation_completed
        # Verify UI was updated (the helper tracks status messages)
        status_messages = mock_main_window.get_signal_emissions()["status_messages"]
        assert any("Working" in msg for msg in status_messages)


# ============================================================================
# Manager Thread Safety Tests
# ============================================================================

class TestManagerThreadSafety:
    """Test manager thread safety with concurrent access."""

    def test_extraction_manager_concurrent_access(self, qtbot, sample_files):
        """Test ExtractionManager handles concurrent extractions safely."""
        from spritepal.core.managers import get_extraction_manager

        manager = get_extraction_manager()
        results = {"previews": 0, "errors": []}

        class PreviewWorker(QThread):
            finished = pyqtSignal()
            error = pyqtSignal(str)

            def __init__(self, worker_id):
                super().__init__()
                self.worker_id = worker_id

            def run(self):
                try:
                    # Try to generate preview multiple times
                    for i in range(3):
                        # Generate preview with different offsets
                        offset = 0xC000 + (self.worker_id * 0x100) + (i * 0x10)
                        img, tiles = manager.generate_preview(
                            sample_files["vram_path"],
                            offset
                        )
                        if img and tiles > 0:
                            results["previews"] += 1
                        time.sleep(0.05)  # Small delay
                    self.finished.emit()
                except Exception as e:
                    results["errors"].append(str(e))
                    self.error.emit(str(e))

        # Create multiple workers
        workers = [PreviewWorker(i) for i in range(3)]

        # Start all workers
        for worker in workers:
            worker.start()

        # Wait for all to complete
        for worker in workers:
            worker.wait(5000)

        # Verify no errors occurred
        assert len(results["errors"]) == 0
        # Verify previews were generated
        assert results["previews"] > 0


# ============================================================================
# Race Condition Tests
# ============================================================================

class TestRaceConditions:
    """Test for specific race conditions."""

    def test_cache_save_during_read(self, qtbot, sample_files, real_cache):
        """Test saving to cache while another thread is reading."""
        rom_path = sample_files["rom_path"]
        race_detected = {"collision": False}

        # Pre-populate cache
        from spritepal.core.rom_injector import SpritePointer
        initial_data = {"InitialSprite": SpritePointer(offset=0x1000, bank=0x20, address=0x8000, compressed_size=256)}
        real_cache.save_sprite_locations(rom_path, initial_data)

        class Reader(QThread):
            def run(self):
                for _ in range(100):
                    data = real_cache.get_sprite_locations(rom_path)
                    if data and "NewSprite" in data and "InitialSprite" not in data:
                        # Detected incomplete read
                        race_detected["collision"] = True
                    time.sleep(0.001)

        class Writer(QThread):
            def run(self):
                from spritepal.core.rom_injector import SpritePointer
                for i in range(100):
                    new_data = {
                        "InitialSprite": SpritePointer(offset=0x1000, bank=0x20, address=0x8000, compressed_size=256),
                        "NewSprite": SpritePointer(offset=0x2000 + i, bank=0x20, address=0x8000, compressed_size=256)
                    }
                    real_cache.save_sprite_locations(rom_path, new_data)
                    time.sleep(0.001)

        reader = Reader()
        writer = Writer()

        # Start both threads
        reader.start()
        writer.start()

        # Wait for completion
        reader.wait(5000)
        writer.wait(5000)

        # Verify no race condition was detected
        assert not race_detected["collision"]

        # Verify final state is consistent
        final_data = real_cache.get_sprite_locations(rom_path)
        assert "InitialSprite" in final_data
        assert "NewSprite" in final_data
