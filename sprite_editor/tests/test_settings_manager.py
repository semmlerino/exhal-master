#!/usr/bin/env python3
"""
Tests for settings manager
Tests settings persistence with minimal mocking
"""

import json
from unittest.mock import patch

import pytest

from sprite_editor.settings_manager import SettingsManager, get_settings


@pytest.fixture
def temp_settings_dir(tmp_path):
    """Create temporary directory for settings"""
    settings_dir = tmp_path / "test_settings"
    settings_dir.mkdir()
    return settings_dir


@pytest.fixture
def settings_manager(temp_settings_dir, monkeypatch):
    """Create settings manager with temporary directory"""

    # Mock the settings path to use temp directory
    def mock_get_settings_path(self):
        return temp_settings_dir / "settings.json"

    monkeypatch.setattr(SettingsManager, "_get_settings_path", mock_get_settings_path)

    # Create fresh instance
    return SettingsManager("test_app")


@pytest.mark.unit
class TestSettingsManagerInitialization:
    """Test settings manager initialization"""

    def test_initialization_creates_directory(self, tmp_path, monkeypatch):
        """Test that initialization creates settings directory"""
        settings_dir = tmp_path / "new_settings"

        def mock_get_settings_path(self):
            settings_dir.mkdir(parents=True, exist_ok=True)
            return settings_dir / "settings.json"

        monkeypatch.setattr(
            SettingsManager, "_get_settings_path", mock_get_settings_path
        )

        SettingsManager()
        assert settings_dir.exists()

    def test_initialization_loads_existing_settings(self, temp_settings_dir):
        """Test loading existing settings file"""
        # Create existing settings
        existing_settings = {
            "last_vram_file": "/path/to/vram.dmp",
            "preferences": {"auto_load_files": False},
        }
        settings_file = temp_settings_dir / "settings.json"
        settings_file.write_text(json.dumps(existing_settings))

        # Create manager
        with patch.object(
            SettingsManager, "_get_settings_path", return_value=settings_file
        ):
            manager = SettingsManager()

        assert manager.settings["last_vram_file"] == "/path/to/vram.dmp"
        assert manager.settings["preferences"]["auto_load_files"] is False

    def test_initialization_handles_corrupted_json(self, temp_settings_dir):
        """Test handling corrupted settings file"""
        # Create corrupted settings file
        settings_file = temp_settings_dir / "settings.json"
        settings_file.write_text("{corrupted json")

        # Create manager - should use defaults
        with patch.object(
            SettingsManager, "_get_settings_path", return_value=settings_file
        ):
            manager = SettingsManager()

        # Should have default settings
        assert manager.settings["last_vram_file"] == ""
        assert manager.settings["preferences"]["auto_load_files"] is True

    def test_default_settings_structure(self, settings_manager):
        """Test default settings have expected structure"""
        defaults = settings_manager._get_default_settings()

        # Check top-level keys
        assert "last_vram_file" in defaults
        assert "last_cgram_file" in defaults
        assert "last_oam_file" in defaults
        assert "recent_files" in defaults
        assert "preferences" in defaults

        # Check nested structures
        assert isinstance(defaults["recent_files"], dict)
        assert "vram" in defaults["recent_files"]
        assert isinstance(defaults["recent_files"]["vram"], list)

        assert isinstance(defaults["preferences"], dict)
        assert defaults["preferences"]["max_recent_files"] == 10


@pytest.mark.unit
class TestSettingsGetSet:
    """Test getting and setting values"""

    def test_get_simple_value(self, settings_manager):
        """Test getting simple value"""
        settings_manager.settings["test_key"] = "test_value"
        assert settings_manager.get("test_key") == "test_value"

    def test_get_nested_value(self, settings_manager):
        """Test getting nested value with dot notation"""
        settings_manager.settings["level1"] = {"level2": {"level3": "deep_value"}}
        assert settings_manager.get("level1.level2.level3") == "deep_value"

    def test_get_nonexistent_returns_default(self, settings_manager):
        """Test getting non-existent key returns default"""
        assert settings_manager.get("nonexistent") is None
        assert settings_manager.get("nonexistent", "default") == "default"

    def test_get_partial_path_returns_default(self, settings_manager):
        """Test getting partial path returns default"""
        settings_manager.settings["level1"] = {"level2": "value"}
        assert settings_manager.get("level1.level2.level3", "default") == "default"

    def test_set_simple_value(self, settings_manager):
        """Test setting simple value"""
        settings_manager.set("new_key", "new_value")
        assert settings_manager.settings["new_key"] == "new_value"

    def test_set_nested_value_creates_structure(self, settings_manager):
        """Test setting nested value creates structure"""
        settings_manager.set("new.nested.key", "nested_value")
        assert settings_manager.settings["new"]["nested"]["key"] == "nested_value"

    def test_set_nested_value_preserves_existing(self, settings_manager):
        """Test setting nested value preserves existing structure"""
        settings_manager.settings["existing"] = {"keep": "this"}
        settings_manager.set("existing.new", "value")

        assert settings_manager.settings["existing"]["keep"] == "this"
        assert settings_manager.settings["existing"]["new"] == "value"

    def test_set_saves_settings(self, settings_manager, temp_settings_dir):
        """Test that set() saves settings to file"""
        settings_manager.set("test_save", "saved_value")

        # Check file was written
        settings_file = temp_settings_dir / "settings.json"
        assert settings_file.exists()

        # Load and verify
        with open(settings_file) as f:
            saved_data = json.load(f)
        assert saved_data["test_save"] == "saved_value"


@pytest.mark.unit
class TestRecentFiles:
    """Test recent files functionality"""

    def test_add_recent_file_new_type(self, settings_manager):
        """Test adding file to new type"""
        settings_manager.add_recent_file("custom", "/path/to/file.dat")

        assert "custom" in settings_manager.settings["recent_files"]
        assert (
            settings_manager.settings["recent_files"]["custom"][0]
            == "/path/to/file.dat"
        )

    def test_add_recent_file_moves_to_front(self, settings_manager):
        """Test adding existing file moves it to front"""
        # Add multiple files
        settings_manager.add_recent_file("vram", "/path/1.dmp")
        settings_manager.add_recent_file("vram", "/path/2.dmp")
        settings_manager.add_recent_file("vram", "/path/3.dmp")

        # Re-add first file
        settings_manager.add_recent_file("vram", "/path/1.dmp")

        # Should be at front now
        recent = settings_manager.settings["recent_files"]["vram"]
        assert recent[0] == "/path/1.dmp"
        assert recent[1] == "/path/3.dmp"
        assert recent[2] == "/path/2.dmp"

    def test_add_recent_file_respects_limit(self, settings_manager):
        """Test recent files list respects max limit"""
        # Set lower limit
        settings_manager.settings["preferences"]["max_recent_files"] = 3

        # Add more files than limit
        for i in range(5):
            settings_manager.add_recent_file("vram", f"/path/{i}.dmp")

        # Should only keep most recent 3
        recent = settings_manager.settings["recent_files"]["vram"]
        assert len(recent) == 3
        assert recent[0] == "/path/4.dmp"
        assert recent[1] == "/path/3.dmp"
        assert recent[2] == "/path/2.dmp"

    def test_get_recent_files(self, settings_manager):
        """Test getting recent files"""
        # Add some files
        settings_manager.add_recent_file("cgram", "/path/1.cgram")
        settings_manager.add_recent_file("cgram", "/path/2.cgram")

        recent = settings_manager.get_recent_files("cgram")
        assert len(recent) == 2
        assert recent[0] == "/path/2.cgram"
        assert recent[1] == "/path/1.cgram"

    def test_get_recent_files_empty(self, settings_manager):
        """Test getting recent files for empty type"""
        recent = settings_manager.get_recent_files("nonexistent")
        assert recent == []


@pytest.mark.unit
class TestFileManagement:
    """Test file management functions"""

    def test_update_last_used_files(self, settings_manager):
        """Test updating last used files"""
        settings_manager.update_last_used_files(
            vram="/new/vram.dmp", cgram="/new/cgram.dmp"
        )

        assert settings_manager.settings["last_vram_file"] == "/new/vram.dmp"
        assert settings_manager.settings["last_cgram_file"] == "/new/cgram.dmp"

        # Also added to recent
        assert "/new/vram.dmp" in settings_manager.settings["recent_files"]["vram"]
        assert "/new/cgram.dmp" in settings_manager.settings["recent_files"]["cgram"]

    def test_update_last_used_files_partial(self, settings_manager):
        """Test updating only some files"""
        # Set initial values
        settings_manager.settings["last_vram_file"] = "/old/vram.dmp"
        settings_manager.settings["last_cgram_file"] = "/old/cgram.dmp"

        # Update only vram
        settings_manager.update_last_used_files(vram="/new/vram.dmp")

        assert settings_manager.settings["last_vram_file"] == "/new/vram.dmp"
        assert settings_manager.settings["last_cgram_file"] == "/old/cgram.dmp"

    def test_get_last_used_files(self, settings_manager):
        """Test getting last used files"""
        settings_manager.settings["last_vram_file"] = "/path/vram.dmp"
        settings_manager.settings["last_cgram_file"] = "/path/cgram.dmp"
        settings_manager.settings["last_oam_file"] = "/path/oam.dmp"

        last_used = settings_manager.get_last_used_files()
        assert last_used["vram"] == "/path/vram.dmp"
        assert last_used["cgram"] == "/path/cgram.dmp"
        assert last_used["oam"] == "/path/oam.dmp"


@pytest.mark.unit
class TestExtractionParams:
    """Test extraction parameter management"""

    def test_update_extraction_params(self, settings_manager):
        """Test updating extraction parameters"""
        settings_manager.update_extraction_params(
            offset=0xC000, tile_count=256, palette=5
        )

        assert settings_manager.settings["last_offset"] == 0xC000
        assert settings_manager.settings["last_tile_count"] == 256
        assert settings_manager.settings["last_palette"] == 5

    def test_get_extraction_params(self, settings_manager):
        """Test getting extraction parameters"""
        settings_manager.settings["last_offset"] = 0x8000
        settings_manager.settings["last_tile_count"] = 128
        settings_manager.settings["last_palette"] = 3

        params = settings_manager.get_extraction_params()
        assert params["offset"] == 0x8000
        assert params["tile_count"] == 128
        assert params["palette"] == 3

    def test_get_extraction_params_defaults(self, settings_manager):
        """Test getting extraction parameters with defaults"""
        # Clear any existing values
        for key in ["last_offset", "last_tile_count", "last_palette"]:
            if key in settings_manager.settings:
                del settings_manager.settings[key]

        params = settings_manager.get_extraction_params()
        assert params["offset"] == 0
        assert params["tile_count"] == 512
        assert params["palette"] == 0


@pytest.mark.unit
class TestSettingsPersistence:
    """Test settings persistence"""

    def test_save_settings(self, settings_manager, temp_settings_dir):
        """Test saving settings to file"""
        settings_manager.settings["test_key"] = "test_value"
        settings_manager.save_settings()

        # Load file and verify
        settings_file = temp_settings_dir / "settings.json"
        with open(settings_file) as f:
            saved_data = json.load(f)

        assert saved_data["test_key"] == "test_value"

    def test_save_settings_io_error_handled(self, settings_manager, monkeypatch):
        """Test save handles IO errors gracefully"""

        # Mock open to raise IOError
        def mock_open_error(*args, **kwargs):
            raise OSError("Permission denied")

        monkeypatch.setattr("builtins.open", mock_open_error)

        # Should not raise
        settings_manager.save_settings()

    def test_reset_settings(self, settings_manager):
        """Test resetting settings to defaults"""
        # Modify settings
        settings_manager.settings["last_vram_file"] = "/custom/path.vram"
        settings_manager.settings["preferences"]["auto_load_files"] = False

        # Reset
        settings_manager.reset_settings()

        # Should be back to defaults
        assert settings_manager.settings["last_vram_file"] == ""
        assert settings_manager.settings["preferences"]["auto_load_files"] is True


@pytest.mark.unit
class TestSingleton:
    """Test singleton functionality"""

    def test_get_settings_singleton(self, monkeypatch):
        """Test get_settings returns singleton"""
        # Clear any existing instance
        import sprite_editor.settings_manager

        sprite_editor.settings_manager._settings_instance = None

        # Get instance twice
        instance1 = get_settings()
        instance2 = get_settings()

        assert instance1 is instance2

    def test_get_settings_creates_instance(self, monkeypatch):
        """Test get_settings creates instance if needed"""
        # Clear any existing instance
        import sprite_editor.settings_manager

        sprite_editor.settings_manager._settings_instance = None

        instance = get_settings()
        assert isinstance(instance, SettingsManager)
        assert sprite_editor.settings_manager._settings_instance is instance
