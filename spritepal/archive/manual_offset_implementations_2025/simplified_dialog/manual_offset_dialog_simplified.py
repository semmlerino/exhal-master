"""
Manual Offset Control Dialog - Simplified Architecture

A streamlined manual offset dialog that consolidates business logic directly in the 
dialog class while leveraging well-designed components for UI organization. Features 
tab-based navigation, integrated sprite searching, and robust resource management.

Key improvements:
- Clean component delegation (tabs, registry, navigator)
- Thread-safe offset management with queue-based updates  
- Comprehensive worker and resource cleanup
- Signal flow designed to prevent loops and race conditions
- Centralized sprite management through registry pattern
"""

import os
import weakref
from collections import deque
from typing import TYPE_CHECKING, Any, override

if TYPE_CHECKING:
    from core.managers.extraction_manager import ExtractionManager
    from core.rom_extractor import ROMExtractor
    from ui.dialogs.manual_offset.cache_event_handler import CacheEventHandler

from PyQt6.QtCore import QMutex, QMutexLocker, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QCloseEvent, QHideEvent, QKeyEvent, QMouseEvent
from PyQt6.QtWidgets import QPushButton, QWidget

from ui.common import WorkerManager
from ui.components import DialogBase
from ui.components.panels import (
    ImportExportPanel,
    ScanControlsPanel,
    StatusPanel,
)
from ui.components.visualization import ROMMapWidget
from ui.dialogs.manual_offset import (
    FoundSpritesRegistry,
    TabbedManualOffsetWidget,
)
from ui.dialogs.manual_offset.offset_navigator import OffsetNavigator
from ui.dialogs.manual_offset.data_structures import FoundSprite
from ui.dialogs.manual_offset.panel_factory import PanelFactory
from ui.dialogs.services import ViewStateManager
from ui.rom_extraction.workers import SpritePreviewWorker, SpriteSearchWorker
from ui.widgets.sprite_preview_widget import SpritePreviewWidget
from utils.logging_config import get_logger
from utils.preview_generator import get_preview_generator, create_rom_preview_request

logger = get_logger(__name__)


# Module-level helper classes to avoid circular references
class _SimpleROMDataManager:
    """ROM data manager implementation using weak reference to parent dialog.
    
    This class is extracted to module level to avoid circular references that
    occur when inline classes hold strong references to their parent.
    """
    
    def __init__(self, dialog_ref: "weakref.ref[ManualOffsetDialogSimplified]"):
        """Initialize with weak reference to parent dialog.
        
        Args:
            dialog_ref: Weak reference to the parent dialog
        """
        self._dialog_ref = dialog_ref
        
    def has_rom_data(self) -> bool:
        """Check if ROM data is available."""
        dialog = self._dialog_ref()
        if dialog is None:
            return False
        return dialog._has_rom_data()
        
    def get_rom_config(self):
        """Get ROM configuration if available."""
        dialog = self._dialog_ref()
        if dialog is None:
            return None
            
        from ui.dialogs.manual_offset.data_structures import ROMConfiguration
        if dialog.rom_path:
            return ROMConfiguration(
                path=dialog.rom_path,
                size=dialog.rom_size,
                checksum=None  # Simplified for testing
            )
        return None
        
    def get_rom_extractor(self):
        """Get ROM extractor from dialog managers.
        
        WARNING: This method has inherent TOCTOU risk as the extractor
        could be deleted after this method returns. Callers should be
        prepared to handle None or invalid references.
        """
        dialog = self._dialog_ref()
        if dialog is None:
            return None
            
        # Hold lock while accessing to prevent mid-access deletion
        with QMutexLocker(dialog._manager_mutex):
            return dialog.rom_extractor
        
    def __del__(self):
        """Cleanup to ensure no lingering references."""
        self._dialog_ref = None


class _SimpleStatusReporter:
    """Status reporter implementation using weak reference to parent dialog.
    
    This class is extracted to module level to avoid circular references that
    occur when inline classes hold strong references to their parent.
    """
    
    def __init__(self, dialog_ref: "weakref.ref[ManualOffsetDialogSimplified]"):
        """Initialize with weak reference to parent dialog.
        
        Args:
            dialog_ref: Weak reference to the parent dialog
        """
        self._dialog_ref = dialog_ref
        
    def update_status(self, update):
        """Update status through the parent dialog."""
        dialog = self._dialog_ref()
        if dialog is not None:
            dialog._update_status(update.message)
            
    def report_error(self, message: str, details: str | None = None):
        """Report error through the parent dialog."""
        dialog = self._dialog_ref()
        if dialog is not None:
            dialog._update_status(f"Error: {message}")
            
    def __del__(self):
        """Cleanup to ensure no lingering references."""
        self._dialog_ref = None


class ManualOffsetDialogSimplified(DialogBase):
    """Simplified Manual Offset Control Dialog with direct business logic.

    Eliminates the over-engineered MVP pattern with 4 services, consolidating
    all business logic directly in the dialog class. This fixes Qt lifecycle
    issues while preserving all functionality.
    """

    # External signals (for ROM extraction panel integration)
    offset_changed: pyqtSignal = pyqtSignal(int)  # Current offset changed
    sprite_found: pyqtSignal = pyqtSignal(int, str)  # Sprite found at offset with name
    validation_failed: pyqtSignal = pyqtSignal(str)  # Validation error message

    def __init__(self, parent: "QWidget | None" = None) -> None:
        # UI Components - declare BEFORE super().__init__() to avoid overwriting
        self.rom_map: ROMMapWidget | None = None
        self.offset_widget: TabbedManualOffsetWidget | None = None
        self.scan_controls: ScanControlsPanel | None = None
        self.import_export: ImportExportPanel | None = None
        self.status_panel: StatusPanel | None = None
        self.preview_widget: SpritePreviewWidget | None = None
        self.apply_btn: QPushButton | None = None

        # Business logic state - declare BEFORE super().__init__()
        self.rom_path: str = ""
        self.rom_size: int = 0x400000  # Default 4MB
        # Offset and found sprites managed by tabs (single source of truth)

        # Manager references with thread safety
        self.extraction_manager: ExtractionManager | None = None
        self.rom_extractor: ROMExtractor | None = None
        self._manager_mutex = QMutex()

        # Worker references
        self.preview_worker: SpritePreviewWorker | None = None
        self.search_worker: SpriteSearchWorker | None = None

        # Preview update timer for debouncing
        self._preview_timer: QTimer | None = None

        # Queue-based offset update system (thread-safe, no lost updates)
        self._offset_update_queue: deque[int] = deque()
        self._offset_update_timer: QTimer | None = None

        # Cache event handling
        self._cache_event_handler: CacheEventHandler | None = None
        self._cache_signals_connected: bool = False

        # Preview generator for unified preview management
        self.preview_generator = get_preview_generator()

        # Panel factory for UI creation (declared before super().__init__() to follow widget init pattern)
        self._panel_factory: PanelFactory | None = None
        
        # Found sprites registry for centralized sprite management
        self._found_sprites_registry: FoundSpritesRegistry | None = None
        
        # Navigation component for sprite search operations
        self._offset_navigator: OffsetNavigator | None = None

        super().__init__(
            parent=parent,
            title="Manual Offset Control - SpritePal",
            modal=False,
            size=(1400, 900),  # Larger default size for better preview visibility
            min_size=(1200, 800),  # Larger minimum size to prevent UI cramping
            with_status_bar=False,
            orientation=Qt.Orientation.Horizontal,
            splitter_handle_width=6
        )

        # Initialize ONLY the view state manager (positioning works well)
        self.view_state_manager = ViewStateManager(self, self)

        # Create panel factory for UI creation
        self._panel_factory = PanelFactory()

        self._setup_ui()
        self._setup_found_sprites_registry()
        self._setup_offset_navigator()
        self._setup_preview_timer()
        self._setup_preview_generator()
        self._connect_signals()
        self._connect_view_state_signals()

    def _setup_found_sprites_registry(self) -> None:
        """Set up the found sprites registry with dependencies."""
        if self.offset_widget is not None:
            self._found_sprites_registry = FoundSpritesRegistry(
                offset_widget=self.offset_widget,
                rom_map=self.rom_map,
                parent=self
            )
            logger.debug("Found sprites registry initialized")
        else:
            logger.warning("Cannot create found sprites registry: offset widget not available")

    def _setup_offset_navigator(self) -> None:
        """Set up the offset navigator for sprite search operations."""
        if self.status_panel is not None and self.offset_widget is not None:
            # Create managers using weak references to avoid circular references
            rom_data_manager = _SimpleROMDataManager(weakref.ref(self))
            status_reporter = _SimpleStatusReporter(weakref.ref(self))
            
            # Initialize navigator
            self._offset_navigator = OffsetNavigator(
                rom_data_manager=rom_data_manager,
                status_reporter=status_reporter,
                navigation_setter=self.offset_widget,
                parent=self
            )
            
            # Connect navigator signals
            self._offset_navigator.sprite_found_during_search.connect(
                self._on_navigator_sprite_found
            )
            self._offset_navigator.search_completed.connect(
                self._on_navigator_search_complete
            )
            
            logger.debug("Offset navigator initialized")
        else:
            logger.warning("Cannot create offset navigator: required components not available")
    
    def _setup_preview_timer(self) -> None:
        """Setup debouncing timer for preview updates"""
        self._preview_timer = QTimer(self)  # Parent this timer to prevent crashes
        self._preview_timer.setSingleShot(True)
        self._preview_timer.timeout.connect(self._update_preview)

        # Setup offset update timer for queue processing
        self._offset_update_timer = QTimer(self)  # Parent this timer to prevent crashes
        self._offset_update_timer.setSingleShot(True)
        self._offset_update_timer.timeout.connect(self._process_offset_queue)

    def _setup_preview_generator(self) -> None:
        """Set up the preview generator with managers and signals."""
        # Connect preview generator signals
        self.preview_generator.preview_ready.connect(self._on_preview_generator_ready)
        self.preview_generator.preview_error.connect(self._on_preview_generator_error)
        self.preview_generator.preview_progress.connect(self._on_preview_generator_progress)
        
        logger.debug("Preview generator initialized and connected")

    def _setup_ui(self):
        """Initialize the dialog-specific UI components"""
        # Ensure panel factory exists (defensive programming)
        if self._panel_factory is None:
            self._panel_factory = PanelFactory()

        # Create left panel with controls using factory
        left_panel, offset_widget, rom_map, scan_controls, import_export, status_panel = self._panel_factory.create_left_panel()
        self.offset_widget = offset_widget
        self.rom_map = rom_map
        self.scan_controls = scan_controls
        self.import_export = import_export
        self.status_panel = status_panel

        # Initialize cache event handler now that status panel is available
        if self.status_panel is not None:
            from ui.dialogs.manual_offset.cache_event_handler import (
                CacheEventHandler,
            )
            self._cache_event_handler = CacheEventHandler(self.status_panel, parent=self)

        self.add_panel(left_panel, stretch_factor=0)

        # Create right panel with preview using factory
        right_panel, preview_widget = self._panel_factory.create_right_panel()
        self.preview_widget = preview_widget
        self.add_panel(right_panel, stretch_factor=1)

        # Set initial panel sizes proportionally
        # Left panel (controls): ~30%, Right panel (preview): ~70%
        # Preview should dominate the interface since browsing sprites is the main task
        total_width = self.width()
        left_width = int(total_width * 0.30)
        right_width = total_width - left_width
        logger.debug(f"GEOMETRY: Setting initial splitter sizes - total: {total_width}, left: {left_width}, right: {right_width}")
        self.main_splitter.setSizes([left_width, right_width])
        logger.debug(f"GEOMETRY: Dialog geometry after splitter setup: {self.geometry()}")

        # Override button box to add custom buttons
        self._setup_custom_buttons()


    def _setup_custom_buttons(self):
        """Set up custom dialog buttons"""
        self.apply_btn = self._panel_factory.setup_custom_buttons(
            self.button_box,
            self._apply_offset,
            self.hide  # Hide instead of close to maintain state
        )

    def _connect_signals(self):
        """Connect internal signals directly (no service layer)"""
        # Connect offset widget signals
        if self.offset_widget is not None:
            self.offset_widget.offset_changed.connect(self._on_offset_changed)
            self.offset_widget.find_next_clicked.connect(self._find_next_sprite)
            self.offset_widget.find_prev_clicked.connect(self._find_prev_sprite)
            self.offset_widget.smart_mode_changed.connect(self._on_smart_mode_changed)
            self.offset_widget.region_changed.connect(self._on_region_changed)

        # Connect ROM map
        if self.rom_map is not None:
            self.rom_map.offset_clicked.connect(self._on_map_clicked)

        # Connect scan controls directly (no controller layer)
        if self.scan_controls is not None:
            self.scan_controls.sprite_found.connect(self._on_sprite_found_during_scan)
            self.scan_controls.scan_status_changed.connect(self._update_status)
            self.scan_controls.progress_update.connect(self._on_scan_progress_update)
            self.scan_controls.scan_started.connect(self._on_scan_started)
            self.scan_controls.scan_finished.connect(self._on_scan_finished)
            self.scan_controls.partial_scan_detected.connect(self._on_partial_scan_detected)
            self.scan_controls.sprites_detected.connect(self._on_sprites_detected)

        # Connect import/export directly (no controller layer)
        if self.import_export is not None:
            self.import_export.sprites_imported.connect(self._on_sprites_imported)
            self.import_export.status_changed.connect(self._update_status)

    def _connect_view_state_signals(self) -> None:
        """Connect view state manager signals"""
        # View state manager handles fullscreen - no dialog-specific logic needed
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

        # Update preview generator with managers
        self.preview_generator.set_managers(
            extraction_manager=extraction_manager,
            rom_extractor=extraction_manager.get_rom_extractor()
        )

        # Update UI components with new ROM data
        self._update_ui_with_rom_data(rom_path, rom_size)

        # Update window title with ROM name
        self.view_state_manager.update_title_with_rom(rom_path)

        logger.debug(f"ROM data updated: {os.path.basename(rom_path)} ({rom_size} bytes)")

    def _update_ui_with_rom_data(self, rom_path: str, rom_size: int) -> None:
        """Update UI components with new ROM data"""
        # Store widget references locally to prevent TOCTOU bugs
        offset_widget = self.offset_widget
        rom_map = self.rom_map
        scan_controls = self.scan_controls
        import_export = self.import_export

        if offset_widget is not None:
            offset_widget.set_rom_size(rom_size)
        if rom_map is not None:
            rom_map.set_rom_size(rom_size)
        if scan_controls is not None:
            scan_controls.set_rom_data(rom_path, rom_size, self.extraction_manager)
            scan_controls.set_rom_map(rom_map)
        if import_export is not None:
            import_export.set_rom_data(rom_path, rom_size)
            import_export.set_rom_map(rom_map)
        
        # Update registry with ROM map if it changed
        if self._found_sprites_registry is not None and rom_map is not None:
            self._found_sprites_registry.update_rom_map(rom_map)

    def _get_managers_safely(self) -> tuple["ExtractionManager | None", "ROMExtractor | None"]:
        """Get manager references safely with thread protection.
        
        WARNING: The returned references are only safe to use within the calling
        context if that context also holds the mutex. For operations that need
        managers, prefer using _with_managers_safely() instead.
        """
        with QMutexLocker(self._manager_mutex):
            return self.extraction_manager, self.rom_extractor
    
    def _with_managers_safely(self, operation):
        """Execute an operation with manager references under mutex protection.
        
        This prevents TOCTOU race conditions by holding the lock during the entire
        operation. For long operations, extract only necessary data under lock.
        
        Args:
            operation: Callable that takes (extraction_manager, rom_extractor) and returns a result
            
        Returns:
            The result of the operation, or None if managers are not available
        """
        with QMutexLocker(self._manager_mutex):
            if self.extraction_manager is None or self.rom_extractor is None:
                return None
            return operation(self.extraction_manager, self.rom_extractor)

    def _connect_cache_signals(self) -> None:
        """Connect extraction manager cache signals via cache handler"""
        # Prevent duplicate connections
        if self._cache_signals_connected:
            logger.debug("Cache signals already connected, skipping")
            return

        if not self._cache_event_handler:
            logger.warning("Cannot connect cache signals: cache handler not initialized")
            return

        # Use _with_managers_safely to prevent TOCTOU
        def connect_signals(extraction_manager, _):
            try:
                # Delegate cache signal connection to handler
                self._cache_event_handler.connect_cache_signals(extraction_manager)
                self._cache_signals_connected = True
                logger.debug("Cache signals connected via handler")
                return True
            except Exception as e:
                logger.warning(f"Failed to connect cache signals: {e}")
                return False
        
        self._with_managers_safely(connect_signals)

    # Offset Management (consolidated from ROMDataSession)

    def get_current_offset(self) -> int:
        """Get the current offset value from browse tab (single source of truth)"""
        if self.offset_widget is not None:
            return self.offset_widget.get_current_offset()
        return 0x200000  # Default fallback

    def set_offset(self, offset: int) -> bool:
        """Set the current offset with validation - tabs are the single source of truth
        
        Returns:
            bool: True if offset was set successfully, False if validation failed
        """
        # Input validation with detailed error message
        valid, error_msg = self._validate_offset(offset)
        if not valid:
            logger.warning(f"Invalid offset 0x{offset:06X}: {error_msg}")
            self.validation_failed.emit(error_msg)
            self._update_status(f"Invalid offset: {error_msg}")
            return False

        # Queue the offset update for processing in next event loop iteration
        # This prevents signal loops and ensures thread safety
        self._offset_update_queue.append(offset)

        # Start timer to process queue if not already running
        if self._offset_update_timer is not None and not self._offset_update_timer.isActive():
            self._offset_update_timer.start(0)  # 0 delay = next event loop iteration

        return True

    def _set_current_offset(self, offset: int) -> None:
        """Coordinate UI components when offset changes - tabs are single source of truth
        
        This method only synchronizes UI components and does NOT manage state.
        The offset_widget (tabs) is the authoritative source for the current offset.
        """
        # Store widget references locally to prevent TOCTOU bugs
        rom_map = self.rom_map
        scan_controls = self.scan_controls

        # Synchronize other UI components with the new offset
        if rom_map is not None:
            rom_map.set_current_offset(offset)
        if scan_controls is not None:
            scan_controls.set_current_offset(offset)

        # Request preview update with debouncing
        self._request_preview_update(50)

        # Emit signal for external listeners (ROM extraction panel)
        self.offset_changed.emit(offset)

    def _on_offset_changed(self, offset: int) -> None:
        """Handle offset changes from the widget - tabs are single source of truth"""
        # The offset_widget has already updated its state, just coordinate other UI components
        self._set_current_offset(offset)

    def _on_map_clicked(self, offset: int) -> None:
        """Handle clicks on the ROM map"""
        self.set_offset(offset)

    def _process_offset_queue(self) -> None:
        """Process all queued offset updates in order
        
        This runs in the next event loop iteration, ensuring:
        - No signal loops (updates are batched)
        - Thread safety (Qt's event loop handles synchronization)
        - No lost updates (all offsets are processed)
        """
        # Check if widget is still valid
        try:
            if not hasattr(self, '_offset_update_queue'):
                return
        except (RuntimeError, AttributeError):
            # Widget may have been deleted
            return
            
        while self._offset_update_queue:
            offset = self._offset_update_queue.popleft()

            # Delegate to tabs (single source of truth) with signal blocking to prevent circular updates
            if self.offset_widget is not None:
                # Block signals to prevent circular dependency: set_offset → offset_changed → _on_offset_changed
                self.offset_widget.blockSignals(True)
                try:
                    self.offset_widget.set_offset(offset)
                finally:
                    self.offset_widget.blockSignals(False)
                
                # Manually trigger the UI updates that would normally be in _on_offset_changed
                # This ensures the dialog components stay in sync without circular signals
                self._set_current_offset(offset)

    # Found Sprites Management (consolidated from ROMDataSession)

    def add_found_sprite(self, offset: int, quality: float = 1.0) -> None:
        """Add a found sprite to the collection - registry and tabs are single source of truth"""
        if self._found_sprites_registry is not None:
            # Registry coordinates all UI updates - no duplicate tracking needed
            from datetime import datetime
            sprite = FoundSprite(
                offset=offset,
                quality=quality,
                timestamp=datetime.now(),
                name=f"sprite_0x{offset:06X}"
            )
            self._found_sprites_registry.add_sprite(sprite)
        else:
            # Fallback: delegate directly to tabs and map (no dialog-level tracking)
            logger.warning("Found sprites registry not available, using direct delegation")
            if self.offset_widget is not None:
                self.offset_widget.add_found_sprite(offset, quality)
            if self.rom_map is not None:
                self.rom_map.add_found_sprite(offset, quality)

    # Sprite Operations (consolidated from OffsetExplorationService)

    def _request_preview_update(self, delay_ms: int = 50) -> None:
        """Request a preview update with debouncing"""
        if self._preview_timer is not None:
            self._preview_timer.stop()
            self._preview_timer.start(delay_ms)

    def _find_next_sprite(self) -> None:
        """Find next sprite offset using navigator."""
        if self._offset_navigator is not None and self.offset_widget is not None:
            step_size = self.offset_widget.get_step_size()
            self._offset_navigator.find_next_sprite(step_size)
        else:
            logger.warning("Navigator or offset widget not available for sprite search")

    def _find_prev_sprite(self) -> None:
        """Find previous sprite offset using navigator."""
        if self._offset_navigator is not None and self.offset_widget is not None:
            step_size = self.offset_widget.get_step_size()
            self._offset_navigator.find_previous_sprite(step_size)
        else:
            logger.warning("Navigator or offset widget not available for sprite search")


    def _update_preview(self) -> None:
        """Update the sprite preview for current offset"""
        # Check if widget is still valid
        try:
            if not self._has_rom_data():
                return
        except (RuntimeError, AttributeError):
            # Widget may have been deleted
            return

        current_offset = self.get_current_offset()
        self._update_status(f"Loading preview for 0x{current_offset:06X}...")

        # Clean up any existing preview worker (safe pattern)
        if self.preview_worker is not None:
            WorkerManager.cleanup_worker(self.preview_worker, timeout=1000)
            self.preview_worker = None

        # Extract necessary data under lock to prevent TOCTOU
        preview_data = self._extract_preview_data_safely(current_offset)
        if preview_data is None:
            self._update_status("ROM not loaded")
            return

        # Unpack the safely extracted data
        rom_path, sprite_config, sprite_name, rom_extractor = preview_data

        # Create and start preview worker with extracted data
        self.preview_worker = SpritePreviewWorker(
            rom_path, current_offset, sprite_name, rom_extractor, sprite_config
        )
        self.preview_worker.preview_ready.connect(self._on_preview_ready)
        self.preview_worker.preview_error.connect(self._on_preview_error)
        self.preview_worker.start()
    
    def _extract_preview_data_safely(self, current_offset: int):
        """Extract necessary preview data under mutex protection.
        
        This method holds the mutex while extracting all necessary data,
        preventing TOCTOU vulnerabilities.
        
        Args:
            current_offset: The ROM offset to preview
            
        Returns:
            Tuple of (rom_path, sprite_config, sprite_name, rom_extractor) or None
        """
        def extract_data(extraction_manager, rom_extractor):
            sprite_config = None
            sprite_name = f"manual_0x{current_offset:X}"
            
            # Look up known sprite configurations
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
            except OSError as e:
                logger.warning(f"I/O error reading sprite config: {e}")
            except Exception as e:
                logger.warning(f"Unexpected error looking up sprite config: {e}")
            
            # Return all necessary data extracted under lock
            return (self.rom_path, sprite_config, sprite_name, rom_extractor)
        
        return self._with_managers_safely(extract_data)

    # Signal Handlers (consolidated from controller)

    def _on_preview_ready(self, tile_data: bytes, width: int, height: int, sprite_name: str) -> None:
        """Handle preview data ready"""
        # Store widget reference locally to prevent TOCTOU
        preview_widget = self.preview_widget
        if preview_widget is not None:
            preview_widget.load_sprite_from_4bpp(tile_data, width, height, sprite_name)

        current_offset = self.get_current_offset()
        self._update_status(f"Sprite found at 0x{current_offset:06X}")

    def _on_preview_error(self, error_msg: str) -> None:
        """Handle preview error with enhanced recovery"""
        # Store widget reference locally to prevent TOCTOU
        preview_widget = self.preview_widget
        if preview_widget is not None:
            try:
                preview_widget.clear()
                preview_widget.info_label.setText("No sprite found")
            except (RuntimeError, AttributeError) as e:
                logger.warning(f"Preview widget operation failed: {e}")

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
            
    def _on_navigator_sprite_found(self, found_sprite: FoundSprite) -> None:
        """Handle sprite found by navigator.
        
        Args:
            found_sprite: FoundSprite data structure from navigator
        """
        # The navigator already called set_offset and add_found_sprite
        # Just update the preview to reflect the new position
        self._request_preview_update()
        
    def _on_navigator_search_complete(self, found: bool, sprites_found: int) -> None:
        """Handle search completion from navigator.
        
        Args:
            found: True if at least one sprite was found
            sprites_found: Number of sprites found during search
        """
        # Navigator already updated the status and re-enabled navigation
        # This could be used for additional UI updates if needed
        logger.debug(f"Navigation search complete: found={found}, count={sprites_found}")

    def _on_preview_generator_ready(self, result) -> None:
        """Handle preview ready from PreviewGenerator service."""
        # Update preview widget directly with QPixmap
        preview_widget = self.preview_widget
        if preview_widget is not None:
            try:
                # Set the preview image using the sprite preview widget's interface
                # The PreviewGenerator has already converted to QPixmap
                preview_widget.set_pixmap(result.pixmap)
                preview_widget.set_tile_count(result.tile_count)
                preview_widget.info_label.setText(result.sprite_name)
                
                # Also store the PIL image for palette operations
                if hasattr(preview_widget, 'set_grayscale_image'):
                    preview_widget.set_grayscale_image(result.pil_image)
            except (RuntimeError, AttributeError) as e:
                logger.warning(f"Preview widget update failed: {e}")

        # Update status with cache info
        cache_status = " (cached)" if result.cached else ""
        current_offset = self.get_current_offset()
        self._update_status(f"Sprite found at 0x{current_offset:06X}{cache_status}")

    def _on_preview_generator_error(self, error_msg: str, request) -> None:
        """Handle preview error from PreviewGenerator service."""
        # Clear preview widget
        preview_widget = self.preview_widget
        if preview_widget is not None:
            try:
                preview_widget.clear()
                preview_widget.info_label.setText("No sprite found")
            except (RuntimeError, AttributeError) as e:
                logger.warning(f"Preview widget clear failed: {e}")

        # The PreviewGenerator already converts technical errors to user-friendly messages
        self._update_status(error_msg)

    def _on_preview_generator_progress(self, percent: int, message: str) -> None:
        """Handle progress updates from PreviewGenerator service."""
        # Update status with progress
        self._update_status(f"{message} ({percent}%)")
        
        # Update progress bar if available
        status_panel = self.status_panel
        if status_panel is not None:
            try:
                if percent == 100:
                    status_panel.hide_progress()
                else:
                    status_panel.show_progress(percent, 100)
            except (RuntimeError, AttributeError) as e:
                logger.debug(f"Status panel progress update failed: {e}")

    def _on_sprite_found_during_search(self, offset: int, quality: float) -> None:
        """Handle sprite found during scan operation.
        
        Note: Used by scan controls for scan results.
        Navigation uses the navigator component directly.
        """
        self.set_offset(offset)
        self.add_found_sprite(offset, quality)
        self._update_status(
            f"Found sprite at 0x{offset:06X} (quality: {quality:.2f})"
        )

    def _on_search_complete(self, found: bool) -> None:
        """Handle search completion from scan operations.
        
        Note: Used by scan controls.
        Navigation completion is handled by the navigator component.
        """
        self._set_navigation_enabled(True)

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
        if self.status_panel is not None:
            self.status_panel.show_progress(progress_pct, 100)  # Show percentage out of 100

    def _on_scan_started(self) -> None:
        """Handle scan started"""
        if self.status_panel is not None:
            self.status_panel.show_progress(0, 100)  # Start at 0% out of 100%

    def _on_scan_finished(self) -> None:
        """Handle scan finished"""
        if self.status_panel is not None:
            self.status_panel.hide_progress()

        # Get found sprites from scan controls and update import/export
        if self.import_export is not None and self.scan_controls is not None:
            found_sprites = self.scan_controls.get_found_sprites()
            self.import_export.set_found_sprites(found_sprites)

    def _on_partial_scan_detected(self, scan_info: dict[str, Any]) -> None:
        """Handle detection of partial scan cache - show ResumeScanDialog"""
        try:
            from ui.dialogs import ResumeScanDialog
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
        """Handle sprites imported from file - delegate to registry (single source of truth)"""
        if self._found_sprites_registry is not None:
            # Registry coordinates all UI updates - no duplicate tracking needed
            from datetime import datetime
            found_sprites = [
                FoundSprite(
                    offset=offset,
                    quality=quality,
                    timestamp=datetime.now(),
                    name=f"sprite_0x{offset:06X}"
                )
                for offset, quality in sprites
            ]
            self._found_sprites_registry.import_sprites(found_sprites)
        else:
            # Fallback: delegate to individual components (no dialog-level tracking)
            for offset, quality in sprites:
                self.add_found_sprite(offset, quality)

    def _on_sprites_detected(self, sprites: list[tuple[int, float]]) -> None:
        """Handle sprites detected from scan for smart mode"""
        if sprites and self.offset_widget:
            # Store widget references locally to prevent TOCTOU
            offset_widget = self.offset_widget
            rom_map = self.rom_map

            # Update offset widget with sprite regions
            if offset_widget is not None:
                offset_widget.set_sprite_regions(sprites)

                # Update ROM map with regions
                if rom_map is not None and hasattr(rom_map, "set_sprite_regions"):
                    regions = offset_widget.get_sprite_regions()
                    rom_map.set_sprite_regions(regions)

    # Cache event handling methods - delegated to cache handler
    # These methods are preserved for backwards compatibility with existing signal connections

    def _on_cache_hit(self, cache_type: str, time_saved: float) -> None:
        """Handle cache hit - delegated to cache handler and update status panel directly"""
        # Delegate to cache handler for centralized logic
        if self._cache_event_handler:
            self._cache_event_handler._on_cache_hit(cache_type, time_saved)
        
        # Also handle status panel updates directly for backward compatibility with tests
        status_panel = self.status_panel
        if status_panel is not None:
            cache_type_display = cache_type.replace("_", " ")
            message = f"Loaded {cache_type_display} from cache (saved {time_saved:.1f}s)"
            
            try:
                if hasattr(status_panel, "update_cache_status"):
                    status_panel.update_cache_status()
                if hasattr(status_panel, "update_status"):
                    status_panel.update_status(message)
            except (RuntimeError, AttributeError) as e:
                logger.debug(f"Status panel update failed (widget may be deleted): {e}")

    def _on_cache_miss(self, cache_type: str) -> None:
        """Handle cache miss - delegated to cache handler"""
        if self._cache_event_handler:
            self._cache_event_handler._on_cache_miss(cache_type)

    def _on_cache_saved(self, cache_type: str, count: int) -> None:
        """Handle cache saved - delegated to cache handler and update status panel directly"""
        # Delegate to cache handler for centralized logic
        if self._cache_event_handler:
            self._cache_event_handler._on_cache_saved(cache_type, count)
        
        # Also handle status panel updates directly for backward compatibility with tests
        status_panel = self.status_panel
        if status_panel is not None:
            cache_type_display = cache_type.replace("_", " ")
            message = f"Saved {count} {cache_type_display} to cache"
            
            try:
                if hasattr(status_panel, "update_status"):
                    status_panel.update_status(message)
            except (RuntimeError, AttributeError) as e:
                logger.debug(f"Status panel update failed (widget may be deleted): {e}")


    def _on_smart_mode_changed(self, enabled: bool) -> None:
        """Handle smart mode toggle"""
        if self.rom_map is not None:
            self.rom_map.toggle_region_highlight(enabled)

    def _on_region_changed(self, region_index: int) -> None:
        """Handle region change in smart mode"""
        if self.rom_map is not None:
            self.rom_map.set_current_region(region_index)

    # Main Operations

    def _apply_offset(self) -> None:
        """Apply the current offset and close dialog"""
        offset = self.get_current_offset()

        # Validate before applying
        valid, error_msg = self._validate_offset(offset)
        if not valid:
            logger.warning(f"Cannot apply invalid offset 0x{offset:06X}: {error_msg}")
            self._update_status(f"Cannot apply offset: {error_msg}")
            return

        sprite_name = f"manual_0x{offset:X}"
        self.sprite_found.emit(offset, sprite_name)
        self.hide()

    # Utility Methods

    def _validate_offset(self, offset: int) -> tuple[bool, str]:
        """Validate that an offset is within reasonable bounds
        
        Returns:
            tuple[bool, str]: (is_valid, error_message)
        """
        # Check for negative offsets
        if offset < 0:
            return False, "Offset cannot be negative"

        # Check for reasonable maximum bounds (16MB should be enough for any SNES ROM)
        if offset > 0x1000000:  # 16MB
            return False, "Offset exceeds maximum ROM size (16MB)"

        # If ROM data is loaded, check against actual ROM size
        if self.rom_size > 0 and offset >= self.rom_size:
            return False, f"Offset 0x{offset:06X} exceeds ROM size 0x{self.rom_size:06X}"

        return True, ""

    def _has_rom_data(self) -> bool:
        """Check if ROM data is loaded"""
        return bool(self.rom_path and self.rom_size > 0)

    def _update_status(self, message: str) -> None:
        """Update status message"""
        # Store widget reference locally to prevent TOCTOU
        status_panel = self.status_panel
        if status_panel is not None:
            try:
                status_panel.update_status(message)
            except (RuntimeError, AttributeError) as e:
                logger.debug(f"Status panel update failed (widget may be deleted): {e}")

    def _clear_rom_cache(self) -> None:
        """Clear cache for the current ROM - delegated to cache handler"""
        if not self.rom_path:
            return

        if self._cache_event_handler:
            self._cache_event_handler.clear_cache_for_rom(self.rom_path)
        else:
            logger.warning("Cannot clear cache: cache handler not initialized")

    def _set_navigation_enabled(self, enabled: bool) -> None:
        """Set navigation enabled state - delegate to tabs (single source of truth)"""
        if self.offset_widget is not None:
            self.offset_widget.set_navigation_enabled(enabled)

    def _cleanup_workers(self) -> None:
        """Clean up any running worker threads with timeouts to prevent hangs"""
        # Use WorkerManager for consistent cleanup
        WorkerManager.cleanup_worker(self.preview_worker, timeout=2000)
        self.preview_worker = None

        WorkerManager.cleanup_worker(self.search_worker, timeout=2000)
        self.search_worker = None
        
        # Clean up timers with proper stopping and deletion
        if self._preview_timer is not None:
            self._preview_timer.stop()
            self._preview_timer.deleteLater()
            self._preview_timer = None
        
        if self._offset_update_timer is not None:
            self._offset_update_timer.stop()
            self._offset_update_timer.deleteLater()
            self._offset_update_timer = None
        
        # Clean up navigator
        if self._offset_navigator is not None:
            self._offset_navigator.cleanup()

        # Clean up scan controls workers
        if hasattr(self, "scan_controls"):
            scan_controls = self.scan_controls
            if scan_controls is not None:
                try:
                    scan_controls.cleanup_workers()
                except RuntimeError as e:
                    logger.warning(f"Error cleaning up scan controls workers: {e}")

        # Clean up cache event handler
        if self._cache_event_handler is not None:
            try:
                self._cache_event_handler.disconnect_cache_signals()
                self._cache_signals_connected = False
            except Exception as e:
                logger.warning(f"Error disconnecting cache signals: {e}")

        # Clean up preview generator
        if hasattr(self, 'preview_generator') and self.preview_generator is not None:
            try:
                self.preview_generator.cancel_pending_requests()
            except Exception as e:
                logger.warning(f"Error cleaning up preview generator: {e}")

        logger.debug("Dialog workers and timers cleaned up")

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


    def __del__(self) -> None:
        """Destructor to ensure timers are stopped even if cleanup fails."""
        try:
            if hasattr(self, '_preview_timer') and self._preview_timer is not None:
                self._preview_timer.stop()
            if hasattr(self, '_offset_update_timer') and self._offset_update_timer is not None:
                self._offset_update_timer.stop()
        except (RuntimeError, AttributeError):
            # Widget may already be deleted
            pass

    @override
    def closeEvent(self, a0: QCloseEvent | None):
        """Handle close event - clean up and close properly"""
        self._cleanup_workers()
        if a0:
            super().closeEvent(a0)  # Let parent handle close event normally

    @override
    def hideEvent(self, a0: QHideEvent | None):
        """Handle hide event - cleanup workers and save position"""
        logger.debug(f"GEOMETRY: Dialog hideEvent - current geometry: {self.geometry()}")
        self._cleanup_workers()
        self.view_state_manager.handle_hide_event()

        if a0:
            super().hideEvent(a0)
    
    def __del__(self):
        """Ensure proper cleanup of all resources to prevent memory leaks."""
        # Clean up any remaining workers
        try:
            self._cleanup_workers()
        except Exception:
            pass  # Ignore errors during deletion
            
        # Clear all widget references
        self.rom_map = None
        self.offset_widget = None
        self.scan_controls = None
        self.import_export = None
        self.status_panel = None
        self.preview_widget = None
        self.apply_btn = None
        
        # Clear manager references
        self.extraction_manager = None
        self.rom_extractor = None
        
        # Clear component references
        self._panel_factory = None
        self._found_sprites_registry = None
        self._offset_navigator = None
        self._cache_event_handler = None
        
        logger.debug("ManualOffsetDialogSimplified cleaned up")

    def showEvent(self, event):  # noqa: N802
        """Handle show event - restore position if available"""
        logger.debug(f"GEOMETRY: Dialog showEvent - initial geometry: {self.geometry()}")
        super().showEvent(event)
        self.view_state_manager.handle_show_event()
        logger.debug(f"GEOMETRY: Dialog showEvent - final geometry: {self.geometry()}")
