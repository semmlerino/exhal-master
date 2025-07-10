#!/usr/bin/env python3
"""
Tests for file operation utilities
Tests actual file operations with minimal mocking
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
from PyQt6.QtWidgets import QFileDialog

from sprite_editor.utils.file_operations import FileFilters, FileOperations


@pytest.fixture
def temp_dir():
    """Create a temporary directory with test files"""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create some test files
        test_file = Path(tmpdir) / "test.txt"
        test_file.write_text("test content")

        large_file = Path(tmpdir) / "large.bin"
        large_file.write_bytes(b"\x00" * 1024 * 1024)  # 1MB

        subdir = Path(tmpdir) / "subdir"
        subdir.mkdir()

        yield tmpdir


@pytest.mark.unit
class TestFileOperations:
    """Test FileOperations utility class"""

    def test_get_initial_directory_with_valid_path(self, temp_dir):
        """Test getting initial directory from valid file path"""
        file_path = os.path.join(temp_dir, "test.txt")
        result = FileOperations.get_initial_directory(file_path)
        assert result == temp_dir

    def test_get_initial_directory_with_invalid_path(self):
        """Test getting initial directory from invalid path"""
        result = FileOperations.get_initial_directory(
            "/nonexistent/file.txt", "/fallback"
        )
        assert result == "/fallback"

    def test_get_initial_directory_with_empty_path(self):
        """Test getting initial directory from empty path"""
        result = FileOperations.get_initial_directory("", "/fallback")
        assert result == "/fallback"

    def test_ensure_absolute_path_already_absolute(self):
        """Test ensuring path is absolute when already absolute"""
        abs_path = "/absolute/path/file.txt"
        result = FileOperations.ensure_absolute_path(abs_path)
        assert result == abs_path

    def test_ensure_absolute_path_relative_with_base(self):
        """Test ensuring relative path becomes absolute with base dir"""
        rel_path = "relative/file.txt"
        base_dir = "/base/dir"
        result = FileOperations.ensure_absolute_path(rel_path, base_dir)
        assert result == "/base/dir/relative/file.txt"

    def test_ensure_absolute_path_relative_no_base(self):
        """Test ensuring relative path becomes absolute without base dir"""
        rel_path = "relative/file.txt"
        result = FileOperations.ensure_absolute_path(rel_path)
        assert os.path.isabs(result)
        assert result.endswith("relative/file.txt")

    def test_validate_file_exists_valid(self, temp_dir):
        """Test validating existing file"""
        file_path = os.path.join(temp_dir, "test.txt")
        valid, error = FileOperations.validate_file_exists(file_path)
        assert valid is True
        assert error == ""

    def test_validate_file_exists_empty_path(self):
        """Test validating empty file path"""
        valid, error = FileOperations.validate_file_exists("")
        assert valid is False
        assert error == "No file path provided"

    def test_validate_file_exists_nonexistent(self):
        """Test validating non-existent file"""
        valid, error = FileOperations.validate_file_exists("/nonexistent/file.txt")
        assert valid is False
        assert "File not found" in error

    def test_validate_file_exists_directory(self, temp_dir):
        """Test validating directory instead of file"""
        valid, error = FileOperations.validate_file_exists(temp_dir)
        assert valid is False
        assert "Path is not a file" in error

    def test_get_file_size_text_small(self, temp_dir):
        """Test getting file size text for small file"""
        file_path = os.path.join(temp_dir, "test.txt")
        size_text = FileOperations.get_file_size_text(file_path)
        assert "B" in size_text
        assert size_text == "12.0 B"  # "test content" is 12 bytes

    def test_get_file_size_text_large(self, temp_dir):
        """Test getting file size text for large file"""
        file_path = os.path.join(temp_dir, "large.bin")
        size_text = FileOperations.get_file_size_text(file_path)
        assert size_text == "1.0 MB"

    def test_get_file_size_text_nonexistent(self):
        """Test getting file size text for non-existent file"""
        size_text = FileOperations.get_file_size_text("/nonexistent/file.txt")
        assert size_text == "N/A"

    def test_create_backup_simple(self, temp_dir):
        """Test creating simple backup"""
        file_path = os.path.join(temp_dir, "test.txt")
        backup_path = FileOperations.create_backup(file_path)

        assert backup_path is not None
        assert os.path.exists(backup_path)
        assert backup_path == file_path + ".bak"

        # Verify content was copied
        with open(file_path) as f:
            original = f.read()
        with open(backup_path) as f:
            backup = f.read()
        assert original == backup

    def test_create_backup_multiple(self, temp_dir):
        """Test creating multiple backups"""
        file_path = os.path.join(temp_dir, "test.txt")

        # Create first backup
        backup1 = FileOperations.create_backup(file_path)
        assert backup1 == file_path + ".bak"

        # Create second backup
        backup2 = FileOperations.create_backup(file_path)
        assert backup2 == file_path + ".1.bak"

        # Create third backup
        backup3 = FileOperations.create_backup(file_path)
        assert backup3 == file_path + ".2.bak"

        # All should exist
        assert all(os.path.exists(b) for b in [backup1, backup2, backup3])

    def test_create_backup_custom_suffix(self, temp_dir):
        """Test creating backup with custom suffix"""
        file_path = os.path.join(temp_dir, "test.txt")
        backup_path = FileOperations.create_backup(file_path, ".backup")

        assert backup_path == file_path + ".backup"
        assert os.path.exists(backup_path)

    def test_create_backup_nonexistent_file(self):
        """Test creating backup of non-existent file"""
        backup_path = FileOperations.create_backup("/nonexistent/file.txt")
        assert backup_path is None

    def test_browse_file_cancelled(self):
        """Test browse file when dialog is cancelled"""
        with patch.object(QFileDialog, "getOpenFileName") as mock_dialog:
            mock_dialog.return_value = ("", "")
            result = FileOperations.browse_file(None, "Title", "Filter")
            assert result is None

    def test_browse_file_selected(self):
        """Test browse file when file is selected"""
        with patch.object(QFileDialog, "getOpenFileName") as mock_dialog:
            mock_dialog.return_value = ("/path/to/file.txt", "Filter")
            result = FileOperations.browse_file(None, "Title", "Filter")
            assert result == "/path/to/file.txt"

    def test_save_file_cancelled(self):
        """Test save file when dialog is cancelled"""
        with patch.object(QFileDialog, "getSaveFileName") as mock_dialog:
            mock_dialog.return_value = ("", "")
            result = FileOperations.save_file(None, "Title", "default.txt", "Filter")
            assert result is None

    def test_save_file_selected(self):
        """Test save file when path is selected"""
        with patch.object(QFileDialog, "getSaveFileName") as mock_dialog:
            mock_dialog.return_value = ("/path/to/save.txt", "Filter")
            result = FileOperations.save_file(None, "Title", "default.txt", "Filter")
            assert result == "/path/to/save.txt"


@pytest.mark.unit
class TestFileFilters:
    """Test FileFilters utility class"""

    def test_filter_constants(self):
        """Test filter string constants"""
        assert "*.dmp" in FileFilters.DUMP_FILES
        assert "*.png" in FileFilters.PNG_FILES
        assert "*.sfc" in FileFilters.ROM_FILES
        assert "*.smc" in FileFilters.ROM_FILES
        assert "*.act" in FileFilters.PALETTE_FILES
        assert "*.*" in FileFilters.ALL_FILES

    def test_get_filter_dump_types(self):
        """Test getting filter for dump file types"""
        assert FileFilters.get_filter("dump") == FileFilters.DUMP_FILES
        assert FileFilters.get_filter("vram") == FileFilters.DUMP_FILES
        assert FileFilters.get_filter("cgram") == FileFilters.DUMP_FILES
        assert FileFilters.get_filter("oam") == FileFilters.DUMP_FILES

    def test_get_filter_other_types(self):
        """Test getting filter for other file types"""
        assert FileFilters.get_filter("png") == FileFilters.PNG_FILES
        assert FileFilters.get_filter("rom") == FileFilters.ROM_FILES
        assert FileFilters.get_filter("palette") == FileFilters.PALETTE_FILES

    def test_get_filter_case_insensitive(self):
        """Test filter lookup is case insensitive"""
        assert FileFilters.get_filter("PNG") == FileFilters.PNG_FILES
        assert FileFilters.get_filter("Rom") == FileFilters.ROM_FILES
        assert FileFilters.get_filter("VRAM") == FileFilters.DUMP_FILES

    def test_get_filter_unknown_type(self):
        """Test getting filter for unknown type"""
        assert FileFilters.get_filter("unknown") == FileFilters.ALL_FILES
        assert FileFilters.get_filter("") == FileFilters.ALL_FILES
