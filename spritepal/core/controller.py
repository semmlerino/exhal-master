"""
Main controller for SpritePal extraction workflow
"""

from __future__ import annotations

import contextlib
import os
import subprocess
import sys
from typing import TYPE_CHECKING, Any, TypedDict, override

from PIL import Image
from PyQt6.QtCore import QObject, QThread, pyqtSignal
from PyQt6.QtWidgets import QMessageBox

if TYPE_CHECKING:
    from PyQt6.QtGui import QPixmap

    from spritepal.ui.main_window import MainWindow

from spritepal.core.managers import (
    ExtractionManager,
    get_extraction_manager,
    get_injection_manager,
    get_session_manager,
)


# Type definitions
class ExtractionParams(TypedDict):
    """Type definition for extraction parameters"""
    vram_path: str
    cgram_path: str
    oam_path: str
    vram_offset: int
    output_base: str
    create_grayscale: bool
    create_metadata: bool
    grayscale_mode: bool


class ROMExtractionParams(TypedDict):
    """Type definition for ROM extraction parameters"""
    rom_path: str
    sprite_offset: int
    sprite_name: str
    output_base: str
    cgram_path: str | None


# UI imports moved to functions to avoid circular dependencies
from spritepal.utils.constants import (
    DEFAULT_TILES_PER_ROW,
    TILE_WIDTH,
)
from spritepal.utils.image_utils import pil_to_qpixmap
from spritepal.utils.logging_config import get_logger
from spritepal.utils.validation import validate_image_file

logger = get_logger(__name__)


class ExtractionWorker(QThread):
    """Worker thread for extraction process - thin wrapper around ExtractionManager"""

    progress: pyqtSignal = pyqtSignal(str)  # status message
    preview_ready: pyqtSignal = pyqtSignal(object, int)  # pixmap, tile_count
    preview_image_ready: pyqtSignal = pyqtSignal(object)  # PIL image for palette application
    palettes_ready: pyqtSignal = pyqtSignal(dict)  # palette data
    active_palettes_ready: pyqtSignal = pyqtSignal(list)  # active palette indices
    extraction_finished: pyqtSignal = pyqtSignal(list)  # extracted files
    error: pyqtSignal = pyqtSignal(str)  # error message

    def __init__(self, params: ExtractionParams) -> None:
        super().__init__()
        self.params: ExtractionParams = params
        self.manager: ExtractionManager | None = None

    def run(self) -> None:
        """Run the extraction process using ExtractionManager"""
        # Store connection references for proper disconnection
        self._connections = []

        try:
            # Get the extraction manager
            self.manager = get_extraction_manager()

            # Connect manager signals to worker signals BEFORE starting extraction
            # to prevent race condition where signals are emitted before connections
            connection1 = self.manager.extraction_progress.connect(self.progress.emit)
            connection2 = self.manager.palettes_extracted.connect(self.palettes_ready.emit)
            connection3 = self.manager.active_palettes_found.connect(self.active_palettes_ready.emit)

            # Store connections for proper cleanup
            self._connections.extend([connection1, connection2, connection3])

            # Handle preview generation
            def on_preview_generated(img: Image.Image, tile_count: int) -> None:
                # Convert PIL image to QPixmap
                pixmap = pil_to_qpixmap(img)
                self.preview_ready.emit(pixmap, tile_count)
                self.preview_image_ready.emit(img)

            connection4 = self.manager.preview_generated.connect(on_preview_generated)
            self._connections.append(connection4)

            # Perform extraction using manager
            extracted_files = self.manager.extract_from_vram(
                vram_path=self.params["vram_path"],
                output_base=self.params["output_base"],
                cgram_path=self.params.get("cgram_path"),
                oam_path=self.params.get("oam_path"),
                vram_offset=self.params.get("vram_offset"),
                create_grayscale=self.params.get("create_grayscale", True),
                create_metadata=self.params.get("create_metadata", True),
                grayscale_mode=self.params.get("grayscale_mode", False),
            )

            self.extraction_finished.emit(extracted_files)

        except Exception as e:
            self.error.emit(str(e))
        finally:
            # Disconnect only this worker's specific connections to avoid affecting other components
            if self.manager and hasattr(self, "_connections"):
                with contextlib.suppress(Exception):
                    for connection in self._connections:
                        if connection:
                            self.manager.disconnect(connection)


class ExtractionController(QObject):
    """Controller for the extraction workflow"""

    def __init__(self, main_window: MainWindow) -> None:
        super().__init__()
        self.main_window = main_window

        # Get managers
        self.session_manager = get_session_manager()
        self.extraction_manager = get_extraction_manager()
        self.injection_manager = get_injection_manager()

        # Workers still managed locally (thin wrappers)
        self.worker: ExtractionWorker | None = None
        self.rom_worker: ROMExtractionWorker | None = None

        # Connect UI signals
        self.main_window.extract_requested.connect(self.start_extraction)
        self.main_window.open_in_editor_requested.connect(self.open_in_editor)
        self.main_window.arrange_rows_requested.connect(self.open_row_arrangement)
        self.main_window.arrange_grid_requested.connect(self.open_grid_arrangement)
        self.main_window.inject_requested.connect(self.start_injection)
        self.main_window.extraction_panel.offset_changed.connect(
            self.update_preview_with_offset
        )

        # Connect injection manager signals
        self.injection_manager.injection_progress.connect(self._on_injection_progress)
        self.injection_manager.injection_finished.connect(self._on_injection_finished)

    def start_extraction(self) -> None:
        """Start the extraction process"""
        # Get parameters from UI
        params = self.main_window.get_extraction_params()

        # Validate parameters using extraction manager
        try:
            self.extraction_manager.validate_extraction_params(params)
        except Exception as e:
            self.main_window.extraction_failed(str(e))
            return

        # Create and start worker thread
        self.worker = ExtractionWorker(params)
        self.worker.progress.connect(self._on_progress)
        self.worker.preview_ready.connect(self._on_preview_ready)
        self.worker.preview_image_ready.connect(self._on_preview_image_ready)
        self.worker.palettes_ready.connect(self._on_palettes_ready)
        self.worker.active_palettes_ready.connect(self._on_active_palettes_ready)
        self.worker.extraction_finished.connect(self._on_extraction_finished)
        self.worker.error.connect(self._on_extraction_error)
        self.worker.start()

    def _on_progress(self, message: str) -> None:
        """Handle progress updates"""
        self.main_window.status_bar.showMessage(message)

    def _on_preview_ready(self, pixmap: QPixmap, tile_count: int) -> None:
        """Handle preview ready"""
        self.main_window.sprite_preview.set_preview(pixmap, tile_count)
        self.main_window.preview_info.setText(f"Tiles: {tile_count}")

    def _on_preview_image_ready(self, pil_image: Image.Image) -> None:
        """Handle preview PIL image ready"""
        self.main_window.sprite_preview.set_grayscale_image(pil_image)

    def _on_palettes_ready(self, palettes: dict[str, list[tuple[int, int, int]]]) -> None:
        """Handle palettes ready"""
        self.main_window.palette_preview.set_all_palettes(palettes)
        self.main_window.sprite_preview.set_palettes(palettes)

    def _on_active_palettes_ready(self, active_palettes: list[int]) -> None:
        """Handle active palettes ready"""
        self.main_window.palette_preview.highlight_active_palettes(active_palettes)

    def _on_extraction_finished(self, extracted_files: list[str]) -> None:
        """Handle extraction finished"""
        self.main_window.extraction_complete(extracted_files)
        self._cleanup_worker()

    def _on_extraction_error(self, error_message: str) -> None:
        """Handle extraction error"""
        self.main_window.extraction_failed(error_message)
        self._cleanup_worker()

    def _cleanup_worker(self) -> None:
        """Safely cleanup worker thread"""
        if self.worker:
            # Wait for thread to finish before dereferencing
            if self.worker.isRunning():
                self.worker.quit()
                self._ = worker.wait(3000)  # Wait up to 3 seconds
            self.worker = None

    def update_preview_with_offset(self, offset: int) -> None:
        """Update preview with new VRAM offset without full extraction"""
        logger.debug(f"Updating preview with offset: 0x{offset:04X} ({offset})")

        try:
            # Check if we have VRAM loaded
            has_vram = self.main_window.extraction_panel.has_vram()
            logger.debug(f"Has VRAM loaded: {has_vram}")

            if not has_vram:
                logger.debug("No VRAM loaded, skipping preview update")
                return

            # Get VRAM path
            logger.debug("Getting VRAM path from extraction panel")
            vram_path = self.main_window.extraction_panel.get_vram_path()
            logger.debug(f"VRAM path: {vram_path}")

            if not vram_path:
                logger.warning("VRAM path is empty or None")
                self.main_window.status_bar.showMessage("VRAM path not available")
                return

            # Use ExtractionManager for preview generation
            logger.debug("Using ExtractionManager for preview generation")
            img, num_tiles = self.extraction_manager.generate_preview(vram_path, offset)
            logger.debug(f"Generated preview with {num_tiles} tiles, image size: {img.size[0]}x{img.size[1]}")

            # Convert to pixmap
            logger.debug("Converting PIL image to QPixmap")
            pixmap = pil_to_qpixmap(img)
            logger.debug("Pixmap conversion successful")

            # Update preview without resetting view (for real-time slider updates)
            logger.debug("Updating sprite preview widget")
            self.main_window.sprite_preview.update_preview(pixmap, num_tiles)

            info_text = f"Tiles: {num_tiles} (Offset: 0x{offset:04X})"
            logger.debug(f"Setting preview info text: {info_text}")
            self.main_window.preview_info.setText(info_text)

            # Also update the grayscale image for palette application
            logger.debug("Setting grayscale image in sprite preview")
            self.main_window.sprite_preview.set_grayscale_image(img)

            logger.debug("Preview update completed successfully")

        except Exception as e:
            error_msg = f"Preview update failed: {e!s}"
            logger.exception("Error in preview update with offset 0x%04X", offset)

            # Try to show error in status bar
            try:
                self.main_window.status_bar.showMessage(error_msg)
            except Exception:
                logger.exception("Failed to show error in status bar")

            # Try to clear preview on error to prevent showing stale data
            try:
                logger.debug("Attempting to clear preview due to error")
                self.main_window.sprite_preview.clear_preview()
                self.main_window.preview_info.setText("Preview update failed")
            except Exception:
                logger.exception("Failed to clear preview on error")

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
                self.main_window.status_bar.showMessage(
                    "Pixel editor launcher not found"
                )
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

        try:
            # Try to get tiles_per_row from sprite preview or use default
            tiles_per_row = self._get_tiles_per_row_from_sprite(sprite_file)

            # Open row arrangement dialog
            from spritepal.ui.row_arrangement_dialog import (  # noqa: PLC0415
                RowArrangementDialog,
            )
            dialog = RowArrangementDialog(sprite_file, tiles_per_row, self.main_window)

            # Pass palette data from the main window's sprite preview if available
            if (
                hasattr(self.main_window, "sprite_preview")
                and self.main_window.sprite_preview
            ) and hasattr(self.main_window.sprite_preview, "get_palettes"):
                try:
                    palettes = self.main_window.sprite_preview.get_palettes()
                    if palettes:
                        dialog.set_palettes(palettes)
                except Exception as e:
                    # Log palette loading error but continue with dialog
                    logger.warning(f"Failed to load palette data for dialog: {e}")
                        # Dialog can still function without palette data

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
        except Exception as e:
            _ = QMessageBox.critical(
                self.main_window,
                "Error",
                f"Failed to open row arrangement dialog: {e!s}"
            )

    def open_grid_arrangement(self, sprite_file: str) -> None:
        """Open the grid arrangement dialog"""
        if not os.path.exists(sprite_file):
            self.main_window.status_bar.showMessage("Sprite file not found")
            return

        # Try to get tiles_per_row from sprite preview or use default
        tiles_per_row = self._get_tiles_per_row_from_sprite(sprite_file)

        # Open grid arrangement dialog
        from spritepal.ui.grid_arrangement_dialog import (  # noqa: PLC0415
            GridArrangementDialog,
        )
        dialog = GridArrangementDialog(sprite_file, tiles_per_row, self.main_window)

        # Pass palette data from the main window's sprite preview if available
        if (
            hasattr(self.main_window, "sprite_preview")
            and self.main_window.sprite_preview
        ) and hasattr(self.main_window.sprite_preview, "get_palettes"):
            try:
                palettes = self.main_window.sprite_preview.get_palettes()
                if palettes:
                    dialog.set_palettes(palettes)
            except Exception as e:
                # Log palette loading error but continue with dialog
                logger.warning(f"Failed to load palette data for dialog: {e}")
                    # Dialog can still function without palette data

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
        if (
            hasattr(self.main_window, "sprite_preview")
            and self.main_window.sprite_preview
        ):
            try:
                _, tiles_per_row = self.main_window.sprite_preview.get_tile_info()
                if tiles_per_row > 0:
                    return tiles_per_row
            except (AttributeError, TypeError):
                pass

        # Fallback: try to calculate from sprite dimensions
        try:
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
        """Start the injection process using InjectionManager"""
        # Get sprite path and metadata path
        output_base = self.main_window._output_path
        if not output_base:
            self.main_window.status_bar.showMessage("No extraction to inject")
            return

        sprite_path = f"{output_base}.png"
        metadata_path = f"{output_base}.metadata.json"

        # Get smart input VRAM suggestion using injection manager
        suggested_input_vram = self.injection_manager.get_smart_vram_suggestion(
            sprite_path, metadata_path if os.path.exists(metadata_path) else ""
        )

        # Show injection dialog
        from spritepal.ui.injection_dialog import InjectionDialog  # noqa: PLC0415
        dialog = InjectionDialog(
            self.main_window,
            sprite_path=sprite_path,
            metadata_path=metadata_path if os.path.exists(metadata_path) else "",
            input_vram=suggested_input_vram,
        )

        if dialog.exec():
            params = dialog.get_parameters()
            if params:
                # Store dialog and parameters in session for saving on success
                self.session_manager.set("workflow", "current_injection_dialog", dialog)
                self.session_manager.set("workflow", "current_injection_params", params)

                # Start injection using manager
                success = self.injection_manager.start_injection(params)
                if not success:
                    self.main_window.status_bar.showMessage("Failed to start injection")

    def _on_injection_progress(self, message: str) -> None:
        """Handle injection progress updates"""
        self.main_window.status_bar.showMessage(message)

    def _on_injection_finished(self, success: bool, message: str) -> None:
        """Handle injection completion"""
        if success:
            self.main_window.status_bar.showMessage(f"Injection successful: {message}")

            # Save injection parameters for future use if it was a ROM injection
            current_injection_params = self.session_manager.get("workflow", "current_injection_params")
            current_injection_dialog = self.session_manager.get("workflow", "current_injection_dialog")

            if (
                current_injection_params
                and current_injection_params.get("mode") == "rom"
                and current_injection_dialog
                and hasattr(
                    current_injection_dialog, "save_rom_injection_parameters"
                )
            ):
                try:
                    current_injection_dialog.save_rom_injection_parameters()
                except Exception as e:
                    # Don't fail the injection if saving parameters fails
                    logger.warning(f"Could not save ROM injection parameters: {e}")
        else:
            self.main_window.status_bar.showMessage(f"Injection failed: {message}")

        # Clean up
        # Injection worker removed - now handled by InjectionManager
        self.session_manager.set("workflow", "current_injection_dialog", None)
        self.session_manager.set("workflow", "current_injection_params", None)


    def start_rom_extraction(self, params: dict[str, Any]) -> None:
        """Start ROM sprite extraction process"""
        # Create and start ROM extraction worker
        self.rom_worker = ROMExtractionWorker(params)
        self.rom_worker.progress.connect(self._on_rom_progress)
        self.rom_worker.extraction_finished.connect(self._on_rom_extraction_finished)
        self.rom_worker.error.connect(self._on_rom_extraction_error)
        self.rom_worker.start()

    def _on_rom_progress(self, message: str) -> None:
        """Handle ROM extraction progress"""
        self.main_window.status_bar.showMessage(message)

    def _on_rom_extraction_finished(self, extracted_files: list[str]) -> None:
        """Handle ROM extraction completion"""
        self.main_window.extraction_complete(extracted_files)
        self._cleanup_rom_worker()

    def _on_rom_extraction_error(self, error_message: str) -> None:
        """Handle ROM extraction error"""
        self.main_window.extraction_failed(error_message)
        self._cleanup_rom_worker()

    def _cleanup_rom_worker(self) -> None:
        """Safely cleanup ROM worker thread"""
        if self.rom_worker:
            # Wait for thread to finish before dereferencing
            if self.rom_worker.isRunning():
                self.rom_worker.quit()
                self._ = rom_worker.wait(3000)  # Wait up to 3 seconds
            self.rom_worker = None


class ROMExtractionWorker(QThread):
    """Worker thread for ROM extraction process - thin wrapper around ExtractionManager"""

    progress: pyqtSignal = pyqtSignal(str)  # status message
    extraction_finished: pyqtSignal = pyqtSignal(list)  # extracted files
    error: pyqtSignal = pyqtSignal(str)  # error message

    def __init__(self, params: ROMExtractionParams) -> None:
        super().__init__()
        self.params: ROMExtractionParams = params
        self.manager: ExtractionManager | None = None

    @override
    def run(self) -> None:
        """Run the ROM extraction process using ExtractionManager"""
        # Store connection references for proper disconnection
        self._connections = []

        try:
            # Get the extraction manager
            self.manager = get_extraction_manager()

            # Connect manager signals to worker signals BEFORE starting extraction
            # to prevent race condition where signals are emitted before connections
            connection = self.manager.extraction_progress.connect(self.progress.emit)
            self._connections.append(connection)

            # Perform extraction using manager
            extracted_files = self.manager.extract_from_rom(
                rom_path=self.params["rom_path"],
                offset=self.params["sprite_offset"],
                output_base=self.params["output_base"],
                sprite_name=self.params["sprite_name"],
                cgram_path=self.params.get("cgram_path"),
            )

            self.extraction_finished.emit(extracted_files)

        except Exception as e:
            self.error.emit(str(e))
        finally:
            # Disconnect only this worker's specific connections to avoid affecting other components
            if self.manager and hasattr(self, "_connections"):
                with contextlib.suppress(Exception):
                    for connection in self._connections:
                        if connection:
                            self.manager.disconnect(connection)
