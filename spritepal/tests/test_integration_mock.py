"""
Mock-based integration tests that work in any environment.
These tests mock Qt components to test business logic without requiring a display.
"""

import sys
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch

import pytest

# Add parent directories to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from spritepal.core.controller import ExtractionWorker
from spritepal.utils.constants import VRAM_SPRITE_OFFSET, BYTES_PER_TILE


class TestExtractionWorkerMocked:
    """Test ExtractionWorker with mocked Qt components"""
    
    @pytest.fixture
    def mock_signals(self):
        """Create mock signals that behave like Qt signals"""
        class MockSignal:
            def __init__(self):
                self.callbacks = []
                self.emit = Mock(side_effect=self._emit)
                
            def connect(self, callback):
                self.callbacks.append(callback)
                
            def _emit(self, *args):
                for callback in self.callbacks:
                    callback(*args)
                    
        return {
            'progress': MockSignal(),
            'preview_ready': MockSignal(),
            'palettes_ready': MockSignal(),
            'active_palettes_ready': MockSignal(),
            'finished': MockSignal(),
            'error': MockSignal()
        }
    
    @pytest.fixture
    def worker_params(self, tmp_path):
        """Create test parameters"""
        # Create minimal test files
        vram_data = bytearray(0x10000)
        for i in range(10):
            offset = VRAM_SPRITE_OFFSET + i * BYTES_PER_TILE
            for j in range(BYTES_PER_TILE):
                vram_data[offset + j] = (i + j) % 256
                
        cgram_data = bytearray(512)
        cgram_data[256] = 0x1F
        cgram_data[257] = 0x00
        
        vram_path = tmp_path / "test.vram"
        cgram_path = tmp_path / "test.cgram"
        
        vram_path.write_bytes(vram_data)
        cgram_path.write_bytes(cgram_data)
        
        return {
            "vram_path": str(vram_path),
            "cgram_path": str(cgram_path),
            "output_base": str(tmp_path / "output"),
            "create_grayscale": True,
            "create_metadata": False,
            "oam_path": None
        }
    
    @patch('spritepal.core.controller.QThread')
    @patch('spritepal.core.controller.pyqtSignal')
    @patch('spritepal.core.controller.QPixmap')
    def test_worker_with_mocked_qt(self, mock_qpixmap, mock_signal, mock_qthread, 
                                   worker_params, mock_signals):
        """Test worker functionality with mocked Qt components"""
        # Configure mocks
        mock_signal.side_effect = lambda *args: Mock()
        mock_pixmap_instance = Mock()
        mock_qpixmap.return_value = mock_pixmap_instance
        
        # Create worker normally
        worker = ExtractionWorker(worker_params)
        
        # Replace signals with our mocks
        for signal_name, mock_signal_obj in mock_signals.items():
            setattr(worker, signal_name, mock_signal_obj)
        
        # Track emitted data
        progress_messages = []
        preview_data = []
        finished_files = []
        
        # Connect handlers
        worker.progress.connect(lambda msg: progress_messages.append(msg))
        worker.preview_ready.connect(lambda pm, tc: preview_data.append((pm, tc)))
        worker.finished.connect(lambda files: finished_files.extend(files))
        
        # Mock the pixmap creation
        worker._create_pixmap_from_image = Mock(return_value=mock_pixmap_instance)
        
        # Run the worker directly (not as thread)
        worker.run()
        
        # Verify signals were emitted correctly
        assert len(progress_messages) > 0
        assert "Extracting sprites from VRAM..." in progress_messages
        assert "Extraction complete!" in progress_messages
        
        # Verify preview was created
        assert worker.preview_ready.emit.called
        assert worker._create_pixmap_from_image.called
        
        # Verify files were created
        assert worker.finished.emit.called
        call_args = worker.finished.emit.call_args[0][0]
        assert len(call_args) >= 2
        assert any(f.endswith(".png") for f in call_args)
        assert any(f.endswith(".pal.json") for f in call_args)
    
    @patch('spritepal.core.controller.QPixmap')
    def test_pixmap_creation_mocked(self, mock_qpixmap):
        """Test pixmap creation with mocked QPixmap"""
        from PIL import Image
        
        # Create test image
        test_image = Image.new('P', (128, 128), 0)
        
        # Mock QPixmap
        mock_pixmap_instance = Mock()
        mock_pixmap_instance.loadFromData = Mock(return_value=True)
        mock_qpixmap.return_value = mock_pixmap_instance
        
        # Create worker (doesn't matter which params)
        worker = ExtractionWorker({})
        
        # Test pixmap creation
        result = worker._create_pixmap_from_image(test_image)
        
        # Verify
        assert result == mock_pixmap_instance
        assert mock_pixmap_instance.loadFromData.called
        
        # Check that PNG data was passed
        call_args = mock_pixmap_instance.loadFromData.call_args[0][0]
        assert isinstance(call_args, bytes)
        assert len(call_args) > 0  # Should have PNG data


class TestControllerMocked:
    """Test ExtractionController with mocked components"""
    
    @patch('spritepal.core.controller.QObject')
    @patch('spritepal.core.controller.ExtractionWorker')
    def test_controller_workflow(self, mock_worker_class, mock_qobject):
        """Test controller workflow with mocks"""
        # Create mock main window
        mock_main_window = Mock()
        mock_main_window.get_extraction_params = Mock(return_value={
            "vram_path": "/test/vram.dmp",
            "cgram_path": "/test/cgram.dmp",
            "output_base": "/test/output",
            "create_grayscale": True,
            "create_metadata": True,
            "oam_path": None
        })
        
        # Create mock worker
        mock_worker = Mock()
        mock_worker_class.return_value = mock_worker
        
        # Import and create controller
        from spritepal.core.controller import ExtractionController
        
        # Create controller normally
        controller = ExtractionController(mock_main_window)
        
        # Start extraction
        controller.start_extraction()
        
        # Verify worker was created and started
        assert mock_worker_class.called
        assert mock_worker.start.called
        
        # Verify signals were connected
        assert mock_worker.progress.connect.called
        assert mock_worker.preview_ready.connect.called
        assert mock_worker.palettes_ready.connect.called
        assert mock_worker.finished.connect.called
        assert mock_worker.error.connect.called


class TestBusinessLogicOnly:
    """Test pure business logic without Qt dependencies"""
    
    def test_extraction_workflow_no_qt(self, tmp_path):
        """Test the extraction workflow without any Qt components"""
        from spritepal.core.extractor import SpriteExtractor
        from spritepal.core.palette_manager import PaletteManager
        
        # Create test data
        vram_data = bytearray(0x10000)
        cgram_data = bytearray(512)
        
        # Add some test patterns
        for i in range(100):
            offset = VRAM_SPRITE_OFFSET + i * BYTES_PER_TILE
            if offset + BYTES_PER_TILE <= len(vram_data):
                for j in range(BYTES_PER_TILE):
                    vram_data[offset + j] = (i * 2 + j) % 256
        
        # Add test palettes
        for i in range(256):
            cgram_data[i*2] = i % 32
            cgram_data[i*2 + 1] = (i // 32) % 32
        
        # Save test files
        vram_path = tmp_path / "test.vram"
        cgram_path = tmp_path / "test.cgram"
        vram_path.write_bytes(vram_data)
        cgram_path.write_bytes(cgram_data)
        
        # Test extraction
        extractor = SpriteExtractor()
        output_png = str(tmp_path / "output.png")
        img, num_tiles = extractor.extract_sprites_grayscale(str(vram_path), output_png)
        
        assert Path(output_png).exists()
        assert num_tiles > 0
        
        # Test palette extraction
        palette_manager = PaletteManager()
        palette_manager.load_cgram(str(cgram_path))
        
        palettes = palette_manager.get_sprite_palettes()
        assert len(palettes) == 8  # Palettes 8-15
        
        # Test palette file creation
        pal_file = str(tmp_path / "test.pal.json")
        palette_manager.create_palette_json(8, pal_file, output_png)
        assert Path(pal_file).exists()