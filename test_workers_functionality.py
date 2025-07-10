#!/usr/bin/env python3
"""
Focused tests for pixel editor worker threads.

Tests:
- FileLoadWorker can load images
- FileSaveWorker can save images
- PaletteLoadWorker can load palettes
- Progress signals work correctly
- Cancellation works
- Error handling works
"""

import sys
import os
import tempfile
import json
from pathlib import Path
from unittest.mock import MagicMock
import numpy as np
from PIL import Image

# Simple Qt application setup for testing
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QObject, QEventLoop, QTimer

# Import the workers to test
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pixel_editor_workers import FileLoadWorker, FileSaveWorker, PaletteLoadWorker


class WorkerTester(QObject):
    """Helper class to test worker signals"""
    
    def __init__(self):
        super().__init__()
        self.signals_received = {
            'progress': [],
            'error': [],
            'finished': False,
            'result': None,
            'saved': None
        }
        
    def on_progress(self, value):
        self.signals_received['progress'].append(value)
        
    def on_error(self, message):
        self.signals_received['error'].append(message)
        
    def on_finished(self):
        self.signals_received['finished'] = True
        
    def on_result(self, *args):
        self.signals_received['result'] = args
        
    def on_saved(self, path):
        self.signals_received['saved'] = path
        
    def reset(self):
        self.signals_received = {
            'progress': [],
            'error': [],
            'finished': False,
            'result': None,
            'saved': None
        }


def create_test_image(path, width=32, height=32):
    """Create a test indexed image"""
    # Create indexed image
    img = Image.new('P', (width, height))
    
    # Create test pattern
    pixels = []
    for y in range(height):
        for x in range(width):
            pixels.append((x + y) % 256)
    
    img.putdata(pixels)
    
    # Set a palette
    palette = []
    for i in range(256):
        palette.extend([i, 255-i, i//2])  # R, G, B
    img.putpalette(palette)
    
    img.save(str(path), 'PNG')
    return path


def create_test_palette_json(path):
    """Create a test palette JSON file"""
    palette_data = {
        'name': 'Test Palette',
        'colors': []
    }
    
    # Create 16 test colors
    for i in range(16):
        r = (i * 16) % 256
        g = (255 - i * 16) % 256
        b = (i * 8) % 256
        palette_data['colors'].append([r, g, b])
    
    with open(path, 'w') as f:
        json.dump(palette_data, f)
    
    return path


def create_test_palette_pal(path):
    """Create a test PAL/ACT palette file"""
    # 256 colors * 3 bytes each = 768 bytes
    palette_data = bytearray()
    for i in range(256):
        r = (i * 2) % 256
        g = (255 - i) % 256
        b = (i // 2) % 256
        palette_data.extend([r, g, b])
    
    with open(path, 'wb') as f:
        f.write(palette_data)
    
    return path


def create_test_palette_gpl(path):
    """Create a test GIMP palette file"""
    with open(path, 'w') as f:
        f.write("GIMP Palette\n")
        f.write("Name: Test GIMP Palette\n")
        f.write("#\n")
        
        # Write 16 colors
        for i in range(16):
            r = (i * 16) % 256
            g = (255 - i * 16) % 256
            b = (i * 8) % 256
            f.write(f"{r:3d} {g:3d} {b:3d}   Color {i}\n")
    
    return path


def wait_for_worker(worker, timeout_ms=5000):
    """Wait for worker to finish with timeout"""
    loop = QEventLoop()
    worker.finished.connect(loop.quit)
    worker.error.connect(lambda msg: loop.quit())
    
    # Setup timeout
    timer = QTimer()
    timer.timeout.connect(loop.quit)
    timer.start(timeout_ms)
    
    # Start worker and wait
    worker.start()
    loop.exec()
    
    # Cleanup
    timer.stop()
    worker.wait()


def test_file_load_worker(temp_dir):
    """Test FileLoadWorker functionality"""
    print("\n=== Testing FileLoadWorker ===")
    
    # Create test image
    test_image_path = Path(temp_dir) / "test_load.png"
    create_test_image(test_image_path)
    
    # Setup tester
    tester = WorkerTester()
    
    # Test 1: Successful load
    print("Test 1: Successful image load")
    worker = FileLoadWorker(str(test_image_path))
    worker.progress.connect(tester.on_progress)
    worker.error.connect(tester.on_error)
    worker.finished.connect(tester.on_finished)
    worker.result.connect(tester.on_result)
    
    wait_for_worker(worker)
    
    assert tester.signals_received['finished'], "Worker should finish successfully"
    assert len(tester.signals_received['error']) == 0, f"No errors expected, got: {tester.signals_received['error']}"
    assert tester.signals_received['result'] is not None, "Should have result"
    
    image_array, metadata = tester.signals_received['result']
    assert isinstance(image_array, np.ndarray), "Result should contain numpy array"
    assert image_array.shape == (32, 32), "Image should be 32x32"
    assert metadata['width'] == 32, "Metadata should contain correct width"
    assert metadata['height'] == 32, "Metadata should contain correct height"
    assert 'palette' in metadata, "Metadata should contain palette"
    
    # Check progress signals
    progress_values = tester.signals_received['progress']
    assert len(progress_values) > 0, "Should emit progress signals"
    assert progress_values[0] == 0, "Should start at 0%"
    assert progress_values[-1] == 100, "Should end at 100%"
    print(f"✓ Successful load test passed. Progress: {progress_values}")
    
    # Test 2: Non-existent file
    print("\nTest 2: Non-existent file")
    tester.reset()
    worker = FileLoadWorker("/non/existent/file.png")
    worker.error.connect(tester.on_error)
    worker.finished.connect(tester.on_finished)
    
    wait_for_worker(worker)
    
    assert len(tester.signals_received['error']) > 0, "Should emit error for non-existent file"
    assert "File not found" in tester.signals_received['error'][0], "Error should mention file not found"
    assert not tester.signals_received['finished'], "Should not finish successfully"
    print(f"✓ Non-existent file test passed. Error: {tester.signals_received['error'][0]}")
    
    # Test 3: Cancellation
    print("\nTest 3: Cancellation")
    tester.reset()
    worker = FileLoadWorker(str(test_image_path))
    worker.progress.connect(tester.on_progress)
    worker.finished.connect(tester.on_finished)
    
    # Start and immediately cancel
    worker.start()
    worker.cancel()
    worker.wait()
    
    assert not tester.signals_received['finished'], "Cancelled worker should not emit finished"
    print("✓ Cancellation test passed")
    
    return True


def test_file_save_worker(temp_dir):
    """Test FileSaveWorker functionality"""
    print("\n=== Testing FileSaveWorker ===")
    
    # Create test data
    test_array = np.zeros((16, 16), dtype=np.uint8)
    for y in range(16):
        for x in range(16):
            test_array[y, x] = (x + y) % 16
    
    test_palette = []
    for i in range(256):
        test_palette.extend([i, 255-i, i//2])
    
    # Setup tester
    tester = WorkerTester()
    
    # Test 1: Successful save
    print("Test 1: Successful image save")
    save_path = Path(temp_dir) / "test_save.png"
    
    worker = FileSaveWorker(test_array, test_palette, str(save_path))
    worker.progress.connect(tester.on_progress)
    worker.error.connect(tester.on_error)
    worker.finished.connect(tester.on_finished)
    worker.saved.connect(tester.on_saved)
    
    wait_for_worker(worker)
    
    assert tester.signals_received['finished'], "Worker should finish successfully"
    assert len(tester.signals_received['error']) == 0, f"No errors expected, got: {tester.signals_received['error']}"
    assert tester.signals_received['saved'] == str(save_path), "Should emit saved signal with path"
    assert save_path.exists(), "File should be created"
    
    # Verify saved file
    saved_img = Image.open(save_path)
    assert saved_img.size == (16, 16), "Saved image should be 16x16"
    assert saved_img.mode == 'P', "Saved image should be indexed"
    
    # Check progress
    progress_values = tester.signals_received['progress']
    assert progress_values[0] == 0 and progress_values[-1] == 100, "Progress should go from 0 to 100"
    print(f"✓ Successful save test passed. Progress: {progress_values}")
    
    # Test 2: Invalid palette
    print("\nTest 2: Invalid palette")
    tester.reset()
    invalid_palette = [0, 1, 2]  # Too short
    
    worker = FileSaveWorker(test_array, invalid_palette, str(save_path))
    worker.error.connect(tester.on_error)
    worker.finished.connect(tester.on_finished)
    
    wait_for_worker(worker)
    
    assert len(tester.signals_received['error']) > 0, "Should emit error for invalid palette"
    assert "Invalid palette" in tester.signals_received['error'][0], "Error should mention invalid palette"
    print(f"✓ Invalid palette test passed. Error: {tester.signals_received['error'][0]}")
    
    # Test 3: Different formats
    print("\nTest 3: Different file formats")
    formats = ['.gif', '.bmp', '.tiff']
    
    for fmt in formats:
        tester.reset()
        save_path = Path(temp_dir) / f"test_save{fmt}"
        
        worker = FileSaveWorker(test_array, test_palette, str(save_path))
        worker.finished.connect(tester.on_finished)
        worker.error.connect(tester.on_error)
        
        wait_for_worker(worker)
        
        assert tester.signals_received['finished'], f"Should save {fmt} successfully"
        assert save_path.exists(), f"{fmt} file should exist"
        print(f"✓ {fmt} format test passed")
    
    return True


def test_palette_load_worker(temp_dir):
    """Test PaletteLoadWorker functionality"""
    print("\n=== Testing PaletteLoadWorker ===")
    
    # Setup tester
    tester = WorkerTester()
    
    # Test 1: JSON palette
    print("Test 1: JSON palette loading")
    json_path = Path(temp_dir) / "test_palette.json"
    create_test_palette_json(json_path)
    
    worker = PaletteLoadWorker(str(json_path))
    worker.progress.connect(tester.on_progress)
    worker.error.connect(tester.on_error)
    worker.finished.connect(tester.on_finished)
    worker.result.connect(tester.on_result)
    
    wait_for_worker(worker)
    
    assert tester.signals_received['finished'], "Worker should finish successfully"
    assert len(tester.signals_received['error']) == 0, f"No errors expected, got: {tester.signals_received['error']}"
    
    palette_data = tester.signals_received['result'][0]
    assert 'colors' in palette_data, "Should have colors field"
    assert len(palette_data['colors']) == 16, "Should have 16 colors"
    assert palette_data['name'] == 'Test Palette', "Should have correct name"
    print("✓ JSON palette test passed")
    
    # Test 2: PAL/ACT palette
    print("\nTest 2: PAL/ACT palette loading")
    tester.reset()
    pal_path = Path(temp_dir) / "test_palette.pal"
    create_test_palette_pal(pal_path)
    
    worker = PaletteLoadWorker(str(pal_path))
    worker.finished.connect(tester.on_finished)
    worker.result.connect(tester.on_result)
    worker.error.connect(tester.on_error)
    
    wait_for_worker(worker)
    
    assert tester.signals_received['finished'], "Worker should finish successfully"
    palette_data = tester.signals_received['result'][0]
    assert len(palette_data['colors']) == 256, "Should have 256 colors"
    assert palette_data['format'] == 'ACT', "Should identify as ACT format"
    print("✓ PAL/ACT palette test passed")
    
    # Test 3: GIMP palette
    print("\nTest 3: GIMP palette loading")
    tester.reset()
    gpl_path = Path(temp_dir) / "test_palette.gpl"
    create_test_palette_gpl(gpl_path)
    
    worker = PaletteLoadWorker(str(gpl_path))
    worker.finished.connect(tester.on_finished)
    worker.result.connect(tester.on_result)
    worker.error.connect(tester.on_error)
    
    wait_for_worker(worker)
    
    assert tester.signals_received['finished'], "Worker should finish successfully"
    palette_data = tester.signals_received['result'][0]
    assert len(palette_data['colors']) == 16, "Should have 16 colors"
    assert palette_data['format'] == 'GIMP', "Should identify as GIMP format"
    assert palette_data['name'] == 'Test GIMP Palette', "Should have correct name"
    print("✓ GIMP palette test passed")
    
    # Test 4: Unsupported format
    print("\nTest 4: Unsupported format")
    tester.reset()
    bad_path = Path(temp_dir) / "test_palette.xyz"
    bad_path.write_text("Some data")
    
    worker = PaletteLoadWorker(str(bad_path))
    worker.error.connect(tester.on_error)
    worker.finished.connect(tester.on_finished)
    
    wait_for_worker(worker)
    
    assert len(tester.signals_received['error']) > 0, "Should emit error for unsupported format"
    assert "Unsupported palette format" in tester.signals_received['error'][0], "Error should mention unsupported format"
    print(f"✓ Unsupported format test passed. Error: {tester.signals_received['error'][0]}")
    
    return True


def test_worker_edge_cases(temp_dir):
    """Test edge cases and error conditions"""
    print("\n=== Testing Edge Cases ===")
    
    tester = WorkerTester()
    
    # Test 1: Empty image array
    print("Test 1: Empty image array for save")
    save_path = Path(temp_dir) / "empty_test.png"
    empty_array = np.array([], dtype=np.uint8)
    palette = list(range(768))
    
    worker = FileSaveWorker(empty_array, palette, str(save_path))
    worker.error.connect(tester.on_error)
    
    wait_for_worker(worker)
    
    assert len(tester.signals_received['error']) > 0, "Should error on empty array"
    assert "No image data" in tester.signals_received['error'][0], "Error should mention no image data"
    print("✓ Empty array test passed")
    
    # Test 2: Invalid JSON palette
    print("\nTest 2: Invalid JSON palette")
    tester.reset()
    json_path = Path(temp_dir) / "invalid.json"
    json_path.write_text('{"invalid": "json", no colors}')
    
    worker = PaletteLoadWorker(str(json_path))
    worker.error.connect(tester.on_error)
    
    wait_for_worker(worker)
    
    assert len(tester.signals_received['error']) > 0, "Should error on invalid JSON"
    assert "Invalid JSON" in tester.signals_received['error'][0], "Error should mention invalid JSON"
    print("✓ Invalid JSON test passed")
    
    # Test 3: Non-indexed image conversion
    print("\nTest 3: Non-indexed image loading")
    tester.reset()
    rgb_path = Path(temp_dir) / "rgb_test.png"
    
    # Create RGB image
    rgb_img = Image.new('RGB', (8, 8), (255, 0, 0))
    rgb_img.save(rgb_path)
    
    worker = FileLoadWorker(str(rgb_path))
    worker.finished.connect(tester.on_finished)
    worker.result.connect(tester.on_result)
    worker.error.connect(tester.on_error)
    
    wait_for_worker(worker)
    
    assert tester.signals_received['finished'], "Should successfully convert RGB to indexed"
    image_array, metadata = tester.signals_received['result']
    assert metadata['mode'] == 'P', "Should be converted to indexed mode"
    print("✓ RGB conversion test passed")
    
    return True


def run_all_tests():
    """Run all worker tests"""
    print("Starting Worker Functionality Tests")
    print("=" * 50)
    
    # Create temporary directory
    with tempfile.TemporaryDirectory() as temp_dir:
        try:
            # Run each test suite
            results = []
            
            results.append(("FileLoadWorker", test_file_load_worker(temp_dir)))
            results.append(("FileSaveWorker", test_file_save_worker(temp_dir)))
            results.append(("PaletteLoadWorker", test_palette_load_worker(temp_dir)))
            results.append(("Edge Cases", test_worker_edge_cases(temp_dir)))
            
            # Summary
            print("\n" + "=" * 50)
            print("TEST SUMMARY")
            print("=" * 50)
            
            all_passed = True
            for test_name, passed in results:
                status = "PASSED" if passed else "FAILED"
                print(f"{test_name}: {status}")
                if not passed:
                    all_passed = False
            
            if all_passed:
                print("\n✅ All tests passed!")
                return 0
            else:
                print("\n❌ Some tests failed!")
                return 1
                
        except Exception as e:
            print(f"\n❌ Test execution failed: {e}")
            import traceback
            traceback.print_exc()
            return 1


if __name__ == "__main__":
    # Set Qt to use offscreen platform (no display needed)
    os.environ['QT_QPA_PLATFORM'] = 'offscreen'
    
    # Initialize Qt application
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    
    # Run tests
    exit_code = run_all_tests()
    
    # Exit
    sys.exit(exit_code)