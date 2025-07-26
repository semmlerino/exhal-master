"""Tests for settings manager"""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from spritepal.utils.settings_manager import SettingsManager, get_settings_manager


class TestSettingsManager:
    """Test the SettingsManager class"""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for settings"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    @pytest.fixture
    def settings_manager(self, temp_dir):
        """Create a SettingsManager in temp directory"""
        # Patch Path.cwd() to return temp directory
        with patch("pathlib.Path.cwd", return_value=Path(temp_dir)):
            manager = SettingsManager("TestApp")
            yield manager
            # Cleanup
            if manager._settings_file.exists():
                manager._settings_file.unlink()

    def test_init_creates_default_settings(self, settings_manager):
        """Test initialization creates default settings"""
        assert isinstance(settings_manager._settings, dict)
        assert "session" in settings_manager._settings
        assert "ui" in settings_manager._settings

        # Check default session values
        session = settings_manager._settings["session"]
        assert session["vram_path"] == ""
        assert session["cgram_path"] == ""
        assert session["oam_path"] == ""
        assert session["create_grayscale"] is True
        assert session["create_metadata"] is True

    def test_settings_file_path(self, temp_dir):
        """Test settings file path generation"""
        with patch("pathlib.Path.cwd", return_value=Path(temp_dir)):
            manager = SettingsManager("TestApp")
            expected_path = Path(temp_dir) / ".testapp_settings.json"
            assert manager._settings_file == expected_path

    def test_load_existing_settings(self, temp_dir):
        """Test loading existing settings file"""
        # Create settings file
        settings_data = {
            "session": {"vram_path": "/test/vram.dmp"},
            "ui": {"window_width": 1000},
        }
        settings_file = Path(temp_dir) / ".testapp_settings.json"
        with open(settings_file, "w") as f:
            json.dump(settings_data, f)

        # Load settings
        with patch("pathlib.Path.cwd", return_value=Path(temp_dir)):
            manager = SettingsManager("TestApp")

        assert manager._settings["session"]["vram_path"] == "/test/vram.dmp"
        assert manager._settings["ui"]["window_width"] == 1000

    def test_load_corrupted_settings(self, temp_dir):
        """Test loading corrupted settings file"""
        # Create corrupted settings file
        settings_file = Path(temp_dir) / ".testapp_settings.json"
        with open(settings_file, "w") as f:
            f.write("{ invalid json }")

        # Should return default settings
        with patch("pathlib.Path.cwd", return_value=Path(temp_dir)):
            manager = SettingsManager("TestApp")

        assert manager._settings["session"]["vram_path"] == ""
        assert manager._settings["ui"]["window_width"] == 900

    def test_save_settings(self, settings_manager, temp_dir):
        """Test saving settings"""
        # Modify settings
        settings_manager._settings["session"]["vram_path"] = "/test/path.dmp"
        settings_manager._settings["ui"]["window_width"] = 1200

        # Save
        settings_manager.save_settings()

        # Verify file contents
        with open(settings_manager._settings_file) as f:
            saved_data = json.load(f)

        assert saved_data["session"]["vram_path"] == "/test/path.dmp"
        assert saved_data["ui"]["window_width"] == 1200

    def test_get_setting(self, settings_manager):
        """Test getting individual settings"""
        settings_manager._settings["session"]["test_key"] = "test_value"

        value = settings_manager.get("session", "test_key")
        assert value == "test_value"

        # Test with default
        value = settings_manager.get("session", "nonexistent", "default")
        assert value == "default"

        # Test missing category
        value = settings_manager.get("missing_category", "key", "default")
        assert value == "default"

    def test_set_setting(self, settings_manager):
        """Test setting individual values"""
        settings_manager.set("session", "new_key", "new_value")
        assert settings_manager._settings["session"]["new_key"] == "new_value"

        # Test new category
        settings_manager.set("custom", "key", "value")
        assert settings_manager._settings["custom"]["key"] == "value"

    def test_get_session_data(self, settings_manager):
        """Test getting session data"""
        settings_manager._settings["session"]["vram_path"] = "/test.dmp"

        session = settings_manager.get_session_data()
        assert session["vram_path"] == "/test.dmp"
        assert isinstance(session, dict)

    def test_save_session_data(self, settings_manager):
        """Test saving session data"""
        new_session = {
            "vram_path": "/new/vram.dmp",
            "cgram_path": "/new/cgram.dmp",
            "output_name": "output",
        }

        settings_manager.save_session_data(new_session)

        assert settings_manager._settings["session"] == new_session
        # Should also save to file
        assert settings_manager._settings_file.exists()

    def test_get_ui_data(self, settings_manager):
        """Test getting UI data"""
        ui_data = settings_manager.get_ui_data()

        assert ui_data["window_width"] == 900
        assert ui_data["window_height"] == 600
        assert isinstance(ui_data, dict)

    def test_save_ui_data(self, settings_manager):
        """Test saving UI data"""
        new_ui = {
            "window_width": 1024,
            "window_height": 768,
            "window_x": 100,
            "window_y": 100,
        }

        settings_manager.save_ui_data(new_ui)

        assert settings_manager._settings["ui"] == new_ui
        assert settings_manager._settings_file.exists()

    def test_validate_file_paths(self, settings_manager, temp_dir):
        """Test file path validation"""
        # Create test files
        vram_file = Path(temp_dir) / "test.vram"
        vram_file.write_text("data")

        settings_manager._settings["session"]["vram_path"] = str(vram_file)
        settings_manager._settings["session"]["cgram_path"] = "/nonexistent.cgram"
        settings_manager._settings["session"]["oam_path"] = ""

        validated = settings_manager.validate_file_paths()

        assert validated["vram_path"] == str(vram_file)
        assert validated["cgram_path"] == ""  # Nonexistent file
        assert validated["oam_path"] == ""

    def test_has_valid_session(self, settings_manager, temp_dir):
        """Test checking for valid session"""
        # No valid files
        assert not settings_manager.has_valid_session()

        # Create valid file
        vram_file = Path(temp_dir) / "test.vram"
        vram_file.write_text("data")

        settings_manager._settings["session"]["vram_path"] = str(vram_file)
        assert settings_manager.has_valid_session()

    def test_clear_session(self, settings_manager):
        """Test clearing session data"""
        # Set some data
        settings_manager._settings["session"]["vram_path"] = "/test.vram"
        settings_manager._settings["session"]["output_name"] = "test"

        # Clear
        settings_manager.clear_session()

        # Check defaults restored
        session = settings_manager._settings["session"]
        assert session["vram_path"] == ""
        assert session["cgram_path"] == ""
        assert session["output_name"] == ""
        assert session["create_grayscale"] is True
        assert session["create_metadata"] is True


class TestGlobalSettingsInstance:
    """Test the global settings instance"""

    def test_get_settings_manager_singleton(self):
        """Test that get_settings_manager returns singleton"""
        # Reset global instance
        import spritepal.utils.settings_manager

        spritepal.utils.settings_manager._settings_instance = None

        # Get instance twice
        manager1 = get_settings_manager()
        manager2 = get_settings_manager()

        assert manager1 is manager2
        assert isinstance(manager1, SettingsManager)

    def test_get_settings_manager_preserves_state(self):
        """Test that singleton preserves state"""
        import spritepal.utils.settings_manager

        spritepal.utils.settings_manager._settings_instance = None

        manager1 = get_settings_manager()
        manager1.set("custom", "key", "value")

        manager2 = get_settings_manager()
        assert manager2.get("custom", "key") == "value"
