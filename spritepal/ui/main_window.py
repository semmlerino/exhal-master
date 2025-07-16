"""
Main window for SpritePal application
"""

import os
from pathlib import Path

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QGroupBox, QPushButton, QLabel, QLineEdit,
    QCheckBox, QStatusBar, QMessageBox, QGridLayout
)
from PyQt6.QtCore import Qt, QSize, pyqtSignal
from PyQt6.QtGui import QAction, QIcon

from spritepal.ui.extraction_panel import ExtractionPanel
from spritepal.ui.preview_widget import SpritePreviewWidget
from spritepal.ui.zoomable_preview import PreviewPanel
from spritepal.ui.palette_preview import PalettePreviewWidget
from spritepal.core.controller import ExtractionController
from spritepal.utils.settings_manager import get_settings_manager


class MainWindow(QMainWindow):
    """Main application window for SpritePal"""
    
    # Signals
    extract_requested = pyqtSignal()
    open_in_editor_requested = pyqtSignal(str)  # sprite file path
    
    def __init__(self):
        super().__init__()
        self._output_path = ""
        self._extracted_files = []
        self.settings = get_settings_manager()
        
        self._setup_ui()
        self._create_menus()
        self._connect_signals()
        
        # Create controller
        self.controller = ExtractionController(self)
        
        # Restore session after UI is set up
        self._restore_session()
        
    def _setup_ui(self):
        """Initialize the user interface"""
        self.setWindowTitle("SpritePal - Sprite Extraction Tool")
        self.setMinimumSize(900, 600)
        
        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)
        
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
        self.grayscale_check.setToolTip("Extract sprites in grayscale with separate .pal.json files")
        output_layout.addWidget(self.grayscale_check)
        
        self.metadata_check = QCheckBox("Generate metadata for palette switching")
        self.metadata_check.setChecked(True)
        self.metadata_check.setToolTip("Create .metadata.json file for easy palette switching in editor")
        output_layout.addWidget(self.metadata_check)
        
        output_group.setLayout(output_layout)
        left_layout.addWidget(output_group)
        
        # Action buttons
        button_layout = QHBoxLayout()
        button_layout.setContentsMargins(0, 10, 0, 0)
        
        self.extract_button = QPushButton("Extract for Editing")
        self.extract_button.setMinimumHeight(40)
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
        button_layout.addWidget(self.extract_button)
        
        self.open_editor_button = QPushButton("Open in Editor")
        self.open_editor_button.setMinimumHeight(40)
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
        button_layout.addWidget(self.open_editor_button)
        
        left_layout.addLayout(button_layout)
        left_layout.addStretch()
        
        # Right panel - Previews
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        
        # Extraction preview
        preview_group = QGroupBox("Extraction Preview")
        preview_layout = QVBoxLayout()
        
        self.sprite_preview = PreviewPanel()
        preview_layout.addWidget(self.sprite_preview)
        
        # Preview info
        self.preview_info = QLabel("No sprites loaded")
        self.preview_info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_info.setStyleSheet("color: #999; padding: 5px;")
        preview_layout.addWidget(self.preview_info)
        
        preview_group.setLayout(preview_layout)
        right_layout.addWidget(preview_group)
        
        # Palette preview
        palette_group = QGroupBox("Palette Preview")
        palette_layout = QVBoxLayout()
        
        self.palette_preview = PalettePreviewWidget()
        palette_layout.addWidget(self.palette_preview)
        
        palette_group.setLayout(palette_layout)
        right_layout.addWidget(palette_group)
        
        # Add panels to main layout
        main_layout.addWidget(left_panel, 1)
        main_layout.addWidget(right_panel, 1)
        
        # Status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready to extract sprites")
        
    def _create_menus(self):
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
        
    def _connect_signals(self):
        """Connect internal signals"""
        self.extract_button.clicked.connect(self._on_extract_clicked)
        self.open_editor_button.clicked.connect(self._on_open_editor_clicked)
        
        # Connect extraction panel signals
        self.extraction_panel.files_changed.connect(self._on_files_changed)
        self.extraction_panel.extraction_ready.connect(self._on_extraction_ready)
        
    def _on_files_changed(self):
        """Handle when input files change"""
        # Update output name based on input files
        if self.extraction_panel.has_vram():
            vram_path = Path(self.extraction_panel.get_vram_path())
            base_name = vram_path.stem
            
            # Clean up common suffixes
            for suffix in ["_VRAM", ".SnesVideoRam", "_VideoRam", ".VRAM"]:
                if base_name.endswith(suffix):
                    base_name = base_name[:-len(suffix)]
                    break
            
            # Convert to lowercase and add suffix
            output_name = f"{base_name.lower()}_sprites_editor"
            self.output_name_edit.setText(output_name)
            
        # Save session data when files change
        self._save_session()
            
    def _on_extraction_ready(self, ready):
        """Handle extraction ready state change"""
        self.extract_button.setEnabled(ready)
        if ready:
            self.status_bar.showMessage("Ready to extract sprites")
        else:
            self.status_bar.showMessage("Please load VRAM and CGRAM files")
            
    def _browse_output(self):
        """Browse for output location"""
        from PyQt6.QtWidgets import QFileDialog
        
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Save Sprites As",
            self.output_name_edit.text() + ".png",
            "PNG Files (*.png)"
        )
        
        if filename:
            # Update output name without extension
            base_name = Path(filename).stem
            self.output_name_edit.setText(base_name)
            
    def _on_extract_clicked(self):
        """Handle extract button click"""
        if not self.output_name_edit.text():
            QMessageBox.warning(
                self,
                "Output Name Required",
                "Please enter a name for the output files."
            )
            return
            
        self._output_path = self.output_name_edit.text()
        self.status_bar.showMessage("Extracting sprites...")
        self.extract_button.setEnabled(False)
        
        # Emit signal for controller to handle extraction
        self.extract_requested.emit()
        
    def _on_open_editor_clicked(self):
        """Handle open in editor button click"""
        if self._output_path:
            sprite_file = f"{self._output_path}.png"
            self.open_in_editor_requested.emit(sprite_file)
            
    def _new_extraction(self):
        """Start a new extraction"""
        # Reset UI
        self.extraction_panel.clear_files()
        self.output_name_edit.clear()
        self.sprite_preview.clear()
        self.palette_preview.clear()
        self.preview_info.setText("No sprites loaded")
        self.open_editor_button.setEnabled(False)
        self._output_path = ""
        self._extracted_files = []
        self.status_bar.showMessage("Ready to extract sprites")
        
        # Clear session data
        self.settings.clear_session()
        
    def _show_about(self):
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
        
    def get_extraction_params(self):
        """Get extraction parameters from UI"""
        return {
            'vram_path': self.extraction_panel.get_vram_path(),
            'cgram_path': self.extraction_panel.get_cgram_path(),
            'oam_path': self.extraction_panel.get_oam_path(),
            'output_base': self._output_path,
            'create_grayscale': self.grayscale_check.isChecked(),
            'create_metadata': self.metadata_check.isChecked(),
        }
        
    def extraction_complete(self, extracted_files):
        """Called when extraction is complete"""
        self._extracted_files = extracted_files
        self.extract_button.setEnabled(True)
        self.open_editor_button.setEnabled(True)
        
        # Update preview info
        sprite_file = f"{self._output_path}.png"
        if sprite_file in extracted_files:
            self.preview_info.setText(f"Extracted {len(extracted_files)} files")
            self.status_bar.showMessage("Extraction complete!")
        else:
            self.status_bar.showMessage("Extraction failed")
            
    def extraction_failed(self, error_message):
        """Called when extraction fails"""
        self.extract_button.setEnabled(True)
        self.status_bar.showMessage("Extraction failed")
        QMessageBox.critical(
            self,
            "Extraction Failed",
            f"Failed to extract sprites:\n\n{error_message}"
        )
        
    def _restore_session(self):
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
            
    def _save_session(self):
        """Save the current session"""
        # Get session data from extraction panel
        session_data = self.extraction_panel.get_session_data()
        
        # Add output settings
        session_data.update({
            "output_name": self.output_name_edit.text(),
            "create_grayscale": self.grayscale_check.isChecked(),
            "create_metadata": self.metadata_check.isChecked()
        })
        
        # Save session data
        self.settings.save_session_data(session_data)
        
        # Save UI settings
        ui_data = {
            "window_width": self.width(),
            "window_height": self.height(),
            "window_x": self.x(),
            "window_y": self.y()
        }
        self.settings.save_ui_data(ui_data)
        
    def closeEvent(self, event):
        """Handle window close event"""
        self._save_session()
        super().closeEvent(event)