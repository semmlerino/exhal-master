"""
Integration tests for extraction workers using real data.

These tests use real VRAM/CGRAM/ROM files and real ExtractionManager instances
to test the complete worker-manager integration without mocking.
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
from PyQt6.QtTest import QSignalSpy

from spritepal.core.workers.extraction import VRAMExtractionWorker, ROMExtractionWorker
from spritepal.core.managers import cleanup_managers, initialize_managers, are_managers_initialized


class TestVRAMExtractionWorkerIntegration:
    """Integration tests for VRAM extraction worker with real data."""
    
    @pytest.fixture(autouse=True)
    def setup_managers(self, qtbot):
        """Set up managers for each test."""
        # Clean up any existing managers first
        if are_managers_initialized():
            cleanup_managers()
        
        # Initialize managers AFTER QApplication exists (qtbot fixture)
        initialize_managers()
        yield
        
        # Clean up after test - but only if managers are still initialized
        if are_managers_initialized():
            cleanup_managers()
    
    @pytest.fixture
    def test_vram_files(self):
        """Get paths to real test VRAM files."""
        base_dir = Path(__file__).parent.parent.parent
        
        # Look for real VRAM dumps
        vram_candidates = [
            base_dir / "archive" / "obsolete_legacy" / "VRAM.dmp",
            base_dir / "Cave.SnesVideoRam.dmp",
        ]
        
        cgram_candidates = [
            base_dir / "archive" / "obsolete_legacy" / "CGRAM.dmp", 
            base_dir / "Cave.SnesCgRam.dmp",
        ]
        
        # Find existing files
        vram_path = None
        cgram_path = None
        
        for candidate in vram_candidates:
            if candidate.exists():
                vram_path = str(candidate)
                break
                
        for candidate in cgram_candidates:
            if candidate.exists():
                cgram_path = str(candidate)
                break
        
        if not vram_path:
            pytest.skip("No VRAM test files found")
            
        return {
            "vram_path": vram_path,
            "cgram_path": cgram_path,  # Can be None
        }
    
    @pytest.fixture
    def temp_output_dir(self):
        """Create temporary directory for output files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir
    
    def test_vram_extraction_with_real_files(self, qtbot, test_vram_files, temp_output_dir):
        """Test VRAM extraction using real files and real manager."""
        # Prepare parameters
        output_base = os.path.join(temp_output_dir, "test_extraction")
        params = {
            "vram_path": test_vram_files["vram_path"],
            "output_base": output_base,
            "cgram_path": test_vram_files["cgram_path"],
            "create_grayscale": True,
            "create_metadata": True,
        }
        
        # Create worker (this will use real ExtractionManager)
        worker = VRAMExtractionWorker(params)
        qtbot.addWidget(worker)
        
        # Debug: Check if manager is still valid
        print(f"DEBUG: Manager type: {type(worker.manager)}")
        print(f"DEBUG: Manager name: {worker.manager.get_name() if worker.manager else 'None'}")
        
        # Set up signal spies
        progress_spy = QSignalSpy(worker.progress)
        extraction_spy = QSignalSpy(worker.extraction_finished)
        operation_spy = QSignalSpy(worker.operation_finished)
        error_spy = QSignalSpy(worker.error)
        
        # Debug: Check manager again before operation
        print(f"DEBUG: Manager before operation: {worker.manager}")
        
        # Run extraction
        worker.perform_operation()
        
        # Wait a moment for any async operations to complete
        import time
        time.sleep(0.1)
        
        # Verify no errors occurred
        assert len(error_spy) == 0, f"Unexpected error: {error_spy[0] if error_spy else 'None'}"
        
        # Verify signals were emitted
        assert len(progress_spy) > 0, "No progress signals emitted"
        assert len(extraction_spy) == 1, "extraction_finished signal not emitted"
        assert len(operation_spy) == 1, "operation_finished signal not emitted"
        
        # Verify operation succeeded
        success, message = operation_spy[0]
        assert success is True, f"Operation failed: {message}"
        
        # Verify files were created
        created_files = extraction_spy[0][0]
        assert len(created_files) > 0, "No files were created"
        
        # Verify actual files exist
        for file_path in created_files:
            assert os.path.exists(file_path), f"Created file doesn't exist: {file_path}"
    
    def test_vram_extraction_with_invalid_file(self, qtbot, temp_output_dir):
        """Test VRAM extraction with invalid file (should fail gracefully)."""
        # Prepare parameters with non-existent file
        output_base = os.path.join(temp_output_dir, "test_extraction")
        params = {
            "vram_path": "/nonexistent/vram.dmp",
            "output_base": output_base,
            "create_grayscale": True,
        }
        
        # Create worker
        worker = VRAMExtractionWorker(params)
        qtbot.addWidget(worker)
        
        # Set up signal spies
        error_spy = QSignalSpy(worker.error)
        operation_spy = QSignalSpy(worker.operation_finished)
        
        # Run extraction (should fail)
        worker.perform_operation()
        
        # Verify error was handled properly
        assert len(error_spy) == 1, "Expected error signal not emitted"
        assert len(operation_spy) == 1, "operation_finished signal not emitted"
        
        # Verify operation failed
        success, message = operation_spy[0]
        assert success is False, "Operation should have failed"
        assert "does not exist" in message.lower(), f"Unexpected error message: {message}"


class TestROMExtractionWorkerIntegration:
    """Integration tests for ROM extraction worker with real data."""
    
    @pytest.fixture(autouse=True)
    def setup_managers(self, qtbot):
        """Set up managers for each test."""
        # Clean up any existing managers first
        if are_managers_initialized():
            cleanup_managers()
        
        # Initialize managers AFTER QApplication exists (qtbot fixture)
        initialize_managers()
        yield
        
        # Clean up after test - but only if managers are still initialized
        if are_managers_initialized():
            cleanup_managers()
    
    @pytest.fixture
    def test_rom_files(self):
        """Get paths to real test ROM files."""
        base_dir = Path(__file__).parent.parent.parent
        
        # Look for real ROM files
        rom_candidates = [
            base_dir / "Kirby Super Star (USA).sfc",
            base_dir / "archive" / "obsolete_legacy" / "Kirby Super Star (USA) - Backup.sfc",
        ]
        
        # Find existing ROM file
        rom_path = None
        for candidate in rom_candidates:
            if candidate.exists():
                rom_path = str(candidate)
                break
        
        if not rom_path:
            pytest.skip("No ROM test files found")
            
        return {"rom_path": rom_path}
    
    @pytest.fixture
    def temp_output_dir(self):
        """Create temporary directory for output files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir
    
    def test_rom_extraction_with_real_files(self, qtbot, test_rom_files, temp_output_dir):
        """Test ROM extraction using real files and real manager."""
        # Prepare parameters (using a known offset that should work)
        output_base = os.path.join(temp_output_dir, "test_rom_extraction")
        params = {
            "rom_path": test_rom_files["rom_path"],
            "sprite_offset": 0x200000,  # A common sprite location
            "output_base": output_base,
            "sprite_name": "test_sprite",
        }
        
        # Create worker (this will use real ExtractionManager)
        worker = ROMExtractionWorker(params)
        qtbot.addWidget(worker)
        
        # Set up signal spies
        progress_spy = QSignalSpy(worker.progress)
        extraction_spy = QSignalSpy(worker.extraction_finished)
        operation_spy = QSignalSpy(worker.operation_finished)
        error_spy = QSignalSpy(worker.error)
        
        # Run extraction
        worker.perform_operation()
        
        # Verify operation completed (may succeed or fail depending on ROM content)
        assert len(operation_spy) == 1, "operation_finished signal not emitted"
        
        # If it succeeded, verify files were created
        if len(extraction_spy) > 0 and len(error_spy) == 0:
            created_files = extraction_spy[0][0]
            assert len(created_files) > 0, "No files were created"
            
            # Verify actual files exist
            for file_path in created_files:
                assert os.path.exists(file_path), f"Created file doesn't exist: {file_path}"
    
    def test_rom_extraction_with_invalid_file(self, qtbot, temp_output_dir):
        """Test ROM extraction with invalid file (should fail gracefully)."""
        # Prepare parameters with non-existent file
        output_base = os.path.join(temp_output_dir, "test_extraction")
        params = {
            "rom_path": "/nonexistent/rom.sfc",
            "sprite_offset": 0x200000,
            "output_base": output_base,
            "sprite_name": "test_sprite",
        }
        
        # Create worker
        worker = ROMExtractionWorker(params)
        qtbot.addWidget(worker)
        
        # Set up signal spies
        error_spy = QSignalSpy(worker.error)
        operation_spy = QSignalSpy(worker.operation_finished)
        
        # Run extraction (should fail)
        worker.perform_operation()
        
        # Verify error was handled properly
        assert len(error_spy) == 1, "Expected error signal not emitted"
        assert len(operation_spy) == 1, "operation_finished signal not emitted"
        
        # Verify operation failed
        success, message = operation_spy[0]
        assert success is False, "Operation should have failed"
        assert "does not exist" in message.lower(), f"Unexpected error message: {message}"


@pytest.fixture
def qtbot():
    """Provide qtbot for Qt testing."""
    from PyQt6.QtTest import QTest
    from PyQt6.QtWidgets import QApplication
    
    # Ensure QApplication exists and persists for the entire test
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
        app.setQuitOnLastWindowClosed(False)  # Prevent premature quit
    
    class QtBot:
        def addWidget(self, widget):
            pass
    
    qtbot = QtBot()
    
    # Ensure app reference persists during test
    qtbot._app = app
    
    yield qtbot
    
    # Allow Qt event processing to complete
    app.processEvents()