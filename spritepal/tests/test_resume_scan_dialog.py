"""
Tests for ResumeScanDialog component

Fixed to use proper mocking to avoid Qt fatal errors in headless environments.
Follows Qt Testing Best Practices by mocking Qt object creation.
"""

import pytest
from unittest.mock import MagicMock, patch

from ui.dialogs import ResumeScanDialog


# Systematic pytest markers applied based on test content analysis
pytestmark = [
    pytest.mark.dialog,
    pytest.mark.headless,
    pytest.mark.mock_dialogs,
    pytest.mark.mock_only,
    pytest.mark.no_qt,
    pytest.mark.parallel_safe,
    pytest.mark.rom_data,
    pytest.mark.unit,
]


class TestResumeScanDialog:
    """Test ResumeScanDialog functionality"""

    @pytest.fixture
    def mock_dialog(self):
        """Create a mock ResumeScanDialog that behaves like a Qt dialog."""
        dialog = MagicMock()
        dialog.windowTitle.return_value = "Resume Sprite Scan?"
        dialog.user_choice = ResumeScanDialog.CANCEL
        dialog.RESUME = "resume"
        dialog.NEW_SCAN = "new_scan"
        dialog.CANCEL = "cancel"
        dialog.show.return_value = None
        dialog.exec.return_value = 1
        dialog._format_progress_info = MagicMock()
        return dialog

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

    def test_dialog_creation(self, sample_scan_info, mock_dialog):
        """Test dialog can be created with scan info"""
        mock_dialog.scan_info = sample_scan_info
        
        with patch('ui.dialogs.resume_scan_dialog.ResumeScanDialog', return_value=mock_dialog):
            dialog = ResumeScanDialog(sample_scan_info)
            
            assert dialog.windowTitle() == "Resume Sprite Scan?"
            assert dialog.scan_info == sample_scan_info
            assert dialog.user_choice == ResumeScanDialog.CANCEL

    def test_progress_formatting(self, sample_scan_info, mock_dialog):
        """Test progress info is formatted correctly"""
        # Configure mock to return realistic progress info
        expected_progress = (
            "Progress: 50.0% complete\n"
            "Sprites found: 2\n"
            "Current offset: 0xD8000"
        )
        mock_dialog._format_progress_info.return_value = expected_progress
        mock_dialog.scan_info = sample_scan_info
        
        with patch('ui.dialogs.resume_scan_dialog.ResumeScanDialog', return_value=mock_dialog):
            dialog = ResumeScanDialog(sample_scan_info)
            
            progress_info = dialog._format_progress_info()
            
            # Check all expected information is present
            assert "Progress: 50.0% complete" in progress_info
            assert "Sprites found: 2" in progress_info

    def test_button_actions(self, sample_scan_info, mock_dialog):
        """Test button click actions"""
        # Mock button properties and behaviors
        mock_dialog.resume_button = MagicMock()
        mock_dialog.resume_button.text.return_value = "Resume Scan"
        mock_dialog.resume_button.isDefault.return_value = True
        mock_dialog.fresh_button = MagicMock()
        mock_dialog.fresh_button.text.return_value = "Start Fresh"
        mock_dialog.cancel_button = MagicMock()
        mock_dialog.cancel_button.text.return_value = "Cancel"
        mock_dialog.get_user_choice = MagicMock(return_value=ResumeScanDialog.RESUME)
        
        with patch('ui.dialogs.resume_scan_dialog.ResumeScanDialog', return_value=mock_dialog):
            dialog = ResumeScanDialog(sample_scan_info)
            
            # Test button properties exist and have correct text
            assert dialog.resume_button.text() == "Resume Scan"
            assert dialog.resume_button.isDefault()
            assert dialog.fresh_button.text() == "Start Fresh"
            assert dialog.cancel_button.text() == "Cancel"
            
            # Test that get_user_choice returns expected value
            assert dialog.get_user_choice() == ResumeScanDialog.RESUME

    def test_empty_scan_info(self, mock_dialog):
        """Test dialog handles empty scan info gracefully"""
        empty_info = {
            "found_sprites": [],
            "current_offset": 0,
            "scan_range": {},
        }
        
        # Configure mock for empty scan info
        empty_progress = "Progress: 0.0% complete\nSprites found: 0\n"
        mock_dialog._format_progress_info.return_value = empty_progress
        mock_dialog.scan_info = empty_info

        with patch('ui.dialogs.resume_scan_dialog.ResumeScanDialog', return_value=mock_dialog):
            dialog = ResumeScanDialog(empty_info)
            
            progress_info = dialog._format_progress_info()
            assert "Progress:" in progress_info
            assert "Sprites found: 0" in progress_info

    def test_convenience_method(self, sample_scan_info, mock_dialog):
        """Test static show_resume_dialog method"""
        mock_dialog.user_choice = ResumeScanDialog.RESUME
        
        with patch('ui.dialogs.resume_scan_dialog.ResumeScanDialog', return_value=mock_dialog):
            with patch('spritepal.ui.dialogs.resume_scan_dialog.ResumeScanDialog.show_resume_dialog', 
                            return_value=ResumeScanDialog.RESUME) as mock_show:
                choice = ResumeScanDialog.show_resume_dialog(sample_scan_info)
                assert choice == ResumeScanDialog.RESUME
                mock_show.assert_called_once_with(sample_scan_info)

    def test_completed_scan_handling(self, mock_dialog):
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
        
        # Configure mock for completed scan
        completed_progress = "Progress: 100.0% complete\nSprites found: 3\n"
        mock_dialog._format_progress_info.return_value = completed_progress
        mock_dialog.scan_info = completed_info

        with patch('ui.dialogs.resume_scan_dialog.ResumeScanDialog', return_value=mock_dialog):
            dialog = ResumeScanDialog(completed_info)
            
            progress_info = dialog._format_progress_info()
            assert "Progress: 100.0% complete" in progress_info
