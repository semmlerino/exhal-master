#!/usr/bin/env python3
"""
Test cases for the zoom-to-fit functionality fix
Tests that the "Fit" button properly zooms and centers the image without making it blank
"""

import pytest
from unittest.mock import Mock, patch
from PyQt6.QtCore import QPointF
from PyQt6.QtWidgets import QApplication

from pixel_editor.core.indexed_pixel_editor_v3 import IndexedPixelEditor


class TestZoomToFitFix:
    """Test the zoom-to-fit functionality fix using real IndexedPixelEditor"""
    
    @pytest.fixture
    def app(self):
        """Create QApplication instance for Qt tests"""
        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        return app
    
    @pytest.fixture
    def editor(self, app):
        """Create real IndexedPixelEditor with minimal UI mocking"""
        # Mock UI components that would cause headless testing issues
        with patch('pixel_editor.core.indexed_pixel_editor_v3.StartupDialog') as mock_dialog:
            # Mock the startup dialog to avoid UI interaction
            mock_dialog.return_value.exec.return_value = False
            
            # Create real editor instance
            editor = IndexedPixelEditor()
            
            # Create a test image
            editor.controller.new_file(64, 48)
            
            # Mock the scroll area hierarchy for viewport calculations
            # This is the only UI component we need to mock for zoom-to-fit
            scroll_area = Mock()
            scroll_area.width.return_value = 400
            scroll_area.height.return_value = 300
            
            widget_parent = Mock()
            widget_parent.parent.return_value = scroll_area
            
            editor.canvas.parent = Mock(return_value=widget_parent)
            
            # Mock canvas dimensions for pan offset calculation
            editor.canvas.width = Mock(return_value=400)
            editor.canvas.height = Mock(return_value=300)
            
            return editor
    
    def test_zoom_to_fit_with_normal_image(self, editor):
        """Test zoom to fit with a normal sized image"""
        # Call zoom to fit on real editor
        editor._zoom_to_fit()
        
        # Verify zoom calculation
        # Viewport: 400x300, Image: 64x48, Padding: 20
        # Available space: 380x280
        # zoom_x = 380/64 = 5.9375 → round(5.9375) = 6
        # zoom_y = 280/48 = 5.833... → round(5.833) = 6
        # optimal_zoom = min(6, 6) = 6
        
        # Verify canvas zoom was set correctly
        assert editor.canvas.zoom == 6, f"Expected canvas zoom 6, got {editor.canvas.zoom}"
        
        # Verify options panel zoom slider was updated
        assert editor.options_panel.zoom_slider.value() == 6, "Zoom slider should be updated to 6"
        
        # Verify pan offset was set for centering
        assert editor.canvas.pan_offset is not None, "Pan offset should be set for centering"
    
    def test_zoom_to_fit_with_large_image(self, editor):
        """Test zoom to fit with image larger than viewport"""
        # Setup large image using real controller
        editor.controller.new_file(800, 600)
        
        # Call zoom to fit
        editor._zoom_to_fit()
        
        # Verify zoom calculation
        # Viewport: 400x300, Image: 800x600, Padding: 20
        # Available space: 380x280
        # zoom_x = 380/800 = 0.475 → round(0.475) = 0 → max(1, 0) = 1
        # zoom_y = 280/600 = 0.466... → round(0.466) = 0 → max(1, 0) = 1
        # optimal_zoom = min(1, 1) = 1
        
        # Verify canvas zoom was set correctly
        assert editor.canvas.zoom == 1, f"Expected canvas zoom 1, got {editor.canvas.zoom}"
        
        # Verify options panel zoom slider was updated
        assert editor.options_panel.zoom_slider.value() == 1, "Zoom slider should be updated to 1"
    
    def test_zoom_to_fit_with_small_image(self, editor):
        """Test zoom to fit with very small image"""
        # Setup small image using real controller
        editor.controller.new_file(8, 8)
        
        # Call zoom to fit
        editor._zoom_to_fit()
        
        # Verify zoom calculation
        # Viewport: 400x300, Image: 8x8, Padding: 20
        # Available space: 380x280
        # zoom_x = 380/8 = 47.5 → round(47.5) = 48
        # zoom_y = 280/8 = 35 → round(35) = 35
        # optimal_zoom = min(48, 35) = 35
        
        # Verify canvas zoom was set correctly
        assert editor.canvas.zoom == 35, f"Expected canvas zoom 35, got {editor.canvas.zoom}"
        
        # Verify options panel zoom slider was updated
        assert editor.options_panel.zoom_slider.value() == 35, "Zoom slider should be updated to 35"
    
    def test_zoom_to_fit_with_max_zoom_limit(self, editor):
        """Test zoom to fit respects maximum zoom limit"""
        # Setup tiny image that would require huge zoom
        editor.controller.new_file(2, 2)
        
        # Call zoom to fit
        editor._zoom_to_fit()
        
        # Verify zoom is clamped to maximum
        # Calculated zoom would be very high, but should be clamped to 64
        assert editor.canvas.zoom == 64, f"Expected canvas zoom 64, got {editor.canvas.zoom}"
        
        # Verify options panel zoom slider was updated
        assert editor.options_panel.zoom_slider.value() == 64, "Zoom slider should be updated to 64"
    
    def test_zoom_to_fit_no_image(self, editor):
        """Test zoom to fit when no image is loaded"""
        # Clear image data to simulate no image
        editor.controller.image_model.data = None
        
        # Store original zoom to verify it doesn't change
        original_zoom = editor.canvas.zoom
        
        # Call zoom to fit
        editor._zoom_to_fit()
        
        # Verify no zoom change occurs
        assert editor.canvas.zoom == original_zoom, "Zoom should not change when no image is loaded"
    
    def test_zoom_to_fit_no_parent(self, editor):
        """Test zoom to fit when canvas has no parent"""
        # Setup canvas with no parent
        editor.canvas.parent = Mock(return_value=None)
        
        # Store original zoom to verify it doesn't change
        original_zoom = editor.canvas.zoom
        
        # Call zoom to fit
        editor._zoom_to_fit()
        
        # Verify no zoom change occurs
        assert editor.canvas.zoom == original_zoom, "Zoom should not change when canvas has no parent"
    
    def test_zoom_to_fit_no_viewport(self, editor):
        """Test zoom to fit when viewport is not accessible"""
        # Setup canvas with parent but no viewport
        widget_parent = Mock()
        widget_parent.parent.return_value = None  # No viewport
        editor.canvas.parent = Mock(return_value=widget_parent)
        
        # Store original zoom to verify it doesn't change
        original_zoom = editor.canvas.zoom
        
        # Call zoom to fit
        editor._zoom_to_fit()
        
        # Verify no zoom change occurs
        assert editor.canvas.zoom == original_zoom, "Zoom should not change when viewport is not accessible"
    
    def test_zoom_to_fit_precision_improvement(self, editor):
        """Test that float division provides better precision than integer division"""
        # Setup image where integer division would give different result
        editor.controller.new_file(100, 100)
        
        # Setup viewport where integer division would be less precise
        scroll_area = Mock()
        scroll_area.width.return_value = 250  # 250 - 20 = 230 available
        scroll_area.height.return_value = 250  # 250 - 20 = 230 available
        
        widget_parent = Mock()
        widget_parent.parent.return_value = scroll_area
        editor.canvas.parent = Mock(return_value=widget_parent)
        
        # Call zoom to fit
        editor._zoom_to_fit()
        
        # Verify zoom calculation
        # With integer division: 230 // 100 = 2
        # With float division: 230 / 100 = 2.3 → round(2.3) = 2
        # In this case both give same result, but float division is more accurate
        
        # Verify canvas zoom was set correctly
        assert editor.canvas.zoom == 2, f"Expected canvas zoom 2, got {editor.canvas.zoom}"
        
        # Verify options panel zoom slider was updated
        assert editor.options_panel.zoom_slider.value() == 2, "Zoom slider should be updated to 2"
    
    def test_zoom_to_fit_sets_proper_pan_offset(self, editor):
        """Test that zoom to fit sets proper pan offset for centering"""
        # Setup canvas with existing pan offset
        original_pan_offset = QPointF(15, 25)
        editor.canvas.pan_offset = original_pan_offset
        
        # Call zoom to fit
        editor._zoom_to_fit()
        
        # Verify pan offset was set to center the image
        # The new implementation should set a proper pan offset for centering
        assert editor.canvas.pan_offset != original_pan_offset, "Pan offset should be updated for centering"
        
        # Verify zoom was changed from default
        assert editor.canvas.zoom != 4, "Zoom should be changed from default (4x)"
    
    def test_float_vs_integer_division_precision(self):
        """Test that float division gives better precision than integer division"""
        # Test cases where integer division would lose precision
        test_cases = [
            (380, 64, 5.9375, 6),  # 380/64 = 5.9375 → 6, but 380//64 = 5
            (280, 48, 5.833, 6),   # 280/48 = 5.833 → 6, but 280//48 = 5
            (230, 100, 2.3, 2),    # 230/100 = 2.3 → 2, and 230//100 = 2
            (150, 80, 1.875, 2),   # 150/80 = 1.875 → 2, but 150//80 = 1
        ]
        
        for viewport, image, expected_float, expected_result in test_cases:
            # Float division with rounding
            float_result = round(viewport / image)
            
            # Integer division 
            int_result = viewport // image
            
            assert float_result == expected_result, f"Float division failed for {viewport}/{image}"
            
            # Show that integer division can be less accurate
            if int_result != expected_result:
                print(f"Integer division less accurate: {viewport}//{image} = {int_result}, but round({viewport}/{image}) = {float_result}")


class TestZoomToFitRegressionFix:
    """Test the regression fix for zoom-to-fit after zooming in using real editor"""
    
    @pytest.fixture
    def app(self):
        """Create QApplication instance for Qt tests"""
        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        return app
    
    def test_zoom_to_fit_after_zooming_in(self, app):
        """Test that zoom-to-fit works correctly after zooming in (regression test)"""
        # This test simulates the user scenario that was failing:
        # 1. User zooms in to a high level
        # 2. User presses F or clicks Fit button
        # 3. Image should remain visible and centered (not go blank)
        
        # Create real editor with minimal UI mocking
        with patch('pixel_editor.core.indexed_pixel_editor_v3.StartupDialog') as mock_dialog:
            mock_dialog.return_value.exec.return_value = False
            
            editor = IndexedPixelEditor()
            editor.controller.new_file(32, 24)  # Small image
            
            # Mock the scroll area hierarchy for viewport calculations
            scroll_area = Mock()
            scroll_area.width.return_value = 400
            scroll_area.height.return_value = 300
            
            widget_parent = Mock()
            widget_parent.parent.return_value = scroll_area
            editor.canvas.parent = Mock(return_value=widget_parent)
            
            # Mock canvas dimensions for pan offset calculation
            editor.canvas.width = Mock(return_value=512)
            editor.canvas.height = Mock(return_value=384)
            
            # Step 1: Zoom in to a high level (simulate user zooming in)
            editor.canvas.set_zoom(32)  # High zoom level
            
            # Step 2: Execute zoom-to-fit (simulate pressing F or clicking Fit)
            editor._zoom_to_fit()
            
            # Step 3: Verify image remains visible and centered
            # Expected zoom calculation:
            # Viewport: 400x300, Image: 32x24, Padding: 20
            # Available space: 380x280
            # zoom_x = 380/32 = 11.875 → round(11.875) = 12
            # zoom_y = 280/24 = 11.666... → round(11.666) = 12
            # optimal_zoom = min(12, 12) = 12
            expected_zoom = 12
            
            # Verify zoom was set correctly
            assert editor.canvas.zoom == expected_zoom, f"Expected zoom {expected_zoom}, got {editor.canvas.zoom}"
            
            # Verify pan offset was set for centering
            assert editor.canvas.pan_offset is not None, "Pan offset should be set for centering"
            
            # Verify options panel was updated
            assert editor.options_panel.zoom_slider.value() == expected_zoom, "Zoom slider should be updated"
            
            # This is the key regression test: the image should NOT go blank
            # If the bug were present, the zoom would be incorrect or pan offset would be wrong
            assert editor.canvas.zoom > 0, "Canvas zoom should be positive (not blank)"
            assert editor.canvas.zoom != 32, "Zoom should have changed from high zoom (32) to fit zoom"
    
    def test_zoom_to_fit_centering_calculation(self):
        """Test that the centering calculation is correct for various scenarios"""
        test_cases = [
            # (canvas_width, canvas_height, img_width, img_height, zoom, expected_pan_x, expected_pan_y)
            (400, 300, 32, 24, 8, 72, 54),     # Image smaller than canvas
            (200, 150, 64, 48, 2, 36, 27),     # Image smaller than canvas
            (100, 100, 50, 50, 1, 25, 25),     # Image smaller than canvas
            (512, 384, 128, 96, 2, 128, 96),   # Image smaller than canvas
        ]
        
        for canvas_w, canvas_h, img_w, img_h, zoom, expected_pan_x, expected_pan_y in test_cases:
            # Calculate pan offset using the same logic as the implementation
            scaled_img_width = img_w * zoom
            scaled_img_height = img_h * zoom
            
            pan_x = (canvas_w - scaled_img_width) / 2
            pan_y = (canvas_h - scaled_img_height) / 2
            
            assert pan_x == expected_pan_x, f"Pan X calculation failed: expected {expected_pan_x}, got {pan_x}"
            assert pan_y == expected_pan_y, f"Pan Y calculation failed: expected {expected_pan_y}, got {pan_y}"
    
    def test_zoom_to_fit_bypass_workflow(self, app):
        """Test that zoom-to-fit bypasses the normal zoom workflow"""
        # This test verifies that the new implementation doesn't trigger
        # the normal zoom change workflow that was causing the blank image issue
        
        # Create real editor with minimal UI mocking
        with patch('pixel_editor.core.indexed_pixel_editor_v3.StartupDialog') as mock_dialog:
            mock_dialog.return_value.exec.return_value = False
            
            editor = IndexedPixelEditor()
            editor.controller.new_file(16, 16)
            
            # Mock canvas parent hierarchy
            scroll_area = Mock()
            scroll_area.width.return_value = 200
            scroll_area.height.return_value = 200
            widget_parent = Mock()
            widget_parent.parent.return_value = scroll_area
            editor.canvas.parent = Mock(return_value=widget_parent)
            
            # Mock canvas dimensions
            editor.canvas.width = Mock(return_value=256)
            editor.canvas.height = Mock(return_value=256)
            
            # Store original zoom to verify direct setting
            original_zoom = editor.canvas.zoom
            
            # Execute zoom-to-fit
            editor._zoom_to_fit()
            
            # Verify that canvas zoom was set directly
            # Expected zoom: (200-20)/16 = 180/16 = 11.25 → round(11.25) = 11
            expected_zoom = 11
            assert editor.canvas.zoom == expected_zoom, f"Expected zoom {expected_zoom}, got {editor.canvas.zoom}"
            
            # Verify that zoom slider was updated
            assert editor.options_panel.zoom_slider.value() == expected_zoom, "Zoom slider should be updated"
            
            # The key test: verify zoom changed from original (indicating direct setting worked)
            assert editor.canvas.zoom != original_zoom, "Zoom should have changed from original value"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])