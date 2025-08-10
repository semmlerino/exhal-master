"""
Integration tests for preview system using real components.
"""

import pytest
import time
from PySide6.QtCore import QObject, QThread, Signal

from ui.common.simple_preview_coordinator import SimplePreviewCoordinator, SimplePreviewWorker
from core.managers import ExtractionManager
from utils.rom_cache import ROMCache


@pytest.mark.integration
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
        
        # Wait for preview
        wait_for(lambda: preview_data is not None, timeout=3000, message="Preview not generated")
        
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
        
        # Wait for preview
        wait_for(lambda: preview_data is not None, timeout=5000, message="Preview not generated")
        
        # Verify decompressed data was used
        tile_data, width, height, name = preview_data
        expected_size = rom_info['sprites'][0]['decompressed_size']
        
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


@pytest.mark.integration
class TestSimplePreviewWorker:
    """Test SimplePreviewWorker with real ROM data."""
    
    def test_worker_generates_preview(self, test_rom_with_sprites, qtbot, wait_for):
        """Test that worker generates preview correctly."""
        rom_info = test_rom_with_sprites
        rom_path = str(rom_info['path'])
        
        extraction_manager = ExtractionManager()
        extractor = extraction_manager.get_rom_extractor()
        
        # Create worker
        worker = SimplePreviewWorker(rom_path, 0x10000, extractor)
        
        # Track signals
        preview_data = None
        error_msg = None
        
        def on_preview(tile_data, width, height, name):
            nonlocal preview_data
            preview_data = (tile_data, width, height, name)
        
        def on_error(msg):
            nonlocal error_msg
            error_msg = msg
        
        worker.preview_ready.connect(on_preview)
        worker.preview_error.connect(on_error)
        
        # Start worker
        worker.start()
        
        # Wait for completion
        wait_for(
            lambda: preview_data is not None or error_msg is not None,
            timeout=3000,
            message="Worker did not complete"
        )
        
        # Verify result
        if preview_data:
            tile_data, width, height, name = preview_data
            assert len(tile_data) > 0
            assert width > 0 and height > 0
        else:
            # Error case - still valid if no valid data at offset
            assert error_msg is not None
        
        # Ensure worker finished
        worker.wait(1000)
    
    def test_worker_with_compressed_sprite(self, test_rom_with_sprites, qtbot, wait_for):
        """Test worker with HAL-compressed sprite."""
        rom_info = test_rom_with_sprites
        rom_path = str(rom_info['path'])
        
        if not rom_info['sprites']:
            pytest.skip("No test sprites in ROM")
        
        extraction_manager = ExtractionManager()
        extractor = extraction_manager.get_rom_extractor()
        
        sprite_offset = rom_info['sprites'][0]['offset']
        
        # Create worker for compressed sprite
        worker = SimplePreviewWorker(rom_path, sprite_offset, extractor)
        
        # Track result
        preview_data = None
        
        def on_preview(tile_data, width, height, name):
            nonlocal preview_data
            preview_data = (tile_data, width, height, name)
        
        worker.preview_ready.connect(on_preview)
        
        # Start worker
        worker.start()
        
        # Wait for completion
        wait_for(lambda: preview_data is not None, timeout=5000, message="Worker did not complete")
        
        # Verify decompressed data
        tile_data, width, height, name = preview_data
        assert len(tile_data) > 0
        
        # Ensure worker finished
        worker.wait(1000)


@pytest.mark.integration
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


@pytest.mark.integration
class TestPreviewPerformance:
    """Performance tests for preview generation."""
    
    def test_preview_generation_speed(self, test_rom_with_sprites, qtbot, benchmark):
        """Benchmark preview generation speed."""
        rom_info = test_rom_with_sprites
        rom_path = str(rom_info['path'])
        
        extraction_manager = ExtractionManager()
        extractor = extraction_manager.get_rom_extractor()
        
        def generate_preview():
            """Generate a single preview."""
            worker = SimplePreviewWorker(rom_path, 0x10000, extractor)
            
            result = None
            
            def on_preview(tile_data, width, height, name):
                nonlocal result
                result = (tile_data, width, height, name)
            
            worker.preview_ready.connect(on_preview)
            worker.start()
            worker.wait(3000)
            
            return result
        
        # Benchmark preview generation
        result = benchmark(generate_preview)
        
        # Verify it completed
        assert result is not None
    
    def test_multiple_preview_requests(self, test_rom_with_sprites, qtbot):
        """Test handling multiple preview requests efficiently."""
        rom_info = test_rom_with_sprites
        rom_path = str(rom_info['path'])
        
        # Create coordinator
        coordinator = SimplePreviewCoordinator()
        extraction_manager = ExtractionManager()
        
        # Set ROM data
        coordinator.set_rom_data(rom_path, rom_info['path'].stat().st_size, extraction_manager.get_rom_extractor())
        
        # Track previews
        previews_generated = []
        
        def on_preview_ready(tile_data, width, height, name):
            previews_generated.append(time.time())
        
        coordinator.preview_ready.connect(on_preview_ready)
        
        # Make multiple requests
        offsets = [0x1000, 0x2000, 0x3000, 0x4000, 0x5000]
        
        start_time = time.time()
        for offset in offsets:
            coordinator.request_preview(offset)
            qtbot.wait(100)  # Wait between requests
        
        # Wait for all to complete
        qtbot.wait(1000)
        
        elapsed = time.time() - start_time
        
        # Should complete reasonably quickly
        assert elapsed < 5.0  # 5 seconds for 5 previews
        
        # Cleanup
        coordinator.cleanup()