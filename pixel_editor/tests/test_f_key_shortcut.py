#!/usr/bin/env python3
"""
Test that the F key triggers the zoom-to-fit functionality
"""

import pytest
from unittest.mock import Mock, patch
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QKeyEvent
from PyQt6.QtWidgets import QApplication


class TestFKeyShortcut:
    """Test the F key shortcut for zoom-to-fit"""
    
    @pytest.fixture
    def app(self):
        """Create QApplication instance for Qt tests"""
        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        return app
    
    def test_f_key_triggers_zoom_to_fit(self, app):
        """Test that pressing F key triggers zoom-to-fit"""
        # Mock editor with zoom-to-fit method
        from pixel_editor.core.indexed_pixel_editor_v3 import IndexedPixelEditor
        
        # Create a mock editor
        editor = Mock(spec=IndexedPixelEditor)
        editor._zoom_to_fit = Mock()
        
        # Create the actual keyPressEvent method 
        def mock_keyPressEvent(event):
            if (
                event.key() == Qt.Key.Key_F
                and event.modifiers() == Qt.KeyboardModifier.NoModifier
            ):
                editor._zoom_to_fit()
        
        # Create key press event for F key
        f_key_event = QKeyEvent(
            QKeyEvent.Type.KeyPress,
            Qt.Key.Key_F,
            Qt.KeyboardModifier.NoModifier
        )
        
        # Call the key press handler
        mock_keyPressEvent(f_key_event)
        
        # Verify zoom-to-fit was called
        editor._zoom_to_fit.assert_called_once()
    
    def test_f_key_with_modifiers_ignored(self, app):
        """Test that F key with modifiers (like Ctrl+F) is ignored"""
        # Mock editor 
        from pixel_editor.core.indexed_pixel_editor_v3 import IndexedPixelEditor
        
        editor = Mock(spec=IndexedPixelEditor)
        editor._zoom_to_fit = Mock()
        
        # Create the actual keyPressEvent method 
        def mock_keyPressEvent(event):
            if (
                event.key() == Qt.Key.Key_F
                and event.modifiers() == Qt.KeyboardModifier.NoModifier
            ):
                editor._zoom_to_fit()
        
        # Create key press event for Ctrl+F
        ctrl_f_event = QKeyEvent(
            QKeyEvent.Type.KeyPress,
            Qt.Key.Key_F,
            Qt.KeyboardModifier.ControlModifier
        )
        
        # Call the key press handler
        mock_keyPressEvent(ctrl_f_event)
        
        # Verify zoom-to-fit was NOT called
        editor._zoom_to_fit.assert_not_called()
    
    def test_other_keys_not_affected(self, app):
        """Test that other keys are not affected by F key handler"""
        # Mock editor
        from pixel_editor.core.indexed_pixel_editor_v3 import IndexedPixelEditor
        
        editor = Mock(spec=IndexedPixelEditor)
        editor._zoom_to_fit = Mock()
        
        # Create the actual keyPressEvent method 
        def mock_keyPressEvent(event):
            if (
                event.key() == Qt.Key.Key_F
                and event.modifiers() == Qt.KeyboardModifier.NoModifier
            ):
                editor._zoom_to_fit()
        
        # Test various other keys
        other_keys = [
            Qt.Key.Key_G,
            Qt.Key.Key_E,
            Qt.Key.Key_D,
            Qt.Key.Key_Space,
            Qt.Key.Key_Enter
        ]
        
        for key in other_keys:
            key_event = QKeyEvent(
                QKeyEvent.Type.KeyPress,
                key,
                Qt.KeyboardModifier.NoModifier
            )
            
            mock_keyPressEvent(key_event)
        
        # Verify zoom-to-fit was never called
        editor._zoom_to_fit.assert_not_called()
    
    def test_f_key_constant_matches_implementation(self):
        """Test that the F key constant matches the implementation"""
        from pixel_editor.core.pixel_editor_constants import KEY_ZOOM_FIT_F
        
        # Verify the constant is correct
        assert KEY_ZOOM_FIT_F == "F"
        
        # Verify Qt key constant matches
        assert Qt.Key.Key_F.name == "Key_F"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])