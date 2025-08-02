"""
Test the ManualOffsetDialog fix.
Verifies the dialog works properly with normal Qt lifecycle management.
"""


import pytest
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QWidget
from ui.dialogs.manual_offset_dialog_simplified import (
    ManualOffsetDialogSimplified as ManualOffsetDialog,
)


@pytest.mark.gui
def test_manual_offset_dialog_normal_lifecycle(qtbot):
    """Test the dialog works with normal Qt lifecycle management"""
    # Simulate the real scenario: ROM panel creates the dialog
    class MockROMPanel(QWidget):
        def __init__(self):
            super().__init__()
            self._manual_offset_dialog = None

        def open_manual_offset_dialog(self):
            if self._manual_offset_dialog is None or not self._manual_offset_dialog.isVisible():
                if self._manual_offset_dialog is not None:
                    self._manual_offset_dialog.deleteLater()
                self._manual_offset_dialog = ManualOffsetDialog(self)
            self._manual_offset_dialog.show()
            return self._manual_offset_dialog

    # Create ROM panel
    rom_panel = MockROMPanel()
    qtbot.addWidget(rom_panel)

    # Open dialog
    dialog = rom_panel.open_manual_offset_dialog()
    # Don't register with qtbot since dialog has parent and WA_DeleteOnClose
    qtbot.waitUntil(dialog.isVisible)

    # Verify dialog has the panel as parent
    assert dialog.parent() == rom_panel

    # Access the widget that was causing crashes
    # This was the failing line in the bug report:
    # offset_widget.offset_slider.setMaximum(size)
    if hasattr(dialog, "offset_widget") and dialog.offset_widget:
        if hasattr(dialog.offset_widget, "offset_slider"):
            # This should not raise "wrapped C/C++ object has been deleted"
            dialog.offset_widget.offset_slider.setMaximum(0x800000)

    # Close dialog
    dialog.close()
    qtbot.waitUntil(lambda: not dialog.isVisible())

    # Create another dialog - should be a new instance
    dialog2 = rom_panel.open_manual_offset_dialog()
    assert dialog2 != dialog  # Different instances
    qtbot.waitUntil(dialog2.isVisible)

    # Cleanup
    dialog2.close()


@pytest.mark.gui
def test_manual_offset_dialog_multiple_instances(qtbot):
    """Test multiple dialog instances can be created and managed"""
    dialogs = []
    parents = []

    for _i in range(3):
        # Create parent
        parent = QWidget()
        qtbot.addWidget(parent)
        parents.append(parent)

        # Create new dialog instance
        # Don't register with qtbot since WA_DeleteOnClose will handle cleanup
        dialog = ManualOffsetDialog(parent)
        dialogs.append(dialog)

        # Show dialog
        dialog.show()
        qtbot.waitUntil(dialog.isVisible)

        # Dialog should work
        assert dialog.offset_widget is not None
        assert dialog.parent() == parent

        # Hide dialog
        dialog.hide()
        qtbot.waitUntil(lambda: not dialog.isVisible())

    # All dialogs should be independent
    assert len(set(dialogs)) == 3  # All unique instances

    # Cleanup
    for dialog in dialogs:
        dialog.close()


@pytest.mark.gui
def test_dialog_window_properties(qtbot):
    """Test dialog has proper window properties"""
    parent = QWidget()
    qtbot.addWidget(parent)

    dialog = ManualOffsetDialog(parent)
    # Don't register with qtbot since dialog has parent and WA_DeleteOnClose

    # Should not be modal by default (modal=False in __init__)
    assert not dialog.isModal()

    # Should not have stay on top flag anymore
    assert not (dialog.windowFlags() & Qt.WindowType.WindowStaysOnTopHint)

    # Should have standard dialog flags
    assert dialog.windowFlags() & Qt.WindowType.Dialog

    # Cleanup
    dialog.close()
