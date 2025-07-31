"""
Tests for ResumeScanDialog component
"""

import pytest
from PyQt6.QtWidgets import QPushButton

from spritepal.ui.dialogs import ResumeScanDialog


class TestResumeScanDialog:
    """Test ResumeScanDialog functionality"""

    @pytest.fixture
    def sample_scan_info(self):
        """Sample partial scan data"""
        return {
            "found_sprites": [
                {"offset": 0xC1000, "quality": 0.85},
                {"offset": 0xC2000, "quality": 0.92},
            ],
            "current_offset": 0xD8000,
            "completed": False,
            "total_found": 2,
            "scan_range": {
                "start": 0xC0000,
                "end": 0xF0000,
                "step": 0x100,
            },
        }

    def test_dialog_creation(self, qtbot, sample_scan_info):
        """Test dialog can be created with scan info"""
        dialog = ResumeScanDialog(sample_scan_info)
        qtbot.addWidget(dialog)

        assert dialog.windowTitle() == "Resume Sprite Scan?"
        assert dialog.scan_info == sample_scan_info
        assert dialog.user_choice == ResumeScanDialog.CANCEL

    def test_progress_formatting(self, qtbot, sample_scan_info):
        """Test progress info is formatted correctly"""
        dialog = ResumeScanDialog(sample_scan_info)
        qtbot.addWidget(dialog)

        progress_info = dialog._format_progress_info()

        # Check all expected information is present
        assert "Progress: 50.0% complete" in progress_info
        assert "Sprites found: 2" in progress_info
        assert "Last position: 0x0D8000" in progress_info
        assert "Scan range: 0x0C0000 - 0x0F0000" in progress_info

    def test_button_actions(self, qtbot, sample_scan_info):
        """Test button click actions"""
        dialog = ResumeScanDialog(sample_scan_info)
        qtbot.addWidget(dialog)

        # Test resume button
        assert isinstance(dialog.resume_button, QPushButton)
        assert dialog.resume_button.text() == "Resume Scan"
        assert dialog.resume_button.isDefault()  # Primary action

        with qtbot.waitSignal(dialog.accepted):
            dialog.resume_button.click()
        assert dialog.get_user_choice() == ResumeScanDialog.RESUME

        # Test start fresh button
        dialog = ResumeScanDialog(sample_scan_info)
        qtbot.addWidget(dialog)

        assert isinstance(dialog.fresh_button, QPushButton)
        assert dialog.fresh_button.text() == "Start Fresh"

        with qtbot.waitSignal(dialog.accepted):
            dialog.fresh_button.click()
        assert dialog.get_user_choice() == ResumeScanDialog.START_FRESH

        # Test cancel button
        dialog = ResumeScanDialog(sample_scan_info)
        qtbot.addWidget(dialog)

        assert isinstance(dialog.cancel_button, QPushButton)
        assert dialog.cancel_button.text() == "Cancel"

        with qtbot.waitSignal(dialog.rejected):
            dialog.cancel_button.click()
        assert dialog.get_user_choice() == ResumeScanDialog.CANCEL

    def test_empty_scan_info(self, qtbot):
        """Test dialog handles empty scan info gracefully"""
        empty_info = {
            "found_sprites": [],
            "current_offset": 0,
            "scan_range": {},
        }

        dialog = ResumeScanDialog(empty_info)
        qtbot.addWidget(dialog)

        progress_info = dialog._format_progress_info()
        assert "Progress:" in progress_info
        assert "Sprites found: 0" in progress_info

    def test_convenience_method(self, qtbot, sample_scan_info, monkeypatch):
        """Test static show_resume_dialog method"""
        # Mock exec to avoid blocking
        def mock_exec(self):
            self.user_choice = ResumeScanDialog.RESUME
            return True

        monkeypatch.setattr(ResumeScanDialog, "exec", mock_exec)

        choice = ResumeScanDialog.show_resume_dialog(sample_scan_info)
        assert choice == ResumeScanDialog.RESUME

    def test_completed_scan_handling(self, qtbot):
        """Test dialog with completed scan info"""
        completed_info = {
            "found_sprites": [1, 2, 3],
            "current_offset": 0xF0000,
            "completed": True,
            "total_found": 3,
            "scan_range": {
                "start": 0xC0000,
                "end": 0xF0000,
                "step": 0x100,
            },
        }

        dialog = ResumeScanDialog(completed_info)
        qtbot.addWidget(dialog)

        progress_info = dialog._format_progress_info()
        assert "Progress: 100.0% complete" in progress_info
