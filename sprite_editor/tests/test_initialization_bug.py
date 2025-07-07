#!/usr/bin/env python3
"""
Specific test for the ViewerController initialization order bug
This test would have caught the AttributeError we fixed
"""

import pytest
from unittest.mock import Mock

from sprite_editor.controllers.viewer_controller import ViewerController


class TestInitializationOrderBug:
    """Test that specifically targets the initialization order bug"""
    
    def test_viewer_controller_palette_model_initialization_order(self):
        """
        This test reproduces the exact bug that was fixed:
        AttributeError: 'ViewerController' object has no attribute 'palette_model'
        
        The bug occurred because connect_signals() was called from the parent's __init__
        before palette_model was set in ViewerController.__init__
        """
        # Create mocks
        sprite_model = Mock()
        palette_model = Mock()
        view = Mock()
        
        # Mock all required signals that connect_signals() expects
        view.zoom_in_requested = Mock()
        view.zoom_out_requested = Mock()
        view.zoom_fit_requested = Mock()
        view.grid_toggled = Mock()
        view.save_requested = Mock()
        view.open_editor_requested = Mock()
        
        sprite_model.current_image_changed = Mock()
        palette_model.palette_applied = Mock()
        
        # Before the fix, this would raise:
        # AttributeError: 'ViewerController' object has no attribute 'palette_model'
        # at line 34 in connect_signals: self.palette_model.palette_applied.connect(...)
        
        controller = ViewerController(sprite_model, palette_model, view)
        
        # Verify the controller was created successfully
        assert controller is not None
        assert controller.palette_model == palette_model
        assert controller.model == sprite_model
        assert controller.view == view
    
    def test_connect_signals_requires_palette_model(self):
        """
        Test that connect_signals() actually uses palette_model
        This ensures our fix is necessary
        """
        # Create a custom controller that verifies palette_model usage
        class TestViewerController(ViewerController):
            def connect_signals(self):
                # Verify palette_model is available
                assert hasattr(self, 'palette_model'), \
                    "palette_model must be set before connect_signals is called"
                assert self.palette_model is not None, \
                    "palette_model must not be None"
                
                # Track that we accessed palette_model
                self.palette_model_accessed = True
                
                # Call parent implementation
                super().connect_signals()
        
        # Create mocks
        sprite_model = Mock()
        palette_model = Mock()
        palette_model.palette_applied = Mock()
        view = Mock()
        
        # Add required view signals
        view.zoom_in_requested = Mock()
        view.zoom_out_requested = Mock()
        view.zoom_fit_requested = Mock()
        view.grid_toggled = Mock()
        view.save_requested = Mock()
        view.open_editor_requested = Mock()
        
        sprite_model.current_image_changed = Mock()
        
        # Create controller
        controller = TestViewerController(sprite_model, palette_model, view)
        
        # Verify palette_model was accessed during initialization
        assert hasattr(controller, 'palette_model_accessed')
        assert controller.palette_model_accessed is True
    
    def test_initialization_order_with_base_controller(self):
        """
        Test the interaction between BaseController and ViewerController
        This shows why the initialization order matters
        """
        initialization_log = []
        
        # Track when each method is called
        original_base_init = ViewerController.__bases__[0].__init__
        original_viewer_init = ViewerController.__init__
        original_connect_signals = ViewerController.connect_signals
        
        def tracked_base_init(self, model, view, parent):
            initialization_log.append('BaseController.__init__ started')
            original_base_init(self, model, view, parent)
            initialization_log.append('BaseController.__init__ finished')
        
        def tracked_viewer_init(self, sprite_model, palette_model, viewer_view, parent=None):
            initialization_log.append('ViewerController.__init__ started')
            initialization_log.append(f'Setting palette_model = {palette_model}')
            original_viewer_init(self, sprite_model, palette_model, viewer_view, parent)
            initialization_log.append('ViewerController.__init__ finished')
        
        def tracked_connect_signals(self):
            initialization_log.append('connect_signals called')
            if hasattr(self, 'palette_model'):
                initialization_log.append('palette_model is available')
            else:
                initialization_log.append('ERROR: palette_model NOT available!')
            original_connect_signals(self)
        
        # Temporarily replace methods
        ViewerController.__bases__[0].__init__ = tracked_base_init
        ViewerController.__init__ = tracked_viewer_init
        ViewerController.connect_signals = tracked_connect_signals
        
        try:
            # Create mocks
            sprite_model = Mock()
            palette_model = Mock()
            palette_model.palette_applied = Mock()
            view = Mock()
            
            # Add required signals
            view.zoom_in_requested = Mock()
            view.zoom_out_requested = Mock()
            view.zoom_fit_requested = Mock()
            view.grid_toggled = Mock()
            view.save_requested = Mock()
            view.open_editor_requested = Mock()
            sprite_model.current_image_changed = Mock()
            
            # Create controller
            controller = ViewerController(sprite_model, palette_model, view)
            
            # Verify the initialization order
            expected_order = [
                'ViewerController.__init__ started',
                f'Setting palette_model = {palette_model}',
                'BaseController.__init__ started',
                'connect_signals called',
                'palette_model is available',  # This is key - it must be available
                'BaseController.__init__ finished',
                'ViewerController.__init__ finished'
            ]
            
            # The actual order should show palette_model is set before connect_signals
            assert 'palette_model is available' in initialization_log
            assert 'ERROR: palette_model NOT available!' not in initialization_log
            
        finally:
            # Restore original methods
            ViewerController.__bases__[0].__init__ = original_base_init
            ViewerController.__init__ = original_viewer_init
            ViewerController.connect_signals = original_connect_signals


if __name__ == "__main__":
    pytest.main([__file__, "-v"])