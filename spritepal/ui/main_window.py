"""
Main window for SpritePal application
"""

from pathlib import Path
from typing import Dict, List, Any

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QAction, QCloseEvent
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
    QVBoxLayout,
    QWidget,
)

from spritepal.core.controller import ExtractionController
from spritepal.ui.extraction_panel import ExtractionPanel
from spritepal.ui.palette_preview import PalettePreviewWidget
from spritepal.ui.zoomable_preview import PreviewPanel
from spritepal.utils.settings_manager import get_settings_manager


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
        self._extracted_files: List[str] = []
        self.settings = get_settings_manager()

        self._setup_ui()
        self._create_menus()
        self._connect_signals()

        # Create controller
        self.controller = ExtractionController(self)

        # Restore session after UI is set up
        self._restore_session()

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

        # Input files group
        self.extraction_panel = ExtractionPanel()
        left_layout.addWidget(self.extraction_panel)

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
        self.browse_button.clicked.connect(self._browse_output)
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

        output_group.setLayout(output_layout)
        left_layout.addWidget(output_group)

        # Action buttons
        button_layout = QGridLayout()
        button_layout.setContentsMargins(0, 10, 0, 0)
        button_layout.setSpacing(5)

        self.extract_button = QPushButton("Extract for Editing")
        self.extract_button.setMinimumHeight(35)
        self.extract_button.setStyleSheet("""
            QPushButton {
                background-color: #0078d4;
                color: white;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #106ebe;
            }
            QPushButton:pressed {
                background-color: #005a9e;
            }
            QPushButton:disabled {
                background-color: #555;
                color: #999;
            }
        """)
        button_layout.addWidget(self.extract_button, 0, 0)

        self.open_editor_button = QPushButton("Open in Editor")
        self.open_editor_button.setMinimumHeight(35)
        self.open_editor_button.setEnabled(False)
        self.open_editor_button.setStyleSheet("""
            QPushButton {
                background-color: #107c41;
                color: white;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #0e6332;
            }
            QPushButton:pressed {
                background-color: #0c5228;
            }
            QPushButton:disabled {
                background-color: #555;
                color: #999;
            }
        """)
        button_layout.addWidget(self.open_editor_button, 0, 1)

        self.arrange_rows_button = QPushButton("Arrange Rows")
        self.arrange_rows_button.setMinimumHeight(35)
        self.arrange_rows_button.setEnabled(False)
        self.arrange_rows_button.setToolTip("Arrange sprite rows for easier editing")
        self.arrange_rows_button.setStyleSheet("""
            QPushButton {
                background-color: #c7672a;
                color: white;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #a85521;
            }
            QPushButton:pressed {
                background-color: #86441a;
            }
            QPushButton:disabled {
                background-color: #555;
                color: #999;
            }
        """)
        button_layout.addWidget(self.arrange_rows_button, 1, 0)

        self.arrange_grid_button = QPushButton("Grid Arrange")
        self.arrange_grid_button.setMinimumHeight(35)
        self.arrange_grid_button.setEnabled(False)
        self.arrange_grid_button.setToolTip("Arrange sprites using flexible grid (rows/columns/tiles)")
        self.arrange_grid_button.setStyleSheet("""
            QPushButton {
                background-color: #2a67c7;
                color: white;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #2155a8;
            }
            QPushButton:pressed {
                background-color: #1a4486;
            }
            QPushButton:disabled {
                background-color: #555;
                color: #999;
            }
        """)
        button_layout.addWidget(self.arrange_grid_button, 1, 1)

        self.inject_button = QPushButton("Inject")
        self.inject_button.setMinimumHeight(35)
        self.inject_button.setEnabled(False)
        self.inject_button.setToolTip("Inject edited sprite back into VRAM or ROM")
        self.inject_button.setStyleSheet("""
            QPushButton {
                background-color: #744da9;
                color: white;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #5b3d85;
            }
            QPushButton:pressed {
                background-color: #472d68;
            }
            QPushButton:disabled {
                background-color: #555;
                color: #999;
            }
        """)
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
        preview_layout.addWidget(self.sprite_preview, 1)  # Give stretch factor to expand

        # Preview info
        self.preview_info = QLabel("No sprites loaded")
        self.preview_info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_info.setStyleSheet("color: #999; padding: 5px;")
        self.preview_info.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)
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
        self.status_bar.showMessage("Ready to extract sprites")

    def _create_menus(self) -> None:
        """Create application menus"""
        menubar = self.menuBar()

        # File menu
        file_menu = menubar.addMenu("File")

        # New extraction
        new_action = QAction("New Extraction", self)
        new_action.setShortcut("Ctrl+N")
        new_action.triggered.connect(self._new_extraction)
        file_menu.addAction(new_action)

        file_menu.addSeparator()

        # Exit
        exit_action = QAction("Exit", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # Help menu
        help_menu = menubar.addMenu("Help")

        # About
        about_action = QAction("About SpritePal", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)

    def _connect_signals(self) -> None:
        """Connect internal signals"""
        self.extract_button.clicked.connect(self._on_extract_clicked)
        self.open_editor_button.clicked.connect(self._on_open_editor_clicked)
        self.arrange_rows_button.clicked.connect(self._on_arrange_rows_clicked)
        self.arrange_grid_button.clicked.connect(self._on_arrange_grid_clicked)
        self.inject_button.clicked.connect(self._on_inject_clicked)

        # Connect extraction panel signals
        self.extraction_panel.files_changed.connect(self._on_files_changed)
        self.extraction_panel.extraction_ready.connect(self._on_extraction_ready)

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

    def _on_extraction_ready(self, ready: bool) -> None:
        """Handle extraction ready state change"""
        self.extract_button.setEnabled(ready)
        if ready:
            self.status_bar.showMessage("Ready to extract sprites")
        else:
            self.status_bar.showMessage("Please load VRAM and CGRAM files")

    def _browse_output(self) -> None:
        """Browse for output location"""
        # Use the default directory for output as well
        default_dir = self.settings.get_default_directory()
        suggested_path = str(Path(default_dir) / (self.output_name_edit.text() + ".png"))
        
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Save Sprites As",
            suggested_path,
            "PNG Files (*.png)",
        )

        if filename:
            # Update output name without extension
            base_name = Path(filename).stem
            self.output_name_edit.setText(base_name)
            
            # Update last used directory
            self.settings.set_last_used_directory(str(Path(filename).parent))

    def _on_extract_clicked(self) -> None:
        """Handle extract button click"""
        if not self.output_name_edit.text():
            QMessageBox.warning(
                self,
                "Output Name Required",
                "Please enter a name for the output files.",
            )
            return

        self._output_path = self.output_name_edit.text()
        self.status_bar.showMessage("Extracting sprites...")
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
        self.settings.clear_session()

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
            "<p>Part of the Kirby Super Star sprite editing toolkit.</p>",
        )

    def get_extraction_params(self) -> Dict[str, Any]:
        """Get extraction parameters from UI"""
        return {
            "vram_path": self.extraction_panel.get_vram_path(),
            "cgram_path": self.extraction_panel.get_cgram_path(),
            "oam_path": self.extraction_panel.get_oam_path(),
            "vram_offset": self.extraction_panel.get_vram_offset(),
            "output_base": self._output_path,
            "create_grayscale": self.grayscale_check.isChecked(),
            "create_metadata": self.metadata_check.isChecked(),
        }

    def extraction_complete(self, extracted_files: List[str]) -> None:
        """Called when extraction is complete"""
        self._extracted_files = extracted_files
        self.extract_button.setEnabled(True)
        self.open_editor_button.setEnabled(True)
        self.arrange_rows_button.setEnabled(True)
        self.arrange_grid_button.setEnabled(True)
        self.inject_button.setEnabled(True)

        # Update preview info
        sprite_file = f"{self._output_path}.png"
        if sprite_file in extracted_files:
            self.preview_info.setText(f"Extracted {len(extracted_files)} files")
            self.status_bar.showMessage("Extraction complete!")
        else:
            self.status_bar.showMessage("Extraction failed")

    def extraction_failed(self, error_message: str) -> None:
        """Called when extraction fails"""
        self.extract_button.setEnabled(True)
        self.status_bar.showMessage("Extraction failed")
        QMessageBox.critical(
            self, "Extraction Failed", f"Failed to extract sprites:\n\n{error_message}"
        )

    def _restore_session(self) -> None:
        """Restore the previous session"""
        if self.settings.has_valid_session():
            # Restore file paths
            validated_paths = self.settings.validate_file_paths()
            self.extraction_panel.restore_session_files(validated_paths)

            # Restore output settings
            session_data = self.settings.get_session_data()
            if session_data.get("output_name"):
                self.output_name_edit.setText(session_data["output_name"])

            self.grayscale_check.setChecked(session_data.get("create_grayscale", True))
            self.metadata_check.setChecked(session_data.get("create_metadata", True))

            # Restore window size/position
            ui_data = self.settings.get_ui_data()
            if ui_data.get("window_width", 0) > 0:
                self.resize(ui_data["window_width"], ui_data["window_height"])

            if ui_data.get("window_x", -1) >= 0:
                self.move(ui_data["window_x"], ui_data["window_y"])

            self.status_bar.showMessage("Previous session restored")

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
        self.settings.save_session_data(session_data)

        # Save UI settings
        ui_data = {
            "window_width": self.width(),
            "window_height": self.height(),
            "window_x": self.x(),
            "window_y": self.y(),
        }
        self.settings.save_ui_data(ui_data)

    def closeEvent(self, event: QCloseEvent) -> None:
        """Handle window close event"""
        self._save_session()
        super().closeEvent(event)
