#!/usr/bin/env python3
"""
Tests for tool panel brush size controls
"""

import sys
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from PyQt6.QtWidgets import QApplication

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from pixel_editor.core.views.panels.tool_panel import ToolPanel


class TestToolPanelBrushSize:
    """Test brush size controls in the tool panel"""
    
    @pytest.fixture
    def app(self):
        """Create QApplication instance"""
        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        return app
    
    @pytest.fixture
    def tool_panel(self, app):
        """Create a ToolPanel instance"""
        return ToolPanel()
    
    def test_default_brush_size_ui(self, tool_panel):
        """Test that UI shows default brush size of 1"""
        assert tool_panel.get_brush_size() == 1
        assert tool_panel.brush_size_spinbox.value() == 1
    
    def test_set_brush_size_ui(self, tool_panel):
        """Test setting brush size through UI"""
        # Set brush size to 2
        tool_panel.set_brush_size(2)
        assert tool_panel.get_brush_size() == 2
        assert tool_panel.brush_size_spinbox.value() == 2
        
        # Set brush size to 5
        tool_panel.set_brush_size(5)
        assert tool_panel.get_brush_size() == 5
        assert tool_panel.brush_size_spinbox.value() == 5
        
        # Set brush size back to 1
        tool_panel.set_brush_size(1)
        assert tool_panel.get_brush_size() == 1
        assert tool_panel.brush_size_spinbox.value() == 1
    
    def test_brush_size_spinbox_range(self, tool_panel):
        """Test that spinbox has correct range"""
        spinbox = tool_panel.brush_size_spinbox
        assert spinbox.minimum() == 1
        assert spinbox.maximum() == 5
    
    def test_brush_size_changed_signal(self, tool_panel):
        """Test that brushSizeChanged signal is emitted"""
        # Mock the signal
        signal_mock = Mock()
        tool_panel.brushSizeChanged.connect(signal_mock)
        
        # Change brush size via spinbox
        tool_panel.brush_size_spinbox.setValue(3)
        
        # Verify signal was emitted
        signal_mock.assert_called_once_with(3)
    
    def test_brush_size_changed_signal_multiple_values(self, tool_panel):
        """Test brushSizeChanged signal with multiple values"""
        # Mock the signal
        signal_mock = Mock()
        tool_panel.brushSizeChanged.connect(signal_mock)
        
        # Test multiple values that actually change (avoiding duplicate values)
        test_values = [2, 3, 4, 5, 1, 3, 2]
        for size in test_values:
            signal_mock.reset_mock()
            tool_panel.brush_size_spinbox.setValue(size)
            signal_mock.assert_called_once_with(size)
    
    def test_brush_size_spinbox_tooltip(self, tool_panel):
        """Test that spinbox has helpful tooltip"""
        tooltip = tool_panel.brush_size_spinbox.toolTip()
        assert "brush size" in tooltip.lower()
        assert "pixels" in tooltip.lower()
    
    def test_brush_size_label_text(self, tool_panel):
        """Test that label has correct text"""
        label_text = tool_panel.brush_size_label.text()
        assert "size" in label_text.lower()
    
    def test_brush_size_controls_exist(self, tool_panel):
        """Test that brush size controls exist and are properly set up"""
        # Check that brush size controls exist
        assert hasattr(tool_panel, 'brush_size_spinbox')
        assert hasattr(tool_panel, 'brush_size_label')
        
        # Check that spinbox is properly configured
        spinbox = tool_panel.brush_size_spinbox
        assert spinbox.minimum() == 1
        assert spinbox.maximum() == 5
        assert spinbox.value() == 1
        
        # Check that label exists
        label = tool_panel.brush_size_label
        assert label is not None
        assert label.text() == "Size:"
    
    def test_update_brush_size_display(self, tool_panel):
        """Test the update_brush_size_display method"""
        # This method exists for external updates (like keyboard shortcuts)
        # It should not crash when called
        tool_panel.update_brush_size_display()
        
        # Method should be callable without issues
        assert callable(tool_panel.update_brush_size_display)


class TestToolPanelBrushSizeIntegration:
    """Test integration between tool panel brush size and other components"""
    
    @pytest.fixture
    def app(self):
        """Create QApplication instance"""
        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        return app
    
    @pytest.fixture
    def tool_panel(self, app):
        """Create a ToolPanel instance"""
        return ToolPanel()
    
    def test_tool_selection_preserves_brush_size(self, tool_panel):
        """Test that changing tools doesn't affect brush size"""
        # Set brush size to 3
        tool_panel.set_brush_size(3)
        assert tool_panel.get_brush_size() == 3
        
        # Change tool to fill
        tool_panel.set_tool("fill")
        assert tool_panel.get_brush_size() == 3
        
        # Change tool to picker
        tool_panel.set_tool("picker")
        assert tool_panel.get_brush_size() == 3
        
        # Change tool back to pencil
        tool_panel.set_tool("pencil")
        assert tool_panel.get_brush_size() == 3
    
    def test_brush_size_and_tool_signals_independent(self, tool_panel):
        """Test that brush size and tool change signals are independent"""
        # Mock both signals
        tool_signal_mock = Mock()
        brush_signal_mock = Mock()
        tool_panel.toolChanged.connect(tool_signal_mock)
        tool_panel.brushSizeChanged.connect(brush_signal_mock)
        
        # Change brush size - should only emit brush signal
        tool_panel.brush_size_spinbox.setValue(4)
        brush_signal_mock.assert_called_once_with(4)
        tool_signal_mock.assert_not_called()
        
        # Reset mocks
        tool_signal_mock.reset_mock()
        brush_signal_mock.reset_mock()
        
        # Change tool - should only emit tool signal
        tool_panel.set_tool("fill")
        tool_signal_mock.assert_called_once_with("fill")
        brush_signal_mock.assert_not_called()
    
    def test_brush_size_bounds_respected(self, tool_panel):
        """Test that brush size respects spinbox bounds"""
        # Set to minimum value
        tool_panel.set_brush_size(1)
        assert tool_panel.get_brush_size() == 1
        
        # Set to maximum value
        tool_panel.set_brush_size(5)
        assert tool_panel.get_brush_size() == 5
        
        # Try to set below minimum (should be clamped)
        tool_panel.brush_size_spinbox.setValue(0)
        assert tool_panel.get_brush_size() >= 1
        
        # Try to set above maximum (should be clamped)
        tool_panel.brush_size_spinbox.setValue(10)
        assert tool_panel.get_brush_size() <= 5


if __name__ == "__main__":
    pytest.main([__file__, "-v"])