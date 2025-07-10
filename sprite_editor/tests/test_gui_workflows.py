#!/usr/bin/env python3
"""
Simplified GUI workflow tests that avoid timeout issues
"""

from unittest.mock import MagicMock, patch

import pytest
from PyQt6.QtWidgets import QFileDialog, QMessageBox

from sprite_editor_unified import UnifiedSpriteEditor


@pytest.fixture
def simple_editor(qtbot):
    """Create editor without complex setup"""
    # Patch heavy initialization operations
    with patch("sprite_editor_unified.UnifiedSpriteEditor.load_settings"):
        editor = UnifiedSpriteEditor()
        qtbot.addWidget(editor)
        yield editor


@pytest.fixture
def mock_files(tmp_path):
    """Create minimal test files"""
    vram_file = tmp_path / "test.vram"
    vram_file.write_bytes(b"\x00" * 1024)  # Small test file

    cgram_file = tmp_path / "test.cgram"
    cgram_file.write_bytes(b"\x00" * 512)

    return {"vram": str(vram_file), "cgram": str(cgram_file), "tmp_path": tmp_path}


class TestBasicWorkflows:
    """Test basic GUI workflows without complex setup"""

    def test_extraction_workflow(self, simple_editor, mock_files):
        """Test basic extraction workflow"""
        editor = simple_editor

        # Setup inputs
        editor.extract_vram_input.setText(mock_files["vram"])
        editor.extract_cgram_input.setText(mock_files["cgram"])
        editor.tile_mode_radio.setChecked(True)

        # Mock the blocking operations
        with patch.object(
            QFileDialog,
            "getExistingDirectory",
            return_value=str(mock_files["tmp_path"]),
        ), patch("sprite_editor_unified.WorkflowWorker") as mock_worker_class:
            mock_worker = MagicMock()
            mock_worker_class.return_value = mock_worker

            # Perform extraction
            editor.perform_extraction()

            # Verify worker was started
            assert mock_worker.start.called

    def test_validation_workflow(self, simple_editor, mock_files):
        """Test validation workflow"""
        editor = simple_editor

        editor.validate_input.setText(str(mock_files["tmp_path"]))

        with patch("sprite_editor_unified.WorkflowWorker") as mock_worker_class:
            mock_worker = MagicMock()
            mock_worker_class.return_value = mock_worker

            editor.perform_validation()

            assert mock_worker.start.called

    def test_error_handling(self, simple_editor, mock_files):
        """Test error handling in workflows"""
        editor = simple_editor

        # Test missing input error
        with patch.object(QMessageBox, "warning") as mock_warning:
            editor.perform_extraction()
            mock_warning.assert_called_once()

    def test_project_management(self, simple_editor, mock_files):
        """Test basic project operations"""
        editor = simple_editor

        # Create project
        editor.new_project()
        assert editor.current_project is not None

        # Save project
        project_file = mock_files["tmp_path"] / "test.ksproj"
        with patch.object(
            QFileDialog, "getSaveFileName", return_value=(str(project_file), "")
        ):
            editor.save_project()

        # Verify project saved
        assert project_file.exists()

    def test_quick_action(self, simple_editor):
        """Test quick action dialog"""
        editor = simple_editor

        mock_dialog = MagicMock()
        mock_dialog.exec.return_value = 1
        mock_dialog.get_params.return_value = {"action": "test"}

        with patch("sprite_editor_unified.QuickActionDialog", return_value=mock_dialog):
            with patch.object(QMessageBox, "information"):
                editor.show_quick_action()

                assert mock_dialog.exec.called
