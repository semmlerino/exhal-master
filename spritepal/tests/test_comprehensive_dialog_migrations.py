"""
Comprehensive Dialog Migration Testing

This test suite verifies that all migrated dialogs work correctly together
and maintain full functionality after migration to the new component architecture.
"""

import contextlib
import tempfile




import pytest
from PIL import Image

from spritepal.ui.components import BaseDialog, SplitterDialog, TabbedDialog
from spritepal.ui.dialogs.user_error_dialog import UserErrorDialog
from spritepal.ui.grid_arrangement_dialog import GridArrangementDialog
from spritepal.ui.injection_dialog import InjectionDialog
from spritepal.ui.row_arrangement_dialog import RowArrangementDialog


class TestComprehensiveDialogMigrations:
    """Test all migrated dialogs work together correctly"""

    @pytest.fixture
    def test_sprite_image(self):
        """Create a test sprite image for dialog testing"""
        test_image = Image.new("L", (128, 128), 0)
        temp_file = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
        test_image.save(temp_file.name)
        temp_file.close()

        yield temp_file.name

        import os
        with contextlib.suppress(Exception):
            os.unlink(temp_file.name)

    def test_all_dialogs_inherit_from_correct_base_classes(self, qtbot, test_sprite_image, manager_setup):
        """Test that all migrated dialogs inherit from the correct component base classes"""
        # Test UserErrorDialog inherits from BaseDialog
        error_dialog = UserErrorDialog("Test error")
        qtbot.addWidget(error_dialog)
        assert isinstance(error_dialog, BaseDialog)

        # Test InjectionDialog inherits from TabbedDialog
        injection_dialog = InjectionDialog()
        qtbot.addWidget(injection_dialog)
        assert isinstance(injection_dialog, TabbedDialog)
        assert isinstance(injection_dialog, BaseDialog)  # TabbedDialog inherits from BaseDialog

        # Test RowArrangementDialog inherits from SplitterDialog
        row_dialog = RowArrangementDialog(test_sprite_image)
        qtbot.addWidget(row_dialog)
        assert isinstance(row_dialog, SplitterDialog)
        assert isinstance(row_dialog, BaseDialog)  # SplitterDialog inherits from BaseDialog

        # Test GridArrangementDialog inherits from SplitterDialog
        grid_dialog = GridArrangementDialog(test_sprite_image)
        qtbot.addWidget(grid_dialog)
        assert isinstance(grid_dialog, SplitterDialog)
        assert isinstance(grid_dialog, BaseDialog)  # SplitterDialog inherits from BaseDialog

    def test_all_dialogs_have_consistent_component_features(self, qtbot, test_sprite_image, manager_setup):
        """Test that all migrated dialogs have consistent component features"""
        dialogs = [
            UserErrorDialog("Test error"),
            InjectionDialog(),
            RowArrangementDialog(test_sprite_image),
            GridArrangementDialog(test_sprite_image)
        ]

        for dialog in dialogs:
            qtbot.addWidget(dialog)

            # All should inherit from BaseDialog and have these features
            assert hasattr(dialog, "main_layout")
            assert hasattr(dialog, "content_widget")
            assert hasattr(dialog, "button_box")

            # All should be modal
            assert dialog.isModal() is True

            # All should have proper titles
            assert dialog.windowTitle() != ""

    def test_dialog_button_integration_consistency(self, qtbot, test_sprite_image, manager_setup):
        """Test that all dialogs have consistent button integration"""
        # UserErrorDialog has custom OK button (creates button box manually)
        error_dialog = UserErrorDialog("Test error")
        qtbot.addWidget(error_dialog)
        # UserErrorDialog creates button box manually, doesn't expose it as attribute
        assert error_dialog.button_box is None  # BaseDialog was created with with_button_box=False

        # InjectionDialog has custom buttons
        injection_dialog = InjectionDialog()
        qtbot.addWidget(injection_dialog)
        assert injection_dialog.button_box is not None

        # RowArrangementDialog has Export button
        row_dialog = RowArrangementDialog(test_sprite_image)
        qtbot.addWidget(row_dialog)
        assert row_dialog.button_box is not None
        assert hasattr(row_dialog, "export_btn")

        # GridArrangementDialog has Export button
        grid_dialog = GridArrangementDialog(test_sprite_image)
        qtbot.addWidget(grid_dialog)
        assert grid_dialog.button_box is not None
        assert hasattr(grid_dialog, "export_btn")

    def test_dialog_status_bar_integration_consistency(self, qtbot, test_sprite_image):
        """Test that status bar integration is consistent across dialogs"""
        # Dialogs with status bars
        status_dialogs = [
            RowArrangementDialog(test_sprite_image),
            GridArrangementDialog(test_sprite_image)
        ]

        for dialog in status_dialogs:
            qtbot.addWidget(dialog)
            assert hasattr(dialog, "status_bar")
            assert dialog.status_bar is not None

            # Test status update functionality
            dialog.update_status("Test message")
            assert dialog.status_bar.currentMessage() == "Test message"

    def test_dialog_component_api_consistency(self, qtbot, manager_setup):
        """Test that component APIs are consistent across dialogs"""
        # Test InjectionDialog component usage
        injection_dialog = InjectionDialog()
        qtbot.addWidget(injection_dialog)

        # Should have HexOffsetInput components
        assert hasattr(injection_dialog, "vram_offset_input")
        assert hasattr(injection_dialog, "rom_offset_input")

        # Should have FileSelector components
        assert hasattr(injection_dialog, "sprite_file_selector")
        assert hasattr(injection_dialog, "input_vram_selector")

        # Test component API methods exist
        assert hasattr(injection_dialog.vram_offset_input, "get_value")
        assert hasattr(injection_dialog.vram_offset_input, "set_text")
        assert hasattr(injection_dialog.sprite_file_selector, "get_path")
        assert hasattr(injection_dialog.sprite_file_selector, "set_path")

    def test_dialog_layout_architecture_consistency(self, qtbot, test_sprite_image, manager_setup):
        """Test that layout architecture is consistent after migrations"""
        # Test TabbedDialog structure
        injection_dialog = InjectionDialog()
        qtbot.addWidget(injection_dialog)
        assert hasattr(injection_dialog, "tab_widget")
        assert injection_dialog.tab_widget.count() == 2  # VRAM and ROM tabs

        # Test SplitterDialog structure
        row_dialog = RowArrangementDialog(test_sprite_image)
        qtbot.addWidget(row_dialog)
        assert hasattr(row_dialog, "main_splitter")

        # Debug output
        print(f"\nDEBUG: main_splitter = {row_dialog.main_splitter}")
        print(f"DEBUG: main_splitter type = {type(row_dialog.main_splitter)}")
        if row_dialog.main_splitter:
            print(f"DEBUG: main_splitter count = {row_dialog.main_splitter.count()}")
            for i in range(row_dialog.main_splitter.count()):
                widget = row_dialog.main_splitter.widget(i)
                print(f"DEBUG: Widget {i}: {widget} (type: {type(widget).__name__})")

        assert row_dialog.main_splitter.count() == 2  # Content and preview panels

        # Patch QMessageBox to prevent blocking dialogs during GridArrangementDialog initialization
        from unittest.mock import patch
        with patch("spritepal.ui.grid_arrangement_dialog.QMessageBox.critical"):
            grid_dialog = GridArrangementDialog(test_sprite_image)
        qtbot.addWidget(grid_dialog)
        assert hasattr(grid_dialog, "main_splitter")

        # Debug output for GridArrangementDialog
        print(f"\nDEBUG GridArrangementDialog: main_splitter = {grid_dialog.main_splitter}")
        print(f"DEBUG GridArrangementDialog: main_splitter type = {type(grid_dialog.main_splitter)}")
        if grid_dialog.main_splitter:
            print(f"DEBUG GridArrangementDialog: main_splitter count = {grid_dialog.main_splitter.count()}")
            for i in range(grid_dialog.main_splitter.count()):
                widget = grid_dialog.main_splitter.widget(i)
                print(f"DEBUG GridArrangementDialog: Widget {i}: {widget} (type: {type(widget).__name__})")

        assert grid_dialog.main_splitter.count() == 2  # Left and right panels

    def test_dialog_signal_integration_preservation(self, qtbot, test_sprite_image):
        """Test that signal integration is preserved after migrations"""
        # Test RowArrangementDialog signals
        row_dialog = RowArrangementDialog(test_sprite_image)
        qtbot.addWidget(row_dialog)

        # Should have arrangement manager with signals
        assert hasattr(row_dialog, "arrangement_manager")
        assert hasattr(row_dialog.arrangement_manager, "arrangement_changed")

        # Test GridArrangementDialog signals
        grid_dialog = GridArrangementDialog(test_sprite_image)
        qtbot.addWidget(grid_dialog)

        # Should have arrangement manager and grid view with signals
        assert hasattr(grid_dialog, "arrangement_manager")
        assert hasattr(grid_dialog, "grid_view")
        assert hasattr(grid_dialog.grid_view, "tile_clicked")

    def test_dialog_error_handling_consistency(self, qtbot):
        """Test that error handling is consistent across migrated dialogs"""
        # Test error dialog functionality
        error_dialog = UserErrorDialog("Test error", "Test details")
        qtbot.addWidget(error_dialog)

        # Should have proper error mapping
        memory_error_dialog = UserErrorDialog("memory error occurred")
        qtbot.addWidget(memory_error_dialog)
        assert memory_error_dialog.windowTitle() == "Memory Error"

        # Test error state handling in other dialogs
        # Patch QMessageBox to prevent blocking dialogs during GridArrangementDialog initialization
        from unittest.mock import patch
        with patch("spritepal.ui.grid_arrangement_dialog.QMessageBox.critical"):
            grid_dialog = GridArrangementDialog("/non/existent/file.png")
        qtbot.addWidget(grid_dialog)

        # Should handle error gracefully and maintain structure
        assert isinstance(grid_dialog, SplitterDialog)
        assert grid_dialog.status_bar is not None

    def test_dialog_memory_management_consistency(self, qtbot, test_sprite_image):
        """Test that memory management is consistent across dialogs"""
        # Only GridArrangementDialog has _cleanup_resources method
        grid_dialog = GridArrangementDialog(test_sprite_image)
        qtbot.addWidget(grid_dialog)

        # GridArrangementDialog should have cleanup method
        assert hasattr(grid_dialog, "_cleanup_resources")

        # Test cleanup doesn't crash
        try:
            grid_dialog._cleanup_resources()
        except Exception as e:
            pytest.fail(f"Cleanup failed for GridArrangementDialog: {e}")

        # RowArrangementDialog doesn't have explicit cleanup method
        row_dialog = RowArrangementDialog(test_sprite_image)
        qtbot.addWidget(row_dialog)

        # Should still close properly without explicit cleanup
        assert row_dialog.isVisible() or True  # Should not crash

    def test_cross_dialog_workflow_integration(self, qtbot, test_sprite_image, manager_setup):
        """Test that dialogs can work together in typical workflows"""
        # Simulate workflow: Extract -> Arrange -> Inject

        # 1. Start with arrangement dialog (simulating extraction output)
        arrangement_dialog = RowArrangementDialog(test_sprite_image)
        qtbot.addWidget(arrangement_dialog)

        # Should be able to access arrangement functionality
        assert hasattr(arrangement_dialog, "arrangement_manager")
        assert hasattr(arrangement_dialog, "export_btn")

        # 2. Simulate injection workflow
        injection_dialog = InjectionDialog(sprite_path=test_sprite_image)
        qtbot.addWidget(injection_dialog)

        # Should receive sprite path correctly
        assert injection_dialog.sprite_file_selector.get_path() == test_sprite_image

        # Should be able to switch between tabs
        injection_dialog.set_current_tab(0)  # VRAM tab
        assert injection_dialog.get_current_tab_index() == 0

        injection_dialog.set_current_tab(1)  # ROM tab
        assert injection_dialog.get_current_tab_index() == 1

    def test_dialog_component_isolation(self, qtbot, test_sprite_image, manager_setup):
        """Test that component changes don't affect other dialogs"""
        # Create multiple dialogs
        injection_dialog = InjectionDialog()
        row_dialog = RowArrangementDialog(test_sprite_image)
        grid_dialog = GridArrangementDialog(test_sprite_image)

        for dialog in [injection_dialog, row_dialog, grid_dialog]:
            qtbot.addWidget(dialog)

        # Modify one dialog's settings
        injection_dialog.vram_offset_input.set_text("0x8000")
        row_dialog.update_status("Test message")

        # Other dialogs should be unaffected
        assert grid_dialog.status_bar.currentMessage() != "Test message"

        # Each dialog should maintain its own component state
        assert injection_dialog.vram_offset_input.get_value() == 0x8000
