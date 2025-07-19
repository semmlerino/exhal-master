#!/usr/bin/env python3
"""
Tests for line interpolation functionality in the pixel editor.
Tests the drawing consistency fix for fast mouse movements.
"""

import pytest
import numpy as np
from unittest.mock import Mock, patch

from pixel_editor.core.pixel_editor_managers import PencilTool, ToolManager
from pixel_editor.core.pixel_editor_models import ImageModel
from pixel_editor.core.pixel_editor_controller_v3 import PixelEditorController


class TestLineInterpolation:
    """Test line interpolation algorithm in PencilTool"""

    @pytest.fixture
    def image_model(self):
        """Create test image model"""
        return ImageModel(width=10, height=10)

    @pytest.fixture
    def pencil_tool(self):
        """Create pencil tool instance"""
        return PencilTool()

    def test_horizontal_line_interpolation(self, pencil_tool, image_model):
        """Test horizontal line interpolation"""
        # Start at (1, 1)
        pencil_tool.on_press(1, 1, 5, image_model)
        
        # Move to (5, 1) - should create horizontal line
        line_points = pencil_tool.on_move(5, 1, 5, image_model)
        
        # Should have all points from (1,1) to (5,1)
        expected_points = [(1, 1), (2, 1), (3, 1), (4, 1), (5, 1)]
        assert line_points == expected_points

    def test_vertical_line_interpolation(self, pencil_tool, image_model):
        """Test vertical line interpolation"""
        # Start at (2, 1)
        pencil_tool.on_press(2, 1, 7, image_model)
        
        # Move to (2, 5) - should create vertical line
        line_points = pencil_tool.on_move(2, 5, 7, image_model)
        
        # Should have all points from (2,1) to (2,5)
        expected_points = [(2, 1), (2, 2), (2, 3), (2, 4), (2, 5)]
        assert line_points == expected_points

    def test_diagonal_line_interpolation(self, pencil_tool, image_model):
        """Test diagonal line interpolation"""
        # Start at (0, 0)
        pencil_tool.on_press(0, 0, 3, image_model)
        
        # Move to (3, 3) - should create diagonal line
        line_points = pencil_tool.on_move(3, 3, 3, image_model)
        
        # Should have connected line (exact points depend on Bresenham algorithm)
        assert len(line_points) == 4  # (0,0), (1,1), (2,2), (3,3)
        assert (0, 0) in line_points
        assert (3, 3) in line_points
        assert (1, 1) in line_points
        assert (2, 2) in line_points

    def test_steep_diagonal_line(self, pencil_tool, image_model):
        """Test steep diagonal line interpolation"""
        # Start at (1, 1)
        pencil_tool.on_press(1, 1, 9, image_model)
        
        # Move to (2, 5) - steep line
        line_points = pencil_tool.on_move(2, 5, 9, image_model)
        
        # Should have connected line with at least 5 points
        assert len(line_points) >= 5
        assert (1, 1) in line_points
        assert (2, 5) in line_points
        # Check line is connected (no gaps)
        y_coords = [p[1] for p in line_points]
        assert max(y_coords) - min(y_coords) == 4

    def test_negative_slope_line(self, pencil_tool, image_model):
        """Test line with negative slope"""
        # Start at (5, 1)
        pencil_tool.on_press(5, 1, 12, image_model)
        
        # Move to (1, 5) - negative slope
        line_points = pencil_tool.on_move(1, 5, 12, image_model)
        
        # Should have connected line
        assert len(line_points) >= 5
        assert (5, 1) in line_points
        assert (1, 5) in line_points

    def test_single_pixel_move(self, pencil_tool, image_model):
        """Test single pixel movement"""
        # Start at (3, 3)
        pencil_tool.on_press(3, 3, 8, image_model)
        
        # Move to adjacent pixel (4, 3)
        line_points = pencil_tool.on_move(4, 3, 8, image_model)
        
        # Should have both points
        assert len(line_points) == 2
        assert (3, 3) in line_points
        assert (4, 3) in line_points

    def test_no_movement(self, pencil_tool, image_model):
        """Test no movement (same position)"""
        # Start at (2, 2)
        pencil_tool.on_press(2, 2, 6, image_model)
        
        # Move to same position
        line_points = pencil_tool.on_move(2, 2, 6, image_model)
        
        # Should have just one point
        assert len(line_points) == 1
        assert line_points[0] == (2, 2)

    def test_position_tracking_reset(self, pencil_tool, image_model):
        """Test position tracking resets on release"""
        # Start drawing
        pencil_tool.on_press(1, 1, 4, image_model)
        pencil_tool.on_move(3, 3, 4, image_model)
        
        # Release resets position
        pencil_tool.on_release(3, 3, 4, image_model)
        
        # Next move should start fresh (no line from previous position)
        line_points = pencil_tool.on_move(5, 5, 4, image_model)
        
        # Should only have current position since no previous position
        assert len(line_points) == 1
        assert line_points[0] == (5, 5)

    def test_multiple_line_segments(self, pencil_tool, image_model):
        """Test multiple connected line segments"""
        # Start at (0, 0)
        pencil_tool.on_press(0, 0, 11, image_model)
        
        # First segment to (2, 0)
        line1 = pencil_tool.on_move(2, 0, 11, image_model)
        
        # Second segment to (2, 2)
        line2 = pencil_tool.on_move(2, 2, 11, image_model)
        
        # Third segment to (0, 2)
        line3 = pencil_tool.on_move(0, 2, 11, image_model)
        
        # Each segment should be connected
        assert len(line1) == 3  # (0,0), (1,0), (2,0)
        assert len(line2) == 3  # (2,0), (2,1), (2,2)
        assert len(line3) == 3  # (2,2), (1,2), (0,2)

    def test_long_line_interpolation(self, pencil_tool, image_model):
        """Test long line across entire image"""
        # Create larger image for this test
        large_image = ImageModel(width=20, height=20)
        
        # Start at (0, 0)
        pencil_tool.on_press(0, 0, 15, large_image)
        
        # Move to (19, 19) - diagonal across entire image
        line_points = pencil_tool.on_move(19, 19, 15, large_image)
        
        # Should have 20 points (perfect diagonal)
        assert len(line_points) == 20
        assert (0, 0) in line_points
        assert (19, 19) in line_points
        
        # Check line is continuous (no gaps)
        sorted_points = sorted(line_points)
        for i in range(1, len(sorted_points)):
            prev_x, prev_y = sorted_points[i-1]
            curr_x, curr_y = sorted_points[i]
            # Max distance should be 1 in both directions
            assert abs(curr_x - prev_x) <= 1
            assert abs(curr_y - prev_y) <= 1

    def test_bresenham_algorithm_accuracy(self, pencil_tool):
        """Test Bresenham algorithm produces expected results"""
        # Test the internal _get_line_points method directly
        
        # Test case 1: Simple horizontal line
        points = pencil_tool._get_line_points(0, 0, 3, 0)
        assert points == [(0, 0), (1, 0), (2, 0), (3, 0)]
        
        # Test case 2: Simple vertical line
        points = pencil_tool._get_line_points(0, 0, 0, 3)
        assert points == [(0, 0), (0, 1), (0, 2), (0, 3)]
        
        # Test case 3: Perfect diagonal
        points = pencil_tool._get_line_points(0, 0, 2, 2)
        assert points == [(0, 0), (1, 1), (2, 2)]
        
        # Test case 4: Reverse direction
        points = pencil_tool._get_line_points(3, 3, 0, 0)
        assert points == [(3, 3), (2, 2), (1, 1), (0, 0)]


class TestBrushSizeIntegration:
    """Test line interpolation with different brush sizes"""

    @pytest.fixture
    def tool_manager(self):
        """Create tool manager with different brush sizes"""
        return ToolManager()

    @pytest.fixture
    def image_model(self):
        """Create test image model"""
        return ImageModel(width=15, height=15)

    def test_brush_size_1_line(self, tool_manager, image_model):
        """Test line drawing with 1x1 brush"""
        tool_manager.set_brush_size(1)
        
        # Get brush pixels for a line point
        brush_pixels = tool_manager.get_brush_pixels(5, 5)
        
        # Should have exactly 1 pixel
        assert len(brush_pixels) == 1
        assert brush_pixels[0] == (5, 5)

    def test_brush_size_2_line(self, tool_manager, image_model):
        """Test line drawing with 2x2 brush"""
        tool_manager.set_brush_size(2)
        
        # Get brush pixels for a line point
        brush_pixels = tool_manager.get_brush_pixels(5, 5)
        
        # Should have 4 pixels in 2x2 pattern
        assert len(brush_pixels) == 4
        expected_pixels = [(5, 5), (6, 5), (5, 6), (6, 6)]
        assert set(brush_pixels) == set(expected_pixels)

    def test_brush_size_3_line(self, tool_manager, image_model):
        """Test line drawing with 3x3 brush"""
        tool_manager.set_brush_size(3)
        
        # Get brush pixels for a line point
        brush_pixels = tool_manager.get_brush_pixels(5, 5)
        
        # Should have 9 pixels in 3x3 pattern
        assert len(brush_pixels) == 9
        expected_pixels = [
            (5, 5), (6, 5), (7, 5),
            (5, 6), (6, 6), (7, 6),
            (5, 7), (6, 7), (7, 7)
        ]
        assert set(brush_pixels) == set(expected_pixels)

    def test_line_with_brush_coverage(self, tool_manager, image_model):
        """Test that line interpolation works correctly with brush sizes"""
        tool_manager.set_brush_size(2)
        tool_manager.set_tool("pencil")
        
        # Get pencil tool
        pencil = tool_manager.get_tool()
        
        # Draw a line
        pencil.on_press(2, 2, 5, image_model)
        line_points = pencil.on_move(5, 2, 5, image_model)
        
        # Should have points for the line
        assert len(line_points) == 4  # (2,2), (3,2), (4,2), (5,2)
        
        # Each point should work with brush size
        for x, y in line_points:
            brush_pixels = tool_manager.get_brush_pixels(x, y)
            assert len(brush_pixels) == 4  # 2x2 brush


class TestControllerIntegration:
    """Test controller integration with line interpolation"""

    def test_controller_line_drawing_workflow_unit(self):
        """Test line drawing workflow by testing individual components"""
        # Create components directly instead of full controller
        tool_manager = ToolManager()
        image_model = ImageModel(width=10, height=10)
        
        # Set up for drawing
        tool_manager.set_tool("pencil")
        tool_manager.set_color(7)
        tool_manager.set_brush_size(1)
        
        # Get pencil tool
        pencil = tool_manager.get_tool()
        
        # Simulate controller workflow
        # 1. Press
        pencil.on_press(2, 2, 7, image_model)
        
        # 2. Move (should create line)
        line_points = pencil.on_move(5, 2, 7, image_model)
        
        # 3. Apply line points to image
        for x, y in line_points:
            image_model.set_pixel(x, y, 7)
        
        # 4. Release
        pencil.on_release(5, 2, 7, image_model)
        
        # Verify line was drawn
        for x in range(2, 6):
            assert image_model.get_color_at(x, 2) == 7

    def test_controller_brush_size_integration_unit(self):
        """Test brush size integration with line interpolation"""
        # Create components directly
        tool_manager = ToolManager()
        image_model = ImageModel(width=10, height=10)
        
        # Set larger brush size
        tool_manager.set_brush_size(2)
        tool_manager.set_tool("pencil")
        tool_manager.set_color(9)
        
        # Get pencil tool
        pencil = tool_manager.get_tool()
        
        # Simulate line drawing with brush
        pencil.on_press(1, 1, 9, image_model)
        line_points = pencil.on_move(3, 1, 9, image_model)
        
        # Apply brush to each line point
        for x, y in line_points:
            brush_pixels = tool_manager.get_brush_pixels(x, y)
            for bx, by in brush_pixels:
                if 0 <= bx < 10 and 0 <= by < 10:  # Bounds check
                    image_model.set_pixel(bx, by, 9)
        
        # Verify brush coverage
        # Should have a 2x2 brush applied to each line point
        assert image_model.get_color_at(1, 1) == 9  # Top-left of first brush
        assert image_model.get_color_at(2, 1) == 9  # Top-right of first brush
        assert image_model.get_color_at(3, 1) == 9  # Line point coverage


class TestEdgeCases:
    """Test edge cases and boundary conditions"""

    @pytest.fixture
    def small_image(self):
        """Create small image for boundary testing"""
        return ImageModel(width=3, height=3)

    @pytest.fixture
    def pencil_tool(self):
        """Create pencil tool instance"""
        return PencilTool()

    def test_drawing_at_image_boundary(self, pencil_tool, small_image):
        """Test drawing at image boundaries"""
        # Start at edge
        pencil_tool.on_press(0, 0, 1, small_image)
        
        # Draw to opposite edge
        line_points = pencil_tool.on_move(2, 2, 1, small_image)
        
        # Should have valid line points
        assert len(line_points) == 3
        assert (0, 0) in line_points
        assert (2, 2) in line_points

    def test_drawing_outside_image_bounds(self, pencil_tool, small_image):
        """Test that line points can be outside bounds (filtering happens in controller)"""
        # Start inside image
        pencil_tool.on_press(1, 1, 2, small_image)
        
        # Move outside image bounds
        line_points = pencil_tool.on_move(5, 5, 2, small_image)
        
        # Should still generate line points (controller filters them)
        assert len(line_points) >= 3
        assert (1, 1) in line_points
        assert (5, 5) in line_points

    def test_zero_length_line(self, pencil_tool, small_image):
        """Test zero-length line (same start and end point)"""
        # Start and end at same point
        pencil_tool.on_press(1, 1, 3, small_image)
        line_points = pencil_tool.on_move(1, 1, 3, small_image)
        
        # Should have one point
        assert len(line_points) == 1
        assert line_points[0] == (1, 1)

    def test_line_interpolation_with_none_position(self, pencil_tool, small_image):
        """Test line interpolation when previous position is None"""
        # Don't call on_press first
        line_points = pencil_tool.on_move(2, 2, 4, small_image)
        
        # Should return just current position
        assert len(line_points) == 1
        assert line_points[0] == (2, 2)


class TestPerformance:
    """Test performance characteristics of line interpolation"""

    @pytest.fixture
    def pencil_tool(self):
        """Create pencil tool instance"""
        return PencilTool()

    @pytest.fixture
    def large_image(self):
        """Create large image for performance testing"""
        return ImageModel(width=100, height=100)

    def test_long_line_performance(self, pencil_tool, large_image):
        """Test performance of very long line interpolation"""
        import time
        
        # Start at corner
        pencil_tool.on_press(0, 0, 1, large_image)
        
        # Time the line interpolation
        start_time = time.time()
        line_points = pencil_tool.on_move(99, 99, 1, large_image)
        end_time = time.time()
        
        # Should complete quickly (less than 1ms for 100-pixel line)
        assert end_time - start_time < 0.001
        
        # Should have reasonable number of points
        assert len(line_points) >= 99
        assert len(line_points) <= 141  # Max for perfect diagonal

    def test_many_small_lines_performance(self, pencil_tool, large_image):
        """Test performance of many small line segments"""
        import time
        
        # Time many small line segments
        start_time = time.time()
        
        pencil_tool.on_press(10, 10, 2, large_image)
        for i in range(100):
            x = 10 + (i % 10)
            y = 10 + (i // 10)
            pencil_tool.on_move(x, y, 2, large_image)
        
        end_time = time.time()
        
        # Should complete quickly (less than 10ms for 100 small lines)
        assert end_time - start_time < 0.01