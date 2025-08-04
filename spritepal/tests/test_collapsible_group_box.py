"""
Test the CollapsibleGroupBox component, focusing on exception handling
and Qt runtime error scenarios.

This tests the Phase 1 critical bug fix for animation disconnection
and Qt object deletion error handling.
"""

import pytest
from unittest.mock import Mock, patch
from PyQt6.QtWidgets import QVBoxLayout, QLabel
from PyQt6.QtCore import QPropertyAnimation
from PyQt6.QtTest import QTest

from spritepal.ui.common.collapsible_group_box import CollapsibleGroupBox


class TestCollapsibleGroupBox:
    """Test CollapsibleGroupBox widget and exception handling"""

    def test_basic_initialization(self, qtbot):
        """Test basic widget initialization"""
        widget = CollapsibleGroupBox("Test Title")
        qtbot.addWidget(widget)
        
        assert widget._title_label.text() == "Test Title"
        assert widget.is_collapsed() is False  # Default expanded

    def test_collapse_expand_functionality(self, qtbot):
        """Test basic collapse/expand functionality"""
        widget = CollapsibleGroupBox("Test")
        qtbot.addWidget(widget)
        
        # Add some content
        content = QLabel("Test content")
        layout = QVBoxLayout()
        layout.addWidget(content)
        widget.setLayout(layout)
        
        # Test collapse
        widget.set_collapsed(True)
        QTest.qWait(200)  # Wait for animation
        assert widget.is_collapsed() is True
        
        # Test expand
        widget.set_collapsed(False)
        QTest.qWait(200)  # Wait for animation
        assert widget.is_collapsed() is False

    def test_animation_connection_cleanup_runtime_error(self, qtbot):
        """Test handling of Qt runtime errors during animation disconnection"""
        widget = CollapsibleGroupBox("Test")
        qtbot.addWidget(widget)
        
        # Create a mock animation that will raise RuntimeError on disconnect
        mock_animation = Mock(spec=QPropertyAnimation)
        
        # Mock connection that raises RuntimeError with Qt deletion message
        def raise_qt_deletion_error():
            raise RuntimeError("wrapped C/C++ object has been deleted")
        
        # Mock connection that raises RuntimeError with different message
        def raise_other_runtime_error():
            raise RuntimeError("some other runtime error")
        
        # Set up mock connections
        widget._animation = mock_animation
        widget._animation_connections = [
            raise_qt_deletion_error,  # Should be caught and ignored
            raise_other_runtime_error,  # Should be re-raised
        ]
        
        # Test that Qt deletion errors are caught but other RuntimeErrors are not
        # Use set_collapsed to trigger the animation stopping logic
        with pytest.raises(RuntimeError, match="some other runtime error"):
            widget.set_collapsed(True)
        
        # Verify animation.stop() was called
        mock_animation.stop.assert_called_once()

    def test_animation_connection_cleanup_type_error(self, qtbot):
        """Test handling of TypeError during animation disconnection"""
        widget = CollapsibleGroupBox("Test")
        qtbot.addWidget(widget)
        
        # Create mock animation
        mock_animation = Mock(spec=QPropertyAnimation)
        
        # Mock connection that raises TypeError
        def raise_type_error():
            raise TypeError("incompatible connection signature")
        
        # Set up mock connections that will cause errors during cleanup
        widget._animation = mock_animation
        original_problematic_connections = [raise_type_error]
        widget._animation_connections = original_problematic_connections[:]
        
        # Should not raise exception - TypeError should be caught during cleanup
        # Use set_collapsed to trigger the animation stopping logic  
        widget.set_collapsed(True)
        
        # Verify animation.stop() was called
        mock_animation.stop.assert_called_once()
        
        # The problematic connections should have been cleared during cleanup,
        # and new connections for the collapse animation should now exist
        assert widget._animation_connections != original_problematic_connections
        # New connections should be created for the new animation
        assert len(widget._animation_connections) > 0

    def test_animation_connection_cleanup_success(self, qtbot):
        """Test successful animation connection cleanup"""
        widget = CollapsibleGroupBox("Test")
        qtbot.addWidget(widget)
        
        # Create mock animation
        mock_animation = Mock(spec=QPropertyAnimation)
        
        # Mock successful connections
        mock_connection1 = Mock()
        mock_connection2 = Mock()
        
        # Set up mock connections that should be cleaned up
        widget._animation = mock_animation
        original_connections = [mock_connection1, mock_connection2]
        widget._animation_connections = original_connections[:]
        
        # Should successfully disconnect all connections
        # Use set_collapsed to trigger the animation stopping logic
        widget.set_collapsed(True)
        
        # Verify all original connections were called during cleanup
        mock_connection1.assert_called_once()
        mock_connection2.assert_called_once()
        mock_animation.stop.assert_called_once()
        
        # Original connections should be gone, new ones should exist for new animation
        assert widget._animation_connections != original_connections
        assert len(widget._animation_connections) > 0

    def test_mixed_animation_connection_errors(self, qtbot):
        """Test handling of mixed success and error scenarios"""
        widget = CollapsibleGroupBox("Test")
        qtbot.addWidget(widget)
        
        # Create mock animation
        mock_animation = Mock(spec=QPropertyAnimation)
        
        # Create various connection scenarios
        successful_connection = Mock()
        
        def qt_deletion_error():
            raise RuntimeError("wrapped C/C++ object has been deleted")
        
        def type_error():
            raise TypeError("bad signature")
        
        successful_connection2 = Mock()
        
        # Set up mixed connections
        widget._animation = mock_animation
        widget._animation_connections = [
            successful_connection,
            qt_deletion_error,      # Should be caught
            type_error,             # Should be caught
            successful_connection2,
        ]
        
        # Should complete without exceptions
        # Use set_collapsed to trigger the animation stopping logic
        widget.set_collapsed(True)
        
        # Verify successful connections were called during cleanup
        successful_connection.assert_called_once()
        successful_connection2.assert_called_once()
        mock_animation.stop.assert_called_once()
        # Original connections should be cleared, new ones created for new animation
        assert len(widget._animation_connections) > 0

    def test_no_animation_to_stop(self, qtbot):
        """Test animation stopping when no animation exists"""
        widget = CollapsibleGroupBox("Test")
        qtbot.addWidget(widget)
        
        # Ensure no animation is set
        widget._animation = None
        widget._animation_connections = []
        
        # Should complete without error
        # Use set_collapsed to trigger the animation stopping logic
        widget.set_collapsed(True)
        
        # When _animation is None, no connections should be created
        # This tests that the method handles the None case gracefully
        assert len(widget._animation_connections) == 0

    def test_animation_connection_non_callable(self, qtbot):
        """Test handling of non-callable objects in connection list"""
        widget = CollapsibleGroupBox("Test")
        qtbot.addWidget(widget)
        
        # Create mock animation
        mock_animation = Mock(spec=QPropertyAnimation)
        
        # Set up connections with non-callable
        widget._animation = mock_animation
        widget._animation_connections = [
            "not_callable",  # This should cause TypeError
            Mock(),          # This should work
        ]
        
        # Should complete without raising exception
        # Use set_collapsed to trigger the animation stopping logic
        widget.set_collapsed(True)
        
        # Verify animation was stopped and new connections created
        mock_animation.stop.assert_called_once()
        # New connections should be created for the new animation
        assert len(widget._animation_connections) > 0

    def test_qt_object_deletion_error_specificity(self, qtbot):
        """Test that only specific Qt deletion errors are caught"""
        widget = CollapsibleGroupBox("Test")
        qtbot.addWidget(widget)
        
        mock_animation = Mock(spec=QPropertyAnimation)
        
        # Test various RuntimeError messages
        def qt_deletion_exact():
            raise RuntimeError("wrapped C/C++ object has been deleted")
        
        def qt_deletion_different_case():
            raise RuntimeError("Wrapped C/C++ Object Has Been Deleted")
        
        def qt_deletion_partial():
            raise RuntimeError("object has been deleted")
        
        def other_runtime_error():
            raise RuntimeError("unrelated error message")
        
        # Test exact match - should be caught
        widget._animation = mock_animation
        widget._animation_connections = [qt_deletion_exact]
        widget._is_collapsed = False  # Ensure state change will trigger logic
        # Use set_collapsed to trigger the animation stopping logic
        widget.set_collapsed(True)  # Should not raise
        
        # Test different case - should be re-raised
        widget._animation = mock_animation
        widget._animation_connections = [qt_deletion_different_case]
        widget._is_collapsed = False  # Reset state
        with pytest.raises(RuntimeError, match="Wrapped C/C++"):
            widget.set_collapsed(True)
        
        # Test partial match - should be re-raised
        widget._animation = mock_animation
        widget._animation_connections = [qt_deletion_partial]
        widget._is_collapsed = False  # Reset state
        with pytest.raises(RuntimeError, match="object has been deleted"):
            widget.set_collapsed(True)
        
        # Test unrelated error - should be re-raised
        widget._animation = mock_animation
        widget._animation_connections = [other_runtime_error]
        widget._is_collapsed = False  # Reset state
        with pytest.raises(RuntimeError, match="unrelated error"):
            widget.set_collapsed(True)

    def test_animation_state_after_error_cleanup(self, qtbot):
        """Test widget state after error during cleanup"""
        widget = CollapsibleGroupBox("Test")
        qtbot.addWidget(widget)
        
        # Add content to test with
        content = QLabel("Test content")
        layout = QVBoxLayout()
        layout.addWidget(content)
        widget.setLayout(layout)
        
        # Create animation with problematic connection
        mock_animation = Mock(spec=QPropertyAnimation)
        
        def raise_qt_error():
            raise RuntimeError("wrapped C/C++ object has been deleted")
        
        widget._animation = mock_animation
        widget._animation_connections = [raise_qt_error]
        
        # Trigger cleanup
        # Use set_collapsed to trigger the animation stopping logic
        widget.set_collapsed(True)
        
        # Widget should still be functional after error
        # New connections should be created for the new animation
        assert len(widget._animation_connections) > 0
        
        # Should be able to trigger new animations
        widget.set_collapsed(True)
        QTest.qWait(50)  # Allow brief animation start

    @patch('spritepal.ui.common.collapsible_group_box.QPropertyAnimation')
    def test_animation_creation_and_cleanup_integration(self, mock_animation_class, qtbot):
        """Test full animation lifecycle with cleanup integration"""
        # Mock animation instance - set up BEFORE widget creation
        mock_animation = Mock(spec=QPropertyAnimation)
        mock_animation_class.return_value = mock_animation
        
        widget = CollapsibleGroupBox("Test")
        qtbot.addWidget(widget)
        
        # Add content using proper API
        content = QLabel("Test content")
        widget.add_widget(content)
        
        # Trigger collapse to create animation
        widget.set_collapsed(True)
        
        # Verify animation was created
        assert widget._animation is not None
        
        # Trigger another action that should cleanup previous animation
        widget.set_collapsed(False)
        
        # Previous animation should have been stopped
        mock_animation.stop.assert_called()

    def test_widget_deletion_during_animation(self, qtbot):
        """Test widget behavior when deleted during animation"""
        widget = CollapsibleGroupBox("Test")
        # Don't add to qtbot since we're deleting it manually
        
        # Add content using proper API
        content = QLabel("Test content")
        widget.add_widget(content)
        
        # Start animation
        widget.set_collapsed(True)
        
        # Verify widget can be safely deleted
        # This implicitly tests the cleanup in destructor
        widget.deleteLater()
        QTest.qWait(100)  # Allow deletion to process
        
        # Test passed if no crashes occurred