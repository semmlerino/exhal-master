"""
Settings manager for sprite editor
Handles saving and loading user preferences
"""

import json
import os
from pathlib import Path
from typing import Any, Optional


class SettingsManager:
    """Manages application settings with persistence"""

    def __init__(self, app_name="sprite_editor"):
        self.app_name = app_name
        self.settings_file = self._get_settings_path()
        self.settings = self._load_settings()

    def _get_settings_path(self) -> Path:
        """Get the appropriate settings directory for the platform"""
        if os.name == "nt":  # Windows
            base = Path(os.environ.get("APPDATA", os.path.expanduser("~")))
            settings_dir = base / self.app_name
        else:  # Linux/Mac
            base = Path(os.path.expanduser("~"))
            settings_dir = base / f".{self.app_name}"

        # Create directory if it doesn't exist
        settings_dir.mkdir(parents=True, exist_ok=True)
        return settings_dir / "settings.json"

    def _load_settings(self) -> dict[str, Any]:
        """Load settings from file"""
        if self.settings_file.exists():
            try:
                with open(self.settings_file) as f:
                    return json.load(f)
            except (OSError, json.JSONDecodeError):
                # If file is corrupted, start fresh
                return self._get_default_settings()
        return self._get_default_settings()

    def _get_default_settings(self) -> dict[str, Any]:
        """Get default settings"""
        return {
            "last_vram_file": "",
            "last_cgram_file": "",
            "last_oam_file": "",
            "last_output_dir": "",
            "last_offset": 0,
            "last_tile_count": 512,
            "last_palette": 0,
            "tiles_per_row": 16,
            "window_geometry": None,
            "recent_files": {"vram": [], "cgram": [], "oam": []},
            "preferences": {
                "auto_load_files": True,
                "remember_window_position": True,
                "max_recent_files": 10,
            },
        }

    def save_settings(self):
        """Save current settings to file"""
        try:
            with open(self.settings_file, "w") as f:
                json.dump(self.settings, f, indent=2)
        except OSError:
            # Fail silently if we can't save settings
            pass

    def get(self, key: str, default: Any = None) -> Any:
        """Get a setting value"""
        keys = key.split(".")
        value = self.settings
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        return value

    def set(self, key: str, value: Any):
        """Set a setting value"""
        keys = key.split(".")
        target = self.settings
        for k in keys[:-1]:
            if k not in target:
                target[k] = {}
            target = target[k]
        target[keys[-1]] = value
        self.save_settings()

    def add_recent_file(self, file_type: str, file_path: str):
        """Add a file to recent files list"""
        # Ensure file_path is a string (not Path object) for JSON serialization
        file_path = str(file_path)

        if file_type not in self.settings["recent_files"]:
            self.settings["recent_files"][file_type] = []

        recent_list = self.settings["recent_files"][file_type]

        # Remove if already in list
        if file_path in recent_list:
            recent_list.remove(file_path)

        # Add to front
        recent_list.insert(0, file_path)

        # Limit size
        max_recent = self.get("preferences.max_recent_files", 10)
        self.settings["recent_files"][file_type] = recent_list[:max_recent]

        self.save_settings()

    def get_recent_files(self, file_type: str) -> list:
        """Get recent files for a specific type"""
        return self.settings.get("recent_files", {}).get(file_type, [])

    def update_last_used_files(
        self,
        vram: Optional[str] = None,
        cgram: Optional[str] = None,
        oam: Optional[str] = None,
    ):
        """Update last used file paths"""
        if vram is not None:
            self.set("last_vram_file", vram)
            self.add_recent_file("vram", vram)
        if cgram is not None:
            self.set("last_cgram_file", cgram)
            self.add_recent_file("cgram", cgram)
        if oam is not None:
            self.set("last_oam_file", oam)
            self.add_recent_file("oam", oam)

    def get_last_used_files(self) -> dict[str, str]:
        """Get all last used file paths"""
        return {
            "vram": self.get("last_vram_file", ""),
            "cgram": self.get("last_cgram_file", ""),
            "oam": self.get("last_oam_file", ""),
        }

    def update_extraction_params(self, offset: int, tile_count: int, palette: int):
        """Update last used extraction parameters"""
        self.set("last_offset", offset)
        self.set("last_tile_count", tile_count)
        self.set("last_palette", palette)

    def get_extraction_params(self) -> dict[str, int]:
        """Get last used extraction parameters"""
        return {
            "offset": self.get("last_offset", 0),
            "tile_count": self.get("last_tile_count", 512),
            "palette": self.get("last_palette", 0),
        }

    def reset_settings(self):
        """Reset all settings to defaults"""
        self.settings = self._get_default_settings()
        self.save_settings()


# Singleton instance
_settings_instance = None


def get_settings() -> SettingsManager:
    """Get the singleton settings instance"""
    global _settings_instance
    if _settings_instance is None:
        _settings_instance = SettingsManager()
    return _settings_instance
