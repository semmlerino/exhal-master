"""Tests for scan worker division by zero and full ROM scanning fixes"""

import pytest
from unittest.mock import MagicMock, patch
from PySide6.QtCore import QObject
from ui.rom_extraction.workers.scan_worker import SpriteScanWorker
from ui.rom_extraction.workers.range_scan_worker import RangeScanWorker


class TestScanWorkerFixes:
    """Test division by zero and full ROM scanning fixes"""
    
    def test_scan_worker_no_division_by_zero_with_same_offsets(self):
        """Test that scan worker handles start_offset == end_offset without division by zero"""
        with patch('ui.rom_extraction.workers.scan_worker.ParallelSpriteFinder'):
            # Create worker with same start and end offsets
            worker = SpriteScanWorker(
                rom_path="/tmp/test.rom",
                extractor=MagicMock(),
                use_cache=False,
                start_offset=0x1000,
                end_offset=0x1000,  # Same as start - would cause division by zero
                parent=None
            )
            
            # Mock the parallel finder to avoid actual ROM operations
            worker._parallel_finder = MagicMock()
            worker._parallel_finder.step_size = 0x100
            worker._parallel_finder.search_parallel = MagicMock(return_value=[])
            
            # This should not raise division by zero error
            with patch.object(worker, 'emit_progress'):
                worker.run()
    
    def test_scan_worker_full_rom_scanning(self):
        """Test that scan worker scans full ROM by default, not just 0xC0000-0xF0000"""
        with patch('ui.rom_extraction.workers.scan_worker.ParallelSpriteFinder'):
            with patch('ui.rom_extraction.workers.scan_worker.os.path.getsize', return_value=0x200000):  # 2MB ROM
                # Create worker without custom offsets
                worker = SpriteScanWorker(
                    rom_path="/tmp/test.rom",
                    extractor=MagicMock(),
                    use_cache=False,
                    start_offset=None,  # No custom range
                    end_offset=None,     # No custom range
                    parent=None
                )
                
                # Mock the parallel finder
                worker._parallel_finder = MagicMock()
                worker._parallel_finder.step_size = 0x100
                
                # Capture the actual range used
                actual_start = None
                actual_end = None
                
                def capture_range(rom_path, **kwargs):
                    nonlocal actual_start, actual_end
                    actual_start = kwargs.get('start_offset')
                    actual_end = kwargs.get('end_offset')
                    return []
                
                worker._parallel_finder.search_parallel = capture_range
                
                # Run the worker
                with patch.object(worker, 'emit_progress'):
                    worker.run()
                
                # Verify it scans from 0x40000 to end of ROM (not the old 0xC0000-0xF0000)
                assert actual_start == 0x40000, f"Expected start 0x40000, got 0x{actual_start:X}"
                assert actual_end == 0x200000, f"Expected end 0x200000, got 0x{actual_end:X}"
    
    def test_range_scan_worker_no_division_by_zero(self):
        """Test that range scan worker handles division by zero gracefully"""
        # Mock the file open
        mock_file_data = b'\x00' * 0x2000
        
        with patch('builtins.open', create=True) as mock_open:
            mock_open.return_value.__enter__.return_value.read.return_value = mock_file_data
            
            # Create worker with same start and end offsets
            worker = RangeScanWorker(
                rom_path="/tmp/test.rom",
                extractor=MagicMock(),
                start_offset=0x1000,
                end_offset=0x1000,  # Same as start - would cause division by zero
                step_size=0x100,
                parent=None
            )
            
            # Mock the extractor methods
            worker.extractor.rom_injector.find_compressed_sprite = MagicMock(side_effect=ValueError)
            
            with patch.object(worker, 'emit_progress'):
                with patch.object(worker, '_save_progress'):
                    # This should not raise division by zero error
                    worker.run()
    
    def test_scan_worker_progress_with_zero_range(self):
        """Test progress callback handles zero range gracefully"""
        with patch('ui.rom_extraction.workers.scan_worker.ParallelSpriteFinder'):
            worker = SpriteScanWorker(
                rom_path="/tmp/test.rom",
                extractor=MagicMock(),
                use_cache=False,
                start_offset=0x1000,
                end_offset=0x1000,  # Zero range
                parent=None
            )
            
            # Mock the parallel finder
            worker._parallel_finder = MagicMock()
            worker._parallel_finder.step_size = 0x100
            
            # Capture progress callback
            progress_callback = None
            
            def capture_callback(rom_path, **kwargs):
                nonlocal progress_callback
                progress_callback = kwargs.get('progress_callback')
                # Simulate calling the progress callback with 50%
                if progress_callback:
                    progress_callback(50, 100)
                return []
            
            worker._parallel_finder.search_parallel = capture_callback
            
            # This should emit 100% progress for invalid range
            with patch.object(worker, 'emit_progress') as mock_emit:
                worker.run()
                
                # Check that it emitted 100% progress for invalid range
                mock_emit.assert_any_call(100, "Invalid scan range")