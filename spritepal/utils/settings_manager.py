"""
Settings manager for SpritePal application
"""

import json
import os
from pathlib import Path
from typing import Any


class SettingsManager:
    """Manages application settings and session persistence"""

    def __init__(self, app_name: str = "SpritePal") -> None:
        self.app_name = app_name
        self._settings_file = self._get_settings_file()
        self._settings = self._load_settings()

    def _get_settings_file(self) -> Path:
        """Get the settings file path"""
        # Use current directory for now (could be user config dir in future)
        return Path.cwd() / f".{self.app_name.lower()}_settings.json"

    def _load_settings(self) -> dict[str, Any]:
        """Load settings from file"""
        if self._settings_file.exists():
            try:
                with open(self._settings_file) as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        return data
                    print("Warning: Invalid settings file format")
                    return {}
            except (OSError, json.JSONDecodeError) as e:
                print(f"Warning: Could not load settings: {e}")

        # Return default settings
        return {
            "session": {
                "vram_path": "",
                "cgram_path": "",
                "oam_path": "",
                "output_name": "",
                "create_grayscale": True,
                "create_metadata": True,
            },
            "rom_injection": {
                "last_input_rom": "",
                "last_output_rom": "",
                "last_sprite_location": "",
                "last_custom_offset": "",
                "fast_compression": False,
            },
            "ui": {
                "window_width": 900,
                "window_height": 600,
                "window_x": -1,
                "window_y": -1,
            },
            "paths": {
                "default_dumps_dir": r"C:\Users\gabri\OneDrive\Dokumente\Mesen2\Debugger",
                "last_used_dir": "",
            },
        }

    def save_settings(self) -> None:
        """Save settings to file"""
        try:
            with open(self._settings_file, "w") as f:
                json.dump(self._settings, f, indent=2)
        except OSError as e:
            print(f"Warning: Could not save settings: {e}")

    def save(self) -> None:
        """Save settings to file (alias for save_settings)"""
        self.save_settings()

    def get(self, category: str, key: str, default: Any = None) -> Any:
        """Get a setting value"""
        return self._settings.get(category, {}).get(key, default)

    def get_value(self, category: str, key: str, default: Any = None) -> Any:
        """Get a setting value (alias for get method)"""
        return self.get(category, key, default)

    def set(self, category: str, key: str, value: Any) -> None:
        """Set a setting value"""
        if category not in self._settings:
            self._settings[category] = {}
        self._settings[category][key] = value

    def set_value(self, category: str, key: str, value: Any) -> None:
        """Set a setting value (alias for set method)"""
        self.set(category, key, value)

    def get_session_data(self) -> dict[str, Any]:
        """Get all session data"""
        session = self._settings.get("session", {})
        return session if isinstance(session, dict) else {}

    def save_session_data(self, session_data: dict[str, Any]) -> None:
        """Save session data"""
        self._settings["session"] = session_data
        self.save_settings()

    def get_ui_data(self) -> dict[str, Any]:
        """Get UI settings"""
        ui_data = self._settings.get("ui", {})
        return ui_data if isinstance(ui_data, dict) else {}

    def save_ui_data(self, ui_data: dict[str, Any]) -> None:
        """Save UI settings"""
        self._settings["ui"] = ui_data
        self.save_settings()

    def validate_file_paths(self) -> dict[str, str]:
        """Validate and return existing file paths from session"""
        session = self.get_session_data()
        validated_paths = {}

        for key in ["vram_path", "cgram_path", "oam_path"]:
            path = session.get(key, "")
            if path and os.path.exists(path):
                validated_paths[key] = path
            else:
                validated_paths[key] = ""

        return validated_paths

    def has_valid_session(self) -> bool:
        """Check if there's a valid session to restore"""
        validated = self.validate_file_paths()
        return bool(validated.get("vram_path") or validated.get("cgram_path"))

    def clear_session(self) -> None:
        """Clear session data"""
        self._settings["session"] = {
            "vram_path": "",
            "cgram_path": "",
            "oam_path": "",
            "output_name": "",
            "create_grayscale": True,
            "create_metadata": True,
        }
        self.save_settings()

    def get_default_directory(self) -> str:
        """Get the default directory for file operations"""
        # Try last used directory first
        last_used = str(self.get("paths", "last_used_dir", ""))
        if last_used and os.path.exists(last_used):
            return last_used

        # Fall back to default dumps directory
        default_dir = str(
            self.get(
                "paths",
                "default_dumps_dir",
                r"C:\Users\gabri\OneDrive\Dokumente\Mesen2\Debugger",
            )
        )
        if default_dir and os.path.exists(default_dir):
            return default_dir

        # Final fallback to current directory
        return str(Path.cwd())

    def set_last_used_directory(self, directory: str) -> None:
        """Set the last used directory"""
        if directory and os.path.exists(directory):
            self.set("paths", "last_used_dir", directory)
            self.save_settings()


def get_settings_manager() -> SettingsManager:
    """Get the global settings manager instance"""
    if not hasattr(get_settings_manager, '_instance'):
        get_settings_manager._instance = SettingsManager()
    return get_settings_manager._instance
