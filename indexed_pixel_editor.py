#!/usr/bin/env python3
"""
Indexed Pixel Editor for SNES Sprites
A dedicated editor for pixel-level editing of indexed color sprites
Maintains 4bpp indexed format throughout the editing process
"""

# Standard library imports
import json
import os
import sys
from pathlib import Path
from typing import Optional

# Third-party imports
import numpy as np
from PIL import Image
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import (
    QAction,
    QImage,
    QKeyEvent,
    QKeySequence,
    QPixmap,
    QWheelEvent,
)
from PyQt6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QCheckBox,
    QDialog,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QSlider,
    QStatusBar,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

# Local imports
# Import our custom widgets
from pixel_editor_widgets import ColorPaletteWidget, PixelCanvas, ZoomableScrollArea, ProgressDialog

# Import worker threads
from pixel_editor_workers import FileLoadWorker, FileSaveWorker, PaletteLoadWorker

# Import common utilities
from pixel_editor_utils import (
    DEBUG_MODE,
    debug_log,
    debug_color,
    debug_exception,
    validate_palette_file,
    validate_metadata_palette,
    extract_palette_from_pil_image,
    is_grayscale_palette,
    create_indexed_palette,
    count_non_black_colors,
)


class SettingsManager:
    """Manage application settings and recent files"""

    def __init__(self):
        self.settings_dir = Path.home() / ".indexed_pixel_editor"
        self.settings_file = self.settings_dir / "settings.json"
        self.settings_dir.mkdir(exist_ok=True)

        # Default settings
        self.settings = {
            "last_file": "",
            "recent_files": [],
            "max_recent_files": 10,
            "auto_load_last": True,
            "window_geometry": None,
            # Palette-related settings
            "last_palette_file": "",
            "recent_palette_files": [],
            "max_recent_palette_files": 10,
            "auto_offer_palette_loading": True,
            "palette_file_associations": {},  # Maps image files to their palette files
        }

        self.load_settings()

    def load_settings(self):
        """Load settings from file"""
        try:
            if self.settings_file.exists():
                with open(self.settings_file) as f:
                    loaded = json.load(f)
                    self.settings.update(loaded)
                debug_log("SETTINGS", f"Loaded settings from {self.settings_file}")
                debug_log(
                    "SETTINGS",
                    f"Settings content: recent_files={len(self.settings.get('recent_files', []))}, "
                    f"auto_load_last={self.settings.get('auto_load_last', True)}",
                    "DEBUG",
                )
        except Exception as e:
            debug_exception("SETTINGS", e)

    def save_settings(self):
        """Save settings to file"""
        try:
            with open(self.settings_file, "w") as f:
                json.dump(self.settings, f, indent=2)
            debug_log("SETTINGS", f"Saved settings to {self.settings_file}")
        except Exception as e:
            debug_exception("SETTINGS", e)

    def add_recent_file(self, file_path: str):
        """Add file to recent files list"""
        file_path = os.path.abspath(file_path)

        # Remove if already in list
        if file_path in self.settings["recent_files"]:
            self.settings["recent_files"].remove(file_path)

        # Add to beginning
        self.settings["recent_files"].insert(0, file_path)

        # Limit list size
        self.settings["recent_files"] = self.settings["recent_files"][
            : self.settings["max_recent_files"]
        ]

        # Update last file
        self.settings["last_file"] = file_path

        # Remove non-existent files
        self.settings["recent_files"] = [
            f for f in self.settings["recent_files"] if os.path.exists(f)
        ]

        self.save_settings()
        debug_log("SETTINGS", f"Added recent file: {file_path}")

    def get_recent_files(self) -> list[str]:
        """Get list of recent files that still exist"""
        existing_files = [f for f in self.settings["recent_files"] if os.path.exists(f)]
        if existing_files != self.settings["recent_files"]:
            self.settings["recent_files"] = existing_files
            self.save_settings()
        return existing_files

    def get_last_file(self) -> Optional[str]:
        """Get last opened file if it exists"""
        last_file = self.settings.get("last_file", "")
        if last_file and os.path.exists(last_file):
            return last_file
        return None

    def should_auto_load(self) -> bool:
        """Check if we should auto-load the last file"""
        return self.settings.get("auto_load_last", True)

    def add_recent_palette_file(self, file_path: str):
        """Add palette file to recent palette files list"""
        file_path = os.path.abspath(file_path)

        # Remove if already in list
        if file_path in self.settings["recent_palette_files"]:
            self.settings["recent_palette_files"].remove(file_path)

        # Add to beginning
        self.settings["recent_palette_files"].insert(0, file_path)

        # Limit list size
        self.settings["recent_palette_files"] = self.settings["recent_palette_files"][
            : self.settings["max_recent_palette_files"]
        ]

        # Update last palette file
        self.settings["last_palette_file"] = file_path

        # Remove non-existent files
        self.settings["recent_palette_files"] = [
            f for f in self.settings["recent_palette_files"] if os.path.exists(f)
        ]

        self.save_settings()
        debug_log("SETTINGS", f"Added recent palette file: {file_path}")

    def get_recent_palette_files(self) -> list[str]:
        """Get list of recent palette files that still exist"""
        existing_files = [
            f for f in self.settings["recent_palette_files"] if os.path.exists(f)
        ]
        if existing_files != self.settings["recent_palette_files"]:
            self.settings["recent_palette_files"] = existing_files
            self.save_settings()
        return existing_files

    def associate_palette_with_image(self, image_path: str, palette_path: str):
        """Associate a palette file with an image file"""
        image_path = os.path.abspath(image_path)
        palette_path = os.path.abspath(palette_path)

        self.settings["palette_file_associations"][image_path] = palette_path
        self.save_settings()
        debug_log(
            "SETTINGS",
            f"Associated palette {os.path.basename(palette_path)} with {os.path.basename(image_path)}",
        )

    def get_associated_palette(self, image_path: str) -> Optional[str]:
        """Get the associated palette file for an image"""
        image_path = os.path.abspath(image_path)
        palette_path = self.settings["palette_file_associations"].get(image_path)

        if palette_path and os.path.exists(palette_path):
            return palette_path
        if palette_path:
            # Remove broken association
            del self.settings["palette_file_associations"][image_path]
            self.save_settings()

        return None

    def should_auto_offer_palette_loading(self) -> bool:
        """Check if we should automatically offer palette loading"""
        return self.settings.get("auto_offer_palette_loading", True)


class PaletteSwitcherDialog(QDialog):
    """Dialog for switching between palettes in metadata"""

    paletteSelected = pyqtSignal(int, list)  # palette_index, colors

    def __init__(self, metadata, current_index=8, parent=None):
        super().__init__(parent)
        self.metadata = metadata
        self.current_index = current_index
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Select Palette")
        self.setModal(True)
        self.resize(400, 500)

        layout = QVBoxLayout()

        # Info label
        info_label = QLabel("Select a palette to use for color display:")
        layout.addWidget(info_label)

        # Palette list
        self.palette_list = QListWidget()

        # Add sprite palettes (8-15) from metadata
        palette_colors = self.metadata.get("palette_colors", {})

        for i in range(8, 16):
            if str(i) in palette_colors:
                colors = palette_colors[str(i)]

                # Create item with palette info
                item_text = f"Palette {i}"

                # Check for special palettes
                if i == 8:
                    item_text += " (Kirby - Purple/Pink)"
                elif i == 11:
                    item_text += " (Common - Yellow/Brown)"
                elif i == 14:
                    item_text += " (Has blue colors)"

                # Count non-black colors
                non_black = count_non_black_colors([tuple(c[:3]) for c in colors])
                item_text += f" - {non_black} colors"

                item = QListWidgetItem(item_text)
                item.setData(Qt.ItemDataRole.UserRole, i)

                if i == self.current_index:
                    item.setSelected(True)

                self.palette_list.addItem(item)

        self.palette_list.itemDoubleClicked.connect(self.accept)
        layout.addWidget(self.palette_list)

        # Color preview group
        preview_group = QGroupBox("Color Preview")
        preview_layout = QVBoxLayout()
        self.color_preview = QLabel("Select a palette to preview colors")
        self.color_preview.setMinimumHeight(50)
        preview_layout.addWidget(self.color_preview)
        preview_group.setLayout(preview_layout)
        layout.addWidget(preview_group)

        # Update preview on selection
        self.palette_list.currentItemChanged.connect(self.update_preview)

        # Buttons
        button_layout = QHBoxLayout()
        ok_button = QPushButton("OK")
        ok_button.clicked.connect(self.accept)
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)

        button_layout.addWidget(ok_button)
        button_layout.addWidget(cancel_button)
        layout.addLayout(button_layout)

        self.setLayout(layout)

        # Select current palette
        for i in range(self.palette_list.count()):
            item = self.palette_list.item(i)
            if item.data(Qt.ItemDataRole.UserRole) == self.current_index:
                self.palette_list.setCurrentItem(item)
                break

    def update_preview(self, current, previous):
        """Update color preview for selected palette"""
        if not current:
            return

        palette_idx = current.data(Qt.ItemDataRole.UserRole)
        colors = self.metadata["palette_colors"][str(palette_idx)]

        # Create color swatch preview
        preview_html = '<div style="display: flex; flex-wrap: wrap;">'
        for i, color in enumerate(colors):
            r, g, b = color[:3] if len(color) >= 3 else (0, 0, 0)
            preview_html += f'<div style="width: 20px; height: 20px; background-color: rgb({r},{g},{b}); border: 1px solid black; margin: 1px;" title="Index {i}"></div>'
        preview_html += "</div>"

        self.color_preview.setText(preview_html)
        self.color_preview.setTextFormat(Qt.TextFormat.RichText)

    def get_selected_palette(self):
        """Get the selected palette index and colors"""
        current = self.palette_list.currentItem()
        if current:
            palette_idx = current.data(Qt.ItemDataRole.UserRole)
            colors = self.metadata["palette_colors"][str(palette_idx)]
            return palette_idx, colors
        return None, None


class StartupDialog(QDialog):
    """Startup dialog showing recent files and quick actions"""

    def __init__(self, settings_manager: SettingsManager, parent=None):
        super().__init__(parent)
        self.settings = settings_manager
        self.selected_file = None
        self.action = None  # 'open_file', 'new_file', or 'open_recent'

        self.setWindowTitle("Indexed Pixel Editor - Welcome")
        self.setModal(True)
        self.setFixedSize(500, 400)

        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)

        # Title
        title = QLabel("🎨 Indexed Pixel Editor")
        title.setStyleSheet(
            "QLabel { font-size: 18px; font-weight: bold; margin: 10px; }"
        )
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        # Description
        desc = QLabel("Edit SNES sprites with enhanced mouse controls")
        desc.setStyleSheet("QLabel { color: #666; margin-bottom: 20px; }")
        desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(desc)

        # Quick actions
        actions_group = QGroupBox("Quick Actions")
        actions_layout = QVBoxLayout()

        new_btn = QPushButton("📄 Create New 8x8 Image")
        new_btn.clicked.connect(self.new_file)
        new_btn.setStyleSheet("QPushButton { padding: 8px; text-align: left; }")
        actions_layout.addWidget(new_btn)

        open_btn = QPushButton("📁 Open Indexed PNG File...")
        open_btn.clicked.connect(self.open_file)
        open_btn.setStyleSheet("QPushButton { padding: 8px; text-align: left; }")
        actions_layout.addWidget(open_btn)

        actions_group.setLayout(actions_layout)
        layout.addWidget(actions_group)

        # Recent files
        recent_group = QGroupBox("Recent Files")
        recent_layout = QVBoxLayout()

        self.recent_list = QListWidget()
        self.recent_list.setMaximumHeight(150)
        self.populate_recent_files()
        self.recent_list.itemDoubleClicked.connect(self.open_recent_file)
        recent_layout.addWidget(self.recent_list)

        if self.recent_list.count() == 0:
            no_recent = QLabel("No recent files")
            no_recent.setAlignment(Qt.AlignmentFlag.AlignCenter)
            no_recent.setStyleSheet("QLabel { color: #888; font-style: italic; }")
            recent_layout.addWidget(no_recent)

        recent_group.setLayout(recent_layout)
        layout.addWidget(recent_group)

        # Buttons
        button_layout = QHBoxLayout()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)

        button_layout.addStretch()

        if self.recent_list.count() > 0:
            open_recent_btn = QPushButton("Open Selected")
            open_recent_btn.clicked.connect(self.open_selected_recent)
            open_recent_btn.setEnabled(False)
            self.recent_list.itemSelectionChanged.connect(
                lambda: open_recent_btn.setEnabled(
                    len(self.recent_list.selectedItems()) > 0
                )
            )
            button_layout.addWidget(open_recent_btn)

        layout.addLayout(button_layout)

        # Set default focus
        if self.recent_list.count() > 0:
            self.recent_list.setCurrentRow(0)
            self.recent_list.setFocus()
        else:
            new_btn.setFocus()

    def populate_recent_files(self):
        """Populate the recent files list"""
        recent_files = self.settings.get_recent_files()

        for file_path in recent_files:
            filename = os.path.basename(file_path)
            item = QListWidgetItem(f"📁 {filename}")
            item.setToolTip(file_path)
            item.setData(Qt.ItemDataRole.UserRole, file_path)
            self.recent_list.addItem(item)

    def new_file(self):
        """Start with a new file"""
        self.action = "new_file"
        self.accept()

    def open_file(self):
        """Open file dialog"""
        self.action = "open_file"
        self.accept()

    def open_recent_file(self, item):
        """Open a recent file by double-clicking"""
        self.selected_file = item.data(Qt.ItemDataRole.UserRole)
        self.action = "open_recent"
        self.accept()

    def open_selected_recent(self):
        """Open the currently selected recent file"""
        current_item = self.recent_list.currentItem()
        if current_item:
            self.open_recent_file(current_item)


class IndexedPixelEditor(QMainWindow):
    """Main window for the indexed pixel editor"""

    def __init__(self):
        super().__init__()
        self.current_file = None
        self.modified = False
        self.settings = SettingsManager()

        # Palette management
        self.current_palette_file = None
        self.external_palette = None  # Loaded external palette data
        self.external_palette_colors = None  # Just the color array for quick access

        # Metadata support for multi-palette switching
        self.metadata = None
        self.current_palette_index = 8  # Default to Kirby palette

        self.init_ui()

        # Show startup dialog or auto-load last file
        self.handle_startup()

    def init_ui(self):
        self.setWindowTitle("Indexed Pixel Editor")
        self.setGeometry(100, 100, 800, 600)

        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QHBoxLayout(central_widget)

        # Left panel - Tools and palette
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_panel.setMaximumWidth(200)

        # Tool selection
        tool_group = QGroupBox("Tools")
        tool_layout = QVBoxLayout()

        self.tool_group = QButtonGroup()
        pencil_btn = QRadioButton("Pencil")
        pencil_btn.setChecked(True)
        fill_btn = QRadioButton("Fill")
        picker_btn = QRadioButton("Picker")

        self.tool_group.addButton(pencil_btn, 0)
        self.tool_group.addButton(fill_btn, 1)
        self.tool_group.addButton(picker_btn, 2)

        tool_layout.addWidget(pencil_btn)
        tool_layout.addWidget(fill_btn)
        tool_layout.addWidget(picker_btn)
        tool_group.setLayout(tool_layout)

        # Palette
        palette_group = QGroupBox("Palette")
        palette_layout = QVBoxLayout()
        self.palette_widget = ColorPaletteWidget()
        self.palette_widget.colorSelected.connect(self.on_color_selected)
        palette_layout.addWidget(self.palette_widget)
        palette_group.setLayout(palette_layout)

        # Options
        options_group = QGroupBox("Options")
        options_layout = QVBoxLayout()

        self.grid_checkbox = QCheckBox("Show Grid")
        self.grid_checkbox.setChecked(True)
        self.grid_checkbox.toggled.connect(self.toggle_grid)

        self.greyscale_checkbox = QCheckBox("Greyscale Mode")
        self.greyscale_checkbox.setChecked(False)
        self.greyscale_checkbox.toggled.connect(self.toggle_greyscale_mode)

        self.preview_checkbox = QCheckBox("Show Color Preview")
        self.preview_checkbox.setChecked(True)
        self.preview_checkbox.toggled.connect(self.toggle_color_preview)

        # Enhanced zoom controls
        zoom_group = QGroupBox("Zoom Controls")
        zoom_group_layout = QVBoxLayout()

        # Zoom slider with label
        zoom_slider_layout = QHBoxLayout()
        zoom_slider_layout.addWidget(QLabel("Zoom:"))
        self.zoom_slider = QSlider(Qt.Orientation.Horizontal)
        self.zoom_slider.setRange(1, 64)
        self.zoom_slider.setValue(4)  # Start with lower zoom for sprite sheets
        self.zoom_slider.valueChanged.connect(self.on_zoom_changed)
        self.zoom_label = QLabel("4x")
        zoom_slider_layout.addWidget(self.zoom_slider)
        zoom_slider_layout.addWidget(self.zoom_label)

        # Quick zoom buttons
        zoom_buttons_layout = QHBoxLayout()
        zoom_presets = [("1x", 1), ("2x", 2), ("4x", 4), ("8x", 8), ("16x", 16)]
        for label, value in zoom_presets:
            btn = QPushButton(label)
            btn.clicked.connect(lambda checked, v=value: self.set_zoom_preset(v))
            btn.setMaximumWidth(35)
            zoom_buttons_layout.addWidget(btn)

        # Fit to window button
        fit_btn = QPushButton("Fit")
        fit_btn.clicked.connect(self.zoom_to_fit)
        fit_btn.setToolTip("Fit image to visible area")
        zoom_buttons_layout.addWidget(fit_btn)

        zoom_group_layout.addLayout(zoom_slider_layout)
        zoom_group_layout.addLayout(zoom_buttons_layout)
        zoom_group.setLayout(zoom_group_layout)

        options_layout.addWidget(self.grid_checkbox)
        options_layout.addWidget(self.greyscale_checkbox)
        options_layout.addWidget(self.preview_checkbox)
        options_layout.addWidget(zoom_group)
        options_group.setLayout(options_layout)

        # Preview
        preview_group = QGroupBox("Preview")
        preview_layout = QVBoxLayout()

        # Main preview (changes based on mode)
        main_preview_label = QLabel("Current View:")
        main_preview_label.setStyleSheet("QLabel { font-weight: bold; }")
        preview_layout.addWidget(main_preview_label)

        self.preview_label = QLabel()
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_label.setStyleSheet("QLabel { background-color: #202020; }")
        self.preview_label.setMinimumHeight(100)
        preview_layout.addWidget(self.preview_label)

        # Color preview (always shows colored version)
        color_preview_label = QLabel("With Colors:")
        color_preview_label.setStyleSheet("QLabel { font-weight: bold; }")
        preview_layout.addWidget(color_preview_label)

        self.color_preview_label = QLabel()
        self.color_preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.color_preview_label.setStyleSheet(
            "QLabel { background-color: #202020; border: 2px solid #666; }"
        )
        self.color_preview_label.setMinimumHeight(100)
        preview_layout.addWidget(self.color_preview_label)

        preview_group.setLayout(preview_layout)

        left_layout.addWidget(tool_group)
        left_layout.addWidget(palette_group)
        left_layout.addWidget(options_group)
        left_layout.addWidget(preview_group)
        left_layout.addStretch()

        # Right panel - Canvas
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)

        # Scroll area for canvas (custom one that forwards wheel events)
        scroll_area = ZoomableScrollArea()

        # Create canvas with palette widget
        self.canvas = PixelCanvas(self.palette_widget)
        self.canvas.pixelChanged.connect(self.on_canvas_changed)
        self.canvas.editor_parent = self  # Set parent reference for wheel zoom

        # Set initial drawing color
        self.canvas.current_color = self.palette_widget.selected_index
        rgb = (
            self.palette_widget.colors[self.canvas.current_color]
            if self.canvas.current_color < len(self.palette_widget.colors)
            else None
        )
        debug_log(
            "EDITOR",
            f"Canvas created with initial color: {debug_color(self.canvas.current_color, rgb)}",
        )
        scroll_area.setWidget(self.canvas)
        scroll_area.setWidgetResizable(False)
        scroll_area.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Make sure scroll area doesn't consume wheel events meant for zooming
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        right_layout.addWidget(scroll_area)

        # Add panels to main layout
        layout.addWidget(left_panel)
        layout.addWidget(right_panel, 1)

        # Create menu bar
        self.create_menu_bar()

        # Create toolbar
        self.create_toolbar()

        # Status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

        # Connect tool selection
        self.tool_group.buttonClicked.connect(self.on_tool_changed)

        # Start with a new 8x8 image
        self.new_file()

    def create_menu_bar(self):
        menubar = self.menuBar()

        # File menu
        file_menu = menubar.addMenu("File")

        new_action = QAction("New", self)
        new_action.setShortcut(QKeySequence.StandardKey.New)
        new_action.triggered.connect(self.new_file)

        open_action = QAction("Open", self)
        open_action.setShortcut(QKeySequence.StandardKey.Open)
        open_action.triggered.connect(self.open_file)

        save_action = QAction("Save", self)
        save_action.setShortcut(QKeySequence.StandardKey.Save)
        save_action.triggered.connect(self.save_file)

        save_as_action = QAction("Save As...", self)
        save_as_action.setShortcut(QKeySequence.StandardKey.SaveAs)
        save_as_action.triggered.connect(self.save_file_as)

        file_menu.addAction(new_action)
        file_menu.addAction(open_action)
        file_menu.addSeparator()
        file_menu.addAction(save_action)
        file_menu.addAction(save_as_action)
        file_menu.addSeparator()

        # Palette loading actions
        load_palette_action = QAction("Load Palette File...", self)
        load_palette_action.triggered.connect(self.load_palette_file)
        load_palette_action.setToolTip("Load external .pal.json palette file")

        load_with_palette_action = QAction("Load Grayscale + Palette...", self)
        load_with_palette_action.triggered.connect(self.load_grayscale_with_palette)
        load_with_palette_action.setToolTip(
            "Load grayscale image with associated palette"
        )

        file_menu.addAction(load_palette_action)
        file_menu.addAction(load_with_palette_action)

        # Edit menu
        edit_menu = menubar.addMenu("Edit")

        undo_action = QAction("Undo", self)
        undo_action.setShortcut(QKeySequence.StandardKey.Undo)
        undo_action.triggered.connect(self.canvas.undo)

        redo_action = QAction("Redo", self)
        redo_action.setShortcut(QKeySequence.StandardKey.Redo)
        redo_action.triggered.connect(self.canvas.redo)

        edit_menu.addAction(undo_action)
        edit_menu.addAction(redo_action)

        # View menu with zoom controls
        view_menu = menubar.addMenu("View")

        zoom_in_action = QAction("Zoom In", self)
        zoom_in_action.setShortcut(QKeySequence.StandardKey.ZoomIn)
        zoom_in_action.triggered.connect(self.zoom_in)

        zoom_out_action = QAction("Zoom Out", self)
        zoom_out_action.setShortcut(QKeySequence.StandardKey.ZoomOut)
        zoom_out_action.triggered.connect(self.zoom_out)

        zoom_reset_action = QAction("Reset Zoom", self)
        zoom_reset_action.setShortcut("Ctrl+0")
        zoom_reset_action.triggered.connect(lambda: self.set_zoom_preset(4))

        zoom_fit_action = QAction("Zoom to Fit", self)
        zoom_fit_action.setShortcut("Ctrl+Shift+0")
        zoom_fit_action.triggered.connect(self.zoom_to_fit)

        view_menu.addAction(zoom_in_action)
        view_menu.addAction(zoom_out_action)
        view_menu.addAction(zoom_reset_action)
        view_menu.addAction(zoom_fit_action)
        view_menu.addSeparator()

        # Quick zoom presets
        for label, value in [("1x", 1), ("2x", 2), ("4x", 4), ("8x", 8)]:
            action = QAction(f"Zoom {label}", self)
            action.setShortcut(f"Ctrl+{value}")
            action.triggered.connect(lambda checked, v=value: self.set_zoom_preset(v))
            view_menu.addAction(action)

        view_menu.addSeparator()

        # Enhanced features for metadata support
        # Switch palette action
        self.switch_palette_action = QAction("Switch &Palette...", self)
        self.switch_palette_action.setShortcut("P")
        self.switch_palette_action.setStatusTip("Switch between available palettes")
        self.switch_palette_action.triggered.connect(self.show_palette_switcher)
        self.switch_palette_action.setEnabled(False)  # Disabled until metadata loaded
        view_menu.addAction(self.switch_palette_action)

        # Toggle color mode action
        toggle_color_action = QAction("Toggle &Color Mode", self)
        toggle_color_action.setShortcut("C")
        toggle_color_action.setStatusTip("Toggle between index and color view")
        toggle_color_action.triggered.connect(self.toggle_color_mode_shortcut)
        view_menu.addAction(toggle_color_action)

        # Recent files menu
        self.recent_menu = file_menu.addMenu("Recent Files")
        self.update_recent_files_menu()

    def create_toolbar(self):
        toolbar = QToolBar()
        self.addToolBar(toolbar)

        # Add common actions
        toolbar.addAction("New", self.new_file)
        toolbar.addAction("Open", self.open_file)
        toolbar.addAction("Save", self.save_file)
        toolbar.addSeparator()
        toolbar.addAction("Undo", self.canvas.undo)
        toolbar.addAction("Redo", self.canvas.redo)

    def new_file(self):
        """Create a new 8x8 image"""
        if self.check_save():
            debug_log("EDITOR", "Creating new 8x8 image file")
            self.canvas.new_image(8, 8)
            # Set initial color to palette selection
            self.canvas.current_color = self.palette_widget.selected_index
            self.current_file = None
            self.modified = False
            self.setWindowTitle("Indexed Pixel Editor - New File")
            self.update_preview()
            rgb = (
                self.palette_widget.colors[self.canvas.current_color]
                if self.canvas.current_color < len(self.palette_widget.colors)
                else None
            )
            debug_log(
                "EDITOR",
                f"New file created with current color: {debug_color(self.canvas.current_color, rgb)}",
            )

    def open_file(self):
        """Open an indexed PNG file"""
        if not self.check_save():
            return

        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open Indexed PNG", "", "PNG Files (*.png);;All Files (*)"
        )

        if file_path:
            self.load_file_by_path(file_path)

    def save_file(self):
        """Save the current file"""
        if self.current_file:
            self.save_to_file(self.current_file)
        else:
            self.save_file_as()

    def save_file_as(self):
        """Save with a new filename"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Indexed PNG", "", "PNG Files (*.png)"
        )

        if file_path:
            if not file_path.endswith(".png"):
                file_path += ".png"
            self.save_to_file(file_path)

    def save_to_file(self, file_path: str):
        """Save image to file"""
        # Get image data
        img = self.canvas.get_pil_image()
        if not img:
            QMessageBox.warning(self, "Warning", "No image to save")
            return
            
        # Extract image array and palette
        image_array = np.array(img, dtype=np.uint8)
        palette_data = img.getpalette()
        
        if palette_data is None:
            QMessageBox.critical(self, "Error", "Image has no palette data")
            return
            
        # Create progress dialog
        progress_dialog = ProgressDialog("Saving Image", f"Saving {os.path.basename(file_path)}...", self)
        progress_dialog.show()
        
        # Create worker thread
        self.save_worker = FileSaveWorker(image_array, palette_data, file_path, self)
        
        # Connect signals
        self.save_worker.progress.connect(progress_dialog.update_progress)
        self.save_worker.error.connect(self._handle_save_error)
        self.save_worker.saved.connect(self._handle_save_success)
        self.save_worker.finished.connect(progress_dialog.finish)
        
        # Connect cancel
        def on_cancel():
            self.save_worker.cancel()
            progress_dialog.finish()
        progress_dialog.cancel_button.clicked.disconnect()  # Remove default handler
        progress_dialog.cancel_button.clicked.connect(on_cancel)
        
        # Store dialog for use in handlers
        self._save_progress_dialog = progress_dialog
        
        # Start the worker
        self.save_worker.start()
        
    def _handle_save_error(self, error_message: str):
        """Handle errors from file saving"""
        if hasattr(self, '_save_progress_dialog'):
            self._save_progress_dialog.finish()
            
        QMessageBox.critical(self, "Error", f"Failed to save file: {error_message}")
        debug_log("EDITOR", f"Save error: {error_message}", "ERROR")
        
    def _handle_save_success(self, saved_path: str):
        """Handle successful file save"""
        try:
            self.current_file = saved_path
            self.modified = False
            self.setWindowTitle(f"Indexed Pixel Editor - {os.path.basename(saved_path)}")
            self.status_bar.showMessage(f"Saved to {saved_path}", 3000)
            
            # Add to recent files
            self.settings.add_recent_file(saved_path)
            self.update_recent_files_menu()
            
            debug_log("EDITOR", f"Successfully saved file: {saved_path}")
            
        finally:
            # Clean up
            if hasattr(self, '_save_progress_dialog'):
                self._save_progress_dialog.finish()
            self._save_progress_dialog = None

    def handle_startup(self):
        """Handle startup - show dialog or auto-load"""
        # Check if we should auto-load the last file
        if self.settings.should_auto_load():
            last_file = self.settings.get_last_file()
            if last_file:
                debug_log("EDITOR", f"Auto-loading last file: {last_file}")
                self.load_file_by_path(last_file)
                return

        # Show startup dialog if we have recent files or no auto-load
        recent_files = self.settings.get_recent_files()
        if recent_files or not self.settings.should_auto_load():
            self.show_startup_dialog()

    def show_startup_dialog(self):
        """Show the startup dialog"""
        dialog = StartupDialog(self.settings, self)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            if dialog.action == "new_file":
                self.new_file()
            elif dialog.action == "open_file":
                self.open_file()
            elif dialog.action == "open_recent" and dialog.selected_file:
                self.load_file_by_path(dialog.selected_file)

    def load_file_by_path(self, file_path: str):
        """Load a file by its path"""
        # Create progress dialog
        progress_dialog = ProgressDialog("Loading Image", f"Loading {os.path.basename(file_path)}...", self)
        progress_dialog.show()
        
        # Create worker thread
        self.load_worker = FileLoadWorker(file_path, self)
        
        # Connect signals
        self.load_worker.progress.connect(progress_dialog.update_progress)
        self.load_worker.error.connect(self._handle_load_error)
        self.load_worker.result.connect(self._handle_load_result)
        self.load_worker.finished.connect(progress_dialog.finish)
        
        # Connect cancel
        progress_dialog.cancelled = False
        def on_cancel():
            progress_dialog.cancelled = True
            self.load_worker.cancel()
            progress_dialog.finish()
        progress_dialog.cancel_button.clicked.disconnect()  # Remove default handler
        progress_dialog.cancel_button.clicked.connect(on_cancel)
        
        # Store file path and dialog for use in handlers
        self._loading_file_path = file_path
        self._load_progress_dialog = progress_dialog
        
        # Start the worker
        self.load_worker.start()
        
        # Return True to indicate load started (actual result comes via signals)
        return True
        
    def _handle_load_error(self, error_message: str):
        """Handle errors from file loading"""
        if hasattr(self, '_load_progress_dialog'):
            self._load_progress_dialog.finish()
        
        QMessageBox.critical(self, "Error", f"Failed to load file: {error_message}")
        debug_log("EDITOR", f"Load error: {error_message}", "ERROR")
        
    def _handle_load_result(self, image_array: np.ndarray, metadata: dict):
        """Handle successful file load"""
        try:
            # Create PIL image from array for compatibility with existing code
            img = Image.fromarray(image_array, mode='P')
            
            # Apply palette from metadata
            if 'palette' in metadata:
                img.putpalette(metadata['palette'])
            
            # Load into canvas
            self.canvas.load_image(img)
            self.current_file = self._loading_file_path
            self.modified = False
            self.setWindowTitle(f"Indexed Pixel Editor - {os.path.basename(self._loading_file_path)}")
            self.update_preview()
            
            # Add to recent files
            self.settings.add_recent_file(self._loading_file_path)
            self.update_recent_files_menu()
            
            debug_log("EDITOR", f"Successfully loaded file: {self._loading_file_path}")
            
            # Check for metadata file (for multi-palette support)
            metadata_path = self._loading_file_path.replace(".png", "_metadata.json")
            if os.path.exists(metadata_path) and not metadata_path.endswith(
                "_metadata.json"
            ):
                # Make sure we don't double-add _metadata.json
                metadata_path = os.path.splitext(self._loading_file_path)[0] + "_metadata.json"
            
            if os.path.exists(metadata_path):
                try:
                    with open(metadata_path) as f:
                        self.metadata = json.load(f)
                    debug_log("EDITOR", f"Loaded metadata from {metadata_path}")
                    
                    # Enable palette switching
                    if hasattr(self, "switch_palette_action"):
                        self.switch_palette_action.setEnabled(True)
                    
                    # Update status
                    self.update_status_palette_info()
                except Exception as e:
                    debug_log("EDITOR", f"Failed to load metadata: {e}", "WARNING")
                    self.metadata = None
            
            # Check for paired palette file - do this AFTER image is loaded
            # This ensures the external palette overrides any palette from the image
            self._check_and_offer_palette_loading(self._loading_file_path)
            
            # Update status bar
            self.status_bar.showMessage(f"Loaded {os.path.basename(self._loading_file_path)}", 3000)
            
        except Exception as e:
            self._handle_load_error(str(e))
        finally:
            # Clean up
            if hasattr(self, '_load_progress_dialog'):
                self._load_progress_dialog.finish()
            self._loading_file_path = None
            self._load_progress_dialog = None

    def load_palette_file(self):
        """Load an external palette file (.pal.json)"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Load Palette File",
            "",
            "Palette Files (*.pal.json);;JSON Files (*.json);;All Files (*)",
        )

        if file_path:
            success = self.load_palette_by_path(file_path)
            if success:
                self.status_bar.showMessage(
                    f"Loaded palette: {os.path.basename(file_path)}", 3000
                )

    def load_palette_by_path(self, file_path: str) -> bool:
        """Load a palette file by its path"""
        # Create progress dialog
        progress_dialog = ProgressDialog("Loading Palette", f"Loading {os.path.basename(file_path)}...", self)
        progress_dialog.show()
        
        # For JSON files, we need to handle our custom format
        if file_path.endswith('.json'):
            # Use synchronous loading for our custom JSON format
            # since PaletteLoadWorker expects a different format
            try:
                progress_dialog.update_progress(30, "Reading palette file...")
                
                with open(file_path) as f:
                    palette_data = json.load(f)
                
                progress_dialog.update_progress(50, "Validating palette...")
                
                # Validate palette format
                if not self._validate_palette_file(palette_data):
                    progress_dialog.finish()
                    QMessageBox.warning(
                        self,
                        "Invalid Palette",
                        f"File {os.path.basename(file_path)} is not a valid palette file",
                    )
                    return False
                
                progress_dialog.update_progress(70, "Extracting colors...")
                
                # Extract colors
                colors = palette_data["palette"]["colors"]
                if len(colors) < 16:
                    progress_dialog.finish()
                    QMessageBox.warning(
                        self,
                        "Incomplete Palette",
                        f"Palette has only {len(colors)} colors, need 16",
                    )
                    return False
                
                progress_dialog.update_progress(90, "Applying palette...")
                
                # Convert to tuples and store
                self.external_palette = palette_data
                self.external_palette_colors = [tuple(color[:3]) for color in colors[:16]]
                self.current_palette_file = file_path
                
                debug_log(
                    "EDITOR",
                    f"Loading palette colors: {self.external_palette_colors[:4]}"
                )
                
                # Get palette name
                palette_name = palette_data.get("palette", {}).get(
                    "name", "External Palette"
                )
                
                # Apply to palette widget
                self.palette_widget.set_palette(self.external_palette_colors, palette_name)
                
                # Force updates
                self.canvas.update()
                self.palette_widget.update()
                
                # Update preview to show new colors
                self.update_preview()
                
                # Update title to show palette
                current_title = self.windowTitle()
                if " | " in current_title:
                    base_title = current_title.split(" | ")[0]
                else:
                    base_title = current_title
                self.setWindowTitle(f"{base_title} | {palette_name}")
                
                # Update preview with new palette
                self.update_preview()
                
                debug_log(
                    "EDITOR",
                    f"Successfully loaded external palette: {os.path.basename(file_path)}",
                )
                debug_log(
                    "EDITOR",
                    f"Palette info: {palette_name}, {len(self.external_palette_colors)} colors",
                )
                
                # Add to recent palette files
                self.settings.add_recent_palette_file(file_path)
                
                # Associate with current image if one is loaded
                if self.current_file:
                    self.settings.associate_palette_with_image(self.current_file, file_path)
                    
                progress_dialog.update_progress(100, "Complete!")
                progress_dialog.finish()
                
                return True
                
            except Exception as e:
                progress_dialog.finish()
                QMessageBox.critical(self, "Error", f"Failed to load palette: {e!s}")
                return False
        else:
            # For non-JSON files, use the worker thread
            self.palette_worker = PaletteLoadWorker(file_path, self)
            
            # Connect signals
            self.palette_worker.progress.connect(progress_dialog.update_progress)
            self.palette_worker.error.connect(self._handle_palette_error)
            self.palette_worker.result.connect(self._handle_palette_result)
            self.palette_worker.finished.connect(progress_dialog.finish)
            
            # Connect cancel
            def on_cancel():
                self.palette_worker.cancel()
                progress_dialog.finish()
            progress_dialog.cancel_button.clicked.disconnect()
            progress_dialog.cancel_button.clicked.connect(on_cancel)
            
            # Store dialog and path for handlers
            self._palette_progress_dialog = progress_dialog
            self._loading_palette_path = file_path
            
            # Start worker
            self.palette_worker.start()
            
            return True  # Actual result comes via signals
            
    def _handle_palette_error(self, error_message: str):
        """Handle errors from palette loading"""
        if hasattr(self, '_palette_progress_dialog'):
            self._palette_progress_dialog.finish()
            
        QMessageBox.critical(self, "Error", f"Failed to load palette: {error_message}")
        debug_log("EDITOR", f"Palette load error: {error_message}", "ERROR")
        
    def _handle_palette_result(self, palette_data: dict):
        """Handle successful palette load from worker"""
        try:
            # Extract colors based on format
            if 'colors' in palette_data:
                colors = palette_data['colors']
            else:
                self._handle_palette_error("Invalid palette format")
                return
                
            # Ensure we have at least 16 colors
            if len(colors) < 16:
                # Pad with black
                while len(colors) < 16:
                    colors.append([0, 0, 0])
                    
            # Convert to tuples
            color_tuples = [tuple(c[:3]) for c in colors[:16]]
            
            # Store palette data
            self.external_palette = palette_data
            self.external_palette_colors = color_tuples
            self.current_palette_file = self._loading_palette_path
            
            # Get palette name
            palette_name = palette_data.get('name', os.path.basename(self._loading_palette_path))
            
            # Apply to palette widget
            self.palette_widget.set_palette(color_tuples, palette_name)
            
            # Update canvas and preview
            self.canvas.update()
            self.update_preview()
            
            # Update title
            current_title = self.windowTitle()
            if " | " in current_title:
                base_title = current_title.split(" | ")[0]
            else:
                base_title = current_title
            self.setWindowTitle(f"{base_title} | {palette_name}")
            
            # Add to recent files
            self.settings.add_recent_palette_file(self._loading_palette_path)
            
            # Associate with current image
            if self.current_file:
                self.settings.associate_palette_with_image(self.current_file, self._loading_palette_path)
                
            debug_log("EDITOR", f"Successfully loaded palette: {palette_name}")
            
        finally:
            # Clean up
            if hasattr(self, '_palette_progress_dialog'):
                self._palette_progress_dialog.finish()
            self._palette_progress_dialog = None
            self._loading_palette_path = None

    def load_grayscale_with_palette(self):
        """Load a grayscale image and prompt for its palette"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Load Grayscale Image", "", "PNG Files (*.png);;All Files (*)"
        )

        if not file_path:
            return

        # Load the image first
        if not self.load_file_by_path(file_path):
            return

        # Prompt for palette file
        palette_path, _ = QFileDialog.getOpenFileName(
            self,
            "Load Associated Palette",
            os.path.dirname(file_path),
            "Palette Files (*.pal.json);;JSON Files (*.json);;All Files (*)",
        )

        if palette_path:
            self.load_palette_by_path(palette_path)

    def _check_and_offer_palette_loading(self, image_path: str):
        """Check for paired palette file and offer to load it"""
        # Skip if auto-offering is disabled
        if not self.settings.should_auto_offer_palette_loading():
            return

        found_palette = None

        # First, check for associated palette from settings
        associated_palette = self.settings.get_associated_palette(image_path)
        if associated_palette:
            found_palette = associated_palette
            debug_log(
                "EDITOR",
                f"Found associated palette from settings: {associated_palette}",
            )
        else:
            # Look for companion palette file with same base name
            base_path = os.path.splitext(image_path)[0]
            palette_paths = [
                f"{base_path}.pal.json",
                f"{base_path}_palette.json",
                f"{base_path}_metadata.json",  # Check metadata files too
            ]

            for palette_path in palette_paths:
                if os.path.exists(palette_path):
                    # Check if it's a valid palette file
                    try:
                        debug_log(
                            "EDITOR",
                            f"Checking palette file: {os.path.basename(palette_path)}",
                            "DEBUG",
                        )
                        with open(palette_path) as f:
                            data = json.load(f)
                        if self._validate_palette_file(data):
                            debug_log(
                                "EDITOR",
                                f"Found valid palette file: {palette_path}",
                                "DEBUG",
                            )
                            found_palette = palette_path
                            break
                        # Check metadata format too
                        if validate_metadata_palette(data):
                            debug_log(
                                "EDITOR",
                                f"Found metadata format palette: {palette_path}",
                                "DEBUG",
                            )
                            found_palette = palette_path
                            break
                    except Exception as e:
                        debug_log(
                            "EDITOR", f"Failed to check {palette_path}: {e}", "DEBUG"
                        )
                        continue

        if found_palette:
            reply = QMessageBox.question(
                self,
                "Load Associated Palette?",
                f"Found associated palette file:\n{os.path.basename(found_palette)}\n\n"
                "Would you like to load it for accurate color preview?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes,
            )

            if reply == QMessageBox.StandardButton.Yes:
                if found_palette.endswith("_metadata.json"):
                    self._load_metadata_palette(found_palette)
                else:
                    self.load_palette_by_path(found_palette)

    def _load_metadata_palette(self, metadata_path: str):
        """Load palette from metadata file format"""
        try:
            with open(metadata_path) as f:
                metadata = json.load(f)

            # Store the full metadata for palette switching
            self.metadata = metadata

            # Enable palette switching
            if hasattr(self, "switch_palette_action"):
                self.switch_palette_action.setEnabled(True)

            # Extract Kirby palette (usually palette 8) from metadata
            palette_colors = metadata.get("palette_colors", {})
            kirby_palette = palette_colors.get("8")  # Try palette 8 first
            palette_index = 8

            if not kirby_palette:
                # Try to find any sprite palette (8-15)
                for i in range(8, 16):
                    if str(i) in palette_colors:
                        kirby_palette = palette_colors[str(i)]
                        palette_index = i
                        break

            if kirby_palette:
                # Convert to expected format
                colors = [tuple(color[:3]) for color in kirby_palette[:16]]
                self.external_palette_colors = colors
                self.current_palette_file = metadata_path
                self.current_palette_index = palette_index

                # Apply to palette widget
                self.palette_widget.set_palette(colors, f"Palette {palette_index}")

                # Update title
                base_title = (
                    self.windowTitle().split(" | ")[0]
                    if " | " in self.windowTitle()
                    else self.windowTitle()
                )
                self.setWindowTitle(f"{base_title} | Palette {palette_index}")

                self.update_preview()
                self.update_status_palette_info()
                debug_log(
                    "EDITOR",
                    f"Loaded palette {palette_index} from metadata: {metadata_path}",
                )

            else:
                QMessageBox.warning(
                    self, "No Palette Found", "No sprite palette found in metadata file"
                )

        except Exception as e:
            QMessageBox.warning(
                self, "Error", f"Failed to load metadata palette: {e!s}"
            )

    def show_palette_switcher(self):
        """Show palette switching dialog"""
        if not self.metadata:
            QMessageBox.information(
                self, "No Metadata", "No metadata file loaded. Cannot switch palettes."
            )
            return

        dialog = PaletteSwitcherDialog(self.metadata, self.current_palette_index, self)
        if dialog.exec():
            palette_idx, colors = dialog.get_selected_palette()
            if palette_idx is not None:
                self.apply_palette(palette_idx, colors)

    def apply_palette(self, palette_idx: int, colors: list):
        """Apply a different palette from metadata"""
        # Create progress dialog
        progress_dialog = ProgressDialog("Applying Palette", f"Switching to palette {palette_idx}...", self)
        progress_dialog.show()
        
        try:
            progress_dialog.update_progress(20, "Converting colors...")
            
            self.current_palette_index = palette_idx

            # Convert colors to tuples
            color_tuples = [tuple(c[:3]) for c in colors]

            # Update the external palette
            self.external_palette_colors = color_tuples

            progress_dialog.update_progress(50, "Updating palette widget...")

            # Update palette widget
            palette_name = f"Palette {palette_idx}"
            if palette_idx == 8:
                palette_name += " (Kirby)"
            elif palette_idx == 11:
                palette_name += " (Common)"

            self.palette_widget.set_palette(color_tuples, palette_name)

            progress_dialog.update_progress(80, "Refreshing display...")

            # Update canvas
            self.canvas.update()
            self.update_preview()

            # Update title
            base_title = (
                self.windowTitle().split(" | ")[0]
                if " | " in self.windowTitle()
                else self.windowTitle()
            )
            self.setWindowTitle(f"{base_title} | {palette_name}")

            # Update status
            self.update_status_palette_info()

            debug_log("EDITOR", f"Applied palette {palette_idx}")
            
            progress_dialog.update_progress(100, "Complete!")
            
        finally:
            progress_dialog.finish()

    def update_status_palette_info(self):
        """Update status bar with current palette info"""
        if self.metadata:
            status_text = f"Palette: {self.current_palette_index}"
            if self.current_palette_index == 8:
                status_text += " (Kirby)"
            elif self.current_palette_index == 11:
                status_text += " (Common)"
            self.status_bar.showMessage(status_text)

    def toggle_color_mode_shortcut(self):
        """Toggle color mode via keyboard shortcut"""
        # Toggle the checkbox
        current = self.greyscale_checkbox.isChecked()
        self.greyscale_checkbox.setChecked(not current)
        debug_log(
            "EDITOR",
            f"Color mode toggled via shortcut: {'Grayscale' if not current else 'Color'}",
        )

    def _validate_palette_file(self, data: dict) -> bool:
        """Validate that a JSON file is a valid palette file"""
        return validate_palette_file(data)

    def update_recent_files_menu(self):
        """Update the recent files menu"""
        self.recent_menu.clear()

        recent_files = self.settings.get_recent_files()
        if not recent_files:
            no_files_action = QAction("No recent files", self)
            no_files_action.setEnabled(False)
            self.recent_menu.addAction(no_files_action)
            return

        for file_path in recent_files:
            filename = os.path.basename(file_path)
            action = QAction(f"{filename}", self)
            action.setToolTip(file_path)
            action.triggered.connect(
                lambda checked, path=file_path: self.load_file_by_path(path)
            )
            self.recent_menu.addAction(action)

        self.recent_menu.addSeparator()
        clear_action = QAction("Clear Recent Files", self)
        clear_action.triggered.connect(self.clear_recent_files)
        self.recent_menu.addAction(clear_action)

    def clear_recent_files(self):
        """Clear the recent files list"""
        reply = QMessageBox.question(
            self,
            "Clear Recent Files?",
            "Are you sure you want to clear the recent files list?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.settings.settings["recent_files"] = []
            self.settings.save_settings()
            self.update_recent_files_menu()
            print("[EDITOR] Cleared recent files")

    def check_save(self) -> bool:
        """Check if file needs saving"""
        if not self.modified:
            return True

        reply = QMessageBox.question(
            self,
            "Save Changes?",
            "The image has been modified. Do you want to save changes?",
            QMessageBox.StandardButton.Save
            | QMessageBox.StandardButton.Discard
            | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Save,
        )

        if reply == QMessageBox.StandardButton.Save:
            self.save_file()
            return not self.modified
        return reply == QMessageBox.StandardButton.Discard

    def on_tool_changed(self, button):
        """Handle tool selection change"""
        tools = ["pencil", "fill", "picker"]
        self.canvas.tool = tools[self.tool_group.id(button)]
        print(f"[EDITOR] Tool changed to: {self.canvas.tool}")

    def on_color_selected(self, index: int):
        """Handle color selection from palette"""
        # Validate color index for 4bpp
        valid_index = max(0, min(15, index))
        old_color = self.canvas.current_color
        self.canvas.current_color = valid_index

        # Debug: Show color selection change
        if self.palette_widget and valid_index < len(self.palette_widget.colors):
            rgb_color = self.palette_widget.colors[valid_index]
            debug_log(
                "EDITOR",
                f"Color selected: {debug_color(old_color)} -> {debug_color(valid_index, rgb_color)}",
            )
        else:
            debug_log(
                "EDITOR",
                f"Color selected: {old_color} -> {valid_index} (no RGB info)",
                "WARNING",
            )

        self.status_bar.showMessage(f"Selected color {valid_index}")

    def toggle_grid(self, checked: bool):
        """Toggle grid visibility"""
        self.canvas.grid_visible = checked
        self.canvas.update()

    def toggle_greyscale_mode(self, checked: bool):
        """Toggle greyscale drawing mode"""
        self.canvas.greyscale_mode = checked
        self.canvas.update()
        debug_log("EDITOR", f"Greyscale mode: {'ON' if checked else 'OFF'}")
        # Don't change palette widget colors when toggling greyscale mode
        # The palette widget should always show the actual colors

    def toggle_color_preview(self, checked: bool):
        """Toggle color preview"""
        self.canvas.show_color_preview = checked
        self.update_preview()
        debug_log("EDITOR", f"Color preview: {'ON' if checked else 'OFF'}")

    def on_zoom_changed(self, value: int):
        """Handle zoom slider change"""
        self.canvas.set_zoom(value)
        self.zoom_label.setText(f"{value}x")

    def set_zoom_preset(self, zoom_value: int):
        """Set zoom to a preset value"""
        self.zoom_slider.setValue(zoom_value)
        # on_zoom_changed will be called automatically

    def zoom_to_fit(self):
        """Zoom to fit the image in the visible area"""
        if self.canvas.image_data is None:
            return

        # Get canvas scroll area size
        scroll_area = self.canvas.parent()
        if hasattr(scroll_area, "viewport"):
            viewport_size = scroll_area.viewport().size()
            height, width = self.canvas.image_data.shape

            # Calculate zoom to fit both dimensions with some padding
            zoom_x = max(1, (viewport_size.width() - 20) // width)
            zoom_y = max(1, (viewport_size.height() - 20) // height)
            zoom_fit = min(zoom_x, zoom_y, 64)  # Respect max zoom

            self.set_zoom_preset(zoom_fit)
            print(f"[EDITOR] Zoom to fit: {zoom_fit}x for {width}x{height} image")

    def zoom_in(self):
        """Zoom in by doubling current zoom level"""
        current_zoom = self.zoom_slider.value()
        new_zoom = min(current_zoom * 2, 64)
        self.set_zoom_preset(new_zoom)

    def zoom_out(self):
        """Zoom out by halving current zoom level"""
        current_zoom = self.zoom_slider.value()
        new_zoom = max(current_zoom // 2, 1)
        self.set_zoom_preset(new_zoom)

    def on_canvas_changed(self):
        """Handle canvas modification"""
        self.modified = True
        if self.current_file:
            self.setWindowTitle(
                f"Indexed Pixel Editor - {os.path.basename(self.current_file)}*"
            )
        else:
            self.setWindowTitle("Indexed Pixel Editor - New File*")
        self.update_preview()

    def update_preview(self):
        """Update the preview labels"""
        if self.canvas.image_data is None:
            self.preview_label.clear()
            self.color_preview_label.clear()
            return

        # Get main preview image (respects greyscale mode)
        main_img = self.canvas.get_pil_image()
        if main_img:
            # Convert to QPixmap for display
            img_rgb = main_img.convert("RGBA")
            data = img_rgb.tobytes("raw", "RGBA")
            qimage = QImage(
                data, main_img.width, main_img.height, QImage.Format.Format_RGBA8888
            )
            pixmap = QPixmap.fromImage(qimage)

            # Scale up for better visibility but maintain pixel art look
            scale = min(100 // main_img.width, 100 // main_img.height, 8)
            scaled_pixmap = pixmap.scaled(
                pixmap.width() * scale,
                pixmap.height() * scale,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.FastTransformation,
            )
            self.preview_label.setPixmap(scaled_pixmap)

        # Get colored preview (always shows colored version)
        if self.preview_checkbox.isChecked():
            color_img = self.get_colored_preview()
            if color_img:
                # Convert to QPixmap for display
                img_rgb = color_img.convert("RGBA")
                data = img_rgb.tobytes("raw", "RGBA")
                qimage = QImage(
                    data,
                    color_img.width,
                    color_img.height,
                    QImage.Format.Format_RGBA8888,
                )
                pixmap = QPixmap.fromImage(qimage)

                # Scale up for better visibility
                scale = min(100 // color_img.width, 100 // color_img.height, 8)
                scaled_pixmap = pixmap.scaled(
                    pixmap.width() * scale,
                    pixmap.height() * scale,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.FastTransformation,
                )
                self.color_preview_label.setPixmap(scaled_pixmap)
            else:
                self.color_preview_label.clear()
        else:
            self.color_preview_label.clear()

    def get_colored_preview(self):
        """Get the colored version of the image for preview"""
        if self.canvas.image_data is None:
            return None

        # Create indexed image
        img = Image.fromarray(self.canvas.image_data, mode="P")

        # Use external palette if available, otherwise use palette widget colors
        if self.external_palette_colors:
            # Use loaded external palette for accurate game colors
            palette = create_indexed_palette(self.external_palette_colors)
            debug_log(
                "EDITOR",
                f"Using external palette for color preview: {len(self.external_palette_colors)} colors",
                "DEBUG",
            )
        elif self.palette_widget:
            # Use palette widget colors as fallback
            palette = create_indexed_palette(self.palette_widget.colors)
        else:
            return None

        img.putpalette(palette)
        return img

    def keyPressEvent(self, event: QKeyEvent):
        """Handle keyboard shortcuts"""
        if (
            event.key() == Qt.Key.Key_C
            and event.modifiers() == Qt.KeyboardModifier.NoModifier
        ):
            # Toggle color mode with 'C' key
            self.toggle_color_mode_shortcut()
        elif (
            event.key() == Qt.Key.Key_P
            and event.modifiers() == Qt.KeyboardModifier.NoModifier
        ):
            # Show palette switcher with 'P' key (only if metadata is loaded)
            if self.metadata:
                self.show_palette_switcher()
            else:
                debug_log("EDITOR", "P key pressed but no metadata loaded", "DEBUG")
        else:
            super().keyPressEvent(event)

    def wheelEvent(self, event: QWheelEvent):
        """Handle wheel events for the main window - delegate to canvas"""
        debug_log(
            "EDITOR",
            f"Main window wheel event: delta={event.angleDelta().y()}",
            "DEBUG",
        )

        # Try to forward the wheel event to the canvas
        if hasattr(self, "canvas") and self.canvas:
            debug_log("EDITOR", "Forwarding wheel event to canvas", "DEBUG")
            # Forward to canvas
            self.canvas.wheelEvent(event)
        else:
            debug_log(
                "EDITOR", "No canvas found, using default wheel behavior", "WARNING"
            )
            super().wheelEvent(event)


def main():
    app = QApplication(sys.argv)
    editor = IndexedPixelEditor()

    # Load file from command line if provided
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
        palette_file = None

        # Check for palette file argument
        if len(sys.argv) > 3 and sys.argv[2] == "-p":
            palette_file = sys.argv[3]

        # Show the editor first
        editor.show()

        # Load the image
        if os.path.exists(file_path):
            success = editor.load_file_by_path(file_path)
            if success:
                # Load palette if specified
                if palette_file and os.path.exists(palette_file):
                    editor.load_palette_by_path(palette_file)
            else:
                debug_log("MAIN", f"Failed to load file: {file_path}", "ERROR")
        else:
            debug_log("MAIN", f"File not found: {file_path}", "ERROR")
    else:
        editor.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
