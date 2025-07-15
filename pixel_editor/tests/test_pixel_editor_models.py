#!/usr/bin/env python3
"""
Unit tests for pixel editor data models
Tests ImageModel, PaletteModel, and ProjectModel
"""

import json

import numpy as np
import pytest
from PIL import Image

from pixel_editor.core.pixel_editor_models import ImageModel, PaletteModel, ProjectModel


class TestImageModel:
    """Test the ImageModel class"""

    def test_initialization_default(self):
        """Test default initialization"""
        model = ImageModel()

        assert model.width == 8
        assert model.height == 8
        assert model.data.shape == (8, 8)
        assert np.all(model.data == 0)
        assert model.modified is False
        assert model.file_path is None

    def test_initialization_custom(self):
        """Test custom initialization"""
        model = ImageModel(width=16, height=24)

        assert model.width == 16
        assert model.height == 24
        assert model.data.shape == (24, 16)

    def test_post_init_data_adjustment(self):
        """Test data array adjustment in post_init"""
        # Create with mismatched data
        wrong_data = np.ones((4, 4), dtype=np.uint8)
        model = ImageModel(width=8, height=8, data=wrong_data)

        # Should create new array with correct size
        assert model.data.shape == (8, 8)
        assert np.all(model.data == 0)  # New array, not the wrong one

    def test_new_image(self):
        """Test creating new image"""
        model = ImageModel()
        model.data[0, 0] = 5  # Modify existing
        model.file_path = "old.png"

        model.new_image(32, 16)

        assert model.width == 32
        assert model.height == 16
        assert model.data.shape == (16, 32)
        assert np.all(model.data == 0)
        assert model.modified is True
        assert model.file_path is None

    def test_load_from_pil_indexed(self):
        """Test loading from PIL indexed image"""
        # Create test PIL image
        pil_img = Image.new("P", (4, 4))
        pixels = pil_img.load()
        pixels[0, 0] = 5
        pixels[1, 1] = 10

        # Add palette
        test_palette = [255, 0, 0] * 16 + [0] * (768 - 48)
        pil_img.putpalette(test_palette)

        model = ImageModel()
        metadata = model.load_from_pil(pil_img)

        assert model.width == 4
        assert model.height == 4
        assert model.data[0, 0] == 5
        assert model.data[1, 1] == 10
        assert model.modified is False
        assert metadata["palette"] == test_palette

    def test_load_from_pil_wrong_mode(self):
        """Test loading from non-indexed image raises error"""
        pil_img = Image.new("RGB", (4, 4))

        model = ImageModel()
        with pytest.raises(ValueError, match="Expected indexed image"):
            model.load_from_pil(pil_img)

    def test_to_pil_image(self):
        """Test converting to PIL image"""
        model = ImageModel(width=4, height=4)
        model.data[0, 0] = 3
        model.data[2, 2] = 7

        # Without palette
        pil_img = model.to_pil_image()
        assert pil_img.mode == "P"
        assert pil_img.size == (4, 4)
        assert pil_img.getpixel((0, 0)) == 3
        assert pil_img.getpixel((2, 2)) == 7

        # With palette - PIL expects 768 bytes (256 colors * 3 channels)
        test_palette = [(i % 256) for _ in range(3) for i in range(256)]
        pil_img = model.to_pil_image(test_palette)
        assert pil_img.getpalette()[:768] == test_palette

    def test_get_pixel(self):
        """Test getting pixel values"""
        model = ImageModel(width=8, height=8)
        model.data[3, 4] = 9

        assert model.get_pixel(4, 3) == 9
        assert model.get_pixel(0, 0) == 0

        # Out of bounds
        assert model.get_pixel(-1, 0) == 0
        assert model.get_pixel(10, 10) == 0

    def test_set_pixel(self):
        """Test setting pixel values"""
        model = ImageModel(width=8, height=8)

        # Valid set
        result = model.set_pixel(3, 4, 12)
        assert result is True
        assert model.data[4, 3] == 12
        assert model.modified is True

        # Same value (no change)
        model.modified = False
        result = model.set_pixel(3, 4, 12)
        assert result is False
        assert model.modified is False

        # Out of bounds
        result = model.set_pixel(10, 10, 5)
        assert result is False

        # Invalid color value
        result = model.set_pixel(0, 0, 20)
        assert result is False

    def test_fill_basic(self):
        """Test basic flood fill"""
        model = ImageModel(width=4, height=4)

        changed = model.fill(0, 0, 5)

        # Should fill all pixels (all were 0)
        assert len(changed) == 16
        assert np.all(model.data == 5)
        assert model.modified is True

    def test_fill_bounded(self):
        """Test flood fill with boundaries"""
        model = ImageModel(width=6, height=6)

        # Create a box with borders at rows/cols 1 and 4
        model.data[1, 1:5] = 1  # Top
        model.data[4, 1:5] = 1  # Bottom
        model.data[1:5, 1] = 1  # Left
        model.data[1:5, 4] = 1  # Right

        # Fill inside - the interior is 2x2 (rows/cols 2-3)
        changed = model.fill(3, 3, 7)

        # Check only inside filled (2x2 interior)
        assert len(changed) == 4
        assert model.data[2, 2] == 7
        assert model.data[3, 3] == 7
        assert model.data[0, 0] == 0  # Outside
        assert model.data[1, 1] == 1  # Border

    def test_fill_same_color(self):
        """Test fill with same color does nothing"""
        model = ImageModel(width=4, height=4)
        model.data.fill(3)

        changed = model.fill(0, 0, 3)

        assert len(changed) == 0
        assert np.all(model.data == 3)

    def test_fill_out_of_bounds(self):
        """Test fill with out of bounds coordinates"""
        model = ImageModel(width=4, height=4)

        changed = model.fill(10, 10, 5)
        assert len(changed) == 0

        changed = model.fill(-1, -1, 5)
        assert len(changed) == 0

    def test_fill_invalid_color(self):
        """Test fill with invalid color value"""
        model = ImageModel(width=4, height=4)

        changed = model.fill(0, 0, 20)
        assert len(changed) == 0

    def test_get_color_at(self):
        """Test color picker functionality"""
        model = ImageModel(width=4, height=4)
        model.data[2, 1] = 8

        assert model.get_color_at(1, 2) == 8
        assert model.get_color_at(0, 0) == 0
        assert model.get_color_at(10, 10) == 0  # Out of bounds


class TestPaletteModel:
    """Test the PaletteModel class"""

    def test_initialization_default(self):
        """Test default initialization"""
        model = PaletteModel()

        assert len(model.colors) == 16
        assert model.colors[0] == (0, 0, 0)
        assert model.colors[15] == (255, 255, 255)
        assert model.name == "Default"
        assert model.index == 0

    def test_initialization_custom(self):
        """Test custom initialization"""
        colors = [(255, 0, 0)] * 16
        model = PaletteModel(colors=colors, name="Red Palette", index=8)

        assert model.colors == colors
        assert model.name == "Red Palette"
        assert model.index == 8

    def test_from_rgb_list(self):
        """Test loading from RGB tuple list"""
        colors = [(255, 0, 0), (0, 255, 0), (0, 0, 255)]
        model = PaletteModel()

        model.from_rgb_list(colors)

        # Should pad with black
        assert len(model.colors) == 16
        assert model.colors[0] == (255, 0, 0)
        assert model.colors[1] == (0, 255, 0)
        assert model.colors[2] == (0, 0, 255)
        assert model.colors[3] == (0, 0, 0)  # Padded

    def test_from_rgb_list_truncate(self):
        """Test loading from too many colors"""
        colors = [(i, i, i) for i in range(20)]
        model = PaletteModel()

        model.from_rgb_list(colors)

        assert len(model.colors) == 16
        assert model.colors[15] == (15, 15, 15)

    def test_from_flat_list(self):
        """Test loading from flat list"""
        flat = [255, 0, 0, 0, 255, 0, 0, 0, 255] + [0] * 39
        model = PaletteModel()

        model.from_flat_list(flat)

        assert model.colors[0] == (255, 0, 0)
        assert model.colors[1] == (0, 255, 0)
        assert model.colors[2] == (0, 0, 255)

    def test_from_flat_list_padding(self):
        """Test flat list padding"""
        flat = [255, 128, 64]  # Only one color
        model = PaletteModel()

        model.from_flat_list(flat)

        assert model.colors[0] == (255, 128, 64)
        assert model.colors[1] == (0, 0, 0)  # Padded

    def test_to_flat_list(self):
        """Test converting to flat list"""
        model = PaletteModel()
        model.colors[0] = (255, 128, 64)

        flat = model.to_flat_list()

        # Should have 768 values (256 colors * 3)
        assert len(flat) == 768
        assert flat[0:3] == [255, 128, 64]
        assert flat[3:6] == [17, 17, 17]  # Default grayscale
        assert flat[48:] == [0] * (768 - 48)  # Padding

    def test_from_json_file_valid(self, tmp_path):
        """Test loading from valid JSON file"""
        # Create test file
        data = {
            "palette": {
                "name": "Test Palette",
                "colors": [[255, 0, 0], [0, 255, 0]] + [[0, 0, 0]] * 14,
            },
            "extra_metadata": "test",
        }

        json_path = tmp_path / "test.pal.json"
        with open(json_path, "w") as f:
            json.dump(data, f)

        model = PaletteModel()
        result = model.from_json_file(str(json_path))

        assert result is True
        assert model.name == "Test Palette"
        assert model.colors[0] == (255, 0, 0)
        assert model.colors[1] == (0, 255, 0)
        assert model.metadata == data

    def test_from_json_file_invalid(self, tmp_path):
        """Test loading from invalid JSON file"""
        # Invalid JSON
        json_path = tmp_path / "invalid.json"
        with open(json_path, "w") as f:
            f.write("not json")

        model = PaletteModel()
        result = model.from_json_file(str(json_path))
        assert result is False

        # Missing palette data
        json_path2 = tmp_path / "missing.json"
        with open(json_path2, "w") as f:
            json.dump({"no_palette": True}, f)

        result = model.from_json_file(str(json_path2))
        assert result is False

    def test_from_json_file_not_found(self):
        """Test loading from non-existent file"""
        model = PaletteModel()
        result = model.from_json_file("/does/not/exist.json")
        assert result is False

    def test_to_json_file(self, tmp_path):
        """Test saving to JSON file"""
        model = PaletteModel(name="Save Test")
        model.colors[0] = (128, 64, 32)
        model.metadata = {"custom": "data"}

        json_path = tmp_path / "output.pal.json"
        result = model.to_json_file(str(json_path))

        assert result is True
        assert json_path.exists()

        # Verify contents
        with open(json_path) as f:
            data = json.load(f)

        assert data["palette"]["name"] == "Save Test"
        assert data["palette"]["colors"][0] == [128, 64, 32]
        assert data["palette"]["format"] == "RGB888"
        assert data["custom"] == "data"

    def test_to_json_file_error(self):
        """Test saving to invalid path"""
        model = PaletteModel()
        result = model.to_json_file("/invalid/path/file.json")
        assert result is False


class TestProjectModel:
    """Test the ProjectModel class"""

    def test_initialization(self):
        """Test default initialization"""
        model = ProjectModel()

        assert model.image_path is None
        assert model.palette_path is None
        assert model.metadata_path is None
        assert model.associations == {}

    def test_associate_files(self):
        """Test associating image and palette files"""
        model = ProjectModel()

        model.associate_files("/path/image.png", "/path/palette.pal")

        assert model.associations["/path/image.png"] == "/path/palette.pal"

    def test_get_associated_palette(self):
        """Test getting associated palette"""
        model = ProjectModel()
        model.associate_files("/img1.png", "/pal1.pal")
        model.associate_files("/img2.png", "/pal2.pal")

        assert model.get_associated_palette("/img1.png") == "/pal1.pal"
        assert model.get_associated_palette("/img2.png") == "/pal2.pal"
        assert model.get_associated_palette("/img3.png") is None

    def test_get_metadata_path(self):
        """Test getting metadata file path"""
        model = ProjectModel()

        # Basic case
        path = model.get_metadata_path("/path/to/image.png")
        assert path == "/path/to/image.metadata.json"

        # Different extension
        path = model.get_metadata_path("/path/to/sprite.bmp")
        assert path == "/path/to/sprite.metadata.json"

        # No extension
        path = model.get_metadata_path("/path/to/file")
        assert path == "/path/to/file.metadata.json"

    def test_clear(self):
        """Test clearing project state"""
        model = ProjectModel()
        model.image_path = "/image.png"
        model.palette_path = "/palette.pal"
        model.metadata_path = "/meta.json"
        model.associations["test"] = "value"

        model.clear()

        assert model.image_path is None
        assert model.palette_path is None
        assert model.metadata_path is None
        assert model.associations == {"test": "value"}  # Not cleared, by design


class TestModelIntegration:
    """Integration tests for models working together"""

    def test_image_palette_roundtrip(self, tmp_path):
        """Test saving and loading image with palette"""
        # Create image
        image_model = ImageModel(width=8, height=8)
        image_model.data[0, 0] = 5
        image_model.data[7, 7] = 15

        # Create palette
        palette_model = PaletteModel(name="Test Palette")
        palette_model.colors[5] = (255, 0, 0)
        palette_model.colors[15] = (0, 0, 255)

        # Convert to PIL and save
        pil_img = image_model.to_pil_image(palette_model.to_flat_list())
        img_path = tmp_path / "test.png"
        pil_img.save(str(img_path))

        # Load back
        loaded_img = Image.open(str(img_path))
        new_image_model = ImageModel()
        metadata = new_image_model.load_from_pil(loaded_img)

        # Verify
        assert new_image_model.width == 8
        assert new_image_model.height == 8
        assert new_image_model.data[0, 0] == 5
        assert new_image_model.data[7, 7] == 15

        # Check palette preserved
        new_palette_model = PaletteModel()
        new_palette_model.from_flat_list(metadata["palette"])
        assert new_palette_model.colors[5] == (255, 0, 0)
        assert new_palette_model.colors[15] == (0, 0, 255)

    def test_project_workflow(self, tmp_path):
        """Test complete project workflow"""
        # Setup project
        project = ProjectModel()

        # Create files
        img_path = str(tmp_path / "sprite.png")
        pal_path = str(tmp_path / "sprite.pal.json")

        # Set paths
        project.image_path = img_path
        project.palette_path = pal_path
        project.associate_files(img_path, pal_path)

        # Get metadata path
        meta_path = project.get_metadata_path(img_path)
        assert meta_path == str(tmp_path / "sprite.metadata.json")

        # Verify association
        assert project.get_associated_palette(img_path) == pal_path

    def test_data_types_and_ranges(self):
        """Test data type handling and value ranges"""
        # Image data should be uint8
        image = ImageModel(width=4, height=4)
        assert image.data.dtype == np.uint8

        # Test that values are limited to uint8 range
        # For palette indices, we only use 0-15 anyway
        image.set_pixel(0, 0, 15)  # Max palette index
        assert image.data[0, 0] == 15

        # Palette colors should accept 0-255
        palette = PaletteModel()
        palette.colors[0] = (256, -1, 128)  # Should not validate here
        # Model stores as-is, validation happens elsewhere
        assert palette.colors[0] == (256, -1, 128)
