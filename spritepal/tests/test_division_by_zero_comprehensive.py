#!/usr/bin/env python3
"""
Comprehensive tests for division by zero prevention in all scan workers.
Tests all identified division operations to ensure they handle zero cases.
"""

import pytest
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch
import tempfile
from PySide6.QtCore import QObject

# Add parent directory to path for imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))


class TestDivisionByZeroFixes:
    """Test all division by zero scenarios in scan workers."""

    def test_scan_worker_zero_range(self):
        """Test SpriteScanWorker with zero scan range."""
        from ui.rom_extraction.workers.scan_worker import SpriteScanWorker
        
        with tempfile.NamedTemporaryFile(suffix='.rom') as tmp:
            tmp.write(b'x' * 1024)
            tmp.flush()
            
            # Create worker with same start and end (zero range)
            worker = SpriteScanWorker(
                rom_path=tmp.name,
                extractor=MagicMock(),
                use_cache=False,
                start_offset=0x1000,
                end_offset=0x1000  # Same as start = zero range
            )
            
            # Mock the parallel finder to avoid actual scanning
            worker._parallel_finder = MagicMock()
            worker._parallel_finder.search_parallel = MagicMock(return_value=[])
            worker._parallel_finder.step_size = 0x100
            
            # Should not raise division by zero
            worker.run()
            
    def test_scan_worker_progress_callback_zero_range(self):
        """Test SpriteScanWorker progress callback with zero range."""
        from ui.rom_extraction.workers.scan_worker import SpriteScanWorker
        
        with tempfile.NamedTemporaryFile(suffix='.rom') as tmp:
            tmp.write(b'x' * 1024)
            tmp.flush()
            
            worker = SpriteScanWorker(
                rom_path=tmp.name,
                extractor=MagicMock(),
                use_cache=False,
                start_offset=0x500,
                end_offset=0x500  # Zero range
            )
            
            # Capture the progress callback
            worker._parallel_finder = MagicMock()
            progress_callback = None
            
            def capture_callback(*args, **kwargs):
                nonlocal progress_callback
                progress_callback = kwargs.get('progress_callback')
                return []
            
            worker._parallel_finder.search_parallel = capture_callback
            worker._parallel_finder.step_size = 0x100
            
            # Run to capture callback
            worker.run()
            
            # Test progress callback with various values
            if progress_callback:
                # Should handle zero range gracefully
                progress_callback(0, 100)
                progress_callback(50, 100)
                progress_callback(100, 100)

    def test_range_scan_worker_zero_range(self):
        """Test RangeScanWorker with zero scan range."""
        from ui.rom_extraction.workers.range_scan_worker import RangeScanWorker
        
        with tempfile.NamedTemporaryFile(suffix='.rom') as tmp:
            tmp.write(b'x' * 1024)
            tmp.flush()
            
            # Create worker with zero range
            worker = RangeScanWorker(
                rom_path=tmp.name,
                start_offset=0x100,
                end_offset=0x100,  # Same as start
                step_size=0x100,
                extractor=MagicMock()
            )
            
            # Should not raise division by zero
            worker.run()

    def test_similarity_indexing_no_sprites(self):
        """Test SimilarityIndexingWorker with no sprites to index."""
        from ui.rom_extraction.workers.similarity_indexing_worker import SimilarityIndexingWorker
        
        with tempfile.NamedTemporaryFile(suffix='.rom') as tmp:
            tmp.write(b'SNES' * 256)
            tmp.flush()
            
            worker = SimilarityIndexingWorker(
                rom_path=tmp.name
            )
            
            # Don't add any sprites - should handle empty list gracefully
            # The worker should have no pending sprites to process
            
            # Should handle empty sprite list gracefully
            worker.run()
            # Should have emitted progress 100% with "No sprites to index"

    def test_preview_worker_zero_expected_size(self):
        """Test PreviewWorker with zero expected size."""
        from ui.rom_extraction.workers.preview_worker import PreviewWorker
        
        with tempfile.NamedTemporaryFile(suffix='.rom') as tmp:
            # Write test data
            tmp.write(b'\x00' * 1024)
            tmp.flush()
            
            worker = PreviewWorker(
                rom_path=tmp.name,
                offset=0,
                expected_size=0  # Zero expected size
            )
            
            # Mock the extractor
            worker.extractor = MagicMock()
            worker.extractor.extract_tiles_from_rom = MagicMock(
                return_value=(b'\x00' * 32, None, 1)  # Return some tile data
            )
            
            # Should not raise division by zero
            worker.run()

    def test_sprite_search_worker_zero_tile_count(self):
        """Test SpriteSearchWorker quality calculation with zero tile count."""
        from ui.rom_extraction.workers.sprite_search_worker import SpriteSearchWorker
        
        with tempfile.NamedTemporaryFile(suffix='.rom') as tmp:
            tmp.write(b'x' * 1024)
            tmp.flush()
            
            worker = SpriteSearchWorker(
                rom_path=tmp.name,
                search_mode='range',
                search_start=0,
                search_end=512,
                step=256
            )
            
            # Access the internal quality calculation
            # Mock to return sprite with 0 tiles
            mock_extractor = MagicMock()
            mock_extractor.extract_tiles_from_rom = MagicMock(
                return_value=(b'', None, 0)  # 0 tile count
            )
            worker.extractor = mock_extractor
            
            # Should not crash with zero tiles
            worker.run()

    def test_search_worker_zero_step(self):
        """Test SearchWorker with zero step size."""
        from ui.rom_extraction.workers.search_worker import SearchWorker
        
        with tempfile.NamedTemporaryFile(suffix='.rom') as tmp:
            tmp.write(b'x' * 1024)
            tmp.flush()
            
            # Should handle zero step gracefully
            worker = SearchWorker(
                rom_path=tmp.name,
                mode='range',
                start=0,
                end=100,
                step=0  # Zero step - should be prevented
            )
            
            # The worker should either use a default step or handle gracefully
            worker.run()

    @patch('ui.rom_extraction.workers.scan_worker.os.path.getsize')
    def test_scan_worker_zero_rom_size(self, mock_getsize):
        """Test SpriteScanWorker with zero ROM size."""
        mock_getsize.return_value = 0  # Zero file size
        
        from ui.rom_extraction.workers.scan_worker import SpriteScanWorker
        
        with tempfile.NamedTemporaryFile(suffix='.rom') as tmp:
            # Empty file
            tmp.flush()
            
            worker = SpriteScanWorker(
                rom_path=tmp.name,
                extractor=MagicMock(),
                use_cache=False
                # No custom offsets, will use defaults based on file size
            )
            
            # Mock parallel finder
            worker._parallel_finder = MagicMock()
            worker._parallel_finder.search_parallel = MagicMock(return_value=[])
            worker._parallel_finder.step_size = 0x100
            
            # Should handle zero ROM size gracefully
            worker.run()

    def test_all_workers_with_realistic_edge_cases(self):
        """Integration test with realistic edge cases that could cause division by zero."""
        from ui.rom_extraction.workers.scan_worker import SpriteScanWorker
        from ui.rom_extraction.workers.range_scan_worker import RangeScanWorker
        from ui.rom_extraction.workers.similarity_indexing_worker import SimilarityIndexingWorker
        
        with tempfile.NamedTemporaryFile(suffix='.rom') as tmp:
            # Small file that might not have sprites
            tmp.write(b'TEST' * 16)
            tmp.flush()
            
            # Test 1: Scan that finds no sprites
            scan_worker = SpriteScanWorker(
                rom_path=tmp.name,
                extractor=MagicMock(),
                use_cache=False,
                start_offset=0,
                end_offset=64
            )
            scan_worker._parallel_finder = MagicMock()
            scan_worker._parallel_finder.search_parallel = MagicMock(return_value=[])
            scan_worker._parallel_finder.step_size = 16
            
            scan_worker.run()
            
            # Test 2: Similarity indexing with no sprites
            sim_worker = SimilarityIndexingWorker(
                rom_path=tmp.name,
                sprites=[]
            )
            sim_worker.run()
            
            # Test 3: Range scan with tiny range
            range_worker = RangeScanWorker(
                rom_path=tmp.name,
                start_offset=0,
                end_offset=1,  # 1 byte range
                step_size=1,
                extractor=MagicMock()
            )
            range_worker.run()
            
    def test_progress_calculations_boundary_conditions(self):
        """Test progress calculations at boundary conditions."""
        from ui.rom_extraction.workers.scan_worker import SpriteScanWorker
        
        test_cases = [
            (0, 0),      # Zero range
            (0, 1),      # 1 byte range
            (100, 100),  # Same values
            (100, 99),   # Inverted range
        ]
        
        for start, end in test_cases:
            with tempfile.NamedTemporaryFile(suffix='.rom') as tmp:
                tmp.write(b'x' * 1024)
                tmp.flush()
                
                worker = SpriteScanWorker(
                    rom_path=tmp.name,
                    extractor=MagicMock(),
                    use_cache=False,
                    start_offset=start,
                    end_offset=end
                )
                
                worker._parallel_finder = MagicMock()
                worker._parallel_finder.search_parallel = MagicMock(return_value=[])
                worker._parallel_finder.step_size = 1
                
                # Should handle all boundary conditions
                worker.run()


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v", "--tb=short"])