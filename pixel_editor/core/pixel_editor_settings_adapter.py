#!/usr/bin/env python3
"""
Settings adapter to bridge between pixel editor and sprite editor settings
"""

# Standard library imports
from typing import Any, Optional

# Local imports
from sprite_editor.settings_manager import SettingsManager as SpriteSettingsManager


class PixelEditorSettingsAdapter:
    """Adapter to make sprite editor settings work with pixel editor interface"""

    def __init__(self) -> None:
        self.sprite_settings = SpriteSettingsManager()
        self.file_type = "png"  # Default file type for pixel editor

    def get_recent_files(self) -> list[str]:
        """Get recent files (no file_type parameter needed)"""
        return self.sprite_settings.get_recent_files(self.file_type)

    def add_recent_file(self, file_path: str) -> None:
        """Add a file to recent files"""
        # Ensure file_path is a string (not Path object)
        self.sprite_settings.add_recent_file(self.file_type, str(file_path))

    def get_last_file(self) -> Optional[str]:
        """Get the last opened file"""
        last_files = self.sprite_settings.get_last_used_files()
        return last_files.get(self.file_type) if last_files else None

    def set_last_file(self, file_path: str) -> None:
        """Set the last opened file"""
        # Ensure file_path is a string (not Path object)
        # Note: update_last_used_files expects named parameters, not dict
        if self.file_type == "png":
            # For now, we'll store in settings directly since update_last_used_files
            # is designed for vram/cgram/oam files
            self.sprite_settings.set(f"last_{self.file_type}_file", str(file_path))
            self.sprite_settings.add_recent_file(self.file_type, str(file_path))

    def should_auto_load_last(self) -> bool:
        """Check if we should auto-load the last file"""
        # This feature doesn't exist in sprite settings, so return True by default
        return True

    def get_window_geometry(self) -> Any:
        """Get saved window geometry"""
        return self.sprite_settings.settings.get("window_geometry")

    def set_window_geometry(self, geometry: Any) -> None:
        """Save window geometry"""
        self.sprite_settings.settings["window_geometry"] = geometry
        self.sprite_settings.save_settings()

    # Palette-specific methods
    def get_recent_palette_files(self) -> list[str]:
        """Get recent palette files"""
        return self.sprite_settings.get_recent_files("palette")

    def add_recent_palette_file(self, file_path: str) -> None:
        """Add a palette file to recent files"""
        # Ensure file_path is a string (not Path object)
        self.sprite_settings.add_recent_file("palette", str(file_path))

    def get_last_palette_file(self) -> Optional[str]:
        """Get the last opened palette file"""
        last_files = self.sprite_settings.get_last_used_files()
        return last_files.get("palette") if last_files else None

    def set_last_palette_file(self, file_path: str) -> None:
        """Set the last opened palette file"""
        # Ensure file_path is a string (not Path object)
        # Store palette file path directly in settings
        self.sprite_settings.set("last_palette_file", str(file_path))
        self.sprite_settings.add_recent_file("palette", str(file_path))

    def associate_palette_with_image(self, image_path: str, palette_path: str) -> None:
        """Associate a palette file with an image file"""
        # Ensure paths are strings (not Path objects)
        image_path = str(image_path)
        palette_path = str(palette_path)
        # Use sprite settings' project associations feature
        associations = self.sprite_settings.settings.get("palette_associations", {})
        associations[image_path] = palette_path
        self.sprite_settings.settings["palette_associations"] = associations
        self.sprite_settings.save_settings()

    def get_associated_palette(self, image_path: str) -> Optional[str]:
        """Get the associated palette file for an image"""
        # Ensure image_path is a string (not Path object)
        image_path = str(image_path)
        associations = self.sprite_settings.settings.get("palette_associations", {})
        result = associations.get(image_path)
        return result if isinstance(result, str) else None

    def should_auto_offer_palette_loading(self) -> bool:
        """Check if we should automatically offer palette loading"""
        result = self.sprite_settings.settings.get("auto_offer_palette_loading", True)
        return bool(result)

    @property
    def settings(self) -> dict[str, Any]:
        """Direct access to settings dict for compatibility"""
        return self.sprite_settings.settings

    def save_settings(self) -> None:
        """Save settings"""
        self.sprite_settings.save_settings()

    def clear_recent_files(self) -> None:
        """Clear recent files list"""
        if (
            "recent_files" in self.sprite_settings.settings
            and self.file_type in self.sprite_settings.settings["recent_files"]
        ):
            self.sprite_settings.settings["recent_files"][self.file_type] = []
            self.sprite_settings.save_settings()
