#!/usr/bin/env python3
"""
Test project management functionality
Tests project file saving/loading, recent files, and error handling
"""

import json
import os
import tempfile
from datetime import datetime
from unittest.mock import patch

import pytest
from PyQt6.QtWidgets import QListWidgetItem, QMessageBox

from sprite_editor.utils.file_operations import FileOperations
from sprite_editor_unified import UnifiedSpriteEditor


@pytest.fixture
def editor(qtbot):
    """Create UnifiedSpriteEditor instance"""
    editor = UnifiedSpriteEditor()
    qtbot.addWidget(editor)
    return editor


@pytest.fixture
def temp_dir():
    """Create temporary directory for tests"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.mark.project
class TestProjectManagement:
    """Test project file management functionality"""

    def test_new_project_creation(self, editor):
        """Test creating a new project"""
        # Create new project
        editor.new_project()

        # Verify project structure
        assert editor.current_project is not None
        assert editor.current_project["name"] == "New Project"
        assert "created" in editor.current_project
        assert "files" in editor.current_project
        assert isinstance(editor.current_project["files"], dict)

        # Verify UI update
        assert editor.project_label.text() == "New Project"

        # Verify timestamp is valid ISO format
        created_time = editor.current_project["created"]
        try:
            datetime.fromisoformat(created_time)
        except ValueError:
            pytest.fail(f"Invalid timestamp format: {created_time}")

    def test_save_project(self, editor, temp_dir):
        """Test saving a project to file"""
        # Create new project with test data
        editor.new_project()
        editor.current_project["name"] = "Test Project"
        editor.current_project["files"] = {
            "vram": "/path/to/vram.dmp",
            "cgram": "/path/to/cgram.dmp",
        }

        # Save to temp file
        project_file = os.path.join(temp_dir, "test_project.ksproj")

        # Mock QFileDialog to return our test path
        with patch("PyQt6.QtWidgets.QFileDialog.getSaveFileName") as mock_dialog:
            mock_dialog.return_value = (project_file, "Project files (*.ksproj)")
            editor.save_project()

        # Verify file was created
        assert os.path.exists(project_file)

        # Verify file contents
        with open(project_file) as f:
            saved_data = json.load(f)

        assert saved_data["name"] == "Test Project"
        assert saved_data["files"]["vram"] == "/path/to/vram.dmp"
        assert saved_data["files"]["cgram"] == "/path/to/cgram.dmp"
        assert "created" in saved_data

    def test_save_project_no_current(self, editor):
        """Test saving when no project is loaded"""
        # Ensure no project is loaded
        editor.current_project = None

        # Mock message box to capture the message
        with patch.object(QMessageBox, "information") as mock_info:
            editor.save_project()

            # Verify message was shown
            mock_info.assert_called_once()
            args = mock_info.call_args[0]
            assert args[1] == "No Project"
            assert args[2] == "No project to save"

    def test_load_project_success(self, editor, temp_dir):
        """Test successfully loading a project file"""
        # Create a test project file
        project_data = {
            "name": "Loaded Project",
            "created": datetime.now().isoformat(),
            "files": {"vram": "/test/vram.dmp", "cgram": "/test/cgram.dmp"},
        }

        project_file = os.path.join(temp_dir, "load_test.ksproj")
        with open(project_file, "w") as f:
            json.dump(project_data, f)

        # Load the project
        editor.load_project(project_file)

        # Verify project was loaded correctly
        assert editor.current_project is not None
        assert editor.current_project["name"] == "Loaded Project"
        assert editor.current_project["files"]["vram"] == "/test/vram.dmp"

        # Verify UI update
        assert editor.project_label.text() == "Loaded Project"

        # Verify recent files was updated
        assert project_file in editor.recent_files
        assert editor.recent_files[0] == project_file

    def test_load_project_invalid_json(self, editor, temp_dir):
        """Test loading a corrupted project file"""
        # Create invalid JSON file
        project_file = os.path.join(temp_dir, "invalid.ksproj")
        with open(project_file, "w") as f:
            f.write("{ invalid json content")

        # Mock message box to capture error
        with patch.object(QMessageBox, "critical") as mock_critical:
            editor.load_project(project_file)

            # Verify error message was shown
            mock_critical.assert_called_once()
            args = mock_critical.call_args[0]
            assert args[1] == "Error"
            assert "Failed to load project" in args[2]

    def test_load_project_missing_fields(self, editor, temp_dir):
        """Test loading project with missing fields"""
        # Create project with missing 'name' field
        project_data = {"created": datetime.now().isoformat(), "files": {}}

        project_file = os.path.join(temp_dir, "incomplete.ksproj")
        with open(project_file, "w") as f:
            json.dump(project_data, f)

        # Load the project
        editor.load_project(project_file)

        # Should still load but with default name
        assert editor.project_label.text() == "Unnamed"

    def test_recent_files_management(self, editor, temp_dir):
        """Test recent files list management"""
        # Create multiple project files
        project_files = []
        for i in range(15):  # More than the 10 file limit
            project_data = {
                "name": f"Project {i}",
                "created": datetime.now().isoformat(),
                "files": {},
            }

            project_file = os.path.join(temp_dir, f"project_{i}.ksproj")
            with open(project_file, "w") as f:
                json.dump(project_data, f)
            project_files.append(project_file)

        # Load all projects
        for pf in project_files:
            editor.load_project(pf)

        # Verify only last 10 are kept
        assert len(editor.recent_files) == 10

        # Verify most recent is first
        assert editor.recent_files[0] == project_files[-1]

        # Load an already-recent file
        editor.load_project(project_files[10])  # This should be in recent list

        # Verify it moved to top
        assert editor.recent_files[0] == project_files[10]
        assert len(editor.recent_files) == 10  # Still only 10 files

    def test_open_recent_file(self, editor, temp_dir):
        """Test opening a file from recent list"""
        # Create and load a project
        project_data = {
            "name": "Recent Test Project",
            "created": datetime.now().isoformat(),
            "files": {},
        }

        project_file = os.path.join(temp_dir, "recent_test.ksproj")
        with open(project_file, "w") as f:
            json.dump(project_data, f)

        editor.load_project(project_file)

        # Clear current project
        editor.current_project = None
        editor.project_label.setText("")

        # Create a mock list item
        item = QListWidgetItem(project_file)

        # Open from recent
        editor.open_recent_file(item)

        # Verify project was loaded
        assert editor.current_project["name"] == "Recent Test Project"
        assert editor.project_label.text() == "Recent Test Project"

    def test_open_recent_file_missing(self, editor, temp_dir):
        """Test opening a recent file that no longer exists"""
        # Add non-existent file to recent list
        fake_file = os.path.join(temp_dir, "doesnt_exist.ksproj")
        editor.recent_files = [fake_file]

        # Create a mock list item
        item = QListWidgetItem(fake_file)

        # Try to open - should fail silently
        editor.open_recent_file(item)

        # Current project should remain None
        assert editor.current_project is None

    def test_update_recent_menu_without_list_widget(self, editor):
        """Test update_recent_menu before UI is fully initialized"""
        # This tests the defensive check for recent_list existence
        # Remove the recent_list attribute to simulate early initialization
        if hasattr(editor, "recent_list"):
            delattr(editor, "recent_list")

        # Add some recent files
        editor.recent_files = ["/path/to/file1.ksproj", "/path/to/file2.ksproj"]

        # This should not crash
        editor.update_recent_menu()

        # Verify menu was updated
        assert len(editor.recent_menu.actions()) == 2

    def test_project_file_extensions(self, editor, temp_dir):
        """Test that both .ksproj and .json extensions work"""
        for ext in [".ksproj", ".json"]:
            project_data = {
                "name": f"Test {ext}",
                "created": datetime.now().isoformat(),
                "files": {},
            }

            project_file = os.path.join(temp_dir, f"test{ext}")
            with open(project_file, "w") as f:
                json.dump(project_data, f)

            editor.load_project(project_file)
            assert editor.current_project["name"] == f"Test {ext}"


@pytest.mark.backup
class TestFileBackup:
    """Test file backup functionality"""

    def test_create_backup_simple(self, temp_dir):
        """Test creating a simple backup"""
        # Create a test file
        test_file = os.path.join(temp_dir, "test.txt")
        with open(test_file, "w") as f:
            f.write("test content")

        # Create backup
        backup_path = FileOperations.create_backup(test_file)

        # Verify backup was created
        assert backup_path is not None
        assert os.path.exists(backup_path)
        assert backup_path == test_file + ".bak"

        # Verify content matches
        with open(backup_path) as f:
            assert f.read() == "test content"

    def test_create_backup_multiple(self, temp_dir):
        """Test creating multiple backups with collision handling"""
        # Create a test file
        test_file = os.path.join(temp_dir, "test.txt")
        with open(test_file, "w") as f:
            f.write("original content")

        # Create first backup
        backup1 = FileOperations.create_backup(test_file)
        assert backup1 == test_file + ".bak"

        # Modify original file
        with open(test_file, "w") as f:
            f.write("modified content 1")

        # Create second backup - should get numbered
        backup2 = FileOperations.create_backup(test_file)
        assert backup2 == test_file + ".1.bak"

        # Modify again
        with open(test_file, "w") as f:
            f.write("modified content 2")

        # Create third backup
        backup3 = FileOperations.create_backup(test_file)
        assert backup3 == test_file + ".2.bak"

        # Verify all backups exist with correct content
        assert os.path.exists(backup1)
        assert os.path.exists(backup2)
        assert os.path.exists(backup3)

        with open(backup1) as f:
            assert f.read() == "original content"
        with open(backup2) as f:
            assert f.read() == "modified content 1"
        with open(backup3) as f:
            assert f.read() == "modified content 2"

    def test_create_backup_custom_suffix(self, temp_dir):
        """Test creating backup with custom suffix"""
        # Create a test file
        test_file = os.path.join(temp_dir, "test.txt")
        with open(test_file, "w") as f:
            f.write("test content")

        # Create backup with custom suffix
        backup_path = FileOperations.create_backup(test_file, ".backup")

        # Verify backup was created with custom suffix
        assert backup_path == test_file + ".backup"
        assert os.path.exists(backup_path)

    def test_create_backup_nonexistent_file(self, temp_dir):
        """Test backup of non-existent file"""
        fake_file = os.path.join(temp_dir, "doesnt_exist.txt")

        # Should return None
        backup_path = FileOperations.create_backup(fake_file)
        assert backup_path is None

    def test_create_backup_preserves_metadata(self, temp_dir):
        """Test that backup preserves file metadata"""
        import time

        # Create a test file
        test_file = os.path.join(temp_dir, "test.txt")
        with open(test_file, "w") as f:
            f.write("test content")

        # Set specific modification time
        old_time = time.time() - 3600  # 1 hour ago
        os.utime(test_file, (old_time, old_time))

        # Create backup
        backup_path = FileOperations.create_backup(test_file)

        # Verify metadata was preserved (within 1 second tolerance)
        original_mtime = os.path.getmtime(test_file)
        backup_mtime = os.path.getmtime(backup_path)
        assert abs(original_mtime - backup_mtime) < 1.0

    def test_create_backup_permission_error(self, temp_dir):
        """Test backup when permission denied"""
        # Create a test file
        test_file = os.path.join(temp_dir, "test.txt")
        with open(test_file, "w") as f:
            f.write("test content")

        # Mock shutil.copy2 to raise permission error
        with patch("shutil.copy2") as mock_copy:
            mock_copy.side_effect = PermissionError("Access denied")

            # Should return None on error
            backup_path = FileOperations.create_backup(test_file)
            assert backup_path is None
