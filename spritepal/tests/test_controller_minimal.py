"""Minimal controller tests without complex fixtures"""
from __future__ import annotations

import pytest
from unittest.mock import Mock

# Systematic pytest markers applied based on test content analysis
pytestmark = [
    pytest.mark.headless,
    pytest.mark.mock_only,
    pytest.mark.no_qt,
    pytest.mark.parallel_safe,
    pytest.mark.rom_data,
    pytest.mark.unit,
    pytest.mark.ci_safe,
]

@pytest.mark.no_manager_setup
class TestControllerMinimal:
    """Minimal controller tests to verify basic functionality"""
    
    def test_controller_import(self):
        """Test that controller module can be imported"""
        import core.controller
        assert hasattr(core.controller, 'ExtractionController')
    
    def test_controller_with_mock_window(self):
        """Test controller creation with mock window"""
        from unittest.mock import patch
        
        # Mock the managers and preview generator to avoid initialization
        with patch('core.controller.get_extraction_manager'), \
             patch('core.controller.get_injection_manager'), \
             patch('core.controller.get_session_manager'), \
             patch('core.controller.get_preview_generator') as mock_get_preview:
            
            from core.controller import ExtractionController
            
            # Mock the preview generator
            mock_preview_gen = Mock()
            mock_preview_gen.set_managers = Mock()  # This was causing the context manager error
            mock_get_preview.return_value = mock_preview_gen
            
            # Create mock window
            mock_window = Mock()
            mock_window.extract_requested = Mock()
            mock_window.open_in_editor_requested = Mock()
            mock_window.arrange_rows_requested = Mock()
            mock_window.arrange_grid_requested = Mock()
            mock_window.inject_requested = Mock()
            mock_window.extraction_completed = Mock()
            mock_window.extraction_error_occurred = Mock()
            
            # Create controller
            controller = ExtractionController(mock_window)
            
            # Basic assertions
            assert controller.main_window == mock_window
            assert controller.worker is None
            assert hasattr(controller, 'start_extraction')
    
    def test_parameter_validation(self):
        """Test extraction parameter validation"""
        from unittest.mock import patch
        from core.controller import ExtractionController
        
        with patch('core.controller.get_extraction_manager') as mock_get_ext, \
             patch('core.controller.get_injection_manager'), \
             patch('core.controller.get_session_manager'), \
             patch('core.controller.get_preview_generator') as mock_get_preview:
            
            # Setup mocks
            mock_preview_gen = Mock()
            mock_preview_gen.set_managers = Mock()
            mock_get_preview.return_value = mock_preview_gen
            
            mock_window = Mock()
            mock_window.get_extraction_params = Mock(return_value={
                "vram_path": "",
                "cgram_path": "/path/to/cgram",
                "output_base": "/path/to/output"
            })
            mock_window.extraction_failed = Mock()
            
            mock_manager = Mock()
            mock_manager.validate_extraction_params.side_effect = ValueError("VRAM required")
            mock_get_ext.return_value = mock_manager
            
            # Create controller and test
            controller = ExtractionController(mock_window)
            controller.start_extraction()
            
            # Verify failure was handled
            mock_window.extraction_failed.assert_called_once()