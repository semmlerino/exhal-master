"""
Main window for SpritePal application
"""

from pathlib import Path
from typing import Any

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QAction, QCloseEvent, QKeyEvent, QKeySequence
from PyQt6.QtWidgets import (
    QCheckBox,
    QFileDialog,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QSplitter,
    QStatusBar,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from spritepal.core.managers import get_session_manager
from spritepal.ui.dialogs import SettingsDialog, UserErrorDialog
from spritepal.ui.extraction_panel import ExtractionPanel
from spritepal.ui.palette_preview import PalettePreviewWidget
from spritepal.ui.rom_extraction_panel import ROMExtractionPanel
from spritepal.ui.styles import get_button_style, get_muted_text_style
from spritepal.ui.zoomable_preview import PreviewPanel


class MainWindow(QMainWindow):
    """Main application window for SpritePal"""

    # Signals
    extract_requested = pyqtSignal()
    open_in_editor_requested = pyqtSignal(str)  # sprite file path
    arrange_rows_requested = pyqtSignal(str)  # sprite file path for arrangement
    arrange_grid_requested = pyqtSignal(str)  # sprite file path for grid arrangement
    inject_requested = pyqtSignal()  # inject sprite to VRAM

    def __init__(self) -> None:
        super().__init__()
        self._output_path = ""
        self._extracted_files: list[str] = []
        self.session_manager = get_session_manager()

        self._setup_ui()
        self._create_menus()
        self._connect_signals()

        # Create controller (lazy import to avoid circular dependency)
        from spritepal.core.controller import ExtractionController
        self.controller = ExtractionController(self)

        # Restore session after UI is set up
        self._restore_session()

        # Update initial UI state
        self._update_output_info_label()
        self._on_extraction_mode_changed(self.extraction_panel.mode_combo.currentIndex())

    def _setup_ui(self) -> None:
        """Initialize the user interface"""
        self.setWindowTitle("SpritePal - Sprite Extraction Tool")
        self.setMinimumSize(900, 600)

        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Main horizontal splitter
        main_splitter = QSplitter(Qt.Orientation.Horizontal)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.addWidget(main_splitter)

        # Left panel - Input and controls
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)

        # Create tab widget for extraction methods
        self.extraction_tabs = QTabWidget()

        # ROM extraction tab (first tab, selected by default)
        self.rom_extraction_panel = ROMExtractionPanel()
        self.extraction_tabs.addTab(self.rom_extraction_panel, "ROM Extraction")

        # VRAM extraction tab
        self.extraction_panel = ExtractionPanel()
        self.extraction_tabs.addTab(self.extraction_panel, "VRAM Extraction")

        # Add tab navigation shortcuts
        self.extraction_tabs.setToolTip("Switch tabs with Ctrl+Tab/Ctrl+Shift+Tab")

        left_layout.addWidget(self.extraction_tabs)

        # Output settings group
        output_group = QGroupBox("Output Settings")
        output_layout = QVBoxLayout()

        # Output name
        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("Name:"))
        self.output_name_edit = QLineEdit()
        self.output_name_edit.setPlaceholderText("e.g., cave_sprites_editor")
        name_layout.addWidget(self.output_name_edit)
        self.browse_button = QPushButton("Browse...")
        _ = self.browse_button.clicked.connect(self._browse_output)
        name_layout.addWidget(self.browse_button)
        output_layout.addLayout(name_layout)

        # Output options
        self.grayscale_check = QCheckBox("Create grayscale with palettes")
        self.grayscale_check.setChecked(True)
        self.grayscale_check.setToolTip(
            "Extract sprites in grayscale with separate .pal.json files"
        )
        output_layout.addWidget(self.grayscale_check)

        self.metadata_check = QCheckBox("Generate metadata for palette switching")
        self.metadata_check.setChecked(True)
        self.metadata_check.setToolTip(
            "Create .metadata.json file for easy palette switching in editor"
        )
        output_layout.addWidget(self.metadata_check)

        # Output files info label
        self.output_info_label = QLabel("Files to create: Loading...")
        self.output_info_label.setStyleSheet(get_muted_text_style(italic=True))
        output_layout.addWidget(self.output_info_label)

        output_group.setLayout(output_layout)
        left_layout.addWidget(output_group)

        # Action buttons
        button_layout = QGridLayout()
        button_layout.setContentsMargins(0, 10, 0, 0)
        button_layout.setSpacing(5)

        self.extract_button = QPushButton("Extract for Editing")
        self.extract_button.setMinimumHeight(35)
        self.extract_button.setShortcut(QKeySequence("Ctrl+E"))
        self.extract_button.setToolTip("Extract sprites for editing (Ctrl+E)")
        self.extract_button.setStyleSheet(get_button_style("extract"))
        button_layout.addWidget(self.extract_button, 0, 0)

        self.open_editor_button = QPushButton("Open in Editor")
        self.open_editor_button.setMinimumHeight(35)
        self.open_editor_button.setEnabled(False)
        self.open_editor_button.setShortcut(QKeySequence("Ctrl+O"))
        self.open_editor_button.setToolTip("Open extracted sprites in pixel editor (Ctrl+O)")
        self.open_editor_button.setStyleSheet(get_button_style("editor"))
        button_layout.addWidget(self.open_editor_button, 0, 1)

        self.arrange_rows_button = QPushButton("Arrange Rows")
        self.arrange_rows_button.setMinimumHeight(35)
        self.arrange_rows_button.setEnabled(False)
        self.arrange_rows_button.setShortcut(QKeySequence("Ctrl+R"))
        self.arrange_rows_button.setToolTip("Arrange sprite rows for easier editing (Ctrl+R)")
        self.arrange_rows_button.setStyleSheet(get_button_style("primary"))
        button_layout.addWidget(self.arrange_rows_button, 1, 0)

        self.arrange_grid_button = QPushButton("Grid Arrange")
        self.arrange_grid_button.setMinimumHeight(35)
        self.arrange_grid_button.setEnabled(False)
        self.arrange_grid_button.setShortcut(QKeySequence("Ctrl+G"))
        self.arrange_grid_button.setToolTip(
            "Arrange sprites using flexible grid (rows/columns/tiles) (Ctrl+G)"
        )
        self.arrange_grid_button.setStyleSheet(get_button_style("secondary"))
        button_layout.addWidget(self.arrange_grid_button, 1, 1)

        self.inject_button = QPushButton("Inject")
        self.inject_button.setMinimumHeight(35)
        self.inject_button.setEnabled(False)
        self.inject_button.setShortcut(QKeySequence("Ctrl+I"))
        self.inject_button.setToolTip("Inject edited sprite back into VRAM or ROM (Ctrl+I)")
        self.inject_button.setStyleSheet(get_button_style("accent"))
        button_layout.addWidget(self.inject_button, 2, 0, 1, 2)  # Span both columns

        left_layout.addLayout(button_layout)
        left_layout.addStretch()

        # Right panel - Previews
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)

        # Create vertical splitter for right panel
        right_splitter = QSplitter(Qt.Orientation.Vertical)
        right_layout.addWidget(right_splitter)

        # Extraction preview
        preview_group = QGroupBox("Extraction Preview")
        preview_layout = QVBoxLayout()

        self.sprite_preview = PreviewPanel()
        preview_layout.addWidget(
            self.sprite_preview, 1
        )  # Give stretch factor to expand

        # Preview info
        self.preview_info = QLabel("No sprites loaded")
        self.preview_info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_info.setStyleSheet(get_muted_text_style())
        self.preview_info.setSizePolicy(
            QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum
        )
        preview_layout.addWidget(self.preview_info, 0)  # No stretch factor

        preview_group.setLayout(preview_layout)
        right_splitter.addWidget(preview_group)

        # Palette preview
        palette_group = QGroupBox("Palette Preview")
        palette_layout = QVBoxLayout()

        self.palette_preview = PalettePreviewWidget()
        palette_layout.addWidget(self.palette_preview)

        palette_group.setLayout(palette_layout)
        right_splitter.addWidget(palette_group)

        # Configure right splitter
        right_splitter.setSizes([400, 200])  # Initial sizes
        right_splitter.setStretchFactor(0, 1)  # Preview panel stretches
        right_splitter.setStretchFactor(1, 0)  # Palette panel doesn't stretch

        # Set minimum sizes for right panel components
        preview_group.setMinimumHeight(200)
        palette_group.setMinimumHeight(150)

        # Add panels to main splitter
        main_splitter.addWidget(left_panel)
        main_splitter.addWidget(right_panel)

        # Configure main splitter
        main_splitter.setSizes([400, 500])  # Initial sizes
        main_splitter.setStretchFactor(0, 0)  # Left panel doesn't stretch
        main_splitter.setStretchFactor(1, 1)  # Right panel stretches

        # Set minimum sizes for panels
        left_panel.setMinimumWidth(300)
        right_panel.setMinimumWidth(300)

        # Status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

        # Add cache status indicator
        self._setup_status_bar_indicators()

        self.status_bar.showMessage("Ready to extract sprites")

    def _setup_status_bar_indicators(self) -> None:
        """Set up permanent status bar indicators"""
        from spritepal.utils.settings_manager import get_settings_manager

        settings_manager = get_settings_manager()

        # Only show indicators if enabled in settings
        if not settings_manager.get("cache", "show_indicators", True):
            return

        # Cache status widget
        self.cache_status_widget = QWidget()
        cache_layout = QHBoxLayout()
        cache_layout.setContentsMargins(0, 0, 0, 0)
        cache_layout.setSpacing(4)

        # Cache icon
        self.cache_icon_label = QLabel()
        self.cache_icon_label.setToolTip("ROM cache status")
        cache_layout.addWidget(self.cache_icon_label)

        # Cache info label
        self.cache_info_label = QLabel()
        self.cache_info_label.setStyleSheet(get_muted_text_style())
        cache_layout.addWidget(self.cache_info_label)

        # Cache operation badge (hidden by default)
        self.cache_operation_badge = QLabel()
        self.cache_operation_badge.setStyleSheet(
            "background-color: #3498db; color: white; padding: 2px 6px; "
            "border-radius: 3px; font-size: 10px; font-weight: bold;"
        )
        self.cache_operation_badge.setVisible(False)
        cache_layout.addWidget(self.cache_operation_badge)

        self.cache_status_widget.setLayout(cache_layout)

        # Add to status bar as permanent widget
        self.status_bar.addPermanentWidget(self.cache_status_widget)

        # Update cache status
        self._update_cache_status()

    def _update_cache_status(self) -> None:
        """Update cache status indicator"""
        from spritepal.utils.rom_cache import get_rom_cache
        from spritepal.utils.settings_manager import get_settings_manager

        settings_manager = get_settings_manager()

        # Check if indicators are enabled
        if not hasattr(self, "cache_status_widget") or not settings_manager.get("cache", "show_indicators", True):
            return

        # Check if cache is enabled
        cache_enabled = settings_manager.get_cache_enabled()

        if cache_enabled:
            # Get cache stats
            try:
                rom_cache = get_rom_cache()
                stats = rom_cache.get_cache_stats()

                # Update icon (✓ for enabled, ✗ for disabled)
                self.cache_icon_label.setText("✓ Cache:")
                self.cache_icon_label.setStyleSheet("color: green;")

                # Update info
                total_files = stats.get("total_files", 0)
                size_bytes = stats.get("total_size_bytes", 0)
                size_mb = size_bytes / (1024 * 1024)

                self.cache_info_label.setText(f"{total_files} items, {size_mb:.1f}MB")

                # Update tooltip
                sprite_caches = stats.get("sprite_location_caches", 0)
                rom_caches = stats.get("rom_info_caches", 0)
                scan_caches = stats.get("scan_progress_caches", 0)

                tooltip = "ROM Cache Statistics:\n"
                tooltip += f"Total items: {total_files}\n"
                tooltip += f"- Sprite locations: {sprite_caches}\n"
                tooltip += f"- ROM info: {rom_caches}\n"
                tooltip += f"- Scan progress: {scan_caches}\n"
                tooltip += f"Total size: {size_mb:.1f} MB"

                self.cache_status_widget.setToolTip(tooltip)

            except Exception:
                # Error getting stats
                self.cache_icon_label.setText("⚠ Cache:")
                self.cache_icon_label.setStyleSheet("color: orange;")
                self.cache_info_label.setText("Error")
                self.cache_status_widget.setToolTip("Error reading cache statistics")
        else:
            # Cache disabled
            self.cache_icon_label.setText("✗ Cache:")
            self.cache_icon_label.setStyleSheet("color: gray;")
            self.cache_info_label.setText("Disabled")
            self.cache_status_widget.setToolTip("ROM caching is disabled")

    def show_cache_operation_badge(self, operation: str) -> None:
        """Show cache operation badge in status bar

        Args:
            operation: Operation description (e.g., "Loading", "Saving", "Reading")
        """
        if hasattr(self, "cache_operation_badge"):
            self.cache_operation_badge.setText(operation)
            self.cache_operation_badge.setVisible(True)

    def hide_cache_operation_badge(self) -> None:
        """Hide cache operation badge"""
        if hasattr(self, "cache_operation_badge"):
            self.cache_operation_badge.setVisible(False)

    def _create_menus(self) -> None:
        """Create application menus"""
        menubar = self.menuBar()
        if not menubar:
            return

        # File menu
        file_menu = menubar.addMenu("File")

        # New extraction
        new_action = QAction("New Extraction", self)
        new_action.setShortcut("Ctrl+N")
        _ = new_action.triggered.connect(self._new_extraction)
        if file_menu:
            file_menu.addAction(new_action)
            file_menu.addSeparator()

        # Exit
        exit_action = QAction("Exit", self)
        exit_action.setShortcut("Ctrl+Q")
        _ = exit_action.triggered.connect(self.close)
        if file_menu:
            file_menu.addAction(exit_action)

        # Tools menu
        tools_menu = menubar.addMenu("Tools")

        # Settings
        settings_action = QAction("Settings...", self)
        settings_action.setShortcut("Ctrl+,")
        _ = settings_action.triggered.connect(self._show_settings)
        if tools_menu:
            tools_menu.addAction(settings_action)
            tools_menu.addSeparator()

        # Cache Manager
        cache_manager_action = QAction("Cache Manager...", self)
        _ = cache_manager_action.triggered.connect(self._show_cache_manager)
        if tools_menu:
            tools_menu.addAction(cache_manager_action)
            tools_menu.addSeparator()

        # Clear All Caches
        clear_cache_action = QAction("Clear All Caches", self)
        _ = clear_cache_action.triggered.connect(self._clear_all_caches)
        if tools_menu:
            tools_menu.addAction(clear_cache_action)

        # Help menu
        help_menu = menubar.addMenu("Help")

        # Keyboard shortcuts
        shortcuts_action = QAction("Keyboard Shortcuts", self)
        shortcuts_action.setShortcut("F1")
        _ = shortcuts_action.triggered.connect(self._show_keyboard_shortcuts)
        if help_menu:
            help_menu.addAction(shortcuts_action)
            help_menu.addSeparator()

        # About
        about_action = QAction("About SpritePal", self)
        _ = about_action.triggered.connect(self._show_about)
        if help_menu:
            help_menu.addAction(about_action)

    def _connect_signals(self) -> None:
        """Connect internal signals"""
        _ = self.extract_button.clicked.connect(self._on_extract_clicked)
        _ = self.open_editor_button.clicked.connect(self._on_open_editor_clicked)
        _ = self.arrange_rows_button.clicked.connect(self._on_arrange_rows_clicked)
        _ = self.arrange_grid_button.clicked.connect(self._on_arrange_grid_clicked)
        _ = self.inject_button.clicked.connect(self._on_inject_clicked)

        # Connect extraction panel signals
        self.extraction_panel.files_changed.connect(self._on_files_changed)
        self.extraction_panel.extraction_ready.connect(self._on_vram_extraction_ready)
        self.extraction_panel.mode_changed.connect(self._on_extraction_mode_changed)

        # Connect ROM extraction panel signals
        self.rom_extraction_panel.files_changed.connect(self._on_rom_files_changed)
        self.rom_extraction_panel.extraction_ready.connect(
            self._on_rom_extraction_ready
        )
        self.rom_extraction_panel.output_name_changed.connect(
            self._on_rom_output_name_changed
        )

        # Connect tab change signal
        self.extraction_tabs.currentChanged.connect(self._on_extraction_tab_changed)

        # Connect checkbox signals
        self.grayscale_check.toggled.connect(lambda: self._update_output_info_label())
        self.metadata_check.toggled.connect(lambda: self._update_output_info_label())

        # Connect output name change to sync with ROM panel
        _ = self.output_name_edit.textChanged.connect(self._on_output_name_changed)

    def _on_files_changed(self) -> None:
        """Handle when input files change"""
        # Update output name based on input files
        if self.extraction_panel.has_vram():
            vram_path = Path(self.extraction_panel.get_vram_path())
            base_name = vram_path.stem

            # Clean up common suffixes
            for suffix in ["_VRAM", ".SnesVideoRam", "_VideoRam", ".VRAM"]:
                if base_name.endswith(suffix):
                    base_name = base_name[: -len(suffix)]
                    break

            # Convert to lowercase and add suffix
            output_name = f"{base_name.lower()}_sprites_editor"
            self.output_name_edit.setText(output_name)

        # Save session data when files change
        self._save_session()

    def _on_vram_extraction_ready(self, ready: bool) -> None:
        """Handle VRAM extraction ready state change"""
        # Only enable if VRAM tab is active
        if self.extraction_tabs.currentIndex() == 1:
            self.extract_button.setEnabled(ready)

    def _on_extraction_mode_changed(self, mode_index: int) -> None:
        """Handle extraction mode change"""
        # Update checkboxes based on mode
        is_grayscale_mode = mode_index == 1

        # Disable palette-related options in grayscale mode
        self.grayscale_check.setEnabled(not is_grayscale_mode)
        self.metadata_check.setEnabled(not is_grayscale_mode)

        # Update tooltips to explain why they're disabled
        if is_grayscale_mode:
            self.grayscale_check.setToolTip(
                "Not applicable in Grayscale Only mode - no palette files will be created"
            )
            self.metadata_check.setToolTip(
                "Not applicable in Grayscale Only mode - no metadata file will be created"
            )
        else:
            self.grayscale_check.setToolTip(
                "Extract sprites in grayscale with separate .pal.json files"
            )
            self.metadata_check.setToolTip(
                "Create .metadata.json file for easy palette switching in editor"
            )

        # Update output info label
        self._update_output_info_label()

    def _update_output_info_label(self) -> None:
        """Update the label showing which files will be created"""
        # Check if we're in VRAM extraction tab
        if self.extraction_tabs.currentIndex() != 1:
            return

        is_grayscale_mode = self.extraction_panel.is_grayscale_mode()

        if is_grayscale_mode:
            self.output_info_label.setText("Files to create: grayscale PNG only")
        else:
            files = ["PNG"]
            if self.grayscale_check.isChecked():
                files.append("8 palette files (.pal.json)")
            if self.metadata_check.isChecked():
                files.append("metadata.json")

            self.output_info_label.setText(f"Files to create: {', '.join(files)}")

    def _on_rom_extraction_ready(self, ready: bool) -> None:
        """Handle ROM extraction ready state change"""
        # Only enable if ROM tab is active
        if self.extraction_tabs.currentIndex() == 0:
            self.extract_button.setEnabled(ready)

    def _on_rom_files_changed(self) -> None:
        """Handle when ROM extraction files change"""
        # ROM extraction handles its own output naming

    def _on_output_name_changed(self, text: str) -> None:
        """Handle output name change to sync with active panel"""
        # If ROM extraction tab is active, update its output name
        if self.extraction_tabs.currentIndex() == 0:
            # Temporarily disconnect to avoid infinite loop
            self.rom_extraction_panel.output_name_changed.disconnect()
            self.rom_extraction_panel.output_name_widget.set_output_name(text)
            self.rom_extraction_panel.output_name_changed.connect(
                self._on_rom_output_name_changed
            )

    def _on_rom_output_name_changed(self, text: str) -> None:
        """Handle ROM panel output name change"""
        # Update main output field without triggering sync back
        self.output_name_edit.textChanged.disconnect()
        self.output_name_edit.setText(text)
        _ = self.output_name_edit.textChanged.connect(self._on_output_name_changed)

    def _on_extraction_tab_changed(self, index: int) -> None:
        """Handle tab change between VRAM and ROM extraction"""
        if index == 0:
            # ROM extraction tab
            params = self.rom_extraction_panel.get_extraction_params()
            self.extract_button.setEnabled(params is not None)

            # Sync output name from ROM panel to main output field
            if params and params.get("output_base"):
                self.output_name_edit.setText(params["output_base"])

            # Update output info label for ROM mode
            self.output_info_label.setText("Files to create: PNG, palette files (.pal.json), metadata.json")

            # Keep output settings visible but update label
            parent = self.output_name_edit.parent()
            if parent:
                output_group = parent.parent()
                if output_group and isinstance(output_group, QGroupBox):
                    output_group.setTitle("Output Settings (Shared)")
        else:
            # VRAM extraction tab
            # Check extraction readiness based on mode
            if self.extraction_panel.is_grayscale_mode():
                ready = self.extraction_panel.has_vram()
            else:
                ready = (
                    self.extraction_panel.has_vram() and self.extraction_panel.has_cgram()
                )
            self.extract_button.setEnabled(ready)

            # Update output info label
            self._update_output_info_label()

            # Update checkbox states based on mode
            self._on_extraction_mode_changed(self.extraction_panel.mode_combo.currentIndex())

            # Reset group title
            parent = self.output_name_edit.parent()
            if parent:
                output_group = parent.parent()
                if output_group and isinstance(output_group, QGroupBox):
                    output_group.setTitle("Output Settings")

    def _browse_output(self) -> None:
        """Browse for output location"""
        # Get current directory from session
        current_files = self.extraction_panel.get_session_data()
        if current_files.get("vram_path"):
            default_dir = str(Path(current_files["vram_path"]).parent)
        else:
            default_dir = str(Path.cwd())

        suggested_path = str(
            Path(default_dir) / (self.output_name_edit.text() + ".png")
        )

        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Save Sprites As",
            suggested_path,
            "PNG Files (*.png)"
        )

        if filename:
            # Update output name without extension
            base_name = Path(filename).stem
            self.output_name_edit.setText(base_name)

    def _on_extract_clicked(self) -> None:
        """Handle extract button click"""
        # Check which tab is active
        if self.extraction_tabs.currentIndex() == 0:
            # ROM extraction
            params = self.rom_extraction_panel.get_extraction_params()
            if params:
                # Use the shared output name
                params["output_base"] = self.output_name_edit.text()

                # Validate parameters using extraction manager
                from spritepal.core.managers import get_extraction_manager
                try:
                    extraction_manager = get_extraction_manager()
                    extraction_manager.validate_extraction_params(params)
                except Exception as e:
                    _ = QMessageBox.warning(
                        self,
                        "Validation Error",
                        str(e)
                    )
                    return

                self._output_path = params["output_base"]
                self.status_bar.showMessage("Extracting sprites from ROM...")
                self.extract_button.setEnabled(False)
                self.controller.start_rom_extraction(params)
        else:
            # VRAM extraction - validation will be handled by controller
            self._output_path = self.output_name_edit.text()
            self.status_bar.showMessage("Extracting sprites from VRAM...")
            self.extract_button.setEnabled(False)

            # Emit signal for controller to handle extraction
            self.extract_requested.emit()

    def _on_open_editor_clicked(self) -> None:
        """Handle open in editor button click"""
        if self._output_path:
            sprite_file = f"{self._output_path}.png"
            self.open_in_editor_requested.emit(sprite_file)

    def _on_arrange_rows_clicked(self) -> None:
        """Handle arrange rows button click"""
        if self._output_path:
            sprite_file = f"{self._output_path}.png"
            self.arrange_rows_requested.emit(sprite_file)

    def _on_arrange_grid_clicked(self) -> None:
        """Handle arrange grid button click"""
        if self._output_path:
            sprite_file = f"{self._output_path}.png"
            self.arrange_grid_requested.emit(sprite_file)

    def _on_inject_clicked(self) -> None:
        """Handle inject to VRAM button click"""
        if self._output_path:
            self.inject_requested.emit()

    def _new_extraction(self) -> None:
        """Start a new extraction"""
        # Reset UI
        self.extraction_panel.clear_files()
        self.output_name_edit.clear()
        self.sprite_preview.clear()
        self.palette_preview.clear()
        self.preview_info.setText("No sprites loaded")
        self.open_editor_button.setEnabled(False)
        self.arrange_rows_button.setEnabled(False)
        self.arrange_grid_button.setEnabled(False)
        self._output_path = ""
        self._extracted_files = []
        self.status_bar.showMessage("Ready to extract sprites")

        # Clear session data
        self.session_manager.clear_session()

    def _show_about(self) -> None:
        """Show about dialog"""
        QMessageBox.about(
            self,
            "About SpritePal",
            "<h2>SpritePal</h2>"
            "<p>Version 1.0.0</p>"
            "<p>A modern sprite extraction tool for SNES games.</p>"
            "<p>Simplifies sprite extraction with automatic palette association.</p>"
            "<br>"
            "<p>Part of the Kirby Super Star sprite editing toolkit.</p>"
        )

    def _show_keyboard_shortcuts(self) -> None:
        """Show keyboard shortcuts dialog"""
        shortcuts_text = """
        <h3>Main Actions</h3>
        <table>
        <tr><td><b>Ctrl+E / F5</b></td><td>Extract sprites</td></tr>
        <tr><td><b>Ctrl+O</b></td><td>Open in editor</td></tr>
        <tr><td><b>Ctrl+R</b></td><td>Arrange rows</td></tr>
        <tr><td><b>Ctrl+G</b></td><td>Grid arrange</td></tr>
        <tr><td><b>Ctrl+I</b></td><td>Inject sprites</td></tr>
        <tr><td><b>Ctrl+N</b></td><td>New extraction</td></tr>
        <tr><td><b>Ctrl+Q</b></td><td>Exit application</td></tr>
        </table>

        <h3>Navigation</h3>
        <table>
        <tr><td><b>Ctrl+Tab</b></td><td>Next tab</td></tr>
        <tr><td><b>Ctrl+Shift+Tab</b></td><td>Previous tab</td></tr>
        <tr><td><b>Alt+N</b></td><td>Focus output name field</td></tr>
        <tr><td><b>F1</b></td><td>Show this help</td></tr>
        </table>

        <h3>ROM Manual Offset Mode</h3>
        <table>
        <tr><td><b>Ctrl+M</b></td><td>Open Manual Offset Control window</td></tr>
        <tr><td><b>Alt+Left</b></td><td>Find previous sprite (in dialog)</td></tr>
        <tr><td><b>Alt+Right</b></td><td>Find next sprite (in dialog)</td></tr>
        <tr><td><b>Page Up</b></td><td>Jump backward 64KB (in dialog)</td></tr>
        <tr><td><b>Page Down</b></td><td>Jump forward 64KB (in dialog)</td></tr>
        </table>

        <h3>Preview Window</h3>
        <table>
        <tr><td><b>G</b></td><td>Toggle grid</td></tr>
        <tr><td><b>F</b></td><td>Zoom to fit</td></tr>
        <tr><td><b>Ctrl+0</b></td><td>Reset zoom to 4x</td></tr>
        <tr><td><b>C</b></td><td>Toggle palette</td></tr>
        <tr><td><b>Mouse Wheel</b></td><td>Zoom in/out</td></tr>
        </table>
        """

        _ = QMessageBox.information(
            self,
            "Keyboard Shortcuts",
            shortcuts_text
        )

    def _show_settings(self) -> None:
        """Show the settings dialog"""
        dialog = SettingsDialog(self)

        # Connect signals
        dialog.settings_changed.connect(self._on_settings_changed)
        dialog.cache_cleared.connect(self._on_cache_cleared)

        dialog.exec()

    def _show_cache_manager(self) -> None:
        """Show the cache manager dialog"""
        # For now, just open settings dialog to cache tab
        dialog = SettingsDialog(self)
        dialog.tab_widget.setCurrentIndex(1)  # Switch to cache tab

        # Connect signals
        dialog.settings_changed.connect(self._on_settings_changed)
        dialog.cache_cleared.connect(self._on_cache_cleared)

        dialog.exec()

    def _clear_all_caches(self) -> None:
        """Clear all ROM caches with confirmation"""
        from spritepal.utils.rom_cache import get_rom_cache

        reply = QMessageBox.question(
            self,
            "Clear All Caches",
            "Are you sure you want to clear all ROM caches?\n\n"
            "This will remove all cached scan results and sprite locations.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            try:
                rom_cache = get_rom_cache()
                removed_count = rom_cache.clear_cache()

                self.status_bar.showMessage(f"Cleared {removed_count} cache files")

                QMessageBox.information(
                    self,
                    "Cache Cleared",
                    f"Successfully removed {removed_count} cache files."
                )
            except Exception as e:
                QMessageBox.critical(
                    self,
                    "Error",
                    f"Failed to clear cache: {e!s}"
                )

    def _on_settings_changed(self) -> None:
        """Handle settings change from settings dialog"""
        # Reload any settings that affect the main window
        # For example, cache indicators in status bar
        from spritepal.utils.rom_cache import get_rom_cache
        from spritepal.utils.settings_manager import get_settings_manager

        settings_manager = get_settings_manager()
        cache_enabled = settings_manager.get_cache_enabled()
        show_indicators = settings_manager.get("cache", "show_indicators", True)

        # Refresh ROM cache settings
        rom_cache = get_rom_cache()
        rom_cache.refresh_settings()

        # Update or hide cache status indicators
        if show_indicators:
            if not hasattr(self, "cache_status_widget"):
                # Re-create indicators if they were previously hidden
                self._setup_status_bar_indicators()
            else:
                # Update existing indicators
                self._update_cache_status()
        # Hide indicators if disabled
        elif hasattr(self, "cache_status_widget"):
            self.status_bar.removeWidget(self.cache_status_widget)
            self.cache_status_widget.deleteLater()
            del self.cache_status_widget

        if cache_enabled and show_indicators:
            self.status_bar.showMessage("Settings updated - cache enabled", 3000)
        else:
            self.status_bar.showMessage("Settings updated", 3000)

    def _on_cache_cleared(self) -> None:
        """Handle cache cleared signal from settings dialog"""
        self.status_bar.showMessage("ROM cache cleared", 3000)
        # Update cache status indicator
        self._update_cache_status()

    def get_extraction_params(self) -> dict[str, Any]:  # TODO: Should return ExtractionParams TypedDict
        """Get extraction parameters from UI"""
        return {
            "vram_path": self.extraction_panel.get_vram_path(),
            "cgram_path": self.extraction_panel.get_cgram_path() if not self.extraction_panel.is_grayscale_mode() else "",
            "oam_path": self.extraction_panel.get_oam_path(),
            "vram_offset": self.extraction_panel.get_vram_offset(),
            "output_base": self.output_name_edit.text(),  # CRITICAL FIX FOR BUG #8: Use single source of truth
            "create_grayscale": self.grayscale_check.isChecked(),
            "create_metadata": self.metadata_check.isChecked(),
            "grayscale_mode": self.extraction_panel.is_grayscale_mode(),
        }

    def extraction_complete(self, extracted_files: list[str]) -> None:
        """Called when extraction is complete"""
        self._extracted_files = extracted_files

        # CRITICAL FIX FOR BUG #7: Update _output_path based on actual extracted files
        # This ensures UI state consistency with what was actually extracted
        sprite_file = None
        for file_path in extracted_files:
            if file_path.endswith(".png"):
                sprite_file = file_path
                # Derive the actual output base path by removing .png extension
                self._output_path = file_path[:-4]  # Remove ".png"
                break

        # Enable buttons only if we successfully found a sprite file
        if sprite_file:
            self.extract_button.setEnabled(True)
            self.open_editor_button.setEnabled(True)
            self.arrange_rows_button.setEnabled(True)
            self.arrange_grid_button.setEnabled(True)
            self.inject_button.setEnabled(True)

            # Update preview info with successful extraction
            self.preview_info.setText(f"Extracted {len(extracted_files)} files")
            self.status_bar.showMessage("Extraction complete!")
        else:
            # No PNG file found - this shouldn't happen with successful extraction
            self.status_bar.showMessage("Extraction failed: No sprite file created")

    def extraction_failed(self, error_message: str) -> None:
        """Called when extraction fails"""
        self.extract_button.setEnabled(True)
        self.status_bar.showMessage("Extraction failed")

        UserErrorDialog.show_error(
            self,
            error_message,
            error_message  # Pass full error as technical details
        )

    def _restore_session(self) -> None:
        """Restore the previous session"""
        # Validate file paths
        session_data = self.session_manager.get_session_data()
        validated_paths = {}

        for key in ["vram_path", "cgram_path", "oam_path"]:
            path = session_data.get(key, "")
            if path and Path(path).exists():
                validated_paths[key] = path
            else:
                validated_paths[key] = ""

        # Check if there's a valid session to restore
        has_valid_session = bool(validated_paths.get("vram_path") or validated_paths.get("cgram_path"))

        if has_valid_session:
            # Restore file paths
            self.extraction_panel.restore_session_files(validated_paths)

            # Restore output settings
            if session_data.get("output_name"):
                self.output_name_edit.setText(session_data["output_name"])

            self.grayscale_check.setChecked(session_data.get("create_grayscale", True))
            self.metadata_check.setChecked(session_data.get("create_metadata", True))

            self.status_bar.showMessage("Previous session restored")

        # Always restore window size/position if enabled (regardless of session validity)
        from spritepal.utils.settings_manager import get_settings_manager
        settings_manager = get_settings_manager()
        if settings_manager.get("ui", "restore_position", False):
            window_geometry = self.session_manager.get_window_geometry()
            if window_geometry["width"] > 0:
                self.resize(window_geometry["width"], window_geometry["height"])

            if window_geometry["x"] >= 0:
                self.move(window_geometry["x"], window_geometry["y"])

    def _save_session(self) -> None:
        """Save the current session"""
        # Get session data from extraction panel
        session_data = self.extraction_panel.get_session_data()

        # Add output settings
        session_data.update(
            {
                "output_name": self.output_name_edit.text(),
                "create_grayscale": self.grayscale_check.isChecked(),
                "create_metadata": self.metadata_check.isChecked(),
            }
        )

        # Save session data
        self.session_manager.update_session_data(session_data)

        # Save UI settings
        window_geometry = {
            "width": self.width(),
            "height": self.height(),
            "x": self.x(),
            "y": self.y(),
        }
        self.session_manager.update_window_state(window_geometry)

        # Save the session to disk
        self.session_manager.save_session()

    def closeEvent(self, a0: QCloseEvent | None) -> None:
        """Handle window close event"""
        self._save_session()
        if a0:
            super().closeEvent(a0)

    def keyPressEvent(self, a0: QKeyEvent | None) -> None:
        """Handle keyboard shortcuts"""
        if not a0:
            return

        # Tab navigation
        if a0.modifiers() == Qt.KeyboardModifier.ControlModifier:
            if a0.key() == Qt.Key.Key_Tab:
                # Ctrl+Tab: Next tab
                current = self.extraction_tabs.currentIndex()
                next_tab = (current + 1) % self.extraction_tabs.count()
                self.extraction_tabs.setCurrentIndex(next_tab)
                a0.accept()
                return
        elif a0.modifiers() == (Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.ShiftModifier):
            if a0.key() == Qt.Key.Key_Backtab:
                # Ctrl+Shift+Tab: Previous tab
                current = self.extraction_tabs.currentIndex()
                prev_tab = (current - 1) % self.extraction_tabs.count()
                self.extraction_tabs.setCurrentIndex(prev_tab)
                a0.accept()
                return

        # F5 as alternative to Extract
        if a0.key() == Qt.Key.Key_F5 and self.extract_button.isEnabled():
            self._on_extract_clicked()
            a0.accept()
            return

        # Ctrl+M: Open Manual Offset Control (if in ROM extraction mode)
        if a0.modifiers() == Qt.KeyboardModifier.ControlModifier:
            if a0.key() == Qt.Key.Key_M:
                # Check if ROM extraction tab is active and manual mode is selected
                if (self.extraction_tabs.currentIndex() == 0 and
                    hasattr(self.rom_extraction_panel, "_manual_offset_mode") and
                    self.rom_extraction_panel._manual_offset_mode):
                    self.rom_extraction_panel._open_manual_offset_dialog()
                    a0.accept()
                    return

        # Focus shortcuts
        if a0.modifiers() == Qt.KeyboardModifier.AltModifier:
            if a0.key() == Qt.Key.Key_N:
                # Alt+N: Focus output name field
                self.output_name_edit.setFocus()
                self.output_name_edit.selectAll()
                a0.accept()
                return

        super().keyPressEvent(a0)
