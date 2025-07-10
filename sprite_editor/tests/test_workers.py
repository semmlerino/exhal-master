#!/usr/bin/env python3
"""
Tests for worker threads
Tests background processing with minimal mocking
"""

import os
from unittest.mock import MagicMock, patch

import pytest
from PIL import Image

from sprite_editor.sprite_editor_core import SpriteEditorCore
from sprite_editor.workers.extract_worker import ExtractWorker
from sprite_editor.workers.inject_worker import InjectWorker


@pytest.fixture
def temp_files(tmp_path):
    """Create temporary test files"""
    # Create test VRAM file with pattern
    vram_file = tmp_path / "test.vram"
    vram_data = bytearray(0x10000)  # 64KB
    # Add some tile data pattern
    for i in range(0, 0x10000, 32):
        vram_data[i : i + 32] = bytes([(i // 32) % 16] * 32)
    vram_file.write_bytes(vram_data)

    # Create test CGRAM file with palettes
    cgram_file = tmp_path / "test.cgram"
    cgram_data = bytearray(512)
    # Create simple BGR555 palette
    for i in range(16):
        # Simple gradient palette
        r = (i * 2) & 0x1F
        g = (i * 2) & 0x1F
        b = (i * 2) & 0x1F
        bgr555 = (b << 10) | (g << 5) | r
        cgram_data[i * 2] = bgr555 & 0xFF
        cgram_data[i * 2 + 1] = (bgr555 >> 8) & 0xFF
    cgram_file.write_bytes(cgram_data)

    # Create test PNG file (8x8 valid SNES sprite)
    png_file = tmp_path / "test.png"
    img = Image.new("P", (8, 8))
    # Create simple pattern
    pixels = []
    for y in range(8):
        for x in range(8):
            pixels.append((x + y) % 16)
    img.putdata(pixels)
    img.save(png_file)

    return {
        "vram": str(vram_file),
        "cgram": str(cgram_file),
        "png": str(png_file),
        "dir": str(tmp_path),
    }


@pytest.mark.unit
class TestExtractWorker:
    """Test extract worker thread"""

    def test_worker_initialization(self, temp_files):
        """Test creating extract worker"""
        worker = ExtractWorker(
            temp_files["vram"],
            0xC000,
            0x1000,
            16,
            palette_num=5,
            cgram_file=temp_files["cgram"],
        )

        assert worker.vram_file == temp_files["vram"]
        assert worker.offset == 0xC000
        assert worker.size == 0x1000
        assert worker.tiles_per_row == 16
        assert worker.palette_num == 5
        assert worker.cgram_file == temp_files["cgram"]
        assert isinstance(worker.core, SpriteEditorCore)

    def test_successful_extraction_without_palette(self, temp_files, qtbot):
        """Test successful extraction without palette"""
        worker = ExtractWorker(temp_files["vram"], 0xC000, 0x400, 8)  # 32 tiles

        # Connect signal spies
        finished_spy = qtbot.waitSignal(worker.finished, timeout=1000)

        # Run worker
        worker.run()

        # Verify signals
        assert finished_spy.signal_triggered
        image, tile_count = finished_spy.args
        assert isinstance(image, Image.Image)
        assert tile_count == 32
        assert image.size == (64, 32)  # 8 tiles per row, 4 rows

    def test_successful_extraction_with_palette(self, temp_files, qtbot):
        """Test successful extraction with palette application"""
        worker = ExtractWorker(
            temp_files["vram"],
            0xC000,
            0x400,
            8,
            palette_num=0,
            cgram_file=temp_files["cgram"],
        )

        # Connect signal spies
        finished_spy = qtbot.waitSignal(worker.finished, timeout=1000)
        progress_spy = MagicMock()
        worker.progress.connect(progress_spy)

        # Run worker
        worker.run()

        # Verify signals
        assert finished_spy.signal_triggered
        image, tile_count = finished_spy.args
        assert isinstance(image, Image.Image)
        assert tile_count == 32

        # Check progress messages
        assert progress_spy.call_count >= 2
        progress_messages = [call[0][0] for call in progress_spy.call_args_list]
        assert any("Extracting sprites" in msg for msg in progress_messages)
        assert any("Applying palette" in msg for msg in progress_messages)

    def test_extraction_with_invalid_cgram(self, temp_files, qtbot):
        """Test extraction with non-existent CGRAM file"""
        worker = ExtractWorker(
            temp_files["vram"],
            0xC000,
            0x400,
            8,
            palette_num=0,
            cgram_file="/nonexistent/cgram.dmp",
        )

        # Should still succeed but without palette
        finished_spy = qtbot.waitSignal(worker.finished, timeout=1000)

        worker.run()

        assert finished_spy.signal_triggered
        image, tile_count = finished_spy.args
        assert tile_count == 32

    def test_extraction_error_handling(self, temp_files, qtbot):
        """Test error handling in extraction"""
        worker = ExtractWorker("/nonexistent/vram.dmp", 0xC000, 0x400, 8)

        # Connect error signal
        error_spy = qtbot.waitSignal(worker.error, timeout=1000)

        # Run worker
        worker.run()

        # Verify error signal
        assert error_spy.signal_triggered
        error_msg = error_spy.args[0]
        assert "No such file" in error_msg or "cannot find" in error_msg.lower()

    def test_extraction_with_core_exception(self, temp_files, qtbot):
        """Test handling of core extraction exception"""
        worker = ExtractWorker(temp_files["vram"], 0xC000, 0x400, 8)

        # Mock core to raise exception
        with patch.object(worker.core, "extract_sprites") as mock_extract:
            mock_extract.side_effect = Exception("Test extraction error")

            error_spy = qtbot.waitSignal(worker.error, timeout=1000)

            worker.run()

            assert error_spy.signal_triggered
            assert "Test extraction error" in error_spy.args[0]


@pytest.mark.unit
class TestInjectWorker:
    """Test inject worker thread"""

    def test_worker_initialization(self, temp_files):
        """Test creating inject worker"""
        output_file = os.path.join(temp_files["dir"], "output.vram")
        worker = InjectWorker(
            temp_files["png"], temp_files["vram"], 0xC000, output_file
        )

        assert worker.png_file == temp_files["png"]
        assert worker.vram_file == temp_files["vram"]
        assert worker.offset == 0xC000
        assert worker.output_file == output_file
        assert isinstance(worker.core, SpriteEditorCore)

    def test_successful_injection(self, temp_files, qtbot):
        """Test successful injection workflow"""
        output_file = os.path.join(temp_files["dir"], "output.vram")
        worker = InjectWorker(
            temp_files["png"], temp_files["vram"], 0xC000, output_file
        )

        # Mock core methods for controlled test
        worker.core.validate_png_for_snes = MagicMock(return_value=(True, []))
        worker.core.png_to_snes = MagicMock(return_value=(b"\x00" * 32, 1))
        worker.core.inject_into_vram = MagicMock(return_value=output_file)

        # Connect signal spies
        finished_spy = qtbot.waitSignal(worker.finished, timeout=1000)
        progress_spy = MagicMock()
        worker.progress.connect(progress_spy)

        # Run worker
        worker.run()

        # Verify signals
        assert finished_spy.signal_triggered
        assert finished_spy.args[0] == output_file

        # Verify core method calls
        worker.core.validate_png_for_snes.assert_called_once_with(temp_files["png"])
        worker.core.png_to_snes.assert_called_once_with(temp_files["png"])
        worker.core.inject_into_vram.assert_called_once()

        # Check progress messages
        assert progress_spy.call_count >= 3
        progress_messages = [call[0][0] for call in progress_spy.call_args_list]
        assert any("Validating PNG" in msg for msg in progress_messages)
        assert any("Converting to SNES" in msg for msg in progress_messages)
        assert any("Injecting" in msg for msg in progress_messages)

    def test_injection_validation_failure(self, temp_files, qtbot):
        """Test injection with PNG validation failure"""
        output_file = os.path.join(temp_files["dir"], "output.vram")
        worker = InjectWorker(
            temp_files["png"], temp_files["vram"], 0xC000, output_file
        )

        # Mock validation to fail
        validation_issues = ["Wrong dimensions", "Too many colors"]
        worker.core.validate_png_for_snes = MagicMock(
            return_value=(False, validation_issues)
        )

        # Connect signals
        error_spy = qtbot.waitSignal(worker.error, timeout=1000)
        finished_spy = MagicMock()
        worker.finished.connect(finished_spy)

        # Run worker
        worker.run()

        # Verify error signal
        assert error_spy.signal_triggered
        error_msg = error_spy.args[0]
        assert "PNG validation failed" in error_msg
        assert "Wrong dimensions" in error_msg
        assert "Too many colors" in error_msg

        # Verify finished signal was NOT emitted
        assert finished_spy.call_count == 0

    def test_injection_conversion_error(self, temp_files, qtbot):
        """Test injection with PNG conversion error"""
        output_file = os.path.join(temp_files["dir"], "output.vram")
        worker = InjectWorker(
            temp_files["png"], temp_files["vram"], 0xC000, output_file
        )

        # Mock successful validation but conversion fails
        worker.core.validate_png_for_snes = MagicMock(return_value=(True, []))
        worker.core.png_to_snes = MagicMock(side_effect=Exception("Conversion failed"))

        # Connect error signal
        error_spy = qtbot.waitSignal(worker.error, timeout=1000)

        # Run worker
        worker.run()

        # Verify error signal
        assert error_spy.signal_triggered
        assert "Conversion failed" in error_spy.args[0]

    def test_injection_vram_error(self, temp_files, qtbot):
        """Test injection with VRAM injection error"""
        output_file = os.path.join(temp_files["dir"], "output.vram")
        worker = InjectWorker(
            temp_files["png"], temp_files["vram"], 0xC000, output_file
        )

        # Mock successful validation and conversion but injection fails
        worker.core.validate_png_for_snes = MagicMock(return_value=(True, []))
        worker.core.png_to_snes = MagicMock(return_value=(b"\x00" * 32, 1))
        worker.core.inject_into_vram = MagicMock(
            side_effect=Exception("VRAM write failed")
        )

        # Connect error signal
        error_spy = qtbot.waitSignal(worker.error, timeout=1000)

        # Run worker
        worker.run()

        # Verify error signal
        assert error_spy.signal_triggered
        assert "VRAM write failed" in error_spy.args[0]
