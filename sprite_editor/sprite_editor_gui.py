#!/usr/bin/env python3
"""
Kirby Super Star Sprite Editor GUI
Complete PyQt6 interface for sprite extraction and injection
"""

import sys
import os
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTabWidget, QPushButton, QLabel, QLineEdit, QSpinBox,
    QFileDialog, QMessageBox, QGroupBox, QGridLayout,
    QCheckBox, QComboBox, QTextEdit, QStatusBar,
    QSplitter
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QSettings
from PyQt6.QtGui import QAction

from .sprite_editor_core import SpriteEditorCore
from .sprite_viewer_widget import SpriteViewerWidget, PaletteViewerWidget
from .multi_palette_viewer import MultiPaletteViewer

class HexLineEdit(QLineEdit):
    """Line edit for hexadecimal input"""
    def __init__(self, default="0x0000"):
        super().__init__(default)
        self.setMaxLength(8)

    def value(self):
        """Get the hex value as integer"""
        try:
            text = self.text().strip()
            if text.startswith("0x") or text.startswith("0X"):
                return int(text, 16)
            else:
                return int(text, 16)
        except ValueError:
            return 0

    def setValue(self, value):
        """Set value from integer"""
        self.setText(f"0x{value:04X}")

class ExtractWorker(QThread):
    """Worker thread for sprite extraction"""
    finished = pyqtSignal(object, int)  # image, tile_count
    error = pyqtSignal(str)
    progress = pyqtSignal(str)

    def __init__(self, vram_file, offset, size, tiles_per_row, palette_num=None, cgram_file=None):
        super().__init__()
        self.vram_file = vram_file
        self.offset = offset
        self.size = size
        self.tiles_per_row = tiles_per_row
        self.palette_num = palette_num
        self.cgram_file = cgram_file
        self.core = SpriteEditorCore()

    def run(self):
        try:
            self.progress.emit("Extracting sprites from VRAM...")
            image, tile_count = self.core.extract_sprites(
                self.vram_file, self.offset, self.size, self.tiles_per_row
            )

            # Apply palette if requested
            if self.palette_num is not None and self.cgram_file and os.path.exists(self.cgram_file):
                self.progress.emit(f"Applying palette {self.palette_num}...")
                palette = self.core.read_cgram_palette(self.cgram_file, self.palette_num)
                if palette:
                    image.putpalette(palette)

            self.finished.emit(image, tile_count)
        except Exception as e:
            self.error.emit(str(e))

class InjectWorker(QThread):
    """Worker thread for sprite injection"""
    finished = pyqtSignal(str)  # output file
    error = pyqtSignal(str)
    progress = pyqtSignal(str)

    def __init__(self, png_file, vram_file, offset, output_file):
        super().__init__()
        self.png_file = png_file
        self.vram_file = vram_file
        self.offset = offset
        self.output_file = output_file
        self.core = SpriteEditorCore()

    def run(self):
        try:
            # Validate PNG
            self.progress.emit("Validating PNG file...")
            valid, issues = self.core.validate_png_for_snes(self.png_file)
            if not valid:
                self.error.emit("PNG validation failed:\n" + "\n".join(issues))
                return

            # Convert to SNES format
            self.progress.emit("Converting to SNES format...")
            tile_data, tile_count = self.core.png_to_snes(self.png_file)

            # Inject into VRAM
            self.progress.emit(f"Injecting {tile_count} tiles into VRAM...")
            output = self.core.inject_into_vram(tile_data, self.vram_file, self.offset, self.output_file)

            self.finished.emit(output)
        except Exception as e:
            self.error.emit(str(e))

class SpriteEditorGUI(QMainWindow):
    """Main application window"""

    def __init__(self):
        super().__init__()
        self.core = SpriteEditorCore()
        self.settings = QSettings("KirbySpriteEditor", "MainWindow")

        # Current state
        self.current_vram_file = None
        self.current_image = None

        self.init_ui()
        self.load_settings()

    def init_ui(self):
        """Initialize the user interface"""
        self.setWindowTitle("Kirby Super Star Sprite Editor")
        self.setGeometry(100, 100, 1200, 800)

        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Create main layout
        main_layout = QVBoxLayout(central_widget)

        # Create toolbar
        self.create_toolbar()

        # Create tab widget
        self.tab_widget = QTabWidget()
        self.create_extract_tab()
        self.create_inject_tab()
        self.create_viewer_tab()
        self.create_multi_palette_tab()

        main_layout.addWidget(self.tab_widget)

        # Create status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")

        # Apply dark theme
        self.setStyleSheet("""
            QMainWindow {
                background-color: #2b2b2b;
            }
            QWidget {
                background-color: #3c3f41;
                color: #bbbbbb;
            }
            QTabWidget::pane {
                border: 1px solid #555;
                background-color: #3c3f41;
            }
            QTabBar::tab {
                background-color: #2b2b2b;
                padding: 8px 16px;
                margin-right: 2px;
            }
            QTabBar::tab:selected {
                background-color: #3c3f41;
            }
            QPushButton {
                background-color: #365880;
                border: 1px solid #555;
                padding: 6px 12px;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #4a7ab7;
            }
            QPushButton:pressed {
                background-color: #2d4f70;
            }
            QLineEdit, QSpinBox, QComboBox {
                background-color: #45494a;
                border: 1px solid #555;
                padding: 4px;
                border-radius: 3px;
            }
            QGroupBox {
                border: 1px solid #555;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
        """)

    def create_toolbar(self):
        """Create the toolbar"""
        toolbar = self.addToolBar("Main")
        toolbar.setMovable(False)

        # Open VRAM action
        open_vram_action = QAction("Open VRAM", self)
        open_vram_action.setShortcut("Ctrl+O")
        open_vram_action.triggered.connect(self.open_vram_file)
        toolbar.addAction(open_vram_action)

        # Open CGRAM action
        open_cgram_action = QAction("Open CGRAM", self)
        open_cgram_action.triggered.connect(self.open_cgram_file)
        toolbar.addAction(open_cgram_action)

        toolbar.addSeparator()

        # Quick extract action
        quick_extract_action = QAction("Quick Extract", self)
        quick_extract_action.setShortcut("Ctrl+E")
        quick_extract_action.triggered.connect(self.quick_extract)
        toolbar.addAction(quick_extract_action)

        # Quick inject action
        quick_inject_action = QAction("Quick Inject", self)
        quick_inject_action.setShortcut("Ctrl+I")
        quick_inject_action.triggered.connect(self.quick_inject)
        toolbar.addAction(quick_inject_action)

    def create_extract_tab(self):
        """Create the extraction tab"""
        extract_widget = QWidget()
        layout = QVBoxLayout(extract_widget)

        # File selection group
        file_group = QGroupBox("VRAM File")
        file_layout = QHBoxLayout()

        self.vram_file_edit = QLineEdit()
        self.vram_file_edit.setReadOnly(True)
        self.vram_file_btn = QPushButton("Browse...")
        self.vram_file_btn.clicked.connect(self.browse_vram_file)

        file_layout.addWidget(QLabel("File:"))
        file_layout.addWidget(self.vram_file_edit)
        file_layout.addWidget(self.vram_file_btn)
        file_group.setLayout(file_layout)
        layout.addWidget(file_group)

        # Extraction settings group
        settings_group = QGroupBox("Extraction Settings")
        settings_layout = QGridLayout()

        # Offset
        self.extract_offset_edit = HexLineEdit("0xC000")
        settings_layout.addWidget(QLabel("Offset:"), 0, 0)
        settings_layout.addWidget(self.extract_offset_edit, 0, 1)
        settings_layout.addWidget(QLabel("(VRAM $6000)"), 0, 2)

        # Size
        self.extract_size_edit = HexLineEdit("0x4000")
        settings_layout.addWidget(QLabel("Size:"), 1, 0)
        settings_layout.addWidget(self.extract_size_edit, 1, 1)
        settings_layout.addWidget(QLabel("(16KB)"), 1, 2)

        # Tiles per row
        self.tiles_per_row_spin = QSpinBox()
        self.tiles_per_row_spin.setRange(1, 64)
        self.tiles_per_row_spin.setValue(16)
        settings_layout.addWidget(QLabel("Tiles/Row:"), 2, 0)
        settings_layout.addWidget(self.tiles_per_row_spin, 2, 1)

        settings_group.setLayout(settings_layout)
        layout.addWidget(settings_group)

        # Palette settings group
        palette_group = QGroupBox("Palette (Optional)")
        palette_layout = QGridLayout()

        self.use_palette_check = QCheckBox("Apply CGRAM Palette")
        self.cgram_file_edit = QLineEdit()
        self.cgram_file_edit.setReadOnly(True)
        self.cgram_browse_btn = QPushButton("Browse...")
        self.cgram_browse_btn.clicked.connect(self.browse_cgram_file)

        self.palette_combo = QComboBox()
        for i in range(16):
            self.palette_combo.addItem(f"Palette {i}")
        self.palette_combo.setCurrentIndex(8)

        palette_layout.addWidget(self.use_palette_check, 0, 0, 1, 3)
        palette_layout.addWidget(QLabel("CGRAM:"), 1, 0)
        palette_layout.addWidget(self.cgram_file_edit, 1, 1)
        palette_layout.addWidget(self.cgram_browse_btn, 1, 2)
        palette_layout.addWidget(QLabel("Palette:"), 2, 0)
        palette_layout.addWidget(self.palette_combo, 2, 1)

        palette_group.setLayout(palette_layout)
        layout.addWidget(palette_group)

        # Extract button
        self.extract_btn = QPushButton("Extract Sprites")
        self.extract_btn.clicked.connect(self.extract_sprites)
        self.extract_btn.setMinimumHeight(40)
        layout.addWidget(self.extract_btn)

        # Output group
        output_group = QGroupBox("Output")
        output_layout = QVBoxLayout()

        self.extract_output_text = QTextEdit()
        self.extract_output_text.setReadOnly(True)
        self.extract_output_text.setMaximumHeight(100)
        output_layout.addWidget(self.extract_output_text)

        output_group.setLayout(output_layout)
        layout.addWidget(output_group)

        layout.addStretch()

        self.tab_widget.addTab(extract_widget, "Extract")

    def create_inject_tab(self):
        """Create the injection tab"""
        inject_widget = QWidget()
        layout = QVBoxLayout(inject_widget)

        # PNG file group
        png_group = QGroupBox("PNG File to Inject")
        png_layout = QHBoxLayout()

        self.png_file_edit = QLineEdit()
        self.png_file_edit.setReadOnly(True)
        self.png_browse_btn = QPushButton("Browse...")
        self.png_browse_btn.clicked.connect(self.browse_png_file)

        png_layout.addWidget(QLabel("File:"))
        png_layout.addWidget(self.png_file_edit)
        png_layout.addWidget(self.png_browse_btn)
        png_group.setLayout(png_layout)
        layout.addWidget(png_group)

        # Validation group
        validation_group = QGroupBox("PNG Validation")
        validation_layout = QVBoxLayout()

        self.validation_text = QTextEdit()
        self.validation_text.setReadOnly(True)
        self.validation_text.setMaximumHeight(80)
        validation_layout.addWidget(self.validation_text)

        validation_group.setLayout(validation_layout)
        layout.addWidget(validation_group)

        # Target settings group
        target_group = QGroupBox("Target Settings")
        target_layout = QGridLayout()

        # VRAM file
        self.inject_vram_edit = QLineEdit()
        self.inject_vram_edit.setReadOnly(True)
        self.inject_vram_btn = QPushButton("Browse...")
        self.inject_vram_btn.clicked.connect(self.browse_inject_vram)

        target_layout.addWidget(QLabel("VRAM:"), 0, 0)
        target_layout.addWidget(self.inject_vram_edit, 0, 1)
        target_layout.addWidget(self.inject_vram_btn, 0, 2)

        # Offset
        self.inject_offset_edit = HexLineEdit("0xC000")
        target_layout.addWidget(QLabel("Offset:"), 1, 0)
        target_layout.addWidget(self.inject_offset_edit, 1, 1)

        # Output file
        self.output_file_edit = QLineEdit("VRAM_edited.dmp")
        target_layout.addWidget(QLabel("Output:"), 2, 0)
        target_layout.addWidget(self.output_file_edit, 2, 1)

        target_group.setLayout(target_layout)
        layout.addWidget(target_group)

        # Inject button
        self.inject_btn = QPushButton("Inject Sprites")
        self.inject_btn.clicked.connect(self.inject_sprites)
        self.inject_btn.setMinimumHeight(40)
        layout.addWidget(self.inject_btn)

        # Output group
        output_group = QGroupBox("Output")
        output_layout = QVBoxLayout()

        self.inject_output_text = QTextEdit()
        self.inject_output_text.setReadOnly(True)
        self.inject_output_text.setMaximumHeight(100)
        output_layout.addWidget(self.inject_output_text)

        output_group.setLayout(output_layout)
        layout.addWidget(output_group)

        layout.addStretch()

        self.tab_widget.addTab(inject_widget, "Inject")

    def create_viewer_tab(self):
        """Create the viewer tab"""
        viewer_widget = QWidget()
        layout = QVBoxLayout(viewer_widget)

        # Create splitter for viewer and info panel
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left side - Image viewer
        viewer_container = QWidget()
        viewer_layout = QVBoxLayout(viewer_container)

        # Viewer controls
        controls_layout = QHBoxLayout()

        zoom_in_btn = QPushButton("Zoom In (+)")
        zoom_in_btn.clicked.connect(self.zoom_in)
        zoom_out_btn = QPushButton("Zoom Out (-)")
        zoom_out_btn.clicked.connect(self.zoom_out)
        zoom_fit_btn = QPushButton("Fit")
        zoom_fit_btn.clicked.connect(self.zoom_fit)

        self.zoom_label = QLabel("Zoom: 1x")
        self.grid_check = QCheckBox("Show Grid")
        self.grid_check.setChecked(True)
        self.grid_check.toggled.connect(self.toggle_grid)

        controls_layout.addWidget(zoom_in_btn)
        controls_layout.addWidget(zoom_out_btn)
        controls_layout.addWidget(zoom_fit_btn)
        controls_layout.addWidget(self.zoom_label)
        controls_layout.addStretch()
        controls_layout.addWidget(self.grid_check)

        viewer_layout.addLayout(controls_layout)

        # Image viewer
        self.sprite_viewer = SpriteViewerWidget()
        self.sprite_viewer.tile_hovered.connect(self.on_tile_hover)
        self.sprite_viewer.pixel_hovered.connect(self.on_pixel_hover)
        viewer_layout.addWidget(self.sprite_viewer)

        # Palette viewer
        self.palette_viewer = PaletteViewerWidget()
        viewer_layout.addWidget(self.palette_viewer)

        splitter.addWidget(viewer_container)

        # Right side - Info panel
        info_widget = QWidget()
        info_layout = QVBoxLayout(info_widget)
        info_widget.setMaximumWidth(300)

        # Image info
        info_group = QGroupBox("Image Info")
        info_group_layout = QGridLayout()

        self.info_labels = {}
        info_items = [
            ("Dimensions:", "dimensions"),
            ("Tiles:", "tiles"),
            ("Mode:", "mode"),
            ("Colors:", "colors")
        ]

        for i, (label, key) in enumerate(info_items):
            info_group_layout.addWidget(QLabel(label), i, 0)
            self.info_labels[key] = QLabel("-")
            info_group_layout.addWidget(self.info_labels[key], i, 1)

        info_group.setLayout(info_group_layout)
        info_layout.addWidget(info_group)

        # Hover info
        hover_group = QGroupBox("Hover Info")
        hover_layout = QGridLayout()

        self.tile_pos_label = QLabel("-")
        self.pixel_pos_label = QLabel("-")
        self.color_index_label = QLabel("-")

        hover_layout.addWidget(QLabel("Tile:"), 0, 0)
        hover_layout.addWidget(self.tile_pos_label, 0, 1)
        hover_layout.addWidget(QLabel("Pixel:"), 1, 0)
        hover_layout.addWidget(self.pixel_pos_label, 1, 1)
        hover_layout.addWidget(QLabel("Color:"), 2, 0)
        hover_layout.addWidget(self.color_index_label, 2, 1)

        hover_group.setLayout(hover_layout)
        info_layout.addWidget(hover_group)

        # Actions
        actions_group = QGroupBox("Actions")
        actions_layout = QVBoxLayout()

        save_btn = QPushButton("Save Current View")
        save_btn.clicked.connect(self.save_current_view)
        open_editor_btn = QPushButton("Open in External Editor")
        open_editor_btn.clicked.connect(self.open_in_editor)

        actions_layout.addWidget(save_btn)
        actions_layout.addWidget(open_editor_btn)

        actions_group.setLayout(actions_layout)
        info_layout.addWidget(actions_group)

        info_layout.addStretch()

        splitter.addWidget(info_widget)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 1)

        layout.addWidget(splitter)

        self.tab_widget.addTab(viewer_widget, "View/Edit")

    def create_multi_palette_tab(self):
        """Create the multi-palette preview tab"""
        multi_palette_widget = QWidget()
        layout = QVBoxLayout(multi_palette_widget)

        # Controls
        controls_group = QGroupBox("Multi-Palette Controls")
        controls_layout = QHBoxLayout()

        # OAM file selection
        self.oam_file_edit = QLineEdit()
        self.oam_file_edit.setReadOnly(True)
        self.oam_browse_btn = QPushButton("Load OAM")
        self.oam_browse_btn.clicked.connect(self.browse_oam_file)

        controls_layout.addWidget(QLabel("OAM:"))
        controls_layout.addWidget(self.oam_file_edit)
        controls_layout.addWidget(self.oam_browse_btn)

        # Preview size control
        controls_layout.addWidget(QLabel("Preview Size:"))
        self.preview_size_spin = QSpinBox()
        self.preview_size_spin.setRange(16, 512)
        self.preview_size_spin.setValue(64)  # Default to 64 tiles (2KB)
        self.preview_size_spin.setSuffix(" tiles")
        controls_layout.addWidget(self.preview_size_spin)

        # Generate preview button
        self.generate_multi_btn = QPushButton("Generate Multi-Palette Preview")
        self.generate_multi_btn.clicked.connect(self.generate_multi_palette_preview)
        controls_layout.addWidget(self.generate_multi_btn)

        controls_layout.addStretch()
        controls_group.setLayout(controls_layout)
        layout.addWidget(controls_group)

        # Create multi-palette viewer
        self.multi_palette_viewer = MultiPaletteViewer()
        self.multi_palette_viewer.palette_selected.connect(self.on_multi_palette_selected)
        layout.addWidget(self.multi_palette_viewer)

        self.tab_widget.addTab(multi_palette_widget, "Multi-Palette")

    # File browsing methods
    def browse_vram_file(self):
        """Browse for VRAM dump file"""
        file_name, _ = QFileDialog.getOpenFileName(
            self, "Select VRAM Dump",
            self.settings.value("last_vram_dir", ""),
            "Dump Files (*.dmp);;All Files (*.*)"
        )
        if file_name:
            self.vram_file_edit.setText(file_name)
            self.current_vram_file = file_name
            self.settings.setValue("last_vram_dir", os.path.dirname(file_name))

            # Auto-populate inject tab
            self.inject_vram_edit.setText(file_name)

            # Get VRAM info
            info = self.core.get_vram_info(file_name)
            if info:
                self.status_bar.showMessage(f"VRAM: {info['size_text']}")

    def browse_cgram_file(self):
        """Browse for CGRAM dump file"""
        file_name, _ = QFileDialog.getOpenFileName(
            self, "Select CGRAM Dump",
            self.settings.value("last_cgram_dir", ""),
            "Dump Files (*.dmp);;All Files (*.*)"
        )
        if file_name:
            self.cgram_file_edit.setText(file_name)
            self.settings.setValue("last_cgram_dir", os.path.dirname(file_name))

    def browse_png_file(self):
        """Browse for PNG file to inject"""
        file_name, _ = QFileDialog.getOpenFileName(
            self, "Select PNG File",
            self.settings.value("last_png_dir", ""),
            "PNG Files (*.png);;All Files (*.*)"
        )
        if file_name:
            self.png_file_edit.setText(file_name)
            self.settings.setValue("last_png_dir", os.path.dirname(file_name))

            # Validate PNG
            self.validate_png(file_name)

    def browse_inject_vram(self):
        """Browse for target VRAM file"""
        file_name, _ = QFileDialog.getOpenFileName(
            self, "Select Target VRAM",
            self.settings.value("last_vram_dir", ""),
            "Dump Files (*.dmp);;All Files (*.*)"
        )
        if file_name:
            self.inject_vram_edit.setText(file_name)

    def browse_oam_file(self):
        """Browse for OAM dump file"""
        file_name, _ = QFileDialog.getOpenFileName(
            self, "Select OAM Dump",
            self.settings.value("last_oam_dir", ""),
            "Dump Files (*.dmp);;All Files (*.*)"
        )
        if file_name:
            self.oam_file_edit.setText(file_name)
            self.settings.setValue("last_oam_dir", os.path.dirname(file_name))

            # Load OAM data
            if self.core.load_oam_mapping(file_name):
                self.status_bar.showMessage("OAM data loaded successfully", 3000)
            else:
                QMessageBox.warning(self, "Error", "Failed to load OAM data")

    # Main operations
    def extract_sprites(self):
        """Extract sprites from VRAM"""
        # Validate inputs
        vram_file = self.vram_file_edit.text()
        if not vram_file or not os.path.exists(vram_file):
            QMessageBox.warning(self, "Error", "Please select a valid VRAM file")
            return

        offset = self.extract_offset_edit.value()
        size = self.extract_size_edit.value()
        tiles_per_row = self.tiles_per_row_spin.value()

        # Get palette settings
        palette_num = None
        cgram_file = None
        if self.use_palette_check.isChecked():
            cgram_file = self.cgram_file_edit.text()
            if cgram_file and os.path.exists(cgram_file):
                palette_num = self.palette_combo.currentIndex()

        # Clear output
        self.extract_output_text.clear()
        self.extract_output_text.append("Starting extraction...")

        # Create worker thread
        self.extract_worker = ExtractWorker(
            vram_file, offset, size, tiles_per_row, palette_num, cgram_file
        )
        self.extract_worker.progress.connect(self.on_extract_progress)
        self.extract_worker.finished.connect(self.on_extract_finished)
        self.extract_worker.error.connect(self.on_extract_error)

        # Disable controls
        self.extract_btn.setEnabled(False)

        # Start extraction
        self.extract_worker.start()

    def on_extract_progress(self, message):
        """Handle extraction progress"""
        self.extract_output_text.append(message)
        self.status_bar.showMessage(message)

    def on_extract_finished(self, image, tile_count):
        """Handle extraction completion"""
        self.extract_btn.setEnabled(True)
        self.current_image = image

        # Update output
        self.extract_output_text.append(f"\nSuccess! Extracted {tile_count} tiles")
        self.extract_output_text.append(f"Image size: {image.width}x{image.height} pixels")

        # Show in viewer
        self.sprite_viewer.set_image(image)
        self.tab_widget.setCurrentIndex(2)  # Switch to viewer tab

        # Update info
        self.update_image_info()

        # Update palette viewer
        if hasattr(image, 'getpalette') and image.getpalette():
            self.palette_viewer.set_palette(image.getpalette())

        self.status_bar.showMessage(f"Extraction complete - {tile_count} tiles", 5000)

    def on_extract_error(self, error):
        """Handle extraction error"""
        self.extract_btn.setEnabled(True)
        self.extract_output_text.append(f"\nError: {error}")
        QMessageBox.critical(self, "Extraction Error", error)

    def inject_sprites(self):
        """Inject sprites into VRAM"""
        # Validate inputs
        png_file = self.png_file_edit.text()
        if not png_file or not os.path.exists(png_file):
            QMessageBox.warning(self, "Error", "Please select a valid PNG file")
            return

        vram_file = self.inject_vram_edit.text()
        if not vram_file or not os.path.exists(vram_file):
            QMessageBox.warning(self, "Error", "Please select a valid VRAM file")
            return

        offset = self.inject_offset_edit.value()
        output_file = self.output_file_edit.text()

        if not output_file:
            output_file = "VRAM_edited.dmp"

        # Make full path
        if not os.path.isabs(output_file):
            output_file = os.path.join(os.path.dirname(vram_file), output_file)

        # Clear output
        self.inject_output_text.clear()
        self.inject_output_text.append("Starting injection...")

        # Create worker thread
        self.inject_worker = InjectWorker(png_file, vram_file, offset, output_file)
        self.inject_worker.progress.connect(self.on_inject_progress)
        self.inject_worker.finished.connect(self.on_inject_finished)
        self.inject_worker.error.connect(self.on_inject_error)

        # Disable controls
        self.inject_btn.setEnabled(False)

        # Start injection
        self.inject_worker.start()

    def on_inject_progress(self, message):
        """Handle injection progress"""
        self.inject_output_text.append(message)
        self.status_bar.showMessage(message)

    def on_inject_finished(self, output_file):
        """Handle injection completion"""
        self.inject_btn.setEnabled(True)

        self.inject_output_text.append(f"\nSuccess! Created: {output_file}")
        self.inject_output_text.append("You can now load this file in your emulator")

        self.status_bar.showMessage("Injection complete", 5000)

        QMessageBox.information(self, "Success",
            f"Sprites injected successfully!\n\nOutput: {output_file}")

    def on_inject_error(self, error):
        """Handle injection error"""
        self.inject_btn.setEnabled(True)
        self.inject_output_text.append(f"\nError: {error}")
        QMessageBox.critical(self, "Injection Error", error)

    def validate_png(self, png_file):
        """Validate PNG file for SNES compatibility"""
        if not os.path.exists(png_file):
            return

        valid, issues = self.core.validate_png_for_snes(png_file)

        if valid:
            self.validation_text.setStyleSheet("color: #00ff00;")
            self.validation_text.setText("✓ PNG is valid for SNES conversion")
        else:
            self.validation_text.setStyleSheet("color: #ff0000;")
            self.validation_text.setText("✗ Issues found:\n" + "\n".join(issues))

    # Viewer methods
    def zoom_in(self):
        """Zoom in the viewer"""
        self.sprite_viewer.zoom_in()
        self.zoom_label.setText(f"Zoom: {self.sprite_viewer.get_current_zoom()}x")

    def zoom_out(self):
        """Zoom out the viewer"""
        self.sprite_viewer.zoom_out()
        self.zoom_label.setText(f"Zoom: {self.sprite_viewer.get_current_zoom()}x")

    def zoom_fit(self):
        """Fit image to window"""
        self.sprite_viewer.zoom_fit()
        self.zoom_label.setText(f"Zoom: {self.sprite_viewer.get_current_zoom()}x")

    def toggle_grid(self, checked):
        """Toggle grid overlay"""
        self.sprite_viewer.set_show_grid(checked)

    def on_tile_hover(self, tile_x, tile_y):
        """Handle tile hover event"""
        self.tile_pos_label.setText(f"{tile_x}, {tile_y}")

    def on_pixel_hover(self, x, y, color_index):
        """Handle pixel hover event"""
        self.pixel_pos_label.setText(f"{x}, {y}")
        self.color_index_label.setText(f"Index {color_index}")

    def update_image_info(self):
        """Update image information display"""
        info = self.sprite_viewer.get_image_info()
        if info:
            self.info_labels["dimensions"].setText(f"{info['width']}x{info['height']}")
            self.info_labels["tiles"].setText(f"{info['tiles_x']}x{info['tiles_y']} ({info['total_tiles']})")
            self.info_labels["mode"].setText(info.get("mode", "-"))
            self.info_labels["colors"].setText(str(info.get("colors", "-")))

    def save_current_view(self):
        """Save the current view to file"""
        if not self.current_image:
            QMessageBox.warning(self, "Error", "No image to save")
            return

        file_name, _ = QFileDialog.getSaveFileName(
            self, "Save Image",
            self.settings.value("last_save_dir", "sprites.png"),
            "PNG Files (*.png);;All Files (*.*)"
        )

        if file_name:
            self.current_image.save(file_name)
            self.settings.setValue("last_save_dir", os.path.dirname(file_name))
            self.status_bar.showMessage(f"Saved: {file_name}", 5000)

    def open_in_editor(self):
        """Open current image in external editor"""
        if not self.current_image:
            QMessageBox.warning(self, "Error", "No image to edit")
            return

        # Save to temp file
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            self.current_image.save(tmp.name)

            # Open with default editor
            if sys.platform == "win32":
                os.startfile(tmp.name)
            elif sys.platform == "darwin":
                os.system(f"open '{tmp.name}'")
            else:
                os.system(f"xdg-open '{tmp.name}'")

    # Multi-palette methods
    def generate_multi_palette_preview(self):
        """Generate multi-palette preview"""
        # Check prerequisites
        vram_file = self.vram_file_edit.text()
        if not vram_file or not os.path.exists(vram_file):
            QMessageBox.warning(self, "Error", "Please load a VRAM file first")
            return

        cgram_file = self.cgram_file_edit.text()
        if not cgram_file or not os.path.exists(cgram_file):
            QMessageBox.warning(self, "Error", "Please load a CGRAM file for palettes")
            return

        offset = self.extract_offset_edit.value()

        # Use preview size for multi-palette view
        preview_tiles = self.preview_size_spin.value()
        preview_size = preview_tiles * 32  # 32 bytes per tile

        # Use fewer tiles per row for preview (8 instead of 16)
        preview_tiles_per_row = min(8, self.tiles_per_row_spin.value())

        try:
            # Get OAM statistics if available
            oam_stats = None
            if self.core.oam_mapper:
                oam_stats = self.core.oam_mapper.get_palette_usage_stats()

            # Extract base sprite data (limited size for preview)
            base_img, total_tiles = self.core.extract_sprites(
                vram_file, offset, preview_size, preview_tiles_per_row
            )

            # Load all palettes
            palettes = []
            for i in range(16):
                pal = self.core.read_cgram_palette(cgram_file, i)
                palettes.append(pal)

            # Set images in multi-palette viewer
            self.multi_palette_viewer.set_single_image_all_palettes(base_img, palettes)

            # Set OAM statistics if available
            if oam_stats:
                self.multi_palette_viewer.set_oam_statistics(oam_stats)

            self.status_bar.showMessage(f"Generated multi-palette preview ({total_tiles} tiles)", 5000)

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to generate preview: {str(e)}")

    def on_multi_palette_selected(self, palette_num):
        """Handle palette selection in multi-palette viewer"""
        # Update the main viewer with selected palette
        if hasattr(self, 'sprite_viewer') and self.current_image:
            if self.current_image.mode == 'P':
                cgram_file = self.cgram_file_edit.text()
                if cgram_file and os.path.exists(cgram_file):
                    palette = self.core.read_cgram_palette(cgram_file, palette_num)
                    if palette:
                        self.current_image.putpalette(palette)
                        self.sprite_viewer.set_image(self.current_image)
                        self.palette_viewer.set_palette(palette)
                        self.status_bar.showMessage(f"Applied palette {palette_num}", 3000)

    # Quick actions
    def quick_extract(self):
        """Quick extract with default settings"""
        if not self.current_vram_file:
            self.open_vram_file()

        if self.current_vram_file:
            self.extract_sprites()

    def quick_inject(self):
        """Quick inject - prompt for file"""
        file_name, _ = QFileDialog.getOpenFileName(
            self, "Select PNG to Inject",
            self.settings.value("last_png_dir", ""),
            "PNG Files (*.png);;All Files (*.*)"
        )

        if file_name:
            self.png_file_edit.setText(file_name)
            self.tab_widget.setCurrentIndex(1)  # Switch to inject tab

            # Use current VRAM if available
            if self.current_vram_file:
                self.inject_vram_edit.setText(self.current_vram_file)

    def open_vram_file(self):
        """Open VRAM file from toolbar"""
        self.browse_vram_file()

    def open_cgram_file(self):
        """Open CGRAM file from toolbar"""
        self.browse_cgram_file()

    # Settings
    def load_settings(self):
        """Load saved settings"""
        # Window geometry
        geometry = self.settings.value("geometry")
        if geometry:
            self.restoreGeometry(geometry)

        # Last used values
        self.extract_offset_edit.setText(self.settings.value("last_offset", "0xC000"))
        self.extract_size_edit.setText(self.settings.value("last_size", "0x4000"))
        self.tiles_per_row_spin.setValue(int(self.settings.value("last_tiles_per_row", 16)))

    def closeEvent(self, event):
        """Save settings on close"""
        self.settings.setValue("geometry", self.saveGeometry())
        self.settings.setValue("last_offset", self.extract_offset_edit.text())
        self.settings.setValue("last_size", self.extract_size_edit.text())
        self.settings.setValue("last_tiles_per_row", self.tiles_per_row_spin.value())
        event.accept()

def main():
    """Main application entry point"""
    app = QApplication(sys.argv)
    app.setApplicationName("Kirby Sprite Editor")

    # Set application style
    app.setStyle("Fusion")

    window = SpriteEditorGUI()
    window.show()

    sys.exit(app.exec())

if __name__ == "__main__":
    main()