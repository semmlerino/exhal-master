#!/usr/bin/env python3
"""
Test transparency preservation in PNG save/load operations.

This test verifies that transparent pixels (index 0) are preserved when saving
and loading PNG files through the pixel editor's file operations.
"""

import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pytest
from PIL import Image
from PyQt6.QtCore import QEventLoop, QTimer
from PyQt6.QtWidgets import QApplication

from pixel_editor.core.pixel_editor_constants import DEFAULT_GRAYSCALE_PALETTE
from pixel_editor.core.pixel_editor_managers import FileManager
from pixel_editor.core.pixel_editor_models import ImageModel, PaletteModel
from pixel_editor.core.pixel_editor_workers import FileLoadWorker, FileSaveWorker


@pytest.fixture(scope="session")
def qapp():
    """Create QApplication instance for testing"""
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    return app


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def test_image_with_transparency():
    """Create a test image with transparent pixels (index 0)"""
    # Create a simple 8x8 test image with transparent pixels
    image_data = np.array([
        [0, 1, 2, 3, 0, 1, 2, 3],  # Row with transparency (index 0)
        [1, 2, 3, 4, 1, 2, 3, 4],  # Row without transparency
        [2, 3, 4, 5, 2, 3, 4, 5],  # Row without transparency
        [0, 0, 0, 0, 1, 1, 1, 1],  # Row with transparency block
        [3, 4, 5, 6, 3, 4, 5, 6],  # Row without transparency
        [0, 1, 0, 1, 0, 1, 0, 1],  # Alternating transparency
        [4, 5, 6, 7, 4, 5, 6, 7],  # Row without transparency
        [0, 0, 0, 0, 0, 0, 0, 0],  # Full transparency row
    ], dtype=np.uint8)
    
    return image_data


@pytest.fixture
def test_palette():
    """Create a test palette (grayscale)"""
    # Create palette data as flat list (768 values for 256 colors)
    palette_data = []
    for r, g, b in DEFAULT_GRAYSCALE_PALETTE:
        palette_data.extend([r, g, b])
    
    # Pad to 256 colors (768 values total)
    while len(palette_data) < 768:
        palette_data.extend([0, 0, 0])
    
    return palette_data


class TestTransparencyPreservation:
    """Test transparency preservation in save/load operations"""
    
    def test_save_worker_sets_transparency_for_png(self, qapp, temp_dir, test_image_with_transparency, test_palette):
        """Test that FileSaveWorker sets transparency=0 for PNG files"""
        test_file = temp_dir / "test_transparency.png"
        
        # Create save worker
        save_worker = FileSaveWorker(
            image_array=test_image_with_transparency,
            palette=test_palette,
            file_path=test_file
        )
        
        # Use event loop to wait for worker completion
        result = {"success": False, "error": None}
        
        def on_saved(file_path):
            result["success"] = True
            result["saved_path"] = file_path
            
        def on_error(error_msg):
            result["error"] = error_msg
            
        save_worker.saved.connect(on_saved)
        save_worker.error.connect(on_error)
        
        # Start worker and wait for completion
        save_worker.start()
        
        # Wait for worker to complete with timeout
        loop = QEventLoop()
        save_worker.finished.connect(loop.quit)
        timer = QTimer()
        timer.timeout.connect(loop.quit)
        timer.start(5000)  # 5 second timeout
        loop.exec()
        
        save_worker.wait(1000)  # Wait up to 1 second for cleanup
        
        # Verify save was successful
        assert result["success"], f"Save failed: {result.get('error', 'Unknown error')}"
        assert result["error"] is None
        assert test_file.exists()
        
        # Verify the saved PNG has transparency set
        with Image.open(test_file) as img:
            assert img.mode == "P", "Image should be in palette mode"
            assert img.format == "PNG", "Image should be PNG format"
            
            # Check if transparency is set in the image
            transparency = img.info.get("transparency")
            assert transparency == 0, f"Transparency should be set to 0, got {transparency}"
            
            # Verify the image data matches what we saved
            loaded_array = np.array(img)
            np.testing.assert_array_equal(loaded_array, test_image_with_transparency)
    
    def test_load_worker_preserves_transparency(self, qapp, temp_dir, test_image_with_transparency, test_palette):
        """Test that FileLoadWorker preserves transparency when loading PNG files"""
        test_file = temp_dir / "test_transparency_load.png"
        
        # First, create a PNG file with transparency using PIL directly
        pil_image = Image.fromarray(test_image_with_transparency, mode="P")
        pil_image.putpalette(test_palette)
        pil_image.save(test_file, format="PNG", optimize=True, transparency=0)
        
        # Verify the file was created with transparency
        with Image.open(test_file) as img:
            assert img.info.get("transparency") == 0, "Test file should have transparency=0"
        
        # Now test loading with FileLoadWorker
        load_worker = FileLoadWorker(test_file)
        
        result = {"success": False, "error": None, "data": None, "metadata": None}
        
        def on_result(image_data, metadata):
            result["success"] = True
            result["data"] = image_data
            result["metadata"] = metadata
            
        def on_error(error_msg):
            result["error"] = error_msg
            
        load_worker.result.connect(on_result)
        load_worker.error.connect(on_error)
        
        # Start worker and wait for completion
        load_worker.start()
        
        # Wait for worker to complete
        loop = QEventLoop()
        load_worker.finished.connect(loop.quit)
        timer = QTimer()
        timer.timeout.connect(loop.quit)
        timer.start(5000)  # 5 second timeout
        loop.exec()
        
        load_worker.wait(1000)  # Wait up to 1 second for cleanup
        
        # Verify load was successful
        assert result["success"], f"Load failed: {result.get('error', 'Unknown error')}"
        assert result["error"] is None
        assert result["data"] is not None
        assert result["metadata"] is not None
        
        # Verify the loaded data matches the original
        loaded_array = result["data"]
        np.testing.assert_array_equal(loaded_array, test_image_with_transparency)
        
        # Verify metadata contains palette information
        metadata = result["metadata"]
        assert "palette" in metadata
        assert metadata["palette"] is not None
        assert len(metadata["palette"]) == 768  # 256 colors * 3 RGB values
    
    def test_save_load_cycle_preserves_transparency(self, qapp, temp_dir, test_image_with_transparency, test_palette):
        """Test complete save/load cycle preserves transparency"""
        test_file = temp_dir / "test_cycle_transparency.png"
        
        # Create models
        image_model = ImageModel()
        palette_model = PaletteModel()
        
        # Set up initial data
        image_model.data = test_image_with_transparency.copy()
        palette_model.colors = [(r, g, b) for r, g, b in zip(test_palette[::3], test_palette[1::3], test_palette[2::3])]
        
        # Create file manager
        file_manager = FileManager()
        
        # Test save operation
        save_worker = file_manager.save_file(
            image_model=image_model,
            palette_model=palette_model,
            file_path=test_file,
            use_grayscale_palette=True
        )
        
        assert save_worker is not None, "Save worker should be created"
        
        # Wait for save to complete
        save_result = {"success": False, "error": None}
        
        def on_saved(file_path):
            save_result["success"] = True
            
        def on_save_error(error_msg):
            save_result["error"] = error_msg
            
        save_worker.saved.connect(on_saved)
        save_worker.error.connect(on_save_error)
        
        save_worker.start()
        
        # Wait for save completion
        loop = QEventLoop()
        save_worker.finished.connect(loop.quit)
        timer = QTimer()
        timer.timeout.connect(loop.quit)
        timer.start(5000)  # 5 second timeout
        loop.exec()
        
        save_worker.wait(1000)
        
        # Verify save was successful
        assert save_result["success"], f"Save failed: {save_result.get('error', 'Unknown error')}"
        assert test_file.exists()
        
        # Test load operation
        load_worker = file_manager.load_file(test_file)
        
        assert load_worker is not None, "Load worker should be created"
        
        # Wait for load to complete
        load_result = {"success": False, "error": None, "data": None, "metadata": None}
        
        def on_loaded(image_data, metadata):
            load_result["success"] = True
            load_result["data"] = image_data
            load_result["metadata"] = metadata
            
        def on_load_error(error_msg):
            load_result["error"] = error_msg
            
        load_worker.result.connect(on_loaded)
        load_worker.error.connect(on_load_error)
        
        load_worker.start()
        
        # Wait for load completion
        loop = QEventLoop()
        load_worker.finished.connect(loop.quit)
        timer = QTimer()
        timer.timeout.connect(loop.quit)
        timer.start(5000)  # 5 second timeout
        loop.exec()
        
        load_worker.wait(1000)
        
        # Verify load was successful
        assert load_result["success"], f"Load failed: {load_result.get('error', 'Unknown error')}"
        assert load_result["data"] is not None
        
        # Compare original and loaded data
        loaded_array = load_result["data"]
        np.testing.assert_array_equal(loaded_array, test_image_with_transparency, 
                                     "Loaded image data should match original")
        
        # Verify transparency is preserved in the actual file
        with Image.open(test_file) as img:
            assert img.mode == "P", "Saved image should be in palette mode"
            assert img.format == "PNG", "Saved image should be PNG format"
            
            transparency = img.info.get("transparency")
            assert transparency == 0, f"Transparency should be preserved as 0, got {transparency}"
            
            # Check that transparent pixels (index 0) are actually transparent
            img_array = np.array(img)
            transparent_pixels = np.where(img_array == 0)
            original_transparent_pixels = np.where(test_image_with_transparency == 0)
            
            # Verify transparent pixel locations match
            np.testing.assert_array_equal(transparent_pixels[0], original_transparent_pixels[0])
            np.testing.assert_array_equal(transparent_pixels[1], original_transparent_pixels[1])
    
    def test_transparency_with_different_file_formats(self, qapp, temp_dir, test_image_with_transparency, test_palette):
        """Test that transparency is only set for PNG files, not other formats"""
        formats_to_test = [
            ("test.png", "PNG", True),  # PNG should have transparency
            ("test.gif", "GIF", True),  # GIF can have transparency but may not be set the same way
            ("test.bmp", "BMP", False), # BMP doesn't support transparency
        ]
        
        for filename, expected_format, transparency_expected in formats_to_test:
            test_file = temp_dir / filename
            
            # Create save worker
            save_worker = FileSaveWorker(
                image_array=test_image_with_transparency,
                palette=test_palette,
                file_path=test_file
            )
            
            result = {"success": False, "error": None}
            
            def on_saved(file_path):
                result["success"] = True
                
            def on_error(error_msg):
                result["error"] = error_msg
                
            save_worker.saved.connect(on_saved)
            save_worker.error.connect(on_error)
            
            # Start worker and wait for completion
            save_worker.start()
            
            # Wait for worker to complete
            loop = QEventLoop()
            save_worker.finished.connect(loop.quit)
            timer = QTimer()
            timer.timeout.connect(loop.quit)
            timer.start(5000)  # 5 second timeout
            loop.exec()
            
            save_worker.wait(1000)
            
            # Verify save was successful
            assert result["success"], f"Save failed for {filename}: {result.get('error', 'Unknown error')}"
            assert test_file.exists()
            
            # Check file format and transparency
            with Image.open(test_file) as img:
                assert img.format == expected_format, f"File format should be {expected_format}"
                
                if expected_format == "PNG":
                    # PNG should have transparency=0
                    transparency = img.info.get("transparency")
                    assert transparency == 0, f"PNG should have transparency=0, got {transparency}"
                elif expected_format == "GIF":
                    # GIF may or may not have transparency info depending on PIL version
                    # We'll just check that it doesn't crash
                    pass
                elif expected_format == "BMP":
                    # BMP doesn't support transparency
                    transparency = img.info.get("transparency")
                    assert transparency is None, f"BMP should not have transparency, got {transparency}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])