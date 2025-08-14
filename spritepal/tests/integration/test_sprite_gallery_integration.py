"""
Integration tests for sprite gallery functionality.
Tests the complete gallery system including detached windows and thumbnails.
"""

from unittest.mock import MagicMock

import pytest
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QSizePolicy

from ui.tabs.sprite_gallery_tab import SpriteGalleryTab
from ui.windows.detached_gallery_window import DetachedGalleryWindow


@pytest.fixture
def gallery_tab(qtbot):
    """Create a gallery tab for testing."""
    tab = SpriteGalleryTab()
    qtbot.addWidget(tab)

    # Setup mock ROM data
    tab.rom_path = "test_rom.smc"
    tab.rom_size = 4 * 1024 * 1024

    # Mock extractor
    tab.rom_extractor = MagicMock()
    tab.rom_extractor.rom_injector = None

    return tab


@pytest.fixture
def test_sprites():
    """Create test sprite data."""
    sprites = []
    for i in range(17):
        sprites.append({
            'offset': i * 0x1000,
            'decompressed_size': 2048,
            'tile_count': 64,
            'compressed': i % 3 == 0,
        })
    return sprites


@pytest.fixture
def gallery_with_sprites(gallery_tab, test_sprites):
    """Gallery tab with sprites loaded."""
    gallery_tab.sprites_data = test_sprites
    gallery_tab.gallery_widget.set_sprites(test_sprites)

    # Generate mock thumbnails
    for sprite in test_sprites:
        offset = sprite['offset']
        if offset in gallery_tab.gallery_widget.thumbnails:
            pixmap = QPixmap(128, 128)
            pixmap.fill(Qt.GlobalColor.darkGray)
            thumbnail = gallery_tab.gallery_widget.thumbnails[offset]
            thumbnail.set_sprite_data(pixmap, sprite)

    return gallery_tab


class TestSpriteGalleryTab:
    """Test the main sprite gallery tab."""

    @pytest.mark.gui
    def test_gallery_initialization(self, gallery_tab):
        """Test that gallery tab initializes correctly."""
        assert gallery_tab.gallery_widget is not None
        assert gallery_tab.toolbar is not None
        assert gallery_tab.info_label is not None
        assert gallery_tab.detached_window is None

    @pytest.mark.gui
    def test_set_sprites(self, gallery_tab, test_sprites, qtbot):
        """Test setting sprites in the gallery."""
        gallery_tab.sprites_data = test_sprites
        gallery_tab.gallery_widget.set_sprites(test_sprites)

        # Wait for layout update
        qtbot.wait(100)

        # Check thumbnails were created
        assert len(gallery_tab.gallery_widget.thumbnails) == 17

        # Check status label
        status_text = gallery_tab.gallery_widget.status_label.text()
        assert "17 sprites" in status_text

    @pytest.mark.gui
    def test_thumbnail_generation(self, gallery_with_sprites):
        """Test that thumbnails are generated with pixmaps."""
        gallery = gallery_with_sprites.gallery_widget

        # Check all thumbnails have pixmaps
        valid_count = 0
        for thumbnail in gallery.thumbnails.values():
            if hasattr(thumbnail, 'sprite_pixmap') and thumbnail.sprite_pixmap:
                if not thumbnail.sprite_pixmap.isNull():
                    valid_count += 1

        assert valid_count == 17, f"Expected 17 valid pixmaps, got {valid_count}"

    @pytest.mark.gui
    def test_gallery_no_stretching_embedded(self, gallery_with_sprites):
        """Test that embedded gallery doesn't stretch vertically."""
        gallery = gallery_with_sprites.gallery_widget

        # Check that setWidgetResizable is False for embedded gallery
        assert gallery.widgetResizable() == False, "Embedded gallery should have setWidgetResizable(False)"

        # Check container size policy
        container = gallery.container_widget
        assert container is not None

        policy = container.sizePolicy()
        v_policy = policy.verticalPolicy()

        # Should be Minimum to prevent expansion
        assert v_policy == QSizePolicy.Policy.Minimum, f"Container should have Minimum policy, has {v_policy.name}"


class TestDetachedGalleryWindow:
    """Test the detached gallery window functionality."""

    @pytest.mark.gui
    def test_open_detached_gallery(self, gallery_with_sprites, qtbot):
        """Test opening the detached gallery window."""
        tab = gallery_with_sprites

        # Open detached gallery
        tab._open_detached_gallery()

        # Wait for window to appear
        qtbot.wait(100)

        # Check window was created
        assert tab.detached_window is not None
        assert isinstance(tab.detached_window, DetachedGalleryWindow)

        # Check window is visible
        assert tab.detached_window.isVisible()

        # Close window
        tab.detached_window.close()

    @pytest.mark.gui
    def test_detached_gallery_thumbnails_copied(self, gallery_with_sprites, qtbot):
        """Test that thumbnails are copied to detached gallery."""
        tab = gallery_with_sprites

        # Open detached gallery
        tab._open_detached_gallery()
        qtbot.wait(100)

        detached_gallery = tab.detached_window.gallery_widget

        # Check thumbnails were copied
        assert len(detached_gallery.thumbnails) == 17

        # Check pixmaps were copied
        valid_count = 0
        for thumbnail in detached_gallery.thumbnails.values():
            if hasattr(thumbnail, 'sprite_pixmap') and thumbnail.sprite_pixmap:
                if not thumbnail.sprite_pixmap.isNull():
                    valid_count += 1

        assert valid_count == 17, f"Expected 17 copied pixmaps, got {valid_count}"

        # Close window
        tab.detached_window.close()

    @pytest.mark.gui
    def test_detached_gallery_proper_scrolling(self, gallery_with_sprites, qtbot):
        """Test that detached gallery has proper scrolling setup."""
        tab = gallery_with_sprites

        # Open detached gallery
        tab._open_detached_gallery()
        qtbot.wait(100)

        detached_gallery = tab.detached_window.gallery_widget

        # Check setWidgetResizable is True for scrolling
        assert detached_gallery.widgetResizable() == True, "Detached gallery should have setWidgetResizable(True)"

        # Check gallery fills window
        gallery_policy = detached_gallery.sizePolicy()
        v_policy = gallery_policy.verticalPolicy()
        assert v_policy == QSizePolicy.Policy.Expanding, "Detached gallery should expand vertically"

        # Check container uses Preferred policy
        if detached_gallery.container_widget:
            container_policy = detached_gallery.container_widget.sizePolicy()
            v_policy = container_policy.verticalPolicy()
            assert v_policy == QSizePolicy.Policy.Preferred, "Container should use Preferred policy"

        # Close window
        tab.detached_window.close()

    @pytest.mark.gui
    def test_detached_window_signals(self, gallery_with_sprites, qtbot):
        """Test that detached window signals are connected properly."""
        tab = gallery_with_sprites

        # Connect to sprite_selected signal
        selected_sprites = []
        tab.sprite_selected.connect(lambda offset: selected_sprites.append(offset))

        # Open detached gallery
        tab._open_detached_gallery()
        qtbot.wait(100)

        detached_gallery = tab.detached_window.gallery_widget

        # Simulate sprite selection in detached window
        if detached_gallery.thumbnails:
            first_offset = list(detached_gallery.thumbnails.keys())[0]
            detached_gallery.sprite_selected.emit(first_offset)

            # Check signal was propagated
            assert len(selected_sprites) == 1
            assert selected_sprites[0] == first_offset

        # Close window
        tab.detached_window.close()

    @pytest.mark.gui
    def test_detached_window_close_cleanup(self, gallery_with_sprites, qtbot):
        """Test that closing detached window cleans up properly."""
        tab = gallery_with_sprites

        # Open detached gallery
        tab._open_detached_gallery()
        qtbot.wait(100)

        assert tab.detached_window is not None

        # Close window
        tab.detached_window.close()
        qtbot.wait(100)

        # Trigger the close handler
        tab._on_detached_closed()

        # Check cleanup
        assert tab.detached_window is None


class TestGalleryLayoutFixes:
    """Test the layout fixes for empty space issues."""

    @pytest.mark.gui
    def test_gallery_columns_update(self, gallery_with_sprites, qtbot):
        """Test that gallery columns update based on width."""
        gallery = gallery_with_sprites.gallery_widget

        # Initial columns
        initial_columns = gallery.columns
        assert initial_columns > 0

        # Resize gallery
        gallery.resize(1200, 800)
        qtbot.wait(100)

        # Force column update
        gallery._update_columns()

        # Columns should have changed
        assert gallery.columns > 0

    @pytest.mark.gui
    def test_gallery_force_layout_update(self, gallery_with_sprites, qtbot):
        """Test force layout update method."""
        gallery = gallery_with_sprites.gallery_widget

        # Show gallery to get valid geometry
        gallery.show()
        qtbot.wait(100)

        # Force layout update
        gallery.force_layout_update()

        # Check container size was updated
        assert gallery.container_widget is not None
        assert gallery.container_widget.size().width() > 0
        assert gallery.container_widget.size().height() > 0

    @pytest.mark.gui
    def test_thumbnail_size_change(self, gallery_with_sprites, qtbot):
        """Test changing thumbnail size."""
        gallery = gallery_with_sprites.gallery_widget

        # Initial size
        assert gallery.thumbnail_size == 256

        # Change size via slider
        gallery.size_slider.setValue(512)
        qtbot.wait(100)

        # Check size updated
        assert gallery.thumbnail_size == 512
        assert gallery.size_label.text() == "512px"

        # Check thumbnails were resized
        for thumbnail in gallery.thumbnails.values():
            assert thumbnail.thumbnail_size == 512

    @pytest.mark.gui
    def test_gallery_filtering(self, gallery_with_sprites, qtbot):
        """Test gallery filtering functionality."""
        gallery = gallery_with_sprites.gallery_widget

        # Initially all visible
        visible_count = sum(1 for t in gallery.thumbnails.values() if t.isVisible())
        assert visible_count == 17

        # Apply HAL compression filter
        gallery.compressed_check.setChecked(True)
        gallery._apply_filters()
        qtbot.wait(100)

        # Only compressed sprites should be visible (every 3rd)
        visible_count = sum(1 for t in gallery.thumbnails.values() if t.isVisible())
        assert visible_count == 6  # 0, 3, 6, 9, 12, 15

        # Clear filter
        gallery.compressed_check.setChecked(False)
        gallery._apply_filters()
        qtbot.wait(100)

        # All visible again
        visible_count = sum(1 for t in gallery.thumbnails.values() if t.isVisible())
        assert visible_count == 17


class TestGalleryCaching:
    """Test gallery scan result caching."""

    @pytest.mark.gui
    def test_cache_save(self, gallery_with_sprites, tmp_path, monkeypatch):
        """Test saving scan results to cache."""
        tab = gallery_with_sprites

        # Mock cache path to use tmp directory
        def mock_cache_path(self, rom_path=None):
            return tmp_path / "test_cache.json"

        monkeypatch.setattr(SpriteGalleryTab, '_get_cache_path', mock_cache_path)

        # Save cache
        tab._save_scan_cache()

        # Check cache file exists
        cache_file = tmp_path / "test_cache.json"
        assert cache_file.exists()

        # Load and verify cache content
        import json
        with open(cache_file) as f:
            cache_data = json.load(f)

        assert cache_data['sprite_count'] == 17
        assert len(cache_data['sprites']) == 17
        assert cache_data['rom_path'] == "test_rom.smc"

    @pytest.mark.gui
    def test_cache_load(self, gallery_tab, test_sprites, tmp_path, monkeypatch):
        """Test loading scan results from cache."""
        # Mock cache path
        def mock_cache_path(self, rom_path=None):
            return tmp_path / "test_cache.json"

        monkeypatch.setattr(SpriteGalleryTab, '_get_cache_path', mock_cache_path)

        # Create cache file
        import json
        cache_data = {
            'version': 2,
            'rom_path': "test_rom.smc",
            'rom_size': 4 * 1024 * 1024,
            'sprite_count': len(test_sprites),
            'sprites': test_sprites,
            'scan_mode': 'quick',
            'timestamp': 0
        }

        cache_file = tmp_path / "test_cache.json"
        with open(cache_file, 'w') as f:
            json.dump(cache_data, f)

        # Load cache
        result = gallery_tab._load_scan_cache("test_rom.smc")

        assert result == True
        assert len(gallery_tab.sprites_data) == 17
        assert len(gallery_tab.gallery_widget.thumbnails) == 17


@pytest.mark.gui
class TestGalleryIntegration:
    """Full integration tests."""

    def test_complete_workflow(self, qtbot):
        """Test complete workflow from loading to detached window."""
        # Create gallery tab
        tab = SpriteGalleryTab()
        qtbot.addWidget(tab)

        # Set ROM data
        tab.set_rom_data("test_rom.smc", 4 * 1024 * 1024, MagicMock())

        # Create and set sprites
        sprites = []
        for i in range(10):
            sprites.append({
                'offset': i * 0x1000,
                'decompressed_size': 1024,
                'tile_count': 32,
                'compressed': i % 2 == 0,
            })

        tab.sprites_data = sprites
        tab.gallery_widget.set_sprites(sprites)

        # Generate thumbnails
        for sprite in sprites:
            offset = sprite['offset']
            if offset in tab.gallery_widget.thumbnails:
                pixmap = QPixmap(128, 128)
                pixmap.fill(Qt.GlobalColor.darkCyan)
                thumbnail = tab.gallery_widget.thumbnails[offset]
                thumbnail.set_sprite_data(pixmap, sprite)

        qtbot.wait(100)

        # Verify main gallery
        assert len(tab.gallery_widget.thumbnails) == 10

        # Open detached window
        tab._open_detached_gallery()
        qtbot.wait(100)

        # Verify detached window
        assert tab.detached_window is not None
        assert len(tab.detached_window.gallery_widget.thumbnails) == 10

        # Verify thumbnails copied
        detached_gallery = tab.detached_window.gallery_widget
        valid_count = sum(
            1 for t in detached_gallery.thumbnails.values()
            if hasattr(t, 'sprite_pixmap') and t.sprite_pixmap and not t.sprite_pixmap.isNull()
        )
        assert valid_count == 10

        # Clean up
        tab.detached_window.close()
        tab.cleanup()