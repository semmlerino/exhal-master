#!/usr/bin/env python3
"""
Test suite for StartupDialog functionality
Tests dialog behavior, recent files handling, and user interactions
"""

import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QPushButton

from indexed_pixel_editor import SettingsManager, StartupDialog


class TestStartupDialog:
    """Test cases for StartupDialog functionality"""

    @pytest.fixture
    def temp_settings_dir(self):
        """Create temporary settings directory"""
        with tempfile.TemporaryDirectory() as temp_dir:
            settings_dir = Path(temp_dir) / ".indexed_pixel_editor"
            settings_dir.mkdir()
            yield settings_dir

    @pytest.fixture
    def mock_settings_manager(self, temp_settings_dir):
        """Create a SettingsManager with temporary directory"""
        with patch("pathlib.Path.home", return_value=temp_settings_dir.parent):
            return SettingsManager()

    @pytest.fixture
    def temp_image_files(self):
        """Create temporary image files for testing"""
        with tempfile.TemporaryDirectory() as temp_dir:
            files = []
            for i in range(3):
                file_path = Path(temp_dir) / f"test_image_{i}.png"
                file_path.write_text("fake png data")  # Just create the file
                files.append(str(file_path))
            yield files

    def test_startup_dialog_creation_with_no_recent_files(self, qtbot, mock_settings_manager):
        """Test dialog creation when no recent files exist"""
        dialog = StartupDialog(mock_settings_manager, None)
        qtbot.addWidget(dialog)

        # Check basic properties
        assert dialog.windowTitle() == "Indexed Pixel Editor - Welcome"
        assert dialog.isModal()

        # Check that recent list is empty
        assert dialog.recent_list.count() == 0

        # Check that no "Open Selected" button exists
        open_selected_btn = None
        for button in dialog.findChildren(QPushButton):
            if button.text() == "Open Selected":
                open_selected_btn = button
                break
        assert open_selected_btn is None

    def test_startup_dialog_with_recent_files(self, qtbot, mock_settings_manager, temp_image_files):
        """Test dialog creation with recent files"""
        # Add recent files
        for file_path in temp_image_files:
            mock_settings_manager.add_recent_file(file_path)

        dialog = StartupDialog(mock_settings_manager, None)
        qtbot.addWidget(dialog)

        # Check recent list has correct number of items
        assert dialog.recent_list.count() == len(temp_image_files)

        # Check first item is selected
        assert dialog.recent_list.currentRow() == 0

        # Check items have correct data
        for i in range(dialog.recent_list.count()):
            item = dialog.recent_list.item(i)
            assert item.data(Qt.ItemDataRole.UserRole) in temp_image_files
            assert item.toolTip() in temp_image_files

    def test_new_file_action(self, qtbot, mock_settings_manager):
        """Test clicking 'Create New' button"""
        dialog = StartupDialog(mock_settings_manager, None)
        qtbot.addWidget(dialog)

        # Find and click new file button
        new_btn = None
        for button in dialog.findChildren(QPushButton):
            if "Create New" in button.text():
                new_btn = button
                break

        assert new_btn is not None

        # Click the button
        with qtbot.waitSignal(dialog.accepted):
            qtbot.mouseClick(new_btn, Qt.MouseButton.LeftButton)

        assert dialog.action == "new_file"
        assert dialog.result() == dialog.DialogCode.Accepted

    def test_open_file_action(self, qtbot, mock_settings_manager):
        """Test clicking 'Open File' button"""
        dialog = StartupDialog(mock_settings_manager, None)
        qtbot.addWidget(dialog)

        # Find and click open file button
        open_btn = None
        for button in dialog.findChildren(QPushButton):
            if "Open Indexed PNG" in button.text():
                open_btn = button
                break

        assert open_btn is not None

        with qtbot.waitSignal(dialog.accepted):
            qtbot.mouseClick(open_btn, Qt.MouseButton.LeftButton)

        assert dialog.action == "open_file"

    def test_double_click_recent_file(self, qtbot, mock_settings_manager, temp_image_files):
        """Test double-clicking a recent file"""
        # Add a recent file
        mock_settings_manager.add_recent_file(temp_image_files[0])

        dialog = StartupDialog(mock_settings_manager, None)
        qtbot.addWidget(dialog)

        # Directly trigger the itemDoubleClicked signal
        first_item = dialog.recent_list.item(0)

        with qtbot.waitSignal(dialog.accepted):
            dialog.recent_list.itemDoubleClicked.emit(first_item)

        assert dialog.action == "open_recent"
        assert dialog.selected_file == temp_image_files[0]

    def test_open_selected_button_state(self, qtbot, mock_settings_manager, temp_image_files):
        """Test 'Open Selected' button enable/disable state"""
        # Add recent files
        for file_path in temp_image_files:
            mock_settings_manager.add_recent_file(file_path)

        dialog = StartupDialog(mock_settings_manager, None)
        qtbot.addWidget(dialog)

        # Find Open Selected button
        open_selected_btn = None
        for button in dialog.findChildren(QPushButton):
            if button.text() == "Open Selected":
                open_selected_btn = button
                break

        assert open_selected_btn is not None

        # Should be enabled initially (first item selected)
        assert open_selected_btn.isEnabled()

        # Clear selection
        dialog.recent_list.clearSelection()
        assert not open_selected_btn.isEnabled()

        # Select an item
        dialog.recent_list.setCurrentRow(1)
        assert open_selected_btn.isEnabled()

    def test_cancel_action(self, qtbot, mock_settings_manager):
        """Test clicking Cancel button"""
        dialog = StartupDialog(mock_settings_manager, None)
        qtbot.addWidget(dialog)

        # Find and click cancel button
        cancel_btn = None
        for button in dialog.findChildren(QPushButton):
            if button.text() == "Cancel":
                cancel_btn = button
                break

        assert cancel_btn is not None

        with qtbot.waitSignal(dialog.rejected):
            qtbot.mouseClick(cancel_btn, Qt.MouseButton.LeftButton)

        assert dialog.result() == dialog.DialogCode.Rejected
        assert dialog.action is None

    def test_non_existent_recent_files_filtered(self, qtbot, mock_settings_manager):
        """Test that non-existent files are filtered from recent list"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create files
            existing_file = Path(temp_dir) / "exists.png"
            existing_file.write_text("data")

            # Add both existing and non-existing files directly to settings
            mock_settings_manager.settings["recent_files"] = [
                str(existing_file),
                str(Path(temp_dir) / "missing1.png"),
                str(Path(temp_dir) / "missing2.png")
            ]
            mock_settings_manager.save_settings()

            dialog = StartupDialog(mock_settings_manager, None)
            qtbot.addWidget(dialog)

            # Should only show existing file
            assert dialog.recent_list.count() == 1
            item = dialog.recent_list.item(0)
            assert item.data(Qt.ItemDataRole.UserRole) == str(existing_file)
