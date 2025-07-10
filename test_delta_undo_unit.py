#!/usr/bin/env python3
"""
Unit tests for the delta-based undo system integration
"""

import sys
import os
import numpy as np

# Set Qt to use offscreen platform for headless testing
os.environ['QT_QPA_PLATFORM'] = 'offscreen'

from PyQt6.QtWidgets import QApplication

# Create QApplication before importing widgets
app = QApplication(sys.argv)

from pixel_editor_widgets import PixelCanvas, ColorPaletteWidget
from pixel_editor_commands import DrawPixelCommand, DrawLineCommand, FloodFillCommand, BatchCommand


def test_basic_undo_redo():
    """Test basic undo/redo functionality"""
    print("Testing basic undo/redo...")
    
    # Create canvas
    palette = ColorPaletteWidget()
    canvas = PixelCanvas(palette)
    canvas.new_image(10, 10)
    
    # Initial state - all zeros
    assert np.all(canvas.image_data == 0), "Initial image should be all zeros"
    
    # Draw a pixel
    canvas.current_color = 5
    canvas.draw_pixel(2, 3)
    assert canvas.image_data[3, 2] == 5, "Pixel should be drawn"
    
    # Undo
    canvas.undo()
    assert canvas.image_data[3, 2] == 0, "Pixel should be undone"
    
    # Redo
    canvas.redo()
    assert canvas.image_data[3, 2] == 5, "Pixel should be redrawn"
    
    print("✓ Basic undo/redo works correctly")


def test_batch_command():
    """Test batch command for continuous drawing"""
    print("\nTesting batch command for continuous drawing...")
    
    # Create canvas
    palette = ColorPaletteWidget()
    canvas = PixelCanvas(palette)
    canvas.new_image(10, 10)
    
    # Simulate continuous drawing
    canvas.current_color = 3
    canvas.current_batch = BatchCommand()
    
    # Draw multiple pixels
    canvas.draw_pixel(1, 1)
    canvas.draw_pixel(2, 1)
    canvas.draw_pixel(3, 1)
    
    # Check pixels are drawn
    assert canvas.image_data[1, 1] == 3
    assert canvas.image_data[1, 2] == 3
    assert canvas.image_data[1, 3] == 3
    
    # Finalize batch
    if canvas.current_batch and len(canvas.current_batch.commands) > 0:
        canvas.undo_manager.execute_command(canvas.current_batch, canvas)
        canvas.current_batch = None
    
    # Undo should undo all three pixels
    canvas.undo()
    assert canvas.image_data[1, 1] == 0
    assert canvas.image_data[1, 2] == 0
    assert canvas.image_data[1, 3] == 0
    
    print("✓ Batch command works correctly")


def test_memory_efficiency():
    """Test memory efficiency of delta system"""
    print("\nTesting memory efficiency...")
    
    # Create larger canvas
    palette = ColorPaletteWidget()
    canvas = PixelCanvas(palette)
    canvas.new_image(100, 100)
    
    # Get initial memory
    initial_stats = canvas.get_undo_memory_stats()
    print(f"  Initial: {initial_stats['total_bytes']} bytes")
    
    # Draw 50 individual pixels
    canvas.current_color = 7
    for i in range(50):
        canvas.draw_pixel(i, i)
    
    # Check memory usage
    pixel_stats = canvas.get_undo_memory_stats()
    print(f"  After 50 pixels: {pixel_stats['total_bytes']} bytes ({pixel_stats['command_count']} commands)")
    
    # Memory per pixel command should be small (around 80 bytes each)
    bytes_per_command = pixel_stats['total_bytes'] / pixel_stats['command_count']
    assert bytes_per_command < 200, f"Commands are too large: {bytes_per_command} bytes each"
    
    # Test compression of old commands
    # Add more commands to trigger compression
    for i in range(30):
        canvas.draw_pixel(50 + i, i)
    
    final_stats = canvas.get_undo_memory_stats()
    print(f"  After 80 pixels: {final_stats['total_bytes']} bytes ({final_stats['compressed_count']} compressed)")
    
    # Verify some commands got compressed
    assert final_stats['compressed_count'] > 0, "Old commands should be compressed"
    
    print("✓ Memory efficiency verified")


def test_flood_fill_command():
    """Test flood fill with delta command"""
    print("\nTesting flood fill command...")
    
    # Create canvas
    palette = ColorPaletteWidget()
    canvas = PixelCanvas(palette)
    canvas.new_image(10, 10)
    
    # Create a shape to fill
    canvas.current_color = 1
    # Draw a square
    for i in range(3, 7):
        canvas.draw_pixel(i, 3)  # Top
        canvas.draw_pixel(i, 6)  # Bottom
        canvas.draw_pixel(3, i)  # Left
        canvas.draw_pixel(6, i)  # Right
    
    # Fill the square
    canvas.current_color = 5
    canvas.flood_fill(5, 5)
    
    # Check fill worked
    assert canvas.image_data[5, 5] == 5, "Center should be filled"
    assert canvas.image_data[4, 4] == 5, "Inside should be filled"
    assert canvas.image_data[2, 2] == 0, "Outside should not be filled"
    
    # Undo flood fill
    canvas.undo()
    assert canvas.image_data[5, 5] == 0, "Fill should be undone"
    assert canvas.image_data[4, 4] == 0, "Fill should be undone"
    
    # Redo flood fill
    canvas.redo()
    assert canvas.image_data[5, 5] == 5, "Fill should be redone"
    
    print("✓ Flood fill command works correctly")


def test_line_command():
    """Test line drawing with delta command"""
    print("\nTesting line command...")
    
    # Create canvas
    palette = ColorPaletteWidget()
    canvas = PixelCanvas(palette)
    canvas.new_image(10, 10)
    
    # Draw a line
    canvas.current_color = 4
    canvas.draw_line(1, 1, 5, 5)
    
    # Check line pixels
    for i in range(5):
        assert canvas.image_data[1 + i, 1 + i] == 4, f"Diagonal line pixel ({1+i}, {1+i}) should be drawn"
    
    # Undo line
    canvas.undo()
    for i in range(5):
        assert canvas.image_data[1 + i, 1 + i] == 0, f"Line pixel ({1+i}, {1+i}) should be undone"
    
    print("✓ Line command works correctly")


def main():
    """Run all tests"""
    print("Delta-based Undo System Integration Tests")
    print("=========================================")
    
    try:
        test_basic_undo_redo()
        test_batch_command()
        test_memory_efficiency()
        test_flood_fill_command()
        test_line_command()
        
        print("\n✅ All tests passed!")
        
        # Print summary
        print("\nSummary:")
        print("- DrawPixelCommand integration: ✓")
        print("- DrawLineCommand integration: ✓")
        print("- FloodFillCommand integration: ✓")
        print("- BatchCommand for continuous drawing: ✓")
        print("- Memory efficiency with compression: ✓")
        print("- Undo/redo functionality: ✓")
        
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        return 1
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())