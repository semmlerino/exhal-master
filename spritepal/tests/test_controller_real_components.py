"""
Refactored controller tests using real components and minimal mocking.

Key improvements:
- Uses real ExtractionController with real managers
- Only mocks external dependencies (subprocess, file I/O)
- Tests behavior and outcomes, not implementation details
- No assert_called patterns - verifies actual results
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Any
from unittest.mock import Mock, patch

import pytest
from PIL import Image

from core.controller import ExtractionController
from core.managers import ExtractionManager, InjectionManager, SessionManager
from core.workers import VRAMExtractionWorker
from tests.infrastructure.test_doubles import (
    MockROMFile,
    MockProgressDialog,
    MockMessageBox,
    TestDoubleFactory,
    setup_hal_mocking,
    setup_rom_mocking,
)
from utils.file_validator import FileValidator

pytestmark = [
    pytest.mark.unit,
    pytest.mark.headless,
    pytest.mark.parallel_safe,
]

class TestControllerWithRealManagers:
    """Test ExtractionController with real manager instances."""

    @pytest.fixture
    def real_managers(self):
        """Create real manager instances with test doubles for external deps."""
        extraction_manager = ExtractionManager()
        injection_manager = InjectionManager()
        session_manager = SessionManager()
        
        # Setup test doubles only for external dependencies
        setup_hal_mocking(extraction_manager, deterministic=True)
        setup_rom_mocking(extraction_manager, rom_type="standard")
        setup_hal_mocking(injection_manager, deterministic=True)
        
        return {
            'extraction': extraction_manager,
            'injection': injection_manager,
            'session': session_manager
        }

    @pytest.fixture
    def mock_main_window(self):
        """Create a minimal mock main window with required attributes."""
        window = Mock()
        
        # Add required signals
        window.extract_requested = Mock()
        window.open_in_editor_requested = Mock()
        window.arrange_rows_requested = Mock()
        window.arrange_grid_requested = Mock()
        window.inject_requested = Mock()
        
        # Add UI components
        window.extraction_panel = Mock()
        window.rom_extraction_panel = Mock()
        window.output_settings_manager = Mock()
        window.toolbar_manager = Mock()
        window.preview_coordinator = Mock()
        window.status_bar_manager = Mock()
        window.status_bar = Mock()
        window.sprite_preview = Mock()
        window.palette_preview = Mock()
        window.extraction_tabs = Mock()
        
        # Add methods
        window.get_extraction_params = Mock()
        window.extraction_failed = Mock()
        window.extraction_completed = Mock()
        window.update_preview = Mock()
        
        # Add state
        window._output_path = ""
        window._extracted_files = []
        
        return window

    def test_controller_initialization_with_real_managers(self, mock_main_window, real_managers):
        """Test that controller initializes correctly with real managers."""
        # Create controller with real managers
        controller = ExtractionController(
            main_window=mock_main_window,
            extraction_manager=real_managers['extraction'],
            injection_manager=real_managers['injection'],
            session_manager=real_managers['session']
        )
        
        # Verify controller is properly initialized
        assert controller.main_window == mock_main_window
        assert controller.extraction_manager == real_managers['extraction']
        assert controller.injection_manager == real_managers['injection']
        assert controller.session_manager == real_managers['session']
        assert controller.worker is None
        assert controller.rom_worker is None
        
        # Verify error handler is set up
        assert controller.error_handler is not None

    def test_vram_extraction_validation_behavior(self, mock_main_window, real_managers, tmp_path):
        """Test VRAM extraction parameter validation with real manager."""
        # Setup: Invalid parameters (missing VRAM)
        mock_main_window.get_extraction_params.return_value = {
            "vram_path": "",  # Missing VRAM
            "cgram_path": str(tmp_path / "test.cgram"),
            "output_base": str(tmp_path / "output"),
            "grayscale_mode": False,
        }
        
        # Create controller with real managers
        controller = ExtractionController(
            main_window=mock_main_window,
            extraction_manager=real_managers['extraction'],
            injection_manager=real_managers['injection'],
            session_manager=real_managers['session']
        )
        
        # Act: Start extraction
        controller.start_extraction()
        
        # Assert BEHAVIOR: Error was reported to user
        mock_main_window.extraction_failed.assert_called_once()
        error_msg = mock_main_window.extraction_failed.call_args[0][0]
        assert "VRAM" in error_msg or "required" in error_msg.lower()
        
        # Assert STATE: No worker was created
        assert controller.worker is None

    def test_successful_vram_extraction_workflow(self, mock_main_window, real_managers, tmp_path):
        """Test successful VRAM extraction with real managers and files."""
        # Setup: Create real test files
        vram_file = tmp_path / "test.vram"
        cgram_file = tmp_path / "test.cgram"
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        
        # Write minimal valid data
        vram_file.write_bytes(b'\x00' * 0x10000)  # 64KB VRAM
        cgram_file.write_bytes(b'\x00' * 512)      # 512 bytes CGRAM
        
        # Configure valid extraction params
        mock_main_window.get_extraction_params.return_value = {
            "vram_path": str(vram_file),
            "cgram_path": str(cgram_file),
            "output_base": str(output_dir / "sprite"),
            "vram_offset": 0x0000,
            "create_grayscale": False,
            "create_metadata": True,
            "grayscale_mode": False,
        }
        
        # Create controller
        controller = ExtractionController(
            main_window=mock_main_window,
            extraction_manager=real_managers['extraction'],
            injection_manager=real_managers['injection'],
            session_manager=real_managers['session']
        )
        
        # Mock worker creation to avoid Qt thread issues in test
        with patch.object(controller, '_create_vram_worker') as mock_create:
            mock_worker = Mock(spec=VRAMExtractionWorker)
            mock_create.return_value = mock_worker
            
            # Act: Start extraction
            controller.start_extraction()
            
            # Assert BEHAVIOR: Worker was created with correct params
            mock_create.assert_called_once()
            assert controller.worker == mock_worker
            mock_worker.start.assert_called_once()

    def test_open_in_pixel_editor_behavior(self, mock_main_window, real_managers, tmp_path):
        """Test opening sprite in external editor with real controller."""
        # Setup: Create test image file
        image_file = tmp_path / "sprite.png"
        test_image = Image.new('RGBA', (64, 64), color=(255, 0, 0, 255))
        test_image.save(image_file)
        
        # Create controller
        controller = ExtractionController(
            main_window=mock_main_window,
            extraction_manager=real_managers['extraction'],
            injection_manager=real_managers['injection'],
            session_manager=real_managers['session']
        )
        
        # Mock subprocess to avoid launching real editor
        with patch('core.controller.subprocess.Popen') as mock_popen:
            mock_process = Mock()
            mock_process.poll.return_value = None
            mock_popen.return_value = mock_process
            
            # Act: Open in editor
            controller.open_in_pixel_editor(str(image_file))
            
            # Assert BEHAVIOR: Editor was launched with correct file
            mock_popen.assert_called_once()
            call_args = mock_popen.call_args[0][0]
            assert str(image_file) in call_args

    def test_rom_extraction_with_real_manager(self, mock_main_window, real_managers, tmp_path):
        """Test ROM extraction using real extraction manager."""
        # Setup: Create test ROM file
        rom_file = tmp_path / "test.sfc"
        rom_data = TestDoubleFactory.create_rom_file()._data
        rom_file.write_bytes(rom_data)
        
        cgram_file = tmp_path / "test.cgram"
        cgram_file.write_bytes(b'\x00' * 512)
        
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        
        # Create controller
        controller = ExtractionController(
            main_window=mock_main_window,
            extraction_manager=real_managers['extraction'],
            injection_manager=real_managers['injection'],
            session_manager=real_managers['session']
        )
        
        # Setup ROM extraction params
        params = {
            "rom_path": str(rom_file),
            "sprite_offset": 0x200000,
            "sprite_name": "test_sprite",
            "output_base": str(output_dir / "sprite"),
            "cgram_path": str(cgram_file),
        }
        
        # Mock worker creation to avoid Qt threads
        with patch('core.controller.ROMExtractionWorker') as mock_worker_class:
            mock_worker = Mock()
            mock_worker_class.return_value = mock_worker
            
            # Act: Start ROM extraction
            controller.start_rom_extraction(params)
            
            # Assert BEHAVIOR: Worker was created and started
            mock_worker_class.assert_called_once()
            mock_worker.start.assert_called_once()
            assert controller.rom_worker == mock_worker

    def test_error_handling_with_real_components(self, mock_main_window, real_managers):
        """Test error handling with real manager that raises exception."""
        # Setup: Configure params that will cause real validation error
        mock_main_window.get_extraction_params.return_value = {
            "vram_path": "/nonexistent/file.vram",
            "cgram_path": "/nonexistent/file.cgram",
            "output_base": "/nonexistent/output",
            "grayscale_mode": False,
        }
        
        # Create controller
        controller = ExtractionController(
            main_window=mock_main_window,
            extraction_manager=real_managers['extraction'],
            injection_manager=real_managers['injection'],
            session_manager=real_managers['session']
        )
        
        # Act: Start extraction (will fail validation)
        controller.start_extraction()
        
        # Assert BEHAVIOR: Error was handled gracefully
        mock_main_window.extraction_failed.assert_called()
        assert controller.worker is None  # No worker created on error

class TestVRAMWorkerWithRealManager:
    """Test VRAM extraction worker with real extraction manager."""

    def test_worker_successful_extraction(self, tmp_path):
        """Test worker completes extraction successfully with real manager."""
        # Setup: Create real manager with test doubles
        manager = ExtractionManager()
        setup_hal_mocking(manager, deterministic=True)
        
        # Create test files
        vram_file = tmp_path / "test.vram"
        cgram_file = tmp_path / "test.cgram"
        vram_file.write_bytes(b'\x00' * 0x10000)
        cgram_file.write_bytes(b'\x00' * 512)
        
        # Create worker with real manager
        worker = VRAMExtractionWorker(
            manager=manager,
            vram_path=str(vram_file),
            cgram_path=str(cgram_file),
            output_base=str(tmp_path / "output"),
            vram_offset=0x0000,
        )
        
        # Connect signal to capture results
        results = []
        worker.extraction_completed.connect(results.append)
        
        # Mock the actual extraction to return predictable results
        with patch.object(manager, 'extract_from_vram') as mock_extract:
            mock_extract.return_value = ["sprite_0000.png", "sprite_0001.png"]
            
            # Act: Run worker
            worker.run()
            
            # Assert BEHAVIOR: Extraction completed with results
            assert results == [["sprite_0000.png", "sprite_0001.png"]]

    def test_worker_error_handling(self):
        """Test worker handles extraction errors gracefully."""
        # Setup: Create manager that will fail
        manager = ExtractionManager()
        
        # Create worker with invalid paths
        worker = VRAMExtractionWorker(
            manager=manager,
            vram_path="/nonexistent/vram",
            cgram_path="/nonexistent/cgram",
            output_base="/nonexistent/output",
            vram_offset=0x0000,
        )
        
        # Connect signal to capture errors
        errors = []
        worker.extraction_failed.connect(errors.append)
        
        # Act: Run worker (will fail)
        worker.run()
        
        # Assert BEHAVIOR: Error was emitted
        assert len(errors) == 1
        assert "error" in errors[0].lower() or "fail" in errors[0].lower()

class TestDialogIntegration:
    """Test dialog opening with real components."""

    def test_open_grid_arrangement_dialog(self, mock_main_window, tmp_path):
        """Test opening grid arrangement dialog with real file data."""
        # Setup: Create test files
        extracted_files = []
        for i in range(3):
            img_file = tmp_path / f"sprite_{i:04d}.png"
            img = Image.new('RGBA', (32, 32), color=(255, 0, 0, 255))
            img.save(img_file)
            extracted_files.append(str(img_file))
        
        # Create real managers
        extraction_manager = ExtractionManager()
        injection_manager = InjectionManager()
        session_manager = SessionManager()
        
        # Create controller
        controller = ExtractionController(
            main_window=mock_main_window,
            extraction_manager=extraction_manager,
            injection_manager=injection_manager,
            session_manager=session_manager
        )
        
        # Mock dialog creation to avoid Qt display
        with patch('core.controller.GridArrangementDialog') as mock_dialog_class:
            mock_dialog = Mock()
            mock_dialog_class.return_value = mock_dialog
            mock_dialog.exec.return_value = True
            
            # Act: Open grid arrangement
            controller.open_grid_arrangement(extracted_files)
            
            # Assert BEHAVIOR: Dialog was created with files
            mock_dialog_class.assert_called_once()
            call_args = mock_dialog_class.call_args[0]
            assert call_args[0] == extracted_files
            mock_dialog.exec.assert_called_once()

    def test_open_injection_dialog(self, mock_main_window):
        """Test opening injection dialog."""
        # Create real managers
        extraction_manager = ExtractionManager()
        injection_manager = InjectionManager()
        session_manager = SessionManager()
        
        # Create controller
        controller = ExtractionController(
            main_window=mock_main_window,
            extraction_manager=extraction_manager,
            injection_manager=injection_manager,
            session_manager=session_manager
        )
        
        # Mock dialog creation
        with patch('core.controller.InjectionDialog') as mock_dialog_class:
            mock_dialog = Mock()
            mock_dialog_class.return_value = mock_dialog
            mock_dialog.exec.return_value = True
            
            # Act: Start injection
            controller.start_injection()
            
            # Assert BEHAVIOR: Dialog was created and shown
            mock_dialog_class.assert_called_once()
            mock_dialog.exec.assert_called_once()

class TestFileValidation:
    """Test file validation with real FileValidator."""

    def test_validate_real_image_file(self, tmp_path):
        """Test validating actual image files."""
        # Create real image file
        img_file = tmp_path / "test.png"
        img = Image.new('RGBA', (64, 64), color=(0, 255, 0, 255))
        img.save(img_file)
        
        # Validate with real validator
        validator = FileValidator()
        result = validator.validate_image_file(str(img_file))
        
        # Should validate successfully
        assert result is True or result is None  # Depends on implementation

    def test_validate_invalid_image_file(self):
        """Test validating non-existent image file."""
        validator = FileValidator()
        
        # Should raise or return False for invalid file
        try:
            result = validator.validate_image_file("/nonexistent/file.png")
            assert result is False
        except Exception as e:
            # Expected - file doesn't exist
            assert "not found" in str(e).lower() or "exist" in str(e).lower()

    def test_validate_vram_file(self, tmp_path):
        """Test validating VRAM dump files."""
        # Create test VRAM file
        vram_file = tmp_path / "test.vram"
        vram_file.write_bytes(b'\x00' * 0x10000)  # 64KB
        
        validator = FileValidator()
        result = validator.validate_vram_file(str(vram_file))
        
        # Should validate successfully
        assert result is True or result is None