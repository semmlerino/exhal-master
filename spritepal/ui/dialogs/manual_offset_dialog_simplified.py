"""
Manual Offset Control Dialog - Simplified Architecture

A streamlined version of ManualOffsetDialog that eliminates the over-engineered MVP
pattern with 4 services. Consolidates all business logic directly in the dialog class
while preserving all functionality.

This replaces the complex service coordination with direct implementation to fix
Qt lifecycle issues and eliminate "buggy and janky" behavior.
"""

import os
from typing import TYPE_CHECKING, override

if TYPE_CHECKING:
    from spritepal.core.managers.extraction_manager import ExtractionManager
    from spritepal.core.rom_extractor import ROMExtractor

from PyQt6.QtCore import QMutex, QMutexLocker, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QCloseEvent, QHideEvent, QKeyEvent, QMouseEvent
from PyQt6.QtWidgets import (
    QDialogButtonBox,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from spritepal.ui.common import WorkerManager
from spritepal.ui.components import DialogBase
from spritepal.ui.components.panels import (
    ImportExportPanel,
    ScanControlsPanel,
    StatusPanel,
)
from spritepal.ui.components.visualization import ROMMapWidget
from spritepal.ui.dialogs.services import ViewStateManager
from spritepal.ui.rom_extraction.widgets.manual_offset_widget import ManualOffsetWidget
from spritepal.ui.rom_extraction.workers import SpritePreviewWorker, SpriteSearchWorker
from spritepal.ui.styles import get_panel_style, get_borderless_preview_style
from spritepal.ui.widgets.sprite_preview_widget import SpritePreviewWidget
from spritepal.utils.logging_config import get_logger

logger = get_logger(__name__)


class ManualOffsetDialogSimplified(DialogBase):
    """Simplified Manual Offset Control Dialog with direct business logic.

    Eliminates the over-engineered MVP pattern with 4 services, consolidating
    all business logic directly in the dialog class. This fixes Qt lifecycle
    issues while preserving all functionality.
    """

    # External signals (for ROM extraction panel integration)
    offset_changed: pyqtSignal = pyqtSignal(int)  # Current offset changed
    sprite_found: pyqtSignal = pyqtSignal(int, str)  # Sprite found at offset with name

    def __init__(self, parent: "QWidget | None" = None) -> None:
        # UI Components - declare BEFORE super().__init__() to avoid overwriting
        self.rom_map: ROMMapWidget | None = None
        self.offset_widget: ManualOffsetWidget | None = None
        self.scan_controls: ScanControlsPanel | None = None
        self.import_export: ImportExportPanel | None = None
        self.status_panel: StatusPanel | None = None
        self.preview_widget: SpritePreviewWidget | None = None
        self.apply_btn: QPushButton | None = None

        # Business logic state - declare BEFORE super().__init__()
        self.rom_path: str = ""
        self.rom_size: int = 0x400000  # Default 4MB
        self._current_offset: int = 0x200000  # Start at 2MB
        self._found_sprites: list[tuple[int, float]] = []

        # Manager references with thread safety
        self.extraction_manager: ExtractionManager | None = None
        self.rom_extractor: ROMExtractor | None = None
        self._manager_mutex = QMutex()

        # Worker references
        self.preview_worker: SpritePreviewWorker | None = None
        self.search_worker: SpriteSearchWorker | None = None

        # Preview update timer for debouncing
        self._preview_timer: QTimer | None = None

        # Navigation state
        self._navigation_enabled = True

        # Cache signal connections
        self._cache_signals_connected = False

        super().__init__(
            parent=parent,
            title="Manual Offset Control - SpritePal",
            modal=False,
            size=(1000, 650),  # More reasonable default size
            min_size=(800, 500),  # More reasonable minimum size
            with_status_bar=False,
            orientation=Qt.Orientation.Horizontal,
            splitter_handle_width=6
        )

        # Initialize ONLY the view state manager (positioning works well)
        self.view_state_manager = ViewStateManager(self, self)

        self._setup_ui()
        self._setup_preview_timer()
        self._connect_signals()
        self._connect_view_state_signals()

    def _setup_preview_timer(self) -> None:
        """Setup debouncing timer for preview updates"""
        self._preview_timer = QTimer()
        self._preview_timer.setSingleShot(True)
        self._preview_timer.timeout.connect(self._update_preview)

    def _setup_ui(self):
        """Initialize the dialog-specific UI components"""
        # Create left panel with controls
        left_panel = self._create_left_panel()
        self.add_panel(left_panel, stretch_factor=0)

        # Create right panel with preview
        right_panel = self._create_right_panel()
        self.add_panel(right_panel, stretch_factor=1)

        # Set initial panel sizes proportionally
        # Left panel (controls): ~55%, Right panel (preview): ~45%
        total_width = self.width()
        left_width = int(total_width * 0.55)
        right_width = total_width - left_width
        self.main_splitter.setSizes([left_width, right_width])

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
        # More flexible sizing - adjust based on dialog size
        dialog_width = self.width()
        min_left_width = max(400, int(dialog_width * 0.4))  # At least 400px or 40% of dialog
        max_left_width = min(700, int(dialog_width * 0.7))  # At most 700px or 70% of dialog

        panel.setMinimumWidth(min_left_width)
        panel.setMaximumWidth(max_left_width)

        return panel

    def _create_right_panel(self) -> QWidget:
        """Create the right preview panel"""
        panel = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)  # Zero margins for maximum space efficiency
        layout.setSpacing(0)  # Zero spacing for maximum space efficiency

        # Sprite preview - set proper parent to prevent Qt lifecycle bugs  
        # SPACE EFFICIENCY: Use borderless style to eliminate wasted space
        self.preview_widget = SpritePreviewWidget("Live Preview", parent=panel)
        self.preview_widget.setStyleSheet(get_borderless_preview_style())
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
        """Connect internal signals directly (no service layer)"""
        # Connect offset widget signals
        if self.offset_widget:
            self.offset_widget.offset_changed.connect(self._on_offset_changed)
            self.offset_widget.find_next_clicked.connect(self._find_next_sprite)
            self.offset_widget.find_prev_clicked.connect(self._find_prev_sprite)

        # Connect ROM map
        if self.rom_map:
            self.rom_map.offset_clicked.connect(self._on_map_clicked)

        # Connect scan controls directly (no controller layer)
        if self.scan_controls:
            self.scan_controls.sprite_found.connect(self._on_sprite_found_during_scan)
            self.scan_controls.scan_status_changed.connect(self._update_status)
            self.scan_controls.progress_update.connect(self._on_scan_progress_update)
            self.scan_controls.scan_started.connect(self._on_scan_started)
            self.scan_controls.scan_finished.connect(self._on_scan_finished)
            self.scan_controls.partial_scan_detected.connect(self._on_partial_scan_detected)

        # Connect import/export directly (no controller layer)
        if self.import_export:
            self.import_export.sprites_imported.connect(self._on_sprites_imported)
            self.import_export.status_changed.connect(self._update_status)

    def _connect_view_state_signals(self) -> None:
        """Connect view state manager signals"""
        self.view_state_manager.fullscreen_toggled.connect(self._on_fullscreen_toggled)
        self.view_state_manager.title_changed.connect(self.setWindowTitle)

    # ROM Data Management (consolidated from ROMDataSession)

    def set_rom_data(self, rom_path: str, rom_size: int, extraction_manager: "ExtractionManager") -> None:
        """Set ROM data for the dialog"""
        with QMutexLocker(self._manager_mutex):
            self.rom_path = rom_path
            self.rom_size = rom_size
            self.extraction_manager = extraction_manager
            self.rom_extractor = extraction_manager.get_rom_extractor()

        # Connect cache signals if not already connected
        self._connect_cache_signals()

        # Update UI components with new ROM data
        self._update_ui_with_rom_data(rom_path, rom_size)

        # Update window title with ROM name
        self.view_state_manager.update_title_with_rom(rom_path)

        logger.debug(f"ROM data updated: {os.path.basename(rom_path)} ({rom_size} bytes)")

    def _update_ui_with_rom_data(self, rom_path: str, rom_size: int) -> None:
        """Update UI components with new ROM data"""
        if self.offset_widget:
            self.offset_widget.set_rom_size(rom_size)
        if self.rom_map:
            self.rom_map.set_rom_size(rom_size)
        if self.scan_controls:
            self.scan_controls.set_rom_data(rom_path, rom_size, self.extraction_manager)
            self.scan_controls.set_rom_map(self.rom_map)
        if self.import_export:
            self.import_export.set_rom_data(rom_path, rom_size)
            self.import_export.set_rom_map(self.rom_map)

    def _get_managers_safely(self) -> tuple["ExtractionManager | None", "ROMExtractor | None"]:
        """Get manager references safely with thread protection"""
        with QMutexLocker(self._manager_mutex):
            return self.extraction_manager, self.rom_extractor

    def _connect_cache_signals(self) -> None:
        """Connect extraction manager cache signals for forwarding"""
        if self._cache_signals_connected:
            return

        extraction_manager, _ = self._get_managers_safely()
        if not extraction_manager:
            return

        try:
            # Connect cache signals to handle them directly
            extraction_manager.cache_hit.connect(self._on_cache_hit)
            extraction_manager.cache_miss.connect(self._on_cache_miss)
            extraction_manager.cache_saved.connect(self._on_cache_saved)
            self._cache_signals_connected = True
            logger.debug("Cache signals connected")
        except Exception as e:
            logger.warning(f"Failed to connect cache signals: {e}")

    # Offset Management (consolidated from ROMDataSession)

    def get_current_offset(self) -> int:
        """Get the current offset value"""
        return self._current_offset

    def set_offset(self, offset: int) -> None:
        """Set the current offset"""
        # Update UI widget first
        if self.offset_widget:
            self.offset_widget.set_offset(offset)
        # Update internal state
        self._set_current_offset(offset)

    def _set_current_offset(self, offset: int) -> None:
        """Set current offset and trigger coordination"""
        if self._current_offset != offset:
            self._current_offset = offset

            # Update UI components
            if self.rom_map:
                self.rom_map.set_current_offset(offset)
            if self.scan_controls:
                self.scan_controls.set_current_offset(offset)

            # Request preview update with debouncing
            self._request_preview_update(50)

            # Emit signal for external listeners (ROM extraction panel)
            self.offset_changed.emit(offset)

    def _on_offset_changed(self, offset: int) -> None:
        """Handle offset changes from the widget"""
        self._set_current_offset(offset)

    def _on_map_clicked(self, offset: int) -> None:
        """Handle clicks on the ROM map"""
        self.set_offset(offset)

    # Found Sprites Management (consolidated from ROMDataSession)

    def add_found_sprite(self, offset: int, quality: float = 1.0) -> None:
        """Add a found sprite to the collection"""
        sprite_entry = (offset, quality)
        if sprite_entry not in self._found_sprites:
            self._found_sprites.append(sprite_entry)

            # Update visualization components
            if self.rom_map:
                self.rom_map.add_found_sprite(offset, quality)
            if self.offset_widget:
                self.offset_widget.add_found_sprite(offset)

            logger.debug(f"Added found sprite at 0x{offset:06X} (quality: {quality:.2f})")

    # Sprite Operations (consolidated from OffsetExplorationService)

    def _request_preview_update(self, delay_ms: int = 50) -> None:
        """Request a preview update with debouncing"""
        if self._preview_timer:
            self._preview_timer.stop()
            self._preview_timer.start(delay_ms)

    def _find_next_sprite(self) -> None:
        """Find next sprite offset"""
        if self.offset_widget:
            step_size = self.offset_widget.get_step_size()
            self._find_next_sprite_with_step(step_size)

    def _find_prev_sprite(self) -> None:
        """Find previous sprite offset"""
        if self.offset_widget:
            step_size = self.offset_widget.get_step_size()
            self._find_previous_sprite_with_step(step_size)

    def _find_next_sprite_with_step(self, step_size: int) -> None:
        """Find next sprite offset with given step size"""
        if not self._has_rom_data():
            self._update_status("No ROM loaded")
            return

        _, rom_extractor = self._get_managers_safely()
        if not rom_extractor:
            self._update_status("ROM extractor not available")
            return

        current_offset = self.get_current_offset()
        self._update_status(f"Searching forward from 0x{current_offset:06X}...")
        self._set_navigation_enabled(False)

        # Clean up any existing search worker
        WorkerManager.cleanup_worker(self.search_worker, timeout=1000)
        self.search_worker = None

        # Create worker to search for next sprite
        self.search_worker = SpriteSearchWorker(
            self.rom_path, current_offset, step_size, self.rom_size, rom_extractor, forward=True
        )
        self.search_worker.sprite_found.connect(self._on_sprite_found_during_search)
        self.search_worker.search_complete.connect(self._on_search_complete)
        self.search_worker.start()

    def _find_previous_sprite_with_step(self, step_size: int) -> None:
        """Find previous sprite offset with given step size"""
        if not self._has_rom_data():
            self._update_status("No ROM loaded")
            return

        _, rom_extractor = self._get_managers_safely()
        if not rom_extractor:
            self._update_status("ROM extractor not available")
            return

        current_offset = self.get_current_offset()
        self._update_status(f"Searching backward from 0x{current_offset:06X}...")
        self._set_navigation_enabled(False)

        # Clean up any existing search worker
        WorkerManager.cleanup_worker(self.search_worker, timeout=1000)
        self.search_worker = None

        # Create worker to search for previous sprite
        self.search_worker = SpriteSearchWorker(
            self.rom_path, current_offset, step_size, self.rom_size, rom_extractor, forward=False
        )
        self.search_worker.sprite_found.connect(self._on_sprite_found_during_search)
        self.search_worker.search_complete.connect(self._on_search_complete)
        self.search_worker.start()

    def _update_preview(self) -> None:
        """Update the sprite preview for current offset"""
        if not self._has_rom_data():
            return

        current_offset = self.get_current_offset()
        self._update_status(f"Loading preview for 0x{current_offset:06X}...")

        # Clean up any existing preview worker
        WorkerManager.cleanup_worker(self.preview_worker, timeout=1000)
        self.preview_worker = None

        # Get managers safely
        extraction_manager, rom_extractor = self._get_managers_safely()
        if not extraction_manager or not rom_extractor:
            self._update_status("ROM not loaded")
            return

        # Try to find sprite configuration for this offset
        sprite_config = None
        sprite_name = f"manual_0x{current_offset:X}"

        # Look up known sprite configurations to see if this offset matches
        try:
            sprite_locations = extraction_manager.get_known_sprite_locations(self.rom_path)
            if sprite_locations:
                for name, pointer in sprite_locations.items():
                    if pointer.offset == current_offset:
                        sprite_config = pointer
                        sprite_name = name
                        logger.debug(f"Found matching sprite config: {name} at 0x{current_offset:06X}")
                        break
        except (FileNotFoundError, KeyError) as e:
            logger.debug(f"Sprite configuration not available: {e}")
            # This is expected for unknown ROMs or missing config files
        except OSError as e:
            logger.warning(f"I/O error reading sprite config: {e}")
        except Exception as e:
            logger.warning(f"Unexpected error looking up sprite config: {e}")

        # Create and start preview worker with sprite config if found
        self.preview_worker = SpritePreviewWorker(
            self.rom_path, current_offset, sprite_name, rom_extractor, sprite_config
        )
        self.preview_worker.preview_ready.connect(self._on_preview_ready)
        self.preview_worker.preview_error.connect(self._on_preview_error)
        self.preview_worker.start()

    # Signal Handlers (consolidated from controller)

    def _on_preview_ready(self, tile_data: bytes, width: int, height: int, sprite_name: str) -> None:
        """Handle preview data ready"""
        if self.preview_widget:
            self.preview_widget.load_sprite_from_4bpp(tile_data, width, height, sprite_name)

        current_offset = self.get_current_offset()
        self._update_status(f"Sprite found at 0x{current_offset:06X}")

    def _on_preview_error(self, error_msg: str) -> None:
        """Handle preview error with enhanced recovery"""
        if self.preview_widget:
            self.preview_widget.clear()
            self.preview_widget.info_label.setText("No sprite found")

        # Update status with user-friendly message and recovery suggestions
        current_offset = self.get_current_offset()
        if "decompression" in error_msg.lower() or "hal" in error_msg.lower():
            self._update_status(
                f"No sprite data at 0x{current_offset:06X}. Use navigation to search."
            )
        elif "memory" in error_msg.lower() or "allocation" in error_msg.lower():
            self._update_status(
                f"Memory error at 0x{current_offset:06X}. Try closing other applications."
            )
        elif "permission" in error_msg.lower() or "access" in error_msg.lower():
            self._update_status(
                f"File access error at 0x{current_offset:06X}. Check ROM file permissions."
            )
        else:
            self._update_status(
                f"Cannot read offset 0x{current_offset:06X}: {error_msg}"
            )

    def _on_sprite_found_during_search(self, offset: int, quality: float) -> None:
        """Handle sprite found during search"""
        self._set_current_offset(offset)
        self.add_found_sprite(offset, quality)
        self._update_status(
            f"Found sprite at 0x{offset:06X} (quality: {quality:.2f})"
        )

    def _on_search_complete(self, found: bool) -> None:
        """Handle search completion"""
        self._set_navigation_enabled(True)

        if self.offset_widget:
            self.offset_widget.set_navigation_enabled(True)

        if not found:
            self._update_status(
                "No valid sprites found in search range. Try a different area."
            )

    def _on_sprite_found_during_scan(self, offset: int, quality: float) -> None:
        """Handle sprite found during scan operation"""
        self.add_found_sprite(offset, quality)

    def _on_scan_progress_update(self, current_offset: int, progress_pct: int) -> None:
        """Handle scan progress update"""
        # Use progress percentage for accurate progress display
        if self.status_panel:
            self.status_panel.show_progress(progress_pct, 100)  # Show percentage out of 100

    def _on_scan_started(self) -> None:
        """Handle scan started"""
        if self.status_panel:
            self.status_panel.show_progress(0, 100)  # Start at 0% out of 100%

    def _on_scan_finished(self, found_sprites: list) -> None:
        """Handle scan finished"""
        if self.status_panel:
            self.status_panel.hide_progress()

        # Update import/export with found sprites
        if self.import_export:
            self.import_export.set_found_sprites(found_sprites)

    def _on_partial_scan_detected(self, scan_info: dict) -> None:
        """Handle detection of partial scan cache - show ResumeScanDialog"""
        try:
            from spritepal.ui.dialogs import ResumeScanDialog
            user_choice = ResumeScanDialog.show_resume_dialog(scan_info, self)

            if user_choice == ResumeScanDialog.RESUME:
                # User wants to resume - the next scan will automatically pick up from cache
                self._update_status("Ready to resume cached scan. Click 'Scan Range' or 'Scan Entire ROM' to continue.")
            elif user_choice == ResumeScanDialog.START_FRESH:
                # User wants fresh scan - clear the cache for this ROM
                self._clear_rom_cache()
                self._update_status("Cache cleared. Next scan will start fresh.")
            # If CANCEL, do nothing - user can start scans manually later

        except Exception as e:
            logger.warning(f"Error handling partial scan detection: {e}")
            self._update_status("Cache detection failed, but scans can still be performed.")

    def _on_sprites_imported(self, sprites: list[tuple[int, float]]) -> None:
        """Handle sprites imported from file"""
        for offset, quality in sprites:
            self.add_found_sprite(offset, quality)

    def _on_cache_hit(self, cache_type: str, time_saved: float) -> None:
        """Handle cache hit"""
        message = f"Loaded {cache_type.replace('_', ' ')} from cache (saved {time_saved:.1f}s)"
        if self.status_panel:
            self.status_panel.update_cache_status()
            self.status_panel.update_status(message)

    def _on_cache_miss(self, cache_type: str) -> None:
        """Handle cache miss"""
        # Cache misses are normal, don't need special handling
        logger.debug(f"Cache miss for {cache_type}")

    def _on_cache_saved(self, cache_type: str, count: int) -> None:
        """Handle cache saved"""
        message = f"Saved {count} {cache_type.replace('_', ' ')} to cache"
        if self.status_panel:
            self.status_panel.update_status(message)

    def _on_fullscreen_toggled(self, is_fullscreen: bool) -> None:
        """Handle fullscreen toggle"""
        # UI can react to fullscreen changes if needed

    # Main Operations

    def _apply_offset(self) -> None:
        """Apply the current offset and close dialog"""
        offset = self.get_current_offset()
        sprite_name = f"manual_0x{offset:X}"
        self.sprite_found.emit(offset, sprite_name)
        self.hide()

    # Utility Methods

    def _has_rom_data(self) -> bool:
        """Check if ROM data is loaded"""
        return bool(self.rom_path and self.rom_size > 0)

    def _update_status(self, message: str) -> None:
        """Update status message"""
        if self.status_panel:
            self.status_panel.update_status(message)

    def _clear_rom_cache(self) -> None:
        """Clear cache for the current ROM"""
        if not self.rom_path:
            return

        try:
            from spritepal.utils.rom_cache import get_rom_cache
            rom_cache = get_rom_cache()

            # Clear scan progress caches for this ROM
            removed_count = rom_cache.clear_scan_progress_cache(self.rom_path)
            logger.info(f"Cleared {removed_count} cache entries for ROM: {os.path.basename(self.rom_path)}")

        except Exception as e:
            logger.warning(f"Error clearing ROM cache: {e}")

    def _set_navigation_enabled(self, enabled: bool) -> None:
        """Set navigation enabled state"""
        self._navigation_enabled = enabled

    def _cleanup_workers(self) -> None:
        """Clean up any running worker threads with timeouts to prevent hangs"""
        # Use WorkerManager for consistent cleanup
        WorkerManager.cleanup_worker(self.preview_worker, timeout=2000)
        self.preview_worker = None

        WorkerManager.cleanup_worker(self.search_worker, timeout=2000)
        self.search_worker = None

        # Clean up scan controls workers
        if hasattr(self, "scan_controls") and self.scan_controls:
            try:
                self.scan_controls.cleanup_workers()
            except RuntimeError as e:
                logger.warning(f"Error cleaning up scan controls workers: {e}")

        logger.debug("Dialog workers cleaned up")

    # Event Handlers

    @override
    def keyPressEvent(self, a0: QKeyEvent | None):
        """Handle keyboard shortcuts"""
        # Let the offset widget handle its shortcuts first
        if a0 and self.offset_widget:
            self.offset_widget.keyPressEvent(a0)

        # Dialog-specific shortcuts
        if a0:
            if a0.key() == Qt.Key.Key_Escape:
                if self.view_state_manager.handle_escape_key():
                    a0.accept()
                else:
                    self.hide()
                    a0.accept()
            elif a0.key() == Qt.Key.Key_F11:
                self.view_state_manager.toggle_fullscreen()
                a0.accept()
            elif a0.key() == Qt.Key.Key_R and a0.modifiers() == Qt.KeyboardModifier.ControlModifier:
                # Ctrl+R to reset dialog position if it gets stuck off-screen
                self.view_state_manager.reset_to_safe_position()
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
            self.view_state_manager.toggle_fullscreen()
            a0.accept()
            return

        super().mouseDoubleClickEvent(a0)

    @override
    def closeEvent(self, a0: QCloseEvent | None):
        """Handle close event - clean up and close properly"""
        self._cleanup_workers()
        if a0:
            super().closeEvent(a0)  # Let parent handle close event normally

    @override
    def hideEvent(self, a0: QHideEvent | None):
        """Handle hide event - cleanup workers and save position"""
        self._cleanup_workers()
        self.view_state_manager.handle_hide_event()

        if a0:
            super().hideEvent(a0)

    def showEvent(self, event):  # noqa: N802
        """Handle show event - restore position if available"""
        super().showEvent(event)
        self.view_state_manager.handle_show_event()
