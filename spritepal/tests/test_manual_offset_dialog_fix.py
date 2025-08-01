"""
Test the specific ManualOffsetDialog singleton fix.
Verifies the dialog survives parent deletion and can be reused.
"""

import pytest
from PyQt6.QtCore import Qt
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import QWidget, QPushButton

from spritepal.ui.dialogs.manual_offset_dialog import ManualOffsetDialog
from unittest.mock import Mock


@pytest.mark.gui
def test_manual_offset_dialog_survives_parent_deletion(qtbot):
    """Test the specific bug fix: dialog survives when ROM panel is deleted"""
    # Simulate the real scenario: ROM panel creates the dialog
    class MockROMPanel(QWidget):
        def __init__(self):
            super().__init__()
            self._manual_offset_dialog = None
            
        def open_manual_offset_dialog(self):
            if self._manual_offset_dialog is None:
                self._manual_offset_dialog = ManualOffsetDialog.get_instance(self)
            self._manual_offset_dialog.show()
            return self._manual_offset_dialog
    
    # Create ROM panel
    rom_panel = MockROMPanel()
    qtbot.addWidget(rom_panel)
    
    # Open dialog
    dialog = rom_panel.open_manual_offset_dialog()
    qtbot.addWidget(dialog)
    qtbot.waitUntil(dialog.isVisible)
    
    # Verify dialog has no parent (singleton safety)
    assert dialog.parent() is None
    
    # Simulate ROM panel being deleted (e.g., main window closes that tab)
    rom_panel.deleteLater()
    QTest.qWait(100)
    
    # Dialog should still be accessible and functional
    assert dialog.isVisible()
    
    # Close dialog
    dialog.close()
    qtbot.waitUntil(lambda: not dialog.isVisible())
    
    # Create new ROM panel
    rom_panel2 = MockROMPanel()
    qtbot.addWidget(rom_panel2)
    
    # Open dialog again - should work without "deleted C++ object" error
    dialog2 = rom_panel2.open_manual_offset_dialog()
    assert dialog2 is dialog  # Same singleton instance
    qtbot.waitUntil(dialog2.isVisible)
    
    # Access the widget that was causing crashes
    # Don't call set_rom_data as it needs a real extraction_manager
    # Instead, directly test the widget that was failing
    
    # This was the failing line in the bug report:
    # offset_widget.offset_slider.setMaximum(size)
    if hasattr(dialog2, 'offset_widget') and dialog2.offset_widget:
        if hasattr(dialog2.offset_widget, 'offset_slider'):
            # This should not raise "wrapped C/C++ object has been deleted"
            dialog2.offset_widget.offset_slider.setMaximum(0x800000)
    
    # Cleanup
    dialog2.close()
    ManualOffsetDialog._instance = None


@pytest.mark.gui  
def test_manual_offset_dialog_repeated_parent_changes(qtbot):
    """Test dialog survives multiple parent creation/deletion cycles"""
    for i in range(3):
        # Create parent
        parent = QWidget()
        qtbot.addWidget(parent)
        
        # Get dialog (parent ignored)
        dialog = ManualOffsetDialog.get_instance(parent)
        if i == 0:
            qtbot.addWidget(dialog)
        
        # Show dialog
        dialog.show()
        qtbot.waitUntil(dialog.isVisible)
        
        # Delete parent
        parent.deleteLater()
        QTest.qWait(50)
        
        # Dialog should still work
        assert dialog.offset_widget is not None
        
        # Hide dialog
        dialog.hide()
        qtbot.waitUntil(lambda: not dialog.isVisible())
    
    # Final cleanup
    ManualOffsetDialog._instance = None


@pytest.mark.gui
def test_dialog_window_modality_without_parent(qtbot):
    """Test parentless singleton has proper window modality"""
    dialog = ManualOffsetDialog.get_instance()
    qtbot.addWidget(dialog)
    
    # Should have application modal since it has no parent
    assert dialog.windowModality() == Qt.WindowModality.ApplicationModal
    
    # Should stay on top
    assert dialog.windowFlags() & Qt.WindowType.WindowStaysOnTopHint
    
    # Cleanup
    dialog.close()
    ManualOffsetDialog._instance = None