"""
Validation tests for TestWorkerHelper to demonstrate real worker thread behavior
"""

import pytest
from tests.fixtures.test_worker_helper import TestWorkerHelper


class TestWorkerHelperValidation:
    """Test TestWorkerHelper functionality"""

    def test_vram_injection_worker_creation(self, tmp_path):
        """Test TestWorkerHelper creates real VRAM injection workers"""
        helper = TestWorkerHelper(str(tmp_path))

        try:
            # Create real VRAM injection worker
            worker = helper.create_vram_injection_worker()

            # Verify it's a real QThread instance
            from PyQt6.QtCore import QThread
            assert isinstance(worker, QThread)

            # Verify it has the expected signals
            assert hasattr(worker, "progress")
            assert hasattr(worker, "finished")

            # Verify parameters are properly set
            assert worker.sprite_path == str(helper.sprite_file)
            assert worker.vram_input == str(helper.vram_file)
            assert worker.offset == 0xC000

        finally:
            helper.cleanup()

    def test_rom_injection_worker_creation(self, tmp_path):
        """Test TestWorkerHelper creates real ROM injection workers"""
        helper = TestWorkerHelper(str(tmp_path))

        try:
            # Create real ROM injection worker
            worker = helper.create_rom_injection_worker()

            # Verify it's a real QThread instance
            from PyQt6.QtCore import QThread
            assert isinstance(worker, QThread)

            # Verify it has the expected signals (including ROM-specific ones)
            assert hasattr(worker, "progress")
            assert hasattr(worker, "finished")
            assert hasattr(worker, "progress_percent")
            assert hasattr(worker, "compression_info")

            # Verify parameters are properly set
            assert worker.sprite_path == str(helper.sprite_file)
            assert worker.rom_input == str(helper.rom_file)
            assert worker.sprite_offset == 0x8000
            assert worker.fast_compression is True

        finally:
            helper.cleanup()

    @pytest.mark.gui
    def test_worker_with_real_threading(self, tmp_path, qtbot):
        """Test worker with real threading using qtbot"""
        helper = TestWorkerHelper(str(tmp_path))

        try:
            # Create real VRAM injection worker
            worker = helper.create_vram_injection_worker()

            # Track signals
            progress_messages = []
            completion_status = []

            worker.progress.connect(lambda msg: progress_messages.append(msg))
            worker.finished.connect(lambda success, msg: completion_status.append((success, msg)))

            # Use managed worker context for safe execution
            with helper.managed_worker(worker):
                # Start worker as real thread and wait for completion
                with qtbot.waitSignal(worker.finished, timeout=10000):
                    worker.start()

                # Wait for worker to complete
                worker.wait(5000)

            # Verify worker executed and emitted signals
            assert len(progress_messages) > 0
            assert len(completion_status) == 1

            # Note: In a real test environment, the worker might fail due to
            # missing dependencies (HAL tools, etc.), but the threading
            # behavior should work correctly

        finally:
            helper.cleanup()

    def test_test_parameters_structure(self, tmp_path):
        """Test that TestWorkerHelper provides properly structured test parameters"""
        helper = TestWorkerHelper(str(tmp_path))

        try:
            # Test VRAM parameters
            vram_params = helper.get_test_params_vram()
            required_vram_keys = {"mode", "sprite_path", "input_vram", "output_vram", "offset", "metadata_path"}
            assert set(vram_params.keys()) == required_vram_keys
            assert vram_params["mode"] == "vram"
            assert vram_params["offset"] == 0xC000

            # Test ROM parameters
            rom_params = helper.get_test_params_rom()
            required_rom_keys = {"mode", "sprite_path", "input_rom", "output_rom", "offset", "fast_compression", "metadata_path"}
            assert set(rom_params.keys()) == required_rom_keys
            assert rom_params["mode"] == "rom"
            assert rom_params["offset"] == 0x8000
            assert rom_params["fast_compression"] is True

        finally:
            helper.cleanup()
