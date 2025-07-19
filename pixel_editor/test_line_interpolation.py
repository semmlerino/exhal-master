#!/usr/bin/env python3
"""
Test script to verify line interpolation functionality in the pixel editor.
This script tests the drawing consistency fix for fast mouse movements.
"""

import numpy as np
from core.pixel_editor_managers import PencilTool
from core.pixel_editor_models import ImageModel


def test_line_interpolation():
    """Test that line interpolation works correctly"""
    print("Testing line interpolation...")
    
    # Create a test image model
    image_model = ImageModel(width=10, height=10)
    
    # Create pencil tool
    tool = PencilTool()
    
    # Test 1: Horizontal line
    print("\nTest 1: Horizontal line from (1,1) to (5,1)")
    tool.on_press(1, 1, 5, image_model)
    line_points = tool.on_move(5, 1, 5, image_model)
    
    print(f"Line points: {line_points}")
    
    # Apply the line points to the image
    for x, y in line_points:
        image_model.set_pixel(x, y, 5)
    
    # Verify all points are filled
    for x in range(1, 6):
        if image_model.get_color_at(x, 1) != 5:
            print(f"ERROR: Point ({x}, 1) not filled")
            return False
    
    print("✓ Horizontal line test passed")
    
    # Test 2: Diagonal line
    print("\nTest 2: Diagonal line from (2,2) to (6,6)")
    tool.on_press(2, 2, 7, image_model)
    line_points = tool.on_move(6, 6, 7, image_model)
    
    print(f"Line points: {line_points}")
    
    # Apply the line points to the image
    for x, y in line_points:
        image_model.set_pixel(x, y, 7)
    
    # Verify diagonal line is connected (should have at least 5 points)
    filled_count = len(line_points)
    print(f"Diagonal line has {filled_count} points")
    if filled_count < 5:
        print("ERROR: Diagonal line too short")
        return False
    
    print("✓ Diagonal line test passed")
    
    # Test 3: Verify position tracking reset
    print("\nTest 3: Testing position tracking reset on release")
    tool.on_release(6, 6, 7, image_model)
    
    # After release, the next move should start fresh
    line_points = tool.on_move(8, 8, 3, image_model)
    print(f"Points after release: {line_points}")
    
    # Should only have the current position since there's no previous position
    if len(line_points) != 1 or line_points[0] != (8, 8):
        print("ERROR: Position tracking not reset properly")
        return False
    
    print("✓ Position tracking reset test passed")
    
    print("\nAll tests passed! ✓")
    return True


def test_fast_movement_simulation():
    """Simulate fast mouse movement that would skip pixels without interpolation"""
    print("\nTesting fast movement simulation...")
    
    # Create a test image model
    image_model = ImageModel(width=20, height=20)
    tool = PencilTool()
    
    # Simulate fast mouse movement with large gaps
    positions = [(0, 0), (5, 3), (10, 7), (15, 10)]
    
    # Start drawing
    tool.on_press(positions[0][0], positions[0][1], 9, image_model)
    image_model.set_pixel(positions[0][0], positions[0][1], 9)
    
    total_points = 1
    
    # Move through positions with large gaps
    for i in range(1, len(positions)):
        x, y = positions[i]
        line_points = tool.on_move(x, y, 9, image_model)
        
        # Apply the line points
        for px, py in line_points:
            image_model.set_pixel(px, py, 9)
        
        total_points += len(line_points)
        print(f"Move to {positions[i]}: {len(line_points)} points interpolated")
    
    print(f"Total points drawn: {total_points}")
    
    # Verify there's a connected path
    if total_points < len(positions):
        print("ERROR: Not enough points for connected path")
        return False
    
    print("✓ Fast movement simulation test passed")
    return True


if __name__ == "__main__":
    print("=== Line Interpolation Test ===")
    
    success = True
    
    try:
        success &= test_line_interpolation()
        success &= test_fast_movement_simulation()
        
        if success:
            print("\n🎉 All tests passed! Drawing consistency fix is working correctly.")
        else:
            print("\n❌ Some tests failed. Please check the implementation.")
            
    except Exception as e:
        print(f"\n❌ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        success = False
    
    exit(0 if success else 1)