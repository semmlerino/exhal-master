"""Comprehensive tests for ROM cache functionality."""

import json
import os
import tempfile
import time
from pathlib import Path
from unittest.mock import patch

import pytest

from spritepal.core.rom_injector import SpritePointer
from spritepal.utils.rom_cache import ROMCache, get_rom_cache


class TestROMCacheCore:
    """Test core ROMCache functionality."""

    @pytest.fixture
    def temp_cache_dir(self):
        """Create a temporary cache directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    @pytest.fixture
    def test_rom_file(self, tmp_path):
        """Create a test ROM file."""
        rom_file = tmp_path / "test.sfc"
        rom_file.write_bytes(b"TEST_ROM_DATA" * 1000)  # ~13KB test ROM
        return str(rom_file)

    @pytest.fixture
    def rom_cache(self, temp_cache_dir):
        """Create a ROMCache instance with temp directory."""
        # Create cache with explicit directory
        return ROMCache(cache_dir=temp_cache_dir)

    @pytest.fixture
    def mock_settings_manager(self, temp_cache_dir):
        """Create a mock settings manager that returns cache settings."""
        class MockSettingsManager:
            def get_cache_enabled(self) -> bool:
                return True

            def get_cache_location(self):
                return temp_cache_dir

            def get_cache_expiration_days(self) -> int:
                return 30

        return MockSettingsManager()

    def test_initialization_with_custom_dir(self, temp_cache_dir) -> None:
        """Test cache initialization with custom directory."""
        cache = ROMCache(cache_dir=temp_cache_dir)
        assert cache.cache_dir == Path(temp_cache_dir)
        assert cache.cache_enabled is True

    def test_initialization_with_settings_manager(self, temp_cache_dir, mock_settings_manager) -> None:
        """Test cache initialization using settings manager."""
        with patch("spritepal.utils.rom_cache.get_settings_manager", return_value=mock_settings_manager):
            cache = ROMCache()
            assert cache.cache_dir == Path(temp_cache_dir)
            assert cache.cache_enabled is True

    def test_initialization_disabled_cache(self, temp_cache_dir) -> None:
        """Test cache initialization when caching is disabled."""
        class MockDisabledSettings:
            def get_cache_enabled(self) -> bool:
                return False

        with patch("spritepal.utils.rom_cache.get_settings_manager", return_value=MockDisabledSettings()):
            cache = ROMCache()
            assert cache.cache_enabled is False

    def test_rom_hash_generation(self, rom_cache, test_rom_file) -> None:
        """Test ROM hash generation for real files."""
        # Get hash for real file
        hash1 = rom_cache._get_rom_hash(test_rom_file)
        assert isinstance(hash1, str)
        assert len(hash1) == 64  # SHA-256 hex digest length

        # Same file should produce same hash
        hash2 = rom_cache._get_rom_hash(test_rom_file)
        assert hash1 == hash2

        # Different file should produce different hash
        hash3 = rom_cache._get_rom_hash("/non/existent/file.sfc")
        assert hash3 != hash1

    def test_cache_file_path_generation(self, rom_cache) -> None:
        """Test cache file path generation."""
        test_hash = "abcd1234" * 8  # 64 char hash

        # Test different cache types
        sprite_path = rom_cache._get_cache_file_path(test_hash, "sprite_locations")
        assert sprite_path.name == f"{test_hash}_sprite_locations.json"
        assert sprite_path.parent == rom_cache.cache_dir

        scan_path = rom_cache._get_cache_file_path(test_hash, "scan_progress_abc123")
        assert scan_path.name == f"{test_hash}_scan_progress_abc123.json"

    def test_save_and_load_sprite_locations(self, rom_cache, test_rom_file) -> None:
        """Test saving and loading sprite locations."""
        # Create test sprite locations with SpritePointer objects
        sprite_locations = {
            "kirby_idle": SpritePointer(
                offset=0x12345,
                bank=0x20,
                address=0x8000,
                compressed_size=256,
            ),
            "kirby_walk": SpritePointer(
                offset=0x23456,
                bank=0x21,
                address=0x8100,
                compressed_size=512,
                offset_variants=[0x23457, 0x23458],
            ),
        }

        # Save sprite locations
        success = rom_cache.save_sprite_locations(test_rom_file, sprite_locations)
        assert success is True

        # Load sprite locations
        loaded = rom_cache.get_sprite_locations(test_rom_file)
        assert loaded is not None
        assert len(loaded) == 2

        # Verify SpritePointer objects were restored correctly
        assert isinstance(loaded["kirby_idle"], SpritePointer)
        assert loaded["kirby_idle"].offset == 0x12345
        assert loaded["kirby_idle"].bank == 0x20
        assert loaded["kirby_idle"].compressed_size == 256

        assert isinstance(loaded["kirby_walk"], SpritePointer)
        assert loaded["kirby_walk"].offset == 0x23456
        assert loaded["kirby_walk"].offset_variants == [0x23457, 0x23458]

    def test_save_sprite_locations_with_rom_header(self, rom_cache, test_rom_file) -> None:
        """Test saving sprite locations with ROM header info."""
        sprite_locations = {"test_sprite": SpritePointer(offset=0x1000, bank=0x20, address=0x8000)}
        rom_header = {
            "title": "KIRBY SUPER STAR",
            "checksum": 0x1234,
            "rom_size": 0x400000,
        }

        # Save with header
        success = rom_cache.save_sprite_locations(test_rom_file, sprite_locations, rom_header)
        assert success is True

        # Verify cache file contains header info
        rom_hash = rom_cache._get_rom_hash(test_rom_file)
        cache_file = rom_cache._get_cache_file_path(rom_hash, "sprite_locations")

        with open(cache_file) as f:
            cache_data = json.load(f)

        assert "rom_header" in cache_data
        assert cache_data["rom_header"]["title"] == "KIRBY SUPER STAR"

    def test_cache_expiration(self, rom_cache, test_rom_file) -> None:
        """Test cache expiration logic."""
        # Save sprite locations
        sprite_locations = {"test": SpritePointer(offset=0x1000, bank=0x20, address=0x8000)}
        rom_cache.save_sprite_locations(test_rom_file, sprite_locations)

        # Should be valid immediately
        loaded = rom_cache.get_sprite_locations(test_rom_file)
        assert loaded is not None

        # Modify cache file to be old
        rom_hash = rom_cache._get_rom_hash(test_rom_file)
        cache_file = rom_cache._get_cache_file_path(rom_hash, "sprite_locations")

        # Set modification time to 31 days ago (past default 30 day expiration)
        old_time = time.time() - (31 * 24 * 3600)
        os.utime(cache_file, (old_time, old_time))

        # Should now be expired
        loaded = rom_cache.get_sprite_locations(test_rom_file)
        assert loaded is None

    def test_cache_invalidation_on_rom_modification(self, rom_cache, test_rom_file) -> None:
        """Test cache invalidation when ROM file is modified."""
        # Save sprite locations
        sprite_locations = {"test": SpritePointer(offset=0x1000, bank=0x20, address=0x8000)}
        rom_cache.save_sprite_locations(test_rom_file, sprite_locations)

        # Should be valid
        loaded = rom_cache.get_sprite_locations(test_rom_file)
        assert loaded is not None

        # Wait a moment then modify ROM file
        time.sleep(0.1)
        with open(test_rom_file, "ab") as f:
            f.write(b"MODIFIED")

        # Cache should be invalidated
        loaded = rom_cache.get_sprite_locations(test_rom_file)
        assert loaded is None

    def test_partial_scan_results(self, rom_cache, test_rom_file) -> None:
        """Test saving and loading partial scan results."""
        scan_params = {
            "start_offset": 0xC0000,
            "end_offset": 0xF0000,
            "alignment": 0x100,
        }

        found_sprites = [
            {"offset": 0xC1000, "name": "sprite1", "size": 256},
            {"offset": 0xC2000, "name": "sprite2", "size": 512},
        ]

        # Save partial results
        success = rom_cache.save_partial_scan_results(
            test_rom_file, scan_params, found_sprites,
            current_offset=0xC3000, completed=False,
        )
        assert success is True

        # Load partial results
        progress = rom_cache.get_partial_scan_results(test_rom_file, scan_params)
        assert progress is not None
        assert progress["found_sprites"] == found_sprites
        assert progress["current_offset"] == 0xC3000
        assert progress["completed"] is False
        assert progress["total_found"] == 2

    def test_partial_scan_completed(self, rom_cache, test_rom_file) -> None:
        """Test marking scan as completed."""
        scan_params = {
            "start_offset": 0xC0000,
            "end_offset": 0xF0000,
            "alignment": 0x100,
        }

        found_sprites = [
            {"offset": 0xC1000, "name": "sprite1"},
            {"offset": 0xC2000, "name": "sprite2"},
            {"offset": 0xC3000, "name": "sprite3"},
        ]

        # Save completed scan
        success = rom_cache.save_partial_scan_results(
            test_rom_file, scan_params, found_sprites,
            current_offset=0xF0000, completed=True,
        )
        assert success is True

        # Verify completed status
        progress = rom_cache.get_partial_scan_results(test_rom_file, scan_params)
        assert progress["completed"] is True
        assert progress["current_offset"] == 0xF0000
        assert len(progress["found_sprites"]) == 3

    def test_scan_id_generation(self, rom_cache) -> None:
        """Test unique scan ID generation from parameters."""
        # Same parameters should produce same ID
        params1 = {"start_offset": 0xC0000, "end_offset": 0xF0000, "alignment": 0x100}
        params2 = {"start_offset": 0xC0000, "end_offset": 0xF0000, "alignment": 0x100}

        id1 = rom_cache._get_scan_id(params1)
        id2 = rom_cache._get_scan_id(params2)
        assert id1 == id2
        assert len(id1) == 16  # Truncated hash

        # Different parameters should produce different ID
        params3 = {"start_offset": 0xD0000, "end_offset": 0xF0000, "alignment": 0x100}
        id3 = rom_cache._get_scan_id(params3)
        assert id3 != id1

    def test_cache_stats(self, rom_cache, test_rom_file) -> None:
        """Test cache statistics gathering."""
        # Empty cache stats
        stats = rom_cache.get_cache_stats()
        assert stats["total_files"] == 0
        assert stats["cache_enabled"] is True
        assert stats["cache_dir_exists"] is True

        # Add some cache entries
        rom_cache.save_sprite_locations(test_rom_file, {"test": SpritePointer(offset=0x1000, bank=0x20, address=0x8000)})
        rom_cache.save_rom_info(test_rom_file, {"title": "TEST ROM"})
        rom_cache.save_partial_scan_results(
            test_rom_file,
            {"start_offset": 0xC0000, "end_offset": 0xF0000},
            [{"offset": 0xC1000}],
            0xC2000,
        )

        # Check updated stats
        stats = rom_cache.get_cache_stats()
        assert stats["total_files"] == 3
        assert stats["sprite_location_caches"] == 1
        assert stats["rom_info_caches"] == 1
        assert stats["scan_progress_caches"] == 1
        assert stats["total_size_bytes"] > 0

    def test_clear_cache_all(self, rom_cache, test_rom_file) -> None:
        """Test clearing all cache files."""
        # Add cache entries
        rom_cache.save_sprite_locations(test_rom_file, {"test": SpritePointer(offset=0x1000, bank=0x20, address=0x8000)})
        rom_cache.save_rom_info(test_rom_file, {"title": "TEST"})

        # Clear all
        removed = rom_cache.clear_cache()
        assert removed == 2

        # Verify cache is empty
        stats = rom_cache.get_cache_stats()
        assert stats["total_files"] == 0

    def test_clear_cache_by_age(self, rom_cache, test_rom_file) -> None:
        """Test clearing old cache files only."""
        # Create two cache files
        rom_cache.save_sprite_locations(test_rom_file, {"test1": SpritePointer(offset=0x1000, bank=0x20, address=0x8000)})
        rom_cache.save_rom_info(test_rom_file, {"title": "TEST"})

        # Make one file old
        rom_hash = rom_cache._get_rom_hash(test_rom_file)
        old_file = rom_cache._get_cache_file_path(rom_hash, "sprite_locations")
        old_time = time.time() - (10 * 24 * 3600)  # 10 days old
        os.utime(old_file, (old_time, old_time))

        # Clear files older than 5 days
        removed = rom_cache.clear_cache(older_than_days=5)
        assert removed == 1

        # Verify only old file was removed
        stats = rom_cache.get_cache_stats()
        assert stats["total_files"] == 1
        assert stats["rom_info_caches"] == 1
        assert stats["sprite_location_caches"] == 0

    def test_clear_scan_progress_specific(self, rom_cache, test_rom_file) -> None:
        """Test clearing specific scan progress cache."""
        scan_params1 = {"start_offset": 0xC0000, "end_offset": 0xF0000}
        scan_params2 = {"start_offset": 0xD0000, "end_offset": 0xE0000}

        # Save two different scan caches
        rom_cache.save_partial_scan_results(test_rom_file, scan_params1, [], 0xC1000)
        rom_cache.save_partial_scan_results(test_rom_file, scan_params2, [], 0xD1000)

        # Clear specific scan
        removed = rom_cache.clear_scan_progress_cache(test_rom_file, scan_params1)
        assert removed == 1

        # Verify only one was removed
        progress1 = rom_cache.get_partial_scan_results(test_rom_file, scan_params1)
        progress2 = rom_cache.get_partial_scan_results(test_rom_file, scan_params2)
        assert progress1 is None
        assert progress2 is not None

    def test_rom_info_cache(self, rom_cache, test_rom_file) -> None:
        """Test ROM info caching."""
        rom_info = {
            "title": "KIRBY SUPER STAR",
            "checksum": 0x1234,
            "rom_size": 0x400000,
            "header_offset": 0x7FC0,
        }

        # Save ROM info
        success = rom_cache.save_rom_info(test_rom_file, rom_info)
        assert success is True

        # Load ROM info
        loaded = rom_cache.get_rom_info(test_rom_file)
        assert loaded == rom_info

    def test_cache_disabled_operations(self, temp_cache_dir) -> None:
        """Test operations when cache is disabled."""
        # Create cache with disabled setting
        class MockDisabledSettings:
            def get_cache_enabled(self) -> bool:
                return False

        with patch("spritepal.utils.rom_cache.get_settings_manager", return_value=MockDisabledSettings()):
            cache = ROMCache(cache_dir=temp_cache_dir)

            # All operations should return False/None
            assert cache.save_sprite_locations("/test.rom", {}) is False
            assert cache.get_sprite_locations("/test.rom") is None
            assert cache.save_partial_scan_results("/test.rom", {}, [], 0) is False
            assert cache.get_partial_scan_results("/test.rom", {}) is None
            assert cache.save_rom_info("/test.rom", {}) is False
            assert cache.get_rom_info("/test.rom") is None
            assert cache.clear_cache() == 0

    def test_refresh_settings(self, rom_cache) -> None:
        """Test refreshing cache settings."""
        # Create mock settings that can change
        class ChangingSettings:
            def __init__(self) -> None:
                self.enabled = True
                self.location = None

            def get_cache_enabled(self):
                return self.enabled

            def get_cache_location(self):
                return self.location

            def get_cache_expiration_days(self) -> int:
                return 30

        settings = ChangingSettings()
        rom_cache.settings_manager = settings

        # Disable cache
        settings.enabled = False
        rom_cache.refresh_settings()
        assert rom_cache.cache_enabled is False

        # Re-enable cache
        settings.enabled = True
        rom_cache.refresh_settings()
        assert rom_cache.cache_enabled is True

    def test_fallback_to_temp_directory(self) -> None:
        """Test fallback to temp directory when main directory fails."""
        # Create a ROMCache that will fail to create its directory
        # We need to make the first mkdir fail but allow the fallback
        import tempfile

        mkdir_calls = 0
        def mock_mkdir(self, *args, **kwargs) -> None:
            nonlocal mkdir_calls
            mkdir_calls += 1
            if mkdir_calls == 1:
                # First call fails (main directory)
                msg = "No permission"
                raise PermissionError(msg)
            # Second call succeeds (fallback directory)
            # Actually create the directory
            import os
            os.makedirs(str(self), exist_ok=True)

        with patch("pathlib.Path.mkdir", mock_mkdir):
            cache = ROMCache(cache_dir="/root/no_permission")
            # Should fallback to temp directory
            assert "spritepal_rom_cache" in str(cache.cache_dir)
            assert str(cache.cache_dir).startswith(tempfile.gettempdir())
            assert cache.cache_enabled is True


class TestROMCacheSingleton:
    """Test the global ROM cache singleton."""

    @pytest.fixture
    def test_rom_file(self, tmp_path):
        """Create a test ROM file."""
        rom_file = tmp_path / "test.sfc"
        rom_file.write_bytes(b"TEST_ROM_DATA" * 1000)
        return str(rom_file)

    def test_get_rom_cache_singleton(self) -> None:
        """Test that get_rom_cache returns singleton."""
        # Reset global instance
        import spritepal.utils.rom_cache
        spritepal.utils.rom_cache._rom_cache_instance = None

        # Get instance twice
        cache1 = get_rom_cache()
        cache2 = get_rom_cache()

        assert cache1 is cache2
        assert isinstance(cache1, ROMCache)

    def test_singleton_preserves_state(self, test_rom_file) -> None:
        """Test that singleton preserves state across calls."""
        import spritepal.utils.rom_cache
        spritepal.utils.rom_cache._rom_cache_instance = None

        cache1 = get_rom_cache()
        # Save some data
        cache1.save_sprite_locations(test_rom_file, {"test": SpritePointer(offset=0x1000, bank=0x20, address=0x8000)})

        cache2 = get_rom_cache()
        # Should be able to load the data
        loaded = cache2.get_sprite_locations(test_rom_file)
        assert loaded is not None
        assert "test" in loaded


class TestROMCacheIntegration:
    """Test ROM cache integration with UI components."""

    @pytest.fixture
    def test_rom_file(self, tmp_path):
        """Create a test ROM file."""
        rom_file = tmp_path / "test.sfc"
        rom_file.write_bytes(b"TEST_ROM_DATA" * 1000)
        return str(rom_file)

    def test_rom_file_widget_cache_check(self, qtbot, test_rom_file) -> None:
        """Test ROMFileWidget cache status checking."""
        from spritepal.ui.rom_extraction.widgets.rom_file_widget import ROMFileWidget

        # Create widget
        widget = ROMFileWidget()
        qtbot.addWidget(widget)

        # Set ROM path
        widget.set_rom_path(test_rom_file)

        # Initially no cache
        status = widget.get_cache_status()
        assert status["has_cache"] is False

        # Add cache data
        cache = get_rom_cache()
        cache.save_sprite_locations(test_rom_file, {
            "kirby_idle": SpritePointer(offset=0x12345, bank=0x20, address=0x8000),
            "kirby_walk": SpritePointer(offset=0x23456, bank=0x21, address=0x8100),
        })

        # Re-check cache status
        widget._check_cache_status()
        status = widget.get_cache_status()
        assert status["has_cache"] is True
        assert status["has_sprite_cache"] is True
        assert status["sprite_count"] == 2

    def test_scan_worker_cache_resume(self, qtbot, test_rom_file) -> None:
        """Test SpriteScanWorker resuming from cache."""
        from spritepal.ui.rom_extraction.workers.range_scan_worker import (
            RangeScanWorker as SpriteScanWorker,
        )

        # Pre-populate cache with partial results
        cache = get_rom_cache()
        scan_params = {
            "start_offset": 0xC0000,
            "end_offset": 0xF0000,
            "alignment": 0x100,
        }

        found_sprites = [
            {"offset": 0xC1000, "name": "cached_sprite1"},
            {"offset": 0xC2000, "name": "cached_sprite2"},
        ]

        cache.save_partial_scan_results(
            test_rom_file, scan_params, found_sprites,
            current_offset=0xC3000, completed=False,
        )

        # Create worker that should resume from cache
        # Need an extractor instance
        from spritepal.core.rom_extractor import ROMExtractor
        extractor = ROMExtractor()

        worker = SpriteScanWorker(
            test_rom_file,
            scan_params["start_offset"],
            scan_params["end_offset"],
            step_size=scan_params["alignment"],
            extractor=extractor,
        )

        # Collect signals
        found_offsets = []

        def on_sprite_found(offset, quality) -> None:
            found_offsets.append((offset, quality))

        worker.sprite_found.connect(on_sprite_found)

        # Worker should detect and use cache
        # Note: We're not running the worker here, just verifying it would use cache
        # In real usage, the worker's run() method checks cache on startup

        # Verify cache is available for the worker
        worker_cache = get_rom_cache()
        progress = worker_cache.get_partial_scan_results(test_rom_file, scan_params)
        assert progress is not None
        assert len(progress["found_sprites"]) == 2
        assert progress["current_offset"] == 0xC3000


class TestROMCacheErrorHandling:
    """Test error handling in ROM cache."""

    @pytest.fixture
    def rom_cache(self, tmp_path):
        """Create a ROMCache instance."""
        return ROMCache(cache_dir=str(tmp_path))

    @pytest.fixture
    def test_rom_file(self, tmp_path):
        """Create a test ROM file."""
        rom_file = tmp_path / "test.sfc"
        rom_file.write_bytes(b"TEST_ROM_DATA" * 1000)
        return str(rom_file)

    def test_corrupted_cache_file(self, rom_cache, test_rom_file, tmp_path) -> None:
        """Test handling of corrupted cache files."""
        # Save valid cache
        rom_cache.save_sprite_locations(test_rom_file, {"test": SpritePointer(offset=0x1000, bank=0x20, address=0x8000)})

        # Corrupt the cache file
        rom_hash = rom_cache._get_rom_hash(test_rom_file)
        cache_file = rom_cache._get_cache_file_path(rom_hash, "sprite_locations")

        with open(cache_file, "w") as f:
            f.write("{ corrupted json !!!")

        # Should return None instead of crashing
        loaded = rom_cache.get_sprite_locations(test_rom_file)
        assert loaded is None

    def test_permission_error_on_save(self, rom_cache, test_rom_file, tmp_path) -> None:
        """Test handling permission errors during save."""
        # Make cache directory read-only
        rom_cache.cache_dir.chmod(0o444)

        try:
            # Should return False instead of crashing
            success = rom_cache.save_sprite_locations(test_rom_file, {"test": SpritePointer(offset=0x1000, bank=0x20, address=0x8000)})
            assert success is False
        finally:
            # Restore permissions
            rom_cache.cache_dir.chmod(0o755)

    def test_invalid_cache_version(self, rom_cache, test_rom_file) -> None:
        """Test handling of incompatible cache versions."""
        # Save cache with wrong version
        rom_hash = rom_cache._get_rom_hash(test_rom_file)
        cache_file = rom_cache._get_cache_file_path(rom_hash, "sprite_locations")

        cache_data = {
            "version": "0.1",  # Wrong version
            "sprite_locations": {"test": {"offset": 0x1000}},
        }

        with open(cache_file, "w") as f:
            json.dump(cache_data, f)

        # Should return None for incompatible version
        loaded = rom_cache.get_sprite_locations(test_rom_file)
        assert loaded is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
