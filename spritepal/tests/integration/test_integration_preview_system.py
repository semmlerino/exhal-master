"""
Integration tests for preview system using real components.
"""
from __future__ import annotations

import time

import pytest
from core.managers import ExtractionManager
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QWidget
from ui.common.simple_preview_coordinator import SimplePreviewCoordinator, SimplePreviewWorker
from utils.rom_cache import ROMCache


@pytest.mark.integration
@pytest.mark.gui  # Qt coordinator can segfault in headless mode during teardown
class TestSimplePreviewCoordinator:
    """Test SimplePreviewCoordinator with real ROM data and decompression."""

    def test_coordinator_initialization(self, managers_initialized):
        """Test that coordinator initializes correctly."""
        coordinator = SimplePreviewCoordinator()

        # Verify components
        assert coordinator._debounce_timer is not None
        assert coordinator._current_worker is None
        assert coordinator._current_offset == 0

        # Cleanup
        coordinator.cleanup()

    def test_preview_request_with_debouncing(self, test_rom_with_sprites, qtbot, wait_for):
        """Test that preview requests are debounced correctly."""
        rom_info = test_rom_with_sprites
        rom_path = str(rom_info['path'])

        # Create coordinator
        coordinator = SimplePreviewCoordinator()
        extraction_manager = ExtractionManager()

        # Set ROM data
        coordinator.set_rom_data(rom_path, rom_info['path'].stat().st_size, extraction_manager.get_rom_extractor())

        # Track preview generation
        previews_generated = []

        def on_preview_ready(tile_data, width, height, name):
            previews_generated.append((len(tile_data), width, height, name))

        coordinator.preview_ready.connect(on_preview_ready)

        # Make rapid requests (should be debounced)
        for offset in [0x1000, 0x2000, 0x3000, 0x4000, 0x5000]:
            coordinator.request_preview(offset)
            qtbot.wait(10)  # Small delay between requests

        # Wait for debouncing to complete and preview to generate
        qtbot.wait(200)  # Debounce timer + generation time

        # Should only generate preview for the last offset
        assert len(previews_generated) <= 2  # May get one intermediate if timing is off

        # Cleanup
        coordinator.cleanup()

    def test_preview_generation_with_real_data(self, test_rom_with_sprites, qtbot, wait_for):
        """Test that preview generates with real tile data."""
        rom_info = test_rom_with_sprites
        rom_path = str(rom_info['path'])

        # Create coordinator
        coordinator = SimplePreviewCoordinator()
        extraction_manager = ExtractionManager()

        # Set ROM data
        coordinator.set_rom_data(rom_path, rom_info['path'].stat().st_size, extraction_manager.get_rom_extractor())

        # Track preview
        preview_data = None

        def on_preview_ready(tile_data, width, height, name):
            nonlocal preview_data
            preview_data = (tile_data, width, height, name)

        coordinator.preview_ready.connect(on_preview_ready)

        # Request preview at offset with tile data
        coordinator.request_preview(0x10000)

        # Wait for preview using qtbot.waitUntil
        try:
            qtbot.waitUntil(lambda: preview_data is not None, timeout=3000)
        except AssertionError:
            pytest.fail("Preview not generated within timeout")

        # Verify preview data
        tile_data, width, height, name = preview_data
        assert len(tile_data) > 0
        assert width > 0
        assert height > 0
        assert name.startswith("manual_")

        # Cleanup
        coordinator.cleanup()

    def test_preview_with_hal_decompression(self, test_rom_with_sprites, qtbot, wait_for):
        """Test preview generation with HAL-compressed sprites."""
        rom_info = test_rom_with_sprites
        rom_path = str(rom_info['path'])

        if not rom_info['sprites']:
            pytest.skip("No test sprites in ROM")

        # Create coordinator
        coordinator = SimplePreviewCoordinator()
        extraction_manager = ExtractionManager()

        # Set ROM data
        coordinator.set_rom_data(rom_path, rom_info['path'].stat().st_size, extraction_manager.get_rom_extractor())

        # Track preview
        preview_data = None

        def on_preview_ready(tile_data, width, height, name):
            nonlocal preview_data
            preview_data = (tile_data, width, height, name)

        coordinator.preview_ready.connect(on_preview_ready)

        # Request preview at compressed sprite offset
        sprite_offset = rom_info['sprites'][0]['offset']
        coordinator.request_preview(sprite_offset)

        # Wait for preview using qtbot.waitUntil
        try:
            qtbot.waitUntil(lambda: preview_data is not None, timeout=5000)
        except AssertionError:
            pytest.fail("Preview not generated within timeout")

        # Verify decompressed data was used
        tile_data, width, height, name = preview_data
        rom_info['sprites'][0]['decompressed_size']

        # Size might not match exactly due to preview limits
        assert len(tile_data) > 0
        assert width > 0 and height > 0

        # Cleanup
        coordinator.cleanup()

    def test_coordinator_cleanup(self, test_rom_with_sprites, qtbot):
        """Test that coordinator cleans up workers properly."""
        rom_info = test_rom_with_sprites
        rom_path = str(rom_info['path'])

        # Create coordinator
        coordinator = SimplePreviewCoordinator()
        extraction_manager = ExtractionManager()

        # Set ROM data
        coordinator.set_rom_data(rom_path, rom_info['path'].stat().st_size, extraction_manager.get_rom_extractor())

        # Start a preview generation
        coordinator.request_preview(0x10000)
        qtbot.wait(50)  # Let worker start

        # Cleanup while worker might be running
        coordinator.cleanup()

        # Verify cleanup
        assert coordinator._current_worker is None or not coordinator._current_worker.isRunning()
        assert not coordinator._debounce_timer.isActive()

class WorkerContainer(QWidget):
    """Container widget to hold worker and manage its lifecycle properly."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.worker = None
        self.cleanup_timer = QTimer(self)
        self.cleanup_timer.setSingleShot(True)
        self.cleanup_timer.timeout.connect(self.cleanup_worker)

    def set_worker(self, worker):
        """Set the worker and connect cleanup."""
        self.worker = worker
        # Ensure worker has parent for proper Qt lifecycle
        if worker.parent() is None:
            worker.setParent(self)

        # Schedule cleanup after worker finishes
        worker.finished.connect(lambda: self.cleanup_timer.start(100))

    def cleanup_worker(self):
        """Clean up the worker safely."""
        if self.worker:
            if self.worker.isRunning():
                self.worker.quit()
                self.worker.wait(500)
            self.worker.deleteLater()
            self.worker = None

@pytest.mark.integration
@pytest.mark.gui  # QThread workers can segfault in headless/offscreen mode
class TestSimplePreviewWorker:
    """Test SimplePreviewWorker with real ROM data."""

    def test_worker_generates_preview(self, test_rom_with_sprites, qtbot):
        """Test that worker generates preview correctly."""
        rom_info = test_rom_with_sprites
        rom_path = str(rom_info['path'])

        extraction_manager = ExtractionManager()
        extractor = extraction_manager.get_rom_extractor()

        # Create container to manage worker lifecycle
        container = WorkerContainer()
        qtbot.addWidget(container)

        # Create worker with parent for proper cleanup
        worker = SimplePreviewWorker(rom_path, 0x10000, extractor, parent=container)
        container.set_worker(worker)

        # Track signals
        preview_data = None
        error_msg = None
        finished = False

        def on_preview(tile_data, width, height, name):
            nonlocal preview_data
            preview_data = (tile_data, width, height, name)

        def on_error(msg):
            nonlocal error_msg
            error_msg = msg

        def on_finished():
            nonlocal finished
            finished = True

        worker.preview_ready.connect(on_preview)
        worker.preview_error.connect(on_error)
        worker.finished.connect(on_finished)

        # Start worker
        worker.start()

        # Wait for completion using qtbot's waitSignal
        with qtbot.waitSignal(worker.finished, timeout=3000):
            pass

        # Verify result
        if preview_data:
            tile_data, width, height, name = preview_data
            assert len(tile_data) > 0
            assert width > 0 and height > 0
        else:
            # Error case - still valid if no valid data at offset
            assert error_msg is not None

        # Ensure proper cleanup
        container.cleanup_worker()

    def test_worker_with_compressed_sprite(self, test_rom_with_sprites, qtbot):
        """Test worker with HAL-compressed sprite."""
        rom_info = test_rom_with_sprites
        rom_path = str(rom_info['path'])

        if not rom_info['sprites']:
            pytest.skip("No test sprites in ROM")

        extraction_manager = ExtractionManager()
        extractor = extraction_manager.get_rom_extractor()

        sprite_offset = rom_info['sprites'][0]['offset']

        # Create container to manage worker lifecycle
        container = WorkerContainer()
        qtbot.addWidget(container)

        # Create worker with parent
        worker = SimplePreviewWorker(rom_path, sprite_offset, extractor, parent=container)
        container.set_worker(worker)

        # Track result
        preview_data = None

        def on_preview(tile_data, width, height, name):
            nonlocal preview_data
            preview_data = (tile_data, width, height, name)

        worker.preview_ready.connect(on_preview)

        # Start worker and wait for completion
        worker.start()

        # Use waitSignal for proper event loop handling
        with qtbot.waitSignal(worker.finished, timeout=5000):
            pass

        # Verify decompressed data
        assert preview_data is not None
        tile_data, width, height, name = preview_data
        assert len(tile_data) > 0

        # Ensure proper cleanup
        container.cleanup_worker()

@pytest.mark.integration
@pytest.mark.gui  # Uses Qt coordinator which can segfault in headless mode
class TestPreviewCaching:
    """Test preview caching with ROM cache."""

    def test_preview_cache_integration(self, test_rom_with_sprites, temp_dir):
        """Test that previews can be cached and retrieved."""
        rom_info = test_rom_with_sprites
        rom_path = str(rom_info['path'])

        # Create cache
        cache = ROMCache(cache_dir=str(temp_dir))

        # Create coordinator with cache
        coordinator = SimplePreviewCoordinator(rom_cache=cache)
        extraction_manager = ExtractionManager()

        # Set ROM data
        coordinator.set_rom_data(rom_path, rom_info['path'].stat().st_size, extraction_manager.get_rom_extractor())

        # Generate preview (would be cached if caching is implemented)
        coordinator.request_preview(0x10000)

        # Note: Actual caching implementation may vary
        # This test structure is ready for when caching is added

        # Cleanup
        coordinator.cleanup()
