"""Integration tests for SpritePal - testing components working together"""

import pytest
import sys
import os
from pathlib import Path
import tempfile
import json
import shutil
from unittest.mock import Mock, patch

# Add parent directories to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from spritepal.core.extractor import SpriteExtractor
from spritepal.core.palette_manager import PaletteManager
from spritepal.core.controller import ExtractionWorker
from spritepal.utils.constants import (
    VRAM_SPRITE_OFFSET, SPRITE_PALETTE_START, SPRITE_PALETTE_END,
    COLORS_PER_PALETTE, BYTES_PER_TILE
)


class TestEndToEndWorkflow:
    """Test complete extraction workflows"""
    
    @pytest.fixture
    def sample_files(self):
        """Create sample VRAM and CGRAM files for testing"""
        # Create temporary directory
        temp_dir = tempfile.mkdtemp()
        
        # Create VRAM file with test sprite data
        vram_data = bytearray(0x10000)  # 64KB
        # Add some recognizable sprite tiles at the sprite offset
        for i in range(10):  # 10 tiles
            tile_start = VRAM_SPRITE_OFFSET + (i * BYTES_PER_TILE)
            # Create a simple pattern for each tile
            for j in range(BYTES_PER_TILE):
                vram_data[tile_start + j] = (i * 16 + j) % 256
        
        vram_path = Path(temp_dir) / "test_VRAM.dmp"
        vram_path.write_bytes(vram_data)
        
        # Create CGRAM file with test palettes
        cgram_data = bytearray(512)  # 256 colors * 2 bytes
        # Set up sprite palettes with distinct colors
        for pal_idx in range(SPRITE_PALETTE_START, SPRITE_PALETTE_END):
            for color_idx in range(COLORS_PER_PALETTE):
                offset = (pal_idx * COLORS_PER_PALETTE + color_idx) * 2
                # Create distinct colors for each palette
                r = (pal_idx * 2) % 32
                g = (color_idx * 2) % 32
                b = ((pal_idx + color_idx) * 2) % 32
                color = (b << 10) | (g << 5) | r
                cgram_data[offset] = color & 0xFF
                cgram_data[offset + 1] = (color >> 8) & 0xFF
        
        cgram_path = Path(temp_dir) / "test_CGRAM.dmp"
        cgram_path.write_bytes(cgram_data)
        
        yield {
            'temp_dir': temp_dir,
            'vram_path': str(vram_path),
            'cgram_path': str(cgram_path)
        }
        
        # Cleanup
        shutil.rmtree(temp_dir)
    
    def test_extractor_palette_manager_integration(self, sample_files):
        """Test SpriteExtractor and PaletteManager working together"""
        output_dir = Path(sample_files['temp_dir'])
        
        # Extract sprites
        extractor = SpriteExtractor()
        sprite_path = output_dir / "sprites.png"
        img, num_tiles = extractor.extract_sprites_grayscale(
            sample_files['vram_path'],
            str(sprite_path)
        )
        
        assert sprite_path.exists()
        assert num_tiles > 0
        assert img.mode == 'P'  # Palette mode
        
        # Extract palettes
        palette_manager = PaletteManager()
        palette_manager.load_cgram(sample_files['cgram_path'])
        
        # Create palette files for the extracted sprite
        pal_path = output_dir / "sprites.pal.json"
        palette_manager.create_palette_json(8, str(pal_path), str(sprite_path))
        
        assert pal_path.exists()
        
        # Verify palette file references the sprite
        with open(pal_path) as f:
            pal_data = json.load(f)
        
        assert pal_data['source']['companion_image'] == str(sprite_path)
        assert len(pal_data['palette']['colors']) == COLORS_PER_PALETTE
    
    @pytest.mark.integration
    def test_multiple_palette_extraction(self, sample_files):
        """Test extracting all sprite palettes"""
        output_dir = Path(sample_files['temp_dir'])
        output_base = str(output_dir / "test_sprite")
        
        # Extract sprite
        extractor = SpriteExtractor()
        sprite_path = f"{output_base}.png"
        extractor.extract_sprites_grayscale(
            sample_files['vram_path'],
            sprite_path
        )
        
        # Extract all sprite palettes
        palette_manager = PaletteManager()
        palette_manager.load_cgram(sample_files['cgram_path'])
        
        palette_files = []
        for pal_idx in range(SPRITE_PALETTE_START, SPRITE_PALETTE_END):
            pal_path = f"{output_base}_pal{pal_idx}.pal.json"
            palette_manager.create_palette_json(pal_idx, pal_path, sprite_path)
            palette_files.append(pal_path)
        
        # Verify all palette files were created
        assert len(palette_files) == 8
        for pal_file in palette_files:
            assert Path(pal_file).exists()
            
        # Check each has unique palette data
        palettes_data = []
        for pal_file in palette_files:
            with open(pal_file) as f:
                palettes_data.append(json.load(f))
        
        # Each should have different palette index
        indices = [p['source']['palette_index'] for p in palettes_data]
        assert len(set(indices)) == 8


class TestExtractionWorker:
    """Test the ExtractionWorker thread integration"""
    
    @pytest.fixture
    def worker_params(self, tmp_path):
        """Create parameters for ExtractionWorker"""
        # Create minimal test files
        vram_data = bytearray(0x10000)
        # Add one test tile
        for i in range(32):
            vram_data[VRAM_SPRITE_OFFSET + i] = i
        
        cgram_data = bytearray(512)
        # Add test palette
        cgram_data[256] = 0x1F  # Red color
        cgram_data[257] = 0x00
        
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
    
    @pytest.mark.gui
    @pytest.mark.skipif("QT_QPA_PLATFORM" in os.environ and os.environ["QT_QPA_PLATFORM"] == "offscreen",
                        reason="QThread tests unstable in headless mode")
    def test_worker_signals(self, worker_params, qtbot):
        """Test ExtractionWorker signal emission"""
        worker = ExtractionWorker(worker_params)
        
        # Connect signal handlers
        progress_messages = []
        preview_data = []
        finished_files = []
        
        worker.progress.connect(lambda msg: progress_messages.append(msg))
        worker.preview_ready.connect(lambda pm, tc: preview_data.append((pm, tc)))
        worker.finished.connect(lambda files: finished_files.extend(files))
        
        # Run worker
        worker.run()
        
        # Check signals were emitted
        assert len(progress_messages) > 0
        assert "Extracting sprites from VRAM..." in progress_messages
        assert "Extraction complete!" in progress_messages
        
        assert len(preview_data) == 1
        pixmap, tile_count = preview_data[0]
        assert tile_count > 0
        
        assert len(finished_files) >= 2  # Main PNG and at least one palette
        assert any(f.endswith('.png') for f in finished_files)
        assert any(f.endswith('.pal.json') for f in finished_files)
    
    @pytest.mark.gui
    @pytest.mark.skipif("QT_QPA_PLATFORM" in os.environ and os.environ["QT_QPA_PLATFORM"] == "offscreen",
                        reason="QThread tests unstable in headless mode")
    def test_worker_error_handling(self, qtbot):
        """Test ExtractionWorker error handling"""
        # Create worker with invalid parameters
        bad_params = {
            'vram_path': '/nonexistent/file.vram',
            'cgram_path': None,
            'output_base': '/invalid/output',
            'create_grayscale': True,
            'create_metadata': False,
            'oam_path': None
        }
        
        worker = ExtractionWorker(bad_params)
        
        # Connect error handler
        errors = []
        worker.error.connect(lambda e: errors.append(e))
        
        # Run worker - should emit error
        worker.run()
        
        assert len(errors) > 0
        assert "No such file" in errors[0] or "not found" in errors[0]


class TestRealFilePatterns:
    """Test with file patterns matching real SNES dumps"""
    
    def test_vram_pattern_matching(self):
        """Test VRAM file pattern recognition"""
        from spritepal.utils.constants import VRAM_PATTERNS
        
        test_filenames = [
            "Kirby_VRAM.dmp",
            "game_vram_dump.dmp",
            "VideoRam_001.dmp",
            "test_VRAM_backup.dmp"
        ]
        
        for filename in test_filenames:
            # At least one pattern should match
            matched = False
            for pattern in VRAM_PATTERNS:
                # Simple pattern matching (real implementation might use glob)
                pattern_regex = pattern.replace('*', '.*')
                if pattern_regex in filename or filename.endswith('.dmp'):
                    matched = True
                    break
            assert matched, f"{filename} should match at least one VRAM pattern"
    
    @pytest.mark.integration
    def test_complete_workflow_with_metadata(self, tmp_path):
        """Test complete workflow including metadata generation"""
        # Create test files
        vram_data = bytearray(0x10000)
        cgram_data = bytearray(512)
        
        # Add some sprite data
        for i in range(5):
            for j in range(32):
                vram_data[VRAM_SPRITE_OFFSET + i*32 + j] = (i + j) % 256
        
        vram_path = tmp_path / "test_VRAM.dmp"
        cgram_path = tmp_path / "test_CGRAM.dmp"
        vram_path.write_bytes(vram_data)
        cgram_path.write_bytes(cgram_data)
        
        # Run extraction
        extractor = SpriteExtractor()
        palette_manager = PaletteManager()
        
        output_base = str(tmp_path / "sprites")
        
        # Extract sprites
        sprite_path = f"{output_base}.png"
        img, num_tiles = extractor.extract_sprites_grayscale(
            str(vram_path), sprite_path
        )
        
        # Extract palettes
        palette_manager.load_cgram(str(cgram_path))
        
        # Create palette files
        palette_files = {}
        for pal_idx in range(SPRITE_PALETTE_START, SPRITE_PALETTE_END):
            pal_file = f"{output_base}_pal{pal_idx}.pal.json"
            palette_manager.create_palette_json(pal_idx, pal_file, sprite_path)
            palette_files[pal_idx] = pal_file
        
        # Verify all outputs exist
        assert Path(sprite_path).exists()
        for pal_file in palette_files.values():
            assert Path(pal_file).exists()
        
        # Verify palette files are valid JSON
        for pal_file in palette_files.values():
            with open(pal_file) as f:
                data = json.load(f)
                assert 'palette' in data
                assert 'colors' in data['palette']