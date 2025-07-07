#!/usr/bin/env python3
"""
Common file operation utilities
Provides reusable file handling functions
"""

import os
from typing import Optional, Tuple

from PyQt6.QtWidgets import QFileDialog


class FileOperations:
    """Utility class for common file operations"""

    @staticmethod
    def browse_file(parent, title: str, file_filter: str,
                    initial_dir: str = "") -> Optional[str]:
        """
        Browse for a file using a file dialog

        Args:
            parent: Parent widget for the dialog
            title: Dialog title
            file_filter: File filter string (e.g., "Dump Files (*.dmp)")
            initial_dir: Initial directory to open

        Returns:
            Selected file path or None if cancelled
        """
        file_name, _ = QFileDialog.getOpenFileName(
            parent, title, initial_dir, file_filter
        )
        return file_name if file_name else None

    @staticmethod
    def save_file(parent, title: str, default_name: str,
                  file_filter: str) -> Optional[str]:
        """
        Get a file path for saving using a file dialog

        Args:
            parent: Parent widget for the dialog
            title: Dialog title
            default_name: Default file name
            file_filter: File filter string

        Returns:
            Selected file path or None if cancelled
        """
        file_name, _ = QFileDialog.getSaveFileName(
            parent, title, default_name, file_filter
        )
        return file_name if file_name else None

    @staticmethod
    def get_initial_directory(file_path: str, fallback: str = "") -> str:
        """
        Get initial directory from a file path

        Args:
            file_path: File path to extract directory from
            fallback: Fallback directory if path is invalid

        Returns:
            Directory path
        """
        if file_path and os.path.exists(os.path.dirname(file_path)):
            return os.path.dirname(file_path)
        return fallback

    @staticmethod
    def ensure_absolute_path(file_path: str, base_dir: str = None) -> str:
        """
        Ensure a file path is absolute

        Args:
            file_path: File path to check
            base_dir: Base directory for relative paths

        Returns:
            Absolute file path
        """
        if os.path.isabs(file_path):
            return file_path

        if base_dir:
            return os.path.join(base_dir, file_path)

        return os.path.abspath(file_path)

    @staticmethod
    def validate_file_exists(file_path: str) -> Tuple[bool, str]:
        """
        Validate that a file exists

        Args:
            file_path: File path to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not file_path:
            return False, "No file path provided"

        if not os.path.exists(file_path):
            return False, f"File not found: {file_path}"

        if not os.path.isfile(file_path):
            return False, f"Path is not a file: {file_path}"

        return True, ""

    @staticmethod
    def get_file_size_text(file_path: str) -> str:
        """
        Get human-readable file size text

        Args:
            file_path: File path

        Returns:
            File size text (e.g., "1.5 MB")
        """
        if not os.path.exists(file_path):
            return "N/A"

        size = os.path.getsize(file_path)

        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0

        return f"{size:.1f} TB"

    @staticmethod
    def create_backup(file_path: str, suffix: str = ".bak") -> Optional[str]:
        """
        Create a backup of a file

        Args:
            file_path: File to backup
            suffix: Backup suffix

        Returns:
            Backup file path or None if failed
        """
        if not os.path.exists(file_path):
            return None

        backup_path = file_path + suffix

        # Find unique backup name
        counter = 1
        while os.path.exists(backup_path):
            backup_path = f"{file_path}.{counter}{suffix}"
            counter += 1

        try:
            import shutil
            shutil.copy2(file_path, backup_path)
            return backup_path
        except Exception:
            return None


class FileFilters:
    """Common file filter strings"""

    DUMP_FILES = "Dump Files (*.dmp);;All Files (*.*)"
    PNG_FILES = "PNG Files (*.png);;All Files (*.*)"
    ROM_FILES = "ROM Files (*.sfc *.smc);;All Files (*.*)"
    PALETTE_FILES = "Palette Files (*.act *.pal *.gpl);;All Files (*.*)"
    ALL_FILES = "All Files (*.*)"

    @staticmethod
    def get_filter(file_type: str) -> str:
        """Get file filter for a specific file type"""
        filters = {
            'dump': FileFilters.DUMP_FILES,
            'vram': FileFilters.DUMP_FILES,
            'cgram': FileFilters.DUMP_FILES,
            'oam': FileFilters.DUMP_FILES,
            'png': FileFilters.PNG_FILES,
            'rom': FileFilters.ROM_FILES,
            'palette': FileFilters.PALETTE_FILES
        }
        return filters.get(file_type.lower(), FileFilters.ALL_FILES)
