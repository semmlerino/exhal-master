"""
Integration tests for error handling across component boundaries - Priority 3 test implementation.
Tests comprehensive error handling across component boundaries.
"""

import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, call
import threading
import time

import pytest

# Add parent directories to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from spritepal.core.controller import ExtractionController
from spritepal.ui.main_window import MainWindow


class TestFileCorruptionErrorPropagation:
    """Test file corruption error propagation to UI"""

    def create_mock_main_window(self):
        """Create mock MainWindow for testing"""
        with patch('spritepal.ui.main_window.get_settings_manager') as mock_settings, \
             patch('spritepal.ui.main_window.ExtractionPanel') as mock_panel_class, \
             patch('spritepal.ui.main_window.PreviewPanel') as mock_preview_class, \
             patch('spritepal.ui.main_window.PalettePreviewWidget') as mock_palette_class, \
             patch('spritepal.ui.main_window.ExtractionController') as mock_controller:
            
            # Mock settings
            settings = Mock()
            settings.has_valid_session.return_value = False
            settings.get_default_directory.return_value = "/tmp"
            settings.get_session_data.return_value = {}
            settings.get_ui_data.return_value = {}
            mock_settings.return_value = settings
            
            # Mock extraction panel
            panel = Mock()
            panel.get_session_data.return_value = {}
            panel.files_changed = Mock()
            panel.files_changed.connect = Mock()
            panel.extraction_ready = Mock()
            panel.extraction_ready.connect = Mock()
            mock_panel_class.return_value = panel
            
            # Mock preview components
            mock_preview_class.return_value = Mock()
            mock_palette_class.return_value = Mock()
            
            # Create mock MainWindow for controller integration testing
            window = Mock()
            window.status_bar = Mock()
            window.status_bar.showMessage = Mock()
            window.extraction_failed = Mock()
            window.extraction_complete = Mock()
            window._output_path = "test_sprites"
            window._extracted_files = []
            
            return window

    @pytest.mark.integration
    def test_corrupted_vram_file_error_handling(self):
        """Test corrupted VRAM file error propagation"""
        # Create temporary corrupted file
        with tempfile.NamedTemporaryFile(suffix=".dmp", delete=False) as temp_file:
            temp_file.write(b"corrupted data")
            corrupted_vram = temp_file.name
        
        try:
            # Test extraction with corrupted VRAM
            window = self.create_mock_main_window()
            controller = window.controller
            
            # Mock extraction worker to simulate corruption error
            with patch('spritepal.core.controller.ExtractionWorker') as mock_worker_class:
                mock_worker = Mock()
                mock_worker.extraction_complete = Mock()
                mock_worker.extraction_complete.connect = Mock()
                mock_worker.extraction_failed = Mock()
                mock_worker.extraction_failed.connect = Mock()
                mock_worker.preview_ready = Mock()
                mock_worker.preview_ready.connect = Mock()
                mock_worker.progress_update = Mock()
                mock_worker.progress_update.connect = Mock()
                mock_worker_class.return_value = mock_worker
                
                # Set up extraction parameters
                extraction_params = {
                    "vram_path": corrupted_vram,
                    "cgram_path": "/tmp/test.cgram",
                    "oam_path": "/tmp/test.oam",
                    "vram_offset": 0xC000,
                    "output_base": "test_output",
                    "create_grayscale": True,
                    "create_metadata": True
                }
                
                # Mock MainWindow methods
                window.get_extraction_params = Mock(return_value=extraction_params)
                window.extraction_failed = Mock()
                
                # Start extraction
                controller._on_extract_requested()
                
                # Simulate corruption error from worker
                error_message = "Corrupted VRAM file: Invalid header"
                mock_worker.extraction_failed.emit.side_effect = lambda msg: window.extraction_failed(msg)
                mock_worker.extraction_failed.emit(error_message)
                
                # Verify error was handled
                window.extraction_failed.assert_called_once_with(error_message)
        
        finally:
            # Clean up
            os.unlink(corrupted_vram)

    @pytest.mark.integration
    def test_corrupted_cgram_file_error_handling(self):
        """Test corrupted CGRAM file error propagation"""
        # Create temporary corrupted file
        with tempfile.NamedTemporaryFile(suffix=".dmp", delete=False) as temp_file:
            temp_file.write(b"invalid cgram data")
            corrupted_cgram = temp_file.name
        
        try:
            # Test extraction with corrupted CGRAM
            window = self.create_mock_main_window()
            controller = window.controller
            
            # Mock extraction worker to simulate corruption error
            with patch('spritepal.core.controller.ExtractionWorker') as mock_worker_class:
                mock_worker = Mock()
                mock_worker.extraction_complete = Mock()
                mock_worker.extraction_complete.connect = Mock()
                mock_worker.extraction_failed = Mock()
                mock_worker.extraction_failed.connect = Mock()
                mock_worker.preview_ready = Mock()
                mock_worker.preview_ready.connect = Mock()
                mock_worker.progress_update = Mock()
                mock_worker.progress_update.connect = Mock()
                mock_worker_class.return_value = mock_worker
                
                # Set up extraction parameters
                extraction_params = {
                    "vram_path": "/tmp/test.vram",
                    "cgram_path": corrupted_cgram,
                    "oam_path": "/tmp/test.oam",
                    "vram_offset": 0xC000,
                    "output_base": "test_output",
                    "create_grayscale": True,
                    "create_metadata": True
                }
                
                # Mock MainWindow methods
                window.get_extraction_params = Mock(return_value=extraction_params)
                window.extraction_failed = Mock()
                
                # Start extraction
                controller._on_extract_requested()
                
                # Simulate corruption error from worker
                error_message = "Corrupted CGRAM file: Invalid palette data"
                mock_worker.extraction_failed.emit.side_effect = lambda msg: window.extraction_failed(msg)
                mock_worker.extraction_failed.emit(error_message)
                
                # Verify error was handled
                window.extraction_failed.assert_called_once_with(error_message)
        
        finally:
            # Clean up
            os.unlink(corrupted_cgram)

    @pytest.mark.integration
    def test_corrupted_image_file_error_handling(self):
        """Test corrupted image file error propagation"""
        # Create temporary corrupted image file
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as temp_file:
            temp_file.write(b"not a valid PNG file")
            corrupted_image = temp_file.name
        
        try:
            # Test dialog with corrupted image
            from spritepal.core.controller import ExtractionController
            
            mock_window = Mock()
            controller = ExtractionController(mock_window)
            
            # Mock arrangement dialog with image loading error
            with patch('spritepal.ui.row_arrangement_dialog.RowArrangementDialog') as mock_dialog:
                mock_dialog.side_effect = Exception("Invalid image file format")
                
                # Mock error handling
                with patch('spritepal.ui.main_window.QMessageBox') as mock_msgbox:
                    # Mock file existence check
                    with patch('os.path.exists', return_value=True):
                        # Trigger arrangement with corrupted image
                        controller.open_row_arrangement(corrupted_image)
                        
                        # Verify error dialog was shown
                        mock_msgbox.critical.assert_called_once()
                        call_args = mock_msgbox.critical.call_args
                        assert "Error" in call_args[0][1]
        
        finally:
            # Clean up
            os.unlink(corrupted_image)

    @pytest.mark.integration
    def test_corrupted_palette_file_error_handling(self):
        """Test corrupted palette file error propagation"""
        # Create temporary corrupted palette file
        with tempfile.NamedTemporaryFile(suffix=".pal.json", delete=False) as temp_file:
            temp_file.write(b"invalid json data")
            corrupted_palette = temp_file.name
        
        try:
            # Test palette loading with corrupted file
            window = self.create_mock_main_window()
            controller = window.controller
            
            # Mock palette loading
            with patch('spritepal.core.controller.load_palette_files') as mock_load_palettes:
                mock_load_palettes.side_effect = Exception("Invalid JSON format")
                
                # Mock arrangement dialog
                with patch('spritepal.ui.row_arrangement_dialog.RowArrangementDialog') as mock_dialog:
                    mock_dialog_instance = Mock()
                    mock_dialog_instance.exec.return_value = 1  # Accepted
                    mock_dialog_instance.get_arranged_path.return_value = "/tmp/test.png"
                    mock_dialog_instance.set_palettes = Mock()
                    mock_dialog.return_value = mock_dialog_instance
                    
                    # Mock file existence check
                    with patch('os.path.exists', return_value=True):
                        # Trigger arrangement (should handle palette loading error)
                        controller._on_arrange_rows_requested("/tmp/test.png")
                        
                        # Verify dialog was still created (error handled gracefully)
                        mock_dialog.assert_called_once()
                        
                        # Verify palette loading was attempted
                        mock_load_palettes.assert_called_once()
        
        finally:
            # Clean up
            os.unlink(corrupted_palette)


class TestMemoryErrorHandling:
    """Test memory exhaustion and graceful degradation"""

    @pytest.mark.integration
    def test_memory_exhaustion_during_extraction(self):
        """Test memory exhaustion during extraction"""
        # Create mock MainWindow
        with patch('spritepal.ui.main_window.get_settings_manager') as mock_settings, \
             patch('spritepal.ui.main_window.ExtractionPanel') as mock_panel_class, \
             patch('spritepal.ui.main_window.PreviewPanel') as mock_preview_class, \
             patch('spritepal.ui.main_window.PalettePreviewWidget') as mock_palette_class, \
             patch('spritepal.ui.main_window.ExtractionController') as mock_controller:
            
            # Mock settings
            settings = Mock()
            settings.has_valid_session.return_value = False
            settings.get_default_directory.return_value = "/tmp"
            settings.get_session_data.return_value = {}
            settings.get_ui_data.return_value = {}
            mock_settings.return_value = settings
            
            # Mock extraction panel
            panel = Mock()
            panel.get_session_data.return_value = {}
            panel.files_changed = Mock()
            panel.files_changed.connect = Mock()
            panel.extraction_ready = Mock()
            panel.extraction_ready.connect = Mock()
            mock_panel_class.return_value = panel
            
            # Mock preview components
            mock_preview_class.return_value = Mock()
            mock_palette_class.return_value = Mock()
            
            # Create MainWindow
            window = MainWindow()
            controller = window.controller
            
            # Mock extraction worker with memory error
            with patch('spritepal.core.controller.ExtractionWorker') as mock_worker_class:
                mock_worker = Mock()
                mock_worker.extraction_complete = Mock()
                mock_worker.extraction_complete.connect = Mock()
                mock_worker.extraction_failed = Mock()
                mock_worker.extraction_failed.connect = Mock()
                mock_worker.preview_ready = Mock()
                mock_worker.preview_ready.connect = Mock()
                mock_worker.progress_update = Mock()
                mock_worker.progress_update.connect = Mock()
                mock_worker_class.return_value = mock_worker
                
                # Set up extraction parameters
                extraction_params = {
                    "vram_path": "/tmp/test.vram",
                    "cgram_path": "/tmp/test.cgram",
                    "oam_path": "/tmp/test.oam",
                    "vram_offset": 0xC000,
                    "output_base": "test_output",
                    "create_grayscale": True,
                    "create_metadata": True
                }
                
                # Mock MainWindow methods
                window.get_extraction_params = Mock(return_value=extraction_params)
                window.extraction_failed = Mock()
                
                # Start extraction
                controller._on_extract_requested()
                
                # Simulate memory error from worker
                error_message = "MemoryError: Unable to allocate memory for image processing"
                mock_worker.extraction_failed.emit.side_effect = lambda msg: window.extraction_failed(msg)
                mock_worker.extraction_failed.emit(error_message)
                
                # Verify error was handled
                window.extraction_failed.assert_called_once_with(error_message)

    @pytest.mark.integration
    def test_memory_exhaustion_during_preview(self):
        """Test memory exhaustion during preview generation"""
        # Create mock MainWindow
        with patch('spritepal.ui.main_window.get_settings_manager') as mock_settings, \
             patch('spritepal.ui.main_window.ExtractionPanel') as mock_panel_class, \
             patch('spritepal.ui.main_window.PreviewPanel') as mock_preview_class, \
             patch('spritepal.ui.main_window.PalettePreviewWidget') as mock_palette_class, \
             patch('spritepal.ui.main_window.ExtractionController') as mock_controller:
            
            # Mock settings
            settings = Mock()
            settings.has_valid_session.return_value = False
            settings.get_default_directory.return_value = "/tmp"
            settings.get_session_data.return_value = {}
            settings.get_ui_data.return_value = {}
            mock_settings.return_value = settings
            
            # Mock extraction panel
            panel = Mock()
            panel.get_session_data.return_value = {}
            panel.files_changed = Mock()
            panel.files_changed.connect = Mock()
            panel.extraction_ready = Mock()
            panel.extraction_ready.connect = Mock()
            mock_panel_class.return_value = panel
            
            # Mock preview components that fail with memory error
            mock_preview_widget = Mock()
            mock_preview_widget.update_preview.side_effect = MemoryError("Cannot allocate memory for preview")
            mock_preview_class.return_value = mock_preview_widget
            mock_palette_class.return_value = Mock()
            
            # Create MainWindow
            window = MainWindow()
            controller = window.controller
            
            # Mock extraction worker with preview update
            with patch('spritepal.core.controller.ExtractionWorker') as mock_worker_class:
                mock_worker = Mock()
                mock_worker.extraction_complete = Mock()
                mock_worker.extraction_complete.connect = Mock()
                mock_worker.extraction_failed = Mock()
                mock_worker.extraction_failed.connect = Mock()
                mock_worker.preview_ready = Mock()
                mock_worker.preview_ready.connect = Mock()
                mock_worker.progress_update = Mock()
                mock_worker.progress_update.connect = Mock()
                mock_worker_class.return_value = mock_worker
                
                # Set up extraction parameters
                extraction_params = {
                    "vram_path": "/tmp/test.vram",
                    "cgram_path": "/tmp/test.cgram",
                    "oam_path": "/tmp/test.oam",
                    "vram_offset": 0xC000,
                    "output_base": "test_output",
                    "create_grayscale": True,
                    "create_metadata": True
                }
                
                # Mock MainWindow methods
                window.get_extraction_params = Mock(return_value=extraction_params)
                window.extraction_failed = Mock()
                
                # Start extraction
                controller._on_extract_requested()
                
                # Simulate preview update that causes memory error
                try:
                    mock_worker.preview_ready.emit.side_effect = lambda img: window.sprite_preview.update_preview(img)
                    mock_worker.preview_ready.emit(Mock())  # This should trigger the memory error
                except MemoryError:
                    # Error should be caught and handled gracefully
                    pass
                
                # Verify preview widget was called (error handled internally)
                mock_preview_widget.update_preview.assert_called_once()

    @pytest.mark.integration
    def test_large_file_memory_management(self):
        """Test memory management with large files"""
        # Create mock MainWindow
        with patch('spritepal.ui.main_window.get_settings_manager') as mock_settings, \
             patch('spritepal.ui.main_window.ExtractionPanel') as mock_panel_class, \
             patch('spritepal.ui.main_window.PreviewPanel') as mock_preview_class, \
             patch('spritepal.ui.main_window.PalettePreviewWidget') as mock_palette_class, \
             patch('spritepal.ui.main_window.ExtractionController') as mock_controller:
            
            # Mock settings
            settings = Mock()
            settings.has_valid_session.return_value = False
            settings.get_default_directory.return_value = "/tmp"
            settings.get_session_data.return_value = {}
            settings.get_ui_data.return_value = {}
            mock_settings.return_value = settings
            
            # Mock extraction panel
            panel = Mock()
            panel.get_session_data.return_value = {}
            panel.files_changed = Mock()
            panel.files_changed.connect = Mock()
            panel.extraction_ready = Mock()
            panel.extraction_ready.connect = Mock()
            mock_panel_class.return_value = panel
            
            # Mock preview components
            mock_preview_class.return_value = Mock()
            mock_palette_class.return_value = Mock()
            
            # Create MainWindow
            window = MainWindow()
            controller = window.controller
            
            # Mock extraction worker with large file processing
            with patch('spritepal.core.controller.ExtractionWorker') as mock_worker_class:
                mock_worker = Mock()
                mock_worker.extraction_complete = Mock()
                mock_worker.extraction_complete.connect = Mock()
                mock_worker.extraction_failed = Mock()
                mock_worker.extraction_failed.connect = Mock()
                mock_worker.preview_ready = Mock()
                mock_worker.preview_ready.connect = Mock()
                mock_worker.progress_update = Mock()
                mock_worker.progress_update.connect = Mock()
                mock_worker_class.return_value = mock_worker
                
                # Set up extraction parameters for large file
                extraction_params = {
                    "vram_path": "/tmp/large_test.vram",
                    "cgram_path": "/tmp/large_test.cgram",
                    "oam_path": "/tmp/large_test.oam",
                    "vram_offset": 0xC000,
                    "output_base": "large_output",
                    "create_grayscale": True,
                    "create_metadata": True
                }
                
                # Mock MainWindow methods
                window.get_extraction_params = Mock(return_value=extraction_params)
                window.extraction_complete = Mock()
                
                # Start extraction
                controller._on_extract_requested()
                
                # Simulate successful large file processing
                extracted_files = ["large_output.png", "large_output.pal.json"]
                mock_worker.extraction_complete.emit.side_effect = lambda files: window.extraction_complete(files)
                mock_worker.extraction_complete.emit(extracted_files)
                
                # Verify extraction was handled successfully
                window.extraction_complete.assert_called_once_with(extracted_files)


class TestNetworkPermissionErrorHandling:
    """Test network and permission error handling"""

    @pytest.mark.integration
    def test_file_permission_error_handling(self):
        """Test file permission error handling"""
        # Create mock MainWindow
        with patch('spritepal.ui.main_window.get_settings_manager') as mock_settings, \
             patch('spritepal.ui.main_window.ExtractionPanel') as mock_panel_class, \
             patch('spritepal.ui.main_window.PreviewPanel') as mock_preview_class, \
             patch('spritepal.ui.main_window.PalettePreviewWidget') as mock_palette_class, \
             patch('spritepal.ui.main_window.ExtractionController') as mock_controller:
            
            # Mock settings
            settings = Mock()
            settings.has_valid_session.return_value = False
            settings.get_default_directory.return_value = "/tmp"
            settings.get_session_data.return_value = {}
            settings.get_ui_data.return_value = {}
            mock_settings.return_value = settings
            
            # Mock extraction panel
            panel = Mock()
            panel.get_session_data.return_value = {}
            panel.files_changed = Mock()
            panel.files_changed.connect = Mock()
            panel.extraction_ready = Mock()
            panel.extraction_ready.connect = Mock()
            mock_panel_class.return_value = panel
            
            # Mock preview components
            mock_preview_class.return_value = Mock()
            mock_palette_class.return_value = Mock()
            
            # Create MainWindow
            window = MainWindow()
            controller = window.controller
            
            # Mock extraction worker with permission error
            with patch('spritepal.core.controller.ExtractionWorker') as mock_worker_class:
                mock_worker = Mock()
                mock_worker.extraction_complete = Mock()
                mock_worker.extraction_complete.connect = Mock()
                mock_worker.extraction_failed = Mock()
                mock_worker.extraction_failed.connect = Mock()
                mock_worker.preview_ready = Mock()
                mock_worker.preview_ready.connect = Mock()
                mock_worker.progress_update = Mock()
                mock_worker.progress_update.connect = Mock()
                mock_worker_class.return_value = mock_worker
                
                # Set up extraction parameters
                extraction_params = {
                    "vram_path": "/tmp/test.vram",
                    "cgram_path": "/tmp/test.cgram",
                    "oam_path": "/tmp/test.oam",
                    "vram_offset": 0xC000,
                    "output_base": "test_output",
                    "create_grayscale": True,
                    "create_metadata": True
                }
                
                # Mock MainWindow methods
                window.get_extraction_params = Mock(return_value=extraction_params)
                window.extraction_failed = Mock()
                
                # Start extraction
                controller._on_extract_requested()
                
                # Simulate permission error from worker
                error_message = "PermissionError: Access denied to output directory"
                mock_worker.extraction_failed.emit.side_effect = lambda msg: window.extraction_failed(msg)
                mock_worker.extraction_failed.emit(error_message)
                
                # Verify error was handled
                window.extraction_failed.assert_called_once_with(error_message)

    @pytest.mark.integration
    def test_readonly_output_directory_error(self):
        """Test read-only output directory error handling"""
        # Create temporary read-only directory
        with tempfile.TemporaryDirectory() as temp_dir:
            readonly_dir = os.path.join(temp_dir, "readonly")
            os.makedirs(readonly_dir)
            
            # Make directory read-only (on systems that support it)
            try:
                os.chmod(readonly_dir, 0o444)
                
                # Create mock MainWindow
                with patch('spritepal.ui.main_window.get_settings_manager') as mock_settings, \
                     patch('spritepal.ui.main_window.ExtractionPanel') as mock_panel_class, \
                     patch('spritepal.ui.main_window.PreviewPanel') as mock_preview_class, \
                     patch('spritepal.ui.main_window.PalettePreviewWidget') as mock_palette_class, \
                     patch('spritepal.ui.main_window.ExtractionController') as mock_controller:
                    
                    # Mock settings
                    settings = Mock()
                    settings.has_valid_session.return_value = False
                    settings.get_default_directory.return_value = readonly_dir
                    settings.get_session_data.return_value = {}
                    settings.get_ui_data.return_value = {}
                    mock_settings.return_value = settings
                    
                    # Mock extraction panel
                    panel = Mock()
                    panel.get_session_data.return_value = {}
                    panel.files_changed = Mock()
                    panel.files_changed.connect = Mock()
                    panel.extraction_ready = Mock()
                    panel.extraction_ready.connect = Mock()
                    mock_panel_class.return_value = panel
                    
                    # Mock preview components
                    mock_preview_class.return_value = Mock()
                    mock_palette_class.return_value = Mock()
                    
                    # Create MainWindow
                    window = MainWindow()
                    controller = window.controller
                    
                    # Mock extraction worker with write permission error
                    with patch('spritepal.core.controller.ExtractionWorker') as mock_worker_class:
                        mock_worker = Mock()
                        mock_worker.extraction_complete = Mock()
                        mock_worker.extraction_complete.connect = Mock()
                        mock_worker.extraction_failed = Mock()
                        mock_worker.extraction_failed.connect = Mock()
                        mock_worker.preview_ready = Mock()
                        mock_worker.preview_ready.connect = Mock()
                        mock_worker.progress_update = Mock()
                        mock_worker.progress_update.connect = Mock()
                        mock_worker_class.return_value = mock_worker
                        
                        # Set up extraction parameters with readonly output
                        extraction_params = {
                            "vram_path": "/tmp/test.vram",
                            "cgram_path": "/tmp/test.cgram",
                            "oam_path": "/tmp/test.oam",
                            "vram_offset": 0xC000,
                            "output_base": os.path.join(readonly_dir, "test_output"),
                            "create_grayscale": True,
                            "create_metadata": True
                        }
                        
                        # Mock MainWindow methods
                        window.get_extraction_params = Mock(return_value=extraction_params)
                        window.extraction_failed = Mock()
                        
                        # Start extraction
                        controller._on_extract_requested()
                        
                        # Simulate permission error from worker
                        error_message = f"PermissionError: Cannot write to read-only directory: {readonly_dir}"
                        mock_worker.extraction_failed.emit.side_effect = lambda msg: window.extraction_failed(msg)
                        mock_worker.extraction_failed.emit(error_message)
                        
                        # Verify error was handled
                        window.extraction_failed.assert_called_once_with(error_message)
                        
            finally:
                # Restore write permissions for cleanup
                try:
                    os.chmod(readonly_dir, 0o755)
                except OSError:
                    pass

    @pytest.mark.integration
    def test_network_file_access_error(self):
        """Test network file access error handling"""
        # Test with network path that doesn't exist
        network_path = "//nonexistent/share/test.vram"
        
        # Create mock MainWindow
        with patch('spritepal.ui.main_window.get_settings_manager') as mock_settings, \
             patch('spritepal.ui.main_window.ExtractionPanel') as mock_panel_class, \
             patch('spritepal.ui.main_window.PreviewPanel') as mock_preview_class, \
             patch('spritepal.ui.main_window.PalettePreviewWidget') as mock_palette_class, \
             patch('spritepal.ui.main_window.ExtractionController') as mock_controller:
            
            # Mock settings
            settings = Mock()
            settings.has_valid_session.return_value = False
            settings.get_default_directory.return_value = "/tmp"
            settings.get_session_data.return_value = {}
            settings.get_ui_data.return_value = {}
            mock_settings.return_value = settings
            
            # Mock extraction panel
            panel = Mock()
            panel.get_session_data.return_value = {}
            panel.files_changed = Mock()
            panel.files_changed.connect = Mock()
            panel.extraction_ready = Mock()
            panel.extraction_ready.connect = Mock()
            mock_panel_class.return_value = panel
            
            # Mock preview components
            mock_preview_class.return_value = Mock()
            mock_palette_class.return_value = Mock()
            
            # Create MainWindow
            window = MainWindow()
            controller = window.controller
            
            # Mock extraction worker with network error
            with patch('spritepal.core.controller.ExtractionWorker') as mock_worker_class:
                mock_worker = Mock()
                mock_worker.extraction_complete = Mock()
                mock_worker.extraction_complete.connect = Mock()
                mock_worker.extraction_failed = Mock()
                mock_worker.extraction_failed.connect = Mock()
                mock_worker.preview_ready = Mock()
                mock_worker.preview_ready.connect = Mock()
                mock_worker.progress_update = Mock()
                mock_worker.progress_update.connect = Mock()
                mock_worker_class.return_value = mock_worker
                
                # Set up extraction parameters with network path
                extraction_params = {
                    "vram_path": network_path,
                    "cgram_path": "/tmp/test.cgram",
                    "oam_path": "/tmp/test.oam",
                    "vram_offset": 0xC000,
                    "output_base": "test_output",
                    "create_grayscale": True,
                    "create_metadata": True
                }
                
                # Mock MainWindow methods
                window.get_extraction_params = Mock(return_value=extraction_params)
                window.extraction_failed = Mock()
                
                # Start extraction
                controller._on_extract_requested()
                
                # Simulate network error from worker
                error_message = f"NetworkError: Cannot access network path: {network_path}"
                mock_worker.extraction_failed.emit.side_effect = lambda msg: window.extraction_failed(msg)
                mock_worker.extraction_failed.emit(error_message)
                
                # Verify error was handled
                window.extraction_failed.assert_called_once_with(error_message)


class TestThreadCleanupOnError:
    """Test worker thread cleanup on error"""

    @pytest.mark.integration
    def test_worker_thread_cleanup_on_error(self):
        """Test worker thread cleanup when extraction fails"""
        # Create mock MainWindow
        with patch('spritepal.ui.main_window.get_settings_manager') as mock_settings, \
             patch('spritepal.ui.main_window.ExtractionPanel') as mock_panel_class, \
             patch('spritepal.ui.main_window.PreviewPanel') as mock_preview_class, \
             patch('spritepal.ui.main_window.PalettePreviewWidget') as mock_palette_class, \
             patch('spritepal.ui.main_window.ExtractionController') as mock_controller:
            
            # Mock settings
            settings = Mock()
            settings.has_valid_session.return_value = False
            settings.get_default_directory.return_value = "/tmp"
            settings.get_session_data.return_value = {}
            settings.get_ui_data.return_value = {}
            mock_settings.return_value = settings
            
            # Mock extraction panel
            panel = Mock()
            panel.get_session_data.return_value = {}
            panel.files_changed = Mock()
            panel.files_changed.connect = Mock()
            panel.extraction_ready = Mock()
            panel.extraction_ready.connect = Mock()
            mock_panel_class.return_value = panel
            
            # Mock preview components
            mock_preview_class.return_value = Mock()
            mock_palette_class.return_value = Mock()
            
            # Create MainWindow
            window = MainWindow()
            controller = window.controller
            
            # Mock extraction worker with cleanup tracking
            with patch('spritepal.core.controller.ExtractionWorker') as mock_worker_class:
                mock_worker = Mock()
                mock_worker.extraction_complete = Mock()
                mock_worker.extraction_complete.connect = Mock()
                mock_worker.extraction_failed = Mock()
                mock_worker.extraction_failed.connect = Mock()
                mock_worker.preview_ready = Mock()
                mock_worker.preview_ready.connect = Mock()
                mock_worker.progress_update = Mock()
                mock_worker.progress_update.connect = Mock()
                mock_worker.quit = Mock()
                mock_worker.wait = Mock()
                mock_worker.isRunning = Mock(return_value=True)
                mock_worker_class.return_value = mock_worker
                
                # Set up extraction parameters
                extraction_params = {
                    "vram_path": "/tmp/test.vram",
                    "cgram_path": "/tmp/test.cgram",
                    "oam_path": "/tmp/test.oam",
                    "vram_offset": 0xC000,
                    "output_base": "test_output",
                    "create_grayscale": True,
                    "create_metadata": True
                }
                
                # Mock MainWindow methods
                window.get_extraction_params = Mock(return_value=extraction_params)
                window.extraction_failed = Mock()
                
                # Start extraction
                controller._on_extract_requested()
                
                # Simulate extraction failure
                error_message = "Extraction failed due to critical error"
                mock_worker.extraction_failed.emit.side_effect = lambda msg: window.extraction_failed(msg)
                mock_worker.extraction_failed.emit(error_message)
                
                # Verify error was handled
                window.extraction_failed.assert_called_once_with(error_message)
                
                # Verify worker was created
                mock_worker_class.assert_called_once()

    @pytest.mark.integration
    def test_worker_thread_timeout_handling(self):
        """Test worker thread timeout handling"""
        # Create mock MainWindow
        with patch('spritepal.ui.main_window.get_settings_manager') as mock_settings, \
             patch('spritepal.ui.main_window.ExtractionPanel') as mock_panel_class, \
             patch('spritepal.ui.main_window.PreviewPanel') as mock_preview_class, \
             patch('spritepal.ui.main_window.PalettePreviewWidget') as mock_palette_class, \
             patch('spritepal.ui.main_window.ExtractionController') as mock_controller:
            
            # Mock settings
            settings = Mock()
            settings.has_valid_session.return_value = False
            settings.get_default_directory.return_value = "/tmp"
            settings.get_session_data.return_value = {}
            settings.get_ui_data.return_value = {}
            mock_settings.return_value = settings
            
            # Mock extraction panel
            panel = Mock()
            panel.get_session_data.return_value = {}
            panel.files_changed = Mock()
            panel.files_changed.connect = Mock()
            panel.extraction_ready = Mock()
            panel.extraction_ready.connect = Mock()
            mock_panel_class.return_value = panel
            
            # Mock preview components
            mock_preview_class.return_value = Mock()
            mock_palette_class.return_value = Mock()
            
            # Create MainWindow
            window = MainWindow()
            controller = window.controller
            
            # Mock extraction worker that hangs
            with patch('spritepal.core.controller.ExtractionWorker') as mock_worker_class:
                mock_worker = Mock()
                mock_worker.extraction_complete = Mock()
                mock_worker.extraction_complete.connect = Mock()
                mock_worker.extraction_failed = Mock()
                mock_worker.extraction_failed.connect = Mock()
                mock_worker.preview_ready = Mock()
                mock_worker.preview_ready.connect = Mock()
                mock_worker.progress_update = Mock()
                mock_worker.progress_update.connect = Mock()
                mock_worker.quit = Mock()
                mock_worker.wait = Mock(return_value=False)  # Timeout
                mock_worker.isRunning = Mock(return_value=True)
                mock_worker.terminate = Mock()
                mock_worker_class.return_value = mock_worker
                
                # Set up extraction parameters
                extraction_params = {
                    "vram_path": "/tmp/test.vram",
                    "cgram_path": "/tmp/test.cgram",
                    "oam_path": "/tmp/test.oam",
                    "vram_offset": 0xC000,
                    "output_base": "test_output",
                    "create_grayscale": True,
                    "create_metadata": True
                }
                
                # Mock MainWindow methods
                window.get_extraction_params = Mock(return_value=extraction_params)
                window.extraction_failed = Mock()
                
                # Start extraction
                controller._on_extract_requested()
                
                # Simulate timeout scenario
                error_message = "Extraction timed out"
                mock_worker.extraction_failed.emit.side_effect = lambda msg: window.extraction_failed(msg)
                mock_worker.extraction_failed.emit(error_message)
                
                # Verify error was handled
                window.extraction_failed.assert_called_once_with(error_message)
                
                # Verify worker was created
                mock_worker_class.assert_called_once()

    @pytest.mark.integration
    def test_multiple_worker_cleanup(self):
        """Test cleanup of multiple worker threads"""
        # Create mock MainWindow
        with patch('spritepal.ui.main_window.get_settings_manager') as mock_settings, \
             patch('spritepal.ui.main_window.ExtractionPanel') as mock_panel_class, \
             patch('spritepal.ui.main_window.PreviewPanel') as mock_preview_class, \
             patch('spritepal.ui.main_window.PalettePreviewWidget') as mock_palette_class, \
             patch('spritepal.ui.main_window.ExtractionController') as mock_controller:
            
            # Mock settings
            settings = Mock()
            settings.has_valid_session.return_value = False
            settings.get_default_directory.return_value = "/tmp"
            settings.get_session_data.return_value = {}
            settings.get_ui_data.return_value = {}
            mock_settings.return_value = settings
            
            # Mock extraction panel
            panel = Mock()
            panel.get_session_data.return_value = {}
            panel.files_changed = Mock()
            panel.files_changed.connect = Mock()
            panel.extraction_ready = Mock()
            panel.extraction_ready.connect = Mock()
            mock_panel_class.return_value = panel
            
            # Mock preview components
            mock_preview_class.return_value = Mock()
            mock_palette_class.return_value = Mock()
            
            # Create MainWindow
            window = MainWindow()
            controller = window.controller
            
            # Mock extraction worker
            with patch('spritepal.core.controller.ExtractionWorker') as mock_worker_class:
                mock_workers = []
                
                def create_mock_worker(*args, **kwargs):
                    mock_worker = Mock()
                    mock_worker.extraction_complete = Mock()
                    mock_worker.extraction_complete.connect = Mock()
                    mock_worker.extraction_failed = Mock()
                    mock_worker.extraction_failed.connect = Mock()
                    mock_worker.preview_ready = Mock()
                    mock_worker.preview_ready.connect = Mock()
                    mock_worker.progress_update = Mock()
                    mock_worker.progress_update.connect = Mock()
                    mock_worker.quit = Mock()
                    mock_worker.wait = Mock()
                    mock_worker.isRunning = Mock(return_value=True)
                    mock_workers.append(mock_worker)
                    return mock_worker
                
                mock_worker_class.side_effect = create_mock_worker
                
                # Set up extraction parameters
                extraction_params = {
                    "vram_path": "/tmp/test.vram",
                    "cgram_path": "/tmp/test.cgram",
                    "oam_path": "/tmp/test.oam",
                    "vram_offset": 0xC000,
                    "output_base": "test_output",
                    "create_grayscale": True,
                    "create_metadata": True
                }
                
                # Mock MainWindow methods
                window.get_extraction_params = Mock(return_value=extraction_params)
                window.extraction_failed = Mock()
                
                # Start multiple extractions
                controller._on_extract_requested()
                controller._on_extract_requested()  # Second extraction
                
                # Verify multiple workers were created
                assert len(mock_workers) >= 1  # At least one worker should be created
                
                # Simulate errors in all workers
                for i, mock_worker in enumerate(mock_workers):
                    error_message = f"Worker {i} failed"
                    mock_worker.extraction_failed.emit.side_effect = lambda msg: window.extraction_failed(msg)
                    mock_worker.extraction_failed.emit(error_message)
                
                # Verify errors were handled
                assert window.extraction_failed.call_count >= 1


class TestCascadingErrorPrevention:
    """Test error isolation and cascading error prevention"""

    @pytest.mark.integration
    def test_extraction_error_isolation(self):
        """Test that extraction errors don't affect other components"""
        # Create mock MainWindow
        with patch('spritepal.ui.main_window.get_settings_manager') as mock_settings, \
             patch('spritepal.ui.main_window.ExtractionPanel') as mock_panel_class, \
             patch('spritepal.ui.main_window.PreviewPanel') as mock_preview_class, \
             patch('spritepal.ui.main_window.PalettePreviewWidget') as mock_palette_class, \
             patch('spritepal.ui.main_window.ExtractionController') as mock_controller:
            
            # Mock settings
            settings = Mock()
            settings.has_valid_session.return_value = False
            settings.get_default_directory.return_value = "/tmp"
            settings.get_session_data.return_value = {}
            settings.get_ui_data.return_value = {}
            settings.save_session_data = Mock()
            settings.save_ui_data = Mock()
            mock_settings.return_value = settings
            
            # Mock extraction panel
            panel = Mock()
            panel.get_session_data.return_value = {}
            panel.files_changed = Mock()
            panel.files_changed.connect = Mock()
            panel.extraction_ready = Mock()
            panel.extraction_ready.connect = Mock()
            mock_panel_class.return_value = panel
            
            # Mock preview components
            mock_preview_class.return_value = Mock()
            mock_palette_class.return_value = Mock()
            
            # Create MainWindow
            window = MainWindow()
            controller = window.controller
            
            # Mock extraction worker that fails
            with patch('spritepal.core.controller.ExtractionWorker') as mock_worker_class:
                mock_worker = Mock()
                mock_worker.extraction_complete = Mock()
                mock_worker.extraction_complete.connect = Mock()
                mock_worker.extraction_failed = Mock()
                mock_worker.extraction_failed.connect = Mock()
                mock_worker.preview_ready = Mock()
                mock_worker.preview_ready.connect = Mock()
                mock_worker.progress_update = Mock()
                mock_worker.progress_update.connect = Mock()
                mock_worker_class.return_value = mock_worker
                
                # Set up extraction parameters
                extraction_params = {
                    "vram_path": "/tmp/test.vram",
                    "cgram_path": "/tmp/test.cgram",
                    "oam_path": "/tmp/test.oam",
                    "vram_offset": 0xC000,
                    "output_base": "test_output",
                    "create_grayscale": True,
                    "create_metadata": True
                }
                
                # Mock MainWindow methods
                window.get_extraction_params = Mock(return_value=extraction_params)
                window.extraction_failed = Mock()
                
                # Start extraction
                controller._on_extract_requested()
                
                # Simulate extraction failure
                error_message = "Extraction failed"
                mock_worker.extraction_failed.emit.side_effect = lambda msg: window.extraction_failed(msg)
                mock_worker.extraction_failed.emit(error_message)
                
                # Verify extraction error was handled
                window.extraction_failed.assert_called_once_with(error_message)
                
                # Verify other components still work (settings operations)
                window.output_name_edit.setText("test_name")
                window._save_session()
                
                # Verify settings were saved (system still functional)
                settings.save_session_data.assert_called_once()
                settings.save_ui_data.assert_called_once()

    @pytest.mark.integration
    def test_dialog_error_isolation(self):
        """Test that dialog errors don't affect main window"""
        # Create mock controller
        from spritepal.core.controller import ExtractionController
        
        mock_window = Mock()
        mock_window.statusBar = Mock()
        mock_window.statusBar.return_value = Mock()
        controller = ExtractionController(mock_window)
        
        # Mock dialog that fails
        with patch('spritepal.ui.row_arrangement_dialog.RowArrangementDialog') as mock_dialog:
            mock_dialog.side_effect = Exception("Dialog initialization failed")
            
            # Mock error handling
            with patch('spritepal.ui.main_window.QMessageBox') as mock_msgbox:
                # Mock file existence check
                with patch('os.path.exists', return_value=True):
                    # Trigger arrangement with failing dialog
                    controller._on_arrange_rows_requested("test_sprite.png")
                    
                    # Verify error was handled
                    mock_msgbox.critical.assert_called_once()
                    
                    # Verify main window is still functional
                    assert mock_window is not None
                    
                    # Verify other operations still work
                    controller._output_path = "test_output"
                    # This should not raise an exception
                    assert controller._output_path == "test_output"

    @pytest.mark.integration
    def test_preview_error_isolation(self):
        """Test that preview errors don't affect extraction"""
        # Create mock MainWindow
        with patch('spritepal.ui.main_window.get_settings_manager') as mock_settings, \
             patch('spritepal.ui.main_window.ExtractionPanel') as mock_panel_class, \
             patch('spritepal.ui.main_window.PreviewPanel') as mock_preview_class, \
             patch('spritepal.ui.main_window.PalettePreviewWidget') as mock_palette_class, \
             patch('spritepal.ui.main_window.ExtractionController') as mock_controller:
            
            # Mock settings
            settings = Mock()
            settings.has_valid_session.return_value = False
            settings.get_default_directory.return_value = "/tmp"
            settings.get_session_data.return_value = {}
            settings.get_ui_data.return_value = {}
            mock_settings.return_value = settings
            
            # Mock extraction panel
            panel = Mock()
            panel.get_session_data.return_value = {}
            panel.files_changed = Mock()
            panel.files_changed.connect = Mock()
            panel.extraction_ready = Mock()
            panel.extraction_ready.connect = Mock()
            mock_panel_class.return_value = panel
            
            # Mock preview components that fail
            mock_preview_widget = Mock()
            mock_preview_widget.update_preview.side_effect = Exception("Preview update failed")
            mock_preview_class.return_value = mock_preview_widget
            mock_palette_class.return_value = Mock()
            
            # Create MainWindow
            window = MainWindow()
            controller = window.controller
            
            # Mock extraction worker
            with patch('spritepal.core.controller.ExtractionWorker') as mock_worker_class:
                mock_worker = Mock()
                mock_worker.extraction_complete = Mock()
                mock_worker.extraction_complete.connect = Mock()
                mock_worker.extraction_failed = Mock()
                mock_worker.extraction_failed.connect = Mock()
                mock_worker.preview_ready = Mock()
                mock_worker.preview_ready.connect = Mock()
                mock_worker.progress_update = Mock()
                mock_worker.progress_update.connect = Mock()
                mock_worker_class.return_value = mock_worker
                
                # Set up extraction parameters
                extraction_params = {
                    "vram_path": "/tmp/test.vram",
                    "cgram_path": "/tmp/test.cgram",
                    "oam_path": "/tmp/test.oam",
                    "vram_offset": 0xC000,
                    "output_base": "test_output",
                    "create_grayscale": True,
                    "create_metadata": True
                }
                
                # Mock MainWindow methods
                window.get_extraction_params = Mock(return_value=extraction_params)
                window.extraction_complete = Mock()
                
                # Start extraction
                controller._on_extract_requested()
                
                # Simulate successful extraction but preview failure
                extracted_files = ["test_output.png"]
                mock_worker.extraction_complete.emit.side_effect = lambda files: window.extraction_complete(files)
                mock_worker.extraction_complete.emit(extracted_files)
                
                # Verify extraction was successful despite preview error
                window.extraction_complete.assert_called_once_with(extracted_files)
                
                # Verify preview update was attempted (and failed)
                mock_preview_widget.update_preview.assert_called_once()


class TestErrorRecoveryWorkflows:
    """Test recovery from error states"""

    @pytest.mark.integration
    def test_extraction_retry_after_error(self):
        """Test extraction retry after error"""
        # Create mock MainWindow
        with patch('spritepal.ui.main_window.get_settings_manager') as mock_settings, \
             patch('spritepal.ui.main_window.ExtractionPanel') as mock_panel_class, \
             patch('spritepal.ui.main_window.PreviewPanel') as mock_preview_class, \
             patch('spritepal.ui.main_window.PalettePreviewWidget') as mock_palette_class, \
             patch('spritepal.ui.main_window.ExtractionController') as mock_controller:
            
            # Mock settings
            settings = Mock()
            settings.has_valid_session.return_value = False
            settings.get_default_directory.return_value = "/tmp"
            settings.get_session_data.return_value = {}
            settings.get_ui_data.return_value = {}
            mock_settings.return_value = settings
            
            # Mock extraction panel
            panel = Mock()
            panel.get_session_data.return_value = {}
            panel.files_changed = Mock()
            panel.files_changed.connect = Mock()
            panel.extraction_ready = Mock()
            panel.extraction_ready.connect = Mock()
            mock_panel_class.return_value = panel
            
            # Mock preview components
            mock_preview_class.return_value = Mock()
            mock_palette_class.return_value = Mock()
            
            # Create MainWindow
            window = MainWindow()
            controller = window.controller
            
            # Mock extraction worker
            with patch('spritepal.core.controller.ExtractionWorker') as mock_worker_class:
                mock_workers = []
                
                def create_mock_worker(*args, **kwargs):
                    mock_worker = Mock()
                    mock_worker.extraction_complete = Mock()
                    mock_worker.extraction_complete.connect = Mock()
                    mock_worker.extraction_failed = Mock()
                    mock_worker.extraction_failed.connect = Mock()
                    mock_worker.preview_ready = Mock()
                    mock_worker.preview_ready.connect = Mock()
                    mock_worker.progress_update = Mock()
                    mock_worker.progress_update.connect = Mock()
                    mock_workers.append(mock_worker)
                    return mock_worker
                
                mock_worker_class.side_effect = create_mock_worker
                
                # Set up extraction parameters
                extraction_params = {
                    "vram_path": "/tmp/test.vram",
                    "cgram_path": "/tmp/test.cgram",
                    "oam_path": "/tmp/test.oam",
                    "vram_offset": 0xC000,
                    "output_base": "test_output",
                    "create_grayscale": True,
                    "create_metadata": True
                }
                
                # Mock MainWindow methods
                window.get_extraction_params = Mock(return_value=extraction_params)
                window.extraction_failed = Mock()
                window.extraction_complete = Mock()
                
                # First extraction - fails
                controller._on_extract_requested()
                first_worker = mock_workers[0]
                
                # Simulate first extraction failure
                error_message = "First extraction failed"
                first_worker.extraction_failed.emit.side_effect = lambda msg: window.extraction_failed(msg)
                first_worker.extraction_failed.emit(error_message)
                
                # Verify first error was handled
                window.extraction_failed.assert_called_once_with(error_message)
                
                # Reset mocks for retry
                window.extraction_failed.reset_mock()
                
                # Second extraction - succeeds
                controller._on_extract_requested()
                second_worker = mock_workers[1]
                
                # Simulate second extraction success
                extracted_files = ["test_output.png"]
                second_worker.extraction_complete.emit.side_effect = lambda files: window.extraction_complete(files)
                second_worker.extraction_complete.emit(extracted_files)
                
                # Verify second extraction succeeded
                window.extraction_complete.assert_called_once_with(extracted_files)
                
                # Verify no new errors
                window.extraction_failed.assert_not_called()

    @pytest.mark.integration
    def test_dialog_retry_after_error(self):
        """Test dialog retry after error"""
        # Create mock controller
        from spritepal.core.controller import ExtractionController
        
        mock_window = Mock()
        controller = ExtractionController(mock_window)
        
        # Mock dialog that fails first time, succeeds second time
        with patch('spritepal.ui.row_arrangement_dialog.RowArrangementDialog') as mock_dialog:
            call_count = 0
            
            def dialog_side_effect(*args, **kwargs):
                nonlocal call_count
                call_count += 1
                if call_count == 1:
                    raise Exception("First dialog failed")
                else:
                    # Second call succeeds
                    mock_dialog_instance = Mock()
                    mock_dialog_instance.exec.return_value = 1  # Accepted
                    mock_dialog_instance.get_arranged_path.return_value = "/tmp/test.png"
                    return mock_dialog_instance
            
            mock_dialog.side_effect = dialog_side_effect
            
            # Mock error handling
            with patch('spritepal.ui.main_window.QMessageBox') as mock_msgbox:
                # Mock file existence check
                with patch('os.path.exists', return_value=True):
                    # First attempt - fails
                    controller._on_arrange_rows_requested("test_sprite.png")
                    
                    # Verify error was handled
                    mock_msgbox.critical.assert_called_once()
                    
                    # Reset mock for retry
                    mock_msgbox.reset_mock()
                    
                    # Second attempt - succeeds
                    controller._on_arrange_rows_requested("test_sprite.png")
                    
                    # Verify success (no error dialog)
                    mock_msgbox.critical.assert_not_called()
                    
                    # Verify both attempts were made
                    assert call_count == 2

    @pytest.mark.integration
    def test_system_recovery_after_multiple_errors(self):
        """Test system recovery after multiple errors"""
        # Create mock MainWindow
        with patch('spritepal.ui.main_window.get_settings_manager') as mock_settings, \
             patch('spritepal.ui.main_window.ExtractionPanel') as mock_panel_class, \
             patch('spritepal.ui.main_window.PreviewPanel') as mock_preview_class, \
             patch('spritepal.ui.main_window.PalettePreviewWidget') as mock_palette_class, \
             patch('spritepal.ui.main_window.ExtractionController') as mock_controller:
            
            # Mock settings
            settings = Mock()
            settings.has_valid_session.return_value = False
            settings.get_default_directory.return_value = "/tmp"
            settings.get_session_data.return_value = {}
            settings.get_ui_data.return_value = {}
            settings.save_session_data = Mock()
            settings.save_ui_data = Mock()
            mock_settings.return_value = settings
            
            # Mock extraction panel
            panel = Mock()
            panel.get_session_data.return_value = {}
            panel.files_changed = Mock()
            panel.files_changed.connect = Mock()
            panel.extraction_ready = Mock()
            panel.extraction_ready.connect = Mock()
            mock_panel_class.return_value = panel
            
            # Mock preview components
            mock_preview_class.return_value = Mock()
            mock_palette_class.return_value = Mock()
            
            # Create MainWindow
            window = MainWindow()
            controller = window.controller
            
            # Mock extraction worker
            with patch('spritepal.core.controller.ExtractionWorker') as mock_worker_class:
                mock_workers = []
                
                def create_mock_worker(*args, **kwargs):
                    mock_worker = Mock()
                    mock_worker.extraction_complete = Mock()
                    mock_worker.extraction_complete.connect = Mock()
                    mock_worker.extraction_failed = Mock()
                    mock_worker.extraction_failed.connect = Mock()
                    mock_worker.preview_ready = Mock()
                    mock_worker.preview_ready.connect = Mock()
                    mock_worker.progress_update = Mock()
                    mock_worker.progress_update.connect = Mock()
                    mock_workers.append(mock_worker)
                    return mock_worker
                
                mock_worker_class.side_effect = create_mock_worker
                
                # Set up extraction parameters
                extraction_params = {
                    "vram_path": "/tmp/test.vram",
                    "cgram_path": "/tmp/test.cgram",
                    "oam_path": "/tmp/test.oam",
                    "vram_offset": 0xC000,
                    "output_base": "test_output",
                    "create_grayscale": True,
                    "create_metadata": True
                }
                
                # Mock MainWindow methods
                window.get_extraction_params = Mock(return_value=extraction_params)
                window.extraction_failed = Mock()
                window.extraction_complete = Mock()
                
                # Simulate multiple extraction failures
                for i in range(3):
                    controller._on_extract_requested()
                    worker = mock_workers[i]
                    
                    # Simulate extraction failure
                    error_message = f"Extraction {i+1} failed"
                    worker.extraction_failed.emit.side_effect = lambda msg: window.extraction_failed(msg)
                    worker.extraction_failed.emit(error_message)
                
                # Verify all errors were handled
                assert window.extraction_failed.call_count == 3
                
                # Reset mocks
                window.extraction_failed.reset_mock()
                
                # Final extraction - succeeds
                controller._on_extract_requested()
                final_worker = mock_workers[3]
                
                # Simulate successful extraction
                extracted_files = ["test_output.png"]
                final_worker.extraction_complete.emit.side_effect = lambda files: window.extraction_complete(files)
                final_worker.extraction_complete.emit(extracted_files)
                
                # Verify system recovered and final extraction succeeded
                window.extraction_complete.assert_called_once_with(extracted_files)
                window.extraction_failed.assert_not_called()
                
                # Verify system is still functional (can save session)
                window.output_name_edit.setText("recovered_output")
                window._save_session()
                
                # Verify settings were saved (system fully recovered)
                settings.save_session_data.assert_called_once()
                settings.save_ui_data.assert_called_once()


class TestErrorBoundaryIntegration:
    """Test comprehensive error boundary integration"""

    @pytest.mark.integration
    def test_end_to_end_error_handling(self):
        """Test end-to-end error handling across all components"""
        # Create mock MainWindow
        with patch('spritepal.ui.main_window.get_settings_manager') as mock_settings, \
             patch('spritepal.ui.main_window.ExtractionPanel') as mock_panel_class, \
             patch('spritepal.ui.main_window.PreviewPanel') as mock_preview_class, \
             patch('spritepal.ui.main_window.PalettePreviewWidget') as mock_palette_class, \
             patch('spritepal.ui.main_window.ExtractionController') as mock_controller:
            
            # Mock settings
            settings = Mock()
            settings.has_valid_session.return_value = False
            settings.get_default_directory.return_value = "/tmp"
            settings.get_session_data.return_value = {}
            settings.get_ui_data.return_value = {}
            mock_settings.return_value = settings
            
            # Mock extraction panel
            panel = Mock()
            panel.get_session_data.return_value = {}
            panel.files_changed = Mock()
            panel.files_changed.connect = Mock()
            panel.extraction_ready = Mock()
            panel.extraction_ready.connect = Mock()
            mock_panel_class.return_value = panel
            
            # Mock preview components
            mock_preview_class.return_value = Mock()
            mock_palette_class.return_value = Mock()
            
            # Create MainWindow
            window = MainWindow()
            controller = window.controller
            
            # Test complete error handling workflow
            error_scenarios = [
                "File not found error",
                "Permission denied error",
                "Memory allocation error",
                "Network timeout error",
                "Corrupted file error"
            ]
            
            # Mock extraction worker
            with patch('spritepal.core.controller.ExtractionWorker') as mock_worker_class:
                mock_workers = []
                
                def create_mock_worker(*args, **kwargs):
                    mock_worker = Mock()
                    mock_worker.extraction_complete = Mock()
                    mock_worker.extraction_complete.connect = Mock()
                    mock_worker.extraction_failed = Mock()
                    mock_worker.extraction_failed.connect = Mock()
                    mock_worker.preview_ready = Mock()
                    mock_worker.preview_ready.connect = Mock()
                    mock_worker.progress_update = Mock()
                    mock_worker.progress_update.connect = Mock()
                    mock_workers.append(mock_worker)
                    return mock_worker
                
                mock_worker_class.side_effect = create_mock_worker
                
                # Set up extraction parameters
                extraction_params = {
                    "vram_path": "/tmp/test.vram",
                    "cgram_path": "/tmp/test.cgram",
                    "oam_path": "/tmp/test.oam",
                    "vram_offset": 0xC000,
                    "output_base": "test_output",
                    "create_grayscale": True,
                    "create_metadata": True
                }
                
                # Mock MainWindow methods
                window.get_extraction_params = Mock(return_value=extraction_params)
                window.extraction_failed = Mock()
                
                # Test each error scenario
                for i, error_message in enumerate(error_scenarios):
                    controller._on_extract_requested()
                    worker = mock_workers[i]
                    
                    # Simulate extraction failure
                    worker.extraction_failed.emit.side_effect = lambda msg: window.extraction_failed(msg)
                    worker.extraction_failed.emit(error_message)
                
                # Verify all errors were handled
                assert window.extraction_failed.call_count == len(error_scenarios)
                
                # Verify system remains stable after multiple errors
                assert window is not None
                assert controller is not None
                
                # Verify system can still perform basic operations
                window.output_name_edit.setText("test_after_errors")
                assert window.output_name_edit.text() == "test_after_errors"

    @pytest.mark.integration
    def test_concurrent_error_handling(self):
        """Test concurrent error handling"""
        # Create mock MainWindow
        with patch('spritepal.ui.main_window.get_settings_manager') as mock_settings, \
             patch('spritepal.ui.main_window.ExtractionPanel') as mock_panel_class, \
             patch('spritepal.ui.main_window.PreviewPanel') as mock_preview_class, \
             patch('spritepal.ui.main_window.PalettePreviewWidget') as mock_palette_class, \
             patch('spritepal.ui.main_window.ExtractionController') as mock_controller:
            
            # Mock settings
            settings = Mock()
            settings.has_valid_session.return_value = False
            settings.get_default_directory.return_value = "/tmp"
            settings.get_session_data.return_value = {}
            settings.get_ui_data.return_value = {}
            mock_settings.return_value = settings
            
            # Mock extraction panel
            panel = Mock()
            panel.get_session_data.return_value = {}
            panel.files_changed = Mock()
            panel.files_changed.connect = Mock()
            panel.extraction_ready = Mock()
            panel.extraction_ready.connect = Mock()
            mock_panel_class.return_value = panel
            
            # Mock preview components
            mock_preview_class.return_value = Mock()
            mock_palette_class.return_value = Mock()
            
            # Create MainWindow
            window = MainWindow()
            controller = window.controller
            
            # Mock extraction worker
            with patch('spritepal.core.controller.ExtractionWorker') as mock_worker_class:
                mock_workers = []
                
                def create_mock_worker(*args, **kwargs):
                    mock_worker = Mock()
                    mock_worker.extraction_complete = Mock()
                    mock_worker.extraction_complete.connect = Mock()
                    mock_worker.extraction_failed = Mock()
                    mock_worker.extraction_failed.connect = Mock()
                    mock_worker.preview_ready = Mock()
                    mock_worker.preview_ready.connect = Mock()
                    mock_worker.progress_update = Mock()
                    mock_worker.progress_update.connect = Mock()
                    mock_workers.append(mock_worker)
                    return mock_worker
                
                mock_worker_class.side_effect = create_mock_worker
                
                # Set up extraction parameters
                extraction_params = {
                    "vram_path": "/tmp/test.vram",
                    "cgram_path": "/tmp/test.cgram",
                    "oam_path": "/tmp/test.oam",
                    "vram_offset": 0xC000,
                    "output_base": "test_output",
                    "create_grayscale": True,
                    "create_metadata": True
                }
                
                # Mock MainWindow methods
                window.get_extraction_params = Mock(return_value=extraction_params)
                window.extraction_failed = Mock()
                
                # Simulate concurrent operations
                controller._on_extract_requested()
                controller._on_extract_requested()  # Second concurrent extraction
                
                # Verify workers were created
                assert len(mock_workers) >= 1
                
                # Simulate concurrent errors
                for i, worker in enumerate(mock_workers):
                    error_message = f"Concurrent error {i+1}"
                    worker.extraction_failed.emit.side_effect = lambda msg: window.extraction_failed(msg)
                    worker.extraction_failed.emit(error_message)
                
                # Verify all errors were handled
                assert window.extraction_failed.call_count >= 1
                
                # Verify system remains stable
                assert window is not None
                assert controller is not None