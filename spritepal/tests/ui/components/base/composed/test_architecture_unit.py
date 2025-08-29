
from __future__ import annotations

pytestmark = [
    pytest.mark.ci_safe,
    pytest.mark.dialog,
    pytest.mark.headless,
    pytest.mark.qt_real,
    pytest.mark.signals_slots,
    pytest.mark.slow,
    pytest.mark.unit,
]
"""
Unit tests for ComposedDialog architecture components.

These tests validate the architecture without requiring Qt widgets,
making them suitable for headless environments.
"""

import pytest
import sys
from unittest.mock import Mock, MagicMock, patch

# Helper functions for creating proper Qt mocks (defined first)
def create_mock_qobject():
    """Create a properly configured QObject mock."""
    mock = Mock()
    return mock

def create_mock_signal(*args, **kwargs):
    """Create a properly configured Signal mock with emit method."""
    mock = Mock()
    mock.emit = Mock()
    mock.connect = Mock()
    return mock

def create_mock_standard_button():
    """Create a mock StandardButton enum that supports bitwise operations."""
    class MockStandardButton:
        def __init__(self, value):
            self.value = value
            
        def __or__(self, other):
            return MockStandardButton(self.value | other.value)
            
        def __eq__(self, other):
            return isinstance(other, MockStandardButton) and self.value == other.value
    
    # Create enum-like object
    mock_enum = Mock()
    mock_enum.Ok = MockStandardButton(1)
    mock_enum.Cancel = MockStandardButton(2)
    mock_enum.Yes = MockStandardButton(4)
    mock_enum.No = MockStandardButton(8)
    
    return mock_enum

def create_mock_button_box(*args, **kwargs):
    """Create a properly configured QDialogButtonBox mock."""
    mock_box = Mock()
    mock_box.accepted = create_mock_signal()
    mock_box.rejected = create_mock_signal()
    mock_box.addButton = Mock(return_value=Mock())  # Returns QPushButton mock
    mock_box.removeButton = Mock()
    mock_box.button = Mock(return_value=Mock())
    return mock_box

# Mock Qt modules before any imports
sys.modules['PySide6'] = Mock()
sys.modules['PySide6.QtCore'] = Mock()
sys.modules['PySide6.QtWidgets'] = Mock()
sys.modules['PySide6.QtGui'] = Mock()

# Set up proper mock objects for the classes we need
qt_core = sys.modules['PySide6.QtCore']
qt_widgets = sys.modules['PySide6.QtWidgets']

# Mock QObject - create a class that behaves like QObject for inheritance
class MockQObject:
    def __init__(self, parent=None):
        pass  # Do nothing

# Mock QWidget that supports union operations for type hints
class MockQWidget:
    def __init__(self, parent=None):
        pass
    
    def __or__(self, other):
        """Support type union operations like QWidget | None"""
        return type('UnionType', (), {})  # Return a simple type-like object
    
    def __ror__(self, other):
        """Support reverse union operations like None | QWidget"""
        return type('UnionType', (), {})  # Return a simple type-like object

# Make MockQWidget itself support union operations
MockQWidget.__or__ = lambda self, other: type('UnionType', (), {})
MockQWidget.__ror__ = lambda self, other: type('UnionType', (), {})

qt_core.QObject = MockQObject
qt_widgets.QWidget = MockQWidget

# Set up Signal mock that accepts arguments and returns proper signals
qt_core.Signal = Mock(side_effect=create_mock_signal)

# Set up common Qt widgets that can be called multiple times
def create_mock_qdialog(*args, **kwargs):
    """Create a mock QDialog that can be called multiple times."""
    return Mock()

def create_mock_qvboxlayout(*args, **kwargs):
    """Create a mock QVBoxLayout that can be called multiple times."""
    return Mock()

# Make the classes themselves callable multiple times
qt_widgets.QDialog = type('MockQDialog', (), {
    '__init__': lambda self, *args, **kwargs: None,
    '__call__': create_mock_qdialog
})()
qt_widgets.QVBoxLayout = type('MockQVBoxLayout', (), {
    '__init__': lambda self, *args, **kwargs: None,
    '__call__': create_mock_qvboxlayout
})()

# But make them respond to attribute access like classes
qt_widgets.QDialog = Mock()
qt_widgets.QVBoxLayout = Mock()

# Set up QMessageBox with all methods
mock_message_box = Mock()
mock_message_box.critical = Mock()
mock_message_box.information = Mock()
mock_message_box.warning = Mock()
mock_message_box.question = Mock(return_value=Mock())
mock_message_box.StandardButton = Mock()
mock_message_box.StandardButton.Yes = Mock()
qt_widgets.QMessageBox = mock_message_box

# Set up QDialogButtonBox
qt_widgets.QDialogButtonBox = Mock(side_effect=create_mock_button_box)
qt_widgets.QDialogButtonBox.StandardButton = create_mock_standard_button()
qt_widgets.QDialogButtonBox.ButtonRole = Mock()
qt_widgets.QDialogButtonBox.ButtonRole.ActionRole = Mock()

# Set up QStatusBar
qt_widgets.QStatusBar = Mock(side_effect=lambda *args, **kwargs: Mock())

# Mock QPushButton
qt_widgets.QPushButton = Mock(side_effect=lambda *args, **kwargs: Mock())

# Mock QPixmap for type aliases - make it support union operations
class MockQPixmap:
    def __init__(self, *args, **kwargs):
        pass
    
    def __or__(self, other):
        """Support type union operations like QPixmap | None"""
        return type('UnionType', (), {})
    
    def __ror__(self, other):
        """Support reverse union operations like None | QPixmap"""
        return type('UnionType', (), {})

# Make MockQPixmap itself support union operations too
MockQPixmap.__or__ = lambda self, other: type('UnionType', (), {})
MockQPixmap.__ror__ = lambda self, other: type('UnionType', (), {})

qt_gui = sys.modules['PySide6.QtGui']
qt_gui.QPixmap = MockQPixmap

class TestDialogContextUnit:
    """Unit tests for DialogContext."""
    
    def test_context_initialization(self):
        """Test DialogContext can be created with required fields."""
        from ui.components.base.composed.dialog_context import DialogContext
        
        mock_dialog = Mock()
        mock_layout = Mock()
        mock_widget = Mock()
        
        context = DialogContext(
            dialog=mock_dialog,
            main_layout=mock_layout,
            content_widget=mock_widget
        )
        
        assert context.dialog == mock_dialog
        assert context.main_layout == mock_layout
        assert context.content_widget == mock_widget
        assert context.button_box is None
        assert context.status_bar is None
        assert context.config == {}
        assert context.components == {}
    
    def test_component_registration(self):
        """Test component registration and retrieval."""
        from ui.components.base.composed.dialog_context import DialogContext
        
        context = DialogContext(
            dialog=Mock(),
            main_layout=Mock(),
            content_widget=Mock()
        )
        
        component = Mock()
        context.register_component("test", component)
        
        assert context.has_component("test")
        assert context.get_component("test") == component
        assert not context.has_component("nonexistent")
        assert context.get_component("nonexistent") is None
    
    def test_component_unregistration(self):
        """Test component unregistration."""
        from ui.components.base.composed.dialog_context import DialogContext
        
        context = DialogContext(
            dialog=Mock(),
            main_layout=Mock(),
            content_widget=Mock()
        )
        
        component = Mock()
        context.register_component("test", component)
        assert context.has_component("test")
        
        context.unregister_component("test")
        assert not context.has_component("test")
        
        # Unregistering non-existent should not raise
        context.unregister_component("nonexistent")

class TestMessageDialogManagerUnit:
    """Unit tests for MessageDialogManager."""
    
    def test_manager_initialization(self):
        """Test MessageDialogManager initialization."""
        from ui.components.base.composed.message_dialog_manager import MessageDialogManager
        from ui.components.base.composed.dialog_context import DialogContext
        
        manager = MessageDialogManager()
        assert not manager.is_initialized
        
        # Create a mock dialog with required methods
        mock_dialog = Mock()
        mock_dialog.accept = Mock()
        mock_dialog.reject = Mock()
        
        context = DialogContext(
            dialog=mock_dialog,
            main_layout=Mock(), 
            content_widget=Mock()
        )
        
        manager.initialize(context)
        assert manager.is_initialized
    
    def test_manager_cleanup(self):
        """Test MessageDialogManager cleanup."""
        from ui.components.base.composed.message_dialog_manager import MessageDialogManager
        from ui.components.base.composed.dialog_context import DialogContext
        
        manager = MessageDialogManager()
        
        # Create a mock dialog with required methods
        mock_dialog = Mock()
        mock_dialog.accept = Mock()
        mock_dialog.reject = Mock()
        
        context = DialogContext(
            dialog=mock_dialog,
            main_layout=Mock(),
            content_widget=Mock()
        )
        
        manager.initialize(context)
        assert manager.is_initialized
        
        manager.cleanup()
        assert not manager.is_initialized
    
    def test_uninitialized_error(self):
        """Test error when using uninitialized manager."""
        from ui.components.base.composed.message_dialog_manager import MessageDialogManager
        
        manager = MessageDialogManager()
        
        with pytest.raises(RuntimeError, match="not initialized"):
            manager.show_error("Title", "Message")
    
    def test_show_error_message(self):
        """Test showing error message."""
        from ui.components.base.composed.message_dialog_manager import MessageDialogManager
        from ui.components.base.composed.dialog_context import DialogContext
        
        # Reset the mock to ensure clean state
        mock_message_box.critical.reset_mock()
        
        manager = MessageDialogManager()
        
        # Create a mock dialog
        mock_dialog = Mock()
        mock_dialog.accept = Mock()
        mock_dialog.reject = Mock()
        
        context = DialogContext(
            dialog=mock_dialog,
            main_layout=Mock(),
            content_widget=Mock()
        )
        
        manager.initialize(context)
        
        # Test showing error
        manager.show_error("Error Title", "Error Message")
        
        # Verify message box was called
        mock_message_box.critical.assert_called_once_with(mock_dialog, "Error Title", "Error Message")

class TestStatusBarManagerUnit:
    """Unit tests for StatusBarManager."""
    
    def test_manager_with_status_bar_enabled(self):
        """Test StatusBarManager when status bar is enabled."""
        from ui.components.base.composed.status_bar_manager import StatusBarManager
        from ui.components.base.composed.dialog_context import DialogContext
        
        # Create a specific mock for this test
        mock_status_bar = Mock()
        # Override the global QStatusBar mock for this test
        original_qstatusbar = qt_widgets.QStatusBar
        qt_widgets.QStatusBar = Mock(return_value=mock_status_bar)
        
        try:
            mock_dialog = Mock()
            mock_layout = Mock()
            
            context = DialogContext(
                dialog=mock_dialog,
                main_layout=mock_layout,
                content_widget=Mock(),
                config={'with_status_bar': True}
            )
            
            manager = StatusBarManager()
            manager.initialize(context)
            
            # The manager should have created a status bar
            assert manager.status_bar is not None
            assert context.status_bar is not None
            assert manager.is_available
            
            # In mock environment, the manager detects this and creates mock objects
            # We just need to verify it worked correctly
            # Note: The manager has built-in mock detection and handles this case
        finally:
            # Restore original mock
            qt_widgets.QStatusBar = original_qstatusbar
    
    def test_manager_with_status_bar_disabled(self):
        """Test StatusBarManager when status bar is disabled."""
        from ui.components.base.composed.status_bar_manager import StatusBarManager
        from ui.components.base.composed.dialog_context import DialogContext
        
        context = DialogContext(
            dialog=Mock(),
            main_layout=Mock(),
            content_widget=Mock(),
            config={'with_status_bar': False}
        )
        
        manager = StatusBarManager()
        manager.initialize(context)
        
        assert manager.status_bar is None
        assert context.status_bar is None
        assert not manager.is_available

class TestButtonBoxManagerUnit:
    """Unit tests for ButtonBoxManager."""
    
    def test_manager_with_button_box_enabled(self):
        """Test ButtonBoxManager when button box is enabled."""
        from ui.components.base.composed.button_box_manager import ButtonBoxManager
        from ui.components.base.composed.dialog_context import DialogContext
        
        # Create a specific mock for this test
        mock_button_box = create_mock_button_box()
        # Override the global QDialogButtonBox mock for this test
        original_qdialogbuttonbox = qt_widgets.QDialogButtonBox
        qt_widgets.QDialogButtonBox = Mock(return_value=mock_button_box)
        qt_widgets.QDialogButtonBox.StandardButton = create_mock_standard_button()
        
        try:
            mock_dialog = Mock()
            mock_dialog.accept = Mock()
            mock_dialog.reject = Mock()
            mock_layout = Mock()
            
            context = DialogContext(
                dialog=mock_dialog,
                main_layout=mock_layout,
                content_widget=Mock(),
                config={'with_button_box': True}
            )
            
            manager = ButtonBoxManager()
            manager.initialize(context)
            
            # The manager should have created a button box
            assert manager.button_box is not None
            assert context.button_box is not None
            assert manager.is_available
            
            # In mock environment, the manager detects this and creates mock objects
            # We just need to verify it worked correctly
            # Note: The manager has built-in mock detection and handles this case
        finally:
            # Restore original mock
            qt_widgets.QDialogButtonBox = original_qdialogbuttonbox
    
    def test_manager_with_button_box_disabled(self):
        """Test ButtonBoxManager when button box is disabled."""
        from ui.components.base.composed.button_box_manager import ButtonBoxManager
        from ui.components.base.composed.dialog_context import DialogContext
        
        context = DialogContext(
            dialog=Mock(),
            main_layout=Mock(),
            content_widget=Mock(),
            config={'with_button_box': False}
        )
        
        manager = ButtonBoxManager()
        manager.initialize(context)
        
        assert manager.button_box is None
        assert context.button_box is None
        assert not manager.is_available
    
    def test_add_custom_button(self):
        """Test adding a custom button."""
        from ui.components.base.composed.button_box_manager import ButtonBoxManager
        from ui.components.base.composed.dialog_context import DialogContext
        
        # Create a specific mock for this test
        mock_button_box = create_mock_button_box()
        # Override the global QDialogButtonBox mock for this test
        original_qdialogbuttonbox = qt_widgets.QDialogButtonBox
        qt_widgets.QDialogButtonBox = Mock(return_value=mock_button_box)
        qt_widgets.QDialogButtonBox.StandardButton = create_mock_standard_button()
        qt_widgets.QDialogButtonBox.ButtonRole = Mock()
        qt_widgets.QDialogButtonBox.ButtonRole.ActionRole = Mock()
        
        try:
            mock_dialog = Mock()
            mock_dialog.accept = Mock()
            mock_dialog.reject = Mock()
            
            context = DialogContext(
                dialog=mock_dialog,
                main_layout=Mock(),
                content_widget=Mock(),
                config={'with_button_box': True}
            )
            
            manager = ButtonBoxManager()
            manager.initialize(context)
            
            # Add custom button
            button = manager.add_button("Custom", callback=lambda: print("clicked"))
            
            assert button is not None
            assert manager.custom_button_count == 1
            # In mock environment, the manager detects this and handles mock behavior
            # The button is still created and tracked correctly
        finally:
            # Restore original mock
            qt_widgets.QDialogButtonBox = original_qdialogbuttonbox

class TestComposedDialogArchitecture:
    """Test the overall architecture integration."""
    
    def test_architecture_design_principles(self):
        """Test that the architecture follows composition principles."""
        from ui.components.base.composed.dialog_context import DialogContext
        from ui.components.base.composed.message_dialog_manager import MessageDialogManager
        from ui.components.base.composed.button_box_manager import ButtonBoxManager
        from ui.components.base.composed.status_bar_manager import StatusBarManager
        
        # Test that all managers can be created independently
        message_manager = MessageDialogManager()
        assert not message_manager.is_initialized
        
        button_manager = ButtonBoxManager()
        assert not button_manager.is_available
        
        status_manager = StatusBarManager()
        assert not status_manager.is_available
        
        # Test that they can all work with the same context
        context = DialogContext(
            dialog=Mock(),
            main_layout=Mock(),
            content_widget=Mock(),
            config={'with_button_box': True, 'with_status_bar': True}
        )
        
        # Initialize all managers with the same context
        message_manager.initialize(context)
        button_manager.initialize(context)
        status_manager.initialize(context)
        
        # All should be properly initialized
        assert message_manager.is_initialized
        assert button_manager.is_available
        assert status_manager.is_available
        
        # Context should contain all components
        context.register_component("messages", message_manager)
        context.register_component("button_box", button_manager)
        context.register_component("status_bar", status_manager)
        
        assert context.has_component("messages")
        assert context.has_component("button_box") 
        assert context.has_component("status_bar")
    
    def test_component_lifecycle_management(self):
        """Test proper component lifecycle management."""
        from ui.components.base.composed.dialog_context import DialogContext
        from ui.components.base.composed.message_dialog_manager import MessageDialogManager
        from ui.components.base.composed.button_box_manager import ButtonBoxManager
        
        # Create context and managers
        context = DialogContext(
            dialog=Mock(),
            main_layout=Mock(),
            content_widget=Mock(),
            config={'with_button_box': True}
        )
        
        message_manager = MessageDialogManager()
        button_manager = ButtonBoxManager()
        
        # Initialize
        message_manager.initialize(context)
        button_manager.initialize(context)
        
        # Register components
        context.register_component("messages", message_manager)
        context.register_component("button_box", button_manager)
        
        assert context.has_component("messages")
        assert context.has_component("button_box")
        
        # Clean up - should be able to unregister
        context.unregister_component("messages")
        context.unregister_component("button_box")
        
        assert not context.has_component("messages")
        assert not context.has_component("button_box")
        
        # Managers should still work independently
        message_manager.cleanup()
        button_manager.cleanup()
        
        assert not message_manager.is_initialized
        assert not button_manager.is_available

if __name__ == "__main__":
    pytest.main([__file__, "-v"])