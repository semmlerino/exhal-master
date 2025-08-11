"""
Detached gallery window for displaying sprites without layout constraints.
Opens in a separate window to avoid parent layout stretch issues.
"""

from pathlib import Path
from typing import Any, Optional

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QAction, QCloseEvent
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSizePolicy,
    QStatusBar,
    QTextEdit,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from core.managers import get_extraction_manager
from ui.common import WorkerManager
from ui.rom_extraction.workers import SpriteScanWorker
from ui.widgets.sprite_gallery_widget import SpriteGalleryWidget
from ui.workers.batch_thumbnail_worker import BatchThumbnailWorker
from utils.logging_config import get_logger
from utils.settings_manager import get_settings_manager

logger = get_logger(__name__)


class DetachedGalleryWindow(QMainWindow):
    """Standalone window for sprite gallery display."""

    # Signals
    sprite_selected = Signal(int)  # Emits when sprite is selected
    window_closed = Signal()  # Emits when window is closed
    sprite_extracted = Signal(str, int)  # path, offset - for successful extraction

    def __init__(self, parent: Optional[QWidget] = None):
        """
        Initialize the detached gallery window.
        
        Args:
            parent: Parent widget (usually the main window)
        """
        super().__init__(parent)

        # Window configuration
        self.setWindowTitle("Sprite Gallery")
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.Window)

        # State
        self.sprites_data: list[dict[str, Any]] = []
        self.rom_path: Optional[str] = None
        self.rom_size: int = 0
        self.scan_worker: Optional[SpriteScanWorker] = None
        self.thumbnail_worker: Optional[BatchThumbnailWorker] = None
        self.scanning: bool = False
        self.scan_timeout_timer: Optional[QTimer] = None

        # Core managers
        self.extraction_manager = get_extraction_manager()
        self.rom_extractor = self.extraction_manager.get_rom_extractor()

        # UI Components
        self.gallery_widget: Optional[SpriteGalleryWidget] = None
        self.status_bar: Optional[QStatusBar] = None
        self.progress_bar: Optional[QProgressBar] = None
        self.scan_results_text: Optional[QTextEdit] = None

        self._setup_ui()

        # Set initial size
        self.resize(1024, 768)
        
        # Load last ROM if available
        self._load_last_rom()

    def _setup_ui(self):
        """Setup the window UI for proper gallery display."""
        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Main layout
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Create gallery widget
        self.gallery_widget = SpriteGalleryWidget(self)

        # For detached window, we want the gallery to fill available space
        # and handle scrolling properly
        self.gallery_widget.setSizePolicy(
            QSizePolicy.Policy.Expanding,  # Fill horizontal space
            QSizePolicy.Policy.Expanding   # Fill vertical space too
        )

        # IMPORTANT: Override the gallery's setWidgetResizable setting
        # In detached window, we want automatic resizing for proper scrolling
        self.gallery_widget.setWidgetResizable(True)

        # Also update the container widget's size policy for proper display
        if self.gallery_widget.container_widget:
            self.gallery_widget.container_widget.setSizePolicy(
                QSizePolicy.Policy.Expanding,
                QSizePolicy.Policy.Preferred  # Use preferred height based on content
            )

        # Connect signals
        self.gallery_widget.sprite_selected.connect(self.sprite_selected.emit)
        self.gallery_widget.sprite_double_clicked.connect(self._on_sprite_double_clicked)

        # Add to layout with stretch factor to fill window
        layout.addWidget(self.gallery_widget, 1)  # Stretch factor 1 to fill space

        # NO stretch spacer - we want the gallery to use all available space

        central_widget.setLayout(layout)

        # Add menu bar
        self._create_menu_bar()

        # Add toolbar
        self._create_toolbar()

        # Add status bar
        self._create_status_bar()

        # Style for dark theme with proper text colors
        self.setStyleSheet("""
            QMainWindow {
                background-color: #1e1e1e;
                color: #ffffff;
            }
            
            /* Menu Bar Styling */
            QMenuBar {
                background-color: #2d2d2d;
                color: #ffffff;
                border-bottom: 1px solid #444444;
            }
            
            QMenuBar::item {
                background-color: transparent;
                color: #ffffff;
                padding: 4px 8px;
            }
            
            QMenuBar::item:selected {
                background-color: #404040;
            }
            
            QMenu {
                background-color: #2d2d2d;
                color: #ffffff;
                border: 1px solid #444444;
            }
            
            QMenu::item {
                padding: 4px 20px;
                color: #ffffff;
            }
            
            QMenu::item:selected {
                background-color: #404040;
            }
            
            /* Toolbar Styling */
            QToolBar {
                background-color: #2d2d2d;
                color: #ffffff;
                border: none;
                spacing: 3px;
            }
            
            QToolButton {
                background-color: #404040;
                color: #ffffff;
                border: 1px solid #555555;
                border-radius: 3px;
                padding: 6px 12px;
                margin: 2px;
            }
            
            QToolButton:hover {
                background-color: #505050;
                border-color: #666666;
            }
            
            QToolButton:pressed {
                background-color: #353535;
            }
            
            /* Status Bar Styling */
            QStatusBar {
                background-color: #2d2d2d;
                color: #ffffff;
                border-top: 1px solid #444444;
            }
            
            QProgressBar {
                background-color: #404040;
                border: 1px solid #555555;
                border-radius: 3px;
                text-align: center;
                color: #ffffff;
            }
            
            QProgressBar::chunk {
                background-color: #0078d4;
                border-radius: 2px;
            }
            
            /* Message Box Styling */
            QMessageBox {
                background-color: #2d2d2d;
                color: #ffffff;
            }
            
            QMessageBox QPushButton {
                background-color: #404040;
                color: #ffffff;
                border: 1px solid #555555;
                border-radius: 3px;
                padding: 6px 12px;
                min-width: 80px;
            }
            
            QMessageBox QPushButton:hover {
                background-color: #505050;
            }
            
            /* Dialog Styling */
            QDialog {
                background-color: #2d2d2d;
                color: #ffffff;
            }
            
            QLabel {
                color: #ffffff;
            }
            
            QTextEdit {
                background-color: #1e1e1e;
                color: #ffffff;
                border: 1px solid #444444;
                border-radius: 3px;
            }
            
            QPushButton {
                background-color: #404040;
                color: #ffffff;
                border: 1px solid #555555;
                border-radius: 3px;
                padding: 6px 12px;
            }
            
            QPushButton:hover {
                background-color: #505050;
            }
            
            QPushButton:pressed {
                background-color: #353535;
            }
        """)

    def _create_menu_bar(self):
        """Create the menu bar."""
        menubar = self.menuBar()

        # File menu
        file_menu = menubar.addMenu("File")

        # Load ROM action
        load_rom_action = QAction("Load ROM...", self)
        load_rom_action.setShortcut("Ctrl+O")
        load_rom_action.triggered.connect(self._load_rom)
        file_menu.addAction(load_rom_action)
        
        # Recent ROMs submenu
        self.recent_roms_menu = file_menu.addMenu("Recent ROMs")
        self._update_recent_roms_menu()

        file_menu.addSeparator()

        close_action = QAction("Close", self)
        close_action.setShortcut("Ctrl+W")
        close_action.triggered.connect(self.close)
        file_menu.addAction(close_action)

        # ROM menu
        rom_menu = menubar.addMenu("ROM")

        scan_action = QAction("Scan for Sprites...", self)
        scan_action.setShortcut("Ctrl+S")
        scan_action.triggered.connect(self._scan_rom)
        rom_menu.addAction(scan_action)

        # Extract menu
        extract_menu = menubar.addMenu("Extract")

        extract_selected_action = QAction("Extract Selected Sprite...", self)
        extract_selected_action.setShortcut("Ctrl+E")
        extract_selected_action.triggered.connect(self._extract_selected_sprite)
        extract_menu.addAction(extract_selected_action)

        # View menu
        view_menu = menubar.addMenu("View")

        fullscreen_action = QAction("Toggle Fullscreen", self)
        fullscreen_action.setShortcut("F11")
        fullscreen_action.triggered.connect(self._toggle_fullscreen)
        view_menu.addAction(fullscreen_action)

        # Show scan results action
        show_results_action = QAction("Show Scan Results", self)
        show_results_action.triggered.connect(self._show_scan_results)
        view_menu.addAction(show_results_action)

    def _create_toolbar(self):
        """Create the toolbar."""
        toolbar = QToolBar()
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        # Load ROM action
        load_rom_action = QAction("📂 Load ROM", self)
        load_rom_action.setToolTip("Load a ROM file for sprite scanning")
        load_rom_action.triggered.connect(self._load_rom)
        toolbar.addAction(load_rom_action)

        # Scan ROM action
        scan_action = QAction("🔍 Scan ROM", self)
        scan_action.setToolTip("Scan ROM for sprite offsets")
        scan_action.triggered.connect(self._scan_rom)
        toolbar.addAction(scan_action)
        
        # Refresh thumbnails action
        refresh_action = QAction("🔄 Refresh", self)
        refresh_action.setToolTip("Refresh sprite thumbnails")
        refresh_action.triggered.connect(self._refresh_thumbnails)
        toolbar.addAction(refresh_action)

        toolbar.addSeparator()

        # Fit to window action
        fit_action = QAction("🖼️ Fit to Window", self)
        fit_action.setToolTip("Adjust columns to fit window width")
        fit_action.triggered.connect(self._fit_to_window)
        toolbar.addAction(fit_action)

        # Reset view action
        reset_action = QAction("🔄 Reset View", self)
        reset_action.setToolTip("Reset to default view settings")
        reset_action.triggered.connect(self._reset_view)
        toolbar.addAction(reset_action)

        # Extract selected sprite action
        extract_action = QAction("💾 Extract Selected", self)
        extract_action.setToolTip("Extract the currently selected sprite")
        extract_action.triggered.connect(self._extract_selected_sprite)
        toolbar.addAction(extract_action)

    def set_sprites(self, sprites: list[dict[str, Any]]):
        """
        Set the sprites to display.
        
        Args:
            sprites: List of sprite dictionaries
        """
        self.sprites_data = sprites
        if self.gallery_widget:
            self.gallery_widget.set_sprites(sprites)

            # Ensure proper settings for detached display
            self.gallery_widget.setWidgetResizable(True)

            # Update container widget policy after sprites are set
            if self.gallery_widget.container_widget:
                self.gallery_widget.container_widget.setSizePolicy(
                    QSizePolicy.Policy.Expanding,
                    QSizePolicy.Policy.Preferred
                )

            # Update the main widget policy too if needed
            if self.gallery_widget.widget():
                self.gallery_widget.widget().setSizePolicy(
                    QSizePolicy.Policy.Preferred,
                    QSizePolicy.Policy.Preferred
                )

            # Force proper layout update
            self.gallery_widget.force_layout_update()

            logger.info(f"Detached gallery loaded {len(sprites)} sprites")

    def copy_thumbnails_from(self, source_gallery):
        """
        Copy thumbnail pixmaps from another gallery widget.
        
        Args:
            source_gallery: Source SpriteGalleryWidget to copy from
        """
        if not self.gallery_widget or not source_gallery:
            return

        copied_count = 0
        for offset, source_thumbnail in source_gallery.thumbnails.items():
            if offset in self.gallery_widget.thumbnails:
                dest_thumbnail = self.gallery_widget.thumbnails[offset]

                # Copy the pixmap if it exists and is valid
                if hasattr(source_thumbnail, 'sprite_pixmap') and source_thumbnail.sprite_pixmap:
                    if not source_thumbnail.sprite_pixmap.isNull():
                        dest_thumbnail.set_sprite_data(
                            source_thumbnail.sprite_pixmap,
                            source_thumbnail.sprite_info
                        )
                        copied_count += 1

        logger.info(f"Copied {copied_count} thumbnails to detached gallery")

    def set_rom_info(self, rom_path: str, rom_extractor):
        """
        Set ROM information for thumbnail generation.
        
        Args:
            rom_path: Path to the ROM file
            rom_extractor: ROM extractor instance
        """
        self.rom_path = rom_path
        # Store for potential future use
        self.rom_extractor = rom_extractor

    def _on_sprite_double_clicked(self, offset: int):
        """Handle sprite double-click."""
        logger.debug(f"Sprite double-clicked in detached window: 0x{offset:06X}")
        # Could close window and navigate to sprite in main window
        self.sprite_selected.emit(offset)

    def _toggle_fullscreen(self):
        """Toggle fullscreen mode."""
        if self.isFullScreen():
            self.showNormal()
        else:
            self.showFullScreen()

    def _fit_to_window(self):
        """Adjust gallery to fit window width."""
        if self.gallery_widget:
            # Force column recalculation
            self.gallery_widget._update_columns()

    def _reset_view(self):
        """Reset to default view settings."""
        if self.gallery_widget:
            # Reset thumbnail size
            self.gallery_widget.thumbnail_size = 256
            self.gallery_widget.size_slider.setValue(256)

            # Reset filters
            self.gallery_widget.filter_input.clear()
            self.gallery_widget.compressed_check.setChecked(False)

            # Update display
            self.gallery_widget._update_columns()

    def _create_status_bar(self):
        """Create the status bar."""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

        # Add progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setMinimumWidth(200)
        self.status_bar.addPermanentWidget(self.progress_bar)

        self.status_bar.showMessage("Ready - Load a ROM to start scanning")

    def _load_rom(self):
        """Load a ROM file."""
        settings = get_settings_manager()
        default_dir = settings.get_default_directory()

        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Select ROM File",
            default_dir,
            "SNES ROM Files (*.sfc *.smc);;All Files (*.*)"
        )

        if filename:
            self._set_rom_file(filename)
            # Save as last used ROM
            self._save_last_rom(filename)
    
    def _load_last_rom(self):
        """Load the last selected ROM if available."""
        try:
            settings = get_settings_manager()
            from utils.constants import SETTINGS_NS_ROM_INJECTION, SETTINGS_KEY_LAST_INPUT_ROM
            
            last_rom = settings.get_value(
                SETTINGS_NS_ROM_INJECTION,
                SETTINGS_KEY_LAST_INPUT_ROM,
                ""
            )
            
            if last_rom and Path(last_rom).exists():
                logger.info(f"Auto-loading last ROM: {last_rom}")
                self._set_rom_file(last_rom)
                self.status_bar.showMessage(f"Auto-loaded: {Path(last_rom).name}")
            elif last_rom:
                logger.warning(f"Last ROM not found: {last_rom}")
                self.status_bar.showMessage("Last ROM not found - Load a new ROM to start")
            else:
                logger.debug("No last ROM in settings")
                self.status_bar.showMessage("Ready - Load a ROM to start scanning")
                
        except Exception as e:
            logger.error(f"Error loading last ROM: {e}")
            self.status_bar.showMessage("Ready - Load a ROM to start scanning")
    
    def _save_last_rom(self, rom_path: str):
        """Save the ROM path as the last used ROM."""
        try:
            settings = get_settings_manager()
            from utils.constants import SETTINGS_NS_ROM_INJECTION, SETTINGS_KEY_LAST_INPUT_ROM
            
            settings.set_value(
                SETTINGS_NS_ROM_INJECTION,
                SETTINGS_KEY_LAST_INPUT_ROM,
                rom_path
            )
            settings.set_last_used_directory(str(Path(rom_path).parent))
            
            # Also update recent ROMs list
            self._add_to_recent_roms(rom_path)
            
            logger.debug(f"Saved last ROM: {rom_path}")
            
        except Exception as e:
            logger.error(f"Error saving last ROM: {e}")
    
    def _add_to_recent_roms(self, rom_path: str):
        """Add a ROM to the recent ROMs list."""
        try:
            settings = get_settings_manager()
            
            # Get current recent ROMs list
            recent_roms = settings.get_value("gallery", "recent_roms", [])
            
            # Remove if already exists to avoid duplicates
            if rom_path in recent_roms:
                recent_roms.remove(rom_path)
            
            # Add to front of list
            recent_roms.insert(0, rom_path)
            
            # Keep only last 10 ROMs
            recent_roms = recent_roms[:10]
            
            # Save updated list
            settings.set_value("gallery", "recent_roms", recent_roms)
            
            # Update menu
            self._update_recent_roms_menu()
            
        except Exception as e:
            logger.error(f"Error updating recent ROMs: {e}")
    
    def _update_recent_roms_menu(self):
        """Update the recent ROMs menu."""
        if not hasattr(self, 'recent_roms_menu'):
            return
            
        self.recent_roms_menu.clear()
        
        try:
            settings = get_settings_manager()
            recent_roms = settings.get_value("gallery", "recent_roms", [])
            
            # Filter out non-existent files
            valid_roms = [rom for rom in recent_roms if Path(rom).exists()]
            
            if not valid_roms:
                no_recent = QAction("(No recent ROMs)", self)
                no_recent.setEnabled(False)
                self.recent_roms_menu.addAction(no_recent)
                return
            
            # Add each recent ROM
            for i, rom_path in enumerate(valid_roms[:10], 1):
                rom_name = Path(rom_path).name
                action = QAction(f"{i}. {rom_name}", self)
                action.setToolTip(rom_path)
                
                # Use lambda with default argument to capture rom_path
                action.triggered.connect(lambda checked=False, path=rom_path: self._load_recent_rom(path))
                
                # Add number shortcut for first 9
                if i <= 9:
                    action.setShortcut(f"Ctrl+{i}")
                
                self.recent_roms_menu.addAction(action)
                
        except Exception as e:
            logger.error(f"Error updating recent ROMs menu: {e}")
    
    def _load_recent_rom(self, rom_path: str):
        """Load a ROM from the recent list."""
        if Path(rom_path).exists():
            self._set_rom_file(rom_path)
            self._save_last_rom(rom_path)
        else:
            QMessageBox.warning(
                self,
                "ROM Not Found",
                f"The ROM file no longer exists:\n{rom_path}"
            )

    def _set_rom_file(self, filename: str):
        """Set the ROM file and update UI."""
        try:
            self.rom_path = filename
            
            # Get ROM size
            with Path(filename).open("rb") as f:
                f.seek(0, 2)  # Seek to end
                self.rom_size = f.tell()

            # Update window title
            rom_name = Path(filename).stem
            self.setWindowTitle(f"Sprite Gallery - {rom_name}")

            # Update status
            self.status_bar.showMessage(f"ROM loaded: {rom_name} ({self.rom_size // 1024} KB)")

            # Check for cached sprites
            self._load_cached_sprites()

            logger.info(f"Loaded ROM: {filename}")

        except Exception as e:
            logger.error(f"Error loading ROM: {e}")
            from ui.dialogs import UserErrorDialog
            UserErrorDialog.show_error(
                self,
                "Error Loading ROM",
                f"Could not load ROM file: {e}"
            )
    
    def _load_cached_sprites(self):
        """Load cached sprites for the current ROM if available."""
        if not self.rom_path:
            return
        
        try:
            # Check cache for known sprites
            from utils.rom_cache import get_rom_cache
            rom_cache = get_rom_cache()
            
            # Get known sprite locations from config
            locations = self.extraction_manager.get_known_sprite_locations(self.rom_path)
            
            if locations:
                self.status_bar.showMessage(f"Found {len(locations)} known sprites in cache")
                
                # Convert to sprite data format
                self.sprites_data = []
                for name, pointer in locations.items():
                    sprite = {
                        'offset': pointer.offset,
                        'decompressed_size': 0,  # Will be determined during thumbnail generation
                        'tile_count': 0,
                        'compressed': False,
                        'name': name.replace("_", " ").title()
                    }
                    self.sprites_data.append(sprite)
                
                # Update gallery
                if self.gallery_widget:
                    self.gallery_widget.set_sprites(self.sprites_data)
                
                # Generate thumbnails automatically
                QTimer.singleShot(500, self._generate_thumbnails)
                
                logger.info(f"Loaded {len(self.sprites_data)} cached sprites")
            else:
                self.status_bar.showMessage("No cached sprites found - use Scan ROM to find sprites")
        
        except Exception as e:
            logger.error(f"Error loading cached sprites: {e}")

    def _scan_rom(self):
        """Scan the ROM for sprites."""
        if not self.rom_path:
            QMessageBox.information(
                self,
                "No ROM Loaded",
                "Please load a ROM file first using File > Load ROM."
            )
            return

        if self.scanning:
            QMessageBox.information(
                self,
                "Scan in Progress",
                "A ROM scan is already in progress. Please wait for it to complete."
            )
            return

        self._start_scan()

    def _start_scan(self):
        """Start the ROM scanning process."""
        self.scanning = True
        
        # Show progress
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.status_bar.showMessage("Scanning ROM for sprites...")

        # Clean up any existing worker
        if self.scan_worker:
            WorkerManager.cleanup_worker(self.scan_worker)

        # Create and start scan worker
        self.scan_worker = SpriteScanWorker(
            self.rom_path, 
            self.rom_extractor, 
            use_cache=True, 
            parent=self
        )

        # Connect signals with proper error handling
        try:
            self.scan_worker.sprite_found.connect(self._on_sprite_found)
            self.scan_worker.finished.connect(self._on_scan_finished)
            self.scan_worker.progress.connect(self._on_scan_progress)
            self.scan_worker.cache_status.connect(self._on_cache_status)
            
            # Also connect to operation_finished signal from BaseWorker
            self.scan_worker.operation_finished.connect(self._on_scan_finished)
            
            # Connect error signal for better error handling
            self.scan_worker.error.connect(self._on_scan_error)

            # Start scanning
            self.scan_worker.start()
            
            # Set up timeout timer (5 minutes max)
            self.scan_timeout_timer = QTimer()
            self.scan_timeout_timer.timeout.connect(self._on_scan_timeout)
            self.scan_timeout_timer.setSingleShot(True)
            self.scan_timeout_timer.start(300000)  # 5 minutes
            
            logger.info("Started ROM sprite scan")
            
        except Exception as e:
            logger.error(f"Error starting ROM scan: {e}")
            self.scanning = False
            self.progress_bar.setVisible(False)
            self.status_bar.showMessage(f"Scan failed to start: {e}")
            if self.scan_worker:
                WorkerManager.cleanup_worker(self.scan_worker)
                self.scan_worker = None

    def _on_sprite_found(self, sprite_info: dict):
        """Handle sprite found during scan."""
        # Convert to the format expected by gallery
        sprite = {
            'offset': sprite_info['offset'],
            'decompressed_size': sprite_info.get('decompressed_size', 0),
            'tile_count': sprite_info.get('tile_count', 0),
            'compressed': False,  # Will be determined later
            'name': f"Sprite_0x{sprite_info['offset']:06X}",
            'quality': sprite_info.get('quality', 1.0)
        }

        # Add to sprites data
        self.sprites_data.append(sprite)
        
        # Update gallery display
        if self.gallery_widget:
            self.gallery_widget.set_sprites(self.sprites_data)

        # Update status
        self.status_bar.showMessage(f"Found {len(self.sprites_data)} sprites...")

        logger.debug(f"Added sprite at 0x{sprite_info['offset']:06X} to gallery")

    def _on_scan_progress(self, percent: int, message: str):
        """Handle scan progress update."""
        self.progress_bar.setValue(percent)
        self.status_bar.showMessage(f"Scanning: {message}")

    def _on_cache_status(self, status: str):
        """Handle cache status update."""
        self.status_bar.showMessage(f"Cache: {status}")
    
    def _on_scan_error(self, error_message: str):
        """Handle scan error."""
        logger.error(f"ROM scan error: {error_message}")
        self.scanning = False
        self.progress_bar.setVisible(False)
        self.status_bar.showMessage(f"Scan error: {error_message}")
        
        # Show error dialog
        QMessageBox.critical(
            self,
            "ROM Scan Error",
            f"An error occurred while scanning the ROM:\n\n{error_message}"
        )
        
        # Clean up timeout timer
        if self.scan_timeout_timer:
            self.scan_timeout_timer.stop()
            self.scan_timeout_timer = None
        
        # Clean up worker
        if self.scan_worker:
            WorkerManager.cleanup_worker(self.scan_worker)
            self.scan_worker = None

    def _on_scan_finished(self):
        """Handle scan completion."""
        try:
            self.scanning = False
            self.progress_bar.setVisible(False)
            
            sprite_count = len(self.sprites_data)
            self.status_bar.showMessage(f"Scan complete - Found {sprite_count} sprites")

            # Clean up timeout timer
            if self.scan_timeout_timer:
                self.scan_timeout_timer.stop()
                self.scan_timeout_timer = None
            
            # Clean up worker
            if self.scan_worker:
                # Wait for thread to finish properly
                if self.scan_worker.isRunning():
                    self.scan_worker.requestInterruption()
                    self.scan_worker.wait(3000)  # Wait up to 3 seconds
                
                WorkerManager.cleanup_worker(self.scan_worker)
                self.scan_worker = None

            # Generate thumbnails for found sprites
            if sprite_count > 0:
                self._generate_thumbnails()
            
            logger.info(f"Scan completed - found {sprite_count} sprites")
            
        except Exception as e:
            logger.error(f"Error in scan finished handler: {e}")
            # Ensure scanning flag is reset
            self.scanning = False
            if self.progress_bar:
                self.progress_bar.setVisible(False)
    
    def _on_scan_timeout(self):
        """Handle scan timeout."""
        logger.warning("ROM scan timed out after 5 minutes")
        self.scanning = False
        self.progress_bar.setVisible(False)
        self.status_bar.showMessage("Scan timed out - ROM scanning took too long")
        
        # Show timeout dialog
        QMessageBox.warning(
            self,
            "Scan Timeout",
            "The ROM scan took longer than 5 minutes and was stopped.\n\n"
            "This may indicate a very large ROM or system performance issues.\n"
            "Try scanning a smaller ROM or restart the application."
        )
        
        # Clean up worker
        if self.scan_worker:
            if self.scan_worker.isRunning():
                self.scan_worker.requestInterruption()
                self.scan_worker.wait(3000)
            WorkerManager.cleanup_worker(self.scan_worker)
            self.scan_worker = None
            
        # Clean up timer
        if self.scan_timeout_timer:
            self.scan_timeout_timer.stop()
            self.scan_timeout_timer = None

    def _generate_thumbnails(self):
        """Generate actual thumbnails from ROM data for the found sprites."""
        if not self.gallery_widget or not self.sprites_data or not self.rom_path:
            logger.warning("Cannot generate thumbnails: missing data")
            return

        self.status_bar.showMessage("Generating thumbnails...")
        
        # Create thumbnail worker if needed
        if not self.thumbnail_worker:
            logger.info("Creating BatchThumbnailWorker for thumbnail generation")
            self.thumbnail_worker = BatchThumbnailWorker(
                self.rom_path,
                self.rom_extractor
            )
            self.thumbnail_worker.thumbnail_ready.connect(self._on_thumbnail_ready)
            self.thumbnail_worker.progress.connect(self._on_thumbnail_progress)
        
        # Queue all sprites for thumbnail generation
        logger.info(f"Queueing {len(self.sprites_data)} sprites for thumbnail generation")
        for sprite_info in self.sprites_data:
            offset = sprite_info.get('offset', 0)
            if isinstance(offset, str):
                offset = int(offset, 16) if offset.startswith('0x') else int(offset)
            # Queue with size 256 for better visibility
            self.thumbnail_worker.queue_thumbnail(offset, 256)
        
        # Start generation if not already running
        if self.thumbnail_worker and not self.thumbnail_worker.isRunning():
            logger.info("Starting BatchThumbnailWorker thread")
            self.thumbnail_worker.start()
    
    def _on_thumbnail_ready(self, offset: int, pixmap):
        """Handle thumbnail ready from worker."""
        logger.debug(f"Thumbnail ready for offset 0x{offset:06X}")
        
        if not self.gallery_widget or offset not in self.gallery_widget.thumbnails:
            return
        
        thumbnail = self.gallery_widget.thumbnails[offset]
        
        # Find sprite info for this offset
        sprite_info = None
        for info in self.sprites_data:
            info_offset = info.get('offset', 0)
            if isinstance(info_offset, str):
                info_offset = int(info_offset, 16) if info_offset.startswith('0x') else int(info_offset)
            if info_offset == offset:
                sprite_info = info
                break
        
        # Set the actual sprite thumbnail
        if sprite_info and not pixmap.isNull():
            thumbnail.set_sprite_data(pixmap, sprite_info)
            logger.debug(f"Set thumbnail for sprite at 0x{offset:06X}")
    
    def _on_thumbnail_progress(self, percent: int, message: str):
        """Handle thumbnail generation progress."""
        self.status_bar.showMessage(f"Generating thumbnails: {percent}% - {message}")
    
    def _refresh_thumbnails(self):
        """Refresh all thumbnail images."""
        if not self.sprites_data or not self.rom_path:
            QMessageBox.information(
                self,
                "No Sprites",
                "No sprites to refresh. Load a ROM and scan for sprites first."
            )
            return
        
        logger.info("Refreshing thumbnails")
        
        # Clear existing thumbnail pixmaps to force regeneration
        if self.gallery_widget:
            for thumbnail in self.gallery_widget.thumbnails.values():
                # Reset to placeholder
                thumbnail.sprite_pixmap = None
                thumbnail.update()
        
        # Regenerate all thumbnails
        self._generate_thumbnails()

    def _extract_selected_sprite(self):
        """Extract the currently selected sprite."""
        if not self.gallery_widget:
            QMessageBox.information(
                self,
                "No Gallery",
                "Gallery is not initialized."
            )
            return

        # Get selected sprite
        selected_offset = self.gallery_widget.get_selected_sprite_offset()
        if selected_offset is None:
            QMessageBox.information(
                self,
                "No Sprite Selected",
                "Please select a sprite to extract by clicking on it."
            )
            return

        # Get output filename
        rom_name = Path(self.rom_path).stem if self.rom_path else "sprite"
        default_name = f"{rom_name}_0x{selected_offset:06X}"
        
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Save Extracted Sprite",
            default_name,
            "PNG Files (*.png);;All Files (*.*)"
        )

        if not filename:
            return

        self._perform_extraction(selected_offset, filename)

    def _perform_extraction(self, offset: int, output_path: str):
        """Perform the sprite extraction."""
        try:
            self.status_bar.showMessage(f"Extracting sprite at 0x{offset:06X}...")
            
            # Create extraction parameters
            params = {
                "rom_path": self.rom_path,
                "sprite_offset": offset,
                "sprite_name": f"sprite_0x{offset:X}",
                "output_base": str(Path(output_path).stem),
                "cgram_path": None  # Could add CGRAM selection later
            }

            # Perform extraction using the extraction manager
            result = self.extraction_manager.extract_sprite_to_png(
                params["rom_path"],
                params["sprite_offset"],
                output_path,
                params["cgram_path"]
            )

            if result:
                self.status_bar.showMessage(f"Sprite extracted to {output_path}")
                
                QMessageBox.information(
                    self,
                    "Extraction Complete",
                    f"Sprite successfully extracted to:\n{output_path}"
                )
                
                # Emit signal for successful extraction
                self.sprite_extracted.emit(output_path, offset)
                
                logger.info(f"Successfully extracted sprite 0x{offset:06X} to {output_path}")
            else:
                self.status_bar.showMessage("Extraction failed")
                QMessageBox.warning(
                    self,
                    "Extraction Failed",
                    "Could not extract the sprite. Check the ROM and offset."
                )

        except Exception as e:
            logger.error(f"Error extracting sprite: {e}")
            self.status_bar.showMessage("Extraction error")
            from ui.dialogs import UserErrorDialog
            UserErrorDialog.show_error(
                self,
                "Extraction Error",
                f"Could not extract sprite: {e}"
            )

    def _show_scan_results(self):
        """Show detailed scan results in a dialog."""
        if not self.sprites_data:
            QMessageBox.information(
                self,
                "No Scan Results",
                "No sprites have been found yet. Load a ROM and scan for sprites first."
            )
            return

        # Create results dialog
        dialog = QWidget(self)
        dialog.setWindowTitle("Scan Results")
        dialog.setWindowModality(Qt.WindowModality.WindowModal)
        dialog.resize(600, 400)

        layout = QVBoxLayout()
        
        # Summary
        summary = QLabel(f"Found {len(self.sprites_data)} sprites in ROM")
        summary.setStyleSheet("font-weight: bold; font-size: 14px; padding: 10px;")
        layout.addWidget(summary)

        # Results text
        results_text = QTextEdit()
        results_text.setReadOnly(True)
        
        # Format results
        text = "Sprite Scan Results:\n\n"
        for i, sprite in enumerate(self.sprites_data, 1):
            text += f"{i}. Offset: 0x{sprite['offset']:06X}\n"
            text += f"   Name: {sprite['name']}\n"
            text += f"   Size: {sprite['decompressed_size']} bytes\n"
            text += f"   Tiles: {sprite['tile_count']}\n"
            if 'quality' in sprite:
                text += f"   Quality: {sprite['quality']:.2f}\n"
            text += "\n"
        
        results_text.setPlainText(text)
        layout.addWidget(results_text)

        # Close button
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(dialog.close)
        layout.addWidget(close_btn)

        dialog.setLayout(layout)
        dialog.show()

    def closeEvent(self, event: QCloseEvent):
        """Handle window close event."""
        # Clean up scan worker if running
        if self.scan_worker:
            WorkerManager.cleanup_worker(self.scan_worker)
            self.scan_worker = None
        
        # Clean up thumbnail worker if running
        if self.thumbnail_worker:
            WorkerManager.cleanup_worker(self.thumbnail_worker)
            self.thumbnail_worker = None
        
        self.window_closed.emit()
        super().closeEvent(event)

    def showEvent(self, event):
        """Handle show event to ensure proper layout."""
        super().showEvent(event)

        # Force layout update when window is shown
        if self.gallery_widget:
            self.gallery_widget.force_layout_update()
