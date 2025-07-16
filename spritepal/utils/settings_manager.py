"""
Settings manager for SpritePal application
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, Optional


class SettingsManager:
    """Manages application settings and session persistence"""
    
    def __init__(self, app_name="SpritePal"):
        self.app_name = app_name
        self._settings_file = self._get_settings_file()
        self._settings = self._load_settings()
        
    def _get_settings_file(self) -> Path:
        """Get the settings file path"""
        # Use current directory for now (could be user config dir in future)
        return Path.cwd() / f".{self.app_name.lower()}_settings.json"
        
    def _load_settings(self) -> Dict[str, Any]:
        """Load settings from file"""
        if self._settings_file.exists():
            try:
                with open(self._settings_file, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                print(f"Warning: Could not load settings: {e}")
                
        # Return default settings
        return {
            "session": {
                "vram_path": "",
                "cgram_path": "",
                "oam_path": "",
                "output_name": "",
                "create_grayscale": True,
                "create_metadata": True
            },
            "ui": {
                "window_width": 900,
                "window_height": 600,
                "window_x": -1,
                "window_y": -1
            }
        }
        
    def save_settings(self):
        """Save settings to file"""
        try:
            with open(self._settings_file, 'w') as f:
                json.dump(self._settings, f, indent=2)
        except IOError as e:
            print(f"Warning: Could not save settings: {e}")
            
    def get(self, category: str, key: str, default=None):
        """Get a setting value"""
        return self._settings.get(category, {}).get(key, default)
        
    def set(self, category: str, key: str, value: Any):
        """Set a setting value"""
        if category not in self._settings:
            self._settings[category] = {}
        self._settings[category][key] = value
        
    def get_session_data(self) -> Dict[str, Any]:
        """Get all session data"""
        return self._settings.get("session", {})
        
    def save_session_data(self, session_data: Dict[str, Any]):
        """Save session data"""
        self._settings["session"] = session_data
        self.save_settings()
        
    def get_ui_data(self) -> Dict[str, Any]:
        """Get UI settings"""
        return self._settings.get("ui", {})
        
    def save_ui_data(self, ui_data: Dict[str, Any]):
        """Save UI settings"""
        self._settings["ui"] = ui_data
        self.save_settings()
        
    def validate_file_paths(self) -> Dict[str, str]:
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
        
    def clear_session(self):
        """Clear session data"""
        self._settings["session"] = {
            "vram_path": "",
            "cgram_path": "",
            "oam_path": "",
            "output_name": "",
            "create_grayscale": True,
            "create_metadata": True
        }
        self.save_settings()


# Global settings instance
_settings_manager = None


def get_settings_manager() -> SettingsManager:
    """Get the global settings manager instance"""
    global _settings_manager
    if _settings_manager is None:
        _settings_manager = SettingsManager()
    return _settings_manager