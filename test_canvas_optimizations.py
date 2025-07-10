#!/usr/bin/env python3
"""
Test script to verify canvas rendering optimizations
"""

import sys
import time
import numpy as np
from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton, QHBoxLayout, QLabel
from PyQt6.QtCore import Qt, QTimer

from pixel_editor_widgets import PixelCanvas, ColorPaletteWidget, ZoomableScrollArea
from pixel_editor_constants import DEFAULT_COLOR_PALETTE


class OptimizationTestWindow(QMainWindow):
    """Test window to verify canvas optimizations"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Canvas Optimization Test")
        self.setGeometry(100, 100, 800, 600)
        
        # Create central widget
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        
        # Create info label
        self.info_label = QLabel("Canvas Optimization Test - Watch console for performance info")
        layout.addWidget(self.info_label)
        
        # Create control buttons
        button_layout = QHBoxLayout()
        
        test_viewport_btn = QPushButton("Test Viewport Culling")
        test_viewport_btn.clicked.connect(self.test_viewport_culling)
        button_layout.addWidget(test_viewport_btn)
        
        test_cache_btn = QPushButton("Test Color Cache")
        test_cache_btn.clicked.connect(self.test_color_cache)
        button_layout.addWidget(test_cache_btn)
        
        test_dirty_btn = QPushButton("Test Dirty Rects")
        test_dirty_btn.clicked.connect(self.test_dirty_rects)
        button_layout.addWidget(test_dirty_btn)
        
        layout.addLayout(button_layout)
        
        # Create palette widget
        self.palette_widget = ColorPaletteWidget()
        self.palette_widget.set_color_mode(True)  # Use color palette
        
        # Create canvas
        self.canvas = PixelCanvas(self.palette_widget)
        
        # Create a large test image
        self.canvas.new_image(256, 256)
        
        # Fill with pattern for testing
        for y in range(256):
            for x in range(256):
                # Create a checkerboard pattern with different colors
                color_index = ((x // 16) + (y // 16)) % 16
                self.canvas.image_data[y, x] = color_index
        
        # Create scroll area
        self.scroll_area = ZoomableScrollArea()
        self.scroll_area.setWidget(self.canvas)
        
        layout.addWidget(self.palette_widget)
        layout.addWidget(self.scroll_area)
        
        # FPS counter
        self.fps_label = QLabel("FPS: 0")
        layout.addWidget(self.fps_label)
        
        self.frame_count = 0
        self.last_fps_time = time.time()
        
    def test_viewport_culling(self):
        """Test viewport culling optimization"""
        print("\n=== Testing Viewport Culling ===")
        
        # Check if viewport culling is working
        visible_range = self.canvas._get_visible_pixel_range()
        if visible_range:
            left, top, right, bottom = visible_range
            visible_pixels = (right - left) * (bottom - top)
            total_pixels = 256 * 256
            
            print(f"Visible range: ({left},{top}) to ({right},{bottom})")
            print(f"Visible pixels: {visible_pixels} out of {total_pixels}")
            print(f"Culling efficiency: {100 * (1 - visible_pixels/total_pixels):.1f}%")
            
            self.info_label.setText(
                f"Viewport Culling: Drawing {visible_pixels}/{total_pixels} pixels "
                f"({100 * visible_pixels/total_pixels:.1f}% of image)"
            )
        else:
            print("Could not determine visible range - viewport culling may not be working")
            self.info_label.setText("Viewport culling test failed")
    
    def test_color_cache(self):
        """Test color cache optimization"""
        print("\n=== Testing Color Cache ===")
        
        # Force cache update
        self.canvas._palette_version += 1
        
        # Time color cache creation
        start_time = time.perf_counter()
        self.canvas._update_qcolor_cache()
        cache_time = time.perf_counter() - start_time
        
        print(f"Color cache creation time: {cache_time*1000:.3f}ms")
        print(f"Cached colors: {len(self.canvas._qcolor_cache)}")
        
        # Verify cache contents
        cache_valid = True
        for i in range(16):
            if i not in self.canvas._qcolor_cache:
                print(f"ERROR: Color {i} not in cache!")
                cache_valid = False
        
        if -1 not in self.canvas._qcolor_cache:
            print("ERROR: Invalid color (-1) not in cache!")
            cache_valid = False
            
        if cache_valid:
            print("Color cache validation: PASSED")
            self.info_label.setText(
                f"Color Cache: {len(self.canvas._qcolor_cache)} colors cached in {cache_time*1000:.3f}ms"
            )
        else:
            print("Color cache validation: FAILED")
            self.info_label.setText("Color cache test failed")
    
    def test_dirty_rects(self):
        """Test dirty rectangle optimization"""
        print("\n=== Testing Dirty Rectangles ===")
        
        # Clear any existing dirty rect
        self.canvas._dirty_rect = None
        
        # Draw a single pixel
        self.canvas.draw_pixel(50, 50)
        
        if self.canvas._dirty_rect:
            dirty = self.canvas._dirty_rect
            print(f"Dirty rect after single pixel: {dirty.x()},{dirty.y()} {dirty.width()}x{dirty.height()}")
            
            expected_size = self.canvas.zoom
            if dirty.width() == expected_size and dirty.height() == expected_size:
                print("Dirty rect size: CORRECT")
            else:
                print(f"Dirty rect size: INCORRECT (expected {expected_size}x{expected_size})")
            
            # Draw another pixel and check accumulation
            self.canvas.draw_pixel(52, 52)
            dirty2 = self.canvas._dirty_rect
            print(f"Dirty rect after second pixel: {dirty2.x()},{dirty2.y()} {dirty2.width()}x{dirty2.height()}")
            
            self.info_label.setText(
                f"Dirty Rects: Single pixel creates {dirty.width()}x{dirty.height()} update region"
            )
        else:
            print("ERROR: No dirty rect created!")
            self.info_label.setText("Dirty rect test failed")
    
    def paintEvent(self, event):
        """Track paint events for FPS counter"""
        super().paintEvent(event)
        
        self.frame_count += 1
        current_time = time.time()
        elapsed = current_time - self.last_fps_time
        
        if elapsed > 1.0:
            fps = self.frame_count / elapsed
            self.fps_label.setText(f"FPS: {fps:.1f}")
            self.frame_count = 0
            self.last_fps_time = current_time


def main():
    """Run the optimization test"""
    app = QApplication(sys.argv)
    
    window = OptimizationTestWindow()
    window.show()
    
    # Run initial tests after window is shown
    QTimer.singleShot(100, window.test_viewport_culling)
    QTimer.singleShot(200, window.test_color_cache)
    QTimer.singleShot(300, window.test_dirty_rects)
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()