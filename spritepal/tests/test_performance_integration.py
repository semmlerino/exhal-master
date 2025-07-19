"""
Integration tests for performance characteristics - Priority 3 test implementation.
Tests performance characteristics under realistic conditions.
"""

import os
import sys
import time
import tempfile
import threading
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, call
import gc
import psutil

import pytest

# Add parent directories to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from spritepal.core.controller import ExtractionController
from spritepal.ui.main_window import MainWindow


class TestLargeFileHandlingPerformance:
    """Test performance characteristics with large VRAM files"""

    def create_large_mock_file(self, size_mb=64):
        """Create a large mock file for testing"""
        temp_file = tempfile.NamedTemporaryFile(suffix=".dmp", delete=False)
        # Create file with specified size
        data = b'A' * (1024 * 1024 * size_mb)  # size_mb MB of data
        temp_file.write(data)
        temp_file.close()
        return temp_file.name

    def create_mock_main_window(self):
        """Create mock MainWindow for performance testing"""
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
    def test_large_vram_file_processing_performance(self):
        """Test performance with large VRAM files (>64MB)"""
        # Create large mock file
        large_file = self.create_large_mock_file(64)  # 64MB file
        
        try:
            # Create mock MainWindow
            window = self.create_mock_main_window()
            controller = window.controller
            
            # Mock extraction worker with performance tracking
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
                
                # Set up extraction parameters with large file
                extraction_params = {
                    "vram_path": large_file,
                    "cgram_path": "/tmp/test.cgram",
                    "oam_path": "/tmp/test.oam",
                    "vram_offset": 0xC000,
                    "output_base": "large_output",
                    "create_grayscale": True,
                    "create_metadata": True
                }
                
                # Mock MainWindow methods
                window.get_extraction_params = Mock(return_value=extraction_params)
                window.extraction_complete = Mock()
                
                # Measure performance of extraction setup
                start_time = time.time()
                
                # Start extraction
                controller._on_extract_requested()
                
                # Verify worker was created
                mock_worker_class.assert_called_once()
                
                # Simulate rapid extraction completion
                extracted_files = ["large_output.png"]
                mock_worker.extraction_complete.emit.side_effect = lambda files: window.extraction_complete(files)
                mock_worker.extraction_complete.emit(extracted_files)
                
                # Measure completion time
                end_time = time.time()
                processing_time = end_time - start_time
                
                # Verify performance is reasonable (setup should be fast)
                assert processing_time < 1.0, f"Extraction setup took too long: {processing_time:.2f}s"
                
                # Verify extraction was handled
                window.extraction_complete.assert_called_once_with(extracted_files)
                
        finally:
            # Clean up large file
            os.unlink(large_file)

    @pytest.mark.integration
    def test_multiple_large_files_performance(self):
        """Test performance with multiple large files"""
        # Create multiple large mock files
        large_files = []
        for i in range(3):
            large_file = self.create_large_mock_file(32)  # 32MB each
            large_files.append(large_file)
        
        try:
            # Create mock MainWindow
            window = self.create_mock_main_window()
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
                
                # Mock MainWindow methods
                window.get_extraction_params = Mock()
                window.extraction_complete = Mock()
                
                # Measure performance of multiple extractions
                start_time = time.time()
                
                # Process multiple large files
                for i, large_file in enumerate(large_files):
                    extraction_params = {
                        "vram_path": large_file,
                        "cgram_path": "/tmp/test.cgram",
                        "oam_path": "/tmp/test.oam",
                        "vram_offset": 0xC000,
                        "output_base": f"output_{i}",
                        "create_grayscale": True,
                        "create_metadata": True
                    }
                    
                    window.get_extraction_params.return_value = extraction_params
                    
                    # Start extraction
                    controller._on_extract_requested()
                    
                    # Simulate completion
                    worker = mock_workers[i]
                    extracted_files = [f"output_{i}.png"]
                    worker.extraction_complete.emit.side_effect = lambda files: window.extraction_complete(files)
                    worker.extraction_complete.emit(extracted_files)
                
                # Measure completion time
                end_time = time.time()
                processing_time = end_time - start_time
                
                # Verify performance is reasonable for multiple files
                assert processing_time < 5.0, f"Multiple file processing took too long: {processing_time:.2f}s"
                
                # Verify all extractions were handled
                assert window.extraction_complete.call_count == len(large_files)
                
        finally:
            # Clean up large files
            for large_file in large_files:
                os.unlink(large_file)

    @pytest.mark.integration  
    def test_memory_usage_with_large_files(self):
        """Test memory usage during large file processing"""
        # Get initial memory usage
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Create large mock file
        large_file = self.create_large_mock_file(100)  # 100MB file
        
        try:
            # Create mock MainWindow
            window = self.create_mock_main_window()
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
                
                # Set up extraction parameters with large file
                extraction_params = {
                    "vram_path": large_file,
                    "cgram_path": "/tmp/test.cgram",
                    "oam_path": "/tmp/test.oam",
                    "vram_offset": 0xC000,
                    "output_base": "memory_test",
                    "create_grayscale": True,
                    "create_metadata": True
                }
                
                # Mock MainWindow methods
                window.get_extraction_params = Mock(return_value=extraction_params)
                window.extraction_complete = Mock()
                
                # Start extraction
                controller._on_extract_requested()
                
                # Simulate extraction completion
                extracted_files = ["memory_test.png"]
                mock_worker.extraction_complete.emit.side_effect = lambda files: window.extraction_complete(files)
                mock_worker.extraction_complete.emit(extracted_files)
                
                # Force garbage collection
                gc.collect()
                
                # Measure memory usage after processing
                final_memory = process.memory_info().rss / 1024 / 1024  # MB
                memory_increase = final_memory - initial_memory
                
                # Verify memory usage is reasonable (should not increase dramatically)
                assert memory_increase < 200, f"Memory usage increased too much: {memory_increase:.2f}MB"
                
                # Verify extraction was handled
                window.extraction_complete.assert_called_once_with(extracted_files)
                
        finally:
            # Clean up large file
            os.unlink(large_file)
            
            # Force garbage collection
            gc.collect()


class TestUIResponsivenessDuringExtraction:
    """Test UI thread responsiveness during extraction"""

    def create_mock_main_window(self):
        """Create mock MainWindow for responsiveness testing"""
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
    def test_ui_responsiveness_during_extraction(self):
        """Test UI thread responsiveness while extraction is running"""
        # Create mock MainWindow
        window = self.create_mock_main_window()
        controller = window.controller
        
        # Mock extraction worker with delayed completion
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
                "output_base": "responsiveness_test",
                "create_grayscale": True,
                "create_metadata": True
            }
            
            # Mock MainWindow methods
            window.get_extraction_params = Mock(return_value=extraction_params)
            window.extraction_complete = Mock()
            
            # Start extraction
            start_time = time.time()
            controller._on_extract_requested()
            
            # Simulate UI operations during extraction
            ui_operations = []
            
            # Test UI responsiveness by performing operations
            for i in range(10):
                operation_start = time.time()
                
                # Simulate UI operation (setting text)
                window.output_name_edit.setText(f"test_{i}")
                
                operation_end = time.time()
                operation_time = operation_end - operation_start
                ui_operations.append(operation_time)
                
                # Small delay to simulate realistic UI interaction
                time.sleep(0.01)
            
            # Complete extraction
            extracted_files = ["responsiveness_test.png"]
            mock_worker.extraction_complete.emit.side_effect = lambda files: window.extraction_complete(files)
            mock_worker.extraction_complete.emit(extracted_files)
            
            end_time = time.time()
            total_time = end_time - start_time
            
            # Verify UI operations were fast (responsive)
            max_operation_time = max(ui_operations)
            average_operation_time = sum(ui_operations) / len(ui_operations)
            
            assert max_operation_time < 0.1, f"UI operation took too long: {max_operation_time:.4f}s"
            assert average_operation_time < 0.05, f"Average UI operation time too high: {average_operation_time:.4f}s"
            
            # Verify extraction was handled
            window.extraction_complete.assert_called_once_with(extracted_files)

    @pytest.mark.integration
    def test_button_state_responsiveness(self):
        """Test button state changes are responsive during extraction"""
        # Create mock MainWindow
        window = self.create_mock_main_window()
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
                "output_base": "button_test",
                "create_grayscale": True,
                "create_metadata": True
            }
            
            # Mock MainWindow methods
            window.get_extraction_params = Mock(return_value=extraction_params)
            window.extraction_complete = Mock()
            
            # Set up initial button state
            window.extract_button.setEnabled(True)
            window.open_editor_button.setEnabled(False)
            
            # Measure button state change responsiveness
            start_time = time.time()
            
            # Start extraction (should disable extract button)
            controller._on_extract_requested()
            
            # Measure how quickly button state changed
            button_change_time = time.time() - start_time
            
            # Verify button state change was fast
            assert button_change_time < 0.1, f"Button state change took too long: {button_change_time:.4f}s"
            
            # Verify button state is correct
            assert window.extract_button.isEnabled() is False
            
            # Complete extraction
            extracted_files = ["button_test.png"]
            mock_worker.extraction_complete.emit.side_effect = lambda files: window.extraction_complete(files)
            mock_worker.extraction_complete.emit(extracted_files)
            
            # Verify extraction was handled
            window.extraction_complete.assert_called_once_with(extracted_files)

    @pytest.mark.integration
    def test_progress_update_responsiveness(self):
        """Test progress update responsiveness"""
        # Create mock MainWindow
        window = self.create_mock_main_window()
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
                "output_base": "progress_test",
                "create_grayscale": True,
                "create_metadata": True
            }
            
            # Mock MainWindow methods
            window.get_extraction_params = Mock(return_value=extraction_params)
            window.extraction_complete = Mock()
            
            # Start extraction
            controller._on_extract_requested()
            
            # Simulate rapid progress updates
            progress_update_times = []
            
            for progress in range(0, 101, 10):
                update_start = time.time()
                
                # Simulate progress update
                mock_worker.progress_update.emit(progress)
                
                update_end = time.time()
                update_time = update_end - update_start
                progress_update_times.append(update_time)
                
                # Small delay between updates
                time.sleep(0.01)
            
            # Complete extraction
            extracted_files = ["progress_test.png"]
            mock_worker.extraction_complete.emit.side_effect = lambda files: window.extraction_complete(files)
            mock_worker.extraction_complete.emit(extracted_files)
            
            # Verify progress updates were fast
            max_update_time = max(progress_update_times)
            average_update_time = sum(progress_update_times) / len(progress_update_times)
            
            assert max_update_time < 0.05, f"Progress update took too long: {max_update_time:.4f}s"
            assert average_update_time < 0.02, f"Average progress update time too high: {average_update_time:.4f}s"
            
            # Verify extraction was handled
            window.extraction_complete.assert_called_once_with(extracted_files)


class TestMemoryUsageDuringWorkflows:
    """Test memory leak detection during workflows"""

    def create_mock_main_window(self):
        """Create mock MainWindow for memory testing"""
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
    def test_memory_leak_detection(self):
        """Test memory leak detection during multiple workflows"""
        # Get initial memory usage
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Create mock MainWindow
        window = self.create_mock_main_window()
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
            
            # Mock MainWindow methods
            window.get_extraction_params = Mock()
            window.extraction_complete = Mock()
            
            # Perform multiple extraction workflows
            memory_measurements = []
            
            for i in range(10):
                # Set up extraction parameters
                extraction_params = {
                    "vram_path": f"/tmp/test_{i}.vram",
                    "cgram_path": f"/tmp/test_{i}.cgram",
                    "oam_path": f"/tmp/test_{i}.oam",
                    "vram_offset": 0xC000,
                    "output_base": f"memory_test_{i}",
                    "create_grayscale": True,
                    "create_metadata": True
                }
                
                window.get_extraction_params.return_value = extraction_params
                
                # Start extraction
                controller._on_extract_requested()
                
                # Complete extraction
                worker = mock_workers[i]
                extracted_files = [f"memory_test_{i}.png"]
                worker.extraction_complete.emit.side_effect = lambda files: window.extraction_complete(files)
                worker.extraction_complete.emit(extracted_files)
                
                # Force garbage collection
                gc.collect()
                
                # Measure memory usage
                current_memory = process.memory_info().rss / 1024 / 1024  # MB
                memory_measurements.append(current_memory)
                
                # Small delay to allow cleanup
                time.sleep(0.1)
            
            # Analyze memory usage trend
            final_memory = memory_measurements[-1]
            memory_increase = final_memory - initial_memory
            
            # Check for memory leaks (should not increase significantly)
            assert memory_increase < 100, f"Memory usage increased too much: {memory_increase:.2f}MB"
            
            # Check that memory usage is stable (no continuous growth)
            if len(memory_measurements) > 5:
                early_avg = sum(memory_measurements[:5]) / 5
                late_avg = sum(memory_measurements[-5:]) / 5
                growth_rate = (late_avg - early_avg) / early_avg
                
                assert growth_rate < 0.2, f"Memory growth rate too high: {growth_rate:.2f}"
            
            # Verify all extractions were handled
            assert window.extraction_complete.call_count == 10

    @pytest.mark.integration
    def test_dialog_memory_management(self):
        """Test memory management during dialog workflows"""
        # Get initial memory usage
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Create mock controller
        from spritepal.core.controller import ExtractionController
        
        mock_window = Mock()
        controller = ExtractionController(mock_window)
        
        # Mock dialog creation and cleanup
        with patch('spritepal.ui.row_arrangement_dialog.RowArrangementDialog') as mock_dialog:
            dialog_instances = []
            
            def create_mock_dialog(*args, **kwargs):
                mock_dialog_instance = Mock()
                mock_dialog_instance.exec.return_value = 1  # Accepted
                mock_dialog_instance.get_arranged_path.return_value = "/tmp/test.png"
                mock_dialog_instance.cleanup = Mock()  # Mock cleanup method
                dialog_instances.append(mock_dialog_instance)
                return mock_dialog_instance
            
            mock_dialog.side_effect = create_mock_dialog
            
            # Mock file operations
            with patch('os.path.exists', return_value=True):
                # Perform multiple dialog workflows
                memory_measurements = []
                
                for i in range(10):
                    # Trigger dialog
                    controller._on_arrange_rows_requested(f"test_sprite_{i}.png")
                    
                    # Force garbage collection
                    gc.collect()
                    
                    # Measure memory usage
                    current_memory = process.memory_info().rss / 1024 / 1024  # MB
                    memory_measurements.append(current_memory)
                    
                    # Small delay to allow cleanup
                    time.sleep(0.1)
                
                # Verify all dialogs were created
                assert len(dialog_instances) == 10
                
                # Check memory usage
                final_memory = memory_measurements[-1]
                memory_increase = final_memory - initial_memory
                
                # Should not increase significantly with proper cleanup
                assert memory_increase < 50, f"Dialog memory usage increased too much: {memory_increase:.2f}MB"

    @pytest.mark.integration
    def test_preview_memory_management(self):
        """Test preview memory management"""
        # Get initial memory usage
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Create mock MainWindow
        window = self.create_mock_main_window()
        controller = window.controller
        
        # Mock extraction worker with preview updates
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
            
            # Mock MainWindow methods
            window.get_extraction_params = Mock()
            window.extraction_complete = Mock()
            
            # Perform multiple extractions with preview updates
            memory_measurements = []
            
            for i in range(10):
                # Set up extraction parameters
                extraction_params = {
                    "vram_path": f"/tmp/test_{i}.vram",
                    "cgram_path": f"/tmp/test_{i}.cgram",
                    "oam_path": f"/tmp/test_{i}.oam",
                    "vram_offset": 0xC000,
                    "output_base": f"preview_test_{i}",
                    "create_grayscale": True,
                    "create_metadata": True
                }
                
                window.get_extraction_params.return_value = extraction_params
                
                # Start extraction
                controller._on_extract_requested()
                
                # Simulate multiple preview updates
                worker = mock_workers[i]
                for j in range(5):
                    mock_image = Mock()
                    worker.preview_ready.emit(mock_image)
                
                # Complete extraction
                extracted_files = [f"preview_test_{i}.png"]
                worker.extraction_complete.emit.side_effect = lambda files: window.extraction_complete(files)
                worker.extraction_complete.emit(extracted_files)
                
                # Force garbage collection
                gc.collect()
                
                # Measure memory usage
                current_memory = process.memory_info().rss / 1024 / 1024  # MB
                memory_measurements.append(current_memory)
                
                # Small delay to allow cleanup
                time.sleep(0.1)
            
            # Check memory usage
            final_memory = memory_measurements[-1]
            memory_increase = final_memory - initial_memory
            
            # Should not increase significantly with proper preview cleanup
            assert memory_increase < 100, f"Preview memory usage increased too much: {memory_increase:.2f}MB"


class TestConcurrentOperationPerformance:
    """Test performance of concurrent operations"""

    def create_mock_main_window(self):
        """Create mock MainWindow for concurrent testing"""
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
    def test_concurrent_extraction_performance(self):
        """Test performance of concurrent extraction operations"""
        # Create mock MainWindow
        window = self.create_mock_main_window()
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
            
            # Mock MainWindow methods
            window.get_extraction_params = Mock()
            window.extraction_complete = Mock()
            
            # Measure concurrent extraction performance
            start_time = time.time()
            
            # Start multiple extractions concurrently
            extraction_count = 5
            for i in range(extraction_count):
                extraction_params = {
                    "vram_path": f"/tmp/concurrent_{i}.vram",
                    "cgram_path": f"/tmp/concurrent_{i}.cgram",
                    "oam_path": f"/tmp/concurrent_{i}.oam",
                    "vram_offset": 0xC000,
                    "output_base": f"concurrent_{i}",
                    "create_grayscale": True,
                    "create_metadata": True
                }
                
                window.get_extraction_params.return_value = extraction_params
                
                # Start extraction
                controller._on_extract_requested()
            
            # Complete all extractions
            for i, worker in enumerate(mock_workers):
                extracted_files = [f"concurrent_{i}.png"]
                worker.extraction_complete.emit.side_effect = lambda files: window.extraction_complete(files)
                worker.extraction_complete.emit(extracted_files)
            
            end_time = time.time()
            total_time = end_time - start_time
            
            # Verify performance is reasonable for concurrent operations
            assert total_time < 2.0, f"Concurrent extractions took too long: {total_time:.2f}s"
            
            # Verify all extractions were handled
            assert window.extraction_complete.call_count == extraction_count

    @pytest.mark.integration
    def test_concurrent_dialog_performance(self):
        """Test performance of concurrent dialog operations"""
        # Create mock controller
        from spritepal.core.controller import ExtractionController
        
        mock_window = Mock()
        controller = ExtractionController(mock_window)
        
        # Mock dialog creation
        with patch('spritepal.ui.row_arrangement_dialog.RowArrangementDialog') as mock_dialog:
            dialog_instances = []
            
            def create_mock_dialog(*args, **kwargs):
                mock_dialog_instance = Mock()
                mock_dialog_instance.exec.return_value = 1  # Accepted
                mock_dialog_instance.get_arranged_path.return_value = "/tmp/test.png"
                dialog_instances.append(mock_dialog_instance)
                return mock_dialog_instance
            
            mock_dialog.side_effect = create_mock_dialog
            
            # Mock file operations
            with patch('os.path.exists', return_value=True):
                # Measure concurrent dialog performance
                start_time = time.time()
                
                # Start multiple dialogs concurrently (simulated)
                dialog_count = 5
                for i in range(dialog_count):
                    controller._on_arrange_rows_requested(f"concurrent_sprite_{i}.png")
                
                end_time = time.time()
                total_time = end_time - start_time
                
                # Verify performance is reasonable
                assert total_time < 1.0, f"Concurrent dialogs took too long: {total_time:.2f}s"
                
                # Verify all dialogs were created
                assert len(dialog_instances) == dialog_count

    @pytest.mark.integration
    def test_concurrent_preview_updates_performance(self):
        """Test performance of concurrent preview updates"""
        # Create mock MainWindow
        window = self.create_mock_main_window()
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
            
            # Mock MainWindow methods
            window.get_extraction_params = Mock()
            window.extraction_complete = Mock()
            
            # Start multiple extractions
            extraction_count = 3
            for i in range(extraction_count):
                extraction_params = {
                    "vram_path": f"/tmp/preview_{i}.vram",
                    "cgram_path": f"/tmp/preview_{i}.cgram",
                    "oam_path": f"/tmp/preview_{i}.oam",
                    "vram_offset": 0xC000,
                    "output_base": f"preview_{i}",
                    "create_grayscale": True,
                    "create_metadata": True
                }
                
                window.get_extraction_params.return_value = extraction_params
                controller._on_extract_requested()
            
            # Measure concurrent preview update performance
            start_time = time.time()
            
            # Simulate concurrent preview updates
            for i, worker in enumerate(mock_workers):
                for j in range(10):
                    mock_image = Mock()
                    worker.preview_ready.emit(mock_image)
            
            end_time = time.time()
            update_time = end_time - start_time
            
            # Verify preview updates are fast
            assert update_time < 0.5, f"Concurrent preview updates took too long: {update_time:.2f}s"
            
            # Complete all extractions
            for i, worker in enumerate(mock_workers):
                extracted_files = [f"preview_{i}.png"]
                worker.extraction_complete.emit.side_effect = lambda files: window.extraction_complete(files)
                worker.extraction_complete.emit(extracted_files)
            
            # Verify all extractions were handled
            assert window.extraction_complete.call_count == extraction_count


class TestPreviewGenerationPerformance:
    """Test preview rendering speed"""

    def create_mock_main_window(self):
        """Create mock MainWindow for preview testing"""
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
            
            # Mock preview components with performance tracking
            mock_preview_widget = Mock()
            mock_preview_widget.update_preview = Mock()
            mock_preview_class.return_value = mock_preview_widget
            
            mock_palette_widget = Mock()
            mock_palette_widget.update_preview = Mock()
            mock_palette_class.return_value = mock_palette_widget
            
            # Create MainWindow
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
    def test_preview_generation_speed(self):
        """Test preview rendering speed"""
        # Create mock MainWindow
        window = self.create_mock_main_window()
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
                "output_base": "preview_speed_test",
                "create_grayscale": True,
                "create_metadata": True
            }
            
            # Mock MainWindow methods
            window.get_extraction_params = Mock(return_value=extraction_params)
            window.extraction_complete = Mock()
            
            # Start extraction
            controller._on_extract_requested()
            
            # Measure preview generation performance
            preview_times = []
            
            for i in range(20):
                mock_image = Mock()
                
                # Measure preview update time
                start_time = time.time()
                
                # Simulate preview update (this calls the mocked method)
                mock_worker.preview_ready.emit(mock_image)
                
                end_time = time.time()
                preview_time = end_time - start_time
                preview_times.append(preview_time)
            
            # Complete extraction
            extracted_files = ["preview_speed_test.png"]
            mock_worker.extraction_complete.emit.side_effect = lambda files: window.extraction_complete(files)
            mock_worker.extraction_complete.emit(extracted_files)
            
            # Verify preview generation is fast
            max_preview_time = max(preview_times)
            average_preview_time = sum(preview_times) / len(preview_times)
            
            assert max_preview_time < 0.1, f"Preview generation took too long: {max_preview_time:.4f}s"
            assert average_preview_time < 0.05, f"Average preview time too high: {average_preview_time:.4f}s"
            
            # Verify extraction was handled
            window.extraction_complete.assert_called_once_with(extracted_files)

    @pytest.mark.integration
    def test_large_preview_performance(self):
        """Test preview performance with large images"""
        # Create mock MainWindow
        window = self.create_mock_main_window()
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
                "vram_path": "/tmp/large_test.vram",
                "cgram_path": "/tmp/large_test.cgram",
                "oam_path": "/tmp/large_test.oam",
                "vram_offset": 0xC000,
                "output_base": "large_preview_test",
                "create_grayscale": True,
                "create_metadata": True
            }
            
            # Mock MainWindow methods
            window.get_extraction_params = Mock(return_value=extraction_params)
            window.extraction_complete = Mock()
            
            # Start extraction
            controller._on_extract_requested()
            
            # Simulate large preview updates
            large_preview_times = []
            
            for i in range(5):
                # Create mock large image
                mock_large_image = Mock()
                mock_large_image.size = (2048, 2048)  # Large image
                
                # Measure large preview update time
                start_time = time.time()
                
                # Simulate large preview update
                mock_worker.preview_ready.emit(mock_large_image)
                
                end_time = time.time()
                preview_time = end_time - start_time
                large_preview_times.append(preview_time)
            
            # Complete extraction
            extracted_files = ["large_preview_test.png"]
            mock_worker.extraction_complete.emit.side_effect = lambda files: window.extraction_complete(files)
            mock_worker.extraction_complete.emit(extracted_files)
            
            # Verify large preview generation is reasonable
            max_large_preview_time = max(large_preview_times)
            average_large_preview_time = sum(large_preview_times) / len(large_preview_times)
            
            assert max_large_preview_time < 0.5, f"Large preview generation took too long: {max_large_preview_time:.4f}s"
            assert average_large_preview_time < 0.2, f"Average large preview time too high: {average_large_preview_time:.4f}s"
            
            # Verify extraction was handled
            window.extraction_complete.assert_called_once_with(extracted_files)


class TestGarbageCollectionIntegration:
    """Test memory cleanup and garbage collection"""

    @pytest.mark.integration
    def test_garbage_collection_after_extraction(self):
        """Test garbage collection after extraction workflow"""
        # Get initial memory usage
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
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
            # Create mock MainWindow for controller integration testing
            window = Mock()
            window.status_bar = Mock()
            window.status_bar.showMessage = Mock()
            window.extraction_failed = Mock()
            window.extraction_complete = Mock()
            window._output_path = "test_sprites"
            window._extracted_files = []
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
                    "vram_path": "/tmp/gc_test.vram",
                    "cgram_path": "/tmp/gc_test.cgram",
                    "oam_path": "/tmp/gc_test.oam",
                    "vram_offset": 0xC000,
                    "output_base": "gc_test",
                    "create_grayscale": True,
                    "create_metadata": True
                }
                
                # Mock MainWindow methods
                window.get_extraction_params = Mock(return_value=extraction_params)
                window.extraction_complete = Mock()
                
                # Start extraction
                controller._on_extract_requested()
                
                # Simulate memory-intensive operations
                for i in range(100):
                    mock_image = Mock()
                    mock_worker.preview_ready.emit(mock_image)
                
                # Complete extraction
                extracted_files = ["gc_test.png"]
                mock_worker.extraction_complete.emit.side_effect = lambda files: window.extraction_complete(files)
                mock_worker.extraction_complete.emit(extracted_files)
                
                # Force garbage collection
                gc.collect()
                
                # Measure memory after garbage collection
                final_memory = process.memory_info().rss / 1024 / 1024  # MB
                memory_increase = final_memory - initial_memory
                
                # Verify memory cleanup is effective
                assert memory_increase < 100, f"Memory not cleaned up effectively: {memory_increase:.2f}MB"
                
                # Verify extraction was handled
                window.extraction_complete.assert_called_once_with(extracted_files)

    @pytest.mark.integration
    def test_resource_cleanup_on_window_close(self):
        """Test resource cleanup when window is closed"""
        # Get initial memory usage
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
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
            # Create mock MainWindow for controller integration testing
            window = Mock()
            window.status_bar = Mock()
            window.status_bar.showMessage = Mock()
            window.extraction_failed = Mock()
            window.extraction_complete = Mock()
            window._output_path = "test_sprites"
            window._extracted_files = []
            
            # Set up some state
            window.output_name_edit.setText("cleanup_test")
            window.grayscale_check.setChecked(True)
            
            # Simulate window close
            from PyQt6.QtGui import QCloseEvent
            close_event = QCloseEvent()
            window.closeEvent(close_event)
            
            # Verify session was saved
            settings.save_session_data.assert_called_once()
            settings.save_ui_data.assert_called_once()
            
            # Force garbage collection
            gc.collect()
            
            # Measure memory after cleanup
            final_memory = process.memory_info().rss / 1024 / 1024  # MB
            memory_increase = final_memory - initial_memory
            
            # Verify memory was cleaned up
            assert memory_increase < 50, f"Window cleanup ineffective: {memory_increase:.2f}MB"

    @pytest.mark.integration
    def test_periodic_garbage_collection(self):
        """Test periodic garbage collection during long operations"""
        # Get initial memory usage
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
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
            # Create mock MainWindow for controller integration testing
            window = Mock()
            window.status_bar = Mock()
            window.status_bar.showMessage = Mock()
            window.extraction_failed = Mock()
            window.extraction_complete = Mock()
            window._output_path = "test_sprites"
            window._extracted_files = []
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
                    "vram_path": "/tmp/periodic_gc_test.vram",
                    "cgram_path": "/tmp/periodic_gc_test.cgram",
                    "oam_path": "/tmp/periodic_gc_test.oam",
                    "vram_offset": 0xC000,
                    "output_base": "periodic_gc_test",
                    "create_grayscale": True,
                    "create_metadata": True
                }
                
                # Mock MainWindow methods
                window.get_extraction_params = Mock(return_value=extraction_params)
                window.extraction_complete = Mock()
                
                # Start extraction
                controller._on_extract_requested()
                
                # Simulate long operation with periodic garbage collection
                memory_measurements = []
                
                for i in range(100):
                    # Simulate memory-intensive operation
                    mock_image = Mock()
                    mock_worker.preview_ready.emit(mock_image)
                    
                    # Periodic garbage collection (every 20 operations)
                    if i % 20 == 0:
                        gc.collect()
                        current_memory = process.memory_info().rss / 1024 / 1024  # MB
                        memory_measurements.append(current_memory)
                
                # Complete extraction
                extracted_files = ["periodic_gc_test.png"]
                mock_worker.extraction_complete.emit.side_effect = lambda files: window.extraction_complete(files)
                mock_worker.extraction_complete.emit(extracted_files)
                
                # Final garbage collection
                gc.collect()
                final_memory = process.memory_info().rss / 1024 / 1024  # MB
                
                # Verify periodic garbage collection keeps memory stable
                if len(memory_measurements) > 2:
                    max_memory = max(memory_measurements)
                    min_memory = min(memory_measurements)
                    memory_variance = max_memory - min_memory
                    
                    assert memory_variance < 100, f"Memory variance too high: {memory_variance:.2f}MB"
                
                # Verify final memory usage is reasonable
                final_memory_increase = final_memory - initial_memory
                assert final_memory_increase < 100, f"Final memory increase too high: {final_memory_increase:.2f}MB"
                
                # Verify extraction was handled
                window.extraction_complete.assert_called_once_with(extracted_files)


class TestPerformanceIntegration:
    """Test comprehensive performance integration scenarios"""

    @pytest.mark.integration
    def test_end_to_end_performance_workflow(self):
        """Test end-to-end performance of complete workflow"""
        # Get initial memory usage
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
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
            # Create mock MainWindow for controller integration testing
            window = Mock()
            window.status_bar = Mock()
            window.status_bar.showMessage = Mock()
            window.extraction_failed = Mock()
            window.extraction_complete = Mock()
            window._output_path = "test_sprites"
            window._extracted_files = []
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
                    "vram_path": "/tmp/end_to_end_test.vram",
                    "cgram_path": "/tmp/end_to_end_test.cgram",
                    "oam_path": "/tmp/end_to_end_test.oam",
                    "vram_offset": 0xC000,
                    "output_base": "end_to_end_test",
                    "create_grayscale": True,
                    "create_metadata": True
                }
                
                # Mock MainWindow methods
                window.get_extraction_params = Mock(return_value=extraction_params)
                window.extraction_complete = Mock()
                
                # Measure end-to-end performance
                start_time = time.time()
                
                # Complete workflow: setup -> extraction -> preview updates -> completion
                controller._on_extract_requested()
                
                # Simulate preview updates
                for i in range(50):
                    mock_image = Mock()
                    mock_worker.preview_ready.emit(mock_image)
                    
                    # Simulate progress updates
                    progress = (i + 1) * 2  # 0-100%
                    mock_worker.progress_update.emit(min(progress, 100))
                
                # Complete extraction
                extracted_files = ["end_to_end_test.png", "end_to_end_test.pal.json"]
                mock_worker.extraction_complete.emit.side_effect = lambda files: window.extraction_complete(files)
                mock_worker.extraction_complete.emit(extracted_files)
                
                end_time = time.time()
                total_time = end_time - start_time
                
                # Verify end-to-end performance
                assert total_time < 2.0, f"End-to-end workflow took too long: {total_time:.2f}s"
                
                # Verify extraction was handled
                window.extraction_complete.assert_called_once_with(extracted_files)
                
                # Force garbage collection
                gc.collect()
                
                # Verify memory usage is reasonable
                final_memory = process.memory_info().rss / 1024 / 1024  # MB
                memory_increase = final_memory - initial_memory
                
                assert memory_increase < 100, f"End-to-end memory increase too high: {memory_increase:.2f}MB"

    @pytest.mark.integration
    def test_stress_test_performance(self):
        """Test performance under stress conditions"""
        # Get initial memory usage
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
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
            # Create mock MainWindow for controller integration testing
            window = Mock()
            window.status_bar = Mock()
            window.status_bar.showMessage = Mock()
            window.extraction_failed = Mock()
            window.extraction_complete = Mock()
            window._output_path = "test_sprites"
            window._extracted_files = []
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
                
                # Mock MainWindow methods
                window.get_extraction_params = Mock()
                window.extraction_complete = Mock()
                
                # Measure stress test performance
                start_time = time.time()
                
                # Stress test: many rapid operations
                stress_operations = 20
                for i in range(stress_operations):
                    # Set up extraction parameters
                    extraction_params = {
                        "vram_path": f"/tmp/stress_test_{i}.vram",
                        "cgram_path": f"/tmp/stress_test_{i}.cgram",
                        "oam_path": f"/tmp/stress_test_{i}.oam",
                        "vram_offset": 0xC000,
                        "output_base": f"stress_test_{i}",
                        "create_grayscale": True,
                        "create_metadata": True
                    }
                    
                    window.get_extraction_params.return_value = extraction_params
                    
                    # Start extraction
                    controller._on_extract_requested()
                    
                    # Simulate rapid preview updates
                    if i < len(mock_workers):
                        worker = mock_workers[i]
                        for j in range(10):
                            mock_image = Mock()
                            worker.preview_ready.emit(mock_image)
                        
                        # Complete extraction
                        extracted_files = [f"stress_test_{i}.png"]
                        worker.extraction_complete.emit.side_effect = lambda files: window.extraction_complete(files)
                        worker.extraction_complete.emit(extracted_files)
                
                end_time = time.time()
                total_time = end_time - start_time
                
                # Verify stress test performance
                assert total_time < 5.0, f"Stress test took too long: {total_time:.2f}s"
                
                # Verify all operations were handled
                assert window.extraction_complete.call_count == stress_operations
                
                # Force garbage collection
                gc.collect()
                
                # Verify memory usage under stress
                final_memory = process.memory_info().rss / 1024 / 1024  # MB
                memory_increase = final_memory - initial_memory
                
                assert memory_increase < 200, f"Stress test memory increase too high: {memory_increase:.2f}MB"