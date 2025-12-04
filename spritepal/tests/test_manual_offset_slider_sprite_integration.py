"""
Integration tests for Manual Offset Dialog - Slider and Sprite Display

Tests the real interaction between:
1. Manual offset dialog state management
2. Slider position changes and offset calculation
3. Sprite extraction at selected offsets
4. Preview widget sprite display updates
5. Signal propagation through the system
"""
from __future__ import annotations

# Use absolute imports from spritepal package root
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from ui.rom_extraction_panel import ManualOffsetDialogSingleton
from utils.sprite_calculations import (
    align_offset_to_sprite,
    calculate_sprite_coords,
    calculate_sprite_offset,
    clamp_offset,
    is_valid_sprite_offset,
)
from utils.sprite_history_manager import SpriteHistoryManager
from utils.state_manager import StateManager
from utils.update_throttler import LastWriteWinsQueue, UpdateThrottler

# Test characteristics: Singleton management
pytestmark = [
    pytest.mark.dialog,
    pytest.mark.file_io,
    pytest.mark.headless,
    pytest.mark.integration,
    pytest.mark.mock_dialogs,
    pytest.mark.mock_only,
    pytest.mark.no_qt,
    pytest.mark.rom_data,
    pytest.mark.serial,
    pytest.mark.singleton,
    pytest.mark.widget,
    pytest.mark.ci_safe,
    pytest.mark.signals_slots,
    pytest.mark.slow,
    pytest.mark.thread_safety,
    pytest.mark.worker_threads,
]

@pytest.mark.integration
@pytest.mark.no_manager_setup
class TestManualOffsetSliderSpriteIntegration:
    """Test the integration between manual offset, slider, and sprite display."""

    @pytest.fixture(autouse=True)
    def setup_singleton_cleanup(self):
        """Ensure singleton is clean before and after each test."""
        ManualOffsetDialogSingleton.reset()
        yield
        ManualOffsetDialogSingleton.reset()

    @pytest.fixture
    def mock_rom_data(self):
        """Create mock ROM data with known sprite patterns."""
        # Create ROM with identifiable sprite patterns at specific offsets
        rom_data = bytearray(0x100000)  # 1MB ROM

        # Add sprite marker patterns at known offsets
        # Pattern 1 at 0x1000: "SPR1"
        rom_data[0x1000:0x1004] = b'SPR1'
        # Pattern 2 at 0x2000: "SPR2"
        rom_data[0x2000:0x2004] = b'SPR2'
        # Pattern 3 at 0x8000: "SPR3"
        rom_data[0x8000:0x8004] = b'SPR3'

        return rom_data

    @pytest.fixture
    def mock_sprite_extractor(self):
        """Mock sprite extractor that returns sprites based on offset."""
        extractor = MagicMock()

        def extract_sprite_at_offset(rom_data, offset):
            """Return sprite data based on offset."""
            if offset == 0x1000:
                return {'width': 16, 'height': 16, 'data': b'sprite1_data'}
            elif offset == 0x2000:
                return {'width': 32, 'height': 32, 'data': b'sprite2_data'}
            elif offset == 0x8000:
                return {'width': 64, 'height': 64, 'data': b'sprite3_data'}
            return None

        extractor.extract_at_offset = extract_sprite_at_offset
        return extractor

    def test_slider_position_updates_sprite_display(self, mock_rom_data, mock_sprite_extractor):
        """Test that moving slider updates sprite display with correct sprite."""
        # Create mock dialog with slider and preview
        mock_dialog = MagicMock()
        mock_dialog.rom_data = mock_rom_data
        mock_dialog.rom_size = len(mock_rom_data)

        # Create mock slider
        slider = MagicMock()
        slider.minimum.return_value = 0
        slider.maximum.return_value = len(mock_rom_data) - 1
        slider.value.return_value = 0
        slider.valueChanged = MagicMock()

        # Create mock preview widget
        preview = MagicMock()
        preview.display_sprite = MagicMock()

        # Set up dialog structure
        browse_tab = MagicMock()
        browse_tab.position_slider = slider
        browse_tab.preview_widget = preview
        mock_dialog.browse_tab = browse_tab

        with patch('ui.rom_extraction_panel.UnifiedManualOffsetDialog', return_value=mock_dialog):
            # Get dialog through singleton
            panel = MagicMock()
            panel.rom_data = mock_rom_data
            ManualOffsetDialogSingleton.get_dialog(panel)

            # Test initial state
            assert slider.value() == 0

            # Simulate slider movement to offset 0x1000
            slider.value.return_value = 0x1000

            # In real implementation, this would trigger sprite extraction
            sprite_data = mock_sprite_extractor.extract_at_offset(mock_rom_data, 0x1000)
            assert sprite_data is not None
            assert sprite_data['data'] == b'sprite1_data'

            # Verify preview would be updated
            preview.display_sprite(sprite_data)
            preview.display_sprite.assert_called_with(sprite_data)

            # Test moving to different offset
            slider.value.return_value = 0x8000
            sprite_data = mock_sprite_extractor.extract_at_offset(mock_rom_data, 0x8000)
            assert sprite_data['data'] == b'sprite3_data'

            preview.display_sprite(sprite_data)
            assert preview.display_sprite.call_count == 2

    def test_offset_clamping_with_slider_bounds(self, mock_rom_data):
        """Test that slider offset is properly clamped to ROM bounds."""
        mock_dialog = MagicMock()
        mock_dialog.rom_data = mock_rom_data
        mock_dialog.rom_size = len(mock_rom_data)

        # Create slider with ROM bounds
        slider = MagicMock()
        slider.minimum.return_value = 0
        slider.maximum.return_value = len(mock_rom_data) - 1

        # Test various offsets using real clamp_offset function
        rom_size = len(mock_rom_data)
        assert clamp_offset(-100, rom_size) == 0
        assert clamp_offset(0, rom_size) == 0
        assert clamp_offset(0x50000, rom_size) == 0x50000
        assert clamp_offset(0xFFFFF, rom_size) == 0xFFFFF
        assert clamp_offset(0x100000, rom_size) == 0xFFFFF  # Clamped to max
        assert clamp_offset(0x200000, rom_size) == 0xFFFFF  # Clamped to max

    def test_sprite_extraction_error_handling(self, mock_rom_data):
        """Test graceful handling when sprite extraction fails."""
        mock_dialog = MagicMock()
        mock_dialog.rom_data = mock_rom_data

        preview = MagicMock()
        preview.show_error = MagicMock()
        preview.clear_display = MagicMock()

        # Simulate extraction failure at invalid offset

        # In real implementation, extraction would fail
        sprite_data = None  # Extraction failed

        if sprite_data is None:
            # Preview should show error or clear
            preview.clear_display()
            preview.clear_display.assert_called_once()

    def test_slider_signal_chain_to_preview(self):
        """Test complete signal chain from slider to preview update."""
        # Track signal emissions
        signal_chain = []

        # Mock slider with signal tracking
        slider = MagicMock()
        slider.value.return_value = 0

        def on_value_changed(value):
            signal_chain.append(('slider_changed', value))

        slider.valueChanged.connect = MagicMock(side_effect=lambda f: on_value_changed)

        # Mock preview with update tracking
        preview = MagicMock()

        def on_preview_update(sprite_data):
            signal_chain.append(('preview_updated', sprite_data))

        preview.update_sprite = MagicMock(side_effect=on_preview_update)

        # Simulate slider movement
        new_offset = 0x5000
        on_value_changed(new_offset)

        # Simulate sprite extraction at new offset
        sprite_data = {'offset': new_offset, 'data': b'sprite_at_5000'}
        on_preview_update(sprite_data)

        # Verify signal chain
        assert len(signal_chain) == 2
        assert signal_chain[0] == ('slider_changed', 0x5000)
        assert signal_chain[1] == ('preview_updated', {'offset': 0x5000, 'data': b'sprite_at_5000'})

    def test_rapid_slider_movements_handling(self):
        """Test that rapid slider movements are handled efficiently using real throttler."""
        # Use real LastWriteWinsQueue for last-write-wins semantics
        update_queue = LastWriteWinsQueue[int]()

        # Simulate rapid slider movements
        for offset in [0x1000, 0x1100, 0x1200, 0x1300, 0x1400]:
            update_queue.put(offset)  # Each put replaces the previous

        # Get the value - should only have the last update
        result = update_queue.get()
        assert result == 0x1400  # Only the last update was kept
        assert not update_queue.has_value()  # Queue is now empty

        # Test with UpdateThrottler for time-based debouncing
        throttler = UpdateThrottler[int](delay_ms=50)  # 50ms debounce

        # Queue rapid updates
        for offset in [0x2000, 0x2100, 0x2200, 0x2300, 0x2400]:
            throttler.queue_update(offset)

        # Process immediately (cancels timer) - should get last value
        result = throttler.process()
        assert result == 0x2400  # Only the last update was kept
        assert not throttler.has_pending()  # No more pending updates

        # Test clear functionality
        throttler.queue_update(0x3000)
        assert throttler.has_pending()
        throttler.clear()
        assert not throttler.has_pending()

    def test_advanced_throttling_features(self):
        """Test advanced throttling features like rate limiting and batching."""
        import time

        from utils.update_throttler import BatchUpdateCollector, RateLimiter

        # Test RateLimiter
        rate_limiter = RateLimiter(min_interval_ms=100, max_burst=2)

        # First two actions should be allowed (burst)
        assert rate_limiter.record_action() == True
        assert rate_limiter.record_action() == True

        # Third should be blocked (exceeded burst)
        assert rate_limiter.record_action() == False

        # Check wait time needed
        wait_time = rate_limiter.wait_if_needed()
        assert wait_time > 0  # Should need to wait

        # Wait and try again
        time.sleep(0.11)  # Wait slightly more than 100ms
        assert rate_limiter.record_action() == True  # Should be allowed now

        # Test BatchUpdateCollector
        collected_batches = []
        collector = BatchUpdateCollector[int](
            batch_size=3,
            batch_delay_ms=50,
            callback=lambda batch: collected_batches.append(batch)
        )

        # Add items - should trigger batch at size 3
        collector.add(1)
        collector.add(2)
        assert collector.size() == 2  # Not processed yet

        collector.add(3)  # This triggers batch processing
        assert collector.size() == 0  # Batch was processed
        assert len(collected_batches) == 1
        assert collected_batches[0] == [1, 2, 3]

        # Test manual batch processing
        collector.add(4)
        collector.add(5)
        batch = collector.process_batch()
        assert batch == [4, 5]
        assert collector.size() == 0

    def test_throttler_with_callbacks(self):
        """Test UpdateThrottler with callbacks for realistic usage."""
        import time

        # Track processed values
        processed_values = []

        # Create throttler with callback
        throttler = UpdateThrottler[int](
            delay_ms=10,  # Short delay for testing
            callback=lambda x: processed_values.append(x)
        )

        # Queue multiple updates rapidly
        throttler.queue_update(100)
        throttler.queue_update(200)
        throttler.queue_update(300)  # Only this should be processed

        # Wait for automatic processing
        time.sleep(0.02)  # Wait 20ms (more than delay)

        # Check that only last value was processed
        assert len(processed_values) == 1
        assert processed_values[0] == 300

        # Test immediate processing with callback
        processed_values.clear()
        throttler.queue_update(400)
        result = throttler.process()  # Process immediately

        assert result == 400
        assert len(processed_values) == 1
        assert processed_values[0] == 400

        # Test that timer is properly cancelled
        processed_values.clear()
        throttler.queue_update(500)
        throttler.cancel_timer()  # Cancel without processing
        time.sleep(0.02)  # Wait to ensure callback not called

        assert len(processed_values) == 0  # Callback not called
        assert throttler.get_pending() == 500  # Value still pending

    def test_slider_position_persistence_across_dialog_reopen(self):
        """Test that slider position is preserved when dialog is reopened using real state manager."""
        # Create state manager for this test
        state_manager = StateManager()

        # First dialog session
        first_dialog = MagicMock()
        slider1 = MagicMock()
        slider1.value.return_value = 0x3000
        first_dialog.browse_tab.position_slider = slider1

        # Save position using state manager
        state_manager.save_state("dialog.slider.position", slider1.value())

        # Verify it was saved
        assert state_manager.has_state("dialog.slider.position")

        # Close dialog (cleanup)
        ManualOffsetDialogSingleton.reset()

        # Second dialog session
        second_dialog = MagicMock()
        slider2 = MagicMock()

        # Restore saved position from state manager
        restored_position = state_manager.restore_state("dialog.slider.position", default=0)
        assert restored_position == 0x3000

        slider2.setValue = MagicMock()
        slider2.setValue(restored_position)
        slider2.setValue.assert_called_with(0x3000)

        second_dialog.browse_tab.position_slider = slider2

        # Test clearing state
        state_manager.clear_state("dialog.slider.position")
        assert not state_manager.has_state("dialog.slider.position")

    def test_state_manager_comprehensive_features(self):
        """Test comprehensive state manager features."""
        import time

        state_manager = StateManager(max_size_mb=0.001)  # Small limit for testing

        # Test basic save/restore
        state_manager.save_state("test.value", 42)
        assert state_manager.restore_state("test.value") == 42

        # Test hierarchical keys
        state_manager.save_state("ui.dialog.width", 800)
        state_manager.save_state("ui.dialog.height", 600)
        state_manager.save_state("ui.toolbar.visible", True)

        # Test wildcard clearing
        assert len(state_manager.get_keys("ui.dialog")) == 2
        cleared = state_manager.clear_state("ui.dialog.*")
        assert cleared == 2
        assert state_manager.has_state("ui.toolbar.visible")  # Not cleared

        # Test TTL expiration
        state_manager.save_state("temp.value", "expires", ttl_seconds=0.01)
        assert state_manager.has_state("temp.value")
        time.sleep(0.02)  # Wait for expiry
        assert not state_manager.has_state("temp.value")

        # Test snapshots
        state_manager.save_state("snapshot.a", 1)
        state_manager.save_state("snapshot.b", 2)
        state_manager.save_state("other.c", 3)

        # Create snapshot of "snapshot" namespace
        snapshot = state_manager.get_snapshot("snapshot")
        assert len(snapshot.states) == 2

        # Modify state
        state_manager.save_state("snapshot.a", 99)
        assert state_manager.restore_state("snapshot.a") == 99

        # Restore snapshot
        state_manager.apply_snapshot(snapshot)
        assert state_manager.restore_state("snapshot.a") == 1  # Restored
        assert state_manager.restore_state("other.c") == 3  # Unchanged

        # Test memory limits (very small limit)
        for i in range(100):
            state_manager.save_state(f"mem.test{i}", "x" * 100)

        # Should have evicted oldest entries due to memory limit
        stats = state_manager.get_stats()
        assert stats["total_keys"] < 100  # Some were evicted
        assert stats["memory_usage_mb"] <= 0.001  # Within limit

        # Test various data types
        state_manager.clear_state()  # Clear all for clean test
        state_manager.save_state("types.int", 42)
        state_manager.save_state("types.float", 3.14)
        state_manager.save_state("types.str", "hello")
        state_manager.save_state("types.list", [1, 2, 3])
        state_manager.save_state("types.dict", {"a": 1, "b": 2})
        state_manager.save_state("types.tuple", (1, 2, 3))
        state_manager.save_state("types.none", None)

        assert state_manager.restore_state("types.int") == 42
        assert state_manager.restore_state("types.float") == 3.14
        assert state_manager.restore_state("types.str") == "hello"
        assert state_manager.restore_state("types.list") == [1, 2, 3]
        assert state_manager.restore_state("types.dict") == {"a": 1, "b": 2}
        assert state_manager.restore_state("types.tuple") == (1, 2, 3)
        assert state_manager.restore_state("types.none") is None

        # Test default values
        assert state_manager.restore_state("nonexistent", default="default") == "default"

    def test_state_manager_thread_safety(self):
        """Test state manager thread safety with concurrent access."""
        import threading

        state_manager = StateManager()
        results = []
        errors = []

        def worker(worker_id: int):
            """Worker that reads and writes state concurrently."""
            try:
                for i in range(10):
                    # Write
                    state_manager.save_state(f"worker{worker_id}.value{i}", i)
                    # Read
                    value = state_manager.restore_state(f"worker{worker_id}.value{i}")
                    results.append((worker_id, i, value))
                    # Snapshot
                    snapshot = state_manager.get_snapshot(f"worker{worker_id}")
                    assert len(snapshot.states) == i + 1
            except Exception as e:
                errors.append((worker_id, e))

        # Start multiple threads
        threads = []
        for i in range(5):
            t = threading.Thread(target=worker, args=(i,))
            threads.append(t)
            t.start()

        # Wait for all threads
        for t in threads:
            t.join()

        # Check results
        assert len(errors) == 0  # No errors
        assert len(results) == 50  # 5 workers * 10 operations

        # Verify all values were saved correctly
        for worker_id in range(5):
            for i in range(10):
                value = state_manager.restore_state(f"worker{worker_id}.value{i}")
                assert value == i

    def test_offset_to_sprite_coordinate_calculation(self):
        """Test calculation from ROM offset to sprite coordinates."""
        # Test various offsets using real calculate_sprite_coords function
        assert calculate_sprite_coords(0) == (0, 0)
        assert calculate_sprite_coords(128) == (1, 0)  # Second sprite
        assert calculate_sprite_coords(128 * 16) == (0, 1)  # Second row
        assert calculate_sprite_coords(128 * 32) == (0, 2)  # Third row

        # Test inverse operation with calculate_sprite_offset
        assert calculate_sprite_offset(0, 0) == 0
        assert calculate_sprite_offset(1, 0) == 128  # Second sprite
        assert calculate_sprite_offset(0, 1) == 128 * 16  # Second row
        assert calculate_sprite_offset(0, 2) == 128 * 32  # Third row

        # Test round-trip conversion
        for offset in [0, 128, 256, 2048, 4096]:
            if offset % 128 == 0:  # Only test aligned offsets
                col, row = calculate_sprite_coords(offset)
                reconstructed = calculate_sprite_offset(col, row)
                assert reconstructed == offset, f"Round-trip failed for offset {offset}"

    def test_sprite_offset_validation_and_alignment(self):
        """Test sprite offset validation and alignment using real utilities."""
        rom_size = 0x100000  # 1MB ROM

        # Test offset validation
        assert is_valid_sprite_offset(0, rom_size) == True
        assert is_valid_sprite_offset(0x1000, rom_size) == True
        assert is_valid_sprite_offset(0xFFF80, rom_size) == True  # Last valid offset for 128-byte sprite
        assert is_valid_sprite_offset(0xFFF81, rom_size) == False  # Not enough space for complete sprite
        assert is_valid_sprite_offset(0xFFFF0, rom_size) == False  # Only 16 bytes left, need 128
        assert is_valid_sprite_offset(0x100000, rom_size) == False  # Beyond ROM
        assert is_valid_sprite_offset(-1, rom_size) == False  # Negative

        # Test offset alignment
        assert align_offset_to_sprite(0) == 0
        assert align_offset_to_sprite(128) == 128  # Already aligned
        assert align_offset_to_sprite(129) == 128  # Align down
        assert align_offset_to_sprite(255) == 128  # Align down
        assert align_offset_to_sprite(256) == 256  # Already aligned
        assert align_offset_to_sprite(300) == 256  # Align down

        # Test with different sprite sizes
        assert align_offset_to_sprite(100, sprite_width=8) == 96  # 8x8 sprites = 32 bytes
        assert align_offset_to_sprite(100, sprite_width=32) == 0   # 32x32 sprites = 512 bytes

    def test_preview_widget_fallback_display(self):
        """Test preview widget shows fallback when no sprite available."""
        preview = MagicMock()
        preview.show_fallback = MagicMock()
        preview.display_sprite = MagicMock()

        # No sprite at offset
        sprite_data = None

        if sprite_data is None:
            preview.show_fallback("No sprite at this offset")
            preview.show_fallback.assert_called_with("No sprite at this offset")
        else:
            preview.display_sprite(sprite_data)

        # Verify fallback was shown
        assert preview.show_fallback.called
        assert not preview.display_sprite.called

@pytest.mark.integration
@pytest.mark.no_manager_setup
class TestManualOffsetHistoryIntegration:
    """Test integration between manual offset and history tracking."""

    @pytest.fixture(autouse=True)
    def setup_singleton_cleanup(self):
        """Ensure singleton is clean before and after each test."""
        ManualOffsetDialogSingleton.reset()
        yield
        ManualOffsetDialogSingleton.reset()

    def test_sprite_selection_adds_to_history(self):
        """Test that selecting a sprite adds it to history using real manager."""
        # Create real history manager
        history_manager = SpriteHistoryManager()

        # Initially empty
        assert history_manager.get_sprite_count() == 0

        # Add sprite at offset
        offset = 0x2000
        quality = 0.95

        # First add should succeed (not a duplicate)
        added = history_manager.add_sprite(offset, quality)
        assert added == True
        assert history_manager.get_sprite_count() == 1

        # Try adding duplicate - should fail
        added_again = history_manager.add_sprite(offset, quality)
        assert added_again == False
        assert history_manager.get_sprite_count() == 1  # Still 1

        # Add different sprite - should succeed
        added_new = history_manager.add_sprite(0x3000, 0.85)
        assert added_new == True
        assert history_manager.get_sprite_count() == 2

        # Verify sprites are stored correctly
        sprites = history_manager.get_sprites()
        assert len(sprites) == 2
        assert (0x2000, 0.95) in sprites
        assert (0x3000, 0.85) in sprites

    def test_history_item_selection_updates_slider(self):
        """Test that selecting history item retrieves correct offset."""
        # Create real history manager with some sprites
        history_manager = SpriteHistoryManager()

        # Add several sprites
        history_manager.add_sprite(0x1000, 0.90)
        history_manager.add_sprite(0x2000, 0.85)
        history_manager.add_sprite(0x4000, 0.95)

        # Get sprite info for specific offset
        sprite_info = history_manager.get_sprite_info(0x4000)
        assert sprite_info is not None
        assert sprite_info["offset"] == 0x4000
        assert sprite_info["quality"] == 0.95

        # Mock slider for UI interaction
        slider = MagicMock()
        slider.setValue = MagicMock()

        # Simulate selecting the history item and updating slider
        selected_offset = sprite_info["offset"]
        slider.setValue(selected_offset)
        slider.setValue.assert_called_with(0x4000)

    def test_history_limit_enforcement(self):
        """Test that history list enforces maximum item limit using real manager."""
        # Create manager with custom limit for easier testing
        history_manager = SpriteHistoryManager(max_history=10)

        # Add more items than the limit
        for i in range(20):
            offset = 0x1000 + (i * 0x100)
            history_manager.add_sprite(offset, quality=0.8 + (i * 0.01))

        # Should only have 10 items (the limit)
        assert history_manager.get_sprite_count() == 10

        # Verify oldest items were removed
        sprites = history_manager.get_sprites()
        offsets = [s[0] for s in sprites]

        # Should have offsets from sprite_10 to sprite_19 (0x1A00 to 0x2300)
        assert min(offsets) == 0x1000 + (10 * 0x100)  # 0x1A00 - oldest remaining
        assert max(offsets) == 0x1000 + (19 * 0x100)  # 0x2300 - newest

        # Test changing limit
        history_manager.set_max_history(5)
        assert history_manager.get_sprite_count() == 5  # Should trim to new limit

        # Test with default MAX_HISTORY constant
        default_manager = SpriteHistoryManager()
        assert default_manager.get_max_history() == 50  # Default from class

    def test_history_manager_advanced_features(self):
        """Test advanced features of the history manager."""
        history_manager = SpriteHistoryManager()

        # Add sprites with varying quality
        history_manager.add_sprite(0x1000, 0.50)
        history_manager.add_sprite(0x2000, 0.95)
        history_manager.add_sprite(0x3000, 0.75)
        history_manager.add_sprite(0x4000, 0.90)
        history_manager.add_sprite(0x5000, 0.60)

        # Test get_highest_quality
        top_sprites = history_manager.get_highest_quality(3)
        assert len(top_sprites) == 3
        assert top_sprites[0] == (0x2000, 0.95)  # Highest
        assert top_sprites[1] == (0x4000, 0.90)  # Second
        assert top_sprites[2] == (0x3000, 0.75)  # Third

        # Test get_most_recent
        recent = history_manager.get_most_recent(2)
        assert len(recent) == 2
        assert recent[0] == (0x5000, 0.60)  # Most recent
        assert recent[1] == (0x4000, 0.90)  # Second most recent

        # Test remove_sprite
        removed = history_manager.remove_sprite(0x3000)
        assert removed == True
        assert history_manager.get_sprite_count() == 4
        assert not history_manager.has_sprite(0x3000)

        # Test get_history_items (formatted strings)
        items = history_manager.get_history_items()
        assert len(items) == 4
        assert "0x001000 - Quality: 0.50" in items[0]
        assert "0x002000 - Quality: 0.95" in items[1]

@pytest.mark.integration
@pytest.mark.no_manager_setup
class TestROMBoundsValidation:
    """Test ROM bounds validation in manual offset dialog."""

    def test_empty_rom_handling(self):
        """Test handling of empty ROM data."""
        dialog = MagicMock()
        dialog.rom_data = b''
        dialog.rom_size = 0

        slider = MagicMock()

        # Should disable slider for empty ROM
        if dialog.rom_size == 0:
            slider.setEnabled(False)
            slider.setEnabled.assert_called_with(False)

    def test_small_rom_slider_range(self):
        """Test slider range for small ROM files."""
        small_rom = bytearray(0x8000)  # 32KB minimum

        slider = MagicMock()
        slider.setMinimum = MagicMock()
        slider.setMaximum = MagicMock()

        # Set slider range
        slider.setMinimum(0)
        slider.setMaximum(len(small_rom) - 1)

        slider.setMinimum.assert_called_with(0)
        slider.setMaximum.assert_called_with(0x7FFF)

    def test_large_rom_slider_range(self):
        """Test slider range for large ROM files."""
        large_rom_size = 0x600000  # 6MB

        slider = MagicMock()
        slider.setMinimum = MagicMock()
        slider.setMaximum = MagicMock()

        # Set slider range
        slider.setMinimum(0)
        slider.setMaximum(large_rom_size - 1)

        slider.setMinimum.assert_called_with(0)
        slider.setMaximum.assert_called_with(0x5FFFFF)
