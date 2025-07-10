#!/usr/bin/env python3
"""
Project model for managing application state
Handles project-wide settings and file management
"""

import os

from PyQt6.QtCore import pyqtSignal

from sprite_editor.settings_manager import SettingsManager

from .base_model import BaseModel, ObservableProperty


class ProjectModel(BaseModel):
    """Model for project state and settings"""

    # Observable properties
    project_name = ObservableProperty("Untitled")
    project_path = ObservableProperty("")
    is_modified = ObservableProperty(False)

    # Recent files
    recent_vram_files = ObservableProperty([])
    recent_cgram_files = ObservableProperty([])
    recent_oam_files = ObservableProperty([])
    recent_png_files = ObservableProperty([])

    # Preferences
    auto_load_files = ObservableProperty(True)
    remember_window_position = ObservableProperty(True)
    max_recent_files = ObservableProperty(10)

    # Signals
    project_name_changed = pyqtSignal(str)
    project_path_changed = pyqtSignal(str)
    is_modified_changed = pyqtSignal(bool)
    recent_files_changed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.settings = SettingsManager()
        self._load_settings()

    def _load_settings(self):
        """Load settings from persistent storage"""
        # Load preferences
        self.auto_load_files = self.settings.get("preferences.auto_load_files", True)
        self.remember_window_position = self.settings.get(
            "preferences.remember_window_position", True
        )

        # Load recent files
        recent = self.settings.get("recent_files", {})
        self.recent_vram_files = recent.get("vram", [])
        self.recent_cgram_files = recent.get("cgram", [])
        self.recent_oam_files = recent.get("oam", [])
        self.recent_png_files = recent.get("png", [])

    def save_settings(self):
        """Save settings to persistent storage"""
        # Save preferences
        self.settings.set("preferences.auto_load_files", self.auto_load_files)
        self.settings.set(
            "preferences.remember_window_position", self.remember_window_position
        )

        # Save recent files
        self.settings.set(
            "recent_files",
            {
                "vram": self.recent_vram_files,
                "cgram": self.recent_cgram_files,
                "oam": self.recent_oam_files,
                "png": self.recent_png_files,
            },
        )

        self.settings.save_settings()

    def add_recent_file(self, file_path, file_type):
        """Add a file to recent files list"""
        if not os.path.exists(file_path):
            return

        # Get the appropriate list
        if file_type == "vram":
            recent_list = self.recent_vram_files
        elif file_type == "cgram":
            recent_list = self.recent_cgram_files
        elif file_type == "oam":
            recent_list = self.recent_oam_files
        elif file_type == "png":
            recent_list = self.recent_png_files
        else:
            return

        # Remove if already exists
        if file_path in recent_list:
            recent_list.remove(file_path)

        # Add to front
        recent_list.insert(0, file_path)

        # Limit size
        if len(recent_list) > self.max_recent_files:
            recent_list = recent_list[: self.max_recent_files]

        # Update the property
        if file_type == "vram":
            self.recent_vram_files = recent_list
        elif file_type == "cgram":
            self.recent_cgram_files = recent_list
        elif file_type == "oam":
            self.recent_oam_files = recent_list
        elif file_type == "png":
            self.recent_png_files = recent_list

        self.recent_files_changed.emit()
        self.save_settings()

    def clear_recent_files(self, file_type=None):
        """Clear recent files list"""
        if file_type:
            if file_type == "vram":
                self.recent_vram_files = []
            elif file_type == "cgram":
                self.recent_cgram_files = []
            elif file_type == "oam":
                self.recent_oam_files = []
            elif file_type == "png":
                self.recent_png_files = []
        else:
            # Clear all
            self.recent_vram_files = []
            self.recent_cgram_files = []
            self.recent_oam_files = []
            self.recent_png_files = []

        self.recent_files_changed.emit()
        self.save_settings()

    def get_last_used_files(self):
        """Get the most recently used file of each type"""
        return {
            "vram": self.recent_vram_files[0] if self.recent_vram_files else "",
            "cgram": self.recent_cgram_files[0] if self.recent_cgram_files else "",
            "oam": self.recent_oam_files[0] if self.recent_oam_files else "",
            "png": self.recent_png_files[0] if self.recent_png_files else "",
        }

    def mark_modified(self):
        """Mark the project as modified"""
        self.is_modified = True

    def mark_saved(self):
        """Mark the project as saved"""
        self.is_modified = False

    def reset_settings(self):
        """Reset all settings to defaults"""
        self.settings.reset_settings()
        self._load_settings()
        self.recent_files_changed.emit()
