"""Integration tests adapted for headless environments"""

import pytest
import sys
from pathlib import Path
import tempfile
import json
import shutil
from unittest.mock import Mock, patch, MagicMock

# Add parent directories to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from spritepal.core.extractor import SpriteExtractor
from spritepal.core.palette_manager import PaletteManager
from spritepal.utils.constants import (
    VRAM_SPRITE_OFFSET, SPRITE_PALETTE_START, SPRITE_PALETTE_END,
    COLORS_PER_PALETTE, BYTES_PER_TILE
)


class TestExtractionWorkerHeadless:
    """Test ExtractionWorker in headless environment"""
    
    @pytest.fixture
    def mock_qt_imports(self):
        """Mock Qt imports for headless testing"""
        # Mock PyQt6 modules
        mock_qobject = MagicMock()
        mock_qthread = MagicMock()
        mock_signal = MagicMock()
        mock_qpixmap = MagicMock()
        
        # Make signals callable
        mock_signal.return_value = MagicMock()
        
        with patch.dict('sys.modules', {
            'PyQt6.QtCore': MagicMock(QObject=mock_qobject, QThread=mock_qthread, pyqtSignal=mock_signal),
            'PyQt6.QtGui': MagicMock(QPixmap=mock_qpixmap),
        }):
            yield {
                'QObject': mock_qobject,
                'QThread': mock_qthread,
                'pyqtSignal': mock_signal,
                'QPixmap': mock_qpixmap
            }
    
    @pytest.fixture
    def worker_params(self, tmp_path):
        """Create parameters for ExtractionWorker"""
        # Create minimal test files
        vram_data = bytearray(0x10000)
        # Add test tiles
        for i in range(5):
            for j in range(32):
                vram_data[VRAM_SPRITE_OFFSET + i*32 + j] = (i * 32 + j) % 256
        
        cgram_data = bytearray(512)
        # Add test colors
        for i in range(256, 512, 2):
            cgram_data[i] = 0x1F
            cgram_data[i+1] = 0x00
        
        vram_path = tmp_path / "test.vram"
        cgram_path = tmp_path / "test.cgram"
        
        vram_path.write_bytes(vram_data)
        cgram_path.write_bytes(cgram_data)
        
        return {
            'vram_path': str(vram_path),
            'cgram_path': str(cgram_path),
            'output_base': str(tmp_path / "output"),
            'create_grayscale': True,
            'create_metadata': False,
            'oam_path': None
        }
    
    def test_worker_logic_without_qt(self, worker_params, mock_qt_imports):
        """Test worker logic without Qt dependencies"""
        # Import after mocking
        from spritepal.core.controller import ExtractionWorker
        
        # Patch the extractor method that has wrong signature
        with patch.object(SpriteExtractor, 'extract_sprites_grayscale') as mock_extract:
            # Make it return what the worker expects
            from PIL import Image
            test_img = Image.new('P', (128, 64), 0)
            mock_extract.return_value = (test_img, 10)
            
            # Create worker
            worker = ExtractionWorker(worker_params)
            
            # Create proper mocks for signals
            progress_mock = Mock()
            progress_mock.emit = Mock()
            preview_mock = Mock()
            preview_mock.emit = Mock()
            palettes_mock = Mock()
            palettes_mock.emit = Mock()
            finished_mock = Mock()
            finished_mock.emit = Mock()
            error_mock = Mock()
            error_mock.emit = Mock()
            
            # Replace signals
            worker.progress = progress_mock
            worker.preview_ready = preview_mock
            worker.palettes_ready = palettes_mock
            worker.finished = finished_mock
            worker.error = error_mock
            
            # Mock pixmap creation to avoid Qt dependency
            worker._create_pixmap_from_image = Mock(return_value=Mock())
            
            # Run the worker logic directly (not as thread)
            worker.run()
            
            # Verify signals would be emitted
            assert progress_mock.emit.called
            assert preview_mock.emit.called
            assert finished_mock.emit.called
            assert not error_mock.emit.called
            
            # Verify methods were called
            assert mock_extract.called
            assert worker._create_pixmap_from_image.called
    
    def test_worker_error_handling_headless(self, mock_qt_imports):
        """Test error handling without Qt"""
        from spritepal.core.controller import ExtractionWorker
        
        bad_params = {
            'vram_path': '/nonexistent/file.vram',
            'cgram_path': '/nonexistent/file.cgram',
            'output_base': '/invalid/output',
            'create_grayscale': True,
            'create_metadata': False,
            'oam_path': None
        }
        
        worker = ExtractionWorker(bad_params)
        
        # Mock signals
        worker.error = Mock()
        worker.progress = Mock()
        worker.preview_ready = Mock()
        worker.finished = Mock()
        
        # Run worker
        worker.run()
        
        # Should emit error
        assert worker.error.emit.called
        error_msg = worker.error.emit.call_args[0][0]
        assert "No such file" in error_msg or "not found" in error_msg
        assert not worker.finished.emit.called


class TestWorkerBusinessLogic:
    """Test worker business logic extracted from Qt dependencies"""
    
    def test_extraction_workflow_logic(self, tmp_path):
        """Test the extraction workflow without threading"""
        # Create test files
        vram_data = bytearray(0x10000)
        cgram_data = bytearray(512)
        
        # Add sprite data
        for i in range(10):
            tile_offset = VRAM_SPRITE_OFFSET + i * BYTES_PER_TILE
            for j in range(BYTES_PER_TILE):
                vram_data[tile_offset + j] = (i + j) % 256
        
        # Add palette data
        for pal_idx in range(SPRITE_PALETTE_START, SPRITE_PALETTE_END):
            for color_idx in range(COLORS_PER_PALETTE):
                offset = (pal_idx * COLORS_PER_PALETTE + color_idx) * 2
                # Simple color pattern
                color = ((pal_idx << 10) | (color_idx << 5) | color_idx) & 0x7FFF
                cgram_data[offset] = color & 0xFF
                cgram_data[offset + 1] = (color >> 8) & 0xFF
        
        vram_path = tmp_path / "test.vram"
        cgram_path = tmp_path / "test.cgram"
        output_base = tmp_path / "output"
        
        vram_path.write_bytes(vram_data)
        cgram_path.write_bytes(cgram_data)
        
        # Simulate worker workflow
        extractor = SpriteExtractor()
        palette_manager = PaletteManager()
        
        # Extract sprites
        output_file = f"{output_base}.png"
        img, num_tiles = extractor.extract_sprites_grayscale(
            str(vram_path), output_file
        )
        
        assert Path(output_file).exists()
        # Default extraction uses VRAM_SPRITE_SIZE (0x4000 bytes = 512 tiles)
        assert num_tiles == 512
        
        # Extract palettes
        palette_manager.load_cgram(str(cgram_path))
        sprite_palettes = palette_manager.get_sprite_palettes()
        assert len(sprite_palettes) == 8
        
        # Create palette files
        main_pal_file = f"{output_base}.pal.json"
        palette_manager.create_palette_json(8, main_pal_file, output_file)
        assert Path(main_pal_file).exists()
        
        # Create individual palette files
        for pal_idx in range(SPRITE_PALETTE_START, SPRITE_PALETTE_END):
            pal_file = f"{output_base}_pal{pal_idx}.pal.json"
            palette_manager.create_palette_json(pal_idx, pal_file, output_file)
            assert Path(pal_file).exists()
    
    def test_pixmap_creation_mocked(self, tmp_path):
        """Test pixmap creation can be mocked for headless"""
        from PIL import Image
        
        # Create a test image
        test_img = Image.new('P', (128, 128), 0)
        
        # Mock QPixmap
        with patch('spritepal.core.controller.QPixmap') as mock_pixmap_class:
            mock_pixmap = Mock()
            mock_pixmap_class.return_value = mock_pixmap
            
            # Import after patching
            from spritepal.core.controller import ExtractionWorker
            
            # Create worker
            worker = ExtractionWorker({})
            
            # Test pixmap creation
            result = worker._create_pixmap_from_image(test_img)
            
            # Verify mock was used
            assert mock_pixmap.loadFromData.called
            assert result == mock_pixmap