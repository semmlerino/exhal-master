#!/usr/bin/env python3
"""
Unit tests for MVC models - Fixed version based on actual implementation
Tests observable properties, data validation, and model behavior
"""

from unittest.mock import Mock, patch

import pytest

from sprite_editor.models.base_model import BaseModel, ObservableProperty
from sprite_editor.models.palette_model import PaletteModel
from sprite_editor.models.project_model import ProjectModel
from sprite_editor.models.sprite_model import SpriteModel


class TestObservableProperty:
    """Test the ObservableProperty descriptor"""

    def test_observable_property_get_set(self):
        """Test basic get/set functionality"""
        class TestModel(BaseModel):
            test_prop = ObservableProperty("initial")
            test_prop_changed = Mock()  # Add the signal manually for testing

        model = TestModel()

        # Test default value
        assert model.test_prop == "initial"

        # Test setting value
        model.test_prop = "new value"
        assert model.test_prop == "new value"

    def test_observable_property_signal_emission(self):
        """Test that property changes emit signals"""
        class TestModel(BaseModel):
            test_prop = ObservableProperty(0)
            test_prop_changed = Mock()  # Mock the signal

        model = TestModel()

        # Change the property
        model.test_prop = 42

        # Verify signal was emitted
        model.test_prop_changed.emit.assert_called_once_with(42)

    def test_observable_property_no_signal_on_same_value(self):
        """Test that setting same value doesn't emit signal"""
        class TestModel(BaseModel):
            test_prop = ObservableProperty("value")
            test_prop_changed = Mock()

        model = TestModel()

        # Set to same value
        model.test_prop = "value"

        # Signal should not be emitted
        model.test_prop_changed.emit.assert_not_called()

    def test_multiple_observable_properties(self):
        """Test model with multiple observable properties"""
        class TestModel(BaseModel):
            prop1 = ObservableProperty(1)
            prop2 = ObservableProperty("text")
            prop3 = ObservableProperty(None)

            prop1_changed = Mock()
            prop2_changed = Mock()
            prop3_changed = Mock()

        model = TestModel()

        # Test independent operation
        model.prop1 = 10
        model.prop1_changed.emit.assert_called_once_with(10)
        model.prop2_changed.emit.assert_not_called()


class TestSpriteModel:
    """Test SpriteModel functionality"""

    def test_sprite_model_initialization(self):
        """Test sprite model initializes with correct defaults"""
        model = SpriteModel()

        # Check actual properties from the implementation
        assert model.current_image is None
        assert model.vram_file == ""
        assert model.cgram_file == ""
        assert model.oam_file == ""
        assert model.extraction_offset == 0xC000
        assert model.extraction_size == 0x4000
        assert model.tiles_per_row == 16
        assert model.current_palette == 0

        # Check internal state
        assert hasattr(model, 'core')
        assert model._tile_count == 0

    def test_sprite_model_signals(self):
        """Test all sprite model signals exist"""
        model = SpriteModel()

        # Verify actual signals from implementation
        signals = [
            'current_image_changed',
            'vram_file_changed',
            'cgram_file_changed',
            'oam_file_changed',
            'extraction_offset_changed',
            'extraction_size_changed',
            'tiles_per_row_changed',
            'current_palette_changed',
            'extraction_started',
            'extraction_completed',
            'extraction_error',
            'injection_started',
            'injection_completed',
            'injection_error'
        ]

        for signal_name in signals:
            assert hasattr(
                model, signal_name), f"Missing signal: {signal_name}"

    def test_sprite_model_property_changes(self):
        """Test property changes emit correct signals"""
        model = SpriteModel()

        # Test vram_file change
        mock_handler = Mock()
        model.vram_file_changed.connect(mock_handler)

        model.vram_file = "/path/to/vram.bin"
        mock_handler.assert_called_once_with("/path/to/vram.bin")

        # Test extraction_offset change
        offset_handler = Mock()
        model.extraction_offset_changed.connect(offset_handler)

        model.extraction_offset = 0x8000
        offset_handler.assert_called_once_with(0x8000)

    def test_sprite_model_image_handling(self):
        """Test image property handling"""
        model = SpriteModel()
        mock_image = Mock()

        image_handler = Mock()
        model.current_image_changed.connect(image_handler)

        model.current_image = mock_image
        image_handler.assert_called_once_with(mock_image)

    def test_sprite_model_methods(self):
        """Test sprite model methods"""
        model = SpriteModel()

        # Test get_tile_count
        assert model.get_tile_count() == 0
        model._tile_count = 16
        assert model.get_tile_count() == 16

        # Test apply_palette (needs mock image)
        mock_image = Mock()
        mock_image.mode = 'P'
        mock_image.putpalette = Mock()
        model.current_image = mock_image
        model.cgram_file = "test.cgram"

        with patch.object(model.core, 'read_cgram_palette', return_value=[0] * 768):
            result = model.apply_palette(2)
            assert result is True
            assert model.current_palette == 2


class TestPaletteModel:
    """Test PaletteModel functionality"""

    def test_palette_model_initialization(self):
        """Test palette model initializes correctly"""
        model = PaletteModel()

        # Check actual properties
        assert model.current_palette_index == 0
        assert model.palettes_loaded is False
        assert model.active_palettes == []

        # Check internal state
        assert hasattr(model, 'core')
        assert model._palettes == []
        assert model._palette_names == {}
        assert model._oam_statistics is None

    def test_palette_model_signals(self):
        """Test palette model signals"""
        model = PaletteModel()

        signals = [
            'current_palette_index_changed',
            'palettes_loaded_changed',
            'active_palettes_changed',
            'palette_applied'
        ]

        for signal_name in signals:
            assert hasattr(
                model, signal_name), f"Missing signal: {signal_name}"

    def test_palette_methods(self):
        """Test palette model methods"""
        model = PaletteModel()

        # Test palette naming
        model.set_palette_name(0, "Sky Palette")
        assert model.get_palette_name(0) == "Sky Palette"
        assert model.get_palette_name(1) == "Palette 1"  # Default name

        # Test OAM statistics
        stats = {0: 10, 2: 5, 7: 3}
        model.set_oam_statistics(stats)
        assert model.get_oam_statistics() == stats
        assert model.active_palettes == [0, 2, 7]
        assert model.is_palette_active(2) is True
        assert model.is_palette_active(1) is False
        assert model.get_palette_usage_count(0) == 10
        assert model.get_palette_usage_count(1) == 0

    def test_apply_palette_to_image(self):
        """Test applying palette to image"""
        model = PaletteModel()

        # Set up test palette
        test_palette = [i for i in range(768)]
        model._palettes = [test_palette]

        # Create mock image - need to mock isinstance check
        from PIL import Image
        mock_image = Mock(spec=Image.Image)
        mock_image.mode = 'P'
        mock_image.putpalette = Mock()

        # Connect signal handler
        handler = Mock()
        model.palette_applied.connect(handler)

        # Apply palette
        result = model.apply_palette_to_image(mock_image, 0)

        assert result is True
        mock_image.putpalette.assert_called_once_with(test_palette)
        handler.assert_called_once_with(0)
        assert model.current_palette_index == 0


class TestProjectModel:
    """Test ProjectModel functionality"""

    def test_project_model_initialization(self):
        """Test project model initialization"""
        model = ProjectModel()

        # Check defaults based on actual implementation
        assert model.project_name == "Untitled"
        assert model.project_path == ""
        assert model.is_modified is False

        # Check for recent files tracking
        assert hasattr(model, 'recent_vram_files')
        assert hasattr(model, 'recent_cgram_files')
        assert hasattr(model, 'recent_oam_files')

    def test_project_model_signals(self):
        """Test project model signals"""
        model = ProjectModel()

        signals = [
            'project_name_changed',
            'project_path_changed',
            'is_modified_changed'
        ]

        for signal_name in signals:
            assert hasattr(
                model, signal_name), f"Missing signal: {signal_name}"

    def test_add_recent_file(self):
        """Test adding files to recent list"""
        model = ProjectModel()

        # Mock file existence check
        with patch('os.path.exists', return_value=True):
            # Add a VRAM file
            model.add_recent_file("/path/to/file1.vram", "vram")
            assert "/path/to/file1.vram" in model.recent_vram_files

            # Add a CGRAM file
            model.add_recent_file("/path/to/palette.cgram", "cgram")
            assert "/path/to/palette.cgram" in model.recent_cgram_files

    def test_recent_files_limit(self):
        """Test recent files list has a maximum size"""
        model = ProjectModel()

        # Mock file existence check
        with patch('os.path.exists', return_value=True):
            # Add many VRAM files
            for i in range(15):
                model.add_recent_file(f"/path/to/file{i}.vram", "vram")

            # Should be limited by max_recent_files
            assert len(model.recent_vram_files) <= model.max_recent_files

    def test_mark_modified(self):
        """Test project modification tracking"""
        model = ProjectModel()

        mock_handler = Mock()
        model.is_modified_changed.connect(mock_handler)

        model.mark_modified()
        assert model.is_modified is True
        mock_handler.assert_called_once_with(True)

        # Reset
        mock_handler.reset_mock()
        model.is_modified = False
        mock_handler.assert_called_once_with(False)


class TestModelInteractions:
    """Test interactions between different models"""

    def test_sprite_and_palette_coordination(self):
        """Test sprite and palette models work together"""
        sprite_model = SpriteModel()
        palette_model = PaletteModel()

        # Simulate loading related files
        sprite_model.vram_file = "/path/to/sprites.vram"
        sprite_model.cgram_file = "/path/to/palette.cgram"

        # Both should have their values set
        assert sprite_model.vram_file == "/path/to/sprites.vram"
        assert sprite_model.cgram_file == "/path/to/palette.cgram"

    def test_project_tracks_sprite_changes(self):
        """Test project model tracks when sprite data changes"""
        sprite_model = SpriteModel()
        project_model = ProjectModel()

        # Connect sprite changes to project modification
        def on_sprite_change(value):
            project_model.mark_modified()

        sprite_model.vram_file_changed.connect(on_sprite_change)
        sprite_model.extraction_offset_changed.connect(on_sprite_change)

        # Change sprite data
        sprite_model.vram_file = "/new/file.vram"

        # Project should be marked as modified
        assert project_model.is_modified is True


class TestModelValidation:
    """Test model data validation"""

    def test_file_path_validation(self):
        """Test file path properties handle various inputs"""
        model = SpriteModel()

        # Empty path
        model.vram_file = ""
        assert model.vram_file == ""

        # Normal path
        model.vram_file = "/path/to/file.bin"
        assert model.vram_file == "/path/to/file.bin"

        # Path with spaces
        model.vram_file = "/path with spaces/file.bin"
        assert model.vram_file == "/path with spaces/file.bin"

    def test_numeric_property_validation(self):
        """Test numeric properties handle edge cases"""
        model = SpriteModel()

        # Valid values
        model.extraction_offset = 0
        assert model.extraction_offset == 0

        model.extraction_offset = 0xFFFF
        assert model.extraction_offset == 0xFFFF

        # Large values
        model.extraction_offset = 0x100000
        assert model.extraction_offset == 0x100000

        # Tiles per row
        model.tiles_per_row = 1
        assert model.tiles_per_row == 1

        model.tiles_per_row = 32
        assert model.tiles_per_row == 32


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
