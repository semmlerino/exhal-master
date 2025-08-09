"""Fixed controller tests that don't hang during collection"""

import pytest
from unittest.mock import Mock, patch


@pytest.mark.no_manager_setup
class TestControllerFixed:
    """Controller tests with proper mocking to prevent hanging"""
    
# Systematic pytest markers applied based on test content analysis
pytestmark = [
    pytest.mark.headless,
    pytest.mark.mock_only,
    pytest.mark.no_qt,
    pytest.mark.parallel_safe,
    pytest.mark.rom_data,
    pytest.mark.unit,
]


    def test_controller_import(self):
        """Test that controller module can be imported"""
        import core.controller
        assert hasattr(core.controller, 'ExtractionController')
        assert hasattr(core.controller, 'pil_to_qpixmap')
    
    def test_extraction_controller_creation(self):
        """Test ExtractionController can be created with mocks"""
        with patch('core.controller.get_extraction_manager'), \
             patch('core.controller.get_injection_manager'), \
             patch('core.controller.get_session_manager'), \
             patch('core.controller.get_preview_generator') as mock_get_preview:
            
            from core.controller import ExtractionController
            
            # Mock the preview generator
            mock_preview_gen = Mock()
            mock_preview_gen.set_managers = Mock()
            mock_get_preview.return_value = mock_preview_gen
            
            # Create mock window with required attributes
            mock_window = Mock()
            mock_window.extract_requested = Mock()
            mock_window.open_in_editor_requested = Mock()
            mock_window.arrange_rows_requested = Mock()
            mock_window.arrange_grid_requested = Mock()
            mock_window.inject_requested = Mock()
            
            # Create controller
            controller = ExtractionController(mock_window)
            
            # Verify basic properties
            assert controller.main_window == mock_window
            assert controller.worker is None
    
    def test_parameter_validation_missing_vram(self):
        """Test validation when VRAM is missing"""
        with patch('core.controller.get_extraction_manager') as mock_get_ext, \
             patch('core.controller.get_injection_manager'), \
             patch('core.controller.get_session_manager'), \
             patch('core.controller.get_preview_generator') as mock_get_preview:
            
            from core.controller import ExtractionController
            
            # Mock the preview generator
            mock_preview_gen = Mock()
            mock_preview_gen.set_managers = Mock()
            mock_get_preview.return_value = mock_preview_gen
            
            # Setup mock window
            mock_window = Mock()
            mock_window.get_extraction_params = Mock(return_value={
                "vram_path": "",  # Missing VRAM
                "cgram_path": "/path/to/cgram",
                "output_base": "/path/to/output"
            })
            
            # Setup mock manager that raises validation error
            mock_manager = Mock()
            mock_manager.validate_extraction_params.side_effect = ValueError("VRAM file is required")
            mock_get_ext.return_value = mock_manager
            
            # Create controller and test
            controller = ExtractionController(mock_window)
            controller.start_extraction()
            
            # Verify failure was handled
            mock_window.extraction_failed.assert_called_once()
            assert controller.worker is None
    
    def test_parameter_validation_missing_cgram(self):
        """Test validation when CGRAM is missing in color mode"""
        with patch('core.controller.get_extraction_manager') as mock_get_ext, \
             patch('core.controller.get_injection_manager'), \
             patch('core.controller.get_session_manager'), \
             patch('core.controller.get_preview_generator') as mock_get_preview:
            
            from core.controller import ExtractionController
            
            # Mock the preview generator
            mock_preview_gen = Mock()
            mock_preview_gen.set_managers = Mock()
            mock_get_preview.return_value = mock_preview_gen
            
            # Setup mock window
            mock_window = Mock()
            mock_window.get_extraction_params = Mock(return_value={
                "vram_path": "/path/to/vram",
                "cgram_path": "",  # Missing CGRAM
                "output_base": "/path/to/output",
                "grayscale_mode": False  # Color mode requires CGRAM
            })
            
            # Setup mock manager
            mock_manager = Mock()
            mock_manager.validate_extraction_params.side_effect = ValueError(
                "CGRAM file is required for Full Color mode"
            )
            mock_get_ext.return_value = mock_manager
            
            # Create controller and test
            controller = ExtractionController(mock_window)
            controller.start_extraction()
            
            # Verify failure was handled
            mock_window.extraction_failed.assert_called_once()
    
    def test_successful_extraction_start(self):
        """Test successful extraction start"""
        with patch('core.controller.get_extraction_manager') as mock_get_ext, \
             patch('core.controller.get_injection_manager'), \
             patch('core.controller.get_session_manager'), \
             patch('core.controller.get_preview_generator') as mock_get_preview, \
             patch('core.controller.VRAMExtractionWorker') as mock_worker_class, \
             patch('core.controller.FileValidator') as mock_validator:
            
            from core.controller import ExtractionController
            
            # Mock the preview generator
            mock_preview_gen = Mock()
            mock_preview_gen.set_managers = Mock()
            mock_get_preview.return_value = mock_preview_gen
            
            # Setup mock window
            mock_window = Mock()
            params = {
                "vram_path": "/path/to/vram",
                "cgram_path": "/path/to/cgram",
                "output_base": "/path/to/output"
            }
            mock_window.get_extraction_params = Mock(return_value=params)
            
            # Setup mock manager
            mock_manager = Mock()
            mock_manager.validate_extraction_params.return_value = None  # Validation passes
            mock_get_ext.return_value = mock_manager
            
            # Setup file validator to pass
            mock_validation_result = Mock()
            mock_validation_result.is_valid = True
            mock_validation_result.warnings = []
            mock_validator.validate_vram_file.return_value = mock_validation_result
            mock_validator.validate_cgram_file.return_value = mock_validation_result
            
            # Setup mock worker with signals
            mock_worker = Mock()
            mock_worker.progress = Mock()
            mock_worker.preview_ready = Mock()
            mock_worker.preview_image_ready = Mock()
            mock_worker.palettes_ready = Mock()
            mock_worker.active_palettes_ready = Mock()
            mock_worker.extraction_finished = Mock()
            mock_worker.error = Mock()
            mock_worker.finished = Mock()
            mock_worker_class.return_value = mock_worker
            
            # Create controller and start extraction
            controller = ExtractionController(mock_window)
            controller.start_extraction()
            
            # Verify worker was created and started
            # The worker is created with extraction_params (subset of params)
            assert mock_worker_class.called
            call_args = mock_worker_class.call_args[0][0]
            assert call_args['vram_path'] == params['vram_path']
            assert call_args['output_base'] == params['output_base']
            mock_worker.start.assert_called_once()
            assert controller.worker == mock_worker
    
    def test_open_in_editor_functionality(self):
        """Test opening files in editor"""
        with patch('core.controller.get_extraction_manager'), \
             patch('core.controller.get_injection_manager'), \
             patch('core.controller.get_session_manager'), \
             patch('core.controller.get_preview_generator') as mock_get_preview, \
             patch('core.controller.subprocess.Popen') as mock_popen, \
             patch('core.controller.Path.exists', return_value=True), \
             patch('core.controller.FileValidator.validate_image_file') as mock_validate:
            
            from core.controller import ExtractionController
            
            # Mock the preview generator
            mock_preview_gen = Mock()
            mock_preview_gen.set_managers = Mock()
            mock_get_preview.return_value = mock_preview_gen
            
            # Mock file validation to pass
            validation_result = Mock()
            validation_result.is_valid = True
            mock_validate.return_value = validation_result
            
            # Setup mock window
            mock_window = Mock()
            mock_window._extracted_files = ["/path/to/file1.png", "/path/to/file2.png"]
            mock_window.status_bar = Mock()
            mock_window.status_bar.showMessage = Mock()
            
            # Create controller
            controller = ExtractionController(mock_window)
            controller.open_in_editor("/path/to/sprite.png")
            
            # Verify subprocess was called to open files
            assert mock_popen.called
    
    def test_worker_signal_connections(self):
        """Test worker signal connections are set up"""
        with patch('core.controller.get_extraction_manager') as mock_get_ext, \
             patch('core.controller.get_injection_manager'), \
             patch('core.controller.get_session_manager'), \
             patch('core.controller.get_preview_generator') as mock_get_preview, \
             patch('core.controller.FileValidator') as mock_validator, \
             patch('core.controller.VRAMExtractionWorker') as mock_worker_class:
            
            from core.controller import ExtractionController
            
            # Mock the preview generator
            mock_preview_gen = Mock()
            mock_preview_gen.set_managers = Mock()
            mock_get_preview.return_value = mock_preview_gen
            
            # Setup mock extraction manager that passes validation
            mock_manager = Mock()
            mock_manager.validate_extraction_params.return_value = None  # Validation passes
            mock_get_ext.return_value = mock_manager
            
            # Mock file validators to pass validation
            valid_result = Mock()
            valid_result.is_valid = True
            valid_result.warnings = []
            mock_validator.validate_vram_file.return_value = valid_result
            mock_validator.validate_cgram_file.return_value = valid_result
            mock_validator.validate_oam_file.return_value = valid_result
            
            # Setup mock window
            mock_window = Mock()
            mock_window.get_extraction_params = Mock(return_value={
                "vram_path": "/path/to/vram",
                "cgram_path": "/path/to/cgram",
                "output_base": "/path/to/output"
            })
            
            # Setup mock worker with signals
            mock_worker = Mock()
            mock_worker.progress = Mock()
            mock_worker.preview_ready = Mock()
            mock_worker.preview_image_ready = Mock()
            mock_worker.palettes_ready = Mock()
            mock_worker.active_palettes_ready = Mock()
            mock_worker.extraction_finished = Mock()
            mock_worker.error = Mock()
            mock_worker.start = Mock()  # Mock the start method
            mock_worker_class.return_value = mock_worker
            
            # Create controller and start extraction
            controller = ExtractionController(mock_window)
            controller.start_extraction()
            
            # Verify signals were connected
            assert mock_worker_class.called, "VRAMExtractionWorker was not instantiated"
            assert controller.worker is not None, "Controller worker is None"
            
            # Check that all required signals were connected
            assert mock_worker.progress.connect.called
            assert mock_worker.error.connect.called
            assert mock_worker.extraction_finished.connect.called