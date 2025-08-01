"""
Test dialog lifecycle to prevent Qt widget deletion issues.
These tests ensure dialogs can be safely opened, closed, and reopened.
"""

import pytest
from PyQt6.QtCore import Qt
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import QApplication

from spritepal.ui.dialogs.manual_offset_dialog import ManualOffsetDialog


class TestDialogLifecycle:
    """Test dialog lifecycle management"""

    @pytest.mark.gui
    def test_manual_offset_dialog_singleton_persistence(self, qtbot):
        """Test that ManualOffsetDialog singleton survives close/reopen cycles"""
        # Get first instance
        dialog1 = ManualOffsetDialog.get_instance()
        qtbot.addWidget(dialog1)
        
        # Verify WA_DeleteOnClose is disabled for singleton
        assert not dialog1.testAttribute(Qt.WidgetAttribute.WA_DeleteOnClose), \
            "Singleton dialogs must have WA_DeleteOnClose=False to prevent widget deletion"
        
        # Show dialog
        dialog1.show()
        qtbot.waitUntil(dialog1.isVisible)
        
        # Access a widget to ensure it exists
        assert dialog1.offset_widget is not None
        offset_widget1 = dialog1.offset_widget
        
        # Close dialog
        dialog1.close()
        qtbot.waitUntil(lambda: not dialog1.isVisible())
        
        # Get instance again - should be same object
        dialog2 = ManualOffsetDialog.get_instance()
        assert dialog2 is dialog1, "Singleton should return same instance"
        
        # Show dialog again
        dialog2.show()
        qtbot.waitUntil(dialog2.isVisible)
        
        # Verify widgets still exist and are accessible
        assert dialog2.offset_widget is not None
        assert dialog2.offset_widget is offset_widget1
        
        # Try to access the slider that was causing the crash
        if hasattr(dialog2.offset_widget, 'offset_slider'):
            # This should not raise "wrapped C/C++ object has been deleted"
            dialog2.offset_widget.offset_slider.setMaximum(1000)
        
        # Cleanup
        dialog2.close()
        ManualOffsetDialog._instance = None

    @pytest.mark.gui
    def test_singleton_dialog_always_parentless(self, qtbot):
        """Test singleton dialogs are created without parents for lifecycle safety"""
        from PyQt6.QtWidgets import QWidget
        
        # Create a parent widget
        parent = QWidget()
        qtbot.addWidget(parent)
        
        # Try to create dialog with parent
        dialog = ManualOffsetDialog.get_instance(parent)
        qtbot.addWidget(dialog)
        
        # Verify dialog has NO parent (singleton safety)
        assert dialog.parent() is None, "Singleton dialogs must be parentless to avoid deletion"
        
        # Verify proper window modality is set
        assert dialog.windowModality() == Qt.WindowModality.ApplicationModal
        
        # Show dialog
        dialog.show()
        qtbot.waitUntil(dialog.isVisible)
        
        # Delete the provided parent
        parent.deleteLater()
        QTest.qWait(100)  # Let deletion process
        
        # Dialog should still be accessible and functional
        assert dialog.offset_widget is not None
        if hasattr(dialog.offset_widget, 'offset_slider'):
            # This should work fine since dialog wasn't deleted
            dialog.offset_widget.offset_slider.setMaximum(2000)
        
        # Close and cleanup
        dialog.close()
        ManualOffsetDialog._instance = None

    def test_singleton_dialog_requirements(self):
        """Document requirements for singleton dialogs"""
        requirements = """
        Singleton Dialog Requirements:
        1. Must disable WA_DeleteOnClose (BaseDialog sets it to True)
        2. Must be created with parent=None to avoid deletion issues
        3. Should set appropriate window modality (e.g., ApplicationModal)
        4. get_instance() should ignore parent parameter
        
        Known singleton dialogs:
        - ManualOffsetDialog
        """
        
        # This test serves as documentation
        assert True, requirements


class TestDialogReopenScenarios:
    """Test various dialog reopen scenarios"""
    
    @pytest.mark.gui
    def test_non_singleton_dialog_lifecycle(self, qtbot):
        """Test that non-singleton dialogs are properly recreated"""
        from spritepal.ui.injection_dialog import InjectionDialog
        
        # Create first instance
        dialog1 = InjectionDialog(None, "test.png", "")
        qtbot.addWidget(dialog1)
        
        # Non-singleton dialogs CAN have DeleteOnClose
        # They should be recreated each time
        
        # Store the id
        id1 = id(dialog1)
        
        # Close dialog
        dialog1.close()
        
        # Create new instance - should be different object
        dialog2 = InjectionDialog(None, "test.png", "")
        qtbot.addWidget(dialog2)
        id2 = id(dialog2)
        
        assert id1 != id2, "Non-singleton dialogs should create new instances"
        
        # Cleanup
        dialog2.close()


def test_dialog_lifecycle_best_practices():
    """Document dialog lifecycle best practices"""
    best_practices = """
    Dialog Lifecycle Best Practices:
    
    1. BaseDialog sets WA_DeleteOnClose=True by default
       - Good for one-time dialogs
       - Bad for singletons or reusable dialogs
    
    2. Singleton dialogs MUST:
       - Set setAttribute(WA_DeleteOnClose, False)
       - Be created with parent=None
       - Implement proper cleanup in closeEvent
    
    3. Parent-child relationships:
       - When parent is deleted, ALL children are deleted
       - Singletons should not have parents
       - Use window modality instead of parent for dialog relationships
    
    4. Testing dialog lifecycle:
       - Test open → close → reopen scenarios
       - Test parent deletion scenarios
       - Use real Qt widgets, not mocks, for lifecycle tests
    """
    
    assert True, best_practices