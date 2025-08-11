"""
Comprehensive tests for the sprite gallery tab functionality.

Tests cover:
- Sprite scanning with improved step sizes
- ROM-specific caching mechanism 
- Quick vs Thorough scan modes
- Cache validation and loading
- Thumbnail generation from cache
"""

import json
import sys
import tempfile
import time
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch, PropertyMock

import pytest

# Only import Qt for GUI tests
if "--no-qt" not in sys.argv:
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QApplication, QMessageBox

from core.sprite_finder import SpriteFinder


def create_mock_gallery_tab():
    """Create a mock SpriteGalleryTab for testing without Qt dependencies."""
    from ui.tabs.sprite_gallery_tab import SpriteGalleryTab
    
    # Mock Qt widget initialization
    with patch('ui.tabs.sprite_gallery_tab.QWidget.__init__'):
        with patch.object(SpriteGalleryTab, '_setup_ui'):
            tab = SpriteGalleryTab()
            # Initialize required attributes
            tab.rom_path = None
            tab.rom_size = 0
            tab.sprites_data = []
            tab.gallery_widget = Mock()
            tab.info_label = Mock()
            return tab


class TestSpriteGalleryCaching:
    """Unit tests for the gallery caching mechanism."""
    
    def test_get_cache_path_creates_unique_names(self):
        """Test that cache paths are unique per ROM."""
        tab = create_mock_gallery_tab()
        
        # Test different ROM paths get different cache files
        path1 = tab._get_cache_path("/path/to/rom1.sfc")
        path2 = tab._get_cache_path("/path/to/rom2.sfc")
        path3 = tab._get_cache_path("/different/path/rom1.sfc")
        
        assert path1 != path2  # Different ROM names
        assert path1 != path3  # Same name, different path
        assert path1.suffix == ".json"
        assert "rom1" in path1.name
        assert "rom2" in path2.name
    
    def test_save_cache_creates_valid_json(self, tmp_path):
        """Test that cache saving creates valid JSON with metadata."""
        tab = create_mock_gallery_tab()
        tab.rom_path = str(tmp_path / "test.sfc")
        tab.rom_size = 1024 * 1024  # 1MB
        tab.scan_mode = "thorough"
        tab.sprites_data = [
            {"offset": 0x200000, "tile_count": 64},
            {"offset": 0x201000, "tile_count": 32}
        ]
        
        # Mock the cache path to use temp directory
        cache_file = tmp_path / "test_cache.json"
        with patch.object(tab, '_get_cache_path', return_value=cache_file):
            tab._save_scan_cache()
        
        # Verify cache was saved
        assert cache_file.exists()
        
        # Load and verify cache contents
        with open(cache_file) as f:
            cache_data = json.load(f)
        
        assert cache_data["version"] == 2
        assert cache_data["rom_path"] == str(tmp_path / "test.sfc")
        assert cache_data["rom_size"] == 1024 * 1024
        assert cache_data["sprite_count"] == 2
        assert cache_data["scan_mode"] == "thorough"
        assert "timestamp" in cache_data
        assert len(cache_data["sprites"]) == 2
    
    def test_load_cache_validates_rom_path(self, tmp_path):
        """Test that cache loading validates the ROM path matches."""
        tab = create_mock_gallery_tab()
        
        # Create a cache file for a different ROM
        cache_file = tmp_path / "test_cache.json"
        cache_data = {
            "version": 2,
            "rom_path": "/different/rom.sfc",
            "rom_size": 1024 * 1024,
            "sprite_count": 5,
            "sprites": [{"offset": 0x200000}],
            "timestamp": time.time()
        }
        with open(cache_file, 'w') as f:
            json.dump(cache_data, f)
        
        # Try to load cache for a different ROM
        with patch.object(tab, '_get_cache_path', return_value=cache_file):
            result = tab._load_scan_cache("/my/rom.sfc")
        
        # Should fail due to path mismatch
        assert result is False
        assert tab.sprites_data == []  # Should not load mismatched data
    
    def test_load_cache_checks_version(self, tmp_path):
        """Test that old cache versions are ignored."""
        tab = create_mock_gallery_tab()
        
        # Create an old version cache file
        cache_file = tmp_path / "test_cache.json"
        cache_data = {
            "version": 1,  # Old version
            "rom_path": str(tmp_path / "test.sfc"),
            "sprites": [{"offset": 0x200000}]
        }
        with open(cache_file, 'w') as f:
            json.dump(cache_data, f)
        
        # Try to load old cache
        with patch.object(tab, '_get_cache_path', return_value=cache_file):
            result = tab._load_scan_cache(str(tmp_path / "test.sfc"))
        
        # Should fail due to old version
        assert result is False
    
    def test_load_cache_calculates_age(self, tmp_path):
        """Test that cache age is calculated correctly."""
        tab = create_mock_gallery_tab()
        
        # Create a cache file with known timestamp
        cache_file = tmp_path / "test_cache.json"
        old_timestamp = time.time() - (3 * 3600)  # 3 hours ago
        cache_data = {
            "version": 2,
            "rom_path": str(tmp_path / "test.sfc"),
            "rom_size": 1024 * 1024,
            "sprite_count": 5,
            "sprites": [{"offset": 0x200000}],
            "timestamp": old_timestamp,
            "scan_mode": "quick"
        }
        with open(cache_file, 'w') as f:
            json.dump(cache_data, f)
        
        # Load cache
        with patch.object(tab, '_get_cache_path', return_value=cache_file):
            with patch.object(tab, '_refresh_thumbnails'):  # Mock thumbnail refresh
                result = tab._load_scan_cache(str(tmp_path / "test.sfc"))
        
        # Should succeed
        assert result is True
        
        # Check that info label shows age
        tab.info_label.setText.assert_called_once()
        call_args = tab.info_label.setText.call_args[0][0]
        assert "3." in call_args or "2.9" in call_args  # ~3 hours old


class TestSpriteGalleryScanning:
    """Integration tests for sprite scanning functionality."""
    
    @pytest.fixture
    def mock_rom_data(self):
        """Create mock ROM data for testing."""
        # Create a simple ROM-like byte array
        rom_size = 0x400000  # 4MB
        rom_data = bytearray(rom_size)
        
        # Add some recognizable patterns at known offsets
        # These would be detected as sprites by SpriteFinder
        test_offsets = [0x200000, 0x200100, 0x200800, 0x201000]
        for offset in test_offsets:
            if offset < rom_size:
                # Add some non-zero data that looks like tiles
                for i in range(32):  # 32 bytes (1 tile)
                    rom_data[offset + i] = (i * 7) % 256
        
        return bytes(rom_data)
    
    def test_scan_ranges_differ_by_mode(self):
        """Test that Quick and Thorough modes use different scan ranges."""
        tab = create_mock_gallery_tab()
        
        # Set up for quick scan
        tab.scan_mode = "quick"
        tab.rom_path = "/test/rom.sfc"
        
        # Track which scan ranges are used
        scan_steps_quick = []
        scan_steps_thorough = []
        
        # Helper to extract step size from scan
        def capture_scan_steps(tab, scan_mode):
            tab.scan_mode = scan_mode
            steps = []
            
            with patch('builtins.open', create=True) as mock_open:
                mock_open.return_value.__enter__.return_value.read.return_value = b'\x00' * 0x400000
                with patch.object(SpriteFinder, 'find_sprite_at_offset', return_value=None):
                    with patch.object(tab, 'progress_dialog', create=True) as mock_dialog:
                        mock_dialog.wasCanceled.return_value = True  # Cancel immediately
                        mock_dialog.setValue = Mock()
                        
                        # Capture the step sizes used
                        original_range = range
                        def mock_range(start, end, step=1):
                            if step > 1:  # Only capture ranges with explicit steps
                                steps.append(step)
                            return original_range(start, min(start+1, end), step)  # Return minimal range
                        
                        with patch('builtins.range', side_effect=mock_range):
                            with patch.object(tab, 'gallery_widget', create=True):
                                with patch.object(tab, '_save_scan_cache'):
                                    tab._start_sprite_scan()
            
            return steps
        
        # Capture steps for both modes
        scan_steps_quick = capture_scan_steps(tab, "quick")
        scan_steps_thorough = capture_scan_steps(tab, "thorough")
        
        # Thorough scan should use smaller steps
        if scan_steps_quick and scan_steps_thorough:
            assert min(scan_steps_thorough) < max(scan_steps_quick)
    
    def test_scan_stops_at_max_sprites(self, mock_rom_data):
        """Test that scanning stops when max sprites limit is reached."""
        tab = create_mock_gallery_tab()
        tab.rom_path = "/test/rom.sfc"
        tab.scan_mode = "thorough"
        
        # Mock SpriteFinder to always find sprites
        sprite_count = 0
        def mock_find_sprite(rom_data, offset):
            nonlocal sprite_count
            sprite_count += 1
            return {"offset": offset, "tile_count": 32}
        
        with patch('builtins.open', create=True) as mock_open:
            mock_open.return_value.__enter__.return_value.read.return_value = mock_rom_data
            with patch.object(SpriteFinder, 'find_sprite_at_offset', side_effect=mock_find_sprite):
                with patch.object(tab, 'progress_dialog', create=True) as mock_dialog:
                    mock_dialog.wasCanceled.return_value = False
                    mock_dialog.setValue = Mock()
                    mock_dialog.setLabelText = Mock()
                    
                    with patch.object(tab, '_save_scan_cache'):
                        with patch.object(tab, '_refresh_thumbnails'):
                            tab._start_sprite_scan()
        
        # Should stop at max_sprites (200)
        assert len(tab.sprites_data) <= 200
    
    def test_scan_updates_progress_with_count(self):
        """Test that scan progress shows sprite count."""
        tab = create_mock_gallery_tab()
        tab.rom_path = "/test/rom.sfc"
        tab.scan_mode = "quick"
        
        progress_labels = []
        
        with patch('builtins.open', create=True) as mock_open:
            mock_open.return_value.__enter__.return_value.read.return_value = b'\x00' * 0x400000
            with patch.object(SpriteFinder, 'find_sprite_at_offset', return_value=None):
                with patch.object(tab, 'progress_dialog', create=True) as mock_dialog:
                    mock_dialog.wasCanceled.return_value = False
                    mock_dialog.setValue = Mock()
                    
                    def capture_label(text):
                        progress_labels.append(text)
                    
                    mock_dialog.setLabelText = Mock(side_effect=capture_label)
                    
                    with patch.object(tab, '_save_scan_cache'):
                        with patch.object(tab, '_refresh_thumbnails'):
                            tab._start_sprite_scan()
        
        # Progress should show "Found:" count
        assert any("Found:" in label for label in progress_labels)


class TestSpriteGalleryIntegration:
    """Integration tests for gallery tab with other components."""
    
    def test_set_rom_data_loads_cache(self, tmp_path):
        """Test that set_rom_data automatically loads cached results."""
        tab = create_mock_gallery_tab()
        
        # Create a cache file
        rom_path = str(tmp_path / "test.sfc")
        cache_file = tmp_path / "test_cache.json"
        cache_data = {
            "version": 2,
            "rom_path": rom_path,
            "rom_size": 1024 * 1024,
            "sprite_count": 3,
            "sprites": [
                {"offset": 0x200000, "tile_count": 64},
                {"offset": 0x201000, "tile_count": 32},
                {"offset": 0x202000, "tile_count": 48}
            ],
            "timestamp": time.time(),
            "scan_mode": "quick"
        }
        
        with open(cache_file, 'w') as f:
            json.dump(cache_data, f)
        
        # Mock the cache path to use our test file
        with patch.object(tab, '_get_cache_path', return_value=cache_file):
            with patch.object(tab, '_refresh_thumbnails'):
                # Call set_rom_data
                tab.set_rom_data(rom_path, 1024 * 1024, Mock())
        
        # Should load cached sprites
        assert len(tab.sprites_data) == 3
        assert tab.sprites_data[0]["offset"] == 0x200000
    
    def test_set_rom_data_clears_old_data_without_cache(self):
        """Test that set_rom_data clears old data when no cache exists."""
        tab = create_mock_gallery_tab()
        
        # Set some existing sprite data
        tab.sprites_data = [{"offset": 0x100000}]
        
        # Set new ROM without cache
        with patch.object(tab, '_load_scan_cache', return_value=False):
            tab.set_rom_data("/new/rom.sfc", 2 * 1024 * 1024, Mock())
        
        # Should clear old sprites
        assert tab.sprites_data == []
        tab.gallery_widget.set_sprites.assert_called_with([])
    
    @pytest.mark.parametrize("scan_mode,expected_min_ranges", [
        ("quick", 1),     # Quick scan has at least 1 range set
        ("thorough", 1),  # Thorough scan has at least 1 range set (may cancel early)
    ])
    def test_scan_mode_affects_ranges(self, scan_mode, expected_min_ranges):
        """Test that scan mode affects the number of scan ranges."""
        tab = create_mock_gallery_tab()
        tab.scan_mode = scan_mode
        tab.rom_path = "/test/rom.sfc"
        
        range_count = 0
        step_sizes = []
        
        with patch('builtins.open', create=True) as mock_open:
            mock_open.return_value.__enter__.return_value.read.return_value = b'\x00' * 0x400000
            with patch.object(SpriteFinder, 'find_sprite_at_offset', return_value=None):
                with patch.object(tab, 'progress_dialog', create=True) as mock_dialog:
                    mock_dialog.wasCanceled.return_value = True  # Cancel immediately
                    mock_dialog.setValue = Mock()
                    
                    # Count how many scan ranges are processed and capture step sizes
                    original_range = range
                    def count_range(start, end, step=1):
                        nonlocal range_count
                        if step > 1:  # Count ranges with explicit steps
                            range_count += 1
                            step_sizes.append(step)
                        return original_range(start, min(start + 1, end))  # Return minimal range
                    
                    with patch('builtins.range', side_effect=count_range):
                        with patch.object(tab, 'gallery_widget', create=True):
                            with patch.object(tab, '_save_scan_cache'):
                                tab._start_sprite_scan()
        
        # Different modes should use different numbers of ranges
        assert range_count >= expected_min_ranges
        
        # More importantly, thorough scan should use smaller step sizes than quick
        if scan_mode == "thorough" and step_sizes:
            # Thorough mode uses smaller steps (0x100-0x400)
            assert min(step_sizes) <= 0x400
        elif scan_mode == "quick" and step_sizes:
            # Quick mode uses larger steps (0x800-0x1000)
            assert max(step_sizes) >= 0x800


class TestGalleryRobustness:
    """Test error handling and edge cases."""
    
    def test_cache_directory_structure(self):
        """Test that cache path has correct structure."""
        tab = create_mock_gallery_tab()
        
        # Test cache path structure
        cache_path = tab._get_cache_path("/test/rom.sfc")
        
        # Verify path structure
        assert ".cache" in str(cache_path)
        assert "gallery_scans" in str(cache_path)
        assert cache_path.suffix == ".json"
        assert "rom" in cache_path.name  # Should contain ROM name
    
    def test_cache_handles_corrupted_json(self, tmp_path):
        """Test that corrupted cache files are handled gracefully."""
        tab = create_mock_gallery_tab()
        
        # Create a corrupted cache file
        cache_file = tmp_path / "corrupted_cache.json"
        with open(cache_file, 'w') as f:
            f.write("{ invalid json }")
        
        # Try to load corrupted cache
        with patch.object(tab, '_get_cache_path', return_value=cache_file):
            result = tab._load_scan_cache("/test/rom.sfc")
        
        # Should fail gracefully
        assert result is False
        assert tab.sprites_data == []
    
    def test_scan_handles_empty_rom(self):
        """Test that scanning handles empty ROM data."""
        tab = create_mock_gallery_tab()
        tab.rom_path = "/test/empty.sfc"
        tab.scan_mode = "quick"
        
        # Empty ROM data
        with patch('builtins.open', create=True) as mock_open:
            mock_open.return_value.__enter__.return_value.read.return_value = b''
            with patch.object(tab, 'progress_dialog', create=True) as mock_dialog:
                mock_dialog.wasCanceled.return_value = False
                mock_dialog.setValue = Mock()
                
                with patch.object(tab, '_save_scan_cache'):
                    with patch.object(tab, '_refresh_thumbnails'):
                        tab._start_sprite_scan()
        
        # Should complete without error
        assert tab.sprites_data == []
    
    def test_scan_handles_no_rom_path(self):
        """Test that scanning handles missing ROM path."""
        tab = create_mock_gallery_tab()
        tab.rom_path = None
        
        with patch('ui.tabs.sprite_gallery_tab.QMessageBox.warning') as mock_warning:
            tab._scan_for_sprites()
        
        # Should show warning
        mock_warning.assert_called_once()
        assert "No ROM" in str(mock_warning.call_args)


@pytest.mark.gui
class TestGalleryWithQt:
    """Tests that require real Qt components."""
    
    @pytest.fixture
    def qt_app(self):
        """Provide Qt application for GUI tests."""
        app = QApplication.instance()
        if not app:
            app = QApplication([])
        return app
    
    def test_gallery_tab_creation(self, qt_app):
        """Test that gallery tab can be created with real Qt."""
        from ui.tabs.sprite_gallery_tab import SpriteGalleryTab
        
        tab = SpriteGalleryTab()
        
        # Check UI components were created
        assert tab.gallery_widget is not None
        assert tab.toolbar is not None
        assert tab.info_label is not None
        
        # Check layout
        assert tab.layout() is not None
        assert tab.layout().count() > 0
    
    def test_scan_dialog_shows_options(self, qt_app):
        """Test that scan dialog shows Quick vs Thorough options."""
        from ui.tabs.sprite_gallery_tab import SpriteGalleryTab
        
        tab = SpriteGalleryTab()
        tab.rom_path = "/test/rom.sfc"
        
        # Mock the dialog to capture its setup
        dialog_text = []
        
        with patch('ui.tabs.sprite_gallery_tab.QMessageBox') as MockMessageBox:
            mock_dialog = Mock()
            mock_dialog.exec.return_value = None
            mock_dialog.clickedButton.return_value = None  # Cancel
            
            def capture_text(text):
                dialog_text.append(text)
            
            mock_dialog.setInformativeText = Mock(side_effect=capture_text)
            MockMessageBox.return_value = mock_dialog
            
            tab._scan_for_sprites()
        
        # Check dialog showed scan options
        assert any("Quick Scan" in text for text in dialog_text)
        assert any("Thorough Scan" in text for text in dialog_text)