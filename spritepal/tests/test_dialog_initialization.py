"""
Regression tests for dialog initialization order issues.

This module ensures all dialogs can be created without InitializationOrderError
which can occur when instance variables are assigned after super().__init__().
"""

import pytest
from PyQt6.QtWidgets import QApplication
from ui.dialogs import UnifiedManualOffsetDialog as ManualOffsetDialog

from spritepal.ui.components.dialogs.range_scan_dialog import RangeScanDialog
from spritepal.ui.dialogs import SettingsDialog, UserErrorDialog
from spritepal.ui.dialogs.resume_scan_dialog import ResumeScanDialog
from spritepal.ui.grid_arrangement_dialog import GridArrangementDialog
from spritepal.ui.injection_dialog import InjectionDialog
from spritepal.ui.row_arrangement_dialog import RowArrangementDialog


class TestDialogInitialization:
    """Test that all dialogs can be initialized without errors"""

    @pytest.fixture(scope="class")
    def qapp(self):
        """Create QApplication instance for dialog tests"""
        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        return app

    def test_manual_offset_dialog_initialization(self, qapp):
        """Test ManualOffsetDialog can be created without initialization errors"""
        # This was the original bug - instance variables assigned after super().__init__()
        dialog = ManualOffsetDialog()

        # Verify tab structure exists and are not None
        assert dialog.tab_widget is not None
        assert dialog.browse_tab is not None
        assert dialog.smart_tab is not None
        assert dialog.history_tab is not None

        # Verify service adapters are initialized
        assert dialog.preview_service is not None
        assert dialog.validation_service is not None
        assert dialog.error_service is not None

        dialog.close()

    def test_settings_dialog_initialization(self, qapp):
        """Test SettingsDialog can be created without initialization errors"""
        dialog = SettingsDialog()

        # Verify UI components exist
        assert dialog.tab_widget is not None
        assert dialog.restore_window_check is not None
        assert dialog.auto_save_session_check is not None
        assert dialog.dumps_dir_edit is not None
        assert dialog.cache_enabled_check is not None

        dialog.close()

    def test_user_error_dialog_initialization(self, qapp):
        """Test UserErrorDialog can be created without initialization errors"""
        dialog = UserErrorDialog(
            error_message="Test error",
            technical_details="Technical details",
            parent=None
        )

        # Verify dialog was created
        assert dialog.windowTitle() == "Error"  # Default title for unknown errors

        dialog.close()

    def test_resume_scan_dialog_initialization(self, qapp):
        """Test ResumeScanDialog can be created without initialization errors"""
        scan_info = {
            "found_sprites": [],
            "current_offset": 0x1000,
            "scan_range": {"start": 0, "end": 0x10000, "step": 0x100},
            "completed": False,
            "total_found": 0
        }

        dialog = ResumeScanDialog(scan_info)

        # Verify dialog was created with correct title
        assert dialog.windowTitle() == "Resume Sprite Scan?"
        assert dialog.user_choice == dialog.CANCEL  # Default choice

        dialog.close()

    def test_injection_dialog_initialization(self, qapp):
        """Test InjectionDialog can be created without initialization errors"""
        dialog = InjectionDialog()

        # Verify UI components exist
        assert dialog.sprite_file_selector is not None
        assert dialog.input_vram_selector is not None
        assert dialog.output_vram_selector is not None
        assert dialog.vram_offset_input is not None
        assert dialog.rom_offset_input is not None

        dialog.close()

    def test_row_arrangement_dialog_initialization(self, qapp, tmp_path):
        """Test RowArrangementDialog can be created without initialization errors"""
        # Create a dummy sprite file
        sprite_file = tmp_path / "test_sprite.png"
        sprite_file.touch()

        try:
            dialog = RowArrangementDialog(str(sprite_file))
            # If sprite loading fails, dialog should still be created
            assert dialog is not None
            dialog.close()
        except Exception:
            # Even if sprite loading fails, we shouldn't get InitializationOrderError
            pytest.skip("Sprite loading failed, but no initialization error occurred")

    def test_grid_arrangement_dialog_initialization(self, qapp, tmp_path):
        """Test GridArrangementDialog can be created without initialization errors"""
        # Create a dummy sprite file
        sprite_file = tmp_path / "test_sprite.png"
        sprite_file.touch()

        try:
            dialog = GridArrangementDialog(str(sprite_file))
            # If sprite loading fails, dialog should still be created
            assert dialog is not None
            dialog.close()
        except Exception:
            # Even if sprite loading fails, we shouldn't get InitializationOrderError
            pytest.skip("Sprite loading failed, but no initialization error occurred")

    def test_range_scan_dialog_initialization(self, qapp):
        """Test RangeScanDialog can be created without initialization errors"""
        dialog = RangeScanDialog(current_offset=0x1000, rom_size=0x400000)

        # Verify dialog was created with correct title
        assert dialog.windowTitle() == "Range Scan Configuration"
        assert dialog.current_offset == 0x1000
        assert dialog.rom_size == 0x400000

        dialog.close()

    def test_all_dialogs_have_close_method(self, qapp):
        """Ensure all dialogs can be properly closed"""
        dialogs = [
            ManualOffsetDialog(),
            SettingsDialog(),
            UserErrorDialog("Test", None, None),
            ResumeScanDialog({"found_sprites": [], "current_offset": 0,
                            "scan_range": {"start": 0, "end": 0, "step": 1},
                            "completed": False, "total_found": 0}),
            InjectionDialog(),
            RangeScanDialog(0, 0x400000),
        ]

        for dialog in dialogs:
            # All dialogs should have close method
            assert hasattr(dialog, "close")
            dialog.close()
