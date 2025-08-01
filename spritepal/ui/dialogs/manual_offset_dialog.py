"""
Manual Offset Control Dialog

A dedicated window for ROM offset exploration with enhanced controls and visualization.
Refactored to use component-based architecture with SplitterDialog base.
"""

import os
from typing import TYPE_CHECKING, ClassVar, override

if TYPE_CHECKING:
    from spritepal.core.managers.extraction_manager import ExtractionManager
    from spritepal.core.rom_extractor import ROMExtractor

from PyQt6.QtCore import QMutex, QMutexLocker, QRect, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QCloseEvent, QHideEvent, QKeyEvent, QMouseEvent
from PyQt6.QtWidgets import QDialogButtonBox, QLabel, QPushButton, QVBoxLayout, QWidget

from spritepal.ui.components import SplitterDialog
from spritepal.ui.components.panels import (
    ImportExportPanel,
    ScanControlsPanel,
    StatusPanel,
)
from spritepal.ui.components.visualization import ROMMapWidget
from spritepal.ui.rom_extraction.widgets.manual_offset_widget import ManualOffsetWidget
from spritepal.ui.rom_extraction.workers import SpritePreviewWorker, SpriteSearchWorker
from spritepal.ui.styles import get_panel_style, get_preview_panel_style
from spritepal.ui.widgets.sprite_preview_widget import SpritePreviewWidget
from spritepal.utils.logging_config import get_logger

logger = get_logger(__name__)


class ManualOffsetDialog(SplitterDialog):
    """Dialog window for manual ROM offset control with enhanced features"""

    # Signals
    offset_changed: pyqtSignal = pyqtSignal(int)  # Current offset changed
    sprite_found: pyqtSignal = pyqtSignal(int, str)  # Sprite found at offset with name

    # Singleton instance
    _instance: ClassVar["ManualOffsetDialog | None"] = None


    @classmethod
    def get_instance(cls, parent: "QWidget | None" = None) -> "ManualOffsetDialog":
        """Get or create singleton instance
        
        Note: Singleton dialogs are created without a parent to prevent
        deletion when the parent is destroyed. The parent parameter is
        ignored to ensure singleton persistence.
        """
        if cls._instance is None:
            # Always create with parent=None for singletons
            cls._instance = cls(parent=None)
        return cls._instance

    def __init__(self, parent: "QWidget | None" = None) -> None:
        # UI Components - declare BEFORE super().__init__() to avoid overwriting
        self.rom_map: ROMMapWidget | None = None
        self.offset_widget: ManualOffsetWidget | None = None
        self.scan_controls: ScanControlsPanel | None = None
        self.import_export: ImportExportPanel | None = None
        self.status_panel: StatusPanel | None = None
        self.preview_widget: SpritePreviewWidget | None = None
        self.apply_btn: QPushButton | None = None

        # State
        self.rom_path: str = ""
        self.rom_size: int = 0x400000  # Default 4MB
        self._preview_timer: QTimer = QTimer()
        self._preview_timer.setSingleShot(True)
        self._preview_timer.timeout.connect(self._update_preview)

        # Manager references (set by set_rom_data)
        self.extraction_manager: ExtractionManager | None = None
        self.rom_extractor: ROMExtractor | None = None
        self._manager_mutex = QMutex()  # Thread safety for manager access

        # Worker references
        self.preview_worker: SpritePreviewWorker | None = None
        self.search_worker: SpriteSearchWorker | None = None

        # Fullscreen state
        self._is_fullscreen: bool = False
        self._normal_geometry: QRect | None = None

        super().__init__(
            parent=parent,
            title="Manual Offset Control - SpritePal",
            modal=False,
            size=(1200, 700),  # Reduced default height
            min_size=(1000, 600),  # Reduced minimum height
            with_status_bar=False,
            orientation=Qt.Orientation.Horizontal,
            splitter_handle_width=6
        )

        self._setup_ui()
        self._connect_signals()

        # Add window flags to keep it on top if desired
        self.setWindowFlags(
            self.windowFlags() |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        # Store original flags for fullscreen toggle
        self._original_window_flags = self.windowFlags()
        
        # IMPORTANT: Disable WA_DeleteOnClose for singleton dialogs
        # BaseDialog sets this to True, but singletons must persist
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, False)
        
        # Set window modality appropriately for parentless singleton
        if parent is None:
            self.setWindowModality(Qt.WindowModality.ApplicationModal)

    def _is_widget_valid(self, widget) -> bool:
        """Check if a Qt widget still has its underlying C++ object"""
        if widget is None:
            return False
        try:
            # Try to access a basic Qt property - this will raise RuntimeError if deleted
            _ = widget.objectName()
            return True
        except RuntimeError:
            # "wrapped C/C++ object has been deleted"
            return False

    def _widgets_are_valid(self) -> bool:
        """Check if all critical widgets are still valid"""
        critical_widgets = [
            self.rom_map, self.offset_widget, self.scan_controls,
            self.import_export, self.status_panel, self.preview_widget
        ]
        return all(self._is_widget_valid(widget) for widget in critical_widgets)

    def _reinitialize_ui(self) -> None:
        """Reinitialize UI components when widgets have been garbage collected"""
        logger.warning("Reinitializing ManualOffsetDialog UI due to Qt widget lifecycle cleanup")
        
        # Clear existing references to deleted widgets
        self.rom_map = None
        self.offset_widget = None
        self.scan_controls = None
        self.import_export = None
        self.status_panel = None
        self.preview_widget = None
        self.apply_btn = None
        
        # Recreate the UI
        self._setup_ui()
        self._connect_signals()
        
        # Restore ROM data if it was set
        if self.rom_path and self.extraction_manager:
            self.set_rom_data(self.rom_path, self.rom_size, self.extraction_manager)

    def ensure_widgets_valid(self) -> None:
        """Ensure widgets are valid, reinitializing if necessary (public method for tests)"""
        if not self._widgets_are_valid():
            self._reinitialize_ui()

    def _setup_ui(self):
        """Initialize the dialog-specific UI components"""
        # Create left panel with controls
        left_panel = self._create_left_panel()
        self.add_panel(left_panel, stretch_factor=0)

        # Create right panel with preview
        right_panel = self._create_right_panel()
        self.add_panel(right_panel, stretch_factor=1)

        # Set initial panel sizes
        self.main_splitter.setSizes([500, 400])

        # Override button box to add custom buttons
        self._setup_custom_buttons()

    def _create_left_panel(self) -> QWidget:
        """Create the left control panel"""
        panel = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(3, 3, 3, 3)  # Small margins
        layout.setSpacing(6)  # Tighter spacing between controls

        # ROM Map visualization at the top - more compact
        rom_map_group = QWidget()
        rom_map_group.setStyleSheet(get_panel_style())
        rom_map_layout = QVBoxLayout()
        rom_map_layout.setContentsMargins(8, 6, 8, 6)  # Reduced from 10,10,10,10
        rom_map_layout.setSpacing(3)  # Tighter spacing

        rom_map_label = QLabel("ROM Overview")
        rom_map_label.setStyleSheet("font-weight: bold; font-size: 12px; margin-bottom: 2px;")  # Smaller font and margin
        rom_map_layout.addWidget(rom_map_label)

        self.rom_map = ROMMapWidget(parent=rom_map_group)
        rom_map_layout.addWidget(self.rom_map)

        rom_map_group.setLayout(rom_map_layout)
        layout.addWidget(rom_map_group)

        # Manual offset widget (reusing existing widget) - set proper parent
        self.offset_widget = ManualOffsetWidget(parent=panel)
        layout.addWidget(self.offset_widget)

        # Scan controls panel - set proper parent
        self.scan_controls = ScanControlsPanel(parent=panel)
        layout.addWidget(self.scan_controls)

        # Import/Export panel - set proper parent
        self.import_export = ImportExportPanel(parent=panel)
        layout.addWidget(self.import_export)

        # Status panel - CRITICAL FIX: Pass parent to prevent Qt lifecycle bug
        # Bug #25: StatusPanel QLabel was being deleted prematurely due to missing parent
        self.status_panel = StatusPanel(parent=panel)
        layout.addWidget(self.status_panel)

        # Smaller stretch to reduce empty space
        layout.addStretch(1)  # Minimal stretch factor

        panel.setLayout(layout)
        panel.setMinimumWidth(500)
        panel.setMaximumWidth(600)

        return panel

    def _create_right_panel(self) -> QWidget:
        """Create the right preview panel"""
        panel = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(3, 3, 3, 3)  # Small margins
        layout.setSpacing(4)  # Tighter spacing

        # Sprite preview - set proper parent to prevent Qt lifecycle bugs
        self.preview_widget = SpritePreviewWidget("Live Preview", parent=panel)
        self.preview_widget.setStyleSheet(get_preview_panel_style())
        layout.addWidget(self.preview_widget)

        panel.setLayout(layout)
        return panel

    def _setup_custom_buttons(self):
        """Set up custom dialog buttons"""
        if self.button_box:
            # Clear existing buttons
            self.button_box.clear()

            # Add custom buttons
            self.apply_btn = self.button_box.addButton("Apply Offset", QDialogButtonBox.ButtonRole.AcceptRole)
            self.apply_btn.setToolTip("Use the current offset for extraction")

            close_btn = self.button_box.addButton("Close", QDialogButtonBox.ButtonRole.RejectRole)
            self.apply_btn.clicked.connect(self._apply_offset)
            if close_btn:
                close_btn.clicked.connect(self.hide)  # Hide instead of close to maintain state

    def _connect_signals(self):
        """Connect internal signals"""
        # Connect offset widget signals
        self.offset_widget.offset_changed.connect(self._on_offset_changed)
        self.offset_widget.find_next_clicked.connect(self._find_next_sprite)
        self.offset_widget.find_prev_clicked.connect(self._find_prev_sprite)

        # Connect ROM map
        self.rom_map.offset_clicked.connect(self._on_map_clicked)

        # Connect scan controls
        self.scan_controls.sprite_found.connect(self._on_scan_sprite_found)
        self.scan_controls.scan_status_changed.connect(self.status_panel.update_status)
        self.scan_controls.progress_update.connect(self.status_panel.update_progress)
        self.scan_controls.scan_started.connect(self._on_scan_started)
        self.scan_controls.scan_finished.connect(self._on_scan_finished)

        # Connect import/export
        self.import_export.sprites_imported.connect(self._on_sprites_imported)
        self.import_export.status_changed.connect(self.status_panel.update_status)

        # Connect custom buttons
        if self.apply_btn:
            _ = self.apply_btn.clicked.connect(self._apply_offset)

    def set_rom_data(self, rom_path: str, rom_size: int, extraction_manager: "ExtractionManager") -> None:
        """Set ROM data for the dialog"""
        with QMutexLocker(self._manager_mutex):
            self.rom_path = rom_path
            self.rom_size = rom_size
            self.extraction_manager = extraction_manager
            self.rom_extractor = extraction_manager.get_rom_extractor()

        # Update all components
        self.offset_widget.set_rom_size(rom_size)
        self.rom_map.set_rom_size(rom_size)
        self.scan_controls.set_rom_data(rom_path, rom_size, extraction_manager)
        self.scan_controls.set_rom_map(self.rom_map)
        self.import_export.set_rom_data(rom_path, rom_size)
        self.import_export.set_rom_map(self.rom_map)

        # Update window title with ROM name
        if rom_path:
            rom_name = os.path.basename(rom_path)
            self.setWindowTitle(f"Manual Offset Control - {rom_name}")

        # Connect cache signals for status updates
        self._connect_cache_signals()

    def _connect_cache_signals(self) -> None:
        """Connect extraction manager cache signals for status updates"""
        extraction_manager, _ = self._get_managers_safely()
        if not extraction_manager:
            return

        # Connect cache signals to update status panel
        extraction_manager.cache_hit.connect(self._on_cache_hit)
        extraction_manager.cache_miss.connect(self._on_cache_miss)
        extraction_manager.cache_saved.connect(self._on_cache_saved)

    def _on_cache_hit(self, cache_type: str, time_saved: float) -> None:
        """Handle cache hit - update status panel"""
        # Ensure widgets are valid before accessing them
        self.ensure_widgets_valid()
        
        # Update cache status to reflect any changes
        self.status_panel.update_cache_status()

        # Show cache hit message in status
        message = f"Loaded {cache_type.replace('_', ' ')} from cache (saved {time_saved:.1f}s)"
        self.status_panel.update_status(message)

    def _on_cache_miss(self, cache_type: str) -> None:
        """Handle cache miss - just for logging, don't update UI"""
        # Cache misses are normal, don't need UI feedback

    def _on_cache_saved(self, cache_type: str, count: int) -> None:
        """Handle cache saved - update status panel"""
        # Ensure widgets are valid before accessing them
        self.ensure_widgets_valid()
        
        # Update cache status to reflect new cached items
        self.status_panel.update_cache_status()

        # Show cache save message in status
        message = f"Saved {count} {cache_type.replace('_', ' ')} to cache"
        self.status_panel.update_status(message)

    def _get_managers_safely(self) -> tuple["ExtractionManager | None", "ROMExtractor | None"]:
        """Get manager references safely with thread protection"""
        with QMutexLocker(self._manager_mutex):
            return self.extraction_manager, self.rom_extractor

    def get_current_offset(self) -> int:
        """Get the current offset value"""
        # Ensure widgets are valid before accessing them
        self.ensure_widgets_valid() 
        return self.offset_widget.get_current_offset()

    def set_offset(self, offset: int):
        """Set the current offset"""
        # Ensure widgets are valid before accessing them
        self.ensure_widgets_valid()
        self.offset_widget.set_offset(offset)

    def _on_offset_changed(self, offset: int):
        """Handle offset changes from the widget"""
        # Update ROM map
        self.rom_map.set_current_offset(offset)

        # Update scan controls
        self.scan_controls.set_current_offset(offset)

        # Schedule preview update
        self._preview_timer.stop()
        self._preview_timer.start(50)  # 50ms delay

        # Emit signal for external listeners
        self.offset_changed.emit(offset)

    def _on_map_clicked(self, offset: int):
        """Handle clicks on the ROM map"""
        self.offset_widget.set_offset(offset)

    def _update_preview(self):
        """Update the sprite preview"""
        if not self.rom_path:
            return

        offset = self.get_current_offset()
        self.status_panel.update_status(f"Loading preview for 0x{offset:06X}...")

        # Clean up any existing preview worker
        if self.preview_worker:
            self.preview_worker.quit()
            if not self.preview_worker.wait(3000):  # 3 second timeout
                logger.warning("Preview worker cleanup timeout, terminating")
                self.preview_worker.terminate()
                _ = self.preview_worker.wait(1000)  # 1 second for termination

        # Get managers safely
        extraction_manager, rom_extractor = self._get_managers_safely()
        if not extraction_manager or not rom_extractor:
            self.status_panel.update_status("ROM not loaded")
            return

        # Try to find sprite configuration for this offset
        sprite_config = None
        sprite_name = f"manual_0x{offset:X}"

        # Look up known sprite configurations to see if this offset matches
        try:
            sprite_locations = extraction_manager.get_known_sprite_locations(self.rom_path)
            if sprite_locations:
                for name, pointer in sprite_locations.items():
                    if pointer.offset == offset:
                        sprite_config = pointer
                        sprite_name = name
                        logger.debug(f"Found matching sprite config: {name} at 0x{offset:06X}")
                        break
        except (FileNotFoundError, KeyError) as e:
            logger.debug(f"Sprite configuration not available: {e}")
            # This is expected for unknown ROMs or missing config files
        except OSError as e:
            logger.warning(f"I/O error reading sprite config: {e}")
            # Could retry here in the future
        except Exception as e:
            logger.warning(f"Unexpected error looking up sprite config: {e}")
            # Continue with default config

        # Create and start preview worker with sprite config if found
        self.preview_worker = SpritePreviewWorker(
            self.rom_path, offset, sprite_name, rom_extractor, sprite_config
        )
        self.preview_worker.preview_ready.connect(self._on_preview_ready)
        self.preview_worker.preview_error.connect(self._on_preview_error)
        self.preview_worker.start()

    def _on_preview_ready(self, tile_data: bytes, width: int, height: int, sprite_name: str):
        """Handle preview data ready"""
        self.preview_widget.load_sprite_from_4bpp(tile_data, width, height, sprite_name)
        self.status_panel.update_status(f"Sprite found at 0x{self.get_current_offset():06X}")

    def _on_preview_error(self, error_msg: str):
        """Handle preview error with enhanced recovery"""
        self.preview_widget.clear()
        self.preview_widget.info_label.setText("No sprite found")

        # Update status with user-friendly message and recovery suggestions
        offset = self.get_current_offset()
        if "decompression" in error_msg.lower() or "hal" in error_msg.lower():
            self.status_panel.update_status(
                f"No sprite data at 0x{offset:06X}. Use navigation to search."
            )
        elif "memory" in error_msg.lower() or "allocation" in error_msg.lower():
            self.status_panel.update_status(
                f"Memory error at 0x{offset:06X}. Try closing other applications."
            )
        elif "permission" in error_msg.lower() or "access" in error_msg.lower():
            self.status_panel.update_status(
                f"File access error at 0x{offset:06X}. Check ROM file permissions."
            )
        else:
            self.status_panel.update_status(
                f"Cannot read offset 0x{offset:06X}: {error_msg}"
            )

    def _find_next_sprite(self):
        """Find next sprite offset"""
        if not self.rom_path:
            return

        # Get managers safely
        extraction_manager, rom_extractor = self._get_managers_safely()
        if not rom_extractor:
            self.status_panel.update_status("ROM not loaded")
            return

        current_offset = self.get_current_offset()
        step = self.offset_widget.get_step_size()

        self.status_panel.update_status(f"Searching forward from 0x{current_offset:06X}...")
        self.offset_widget.set_navigation_enabled(False)

        # Clean up any existing search worker
        if self.search_worker:
            self.search_worker.quit()
            if not self.search_worker.wait(3000):  # 3 second timeout
                logger.warning("Search worker cleanup timeout, terminating")
                self.search_worker.terminate()
                _ = self.search_worker.wait(1000)  # 1 second for termination

        # Create worker to search for next sprite
        self.search_worker = SpriteSearchWorker(
            self.rom_path, current_offset, step, self.rom_size, rom_extractor, forward=True
        )
        self.search_worker.sprite_found.connect(self._on_sprite_found)
        self.search_worker.search_complete.connect(self._on_search_complete)
        self.search_worker.start()

    def _find_prev_sprite(self):
        """Find previous sprite offset"""
        if not self.rom_path:
            return

        # Get managers safely
        extraction_manager, rom_extractor = self._get_managers_safely()
        if not rom_extractor:
            self.status_panel.update_status("ROM not loaded")
            return

        current_offset = self.get_current_offset()
        step = self.offset_widget.get_step_size()

        self.status_panel.update_status(f"Searching backward from 0x{current_offset:06X}...")
        self.offset_widget.set_navigation_enabled(False)

        # Clean up any existing search worker
        if self.search_worker:
            self.search_worker.quit()
            if not self.search_worker.wait(3000):  # 3 second timeout
                logger.warning("Search worker cleanup timeout, terminating")
                self.search_worker.terminate()
                _ = self.search_worker.wait(1000)  # 1 second for termination

        # Create worker to search for previous sprite
        self.search_worker = SpriteSearchWorker(
            self.rom_path, current_offset, step, self.rom_size, rom_extractor, forward=False
        )
        self.search_worker.sprite_found.connect(self._on_sprite_found)
        self.search_worker.search_complete.connect(self._on_search_complete)
        self.search_worker.start()

    def _on_sprite_found(self, offset: int, quality: float):
        """Handle sprite found during search"""
        self.offset_widget.set_offset(offset)
        self.add_found_sprite(offset, quality)
        self.status_panel.update_status(
            f"Found sprite at 0x{offset:06X} (quality: {quality:.2f})"
        )

    def _on_search_complete(self, found: bool):
        """Handle search completion"""
        self.offset_widget.set_navigation_enabled(True)

        if not found:
            self.status_panel.update_status(
                "No valid sprites found in search range. Try a different area."
            )

    def _on_scan_sprite_found(self, offset: int, quality: float):
        """Handle sprite found during scanning"""
        self.add_found_sprite(offset, quality)

    def _on_scan_started(self):
        """Handle scan started"""
        # Show progress bar
        self.status_panel.show_progress(0, self.rom_size)

    def _on_scan_finished(self):
        """Handle scan finished"""
        # Hide progress bar
        self.status_panel.hide_progress()

        # Update import/export with found sprites
        sprites = self.scan_controls.get_found_sprites()
        self.import_export.set_found_sprites(sprites)

    def _on_sprites_imported(self, sprites: list[tuple[int, float]]):
        """Handle sprites imported from file"""
        # Add imported sprites to scan controls
        for offset, quality in sprites:
            self.add_found_sprite(offset, quality)

    def _apply_offset(self):
        """Apply the current offset and close dialog"""
        offset = self.get_current_offset()
        self.sprite_found.emit(offset, f"manual_0x{offset:X}")
        self.hide()

    def add_found_sprite(self, offset: int, quality: float = 1.0):
        """Add a found sprite to the visualization"""
        self.rom_map.add_found_sprite(offset, quality)
        self.offset_widget.add_found_sprite(offset)

    @override
    def keyPressEvent(self, a0: QKeyEvent | None):
        """Handle keyboard shortcuts"""
        # Let the offset widget handle its shortcuts first
        if a0:
            self.offset_widget.keyPressEvent(a0)

        # Dialog-specific shortcuts
        if a0:
            if a0.key() == Qt.Key.Key_Escape:
                if self._is_fullscreen:
                    self._toggle_fullscreen()
                    a0.accept()
                else:
                    self.hide()
                    a0.accept()
            elif a0.key() == Qt.Key.Key_F11:
                self._toggle_fullscreen()
                a0.accept()
            elif (a0.key() == Qt.Key.Key_Return or a0.key() == Qt.Key.Key_Enter) and a0.modifiers() == Qt.KeyboardModifier.NoModifier:
                self._apply_offset()
                a0.accept()

        super().keyPressEvent(a0)

    @override
    def mouseDoubleClickEvent(self, a0: QMouseEvent | None):
        """Handle double-click on title bar to toggle fullscreen"""
        if a0 and a0.button() == Qt.MouseButton.LeftButton and a0.position().y() <= 30:
            # Double-click on title bar area (top 30 pixels)
            self._toggle_fullscreen()
            a0.accept()
            return

        super().mouseDoubleClickEvent(a0)

    def _toggle_fullscreen(self):
        """Toggle between fullscreen and normal window mode"""
        if self._is_fullscreen:
            # Exit fullscreen - restore original window flags
            self.setWindowFlags(self._original_window_flags)
            self.showNormal()
            if self._normal_geometry:
                self.setGeometry(self._normal_geometry)
            self._is_fullscreen = False
            self.setWindowTitle("Manual Offset Control - SpritePal")
        else:
            # Enter fullscreen - use clean window flags for true fullscreen
            self._normal_geometry = self.geometry()
            self.setWindowFlags(Qt.WindowType.Window)
            self.showFullScreen()
            self._is_fullscreen = True
            self.setWindowTitle("Manual Offset Control - SpritePal (Fullscreen - F11 or Esc to exit)")

    def _cleanup_workers(self):
        """Clean up any running worker threads with timeouts to prevent hangs"""
        # Stop preview worker
        if self.preview_worker:
            self.preview_worker.quit()
            if not self.preview_worker.wait(5000):  # 5 second timeout
                logger.warning("Preview worker did not stop gracefully, terminating")
                self.preview_worker.terminate()
                if not self.preview_worker.wait(2000):  # 2 second timeout for termination
                    logger.error("Preview worker failed to terminate")
            self.preview_worker = None

        # Stop search worker
        if self.search_worker:
            self.search_worker.quit()
            if not self.search_worker.wait(5000):  # 5 second timeout
                logger.warning("Search worker did not stop gracefully, terminating")
                self.search_worker.terminate()
                if not self.search_worker.wait(2000):  # 2 second timeout for termination
                    logger.error("Search worker failed to terminate")
            self.search_worker = None

        # Clean up scan controls workers
        self.scan_controls.cleanup_workers()

    @override
    def closeEvent(self, a0: QCloseEvent | None):
        """Handle close event - hide instead of destroying"""
        self._cleanup_workers()
        if a0:
            a0.ignore()
        self.hide()

    @override
    def hideEvent(self, a0: QHideEvent | None):
        """Handle hide event - cleanup workers"""
        self._cleanup_workers()
        if a0:
            super().hideEvent(a0)
