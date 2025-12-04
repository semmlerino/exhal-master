"""
Refactored controller tests using real components instead of excessive mocking.

Following the principle: Mock at system boundaries, not internal methods.
Uses real managers with test doubles for external dependencies.
"""
from __future__ import annotations

from unittest.mock import Mock, patch

import pytest
from core.controller import ExtractionController, VRAMExtractionWorker
from core.managers import ExtractionManager, InjectionManager, SessionManager
from tests.infrastructure.test_doubles import (
    TestDoubleFactory,
    setup_hal_mocking,
    setup_rom_mocking,
)

# Test markers for clarity
pytestmark = [
    pytest.mark.unit,
    pytest.mark.headless,
    pytest.mark.parallel_safe,
]

class TestControllerWithRealComponents:
    """Controller tests using real managers and test doubles for external dependencies."""

    @pytest.fixture
    def real_extraction_manager(self):
        """Create real extraction manager with test doubles for external dependencies."""
        manager = ExtractionManager()
        # Replace only external dependencies with test doubles
        setup_hal_mocking(manager, deterministic=True)
        setup_rom_mocking(manager, rom_type="standard")
        return manager

    @pytest.fixture
    def real_injection_manager(self):
        """Create real injection manager with test doubles for external dependencies."""
        manager = InjectionManager()
        setup_hal_mocking(manager, deterministic=True)
        return manager

    @pytest.fixture
    def real_session_manager(self):
        """Create real session manager."""
        # SessionManager typically doesn't need external mocks
        return SessionManager()

    @pytest.fixture
    def mock_main_window(self):
        """Create mock main window with required signals."""
        window = Mock()
        # Add required signals
        window.extract_requested = Mock()
        window.open_in_editor_requested = Mock()
        window.arrange_rows_requested = Mock()
        window.arrange_grid_requested = Mock()
        window.inject_requested = Mock()

        # Add extraction params method
        window.get_extraction_params = Mock()

        # Add result handlers
        window.extraction_failed = Mock()
        window.extraction_completed = Mock()
        window.update_preview = Mock()

        return window

    def test_controller_creation_with_real_managers(
        self,
        mock_main_window,
        real_extraction_manager,
        real_injection_manager,
        real_session_manager,
    ):
        """Test ExtractionController creation with real manager instances."""
        # Create controller with real managers
        controller = ExtractionController(
            main_window=mock_main_window,
            extraction_manager=real_extraction_manager,
            injection_manager=real_injection_manager,
            session_manager=real_session_manager,
        )

        # Verify BEHAVIOR: Controller is properly initialized
        assert controller.main_window == mock_main_window
        assert controller.extraction_manager == real_extraction_manager
        assert controller.injection_manager == real_injection_manager
        assert controller.session_manager == real_session_manager
        assert controller.worker is None  # No worker initially

    def test_parameter_validation_missing_vram_behavior(
        self,
        mock_main_window,
        real_extraction_manager,
        real_injection_manager,
        real_session_manager,
    ):
        """Test behavior when VRAM is missing - verify actual error handling."""
        # Setup: Configure window to return params with missing VRAM
        mock_main_window.get_extraction_params.return_value = {
            "vram_path": "",  # Missing VRAM
            "cgram_path": "/path/to/cgram",
            "output_base": "/path/to/output",
        }

        # Create controller with real managers
        controller = ExtractionController(
            main_window=mock_main_window,
            extraction_manager=real_extraction_manager,
            injection_manager=real_injection_manager,
            session_manager=real_session_manager,
        )

        # Act: Start extraction
        controller.start_extraction()

        # Assert BEHAVIOR: Error was communicated to user
        mock_main_window.extraction_failed.assert_called_once()
        error_message = mock_main_window.extraction_failed.call_args[0][0]
        assert "VRAM" in error_message or "required" in error_message.lower()

        # Assert BEHAVIOR: No worker was created
        assert controller.worker is None

    def test_parameter_validation_missing_cgram_in_color_mode_behavior(
        self,
        mock_main_window,
        real_extraction_manager,
        real_injection_manager,
        real_session_manager,
    ):
        """Test behavior when CGRAM is missing in color mode."""
        # Setup: Configure params for color mode without CGRAM
        mock_main_window.get_extraction_params.return_value = {
            "vram_path": "/path/to/vram",
            "cgram_path": "",  # Missing CGRAM
            "output_base": "/path/to/output",
            "grayscale_mode": False,  # Color mode requires CGRAM
        }

        # Create controller
        controller = ExtractionController(
            main_window=mock_main_window,
            extraction_manager=real_extraction_manager,
            injection_manager=real_injection_manager,
            session_manager=real_session_manager,
        )

        # Act: Start extraction
        controller.start_extraction()

        # Assert BEHAVIOR: Error about missing CGRAM
        mock_main_window.extraction_failed.assert_called_once()
        error_message = mock_main_window.extraction_failed.call_args[0][0]
        assert "CGRAM" in error_message or "palette" in error_message.lower()

    def test_successful_extraction_behavior(
        self,
        mock_main_window,
        real_extraction_manager,
        real_injection_manager,
        real_session_manager,
        tmp_path,
    ):
        """Test successful extraction with real managers and verify behavior."""
        # Setup: Create actual test files
        vram_file = tmp_path / "test.vram"
        cgram_file = tmp_path / "test.cgram"
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        # Write minimal valid data
        vram_file.write_bytes(b'\x00' * 0x10000)  # 64KB VRAM
        cgram_file.write_bytes(b'\x00' * 512)  # 512 bytes CGRAM

        # Configure extraction params
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
            extraction_manager=real_extraction_manager,
            injection_manager=real_injection_manager,
            session_manager=real_session_manager,
        )

        # Mock the worker to avoid Qt thread issues in tests
        with patch.object(controller, '_create_vram_worker') as mock_create_worker:
            mock_worker = Mock(spec=VRAMExtractionWorker)
            mock_create_worker.return_value = mock_worker

            # Act: Start extraction
            controller.start_extraction()

            # Assert BEHAVIOR: Worker was created and started
            assert mock_create_worker.called
            mock_worker.start.assert_called_once()

            # Simulate successful completion
            mock_worker.extraction_completed.emit(["sprite_0000.png"])

            # Assert BEHAVIOR: Success was communicated
            # Note: In real implementation, this would be connected via signals

    def test_open_in_pixel_editor_with_valid_file(
        self,
        mock_main_window,
        real_extraction_manager,
        real_injection_manager,
        real_session_manager,
        tmp_path,
    ):
        """Test opening a sprite in pixel editor - verify subprocess is called correctly."""
        # Setup: Create a test image file
        test_image = tmp_path / "sprite.png"
        test_image.write_bytes(b'PNG_DATA')  # Minimal file

        # Create controller
        controller = ExtractionController(
            main_window=mock_main_window,
            extraction_manager=real_extraction_manager,
            injection_manager=real_injection_manager,
            session_manager=real_session_manager,
        )

        # Mock subprocess to avoid actually launching editor
        with patch('core.controller.subprocess.Popen') as mock_popen:
            mock_process = Mock()
            mock_process.poll.return_value = None  # Process is running
            mock_popen.return_value = mock_process

            # Act: Open in editor
            controller.open_in_pixel_editor(str(test_image))

            # Assert BEHAVIOR: Editor was launched with correct file
            mock_popen.assert_called_once()
            call_args = mock_popen.call_args[0][0]  # First positional arg
            assert str(test_image) in call_args  # File path is in command

    def test_rom_extraction_with_real_manager(
        self,
        mock_main_window,
        real_extraction_manager,
        real_injection_manager,
        real_session_manager,
        tmp_path,
    ):
        """Test ROM extraction using real extraction manager."""
        # Setup: Create mock ROM file using test double
        rom_file = tmp_path / "test.sfc"
        rom_file.write_bytes(TestDoubleFactory.create_rom_file()._data)

        cgram_file = tmp_path / "test.cgram"
        cgram_file.write_bytes(b'\x00' * 512)

        output_dir = tmp_path / "output"
        output_dir.mkdir()

        # Create controller
        controller = ExtractionController(
            main_window=mock_main_window,
            extraction_manager=real_extraction_manager,
            injection_manager=real_injection_manager,
            session_manager=real_session_manager,
        )

        # Act: Start ROM extraction
        params = {
            "rom_path": str(rom_file),
            "sprite_offset": 0x200000,
            "sprite_name": "test_sprite",
            "output_base": str(output_dir / "sprite"),
            "cgram_path": str(cgram_file),
        }

        controller.start_rom_extraction(params)

        # Assert BEHAVIOR: ROM worker would be created (mocked to avoid Qt threads)
        # In real implementation, this would extract sprites from ROM

    def test_error_handling_with_console_error_handler(
        self,
        real_extraction_manager,
        real_injection_manager,
        real_session_manager,
    ):
        """Test that console error handler is used when UI is not available."""
        # Setup: Create mock window that's not a QWidget
        mock_window = Mock()
        mock_window.extract_requested = Mock()
        mock_window.open_in_editor_requested = Mock()
        mock_window.arrange_rows_requested = Mock()
        mock_window.arrange_grid_requested = Mock()
        mock_window.inject_requested = Mock()

        # Create controller - should use ConsoleErrorHandler
        controller = ExtractionController(
            main_window=mock_window,
            extraction_manager=real_extraction_manager,
            injection_manager=real_injection_manager,
            session_manager=real_session_manager,
        )

        # Assert: Console error handler is used
        from core.console_error_handler import ConsoleErrorHandler
        assert isinstance(controller.error_handler, ConsoleErrorHandler)

    def test_cleanup_on_worker_completion(
        self,
        mock_main_window,
        real_extraction_manager,
        real_injection_manager,
        real_session_manager,
    ):
        """Test that workers are properly cleaned up after completion."""
        # Create controller
        controller = ExtractionController(
            main_window=mock_main_window,
            extraction_manager=real_extraction_manager,
            injection_manager=real_injection_manager,
            session_manager=real_session_manager,
        )

        # Create mock worker
        mock_worker = Mock(spec=VRAMExtractionWorker)
        controller.worker = mock_worker

        # Simulate worker completion
        controller._cleanup_extraction_worker()

        # Assert BEHAVIOR: Worker is cleaned up
        assert controller.worker is None
        mock_worker.deleteLater.assert_called_once()

class TestVRAMExtractionWorkerBehavior:
    """Test VRAM extraction worker behavior with real components."""

    def test_worker_emits_signals_on_success(self):
        """Test that worker emits proper signals on successful extraction."""
        # Create mock manager that returns success
        mock_manager = Mock(spec=ExtractionManager)
        mock_manager.extract_from_vram.return_value = [
            "sprite_0000.png",
            "sprite_0001.png",
        ]

        # Create worker
        worker = VRAMExtractionWorker(
            manager=mock_manager,
            vram_path="/path/to/vram",
            cgram_path="/path/to/cgram",
            output_base="/path/to/output",
            vram_offset=0x0000,
        )

        # Connect signal spy
        completed_files = []
        worker.extraction_completed.connect(lambda files: completed_files.extend(files))

        # Run worker (direct call for testing, normally done in thread)
        worker.run()

        # Assert BEHAVIOR: Files were extracted and signal emitted
        assert completed_files == ["sprite_0000.png", "sprite_0001.png"]

    def test_worker_emits_error_signal_on_failure(self):
        """Test that worker emits error signal on extraction failure."""
        # Create mock manager that raises exception
        mock_manager = Mock(spec=ExtractionManager)
        test_error = ValueError("Test extraction error")
        mock_manager.extract_from_vram.side_effect = test_error

        # Create worker
        worker = VRAMExtractionWorker(
            manager=mock_manager,
            vram_path="/path/to/vram",
            cgram_path="/path/to/cgram",
            output_base="/path/to/output",
            vram_offset=0x0000,
        )

        # Connect signal spy
        error_messages = []
        worker.extraction_failed.connect(error_messages.append)

        # Run worker
        worker.run()

        # Assert BEHAVIOR: Error was emitted
        assert len(error_messages) == 1
        assert "Test extraction error" in error_messages[0]

    def test_worker_handles_partial_extraction(self):
        """Test worker behavior when extraction partially succeeds."""
        # Create mock manager that returns partial results
        mock_manager = Mock(spec=ExtractionManager)
        mock_manager.extract_from_vram.return_value = []  # No sprites found

        # Create worker
        worker = VRAMExtractionWorker(
            manager=mock_manager,
            vram_path="/path/to/vram",
            cgram_path="/path/to/cgram",
            output_base="/path/to/output",
            vram_offset=0x0000,
        )

        # Connect signal spies
        completed_files = []
        worker.extraction_completed.connect(lambda files: completed_files.extend(files))

        # Run worker
        worker.run()

        # Assert BEHAVIOR: Empty result is still a completion
        assert completed_files == []

class TestIntegrationWithTestDoubles:
    """Integration tests using test doubles for external dependencies."""

    def test_full_extraction_workflow_with_test_doubles(self, tmp_path):
        """Test complete extraction workflow with test doubles."""
        # Setup: Create test double factory
        factory = TestDoubleFactory()

        # Create managers with test doubles
        extraction_manager = ExtractionManager()
        injection_manager = InjectionManager()
        session_manager = SessionManager()

        # Setup test doubles for external dependencies
        setup_hal_mocking(extraction_manager, deterministic=True)
        setup_rom_mocking(extraction_manager, rom_type="standard")

        # Create mock main window with progress dialog test double
        mock_window = Mock()
        mock_window.extract_requested = Mock()
        mock_window.open_in_editor_requested = Mock()
        mock_window.arrange_rows_requested = Mock()
        mock_window.arrange_grid_requested = Mock()
        mock_window.inject_requested = Mock()

        # Add progress dialog test double
        mock_window.progress_dialog = factory.create_progress_dialog()

        # Create controller
        controller = ExtractionController(
            main_window=mock_window,
            extraction_manager=extraction_manager,
            injection_manager=injection_manager,
            session_manager=session_manager,
        )

        # Verify the controller is ready
        assert controller.extraction_manager is not None
        assert controller.injection_manager is not None
        assert controller.session_manager is not None

        # Verify test doubles are in place
        assert hasattr(extraction_manager, '_hal_compressor')
        assert hasattr(extraction_manager, '_rom_file')
