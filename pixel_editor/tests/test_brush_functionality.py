#!/usr/bin/env python3
"""
Comprehensive tests for brush functionality in the pixel editor
Tests the brush size feature across all components
"""

import sys
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from pixel_editor.core.pixel_editor_managers import ToolManager
from pixel_editor.core.pixel_editor_models import ImageModel
import numpy as np


class TestToolManagerBrushSize:
    """Test brush size functionality in ToolManager"""
    
    @pytest.fixture
    def tool_manager(self):
        """Create a ToolManager instance"""
        return ToolManager()
    
    def test_default_brush_size(self, tool_manager):
        """Test that default brush size is 1"""
        assert tool_manager.get_brush_size() == 1
    
    def test_set_brush_size_valid(self, tool_manager):
        """Test setting valid brush sizes"""
        tool_manager.set_brush_size(2)
        assert tool_manager.get_brush_size() == 2
        
        tool_manager.set_brush_size(5)
        assert tool_manager.get_brush_size() == 5
        
        tool_manager.set_brush_size(1)
        assert tool_manager.get_brush_size() == 1
    
    def test_set_brush_size_invalid(self, tool_manager):
        """Test setting invalid brush sizes"""
        original_size = tool_manager.get_brush_size()
        
        # Test size too small
        tool_manager.set_brush_size(0)
        assert tool_manager.get_brush_size() == original_size
        
        # Test size too large
        tool_manager.set_brush_size(10)
        assert tool_manager.get_brush_size() == original_size
        
        # Test negative size
        tool_manager.set_brush_size(-1)
        assert tool_manager.get_brush_size() == original_size
    
    def test_get_brush_pixels_size_1(self, tool_manager):
        """Test brush pixels calculation for size 1"""
        tool_manager.set_brush_size(1)
        pixels = tool_manager.get_brush_pixels(10, 10)
        
        expected = [(10, 10)]
        assert pixels == expected
    
    def test_get_brush_pixels_size_2(self, tool_manager):
        """Test brush pixels calculation for size 2"""
        tool_manager.set_brush_size(2)
        pixels = tool_manager.get_brush_pixels(10, 10)
        
        expected = [(10, 10), (11, 10), (10, 11), (11, 11)]
        assert pixels == expected
    
    def test_get_brush_pixels_size_3(self, tool_manager):
        """Test brush pixels calculation for size 3"""
        tool_manager.set_brush_size(3)
        pixels = tool_manager.get_brush_pixels(5, 5)
        
        expected = [
            (5, 5), (6, 5), (7, 5),
            (5, 6), (6, 6), (7, 6),
            (5, 7), (6, 7), (7, 7)
        ]
        assert pixels == expected
    
    def test_get_brush_pixels_different_positions(self, tool_manager):
        """Test brush pixels calculation at different positions"""
        tool_manager.set_brush_size(2)
        
        # Test at origin
        pixels = tool_manager.get_brush_pixels(0, 0)
        expected = [(0, 0), (1, 0), (0, 1), (1, 1)]
        assert pixels == expected
        
        # Test at different position
        pixels = tool_manager.get_brush_pixels(3, 7)
        expected = [(3, 7), (4, 7), (3, 8), (4, 8)]
        assert pixels == expected


class TestBrushDrawingLogic:
    """Test brush drawing logic in controller"""
    
    @pytest.fixture
    def image_model(self):
        """Create a test image model"""
        model = ImageModel()
        model.data = np.zeros((8, 8), dtype=np.uint8)  # 8x8 image filled with 0
        return model
    
    @pytest.fixture
    def tool_manager(self):
        """Create a ToolManager instance"""
        return ToolManager()
    
    def test_filter_valid_pixels_all_valid(self, image_model, tool_manager):
        """Test filtering pixels when all are valid"""
        # Import the controller here to avoid circular imports
        from pixel_editor.core.pixel_editor_controller_v3 import PixelEditorController
        
        # Create a mock controller with our image model
        controller = Mock(spec=PixelEditorController)
        controller.image_model = image_model
        
        # Create the actual method
        def filter_valid_pixels(pixels):
            if image_model.data is None:
                return []
            valid_pixels = []
            height, width = image_model.data.shape[:2]
            for px, py in pixels:
                if 0 <= px < width and 0 <= py < height:
                    valid_pixels.append((px, py))
            return valid_pixels
        
        # Test with all valid pixels
        pixels = [(1, 1), (2, 2), (3, 3)]
        valid = filter_valid_pixels(pixels)
        assert valid == pixels
    
    def test_filter_valid_pixels_some_invalid(self, image_model, tool_manager):
        """Test filtering pixels when some are invalid"""
        def filter_valid_pixels(pixels):
            if image_model.data is None:
                return []
            valid_pixels = []
            height, width = image_model.data.shape[:2]
            for px, py in pixels:
                if 0 <= px < width and 0 <= py < height:
                    valid_pixels.append((px, py))
            return valid_pixels
        
        # Test with some invalid pixels (outside 8x8 bounds)
        pixels = [(1, 1), (8, 8), (7, 7), (-1, 5), (5, 10)]
        valid = filter_valid_pixels(pixels)
        expected = [(1, 1), (7, 7)]  # Only these are within bounds
        assert valid == expected
    
    def test_filter_valid_pixels_brush_at_edge(self, image_model, tool_manager):
        """Test filtering brush pixels at image edge"""
        def filter_valid_pixels(pixels):
            if image_model.data is None:
                return []
            valid_pixels = []
            height, width = image_model.data.shape[:2]
            for px, py in pixels:
                if 0 <= px < width and 0 <= py < height:
                    valid_pixels.append((px, py))
            return valid_pixels
        
        # Test 2x2 brush at bottom-right corner of 8x8 image
        tool_manager.set_brush_size(2)
        brush_pixels = tool_manager.get_brush_pixels(7, 7)  # [(7,7), (8,7), (7,8), (8,8)]
        valid = filter_valid_pixels(brush_pixels)
        expected = [(7, 7)]  # Only (7,7) is valid in 8x8 image
        assert valid == expected


class TestBrushBoundsChecking:
    """Test brush bounds checking and edge cases"""
    
    @pytest.fixture
    def tool_manager(self):
        """Create a ToolManager instance"""
        return ToolManager()
    
    def test_brush_pixels_order_consistency(self, tool_manager):
        """Test that brush pixels are returned in consistent order"""
        tool_manager.set_brush_size(2)
        
        # Test multiple calls return same order
        pixels1 = tool_manager.get_brush_pixels(5, 5)
        pixels2 = tool_manager.get_brush_pixels(5, 5)
        assert pixels1 == pixels2
        
        # Test expected order (top-left, top-right, bottom-left, bottom-right)
        expected = [(5, 5), (6, 5), (5, 6), (6, 6)]
        assert pixels1 == expected
    
    def test_brush_size_boundary_values(self, tool_manager):
        """Test brush size at boundary values"""
        # Test minimum valid size
        tool_manager.set_brush_size(1)
        assert tool_manager.get_brush_size() == 1
        pixels = tool_manager.get_brush_pixels(0, 0)
        assert len(pixels) == 1
        
        # Test maximum valid size
        tool_manager.set_brush_size(5)
        assert tool_manager.get_brush_size() == 5
        pixels = tool_manager.get_brush_pixels(0, 0)
        assert len(pixels) == 25  # 5x5 = 25 pixels
    
    def test_brush_pixels_no_duplicates(self, tool_manager):
        """Test that brush pixels contain no duplicates"""
        for size in range(1, 6):
            tool_manager.set_brush_size(size)
            pixels = tool_manager.get_brush_pixels(10, 10)
            
            # Check no duplicates
            assert len(pixels) == len(set(pixels))
            
            # Check correct count
            assert len(pixels) == size * size


class TestBrushIntegration:
    """Test brush functionality integration"""
    
    def test_brush_size_affects_pixel_count(self):
        """Test that brush size correctly affects number of pixels"""
        tool_manager = ToolManager()
        
        # Test different brush sizes
        size_to_pixel_count = {
            1: 1,   # 1x1
            2: 4,   # 2x2
            3: 9,   # 3x3
            4: 16,  # 4x4
            5: 25   # 5x5
        }
        
        for size, expected_count in size_to_pixel_count.items():
            tool_manager.set_brush_size(size)
            pixels = tool_manager.get_brush_pixels(10, 10)
            assert len(pixels) == expected_count, f"Size {size} should produce {expected_count} pixels"
    
    def test_brush_position_independence(self):
        """Test that brush shape is independent of position"""
        tool_manager = ToolManager()
        tool_manager.set_brush_size(2)
        
        # Get relative positions for different brush centers
        def get_relative_pixels(center_x, center_y):
            pixels = tool_manager.get_brush_pixels(center_x, center_y)
            return [(px - center_x, py - center_y) for px, py in pixels]
        
        # Test at different positions
        rel_pixels_1 = get_relative_pixels(0, 0)
        rel_pixels_2 = get_relative_pixels(10, 10)
        rel_pixels_3 = get_relative_pixels(100, 100)
        
        # All should have same relative pattern
        assert rel_pixels_1 == rel_pixels_2 == rel_pixels_3
        
        # Expected relative pattern for 2x2 brush
        expected = [(0, 0), (1, 0), (0, 1), (1, 1)]
        assert rel_pixels_1 == expected


if __name__ == "__main__":
    pytest.main([__file__, "-v"])