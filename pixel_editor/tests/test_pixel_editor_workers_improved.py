#!/usr/bin/env python3
"""
Comprehensive tests for improved pixel editor workers.
Tests the new file path handling, type validation, and error scenarios.
"""

import json
import os
import sys
import tempfile
from pathlib import Path

import numpy as np
import pytest
from PyQt6.QtWidgets import QApplication

from pixel_editor.core.pixel_editor_managers import FileManager, PaletteManager
from pixel_editor.core.pixel_editor_workers import (
    BaseWorker,
    FileLoadWorker,
    FileSaveWorker,
    PaletteLoadWorker,
)


@pytest.fixture(scope="session")
def qapp():
    """Create QApplication instance for testing"""
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    return app


class TestBaseWorkerPathHandling:
    """Test BaseWorker file path handling improvements"""

    def test_base_worker_accepts_string_path(self, qapp):
        """Test that BaseWorker accepts string paths"""
        worker = BaseWorker("test/path.txt")
        assert worker.file_path == Path("test/path.txt")
        assert isinstance(worker.file_path, Path)

    def test_base_worker_accepts_path_object(self, qapp):
        """Test that BaseWorker accepts Path objects"""
        path_obj = Path("test/path.txt")
        worker = BaseWorker(path_obj)
        assert worker.file_path == path_obj
        assert isinstance(worker.file_path, Path)

    def test_base_worker_no_path(self, qapp):
        """Test BaseWorker with no file path"""
        worker = BaseWorker()
        assert worker.file_path is None

    def test_file_path_is_read_only(self, qapp):
        """Test that file_path property is read-only"""
        worker = BaseWorker("test/path.txt")
        with pytest.raises(AttributeError):
            worker.file_path = "new/path.txt"

    def test_validate_file_path_with_existing_file(self, qapp):
        """Test file path validation with existing file"""
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp_path = tmp.name

        try:
            worker = BaseWorker(tmp_path)
            assert worker.validate_file_path(must_exist=True)
        finally:
            os.unlink(tmp_path)

    def test_validate_file_path_with_missing_file(self, qapp):
        """Test file path validation with missing file"""
        worker = BaseWorker("nonexistent/file.txt")

        error_messages = []
        worker.error.connect(lambda msg: error_messages.append(msg))

        assert not worker.validate_file_path(must_exist=True)
        assert len(error_messages) == 1
        assert "File not found" in error_messages[0]

    def test_validate_file_path_no_existence_check(self, qapp):
        """Test file path validation without existence check"""
        worker = BaseWorker("future/file.txt")
        assert worker.validate_file_path(must_exist=False)

    def test_validate_file_path_with_none(self, qapp):
        """Test file path validation when no path provided"""
        worker = BaseWorker()

        error_messages = []
        worker.error.connect(lambda msg: error_messages.append(msg))

        assert not worker.validate_file_path()
        assert len(error_messages) == 1
        assert "No file path provided" in error_messages[0]


class TestFileLoadWorkerImproved:
    """Test FileLoadWorker with improved path handling"""

    def test_file_load_worker_string_path(self, qapp):
        """Test FileLoadWorker with string path"""
        worker = FileLoadWorker("test.png")
        assert isinstance(worker.file_path, Path)
        assert worker.file_path.name == "test.png"

    def test_file_load_worker_path_object(self, qapp):
        """Test FileLoadWorker with Path object"""
        path = Path("test.png")
        worker = FileLoadWorker(path)
        assert worker.file_path == path

    def test_file_load_worker_cannot_modify_path(self, qapp):
        """Test that file_path cannot be modified after creation"""
        worker = FileLoadWorker("test.png")

        # This should fail - file_path is read-only
        with pytest.raises(AttributeError):
            worker.file_path = "other.png"

    def test_file_load_worker_with_real_image(self, qapp, qtbot):
        """Test loading a real image file"""
        # Create a test image
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            from PIL import Image

            img = Image.new("P", (8, 8))
            img.putpalette([i % 256 for i in range(768)])
            img.save(tmp.name)
            tmp_path = tmp.name

        try:
            worker = FileLoadWorker(tmp_path)

            results = []
            errors = []
            worker.result.connect(lambda data, meta: results.append((data, meta)))
            worker.error.connect(lambda msg: errors.append(msg))

            with qtbot.waitSignal(worker.finished, timeout=2000):
                worker.start()

            assert len(results) == 1
            assert len(errors) == 0

            image_data, metadata = results[0]
            assert image_data.shape == (8, 8)
            assert metadata["width"] == 8
            assert metadata["height"] == 8
        finally:
            os.unlink(tmp_path)

    def test_file_load_worker_nonexistent_file(self, qapp, qtbot):
        """Test loading a nonexistent file"""
        worker = FileLoadWorker("nonexistent.png")

        errors = []
        worker.error.connect(lambda msg: errors.append(msg))

        with qtbot.waitSignal(worker.error, timeout=1000):
            worker.start()

        assert len(errors) == 1
        assert "File not found" in errors[0]


class TestFileSaveWorkerImproved:
    """Test FileSaveWorker with improved path handling"""

    def test_file_save_worker_string_path(self, qapp):
        """Test FileSaveWorker with string path"""
        image_data = np.zeros((8, 8), dtype=np.uint8)
        palette = [0] * 768
        worker = FileSaveWorker(image_data, palette, "output.png")

        assert isinstance(worker.file_path, Path)
        assert worker.file_path.name == "output.png"

    def test_file_save_worker_path_object(self, qapp):
        """Test FileSaveWorker with Path object"""
        image_data = np.zeros((8, 8), dtype=np.uint8)
        palette = [0] * 768
        path = Path("output.png")
        worker = FileSaveWorker(image_data, palette, path)

        assert worker.file_path == path

    def test_file_save_worker_saves_file(self, qapp, qtbot):
        """Test actually saving a file"""
        image_data = np.arange(64).reshape(8, 8).astype(np.uint8) % 16
        palette = [i % 256 for i in range(768)]

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "test_output.png"
            worker = FileSaveWorker(image_data, palette, str(output_path))

            saved_paths = []
            worker.saved.connect(lambda path: saved_paths.append(path))

            with qtbot.waitSignal(worker.saved, timeout=2000):
                worker.start()

            assert len(saved_paths) == 1
            assert saved_paths[0] == str(output_path)
            assert output_path.exists()

            # Verify the saved image
            from PIL import Image

            img = Image.open(output_path)
            assert img.size == (8, 8)
            assert img.mode == "P"


class TestPaletteLoadWorkerImproved:
    """Test PaletteLoadWorker with improved path handling"""

    def test_palette_load_worker_string_path(self, qapp):
        """Test PaletteLoadWorker with string path"""
        worker = PaletteLoadWorker("palette.json")
        assert isinstance(worker.file_path, Path)
        assert worker.file_path.name == "palette.json"

    def test_palette_load_worker_loads_json(self, qapp, qtbot):
        """Test loading a JSON palette file"""
        palette_data = {
            "name": "Test Palette",
            "colors": [[255, 0, 0], [0, 255, 0], [0, 0, 255]] + [[0, 0, 0]] * 13,
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as tmp:
            json.dump(palette_data, tmp)
            tmp_path = tmp.name

        try:
            worker = PaletteLoadWorker(tmp_path)

            results = []
            worker.result.connect(lambda data: results.append(data))

            with qtbot.waitSignal(worker.result, timeout=2000):
                worker.start()

            assert len(results) == 1
            result = results[0]
            assert result["name"] == "Test Palette"
            assert len(result["colors"]) == 16
            assert result["colors"][0] == [255, 0, 0]
        finally:
            os.unlink(tmp_path)


class TestManagersWithPathHandling:
    """Test that managers properly handle Path objects"""

    def test_file_manager_accepts_path_objects(self, qapp):
        """Test FileManager accepts both strings and Path objects"""
        manager = FileManager()

        # Test with string for non-existent file
        worker1 = manager.load_file("nonexistent_test_file_12345.png")
        assert worker1 is None  # File doesn't exist

        # Test with Path object for non-existent file
        path = Path("nonexistent_test_file_67890.png")
        worker2 = manager.load_file(path)
        assert worker2 is None  # File doesn't exist

        # Test with existing file
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            # Test with string path to existing file
            worker3 = manager.load_file(tmp_path)
            assert worker3 is not None
            assert isinstance(worker3, FileLoadWorker)

            # Test with Path object to existing file
            worker4 = manager.load_file(Path(tmp_path))
            assert worker4 is not None
            assert isinstance(worker4, FileLoadWorker)
        finally:
            os.unlink(tmp_path)

    def test_palette_manager_accepts_path_objects(self, qapp):
        """Test PaletteManager accepts both strings and Path objects"""
        manager = PaletteManager()

        # Test with string
        worker1 = manager.load_palette_file("palette.json")
        assert worker1 is None  # File doesn't exist, but no crash

        # Test with Path object
        path = Path("palette.json")
        worker2 = manager.load_palette_file(path)
        assert worker2 is None  # File doesn't exist, but no crash


class TestPathOverwritingBugFix:
    """Test that the path overwriting bug is fixed"""

    def test_worker_path_cannot_be_overwritten(self, qapp):
        """Test that worker's file_path cannot be overwritten like before"""
        worker = FileLoadWorker("original.png")

        # Verify original path
        assert worker.file_path.name == "original.png"

        # Try to overwrite (this was the bug)
        with pytest.raises(AttributeError):
            worker.file_path = "overwritten.png"

        # Verify path is unchanged
        assert worker.file_path.name == "original.png"

    def test_worker_maintains_path_type(self, qapp, qtbot):
        """Test that worker maintains Path type throughout execution"""
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as tmp:
            tmp.write(b"Not an image")
            tmp_path = tmp.name

        try:
            worker = FileLoadWorker(tmp_path)

            # Check type before running
            assert isinstance(worker.file_path, Path)

            errors = []
            worker.error.connect(lambda msg: errors.append(msg))

            # Start the worker
            worker.start()
            qtbot.wait(100)  # Give it time to process

            # Check type after running - should still be Path
            assert isinstance(worker.file_path, Path)

        finally:
            os.unlink(tmp_path)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
