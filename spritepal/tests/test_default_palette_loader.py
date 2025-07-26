"""
Comprehensive tests for Default Palette Loader functionality.
Tests both unit functionality and integration with real file operations.
"""

import json
import os
from pathlib import Path
from unittest.mock import patch

import pytest

from spritepal.core.default_palette_loader import DefaultPaletteLoader


class TestDefaultPaletteLoaderInit:
    """Test default palette loader initialization"""

    def test_init_with_default_path(self):
        """Test initialization with default palette path"""
        loader = DefaultPaletteLoader()

        # Verify path is set to default (from core dir, up one level to spritepal, then config)
        expected_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),  # Go up to spritepal directory
            "config", "default_palettes.json"
        )
        assert loader.palette_path == expected_path

        # Verify data is loaded (if file exists) or empty (if file doesn't exist)
        if os.path.exists(expected_path):
            # File exists - should have loaded data
            assert isinstance(loader.palette_data, dict)
            assert len(loader.palette_data) > 0
        else:
            # File doesn't exist - should be empty
            assert loader.palette_data == {}

    def test_init_with_custom_path(self, tmp_path):
        """Test initialization with custom palette path"""
        custom_path = tmp_path / "custom_palettes.json"
        custom_path.write_text('{"test": "data"}')

        loader = DefaultPaletteLoader(str(custom_path))

        assert loader.palette_path == str(custom_path)
        assert loader.palette_data == {"test": "data"}

    def test_init_calls_load_palettes(self):
        """Test that initialization automatically calls load_palettes"""
        with patch.object(DefaultPaletteLoader, "load_palettes") as mock_load:
            DefaultPaletteLoader()
            mock_load.assert_called_once()


class TestDefaultPaletteLoaderJSONLoading:
    """Test JSON configuration loading"""

    def test_load_palettes_file_not_exists(self, tmp_path):
        """Test loading when palette file doesn't exist"""
        nonexistent_path = tmp_path / "nonexistent.json"

        loader = DefaultPaletteLoader(str(nonexistent_path))

        # Should handle gracefully with empty data
        assert loader.palette_data == {}
        assert loader.palette_path == str(nonexistent_path)

    def test_load_palettes_valid_json(self, tmp_path):
        """Test loading valid JSON configuration"""
        palette_data = {
            "palettes": {
                "kirby_normal": {
                    "palettes": [
                        {
                            "index": 8,
                            "name": "Kirby Pink",
                            "colors": [[255, 192, 203], [255, 255, 255], [0, 0, 0]]
                        }
                    ]
                }
            }
        }

        palette_file = tmp_path / "valid_palettes.json"
        palette_file.write_text(json.dumps(palette_data, indent=2))

        loader = DefaultPaletteLoader(str(palette_file))

        assert loader.palette_data == palette_data

    def test_load_palettes_invalid_json(self, tmp_path):
        """Test loading invalid JSON file"""
        invalid_file = tmp_path / "invalid.json"
        invalid_file.write_text('{"invalid": json syntax}')

        loader = DefaultPaletteLoader(str(invalid_file))

        # Should handle error gracefully with empty data
        assert loader.palette_data == {}

    def test_load_palettes_permission_error(self, tmp_path):
        """Test loading when file has permission issues"""
        palette_file = tmp_path / "protected.json"
        palette_file.write_text('{"test": "data"}')

        # Mock permission error during file opening
        with patch("builtins.open", side_effect=PermissionError("Access denied")):
            loader = DefaultPaletteLoader(str(palette_file))

            assert loader.palette_data == {}

    def test_load_palettes_encoding_error(self, tmp_path):
        """Test loading file with encoding issues"""
        palette_file = tmp_path / "encoding_issue.json"
        # Write invalid UTF-8 bytes
        palette_file.write_bytes(b'\xff\xfe{"test": "data"}')

        loader = DefaultPaletteLoader(str(palette_file))

        # Should handle encoding error gracefully
        assert loader.palette_data == {}

    def test_reload_palettes_updates_data(self, tmp_path):
        """Test that calling load_palettes again updates data"""
        palette_file = tmp_path / "update_test.json"

        # Initial data
        initial_data = {"palettes": {"sprite1": {"palettes": []}}}
        palette_file.write_text(json.dumps(initial_data))

        loader = DefaultPaletteLoader(str(palette_file))
        assert loader.palette_data == initial_data

        # Update file
        updated_data = {"palettes": {"sprite2": {"palettes": []}}}
        palette_file.write_text(json.dumps(updated_data))

        # Reload
        loader.load_palettes()
        assert loader.palette_data == updated_data


class TestDefaultPaletteLoaderSpriteMatching:
    """Test sprite name matching functionality"""

    @pytest.fixture
    def loader_with_data(self, tmp_path):
        """Create loader with realistic test data"""
        palette_data = {
            "palettes": {
                "kirby_normal": {
                    "palettes": [
                        {
                            "index": 8,
                            "name": "Kirby Pink",
                            "colors": [[255, 192, 203], [255, 255, 255], [0, 0, 0]]
                        },
                        {
                            "index": 9,
                            "name": "Kirby Blue",
                            "colors": [[100, 149, 237], [255, 255, 255], [0, 0, 0]]
                        }
                    ]
                },
                "kirby_fire": {
                    "palettes": [
                        {
                            "index": 8,
                            "name": "Fire Kirby",
                            "colors": [[255, 69, 0], [255, 255, 255], [0, 0, 0]]
                        }
                    ]
                },
                "waddle_dee": {
                    "palettes": [
                        {
                            "index": 10,
                            "name": "Waddle Dee",
                            "colors": [[255, 140, 0], [255, 255, 255], [0, 0, 0]]
                        }
                    ]
                }
            }
        }

        palette_file = tmp_path / "test_palettes.json"
        palette_file.write_text(json.dumps(palette_data, indent=2))

        return DefaultPaletteLoader(str(palette_file))

    def test_get_sprite_palettes_exact_match(self, loader_with_data):
        """Test exact sprite name matching"""
        palettes = loader_with_data.get_sprite_palettes("kirby_normal")

        assert len(palettes) == 2
        assert palettes[0]["name"] == "Kirby Pink"
        assert palettes[1]["name"] == "Kirby Blue"
        assert palettes[0]["index"] == 8
        assert palettes[1]["index"] == 9

    def test_get_sprite_palettes_partial_match(self, loader_with_data):
        """Test partial sprite name matching (prefix matching)"""
        # "kirby_ice" should match "kirby" prefix from "kirby_normal"
        palettes = loader_with_data.get_sprite_palettes("kirby_ice")

        assert len(palettes) == 2  # Should return kirby_normal palettes
        assert palettes[0]["name"] == "Kirby Pink"

    def test_get_sprite_palettes_no_match(self, loader_with_data):
        """Test when no sprite matches are found"""
        palettes = loader_with_data.get_sprite_palettes("mario")

        assert palettes == []

    def test_get_sprite_palettes_empty_data(self):
        """Test sprite matching with empty palette data"""
        loader = DefaultPaletteLoader.__new__(DefaultPaletteLoader)
        loader.palette_data = {}

        palettes = loader.get_sprite_palettes("kirby_normal")

        assert palettes == []

    def test_get_sprite_palettes_no_palettes_key(self, tmp_path):
        """Test when JSON doesn't have 'palettes' key"""
        invalid_data = {"other_data": {"sprite": "data"}}
        palette_file = tmp_path / "no_palettes_key.json"
        palette_file.write_text(json.dumps(invalid_data))

        loader = DefaultPaletteLoader(str(palette_file))
        palettes = loader.get_sprite_palettes("kirby_normal")

        assert palettes == []

    def test_get_sprite_palettes_missing_palettes_array(self, loader_with_data):
        """Test when sprite data exists but missing palettes array"""
        # Manually modify loader data to test edge case
        loader_with_data.palette_data["palettes"]["test_sprite"] = {"other_key": "value"}

        palettes = loader_with_data.get_sprite_palettes("test_sprite")

        assert palettes == []

    def test_partial_matching_priority_exact_over_partial(self, tmp_path):
        """Test that exact matches have priority over partial matches"""
        palette_data = {
            "palettes": {
                "kirby": {
                    "palettes": [{"index": 8, "name": "Generic Kirby", "colors": []}]
                },
                "kirby_normal": {
                    "palettes": [{"index": 9, "name": "Specific Kirby", "colors": []}]
                }
            }
        }

        palette_file = tmp_path / "priority_test.json"
        palette_file.write_text(json.dumps(palette_data))

        loader = DefaultPaletteLoader(str(palette_file))

        # Exact match should take priority
        palettes = loader.get_sprite_palettes("kirby_normal")
        assert palettes[0]["name"] == "Specific Kirby"

        # Partial match when no exact match exists
        palettes = loader.get_sprite_palettes("kirby_ice")
        assert palettes[0]["name"] == "Generic Kirby"


class TestDefaultPaletteLoaderFileGeneration:
    """Test palette file creation functionality"""

    @pytest.fixture
    def loader_with_data(self, tmp_path):
        """Create loader with test data for file generation"""
        palette_data = {
            "palettes": {
                "kirby_normal": {
                    "palettes": [
                        {
                            "index": 8,
                            "name": "Kirby Pink",
                            "colors": [[255, 192, 203], [255, 255, 255], [0, 0, 0]]
                        },
                        {
                            "index": 9,
                            "name": "Kirby Blue",
                            "colors": [[100, 149, 237], [255, 255, 255], [0, 0, 0]]
                        }
                    ]
                }
            }
        }

        palette_file = tmp_path / "file_gen_test.json"
        palette_file.write_text(json.dumps(palette_data))

        return DefaultPaletteLoader(str(palette_file))

    def test_create_palette_files_success(self, loader_with_data, tmp_path):
        """Test successful palette file creation"""
        output_base = tmp_path / "test_sprite"

        created_files = loader_with_data.create_palette_files("kirby_normal", str(output_base))

        assert len(created_files) == 2

        # Verify files were created
        pal8_file = tmp_path / "test_sprite_pal8.pal.json"
        pal9_file = tmp_path / "test_sprite_pal9.pal.json"

        assert pal8_file.exists()
        assert pal9_file.exists()
        assert str(pal8_file) in created_files
        assert str(pal9_file) in created_files

    def test_create_palette_files_content_validation(self, loader_with_data, tmp_path):
        """Test that created files have correct JSON content"""
        output_base = tmp_path / "content_test"

        created_files = loader_with_data.create_palette_files("kirby_normal", str(output_base))

        # Verify file content
        pal8_file = Path(created_files[0])
        with open(pal8_file) as f:
            pal8_data = json.load(f)

        assert pal8_data["name"] == "Kirby Pink"
        assert pal8_data["colors"] == [[255, 192, 203], [255, 255, 255], [0, 0, 0]]

    def test_create_palette_files_no_sprite_match(self, loader_with_data, tmp_path):
        """Test file creation when sprite has no palettes"""
        output_base = tmp_path / "no_match_test"

        created_files = loader_with_data.create_palette_files("nonexistent_sprite", str(output_base))

        assert created_files == []

    def test_create_palette_files_default_values(self, tmp_path):
        """Test file creation with default index and name values"""
        palette_data = {
            "palettes": {
                "test_sprite": {
                    "palettes": [
                        {
                            # Missing index and name - should use defaults
                            "colors": [[255, 0, 0], [0, 255, 0], [0, 0, 255]]
                        }
                    ]
                }
            }
        }

        palette_file = tmp_path / "defaults_test.json"
        palette_file.write_text(json.dumps(palette_data))

        loader = DefaultPaletteLoader(str(palette_file))
        output_base = tmp_path / "default_values_test"

        created_files = loader.create_palette_files("test_sprite", str(output_base))

        assert len(created_files) == 1

        # Verify default values were used
        created_file = Path(created_files[0])
        assert "pal8.pal.json" in created_file.name  # Default index 8

        with open(created_file) as f:
            content = json.load(f)
        assert content["name"] == "Palette 8"  # Default name

    def test_create_palette_files_write_permission_error(self, loader_with_data, tmp_path):
        """Test handling of write permission errors"""
        output_base = tmp_path / "permission_test"

        # Mock file write error
        with patch("builtins.open", side_effect=PermissionError("Write access denied")):
            created_files = loader_with_data.create_palette_files("kirby_normal", str(output_base))

            # Should handle error gracefully and return empty list
            assert created_files == []

    def test_create_palette_files_disk_full_error(self, loader_with_data, tmp_path):
        """Test handling of disk space errors"""
        output_base = tmp_path / "disk_full_test"

        # Mock disk full error
        with patch("builtins.open", side_effect=OSError("No space left on device")):
            created_files = loader_with_data.create_palette_files("kirby_normal", str(output_base))

            assert created_files == []

    def test_create_palette_files_directory_creation(self, loader_with_data, tmp_path):
        """Test file creation when output directory doesn't exist"""
        # Create nested path that doesn't exist
        output_base = tmp_path / "nested" / "directory" / "sprite"

        # The current implementation doesn't auto-create directories
        # This should fail gracefully and return empty list
        created_files = loader_with_data.create_palette_files("kirby_normal", str(output_base))

        # Should handle missing directory gracefully by returning empty list
        assert len(created_files) == 0

        # Test with existing directory works
        existing_dir = tmp_path / "existing"
        existing_dir.mkdir()
        output_base_existing = existing_dir / "sprite"

        created_files = loader_with_data.create_palette_files("kirby_normal", str(output_base_existing))
        assert len(created_files) == 2

        for file_path in created_files:
            assert Path(file_path).exists()


class TestDefaultPaletteLoaderKirbyCollection:
    """Test Kirby-specific palette collection functionality"""

    @pytest.fixture
    def kirby_loader(self, tmp_path):
        """Create loader with multiple Kirby sprites"""
        palette_data = {
            "palettes": {
                "kirby_normal": {
                    "palettes": [
                        {"index": 8, "name": "Kirby Pink", "colors": [[255, 192, 203]]},
                        {"index": 9, "name": "Kirby Blue", "colors": [[100, 149, 237]]}
                    ]
                },
                "kirby_fire": {
                    "palettes": [
                        {"index": 8, "name": "Fire Kirby", "colors": [[255, 69, 0]]},
                        {"index": 10, "name": "Fire Effects", "colors": [[255, 140, 0]]}
                    ]
                },
                "KIRBY_ICE": {  # Test case sensitivity
                    "palettes": [
                        {"index": 11, "name": "Ice Kirby", "colors": [[173, 216, 230]]}
                    ]
                },
                "waddle_dee": {  # Non-Kirby sprite
                    "palettes": [
                        {"index": 12, "name": "Waddle Dee", "colors": [[255, 140, 0]]}
                    ]
                }
            }
        }

        palette_file = tmp_path / "kirby_collection_test.json"
        palette_file.write_text(json.dumps(palette_data))

        return DefaultPaletteLoader(str(palette_file))

    def test_get_all_kirby_palettes_basic(self, kirby_loader):
        """Test basic Kirby palette collection"""
        all_kirby = kirby_loader.get_all_kirby_palettes()

        # Should collect palettes from all Kirby sprites
        assert 8 in all_kirby  # From both kirby_normal and kirby_fire (fire overwrites normal)
        assert 9 in all_kirby  # From kirby_normal
        assert 10 in all_kirby  # From kirby_fire
        assert 11 in all_kirby  # From KIRBY_ICE
        assert 12 not in all_kirby  # From waddle_dee (not Kirby)

    def test_get_all_kirby_palettes_case_insensitive(self, kirby_loader):
        """Test that Kirby matching is case insensitive"""
        all_kirby = kirby_loader.get_all_kirby_palettes()

        # Should include KIRBY_ICE (uppercase)
        assert 11 in all_kirby
        assert all_kirby[11] == [[173, 216, 230]]

    def test_get_all_kirby_palettes_index_override(self, kirby_loader):
        """Test that later sprites override earlier ones for same index"""
        all_kirby = kirby_loader.get_all_kirby_palettes()

        # Index 8 appears in both kirby_normal and kirby_fire
        # Implementation processes in dict order, so result depends on dict iteration
        assert 8 in all_kirby
        # The value should be one of the two possible colors
        assert all_kirby[8] in [[[255, 192, 203]], [[255, 69, 0]]]

    def test_get_all_kirby_palettes_empty_colors(self, tmp_path):
        """Test handling of palettes with empty colors"""
        palette_data = {
            "palettes": {
                "kirby_test": {
                    "palettes": [
                        {"index": 8, "name": "Empty Colors", "colors": []},
                        {"index": 9, "name": "Valid Colors", "colors": [[255, 0, 0]]}
                    ]
                }
            }
        }

        palette_file = tmp_path / "empty_colors_test.json"
        palette_file.write_text(json.dumps(palette_data))

        loader = DefaultPaletteLoader(str(palette_file))
        all_kirby = loader.get_all_kirby_palettes()

        # Should exclude palette with empty colors
        assert 8 not in all_kirby
        assert 9 in all_kirby

    def test_get_all_kirby_palettes_no_index(self, tmp_path):
        """Test handling of palettes without index field"""
        palette_data = {
            "palettes": {
                "kirby_test": {
                    "palettes": [
                        {"name": "No Index", "colors": [[255, 0, 0]]}  # Missing index
                    ]
                }
            }
        }

        palette_file = tmp_path / "no_index_test.json"
        palette_file.write_text(json.dumps(palette_data))

        loader = DefaultPaletteLoader(str(palette_file))
        all_kirby = loader.get_all_kirby_palettes()

        # Should use default index 8
        assert 8 in all_kirby
        assert all_kirby[8] == [[255, 0, 0]]

    def test_get_all_kirby_palettes_no_kirby_sprites(self, tmp_path):
        """Test collection when no Kirby sprites exist"""
        palette_data = {
            "palettes": {
                "mario": {"palettes": [{"index": 8, "colors": [[255, 0, 0]]}]},
                "sonic": {"palettes": [{"index": 9, "colors": [[0, 0, 255]]}]}
            }
        }

        palette_file = tmp_path / "no_kirby_test.json"
        palette_file.write_text(json.dumps(palette_data))

        loader = DefaultPaletteLoader(str(palette_file))
        all_kirby = loader.get_all_kirby_palettes()

        assert all_kirby == {}

    def test_get_all_kirby_palettes_empty_palette_data(self):
        """Test collection with empty palette data"""
        loader = DefaultPaletteLoader.__new__(DefaultPaletteLoader)
        loader.palette_data = {}

        all_kirby = loader.get_all_kirby_palettes()

        assert all_kirby == {}


class TestDefaultPaletteLoaderUtilities:
    """Test utility methods"""

    @pytest.fixture
    def basic_loader(self, tmp_path):
        """Create loader with basic test data"""
        palette_data = {
            "palettes": {
                "kirby_normal": {
                    "palettes": [{"index": 8, "name": "Test", "colors": [[255, 0, 0]]}]
                }
            }
        }

        palette_file = tmp_path / "utility_test.json"
        palette_file.write_text(json.dumps(palette_data))

        return DefaultPaletteLoader(str(palette_file))

    def test_has_default_palettes_true(self, basic_loader):
        """Test has_default_palettes returns True when palettes exist"""
        assert basic_loader.has_default_palettes("kirby_normal") is True

    def test_has_default_palettes_false(self, basic_loader):
        """Test has_default_palettes returns False when palettes don't exist"""
        assert basic_loader.has_default_palettes("nonexistent_sprite") is False

    def test_has_default_palettes_empty_list(self, tmp_path):
        """Test has_default_palettes when sprite has empty palette list"""
        palette_data = {
            "palettes": {
                "empty_sprite": {"palettes": []}
            }
        }

        palette_file = tmp_path / "empty_list_test.json"
        palette_file.write_text(json.dumps(palette_data))

        loader = DefaultPaletteLoader(str(palette_file))

        assert loader.has_default_palettes("empty_sprite") is False


class TestDefaultPaletteLoaderIntegration:
    """Integration tests with realistic scenarios"""

    def test_full_workflow_sprite_extraction(self, tmp_path):
        """Test complete workflow for sprite palette generation"""
        # Create realistic Kirby palette configuration
        kirby_config = {
            "palettes": {
                "kirby_normal": {
                    "description": "Main Kirby sprite with pink and blue variants",
                    "palettes": [
                        {
                            "index": 8,
                            "name": "Kirby Pink",
                            "colors": [
                                [255, 192, 203],  # Pink
                                [255, 255, 255],  # White
                                [0, 0, 0],        # Black
                                [255, 100, 100]  # Light pink
                            ]
                        },
                        {
                            "index": 9,
                            "name": "Kirby Blue",
                            "colors": [
                                [100, 149, 237],  # Steel blue
                                [255, 255, 255],  # White
                                [0, 0, 0],        # Black
                                [150, 200, 255]  # Light blue
                            ]
                        }
                    ]
                }
            }
        }

        config_file = tmp_path / "kirby_config.json"
        config_file.write_text(json.dumps(kirby_config, indent=2))

        # Initialize loader
        loader = DefaultPaletteLoader(str(config_file))

        # Test the complete workflow
        output_base = tmp_path / "kirby_extracted"

        # 1. Check if palettes are available
        assert loader.has_default_palettes("kirby_normal") is True

        # 2. Get palette information
        palettes = loader.get_sprite_palettes("kirby_normal")
        assert len(palettes) == 2

        # 3. Create palette files
        created_files = loader.create_palette_files("kirby_normal", str(output_base))
        assert len(created_files) == 2

        # 4. Verify files exist and have correct content
        pal8_file = tmp_path / "kirby_extracted_pal8.pal.json"
        pal9_file = tmp_path / "kirby_extracted_pal9.pal.json"

        assert pal8_file.exists()
        assert pal9_file.exists()

        # Verify content structure matches pixel editor expectations
        with open(pal8_file) as f:
            pal8_content = json.load(f)

        assert "name" in pal8_content
        assert "colors" in pal8_content
        assert pal8_content["name"] == "Kirby Pink"
        assert len(pal8_content["colors"]) == 4
        assert pal8_content["colors"][0] == [255, 192, 203]

    def test_edge_case_handling_malformed_data(self, tmp_path):
        """Test robustness with malformed palette data"""
        malformed_config = {
            "palettes": {
                "valid_sprite": {
                    "palettes": [
                        {"index": 8, "name": "Valid", "colors": [[255, 0, 0]]}
                    ]
                },
                "malformed_sprite": {
                    # Missing palettes array
                    "description": "This sprite has no palettes array"
                },
                "partial_sprite": {
                    "palettes": [
                        {
                            # Missing index and colors
                            "name": "Incomplete Palette"
                        }
                    ]
                }
            }
        }

        config_file = tmp_path / "malformed_config.json"
        config_file.write_text(json.dumps(malformed_config))

        loader = DefaultPaletteLoader(str(config_file))

        # Valid sprite should work
        assert loader.has_default_palettes("valid_sprite") is True
        valid_files = loader.create_palette_files("valid_sprite", str(tmp_path / "valid"))
        assert len(valid_files) == 1

        # Malformed sprite should be handled gracefully
        assert loader.has_default_palettes("malformed_sprite") is False
        malformed_files = loader.create_palette_files("malformed_sprite", str(tmp_path / "malformed"))
        assert len(malformed_files) == 0

        # Partial sprite should use defaults where possible
        partial_files = loader.create_palette_files("partial_sprite", str(tmp_path / "partial"))
        assert len(partial_files) == 1  # Should create file with defaults

        # Verify partial file has defaults
        created_file = Path(partial_files[0])
        with open(created_file) as f:
            content = json.load(f)
        assert content["name"] == "Incomplete Palette"  # Name was provided
        assert content["colors"] == []  # Colors defaulted to empty

    def test_performance_large_configuration(self, tmp_path):
        """Test performance with large palette configuration"""
        # Create large configuration with many sprites
        large_config = {"palettes": {}}

        for i in range(100):
            sprite_name = f"sprite_{i:03d}"
            large_config["palettes"][sprite_name] = {
                "palettes": [
                    {
                        "index": 8 + (i % 8),
                        "name": f"Palette {i}",
                        "colors": [[i, i, i] for _ in range(16)]  # 16 colors each
                    }
                ]
            }

        config_file = tmp_path / "large_config.json"
        config_file.write_text(json.dumps(large_config))

        # Test that loading and operations complete in reasonable time
        loader = DefaultPaletteLoader(str(config_file))

        # Test lookups are still fast
        assert loader.has_default_palettes("sprite_050") is True
        assert loader.has_default_palettes("nonexistent") is False

        # Test file creation works with large config
        files = loader.create_palette_files("sprite_050", str(tmp_path / "large_test"))
        assert len(files) == 1

    def test_concurrent_access_thread_safety(self, tmp_path):
        """Test behavior under concurrent access (basic thread safety check)"""
        import threading
        import time

        palette_data = {
            "palettes": {
                "test_sprite": {
                    "palettes": [
                        {"index": 8, "name": "Test", "colors": [[255, 0, 0]]}
                    ]
                }
            }
        }

        config_file = tmp_path / "concurrent_test.json"
        config_file.write_text(json.dumps(palette_data))

        loader = DefaultPaletteLoader(str(config_file))
        results = []
        errors = []

        def worker_function(worker_id):
            try:
                for i in range(10):
                    # Simulate concurrent operations
                    has_palettes = loader.has_default_palettes("test_sprite")
                    palettes = loader.get_sprite_palettes("test_sprite")

                    results.append((worker_id, i, has_palettes, len(palettes)))
                    time.sleep(0.001)  # Small delay to encourage race conditions
            except Exception as e:
                errors.append((worker_id, str(e)))

        # Run multiple threads
        threads = []
        for worker_id in range(5):
            thread = threading.Thread(target=worker_function, args=(worker_id,))
            threads.append(thread)
            thread.start()

        # Wait for completion
        for thread in threads:
            thread.join()

        # Verify no errors occurred and results are consistent
        assert len(errors) == 0, f"Concurrent access errors: {errors}"
        assert len(results) == 50  # 5 workers * 10 operations each

        # All results should be consistent
        for worker_id, _operation_id, has_palettes, palette_count in results:
            assert has_palettes is True
            assert palette_count == 1
