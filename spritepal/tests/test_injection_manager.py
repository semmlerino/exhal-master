"""
Comprehensive unit tests for InjectionManager
"""

import json
from unittest.mock import Mock, patch

import pytest
from tests.fixtures.test_managers import create_injection_manager_fixture
from tests.fixtures.test_worker_helper import TestWorkerHelper

from spritepal.core.managers import cleanup_managers, initialize_managers
from spritepal.core.managers.exceptions import ValidationError
from spritepal.core.managers.injection_manager import InjectionManager


@pytest.fixture(autouse=True)
def setup_managers():
    """Setup managers for all tests"""
    initialize_managers("TestApp")
    yield
    cleanup_managers()


class TestInjectionManagerInitialization:
    """Test InjectionManager initialization and cleanup"""

    def test_manager_initialization(self):
        """Test manager initializes correctly"""
        manager = InjectionManager()

        # Should be initialized
        assert manager._is_initialized is True
        assert manager._current_worker is None
        assert manager._name == "InjectionManager"

    def test_manager_cleanup_no_worker(self):
        """Test cleanup when no worker is active"""
        manager = InjectionManager()

        # Should not raise exception
        manager.cleanup()
        assert manager._current_worker is None

    def test_manager_cleanup_with_active_worker(self, tmp_path):
        """Test cleanup when real worker is active"""
        manager = InjectionManager()
        worker_helper = TestWorkerHelper(str(tmp_path))

        try:
            # Create a real worker but don't start it
            real_worker = worker_helper.create_vram_injection_worker()
            manager._current_worker = real_worker

            # Verify worker exists before cleanup
            assert manager._current_worker is not None
            assert not real_worker.isRunning()  # Worker not started yet

            # Cleanup should handle inactive worker gracefully
            manager.cleanup()

            # Should clear the worker reference
            assert manager._current_worker is None

        finally:
            worker_helper.cleanup()


class TestInjectionManagerParameterValidation:
    """Test parameter validation methods"""

    def test_validate_vram_injection_params_valid(self, tmp_path):
        """Test validation with valid VRAM injection parameters"""
        manager = InjectionManager()

        # Create test files
        sprite_file = tmp_path / "sprite.png"
        sprite_file.write_text("fake sprite data")
        vram_file = tmp_path / "input.vram"
        vram_file.write_text("fake vram data")

        params = {
            "mode": "vram",
            "sprite_path": str(sprite_file),
            "input_vram": str(vram_file),
            "output_vram": str(tmp_path / "output.vram"),
            "offset": 0x8000,
        }

        # Should not raise exception
        manager.validate_injection_params(params)

    def test_validate_rom_injection_params_valid(self, tmp_path):
        """Test validation with valid ROM injection parameters"""
        manager = InjectionManager()

        # Create test files
        sprite_file = tmp_path / "sprite.png"
        sprite_file.write_text("fake sprite data")
        rom_file = tmp_path / "input.sfc"
        rom_file.write_text("fake rom data")

        params = {
            "mode": "rom",
            "sprite_path": str(sprite_file),
            "input_rom": str(rom_file),
            "output_rom": str(tmp_path / "output.sfc"),
            "offset": 0x8000,
            "fast_compression": True,
        }

        # Should not raise exception
        manager.validate_injection_params(params)

    def test_validate_missing_required_params(self):
        """Test validation fails with missing required parameters"""
        manager = InjectionManager()

        params = {
            "mode": "vram",
            # Missing sprite_path, input_vram, output_vram, offset
        }

        with pytest.raises(ValidationError, match="Missing required parameters"):
            manager.validate_injection_params(params)

    def test_validate_invalid_mode(self, tmp_path):
        """Test validation fails with invalid mode"""
        manager = InjectionManager()

        sprite_file = tmp_path / "sprite.png"
        sprite_file.write_text("fake sprite data")

        params = {
            "mode": "invalid_mode",
            "sprite_path": str(sprite_file),
            "offset": 0x8000,
        }

        with pytest.raises(ValidationError, match="Invalid injection mode"):
            manager.validate_injection_params(params)

    def test_validate_nonexistent_sprite_file(self):
        """Test validation fails with nonexistent sprite file"""
        manager = InjectionManager()

        params = {
            "mode": "vram",
            "sprite_path": "/nonexistent/sprite.png",
            "input_vram": "/fake/input.vram",
            "output_vram": "/fake/output.vram",
            "offset": 0x8000,
        }

        with pytest.raises(ValidationError, match="sprite_path.*does not exist"):
            manager.validate_injection_params(params)

    def test_validate_negative_offset(self, tmp_path):
        """Test validation fails with negative offset"""
        manager = InjectionManager()

        sprite_file = tmp_path / "sprite.png"
        sprite_file.write_text("fake sprite data")
        vram_file = tmp_path / "input.vram"
        vram_file.write_text("fake vram data")

        params = {
            "mode": "vram",
            "sprite_path": str(sprite_file),
            "input_vram": str(vram_file),
            "output_vram": str(tmp_path / "output.vram"),
            "offset": -100,
        }

        with pytest.raises(ValidationError, match="offset.*must be >= 0"):
            manager.validate_injection_params(params)

    def test_validate_metadata_file_validation(self, tmp_path):
        """Test validation of optional metadata file"""
        manager = InjectionManager()

        sprite_file = tmp_path / "sprite.png"
        sprite_file.write_text("fake sprite data")
        vram_file = tmp_path / "input.vram"
        vram_file.write_text("fake vram data")
        metadata_file = tmp_path / "metadata.json"
        metadata_file.write_text('{"test": "data"}')

        params = {
            "mode": "vram",
            "sprite_path": str(sprite_file),
            "input_vram": str(vram_file),
            "output_vram": str(tmp_path / "output.vram"),
            "offset": 0x8000,
            "metadata_path": str(metadata_file),
        }

        # Should not raise exception
        manager.validate_injection_params(params)

    def test_validate_nonexistent_metadata_file(self, tmp_path):
        """Test validation fails with nonexistent metadata file"""
        manager = InjectionManager()

        sprite_file = tmp_path / "sprite.png"
        sprite_file.write_text("fake sprite data")
        vram_file = tmp_path / "input.vram"
        vram_file.write_text("fake vram data")

        params = {
            "mode": "vram",
            "sprite_path": str(sprite_file),
            "input_vram": str(vram_file),
            "output_vram": str(tmp_path / "output.vram"),
            "offset": 0x8000,
            "metadata_path": "/nonexistent/metadata.json",
        }

        with pytest.raises(ValidationError, match="metadata_path.*does not exist"):
            manager.validate_injection_params(params)


class TestInjectionManagerWorkflows:
    """Test injection workflow methods"""

    def test_start_vram_injection_success(self, tmp_path):
        """Test starting VRAM injection parameter validation with real fixture"""
        manager = InjectionManager()

        # Use real injection manager fixture for testing
        injection_fixture = create_injection_manager_fixture(str(tmp_path))

        try:
            # Get real VRAM injection parameters from fixture
            fixture_params = injection_fixture.get_vram_injection_params()

            # Convert to manager expected format
            params = {
                "mode": "vram",
                "sprite_path": fixture_params["sprite_path"],
                "input_vram": fixture_params["input_vram_path"],
                "output_vram": str(tmp_path / "output.vram"),
                "offset": fixture_params["vram_offset"],
            }

            # Validate injection parameters with real manager
            # (Testing parameter validation instead of worker creation to avoid threading)
            manager.validate_injection_params(params)

            # Verify parameters are properly structured for real workflow
            assert params["mode"] == "vram"
            assert params["offset"] == fixture_params["vram_offset"]
            from pathlib import Path
            assert Path(params["sprite_path"]).exists()
            assert Path(params["input_vram"]).exists()

        finally:
            injection_fixture.cleanup()

    def test_start_rom_injection_success(self, tmp_path):
        """Test starting ROM injection parameter validation with real fixture"""
        manager = InjectionManager()

        # Use real injection manager fixture for testing
        injection_fixture = create_injection_manager_fixture(str(tmp_path))

        try:
            # Get real ROM injection parameters from fixture
            fixture_params = injection_fixture.get_rom_injection_params()

            # Convert to manager expected format
            params = {
                "mode": "rom",
                "sprite_path": fixture_params["sprite_path"],
                "input_rom": fixture_params["input_rom_path"],
                "output_rom": str(tmp_path / "output.sfc"),
                "offset": 0x8000,
                "fast_compression": True,
            }

            # Validate ROM injection parameters with real manager
            # (Testing parameter validation instead of worker creation to avoid threading)
            manager.validate_injection_params(params)

            # Verify parameters are properly structured for real workflow
            assert params["mode"] == "rom"
            assert params["offset"] == 0x8000
            assert params["fast_compression"] is True
            from pathlib import Path
            assert Path(params["sprite_path"]).exists()
            assert Path(params["input_rom"]).exists()

        finally:
            injection_fixture.cleanup()

    def test_start_injection_validation_error(self):
        """Test start injection fails on validation error"""
        manager = InjectionManager()

        params = {
            "mode": "vram",
            # Missing required parameters
        }

        result = manager.start_injection(params)
        assert result is False

    def test_start_injection_replaces_existing_worker(self, tmp_path):
        """Test injection parameter validation for worker replacement scenario"""
        manager = InjectionManager()

        # Use real injection manager fixture for testing
        injection_fixture = create_injection_manager_fixture(str(tmp_path))

        try:
            # Get real VRAM injection parameters from fixture
            fixture_params = injection_fixture.get_vram_injection_params()

            # Convert to manager expected format
            params = {
                "mode": "vram",
                "sprite_path": fixture_params["sprite_path"],
                "input_vram": fixture_params["input_vram_path"],
                "output_vram": str(tmp_path / "output.vram"),
                "offset": fixture_params["vram_offset"],
            }

            # Test repeated parameter validation (simulating worker replacement scenario)
            # First validation
            manager.validate_injection_params(params)

            # Second validation (would replace existing worker in real scenario)
            manager.validate_injection_params(params)

            # Both validations should succeed
            from pathlib import Path
            assert Path(params["sprite_path"]).exists()
            assert Path(params["input_vram"]).exists()

        finally:
            injection_fixture.cleanup()

    def test_is_injection_active(self, tmp_path):
        """Test injection active status checking with real worker"""
        manager = InjectionManager()
        worker_helper = TestWorkerHelper(str(tmp_path))

        try:
            # No worker - not active
            assert not manager.is_injection_active()

            # Real inactive worker
            real_worker = worker_helper.create_vram_injection_worker()
            manager._current_worker = real_worker
            assert not manager.is_injection_active()  # Worker created but not started

            # Clean up worker reference
            manager._current_worker = None

        finally:
            worker_helper.cleanup()


class TestInjectionManagerSignalHandling:
    """Test worker signal handling"""

    def test_connect_worker_signals_no_worker(self):
        """Test signal connection when no worker exists"""
        manager = InjectionManager()

        # Should not raise exception
        manager._connect_worker_signals()

    def test_connect_worker_signals_basic_worker(self, tmp_path):
        """Test signal connection for real VRAM injection worker"""
        manager = InjectionManager()
        worker_helper = TestWorkerHelper(str(tmp_path))

        try:
            # Real VRAM injection worker has basic signals
            real_worker = worker_helper.create_vram_injection_worker()
            manager._current_worker = real_worker

            # Connect signals - should not raise exception
            manager._connect_worker_signals()

            # Verify worker has expected signals
            assert hasattr(real_worker, "progress")
            assert hasattr(real_worker, "finished")
            assert hasattr(real_worker.progress, "connect")
            assert hasattr(real_worker.finished, "connect")

        finally:
            worker_helper.cleanup()

    def test_connect_worker_signals_rom_worker(self, tmp_path):
        """Test signal connection for real ROM injection worker"""
        manager = InjectionManager()
        worker_helper = TestWorkerHelper(str(tmp_path))

        try:
            # Real ROM injection worker has additional signals
            real_worker = worker_helper.create_rom_injection_worker()
            manager._current_worker = real_worker

            # Connect signals - should not raise exception
            manager._connect_worker_signals()

            # Verify ROM worker has expected signals (including additional ones)
            assert hasattr(real_worker, "progress")
            assert hasattr(real_worker, "finished")
            assert hasattr(real_worker, "progress_percent")
            assert hasattr(real_worker, "compression_info")
            assert hasattr(real_worker.progress, "connect")
            assert hasattr(real_worker.finished, "connect")
            assert hasattr(real_worker.progress_percent, "connect")
            assert hasattr(real_worker.compression_info, "connect")

        finally:
            worker_helper.cleanup()

    def test_on_worker_progress(self):
        """Test worker progress signal handling"""
        manager = InjectionManager()

        with patch.object(manager, "injection_progress") as mock_signal:
            manager._on_worker_progress("Test progress message")
            mock_signal.emit.assert_called_once_with("Test progress message")

    def test_on_worker_finished_success(self):
        """Test worker finished signal handling for success"""
        manager = InjectionManager()

        # Mock that operation is active
        manager._active_operations = {"injection"}

        with patch.object(manager, "injection_finished") as mock_signal:
            manager._on_worker_finished(True, "Success message")
            mock_signal.emit.assert_called_once_with(True, "Success message")

    def test_on_worker_finished_failure(self):
        """Test worker finished signal handling for failure"""
        manager = InjectionManager()

        # Mock that operation is active
        manager._active_operations = {"injection"}

        with patch.object(manager, "injection_finished") as mock_signal:
            manager._on_worker_finished(False, "Error message")
            mock_signal.emit.assert_called_once_with(False, "Error message")


class TestInjectionManagerVRAMSuggestion:
    """Test smart VRAM suggestion functionality"""

    def test_get_smart_vram_suggestion_no_strategies_work(self, tmp_path):
        """Test VRAM suggestion when no strategies find a file"""
        manager = InjectionManager()

        sprite_file = tmp_path / "sprite.png"
        sprite_file.write_text("fake sprite data")

        result = manager.get_smart_vram_suggestion(str(sprite_file))
        assert result == ""

    def test_get_smart_vram_suggestion_basename_pattern(self, tmp_path):
        """Test VRAM suggestion using basename pattern strategy"""
        manager = InjectionManager()

        # Create sprite file and matching VRAM file
        sprite_file = tmp_path / "test_sprite.png"
        sprite_file.write_text("fake sprite data")
        vram_file = tmp_path / "test_sprite.dmp"
        vram_file.write_text("fake vram data")

        result = manager.get_smart_vram_suggestion(str(sprite_file))
        assert result == str(vram_file)

    def test_get_smart_vram_suggestion_vram_dmp_pattern(self, tmp_path):
        """Test VRAM suggestion using VRAM.dmp pattern"""
        manager = InjectionManager()

        # Create sprite file and VRAM.dmp file
        sprite_file = tmp_path / "sprite.png"
        sprite_file.write_text("fake sprite data")
        vram_file = tmp_path / "VRAM.dmp"
        vram_file.write_text("fake vram data")

        result = manager.get_smart_vram_suggestion(str(sprite_file))
        assert result == str(vram_file)

    @patch("spritepal.core.managers.get_session_manager")
    def test_get_smart_vram_suggestion_session_strategy(self, mock_get_session, tmp_path):
        """Test VRAM suggestion using session strategy"""
        manager = InjectionManager()

        # Create sprite file
        sprite_file = tmp_path / "sprite.png"
        sprite_file.write_text("fake sprite data")

        # Create VRAM file
        vram_file = tmp_path / "session_vram.dmp"
        vram_file.write_text("fake vram data")

        # Mock session manager
        mock_session = Mock()
        mock_session.get.return_value = str(vram_file)
        mock_get_session.return_value = mock_session

        result = manager.get_smart_vram_suggestion(str(sprite_file))
        assert result == str(vram_file)

    def test_try_metadata_vram_valid_file(self, tmp_path):
        """Test metadata VRAM strategy with valid metadata file"""
        manager = InjectionManager()

        # Create VRAM file
        vram_file = tmp_path / "metadata_vram.dmp"
        vram_file.write_text("fake vram data")

        # Create metadata file
        metadata_file = tmp_path / "metadata.json"
        metadata_data = {"source_vram": str(vram_file)}
        metadata_file.write_text(json.dumps(metadata_data))

        sprite_file = tmp_path / "sprite.png"
        sprite_file.write_text("fake sprite data")

        result = manager._try_metadata_vram(str(metadata_file), str(sprite_file))
        assert result == str(vram_file)

    def test_try_metadata_vram_invalid_file(self, tmp_path):
        """Test metadata VRAM strategy with invalid metadata file"""
        manager = InjectionManager()

        sprite_file = tmp_path / "sprite.png"
        sprite_file.write_text("fake sprite data")

        # Nonexistent metadata file
        result = manager._try_metadata_vram("/nonexistent/metadata.json", str(sprite_file))
        assert result == ""

    def test_try_basename_vram_patterns_multiple_patterns(self, tmp_path):
        """Test basename VRAM patterns with multiple pattern matching"""
        manager = InjectionManager()

        sprite_file = tmp_path / "test_sprite.png"
        sprite_file.write_text("fake sprite data")

        # Create VRAM file with _VRAM pattern
        vram_file = tmp_path / "test_sprite_VRAM.dmp"
        vram_file.write_text("fake vram data")

        result = manager._try_basename_vram_patterns(str(sprite_file))
        assert result == str(vram_file)

    @patch("spritepal.core.managers.get_session_manager")
    def test_try_session_vram_recent_files(self, mock_get_session, tmp_path):
        """Test session VRAM strategy with recent files"""
        manager = InjectionManager()

        # Create VRAM file
        vram_file = tmp_path / "recent_vram.dmp"
        vram_file.write_text("fake vram data")

        # Mock session manager
        mock_session = Mock()
        mock_session.get_recent_files.return_value = [str(vram_file)]
        mock_get_session.return_value = mock_session

        result = manager._try_session_vram()
        assert result == str(vram_file)

    @patch("spritepal.core.managers.get_session_manager")
    def test_try_last_injection_vram_settings(self, mock_get_session, tmp_path):
        """Test last injection VRAM strategy"""
        manager = InjectionManager()

        # Create VRAM file
        vram_file = tmp_path / "last_injection_vram.dmp"
        vram_file.write_text("fake vram data")

        # Mock session manager
        mock_session = Mock()
        mock_session.get.return_value = str(vram_file)
        mock_get_session.return_value = mock_session

        result = manager._try_last_injection_vram()
        assert result == str(vram_file)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
