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
from PyQt6.QtCore import QMetaObject, QObject, QThread, pyqtSignal
from PyQt6.QtWidgets import QMessageBox

if TYPE_CHECKING:
    from PyQt6.QtGui import QPixmap

    from spritepal.ui.main_window import MainWindow

from spritepal.core.managers import (
    ExtractionManager,
    InjectionManager,
    SessionManager,
    get_extraction_manager,
    get_injection_manager,
    get_session_manager,
)
from spritepal.core.workers import VRAMExtractionWorker, ROMExtractionWorker
from spritepal.ui.grid_arrangement_dialog import GridArrangementDialog
from spritepal.ui.injection_dialog import InjectionDialog
from spritepal.ui.row_arrangement_dialog import RowArrangementDialog
from spritepal.utils.constants import (
    DEFAULT_TILES_PER_ROW,
    TILE_WIDTH,
)
from spritepal.utils.image_utils import pil_to_qpixmap
from spritepal.utils.logging_config import get_logger
from spritepal.utils.settings_manager import get_settings_manager
from spritepal.utils.validation import validate_image_file


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


logger = get_logger(__name__)



class ExtractionController(QObject):
    """Controller for the extraction workflow"""

    def __init__(self, main_window: MainWindow) -> None:
        super().__init__()
        self.main_window: MainWindow = main_window

        # Get managers
        self.session_manager: SessionManager = get_session_manager()
        self.extraction_manager: ExtractionManager = get_extraction_manager()
        self.injection_manager: InjectionManager = get_injection_manager()

        # Workers still managed locally (thin wrappers)
        self.worker: VRAMExtractionWorker | None = None
        self.rom_worker: ROMExtractionWorker | None = None

        # Connect UI signals
        _ = self.main_window.extract_requested.connect(self.start_extraction)
        _ = self.main_window.open_in_editor_requested.connect(self.open_in_editor)
        _ = self.main_window.arrange_rows_requested.connect(self.open_row_arrangement)
        _ = self.main_window.arrange_grid_requested.connect(self.open_grid_arrangement)
        _ = self.main_window.inject_requested.connect(self.start_injection)
        _ = self.main_window.extraction_panel.offset_changed.connect(
            self.update_preview_with_offset
        )

        # Connect injection manager signals
        _ = self.injection_manager.injection_progress.connect(self._on_injection_progress)
        _ = self.injection_manager.injection_finished.connect(self._on_injection_finished)
        _ = self.injection_manager.cache_saved.connect(self._on_cache_saved)

        # Connect extraction manager cache signals
        _ = self.extraction_manager.cache_operation_started.connect(self._on_cache_operation_started)
        _ = self.extraction_manager.cache_hit.connect(self._on_cache_hit)
        _ = self.extraction_manager.cache_miss.connect(self._on_cache_miss)
        _ = self.extraction_manager.cache_saved.connect(self._on_cache_saved)

    def start_extraction(self) -> None:
        """Start the extraction process"""
        # Get parameters from UI
        params = self.main_window.get_extraction_params()

        # PARAMETER VALIDATION: Check requirements first for better UX
        # Users should get helpful parameter guidance before file system errors
        try:
            self.extraction_manager.validate_extraction_params(params)
        except Exception as e:
            self.main_window.extraction_failed(str(e))
            return

        # DEFENSIVE VALIDATION: Prevent blocking I/O operations with invalid files
        # This ensures fail-fast behavior before expensive worker thread operations
        import os
        vram_path = params.get("vram_path", "")
        if not vram_path or not os.path.exists(vram_path):
            self.main_window.extraction_failed(f"VRAM file does not exist: {vram_path}")
            return
            
        # CRITICAL FIX FOR BUG #11: Add file format validation to prevent 2+ minute blocking
        # Validate VRAM file format and size to prevent expensive processing of invalid files
        try:
            # Check VRAM file size (should be at least 64KB for valid SNES VRAM dump)
            vram_size = os.path.getsize(vram_path)
            if vram_size < 0x10000:  # 64KB minimum
                self.main_window.extraction_failed(f"VRAM file too small ({vram_size} bytes). Expected at least 64KB.")
                return
            if vram_size > 0x100000:  # 1MB maximum (reasonable upper bound)
                self.main_window.extraction_failed(f"VRAM file too large ({vram_size} bytes). Expected at most 1MB.")
                return
                
            # Quick validation: try to read first few bytes to ensure file is readable
            with open(vram_path, 'rb') as f:
                header = f.read(16)  # Read first 16 bytes
                if len(header) < 16:
                    self.main_window.extraction_failed(f"VRAM file appears corrupted or truncated.")
                    return
        except (OSError, IOError) as e:
            self.main_window.extraction_failed(f"Cannot read VRAM file: {e}")
            return
            
        cgram_path = params.get("cgram_path", "")
        grayscale_mode = params.get("grayscale_mode", False)
        if not grayscale_mode and cgram_path:
            if not os.path.exists(cgram_path):
                self.main_window.extraction_failed(f"CGRAM file does not exist: {cgram_path}")
                return
            # Validate CGRAM file size (should be 512 bytes for SNES CGRAM)
            try:
                cgram_size = os.path.getsize(cgram_path)
                if cgram_size != 512:
                    self.main_window.extraction_failed(f"CGRAM file size invalid ({cgram_size} bytes). Expected 512 bytes.")
                    return
            except (OSError, IOError) as e:
                self.main_window.extraction_failed(f"Cannot read CGRAM file: {e}")
                return
            
        oam_path = params.get("oam_path", "")
        if oam_path:
            if not os.path.exists(oam_path):
                self.main_window.extraction_failed(f"OAM file does not exist: {oam_path}")
                return
            # Validate OAM file size (should be 544 bytes for SNES OAM)
            try:
                oam_size = os.path.getsize(oam_path)
                if oam_size != 544:
                    self.main_window.extraction_failed(f"OAM file size invalid ({oam_size} bytes). Expected 544 bytes.")
                    return
            except (OSError, IOError) as e:
                self.main_window.extraction_failed(f"Cannot read OAM file: {e}")
                return

        # Create and start worker thread
        # Convert validated params dict to ExtractionParams TypedDict
        extraction_params: ExtractionParams = {
            "vram_path": params["vram_path"],
            "cgram_path": params.get("cgram_path", ""),
            "oam_path": params.get("oam_path", ""),
            "vram_offset": params.get("vram_offset", 0xC000),
            "output_base": params["output_base"],
            "create_grayscale": params.get("create_grayscale", True),
            "create_metadata": params.get("create_metadata", True),
            "grayscale_mode": params.get("grayscale_mode", False),
        }
        self.worker = VRAMExtractionWorker(extraction_params)
        _ = self.worker.progress.connect(self._on_progress)
        _ = self.worker.preview_ready.connect(self._on_preview_ready)
        _ = self.worker.preview_image_ready.connect(self._on_preview_image_ready)
        _ = self.worker.palettes_ready.connect(self._on_palettes_ready)
        _ = self.worker.active_palettes_ready.connect(self._on_active_palettes_ready)
        _ = self.worker.extraction_finished.connect(self._on_extraction_finished)
        _ = self.worker.error.connect(self._on_extraction_error)
        self.worker.start()

    def _on_progress(self, percent: int, message: str) -> None:
        """Handle progress updates"""
        self.main_window.status_bar.showMessage(message)

    def _on_preview_ready(self, pil_image: Image.Image, tile_count: int) -> None:
        """Handle preview ready - convert PIL Image to QPixmap in main thread"""
        # CRITICAL FIX FOR BUG #26: Convert PIL Image to QPixmap in main thread (safe!)
        # Worker now emits PIL Image to avoid Qt threading violations
        pixmap = pil_to_qpixmap(pil_image)
        if pixmap is not None:
            self.main_window.sprite_preview.set_preview(pixmap, tile_count)
            self.main_window.preview_info.setText(f"Tiles: {tile_count}")
        else:
            logger.error("Failed to convert PIL image to QPixmap for preview")

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

    def _on_extraction_error(self, error_message: str, exception: Exception | None = None) -> None:
        """Handle extraction error"""
        self.main_window.extraction_failed(error_message)
        self._cleanup_worker()

    def _cleanup_worker(self) -> None:
        """Safely cleanup worker thread"""
        if self.worker:
            # Wait for thread to finish before dereferencing
            if self.worker.isRunning():
                self.worker.quit()
                _ = self.worker.wait(3000)  # Wait up to 3 seconds
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
                _ = subprocess.Popen([sys.executable, launcher_path, sprite_file_abs])
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

    def _on_cache_operation_started(self, operation: str, cache_type: str) -> None:
        """Handle cache operation started notification"""
        settings_manager = get_settings_manager()

        # Only show if indicators are enabled
        if settings_manager.get("cache", "show_indicators", True):
            # Show cache operation badge
            badge_text = f"{operation} {cache_type.replace('_', ' ')}"
            self.main_window.show_cache_operation_badge(badge_text)

    def _on_cache_hit(self, cache_type: str, time_saved: float) -> None:
        """Handle cache hit notification"""
        settings_manager = get_settings_manager()

        # Hide cache operation badge since operation is complete
        self.main_window.hide_cache_operation_badge()

        # Only show if indicators are enabled
        if settings_manager.get("cache", "show_indicators", True):
            # Update status bar with cache hit info
            message = f"Loaded {cache_type.replace('_', ' ')} from cache (saved {time_saved:.1f}s)"
            self.main_window.status_bar.showMessage(message, 5000)

            # Update cache status indicator if present
            if hasattr(self.main_window, "_update_cache_status"):
                self.main_window._update_cache_status()

    def _on_cache_miss(self, cache_type: str) -> None:
        """Handle cache miss notification"""
        # Cache misses are normal - only log them, don't show in UI
        logger.debug(f"Cache miss for {cache_type}")

    def _on_cache_saved(self, cache_type: str, count: int) -> None:
        """Handle cache saved notification"""
        settings_manager = get_settings_manager()

        # Hide cache operation badge since operation is complete
        self.main_window.hide_cache_operation_badge()

        # Only show if indicators are enabled
        if settings_manager.get("cache", "show_indicators", True):
            # Update status bar with cache save info
            message = f"💾 Saved {count} {cache_type.replace('_', ' ')} to cache"
            self.main_window.status_bar.showMessage(message, 5000)
            # Update cache status widget if method exists
            if hasattr(self.main_window, "update_cache_status"):
                self.main_window.update_cache_status()  # type: ignore[attr-defined]
            # Refresh ROM file widget cache display
            if hasattr(self.main_window, "rom_extraction_panel") and hasattr(self.main_window.rom_extraction_panel, "rom_file_widget"):
                self.main_window.rom_extraction_panel.rom_file_widget.refresh_cache_status()

    def start_rom_extraction(self, params: dict[str, Any]) -> None:
        """Start ROM sprite extraction process"""
        # Convert validated params dict to ROMExtractionParams TypedDict
        rom_extraction_params: ROMExtractionParams = {
            "rom_path": params["rom_path"],
            "sprite_offset": params["sprite_offset"],
            "sprite_name": params["sprite_name"],
            "output_base": params["output_base"],
            "cgram_path": params.get("cgram_path"),
        }
        # Create and start ROM extraction worker
        self.rom_worker = ROMExtractionWorker(rom_extraction_params)
        _ = self.rom_worker.progress.connect(self._on_rom_progress)
        _ = self.rom_worker.extraction_finished.connect(self._on_rom_extraction_finished)
        _ = self.rom_worker.error.connect(self._on_rom_extraction_error)
        self.rom_worker.start()

    def _on_rom_progress(self, percent: int, message: str) -> None:
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
                _ = self.rom_worker.wait(3000)  # Wait up to 3 seconds
            self.rom_worker = None


