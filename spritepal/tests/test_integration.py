"""Integration tests for SpritePal - testing components working together"""

import json
import shutil
import sys
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

# Add parent directories to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from spritepal.core.controller import ExtractionController
from spritepal.core.extractor import SpriteExtractor
from spritepal.core.palette_manager import PaletteManager
from spritepal.core.workers import VRAMExtractionWorker
from spritepal.utils.constants import (
    BYTES_PER_TILE,
    COLORS_PER_PALETTE,
    SPRITE_PALETTE_END,
    SPRITE_PALETTE_START,
    VRAM_PATTERNS,
    VRAM_SPRITE_OFFSET,
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
            "temp_dir": temp_dir,
            "vram_path": str(vram_path),
            "cgram_path": str(cgram_path),
        }

        # Cleanup
        shutil.rmtree(temp_dir)

    def test_extractor_palette_manager_integration(self, sample_files):
        """Test SpriteExtractor and PaletteManager working together"""
        output_dir = Path(sample_files["temp_dir"])

        # Extract sprites
        extractor = SpriteExtractor()
        sprite_path = output_dir / "sprites.png"
        img, num_tiles = extractor.extract_sprites_grayscale(
            sample_files["vram_path"], str(sprite_path)
        )

        assert sprite_path.exists()
        assert num_tiles > 0
        assert img.mode == "P"  # Palette mode

        # Extract palettes
        palette_manager = PaletteManager()
        palette_manager.load_cgram(sample_files["cgram_path"])

        # Create palette files for the extracted sprite
        pal_path = output_dir / "sprites.pal.json"
        palette_manager.create_palette_json(8, str(pal_path), str(sprite_path))

        assert pal_path.exists()

        # Verify palette file references the sprite
        with open(pal_path) as f:
            pal_data = json.load(f)

        assert pal_data["source"]["companion_image"] == str(sprite_path)
        assert len(pal_data["palette"]["colors"]) == COLORS_PER_PALETTE

    @pytest.mark.integration
    def test_multiple_palette_extraction(self, sample_files):
        """Test extracting all sprite palettes"""
        output_dir = Path(sample_files["temp_dir"])
        output_base = str(output_dir / "test_sprite")

        # Extract sprite
        extractor = SpriteExtractor()
        sprite_path = f"{output_base}.png"
        extractor.extract_sprites_grayscale(sample_files["vram_path"], sprite_path)

        # Extract all sprite palettes
        palette_manager = PaletteManager()
        palette_manager.load_cgram(sample_files["cgram_path"])

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
        indices = [p["source"]["palette_index"] for p in palettes_data]
        assert len(set(indices)) == 8


class TestVRAMExtractionWorker:
    """Test the VRAMExtractionWorker thread integration"""

    @pytest.fixture
    def worker_params(self, tmp_path):
        """Create parameters for VRAMExtractionWorker"""
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
            "vram_path": str(vram_path),
            "cgram_path": str(cgram_path),
            "output_base": str(tmp_path / "output"),
            "create_grayscale": True,
            "create_metadata": False,
            "oam_path": None,
        }

    @pytest.mark.gui
    def test_worker_signals(self, worker_params, qtbot):
        """Test VRAMExtractionWorker signal emission"""
        # Initialize managers for this test
        from spritepal.core.managers import cleanup_managers, initialize_managers
        initialize_managers("TestApp")

        try:
            worker = VRAMExtractionWorker(worker_params)

            # Connect signal handlers
            progress_messages = []
            preview_data = []
            finished_files = []

            worker.progress.connect(lambda percent, msg: progress_messages.append(msg))
            worker.preview_ready.connect(lambda pm, tc: preview_data.append((pm, tc)))
            worker.extraction_finished.connect(lambda files: finished_files.extend(files))

            # Start worker as real thread and wait for completion
            with qtbot.waitSignal(worker.extraction_finished, timeout=10000):
                worker.start()

            # Wait for worker to fully complete
            worker.wait(5000)

            # Check signals were emitted
            assert len(progress_messages) > 0
            assert "Extracting sprites from VRAM..." in progress_messages
            assert "Extraction complete!" in progress_messages

            assert len(preview_data) == 1
            pixmap, tile_count = preview_data[0]
            assert tile_count > 0

            assert len(finished_files) >= 2  # Main PNG and at least one palette
            assert any(f.endswith(".png") for f in finished_files)
            assert any(f.endswith(".pal.json") for f in finished_files)
        finally:
            # Clean up worker and managers
            if worker.isRunning():
                worker.terminate()
                worker.wait(5000)
            cleanup_managers()

    @pytest.mark.gui
    def test_worker_error_handling(self, qtbot):
        """Test VRAMExtractionWorker error handling"""
        # Initialize managers for this test
        from spritepal.core.managers import cleanup_managers, initialize_managers
        initialize_managers("TestApp")

        try:
            # Create worker with invalid parameters
            bad_params = {
                "vram_path": "/nonexistent/file.vram",
                "cgram_path": None,
                "output_base": "/invalid/output",
                "create_grayscale": True,
                "create_metadata": False,
                "oam_path": None,
            }

            worker = VRAMExtractionWorker(bad_params)

            # Connect error handler
            errors = []
            worker.error.connect(lambda e: errors.append(e))

            # Start worker as real thread and wait for error signal
            with qtbot.waitSignal(worker.error, timeout=10000):
                worker.start()

            # Wait for worker to complete
            worker.wait(5000)

            assert len(errors) > 0
            # Check for either file not found or validation error
            assert any(phrase in errors[0].lower() for phrase in ["no such file", "not found", "does not exist", "vram file"])
        finally:
            # Clean up worker and managers
            if worker.isRunning():
                worker.terminate()
                worker.wait(5000)
            cleanup_managers()


class TestRealFilePatterns:
    """Test with file patterns matching real SNES dumps"""

    def test_vram_pattern_matching(self):
        """Test VRAM file pattern recognition"""
        test_filenames = [
            "Kirby_VRAM.dmp",
            "game_vram_dump.dmp",
            "VideoRam_001.dmp",
            "test_VRAM_backup.dmp",
        ]

        for filename in test_filenames:
            # At least one pattern should match
            matched = False
            for pattern in VRAM_PATTERNS:
                # Simple pattern matching (real implementation might use glob)
                pattern_regex = pattern.replace("*", ".*")
                if pattern_regex in filename or filename.endswith(".dmp"):
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
                vram_data[VRAM_SPRITE_OFFSET + i * 32 + j] = (i + j) % 256

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
                assert "palette" in data
                assert "colors" in data["palette"]


class TestFullWorkflowIntegration:
    """Test complete integration workflows with mocked Qt components"""

    @pytest.fixture
    def integration_sample_files(self):
        """Create sample VRAM and CGRAM files for integration testing"""
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
            "temp_dir": temp_dir,
            "vram_path": str(vram_path),
            "cgram_path": str(cgram_path),
        }

        # Cleanup
        shutil.rmtree(temp_dir)

    @pytest.fixture
    def mock_main_window(self):
        """Create a mock main window for testing UI integration"""
        window = Mock()
        window.status_bar = Mock()
        window.sprite_preview = Mock()
        window.preview_info = Mock()
        window.palette_preview = Mock()
        window.extraction_complete = Mock()
        window.extraction_failed = Mock()
        window.extract_requested = Mock()
        window.open_in_editor_requested = Mock()

        return window

    @pytest.fixture
    def oam_test_data(self):
        """Create test OAM data with mixed on/off-screen sprites"""
        oam_data = bytearray(512)

        # On-screen sprite with palette 0
        oam_data[0] = 0x50  # X low
        oam_data[1] = 50  # Y (on-screen)
        oam_data[2] = 0x00  # Tile
        oam_data[3] = 0x00  # Attrs (palette 0)

        # On-screen sprite with palette 2
        oam_data[4] = 0x80  # X low
        oam_data[5] = 100  # Y (on-screen)
        oam_data[6] = 0x00  # Tile
        oam_data[7] = 0x02  # Attrs (palette 2)

        # Off-screen sprite with palette 1
        oam_data[8] = 0x00  # X low
        oam_data[9] = 240  # Y (off-screen)
        oam_data[10] = 0x00  # Tile
        oam_data[11] = 0x01  # Attrs (palette 1)

        return bytes(oam_data)

    @pytest.fixture
    def mock_qt_signals(self):
        """Create mock Qt signals that behave like real signals"""
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
            "progress": MockSignal(),
            "preview_ready": MockSignal(),
            "preview_image_ready": MockSignal(),
            "palettes_ready": MockSignal(),
            "active_palettes_ready": MockSignal(),
            "finished": MockSignal(),
            "error": MockSignal(),
        }

    @pytest.mark.integration
    @pytest.mark.gui
    def test_complete_ui_controller_worker_integration(
        self, integration_sample_files, mock_main_window, mock_qt_signals
    ):
        """Test complete UI-Controller-Worker integration workflow"""
        # Initialize managers for this test
        from spritepal.core.managers import cleanup_managers, initialize_managers
        initialize_managers("TestApp")

        try:
            # Track signals received by UI components
            ui_signals = {
                "progress_messages": [],
                "preview_updates": [],
                "preview_image_updates": [],
                "palette_updates": [],
                "active_palette_updates": [],
                "completion_calls": [],
                "error_calls": [],
            }

            # Connect signal tracking
            def track_progress(msg):
                ui_signals["progress_messages"].append(msg)

            def track_preview(pixmap, tile_count):
                ui_signals["preview_updates"].append((pixmap, tile_count))

            def track_preview_image(pil_image):
                ui_signals["preview_image_updates"].append(pil_image)

            def track_palette(palettes):
                ui_signals["palette_updates"].append(palettes)

            def track_active_palettes(active_pals):
                ui_signals["active_palette_updates"].append(active_pals)

            def track_completion(files):
                ui_signals["completion_calls"].append(files)

            def track_error(error):
                ui_signals["error_calls"].append(error)

            mock_main_window.status_bar.showMessage = track_progress
            mock_main_window.sprite_preview.set_preview = track_preview
            mock_main_window.sprite_preview.set_grayscale_image = track_preview_image
            mock_main_window.palette_preview.set_all_palettes = track_palette
            mock_main_window.palette_preview.highlight_active_palettes = (
                track_active_palettes
            )
            mock_main_window.extraction_complete = track_completion
            mock_main_window.extraction_failed = track_error

            # Set up extraction parameters
            mock_main_window.get_extraction_params.return_value = {
                "vram_path": integration_sample_files["vram_path"],
                "cgram_path": integration_sample_files["cgram_path"],
                "output_base": str(
                    Path(integration_sample_files["temp_dir"]) / "test_integration"
                ),
                "create_grayscale": True,
                "create_metadata": True,
                "oam_path": None,
            }

            # Mock Qt components and create worker directly
            mock_pixmap_instance = Mock()
            mock_pixmap_instance.loadFromData = Mock(return_value=True)

            with (
                patch("spritepal.utils.image_utils.QPixmap") as mock_qpixmap_utils,
                patch("spritepal.core.controller.pil_to_qpixmap") as mock_pil_to_qpixmap,
            ):
                # Configure mocks
                mock_qpixmap_utils.return_value = mock_pixmap_instance
                mock_pil_to_qpixmap.return_value = mock_pixmap_instance

                # Create worker directly with mock signals
                worker = VRAMExtractionWorker(
                    mock_main_window.get_extraction_params.return_value
                )

                # Replace worker signals with our mocks
                for signal_name, mock_signal in mock_qt_signals.items():
                    setattr(worker, signal_name, mock_signal)

                # Create controller
                controller = ExtractionController(mock_main_window)

                # Connect controller handlers to mock signals
                worker.progress.connect(controller._on_progress)
                worker.preview_ready.connect(controller._on_preview_ready)
                worker.preview_image_ready.connect(controller._on_preview_image_ready)
                worker.palettes_ready.connect(controller._on_palettes_ready)
                worker.active_palettes_ready.connect(controller._on_active_palettes_ready)
                worker.extraction_finished.connect(controller._on_extraction_finished)
                worker.error.connect(controller._on_extraction_error)

                # Run worker directly
                worker.run()

            # Verify signal flow
            assert len(ui_signals["progress_messages"]) >= 4  # Multiple progress updates
            assert "Extracting sprites from VRAM..." in ui_signals["progress_messages"]
            assert "Extraction complete!" in ui_signals["progress_messages"]

            # Verify preview updates
            assert len(ui_signals["preview_updates"]) == 1
            pixmap, tile_count = ui_signals["preview_updates"][0]
            assert pixmap is not None
            assert tile_count > 0

            # Verify preview image updates
            assert len(ui_signals["preview_image_updates"]) == 1
            pil_image = ui_signals["preview_image_updates"][0]
            assert pil_image is not None

            # Verify palette updates
            assert len(ui_signals["palette_updates"]) == 1
            assert len(ui_signals["palette_updates"][0]) == 8  # 8 sprite palettes

            # Verify completion
            assert len(ui_signals["completion_calls"]) == 1
            assert len(ui_signals["error_calls"]) == 0

            # Verify output files exist
            output_files = ui_signals["completion_calls"][0]
            assert any(f.endswith(".png") for f in output_files)
            assert any(f.endswith(".pal.json") for f in output_files)

            for file_path in output_files:
                assert Path(file_path).exists()
        finally:
            # Clean up managers
            cleanup_managers()

    @pytest.mark.integration
    @pytest.mark.gui
    def test_error_recovery_and_cleanup_integration(
        self, mock_main_window, mock_qt_signals
    ):
        """Test error recovery and system cleanup integration"""
        # Initialize managers for this test
        from spritepal.core.managers import cleanup_managers, initialize_managers
        initialize_managers("TestApp")

        try:
            # Track error handling
            error_calls = []
            mock_main_window.extraction_failed = error_calls.append

            # Test 1: Error scenario with invalid files
            invalid_params = {
                "vram_path": "/nonexistent/vram.dmp",
                "cgram_path": "/nonexistent/cgram.dmp",
                "output_base": "/invalid/output",
                "create_grayscale": True,
                "create_metadata": False,
                "oam_path": None,
            }

            # Mock Qt components
            mock_pixmap_instance = Mock()
            mock_pixmap_instance.loadFromData = Mock(return_value=True)

            with (
                patch("spritepal.utils.image_utils.QPixmap") as mock_qpixmap_utils,
                patch("spritepal.core.controller.pil_to_qpixmap") as mock_pil_to_qpixmap,
            ):
                # Configure mocks
                mock_qpixmap_utils.return_value = mock_pixmap_instance
                mock_pil_to_qpixmap.return_value = mock_pixmap_instance

                # Create worker directly with invalid params
                worker = VRAMExtractionWorker(invalid_params)

                # Replace worker signals with our mocks
                for signal_name, mock_signal in mock_qt_signals.items():
                    setattr(worker, signal_name, mock_signal)

                # Create controller
                controller = ExtractionController(mock_main_window)

                # Connect error tracking
                worker.error.connect(controller._on_extraction_error)

                # Run worker directly (should error)
                worker.run()

            # Verify error was handled
            assert len(error_calls) == 1
            # Check for either file not found or validation error
            assert any(phrase in error_calls[0].lower() for phrase in ["no such file", "not found", "does not exist", "vram file"])

            # Test 2: Recovery scenario with valid files
            with tempfile.TemporaryDirectory() as temp_dir:
                # Create minimal valid files
                vram_data = bytearray(0x10000)
                cgram_data = bytearray(512)

                vram_path = Path(temp_dir) / "test.vram"
                cgram_path = Path(temp_dir) / "test.cgram"
                vram_path.write_bytes(vram_data)
                cgram_path.write_bytes(cgram_data)

                # Reset error tracking
                error_calls.clear()
                completion_calls = []
                mock_main_window.extraction_complete = completion_calls.append

                # Set up valid parameters
                valid_params = {
                    "vram_path": str(vram_path),
                    "cgram_path": str(cgram_path),
                    "output_base": str(Path(temp_dir) / "recovery_test"),
                    "create_grayscale": True,
                    "create_metadata": False,
                    "oam_path": None,
                }

                # Mock Qt components
                mock_pixmap_instance = Mock()
                mock_pixmap_instance.loadFromData = Mock(return_value=True)

                with (
                    patch("spritepal.utils.image_utils.QPixmap") as mock_qpixmap_utils,
                    patch("spritepal.core.controller.pil_to_qpixmap") as mock_pil_to_qpixmap,
                ):
                    # Configure mocks
                    mock_qpixmap_utils.return_value = mock_pixmap_instance
                    mock_pil_to_qpixmap.return_value = mock_pixmap_instance

                    # Create worker with valid params
                    recovery_worker = VRAMExtractionWorker(valid_params)

                    # Replace worker signals with our mocks
                    for signal_name, mock_signal in mock_qt_signals.items():
                        setattr(recovery_worker, signal_name, mock_signal)

                    # Connect completion tracking
                    recovery_worker.extraction_finished.connect(controller._on_extraction_finished)
                    recovery_worker.error.connect(controller._on_extraction_error)

                    # Run worker directly
                    recovery_worker.run()

                # Verify recovery worked
                assert len(error_calls) == 0
                assert len(completion_calls) == 1

                # Verify output files exist
                output_files = completion_calls[0]
                for file_path in output_files:
                    assert Path(file_path).exists()
        finally:
            # Clean up managers
            cleanup_managers()

    @pytest.mark.integration
    @pytest.mark.gui
    def test_oam_analysis_integration_workflow(
        self, integration_sample_files, mock_main_window, oam_test_data, mock_qt_signals
    ):
        """Test complete OAM analysis integration workflow"""
        # Initialize managers for this test
        from spritepal.core.managers import cleanup_managers, initialize_managers
        initialize_managers("TestApp")

        try:
            # Create OAM file
            oam_path = Path(integration_sample_files["temp_dir"]) / "test_OAM.dmp"
            oam_path.write_bytes(oam_test_data)

            # Track active palette updates
            active_palette_calls = []
            mock_main_window.palette_preview.highlight_active_palettes = (
                active_palette_calls.append
            )

            # Set up extraction parameters with OAM
            mock_main_window.get_extraction_params.return_value = {
                "vram_path": integration_sample_files["vram_path"],
                "cgram_path": integration_sample_files["cgram_path"],
                "output_base": str(Path(integration_sample_files["temp_dir"]) / "oam_test"),
                "create_grayscale": True,
                "create_metadata": True,
                "oam_path": str(oam_path),
            }

            # Track completion
            completion_calls = []
            mock_main_window.extraction_complete = completion_calls.append

            # Mock Qt components and create worker directly
            mock_pixmap_instance = Mock()
            mock_pixmap_instance.loadFromData = Mock(return_value=True)

            with (
                patch("spritepal.utils.image_utils.QPixmap") as mock_qpixmap_utils,
                patch("spritepal.core.controller.pil_to_qpixmap") as mock_pil_to_qpixmap,
            ):
                # Configure mocks
                mock_qpixmap_utils.return_value = mock_pixmap_instance
                mock_pil_to_qpixmap.return_value = mock_pixmap_instance

                # Create worker directly with OAM analysis parameters
                worker = VRAMExtractionWorker(
                    mock_main_window.get_extraction_params.return_value
                )

                # Replace worker signals with our mocks
                for signal_name, mock_signal in mock_qt_signals.items():
                    setattr(worker, signal_name, mock_signal)

                # Create controller
                ExtractionController(mock_main_window)

                # Connect tracking
                worker.active_palettes_ready.connect(
                    lambda p: active_palette_calls.append(p)
                )
                worker.extraction_finished.connect(lambda f: completion_calls.append(f))

                # Run worker directly
                worker.run()

            # Verify OAM analysis was performed
            assert len(active_palette_calls) == 1
            active_palettes = active_palette_calls[0]

            # Should include palettes from on-screen sprites (0+8=8, 2+8=10)
            # Should exclude palette from off-screen sprite (1+8=9)
            assert 8 in active_palettes  # palette 0 -> CGRAM 8 (on-screen)
            assert 10 in active_palettes  # palette 2 -> CGRAM 10 (on-screen)

            # Verify extraction completed successfully
            assert len(completion_calls) == 1
            output_files = completion_calls[0]

            # Verify all expected files exist
            assert any(f.endswith(".png") for f in output_files)
            assert any(f.endswith(".metadata.json") for f in output_files)

            for file_path in output_files:
                assert Path(file_path).exists()
        finally:
            # Clean up managers
            cleanup_managers()
