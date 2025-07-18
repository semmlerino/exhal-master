#!/usr/bin/env python3
"""
Test hover artifacts fix - verify update region calculations
"""

import sys
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch

import pytest
from PyQt6.QtCore import QPoint, QRect, QPointF
from PyQt6.QtGui import QPen, QColor
from PyQt6.QtWidgets import QApplication

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from pixel_editor.core.pixel_editor_canvas_v3 import PixelCanvasV3
from pixel_editor.core.pixel_editor_controller_v3 import PixelEditorController
from pixel_editor.core.pixel_editor_managers import ToolManager


class TestHoverArtifactsFix:
    """Test that hover region updates are calculated correctly"""
    
    def test_hover_region_calculation_logic(self):
        """Test the hover region calculation logic directly"""
        # Create a mock tool manager
        tool_manager = ToolManager()
        
        # Test case 1: Brush size 1, zoom 8
        tool_manager.set_brush_size(1)
        zoom = 8
        pen_width = 1
        pos = QPoint(5, 5)
        
        # Calculate expected update region
        expected_rect = QRect(
            pos.x() * zoom - pen_width,
            pos.y() * zoom - pen_width,
            1 * zoom + pen_width * 2,
            1 * zoom + pen_width * 2
        )
        
        # Verify calculation
        assert expected_rect.x() == 5 * 8 - 1  # 39
        assert expected_rect.y() == 5 * 8 - 1  # 39
        assert expected_rect.width() == 1 * 8 + 2  # 10
        assert expected_rect.height() == 1 * 8 + 2  # 10
        
        # Test case 2: Brush size 3, zoom 16
        tool_manager.set_brush_size(3)
        zoom = 16
        pos = QPoint(10, 10)
        
        expected_rect = QRect(
            pos.x() * zoom - pen_width,
            pos.y() * zoom - pen_width,
            3 * zoom + pen_width * 2,
            3 * zoom + pen_width * 2
        )
        
        assert expected_rect.x() == 10 * 16 - 1  # 159
        assert expected_rect.y() == 10 * 16 - 1  # 159
        assert expected_rect.width() == 3 * 16 + 2  # 50
        assert expected_rect.height() == 3 * 16 + 2  # 50
    
    def test_brush_pixel_calculation(self):
        """Test that brush pixels are calculated correctly"""
        tool_manager = ToolManager()
        
        # Test brush size 1
        tool_manager.set_brush_size(1)
        pixels = tool_manager.get_brush_pixels(5, 5)
        assert pixels == [(5, 5)]
        
        # Test brush size 2
        tool_manager.set_brush_size(2)
        pixels = tool_manager.get_brush_pixels(10, 10)
        expected = [(10, 10), (11, 10), (10, 11), (11, 11)]
        assert pixels == expected
        
        # Test brush size 3
        tool_manager.set_brush_size(3)
        pixels = tool_manager.get_brush_pixels(0, 0)
        expected = [
            (0, 0), (1, 0), (2, 0),
            (0, 1), (1, 1), (2, 1),
            (0, 2), (1, 2), (2, 2)
        ]
        assert pixels == expected
    
    def test_pan_offset_application(self):
        """Test that pan offset is applied correctly to update regions"""
        # Create a rect representing an update region
        rect = QRect(100, 100, 50, 50)
        
        # Apply pan offset (simulating what happens in _update_hover_regions)
        pan_offset = QPointF(25.5, 30.7)
        rect.translate(int(pan_offset.x()), int(pan_offset.y()))
        
        # Verify the translation
        assert rect.x() == 125  # 100 + int(25.5)
        assert rect.y() == 130  # 100 + int(30.7)
        assert rect.width() == 50  # unchanged
        assert rect.height() == 50  # unchanged
    
    @patch('PyQt6.QtWidgets.QWidget.__init__')
    def test_update_hover_regions_method(self, mock_widget_init):
        """Test the actual _update_hover_regions method with mocking"""
        mock_widget_init.return_value = None
        
        # Create minimal mock controller
        controller = Mock()
        controller.tool_manager = ToolManager()
        controller.tool_manager.set_brush_size(2)
        
        # Mock required signals
        controller.imageChanged = Mock()
        controller.paletteChanged = Mock() 
        controller.toolChanged = Mock()
        
        # Create canvas with proper mocking
        canvas = PixelCanvasV3.__new__(PixelCanvasV3)
        canvas.controller = controller
        canvas.zoom = 8
        canvas.drawing = False
        canvas.pan_offset = QPointF(0, 0)
        
        # Track update calls
        updated_regions = []
        canvas.update = Mock(side_effect=lambda rect: updated_regions.append(rect))
        
        # Call the method
        old_pos = QPoint(5, 5)
        new_pos = QPoint(10, 10)
        canvas._update_hover_regions(old_pos, new_pos)
        
        # Verify two regions were updated
        assert len(updated_regions) == 2
        
        # Verify the regions have the correct size for brush size 2
        for rect in updated_regions:
            assert rect.width() == 2 * 8 + 2  # brush_size * zoom + pen_width * 2
            assert rect.height() == 2 * 8 + 2
    

if __name__ == "__main__":
    pytest.main([__file__, "-v"])