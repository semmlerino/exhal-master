"""
Smoke tests for dialog instantiation.

These tests ensure all dialogs can be created without errors,
particularly catching initialization order bugs where attributes
might be None when methods expect them to be initialized.
"""

import pytest
from unittest.mock import Mock, patch
from PyQt6.QtWidgets import QApplication

# Import all dialogs
from spritepal.ui.dialogs import (
    ManualOffsetDialog,
    SettingsDialog,
    UserErrorDialog,
    ResumeScanDialog,
)
from spritepal.ui.injection_dialog import InjectionDialog
from spritepal.ui.row_arrangement_dialog import RowArrangementDialog
from spritepal.ui.grid_arrangement_dialog import GridArrangementDialog


class TestDialogInstantiation:
    """Test that all dialogs can be instantiated without errors."""

    @pytest.fixture(autouse=True)
    def setup_qt_app(self, qapp):
        """Ensure Qt application is available."""
        pass

    def test_manual_offset_dialog_creation(self, qtbot):
        """Test ManualOffsetDialog can be created and used."""
        dialog = ManualOffsetDialog.get_instance()
        qtbot.addWidget(dialog)
        
        # Test that UI components are not None
        assert dialog.rom_map is not None
        assert dialog.offset_widget is not None
        assert dialog.scan_controls is not None
        assert dialog.import_export is not None
        assert dialog.status_panel is not None
        assert dialog.preview_widget is not None
        
        # Test that we can call basic methods that use these components
        # If any widget is None, this will raise AttributeError naturally
        # Don't call set_rom_data as it needs a real extraction_manager
        current_offset = dialog.get_current_offset()
        assert isinstance(current_offset, int)

    def test_settings_dialog_creation(self, qtbot):
        """Test SettingsDialog can be created."""
        dialog = SettingsDialog()
        qtbot.addWidget(dialog)
        
        # Test loading settings doesn't fail
        dialog._load_settings()
        
        # Test UI components exist
        assert hasattr(dialog, 'dumps_dir_edit')
        assert hasattr(dialog, 'cache_enabled_check')

    def test_injection_dialog_creation(self, qtbot):
        """Test InjectionDialog can be created."""
        with patch('spritepal.ui.injection_dialog.get_injection_manager'), \
             patch.object(InjectionDialog, '_load_metadata'), \
             patch.object(InjectionDialog, '_set_initial_paths'), \
             patch.object(InjectionDialog, '_load_rom_info'):
            dialog = InjectionDialog()
            qtbot.addWidget(dialog)
            
            # Test UI components exist
            assert hasattr(dialog, 'sprite_file_selector')
            assert hasattr(dialog, 'preview_widget')

    def test_user_error_dialog_creation(self, qtbot):
        """Test UserErrorDialog can be created."""
        # Constructor signature: (error_message, technical_details=None, parent=None)
        dialog = UserErrorDialog("Test Error", "Technical details about the error")
        qtbot.addWidget(dialog)
        
        # Dialog should display without errors
        assert "Error" in dialog.windowTitle()

    def test_resume_scan_dialog_creation(self, qtbot):
        """Test ResumeScanDialog can be created."""
        scan_info = {
            "found_sprites": [{"offset": 0x1000, "quality": 0.8}],
            "current_offset": 0x1000,
            "scan_range": {"start": 0, "end": 0x10000, "step": 0x20},
            "completed": False,
            "total_found": 1
        }
        dialog = ResumeScanDialog(scan_info)
        qtbot.addWidget(dialog)
        
        # Should have proper result values
        assert hasattr(dialog, 'RESUME')
        assert hasattr(dialog, 'START_FRESH')

    def test_row_arrangement_dialog_creation(self, qtbot):
        """Test RowArrangementDialog can be created."""
        # Create a temporary test file
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            test_file = f.name
            f.write(b"test data")
        
        try:
            with patch('spritepal.ui.row_arrangement_dialog.RowImageProcessor'):
                dialog = RowArrangementDialog(test_file, 16)
                qtbot.addWidget(dialog)
                
                # Test UI components exist
                assert hasattr(dialog, 'available_rows_widget')
                assert hasattr(dialog, 'arranged_rows_widget')
        finally:
            import os
            if os.path.exists(test_file):
                os.unlink(test_file)

    def test_grid_arrangement_dialog_creation(self, qtbot):
        """Test GridArrangementDialog can be created."""
        # Create a temporary test file
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            test_file = f.name
            f.write(b"test data")
        
        try:
            with patch('spritepal.ui.grid_arrangement_dialog.extract_tiles'):
                dialog = GridArrangementDialog(test_file, 16)
                qtbot.addWidget(dialog)
                
                # Test UI components exist
                assert hasattr(dialog, 'source_list')
                assert hasattr(dialog, 'arranged_list')
        finally:
            import os
            if os.path.exists(test_file):
                os.unlink(test_file)


class TestDialogMethodCalls:
    """Test that dialog methods can be called without AttributeError."""

    def test_manual_offset_dialog_methods(self, qtbot):
        """Test ManualOffsetDialog methods don't fail on None attributes."""
        dialog = ManualOffsetDialog.get_instance()
        qtbot.addWidget(dialog)
        
        # These methods should not raise AttributeError
        methods_to_test = [
            ('_update_status', ("Test status",)),
            ('_create_left_panel', ()),
            ('_create_right_panel', ()),
            ('toggle_fullscreen', ()),
        ]
        
        for method_name, args in methods_to_test:
            method = getattr(dialog, method_name, None)
            if method and callable(method):
                # If widgets are not properly initialized (None), 
                # calling these methods will raise AttributeError
                # No need to catch and assert - let it fail naturally
                method(*args)


class TestInitializationOrder:
    """Specific tests for initialization order issues."""

    def test_no_overwritten_widgets(self, qtbot):
        """Test that widgets created in _setup methods aren't overwritten."""
        dialog = ManualOffsetDialog.get_instance()
        qtbot.addWidget(dialog)
        
        # After initialization, all widget attributes should be widgets, not None
        widget_attrs = [
            'rom_map', 'offset_widget', 'scan_controls',
            'import_export', 'status_panel', 'preview_widget'
        ]
        
        for attr in widget_attrs:
            widget = getattr(dialog, attr, None)
            assert widget is not None, f"Widget {attr} is None after initialization"
            # Should be a QWidget subclass, not None
            from PyQt6.QtWidgets import QWidget
            assert isinstance(widget, QWidget), \
                f"Widget {attr} is {type(widget)}, not a QWidget"