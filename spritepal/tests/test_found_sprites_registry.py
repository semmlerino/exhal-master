"""Tests for the FoundSpritesRegistry component."""

import pytest

# Skip all tests in this module since the FoundSpritesRegistry component has been removed
# during the manual offset dialog consolidation cleanup
pytestmark = pytest.mark.skip(reason="FoundSpritesRegistry component removed during cleanup")


class TestFoundSpritesRegistry:
    """Test suite for FoundSpritesRegistry."""
    
    @pytest.fixture
    def mock_offset_widget(self):
        """Create a mock offset widget."""
        widget = MagicMock()
        widget.add_found_sprite = MagicMock()
        widget.get_found_sprites = MagicMock(return_value=[])
        widget.clear_history = MagicMock()
        widget.set_found_sprites = MagicMock()
        return widget
    
    @pytest.fixture
    def mock_rom_map(self):
        """Create a mock ROM map widget."""
        rom_map = MagicMock()
        rom_map.add_found_sprite = MagicMock()
        rom_map.clear_found_sprites = MagicMock()
        return rom_map
    
    @pytest.fixture
    def registry(self, mock_offset_widget, mock_rom_map):
        """Create a FoundSpritesRegistry instance."""
        return FoundSpritesRegistry(
            offset_widget=mock_offset_widget,
            rom_map=mock_rom_map
        )
    
    def test_init_requires_offset_widget(self):
        """Test that initialization requires an offset widget."""
        with pytest.raises(ValueError, match="offset_widget is required"):
            FoundSpritesRegistry(offset_widget=None)
    
    def test_add_sprite_success(self, registry, mock_offset_widget, mock_rom_map):
        """Test successfully adding a sprite."""
        sprite = FoundSprite(
            offset=0x200000,
            quality=0.9,
            timestamp=datetime.now(),
            name="test_sprite"
        )
        
        # Mock that no sprites exist yet
        mock_offset_widget.get_found_sprites.return_value = []
        
        # Add the sprite
        result = registry.add_sprite(sprite)
        
        assert result is True
        mock_offset_widget.add_found_sprite.assert_called_once_with(0x200000, 0.9)
        mock_rom_map.add_found_sprite.assert_called_once_with(0x200000, 0.9)
    
    def test_add_sprite_duplicate(self, registry, mock_offset_widget):
        """Test that adding a duplicate sprite returns False."""
        sprite = FoundSprite(
            offset=0x200000,
            quality=0.9,
            timestamp=datetime.now()
        )
        
        # Mock that sprite already exists
        mock_offset_widget.get_found_sprites.return_value = [(0x200000, 0.9)]
        
        # Try to add duplicate
        result = registry.add_sprite(sprite)
        
        assert result is False
        mock_offset_widget.add_found_sprite.assert_not_called()
    
    def test_get_sprite_found(self, registry, mock_offset_widget):
        """Test getting an existing sprite."""
        # Mock found sprites
        mock_offset_widget.get_found_sprites.return_value = [
            (0x200000, 0.9),
            (0x201000, 0.8)
        ]
        
        sprite = registry.get_sprite(0x200000)
        
        assert sprite is not None
        assert sprite.offset == 0x200000
        assert sprite.quality == 0.9
        assert sprite.name == "sprite_0x200000"
    
    def test_get_sprite_not_found(self, registry, mock_offset_widget):
        """Test getting a non-existent sprite."""
        mock_offset_widget.get_found_sprites.return_value = []
        
        sprite = registry.get_sprite(0x200000)
        
        assert sprite is None
    
    def test_get_all_sprites(self, registry, mock_offset_widget):
        """Test getting all sprites sorted by offset."""
        # Mock unsorted sprites
        mock_offset_widget.get_found_sprites.return_value = [
            (0x201000, 0.8),
            (0x200000, 0.9),
            (0x202000, 0.7)
        ]
        
        sprites = registry.get_all_sprites()
        
        assert len(sprites) == 3
        # Check they're sorted by offset
        assert sprites[0].offset == 0x200000
        assert sprites[1].offset == 0x201000
        assert sprites[2].offset == 0x202000
    
    def test_get_sprite_count(self, registry, mock_offset_widget):
        """Test getting sprite count."""
        mock_offset_widget.get_found_sprites.return_value = [
            (0x200000, 0.9),
            (0x201000, 0.8)
        ]
        
        count = registry.get_sprite_count()
        
        assert count == 2
    
    def test_clear_sprites(self, registry, mock_offset_widget, mock_rom_map):
        """Test clearing all sprites."""
        # Add clear_found_sprites attribute to mock
        mock_rom_map.clear_found_sprites = MagicMock()
        
        registry.clear_sprites()
        
        mock_offset_widget.clear_history.assert_called_once()
        mock_rom_map.clear_found_sprites.assert_called_once()
    
    def test_import_sprites(self, registry, mock_offset_widget, mock_rom_map):
        """Test importing sprites."""
        sprites = [
            FoundSprite(offset=0x200000, quality=0.9, timestamp=datetime.now()),
            FoundSprite(offset=0x201000, quality=0.8, timestamp=datetime.now())
        ]
        
        count = registry.import_sprites(sprites)
        
        assert count == 2
        mock_offset_widget.set_found_sprites.assert_called_once_with([
            (0x200000, 0.9),
            (0x201000, 0.8)
        ])
        assert mock_rom_map.add_found_sprite.call_count == 2
    
    def test_has_sprite_at(self, registry, mock_offset_widget):
        """Test checking if sprite exists at offset."""
        mock_offset_widget.get_found_sprites.return_value = [(0x200000, 0.9)]
        
        assert registry.has_sprite_at(0x200000) is True
        assert registry.has_sprite_at(0x201000) is False
    
    def test_get_sprites_in_range(self, registry, mock_offset_widget):
        """Test getting sprites within a range."""
        mock_offset_widget.get_found_sprites.return_value = [
            (0x200000, 0.9),
            (0x201000, 0.8),
            (0x202000, 0.7),
            (0x203000, 0.6)
        ]
        
        sprites = registry.get_sprites_in_range(0x201000, 0x203000)
        
        assert len(sprites) == 2
        assert sprites[0].offset == 0x201000
        assert sprites[1].offset == 0x202000
    
    def test_update_rom_map(self, registry, mock_offset_widget):
        """Test updating ROM map reference."""
        # Set up existing sprites
        mock_offset_widget.get_found_sprites.return_value = [
            (0x200000, 0.9),
            (0x201000, 0.8)
        ]
        
        # Create new ROM map
        new_rom_map = MagicMock()
        new_rom_map.add_found_sprite = MagicMock()
        
        # Update ROM map
        registry.update_rom_map(new_rom_map)
        
        # Should sync existing sprites to new map
        assert new_rom_map.add_found_sprite.call_count == 2
        new_rom_map.add_found_sprite.assert_any_call(0x200000, 0.9)
        new_rom_map.add_found_sprite.assert_any_call(0x201000, 0.8)
    
    def test_signal_emission(self, registry, mock_offset_widget, qtbot):
        """Test that signals are emitted correctly."""
        sprite = FoundSprite(
            offset=0x200000,
            quality=0.9,
            timestamp=datetime.now()
        )
        
        # Mock no existing sprites
        mock_offset_widget.get_found_sprites.return_value = []
        
        # Connect signal spy
        with qtbot.waitSignal(registry.sprite_added) as blocker:
            registry.add_sprite(sprite)
        
        # Check signal was emitted with sprite
        assert len(blocker.args) == 1
        emitted_sprite = blocker.args[0]
        assert emitted_sprite.offset == sprite.offset
        assert emitted_sprite.quality == sprite.quality