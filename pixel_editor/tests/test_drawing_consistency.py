#!/usr/bin/env python3
"""
Integration tests for drawing consistency - validates the fix for fast drawing.
Tests that fast mouse movements no longer skip pixels due to line interpolation.
"""

import pytest
import numpy as np
from unittest.mock import Mock

from pixel_editor.core.pixel_editor_managers import ToolManager
from pixel_editor.core.pixel_editor_models import ImageModel


class TestDrawingConsistency:
    """Test drawing consistency with fast movements"""

    @pytest.fixture
    def setup_drawing(self):
        """Set up drawing environment"""
        image_model = ImageModel(width=20, height=20)
        tool_manager = ToolManager()
        tool_manager.set_tool("pencil")
        tool_manager.set_color(5)
        tool_manager.set_brush_size(1)
        
        return image_model, tool_manager

    def test_fast_horizontal_line_no_gaps(self, setup_drawing):
        """Test fast horizontal line has no gaps"""
        image_model, tool_manager = setup_drawing
        pencil = tool_manager.get_tool()
        
        # Simulate fast horizontal movement (would skip pixels without interpolation)
        pencil.on_press(2, 5, 5, image_model)
        line_points = pencil.on_move(18, 5, 5, image_model)
        
        # Apply all line points
        for x, y in line_points:
            image_model.set_pixel(x, y, 5)
        
        # Check no gaps in horizontal line
        for x in range(2, 19):
            assert image_model.get_color_at(x, 5) == 5, f"Gap found at ({x}, 5)"

    def test_fast_vertical_line_no_gaps(self, setup_drawing):
        """Test fast vertical line has no gaps"""
        image_model, tool_manager = setup_drawing
        pencil = tool_manager.get_tool()
        
        # Simulate fast vertical movement
        pencil.on_press(10, 1, 5, image_model)
        line_points = pencil.on_move(10, 18, 5, image_model)
        
        # Apply all line points
        for x, y in line_points:
            image_model.set_pixel(x, y, 5)
        
        # Check no gaps in vertical line
        for y in range(1, 19):
            assert image_model.get_color_at(10, y) == 5, f"Gap found at (10, {y})"

    def test_fast_diagonal_line_connected(self, setup_drawing):
        """Test fast diagonal line is connected"""
        image_model, tool_manager = setup_drawing
        pencil = tool_manager.get_tool()
        
        # Simulate fast diagonal movement
        pencil.on_press(1, 1, 5, image_model)
        line_points = pencil.on_move(18, 18, 5, image_model)
        
        # Apply all line points
        for x, y in line_points:
            image_model.set_pixel(x, y, 5)
        
        # Check line is connected (no gaps larger than 1 pixel)
        drawn_pixels = []
        for y in range(20):
            for x in range(20):
                if image_model.get_color_at(x, y) == 5:
                    drawn_pixels.append((x, y))
        
        # Sort pixels by distance from start
        drawn_pixels.sort(key=lambda p: (p[0] - 1) ** 2 + (p[1] - 1) ** 2)
        
        # Check connectivity - each pixel should be within 1 unit of the next
        for i in range(1, len(drawn_pixels)):
            prev_x, prev_y = drawn_pixels[i-1]
            curr_x, curr_y = drawn_pixels[i]
            dx = abs(curr_x - prev_x)
            dy = abs(curr_y - prev_y)
            assert dx <= 1 and dy <= 1, f"Gap between ({prev_x},{prev_y}) and ({curr_x},{curr_y})"

    def test_zigzag_pattern_no_gaps(self, setup_drawing):
        """Test zigzag pattern has no gaps"""
        image_model, tool_manager = setup_drawing
        pencil = tool_manager.get_tool()
        
        # Create zigzag pattern (simulates erratic fast mouse movement)
        points = [(2, 2), (8, 2), (8, 8), (14, 8), (14, 14), (18, 14)]
        
        pencil.on_press(points[0][0], points[0][1], 5, image_model)
        image_model.set_pixel(points[0][0], points[0][1], 5)
        
        all_drawn_pixels = set()
        
        for i in range(1, len(points)):
            x, y = points[i]
            line_points = pencil.on_move(x, y, 5, image_model)
            
            # Apply line points
            for px, py in line_points:
                image_model.set_pixel(px, py, 5)
                all_drawn_pixels.add((px, py))
        
        # Check each segment is connected
        assert len(all_drawn_pixels) >= len(points), "Not enough pixels drawn"
        
        # Verify key points are included
        for point in points:
            assert point in all_drawn_pixels, f"Missing key point {point}"

    def test_circular_motion_approximation(self, setup_drawing):
        """Test circular motion approximation stays connected"""
        image_model, tool_manager = setup_drawing
        pencil = tool_manager.get_tool()
        
        # Simulate circular motion with discrete points
        import math
        center_x, center_y = 10, 10
        radius = 7
        
        # Generate points around circle (big jumps to test interpolation)
        circle_points = []
        for angle in range(0, 360, 45):  # 45-degree steps
            x = center_x + int(radius * math.cos(math.radians(angle)))
            y = center_y + int(radius * math.sin(math.radians(angle)))
            circle_points.append((x, y))
        
        # Start drawing
        pencil.on_press(circle_points[0][0], circle_points[0][1], 5, image_model)
        image_model.set_pixel(circle_points[0][0], circle_points[0][1], 5)
        
        # Draw segments
        for i in range(1, len(circle_points)):
            x, y = circle_points[i]
            line_points = pencil.on_move(x, y, 5, image_model)
            
            # Apply line points
            for px, py in line_points:
                if 0 <= px < 20 and 0 <= py < 20:
                    image_model.set_pixel(px, py, 5)
        
        # Check all circle points are connected
        drawn_pixels = []
        for y in range(20):
            for x in range(20):
                if image_model.get_color_at(x, y) == 5:
                    drawn_pixels.append((x, y))
        
        # Should have drawn a connected path
        assert len(drawn_pixels) >= len(circle_points), "Insufficient pixels for circular path"

    def test_brush_size_2_fast_line(self, setup_drawing):
        """Test fast line with brush size 2"""
        image_model, tool_manager = setup_drawing
        tool_manager.set_brush_size(2)
        pencil = tool_manager.get_tool()
        
        # Draw fast line with brush
        pencil.on_press(2, 5, 5, image_model)
        line_points = pencil.on_move(12, 5, 5, image_model)
        
        # Apply brush to each line point
        for x, y in line_points:
            brush_pixels = tool_manager.get_brush_pixels(x, y)
            for bx, by in brush_pixels:
                if 0 <= bx < 20 and 0 <= by < 20:
                    image_model.set_pixel(bx, by, 5)
        
        # Check brush coverage - should have thick continuous line
        # Main line (y=5) should be fully covered
        for x in range(2, 13):
            assert image_model.get_color_at(x, 5) == 5, f"Main line gap at ({x}, 5)"
        
        # Brush extension (y=6) should also be covered
        for x in range(2, 13):
            assert image_model.get_color_at(x, 6) == 5, f"Brush extension gap at ({x}, 6)"

    def test_multiple_fast_strokes_independence(self, setup_drawing):
        """Test multiple fast strokes don't interfere with each other"""
        image_model, tool_manager = setup_drawing
        pencil = tool_manager.get_tool()
        
        # First stroke
        pencil.on_press(1, 1, 5, image_model)
        line1 = pencil.on_move(10, 1, 5, image_model)
        pencil.on_release(10, 1, 5, image_model)
        
        # Apply first stroke
        for x, y in line1:
            image_model.set_pixel(x, y, 5)
        
        # Second stroke (should start fresh)
        pencil.on_press(1, 5, 7, image_model)
        line2 = pencil.on_move(10, 5, 7, image_model)
        pencil.on_release(10, 5, 7, image_model)
        
        # Apply second stroke
        for x, y in line2:
            image_model.set_pixel(x, y, 7)
        
        # Check first stroke
        for x in range(1, 11):
            assert image_model.get_color_at(x, 1) == 5, f"First stroke gap at ({x}, 1)"
        
        # Check second stroke
        for x in range(1, 11):
            assert image_model.get_color_at(x, 5) == 7, f"Second stroke gap at ({x}, 5)"
        
        # Check strokes don't interfere
        assert image_model.get_color_at(5, 3) == 0, "Strokes interfered with each other"

    def test_performance_regression_check(self, setup_drawing):
        """Test that interpolation doesn't cause performance regression"""
        image_model, tool_manager = setup_drawing
        pencil = tool_manager.get_tool()
        
        import time
        
        # Time many fast movements
        start_time = time.time()
        
        pencil.on_press(0, 0, 5, image_model)
        for i in range(100):
            x = (i * 19) % 20
            y = (i * 7) % 20
            pencil.on_move(x, y, 5, image_model)
        
        end_time = time.time()
        
        # Should complete quickly (less than 10ms for 100 moves)
        assert end_time - start_time < 0.01, f"Performance regression: {end_time - start_time:.3f}s"


class TestOriginalIssueRegression:
    """Test the specific issue mentioned in the original request"""

    def test_fast_drawing_skips_pixels_fix(self):
        """Test that fast drawing no longer skips pixels"""
        # This test specifically addresses the user's original issue:
        # "when drawing, its not drawing consistently, when fast it skips some pixels"
        
        image_model = ImageModel(width=50, height=50)
        tool_manager = ToolManager()
        tool_manager.set_tool("pencil")
        tool_manager.set_color(10)
        tool_manager.set_brush_size(1)
        
        pencil = tool_manager.get_tool()
        
        # Simulate very fast mouse movement across a large distance
        # This would definitely skip pixels without interpolation
        pencil.on_press(5, 25, 10, image_model)
        
        # Make several large jumps (simulating fast mouse movement)
        fast_moves = [(15, 25), (25, 25), (35, 25), (45, 25)]
        
        all_pixels = set()
        
        for x, y in fast_moves:
            line_points = pencil.on_move(x, y, 10, image_model)
            
            # Apply line points
            for px, py in line_points:
                image_model.set_pixel(px, py, 10)
                all_pixels.add((px, py))
        
        # Check that we have a continuous line with no gaps
        # Should have pixels from x=5 to x=45 on y=25
        for x in range(5, 46):
            assert image_model.get_color_at(x, 25) == 10, f"SKIPPED PIXEL at ({x}, 25) - original issue NOT fixed!"
        
        # Verify we have the expected number of pixels
        horizontal_pixels = sum(1 for x in range(5, 46) if image_model.get_color_at(x, 25) == 10)
        assert horizontal_pixels == 41, f"Expected 41 pixels, got {horizontal_pixels}"

    def test_drawing_consistency_at_various_speeds(self):
        """Test drawing consistency at different movement speeds"""
        image_model = ImageModel(width=30, height=30)
        tool_manager = ToolManager()
        tool_manager.set_tool("pencil")
        tool_manager.set_color(12)
        tool_manager.set_brush_size(1)
        
        pencil = tool_manager.get_tool()
        
        # Test different "speeds" (gap sizes between moves)
        test_cases = [
            ("slow", 1),    # 1 pixel gaps
            ("medium", 3),  # 3 pixel gaps  
            ("fast", 7),    # 7 pixel gaps
            ("very_fast", 15)  # 15 pixel gaps
        ]
        
        for speed_name, gap_size in test_cases:
            # Clear image
            image_model.data.fill(0)
            
            # Draw line with specific gap size
            pencil.on_press(2, 15, 12, image_model)
            image_model.set_pixel(2, 15, 12)
            
            x = 2
            while x < 28:
                x += gap_size
                if x > 28:
                    x = 28
                
                line_points = pencil.on_move(x, 15, 12, image_model)
                
                # Apply line points
                for px, py in line_points:
                    image_model.set_pixel(px, py, 12)
            
            # Check for continuous line (no gaps)
            for check_x in range(2, 29):
                assert image_model.get_color_at(check_x, 15) == 12, \
                    f"Gap in {speed_name} drawing at ({check_x}, 15)"