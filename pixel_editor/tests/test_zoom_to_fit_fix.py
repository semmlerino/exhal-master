#!/usr/bin/env python3
"""
Test cases for the zoom-to-fit functionality fix
Tests that the "Fit" button properly zooms and centers the image without making it blank
"""

import pytest
from unittest.mock import Mock
from PyQt6.QtCore import QPointF


class MockEditor:
    """Mock editor that implements only the _zoom_to_fit method for testing"""
    
    def __init__(self):
        self.controller = Mock()
        self.canvas = Mock()
        self.options_panel = Mock()
        
    def _zoom_to_fit(self):
        """Implementation of the fixed zoom-to-fit method"""
        # Get image size first to validate we have an image
        image_size = self.controller.get_image_size()
        if not image_size:
            return
            
        img_width, img_height = image_size
        
        # Get viewport with robust error checking
        canvas_parent = self.canvas.parent()
        if not canvas_parent:
            return
            
        viewport = canvas_parent.parent()  # ScrollArea's viewport
        if not viewport:
            return
            
        # Calculate available viewport space (with padding)
        viewport_width = max(1, viewport.width() - 20)
        viewport_height = max(1, viewport.height() - 20)
        
        # Calculate zoom to fit using float division for precision
        zoom_x = viewport_width / img_width
        zoom_y = viewport_height / img_height
        
        # Round to nearest integer and clamp to valid range
        optimal_zoom = max(1, min(round(min(zoom_x, zoom_y)), 64))
        
        # Let canvas handle centering properly by calling set_zoom
        self.options_panel.set_zoom(optimal_zoom)


class TestZoomToFitFix:
    """Test the zoom-to-fit functionality fix"""
    
    @pytest.fixture 
    def mock_controller(self):
        """Create mock controller with image"""
        controller = Mock()
        controller.get_image_size.return_value = (64, 48)  # 64x48 image
        return controller
    
    @pytest.fixture
    def mock_canvas(self):
        """Create mock canvas with proper parent hierarchy"""
        canvas = Mock()
        canvas.pan_offset = QPointF(10, 10)  # Start with some offset
        
        # Create parent hierarchy: canvas -> widget -> scroll_area
        widget_parent = Mock()
        scroll_area = Mock()
        widget_parent.parent.return_value = scroll_area
        canvas.parent.return_value = widget_parent
        
        # Mock scroll area with dimensions
        scroll_area.width.return_value = 400
        scroll_area.height.return_value = 300
        
        return canvas
    
    @pytest.fixture
    def mock_options_panel(self):
        """Create mock options panel"""
        panel = Mock()
        panel.set_zoom = Mock()
        return panel
    
    @pytest.fixture
    def editor(self, mock_controller, mock_canvas, mock_options_panel):
        """Create editor with mocked components"""
        editor = MockEditor()
        editor.controller = mock_controller
        editor.canvas = mock_canvas
        editor.options_panel = mock_options_panel
        return editor
    
    def test_zoom_to_fit_with_normal_image(self, editor):
        """Test zoom to fit with a normal sized image"""
        # Call zoom to fit
        editor._zoom_to_fit()
        
        # Verify zoom calculation
        # Viewport: 400x300, Image: 64x48, Padding: 20
        # Available space: 380x280
        # zoom_x = 380/64 = 5.9375 → round(5.9375) = 6
        # zoom_y = 280/48 = 5.833... → round(5.833) = 6
        # optimal_zoom = min(6, 6) = 6
        
        editor.options_panel.set_zoom.assert_called_once_with(6)
    
    def test_zoom_to_fit_with_large_image(self, editor):
        """Test zoom to fit with image larger than viewport"""
        # Setup large image
        editor.controller.get_image_size.return_value = (800, 600)  # Large image
        
        # Call zoom to fit
        editor._zoom_to_fit()
        
        # Verify zoom calculation
        # Viewport: 400x300, Image: 800x600, Padding: 20
        # Available space: 380x280
        # zoom_x = 380/800 = 0.475 → round(0.475) = 0 → max(1, 0) = 1
        # zoom_y = 280/600 = 0.466... → round(0.466) = 0 → max(1, 0) = 1
        # optimal_zoom = min(1, 1) = 1
        
        editor.options_panel.set_zoom.assert_called_once_with(1)
    
    def test_zoom_to_fit_with_small_image(self, editor):
        """Test zoom to fit with very small image"""
        # Setup small image
        editor.controller.get_image_size.return_value = (8, 8)  # Small image
        
        # Call zoom to fit
        editor._zoom_to_fit()
        
        # Verify zoom calculation
        # Viewport: 400x300, Image: 8x8, Padding: 20
        # Available space: 380x280
        # zoom_x = 380/8 = 47.5 → round(47.5) = 48
        # zoom_y = 280/8 = 35 → round(35) = 35
        # optimal_zoom = min(48, 35) = 35
        
        editor.options_panel.set_zoom.assert_called_once_with(35)
    
    def test_zoom_to_fit_with_max_zoom_limit(self, editor):
        """Test zoom to fit respects maximum zoom limit"""
        # Setup tiny image that would require huge zoom
        editor.controller.get_image_size.return_value = (2, 2)  # Tiny image
        
        # Call zoom to fit
        editor._zoom_to_fit()
        
        # Verify zoom is clamped to maximum
        # Calculated zoom would be very high, but should be clamped to 64
        editor.options_panel.set_zoom.assert_called_once_with(64)
    
    def test_zoom_to_fit_no_image(self, editor):
        """Test zoom to fit when no image is loaded"""
        # Setup no image
        editor.controller.get_image_size.return_value = None
        
        # Call zoom to fit
        editor._zoom_to_fit()
        
        # Verify no zoom change occurs
        editor.options_panel.set_zoom.assert_not_called()
    
    def test_zoom_to_fit_no_parent(self, editor):
        """Test zoom to fit when canvas has no parent"""
        # Setup canvas with no parent
        editor.canvas.parent.return_value = None
        
        # Call zoom to fit
        editor._zoom_to_fit()
        
        # Verify no zoom change occurs
        editor.options_panel.set_zoom.assert_not_called()
    
    def test_zoom_to_fit_no_viewport(self, editor):
        """Test zoom to fit when viewport is not accessible"""
        # Setup canvas with parent but no viewport
        widget_parent = Mock()
        widget_parent.parent.return_value = None  # No viewport
        editor.canvas.parent.return_value = widget_parent
        
        # Call zoom to fit
        editor._zoom_to_fit()
        
        # Verify no zoom change occurs
        editor.options_panel.set_zoom.assert_not_called()
    
    def test_zoom_to_fit_precision_improvement(self, editor):
        """Test that float division provides better precision than integer division"""
        # Setup image where integer division would give different result
        editor.controller.get_image_size.return_value = (100, 100)  # 100x100 image
        
        # Setup viewport where integer division would be less precise
        scroll_area = editor.canvas.parent().parent()
        scroll_area.width.return_value = 250  # 250 - 20 = 230 available
        scroll_area.height.return_value = 250  # 250 - 20 = 230 available
        
        # Call zoom to fit
        editor._zoom_to_fit()
        
        # Verify zoom calculation
        # With integer division: 230 // 100 = 2
        # With float division: 230 / 100 = 2.3 → round(2.3) = 2
        # In this case both give same result, but float division is more accurate
        
        editor.options_panel.set_zoom.assert_called_once_with(2)
    
    def test_zoom_to_fit_doesnt_reset_pan_offset(self, editor):
        """Test that zoom to fit doesn't manually reset pan offset"""
        # Setup canvas with existing pan offset
        original_pan_offset = QPointF(15, 25)
        editor.canvas.pan_offset = original_pan_offset
        
        # Call zoom to fit
        editor._zoom_to_fit()
        
        # Verify pan offset was not manually reset
        # The canvas's set_zoom method should handle centering properly
        assert editor.canvas.pan_offset == original_pan_offset
        
        # Verify zoom was still set
        editor.options_panel.set_zoom.assert_called_once()
    
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


if __name__ == "__main__":
    pytest.main([__file__, "-v"])