"""
Main controller for SpritePal extraction workflow
"""

import io
import os
import subprocess
import sys
from typing import Any, Dict, List, Optional
from pathlib import Path

from PyQt6.QtCore import QObject, QThread, pyqtSignal
from PyQt6.QtGui import QPixmap

from spritepal.core.extractor import SpriteExtractor
from spritepal.core.injector import InjectionWorker
from spritepal.core.palette_manager import PaletteManager
from spritepal.ui.grid_arrangement_dialog import GridArrangementDialog
from spritepal.ui.injection_dialog import InjectionDialog
from spritepal.ui.row_arrangement_dialog import RowArrangementDialog
from spritepal.utils.validation import validate_image_file
from spritepal.utils.image_utils import pil_to_qpixmap
from spritepal.utils.constants import (
    BYTES_PER_TILE,
    DEFAULT_TILES_PER_ROW,
    SPRITE_PALETTE_END,
    SPRITE_PALETTE_START,
    TILE_WIDTH,
)


class ExtractionWorker(QThread):
    """Worker thread for extraction process"""

    progress = pyqtSignal(str)  # status message
    preview_ready = pyqtSignal(object, int)  # pixmap, tile_count
    preview_image_ready = pyqtSignal(object)  # PIL image for palette application
    palettes_ready = pyqtSignal(dict)  # palette data
    active_palettes_ready = pyqtSignal(list)  # active palette indices
    finished = pyqtSignal(list)  # extracted files
    error = pyqtSignal(str)  # error message

    def __init__(self, params: Dict[str, Any]) -> None:
        super().__init__()
        self.params = params
        self.extractor = SpriteExtractor()
        self.palette_manager = PaletteManager()

    def run(self) -> None:
        """Run the extraction process"""
        try:
            extracted_files = []

            # Extract sprites
            self.progress.emit("Extracting sprites from VRAM...")

            output_file = f"{self.params['output_base']}.png"

            # Get VRAM offset if provided
            vram_offset = self.params.get("vram_offset", None)

            img, num_tiles = self.extractor.extract_sprites_grayscale(
                self.params["vram_path"], output_file, offset=vram_offset
            )
            extracted_files.append(output_file)

            # Create preview
            self.progress.emit("Creating preview...")
            preview_pixmap = self._create_pixmap_from_image(img)
            self.preview_ready.emit(preview_pixmap, num_tiles)

            # Emit PIL image for palette application
            self.preview_image_ready.emit(img)

            # Extract palettes
            if self.params["cgram_path"]:
                self.progress.emit("Extracting palettes...")
                self.palette_manager.load_cgram(self.params["cgram_path"])

                # Get sprite palettes
                sprite_palettes = self.palette_manager.get_sprite_palettes()
                self.palettes_ready.emit(sprite_palettes)

                # Create palette files
                if self.params["create_grayscale"]:
                    self.progress.emit("Creating palette files...")

                    # Create main palette file (default to palette 8)
                    main_pal_file = f"{self.params['output_base']}.pal.json"
                    self.palette_manager.create_palette_json(
                        8, main_pal_file, output_file
                    )
                    extracted_files.append(main_pal_file)

                    # Create individual palette files
                    palette_files = {}
                    for pal_idx in range(SPRITE_PALETTE_START, SPRITE_PALETTE_END):
                        pal_file = f"{self.params['output_base']}_pal{pal_idx}.pal.json"
                        self.palette_manager.create_palette_json(
                            pal_idx, pal_file, output_file
                        )
                        extracted_files.append(pal_file)
                        palette_files[pal_idx] = pal_file

                    # Create metadata file
                    if self.params["create_metadata"]:
                        self.progress.emit("Creating metadata file...")

                        # Prepare extraction parameters for metadata
                        extraction_params = {
                            "vram_source": os.path.basename(self.params["vram_path"]),
                            "vram_offset": vram_offset
                            if vram_offset is not None
                            else 0xC000,
                            "tile_count": num_tiles,
                            "extraction_size": num_tiles * BYTES_PER_TILE,
                        }

                        metadata_file = self.palette_manager.create_metadata_json(
                            self.params["output_base"], palette_files, extraction_params
                        )
                        extracted_files.append(metadata_file)

            # Analyze OAM if available
            if self.params["oam_path"]:
                self.progress.emit("Analyzing sprite palette usage...")
                active_palettes = self.palette_manager.analyze_oam_palettes(
                    self.params["oam_path"]
                )
                self.active_palettes_ready.emit(active_palettes)

            self.progress.emit("Extraction complete!")
            self.finished.emit(extracted_files)

        except Exception as e:
            self.error.emit(str(e))

    def _create_pixmap_from_image(self, pil_image: Any) -> Optional[QPixmap]:
        """Create QPixmap from PIL image using utility function"""
        return pil_to_qpixmap(pil_image)


class ExtractionController(QObject):
    """Controller for the extraction workflow"""

    def __init__(self, main_window: Any) -> None:
        super().__init__()
        self.main_window = main_window
        self.worker: Optional[ExtractionWorker] = None
        self.injection_worker: Optional[InjectionWorker] = None

        # Connect signals
        self.main_window.extract_requested.connect(self.start_extraction)
        self.main_window.open_in_editor_requested.connect(self.open_in_editor)
        self.main_window.arrange_rows_requested.connect(self.open_row_arrangement)
        self.main_window.arrange_grid_requested.connect(self.open_grid_arrangement)
        self.main_window.inject_requested.connect(self.start_injection)
        self.main_window.extraction_panel.offset_changed.connect(
            self.update_preview_with_offset
        )

    def start_extraction(self) -> None:
        """Start the extraction process"""
        # Get parameters from UI
        params = self.main_window.get_extraction_params()

        # Validate parameters
        if not params["vram_path"] or not params["cgram_path"]:
            self.main_window.extraction_failed("VRAM and CGRAM files are required")
            return

        # Create and start worker thread
        self.worker = ExtractionWorker(params)
        self.worker.progress.connect(self._on_progress)
        self.worker.preview_ready.connect(self._on_preview_ready)
        self.worker.preview_image_ready.connect(self._on_preview_image_ready)
        self.worker.palettes_ready.connect(self._on_palettes_ready)
        self.worker.active_palettes_ready.connect(self._on_active_palettes_ready)
        self.worker.finished.connect(self._on_extraction_finished)
        self.worker.error.connect(self._on_extraction_error)
        self.worker.start()

    def _on_progress(self, message: str) -> None:
        """Handle progress updates"""
        self.main_window.status_bar.showMessage(message)

    def _on_preview_ready(self, pixmap: QPixmap, tile_count: int) -> None:
        """Handle preview ready"""
        self.main_window.sprite_preview.set_preview(pixmap, tile_count)
        self.main_window.preview_info.setText(f"Tiles: {tile_count}")

    def _on_preview_image_ready(self, pil_image: Any) -> None:
        """Handle preview PIL image ready"""
        self.main_window.sprite_preview.set_grayscale_image(pil_image)

    def _on_palettes_ready(self, palettes: Dict[str, Any]) -> None:
        """Handle palettes ready"""
        self.main_window.palette_preview.set_all_palettes(palettes)
        self.main_window.sprite_preview.set_palettes(palettes)

    def _on_active_palettes_ready(self, active_palettes: List[int]) -> None:
        """Handle active palettes ready"""
        self.main_window.palette_preview.highlight_active_palettes(active_palettes)

    def _on_extraction_finished(self, extracted_files: List[str]) -> None:
        """Handle extraction finished"""
        self.main_window.extraction_complete(extracted_files)
        self.worker = None

    def _on_extraction_error(self, error_message: str) -> None:
        """Handle extraction error"""
        self.main_window.extraction_failed(error_message)
        self.worker = None

    def update_preview_with_offset(self, offset: int) -> None:
        """Update preview with new VRAM offset without full extraction"""
        # Check if we have VRAM loaded
        if not self.main_window.extraction_panel.has_vram():
            return

        # Get VRAM path
        vram_path = self.main_window.extraction_panel.get_vram_path()

        try:
            # Create a temporary extractor for preview
            extractor = SpriteExtractor()
            extractor.load_vram(vram_path)

            # Extract tiles with new offset
            tiles, num_tiles = extractor.extract_tiles(offset=offset)

            # Create grayscale image
            img = extractor.create_grayscale_image(tiles)

            # Convert to pixmap
            pixmap = pil_to_qpixmap(img)

            # Update preview without resetting view (for real-time slider updates)
            self.main_window.sprite_preview.update_preview(pixmap, num_tiles)
            self.main_window.preview_info.setText(
                f"Tiles: {num_tiles} (Offset: 0x{offset:04X})"
            )

            # Also update the grayscale image for palette application
            self.main_window.sprite_preview.set_grayscale_image(img)

        except Exception as e:
            self.main_window.status_bar.showMessage(f"Preview update failed: {e!s}")

    def open_in_editor(self, sprite_file: str) -> None:
        """Open the extracted sprites in the pixel editor"""
        # Get the directory where this spritepal package is located
        spritepal_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        exhal_dir = os.path.dirname(spritepal_dir)

        # Look for pixel editor launcher using absolute paths
        launcher_paths = [
            os.path.join(spritepal_dir, "launch_pixel_editor.py"),
            os.path.join(spritepal_dir, "pixel_editor", "launch_pixel_editor.py"),
            os.path.join(exhal_dir, "launch_pixel_editor.py"),
            os.path.join(exhal_dir, "pixel_editor", "launch_pixel_editor.py"),
        ]

        launcher_path = None
        for path in launcher_paths:
            if os.path.exists(path):
                launcher_path = path
                break

        if launcher_path:
            # Validate sprite file before launching
            is_valid, error_msg = validate_image_file(sprite_file)
            if not is_valid:
                self.main_window.status_bar.showMessage(
                    f"Invalid sprite file: {error_msg}"
                )
                return
                
            # Ensure launcher path is absolute and exists
            launcher_path = os.path.abspath(launcher_path)
            if not os.path.exists(launcher_path):
                self.main_window.status_bar.showMessage("Pixel editor launcher not found")
                return
                
            # Launch pixel editor with the sprite file
            try:
                # Use absolute paths for safety
                sprite_file_abs = os.path.abspath(sprite_file)
                subprocess.Popen([sys.executable, launcher_path, sprite_file_abs])
                self.main_window.status_bar.showMessage(
                    f"Opened {os.path.basename(sprite_file)} in pixel editor"
                )
            except Exception as e:
                self.main_window.status_bar.showMessage(
                    f"Failed to open pixel editor: {e}"
                )
        else:
            self.main_window.status_bar.showMessage("Pixel editor not found")

    def open_row_arrangement(self, sprite_file: str) -> None:
        """Open the row arrangement dialog"""
        if not os.path.exists(sprite_file):
            self.main_window.status_bar.showMessage("Sprite file not found")
            return

        # Try to get tiles_per_row from sprite preview or use default
        tiles_per_row = self._get_tiles_per_row_from_sprite(sprite_file)

        # Open row arrangement dialog
        dialog = RowArrangementDialog(sprite_file, tiles_per_row, self.main_window)
        
        # Pass palette data from the main window's sprite preview if available
        if hasattr(self.main_window, 'sprite_preview') and self.main_window.sprite_preview:
            if hasattr(self.main_window.sprite_preview, 'get_palettes'):
                palettes = self.main_window.sprite_preview.get_palettes()
                if palettes:
                    dialog.set_palettes(palettes)

        if dialog.exec():
            # Get the arranged sprite path
            arranged_path = dialog.get_arranged_path()

            if arranged_path and os.path.exists(arranged_path):
                # Open the arranged sprite in the pixel editor
                self.open_in_editor(arranged_path)
                self.main_window.status_bar.showMessage(
                    "Opened arranged sprites in pixel editor"
                )
            else:
                self.main_window.status_bar.showMessage("Row arrangement cancelled")

    def open_grid_arrangement(self, sprite_file: str) -> None:
        """Open the grid arrangement dialog"""
        if not os.path.exists(sprite_file):
            self.main_window.status_bar.showMessage("Sprite file not found")
            return
        
        # Try to get tiles_per_row from sprite preview or use default
        tiles_per_row = self._get_tiles_per_row_from_sprite(sprite_file)
        
        # Open grid arrangement dialog
        dialog = GridArrangementDialog(sprite_file, tiles_per_row, self.main_window)
        
        # Pass palette data from the main window's sprite preview if available
        if hasattr(self.main_window, 'sprite_preview') and self.main_window.sprite_preview:
            if hasattr(self.main_window.sprite_preview, 'get_palettes'):
                palettes = self.main_window.sprite_preview.get_palettes()
                if palettes:
                    dialog.set_palettes(palettes)
        
        if dialog.exec():
            # Get the arranged sprite path
            arranged_path = dialog.get_arranged_path()
            
            if arranged_path and os.path.exists(arranged_path):
                # Open the arranged sprite in the pixel editor
                self.open_in_editor(arranged_path)
                self.main_window.status_bar.showMessage(
                    "Opened grid-arranged sprites in pixel editor"
                )
            else:
                self.main_window.status_bar.showMessage("Grid arrangement cancelled")

    def _get_tiles_per_row_from_sprite(self, sprite_file: str) -> int:
        """Determine tiles per row from sprite file or main window state
        
        Args:
            sprite_file: Path to sprite file
            
        Returns:
            Number of tiles per row
        """
        # Try to get from main window's sprite preview first
        if hasattr(self.main_window, 'sprite_preview') and self.main_window.sprite_preview:
            try:
                _, tiles_per_row = self.main_window.sprite_preview.get_tile_info()
                if tiles_per_row > 0:
                    return tiles_per_row
            except (AttributeError, TypeError):
                pass
        
        # Fallback: try to calculate from sprite dimensions
        try:
            from PIL import Image
            with Image.open(sprite_file) as img:
                # Calculate tiles per row based on sprite width
                # Assume 8x8 pixel tiles (TILE_WIDTH)
                calculated_tiles_per_row = img.width // TILE_WIDTH
                if calculated_tiles_per_row > 0:
                    return min(calculated_tiles_per_row, DEFAULT_TILES_PER_ROW)
        except Exception:
            pass
        
        # Ultimate fallback
        return DEFAULT_TILES_PER_ROW

    def start_injection(self) -> None:
        """Start the injection process"""
        # Get sprite path and metadata path
        output_base = self.main_window._output_path
        if not output_base:
            self.main_window.status_bar.showMessage("No extraction to inject")
            return

        sprite_path = f"{output_base}.png"
        metadata_path = f"{output_base}.metadata.json"

        # Show injection dialog
        dialog = InjectionDialog(
            self.main_window,
            sprite_path=sprite_path,
            metadata_path=metadata_path if os.path.exists(metadata_path) else "",
        )

        if dialog.exec():
            params = dialog.get_parameters()
            if params:
                # Create and start injection worker
                self.injection_worker = InjectionWorker(
                    params["sprite_path"],
                    params["input_vram"],
                    params["output_vram"],
                    params["offset"],
                    params.get("metadata_path"),
                )

                # Connect signals
                self.injection_worker.progress.connect(self._on_injection_progress)
                self.injection_worker.finished.connect(self._on_injection_finished)

                # Start injection
                self.main_window.status_bar.showMessage("Starting injection...")
                self.injection_worker.start()

    def _on_injection_progress(self, message: str) -> None:
        """Handle injection progress updates"""
        self.main_window.status_bar.showMessage(message)

    def _on_injection_finished(self, success: bool, message: str) -> None:
        """Handle injection completion"""
        if success:
            self.main_window.status_bar.showMessage(f"Injection successful: {message}")
        else:
            self.main_window.status_bar.showMessage(f"Injection failed: {message}")

        self.injection_worker = None
