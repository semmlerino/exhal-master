#!/usr/bin/env python3
"""
Unified Sprite Editor for Kirby Super Star
Consolidates all sprite editing functionality into one intuitive interface
"""

import json
import os
import sys
from datetime import datetime

from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QAction, QKeySequence
from PyQt6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMainWindow,
    QMessageBox,
    QProgressDialog,
    QPushButton,
    QRadioButton,
    QSpinBox,
    QSplitter,
    QStatusBar,
    QTabWidget,
    QTextEdit,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from sprite_edit_workflow import SpriteEditWorkflow
from sprite_sheet_editor import SpriteSheetEditor


class WorkflowWorker(QThread):
    """Worker thread for long-running operations"""
    progress = pyqtSignal(int, str)
    finished = pyqtSignal(bool, str)
    log = pyqtSignal(str)

    def __init__(self, operation, params):
        super().__init__()
        self.operation = operation
        self.params = params
        self.workflow = None
        self.sheet_editor = None

    def run(self):
        try:
            if self.operation == "extract_tiles":
                self._extract_tiles()
            elif self.operation == "extract_sheet":
                self._extract_sheet()
            elif self.operation == "validate":
                self._validate()
            elif self.operation == "reinsert":
                self._reinsert()
            else:
                self.finished.emit(False, f"Unknown operation: {self.operation}")
        except Exception as e:
            self.finished.emit(False, str(e))

    def _extract_tiles(self):
        """Extract sprites as individual tiles"""
        try:
            self.log.emit("Starting tile extraction...")
            self.progress.emit(10, "Loading palette mappings...")

            # Validate required files
            vram_file = self.params.get("vram_file")
            cgram_file = self.params.get("cgram_file")

            if not vram_file or not os.path.exists(vram_file):
                raise FileNotFoundError(f"VRAM file not found: {vram_file}")
            if not cgram_file or not os.path.exists(cgram_file):
                raise FileNotFoundError(f"CGRAM file not found: {cgram_file}")

            mappings_file = self.params.get("mappings_file")
            if mappings_file and not os.path.exists(mappings_file):
                self.log.emit(f"Warning: Palette mappings file not found: {mappings_file}")
                mappings_file = None

            self.workflow = SpriteEditWorkflow(mappings_file)

            self.progress.emit(30, "Reading memory dumps...")
            offset = self.params.get("offset", 0xC000)
            size = self.params.get("size", 0x1000)
            output_dir = self.params.get("output_dir", "extracted_sprites")
            tiles_per_row = self.params.get("tiles_per_row", 16)

            self.progress.emit(50, "Extracting tiles...")
            metadata = self.workflow.extract_for_editing(
                vram_file, cgram_file, offset, size,
                output_dir, tiles_per_row
            )

            self.progress.emit(90, "Creating reference sheet...")
            tile_count = len(metadata.get("tile_palette_mappings", {}))
            self.log.emit(f"Extracted {tile_count} tiles")

            self.progress.emit(100, "Complete!")
            self.finished.emit(True, f"Successfully extracted {tile_count} tiles to {output_dir}")
        except Exception as e:
            self.log.emit(f"Error during tile extraction: {e!s}")
            raise

    def _extract_sheet(self):
        """Extract sprites as a single sheet"""
        try:
            self.log.emit("Starting sheet extraction...")
            self.progress.emit(10, "Loading palette mappings...")

            # Validate required files
            vram_file = self.params.get("vram_file")
            cgram_file = self.params.get("cgram_file")
            output_png = self.params.get("output_png")

            if not vram_file or not os.path.exists(vram_file):
                raise FileNotFoundError(f"VRAM file not found: {vram_file}")
            if not cgram_file or not os.path.exists(cgram_file):
                raise FileNotFoundError(f"CGRAM file not found: {cgram_file}")
            if not output_png:
                raise ValueError("Output PNG file not specified")

            mappings_file = self.params.get("mappings_file")
            if mappings_file and not os.path.exists(mappings_file):
                self.log.emit(f"Warning: Palette mappings file not found: {mappings_file}")
                mappings_file = None

            self.sheet_editor = SpriteSheetEditor(mappings_file)

            self.progress.emit(30, "Reading memory dumps...")
            offset = self.params.get("offset", 0xC000)
            size = self.params.get("size", 0x4000)

            self.progress.emit(50, "Creating sprite sheet...")
            self.sheet_editor.extract_sheet_for_editing(
                vram_file, cgram_file, offset, size, output_png
            )

            if self.params.get("create_guide", True):
                self.progress.emit(80, "Creating editing guide...")
                self.sheet_editor.create_editing_guide(output_png)

            self.progress.emit(100, "Complete!")
            self.finished.emit(True, f"Successfully extracted sheet to {output_png}")
        except Exception as e:
            self.log.emit(f"Error during sheet extraction: {e!s}")
            raise

    def _validate(self):
        """Validate edited sprites"""
        try:
            self.log.emit("Starting validation...")
            self.progress.emit(20, "Loading metadata...")

            input_path = self.params.get("input_path")
            if not input_path:
                raise ValueError("No input path specified for validation")

            is_sheet = self.params.get("is_sheet", False)

            if is_sheet:
                if not os.path.exists(input_path) or not input_path.lower().endswith(".png"):
                    raise FileNotFoundError(f"PNG file not found: {input_path}")

                # Sheet validation
                self.sheet_editor = SpriteSheetEditor()
                self.progress.emit(50, "Validating sprite sheet...")
                validation = self.sheet_editor.validate_edited_sheet(input_path)
            else:
                if not os.path.isdir(input_path):
                    raise NotADirectoryError(f"Directory not found: {input_path}")

                # Tile validation
                self.workflow = SpriteEditWorkflow()
                self.progress.emit(50, "Validating individual tiles...")
                validation = self.workflow.validate_edited_sprites(input_path)

            self.progress.emit(80, "Generating report...")

            # Format results
            if validation.get("valid", True) and validation.get("valid_tiles"):
                msg = f"Validation passed: {len(validation.get('valid_tiles', []))} valid tiles"
            else:
                errors = validation.get("errors", [])
                invalid_tiles = validation.get("invalid_tiles", [])
                error_count = len(errors) + len(invalid_tiles)
                msg = f"Validation found issues: {error_count} errors"

            self.progress.emit(100, "Complete!")
            self.finished.emit(validation.get("valid", True), msg)
        except Exception as e:
            self.log.emit(f"Error during validation: {e!s}")
            raise

    def _reinsert(self):
        """Reinsert edited sprites"""
        try:
            self.log.emit("Starting reinsertion...")
            self.progress.emit(10, "Validating sprites first...")

            input_path = self.params.get("input_path")
            if not input_path:
                raise ValueError("No input path specified for reinsertion")

            backup = self.params.get("backup", True)
            is_sheet = self.params.get("is_sheet", False)

            if is_sheet:
                if not os.path.exists(input_path) or not input_path.lower().endswith(".png"):
                    raise FileNotFoundError(f"PNG file not found: {input_path}")

                # Sheet reinsertion
                self.sheet_editor = SpriteSheetEditor()
                self.progress.emit(40, "Converting sheet to VRAM format...")
                output_vram = self.sheet_editor.reinsert_sheet(
                    input_path,
                    self.params.get("output_vram")
                )
            else:
                if not os.path.isdir(input_path):
                    raise NotADirectoryError(f"Directory not found: {input_path}")

                # Tile reinsertion
                self.workflow = SpriteEditWorkflow()
                self.progress.emit(40, "Reinserting tiles...")
                output_vram = self.workflow.reinsert_sprites(
                    input_path,
                    self.params.get("output_vram"),
                    backup
                )

            if output_vram:
                self.progress.emit(100, "Complete!")
                self.finished.emit(True, f"Successfully reinserted to {output_vram}")
            else:
                self.finished.emit(False, "Reinsertion was cancelled or failed")
        except Exception as e:
            self.log.emit(f"Error during reinsertion: {e!s}")
            raise


class QuickActionDialog(QDialog):
    """Dialog for quick sprite editing actions"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Quick Action")
        self.setModal(True)
        self.resize(500, 400)

        layout = QVBoxLayout(self)

        # Action selection
        self.action_combo = QComboBox()
        self.action_combo.addItems([
            "Extract Kirby sprites only",
            "Extract enemy sprites only",
            "Extract full sprite sheet",
            "Create palette reference",
            "Generate visual summary",
            "Validate edited sprites",
            "Quick test extraction"
        ])
        self.action_combo.currentIndexChanged.connect(self._update_options)

        layout.addWidget(QLabel("Select quick action:"))
        layout.addWidget(self.action_combo)

        # Options area
        self.options_widget = QWidget()
        self.options_layout = QFormLayout(self.options_widget)
        layout.addWidget(self.options_widget)

        # File inputs
        self.vram_input = QLineEdit()
        self.vram_button = QPushButton("Browse...")
        self.vram_button.clicked.connect(lambda: self._browse_file(self.vram_input, "VRAM"))
        vram_layout = QHBoxLayout()
        vram_layout.addWidget(self.vram_input)
        vram_layout.addWidget(self.vram_button)
        self.options_layout.addRow("VRAM dump:", vram_layout)

        self.cgram_input = QLineEdit()
        self.cgram_button = QPushButton("Browse...")
        self.cgram_button.clicked.connect(lambda: self._browse_file(self.cgram_input, "CGRAM"))
        cgram_layout = QHBoxLayout()
        cgram_layout.addWidget(self.cgram_input)
        cgram_layout.addWidget(self.cgram_button)
        self.options_layout.addRow("CGRAM dump:", cgram_layout)

        # Palette mappings (optional)
        self.mappings_input = QLineEdit()
        self.mappings_button = QPushButton("Browse...")
        self.mappings_button.clicked.connect(lambda: self._browse_file(self.mappings_input, "Mappings"))
        mappings_layout = QHBoxLayout()
        mappings_layout.addWidget(self.mappings_input)
        mappings_layout.addWidget(self.mappings_button)
        self.options_layout.addRow("Palette mappings:", mappings_layout)

        # Buttons
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok |
                                      QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

        self._update_options()

    def _update_options(self):
        """Update visible options based on selected action"""
        self.action_combo.currentText()
        # Update UI based on action requirements
        # For now, show all for most actions

    def _browse_file(self, line_edit, file_type):
        """Browse for file"""
        if file_type == "VRAM":
            filter_str = "VRAM dumps (*.dmp *.bin);;All files (*.*)"
        elif file_type == "CGRAM":
            filter_str = "CGRAM dumps (*.dmp *.bin);;All files (*.*)"
        else:
            filter_str = "JSON files (*.json);;All files (*.*)"

        filename, _ = QFileDialog.getOpenFileName(
            self, f"Select {file_type} file", "", filter_str
        )
        if filename:
            line_edit.setText(filename)

    def get_params(self):
        """Get parameters for the selected action"""
        action = self.action_combo.currentText()
        params = {
            "action": action,
            "vram_file": self.vram_input.text(),
            "cgram_file": self.cgram_input.text(),
            "mappings_file": self.mappings_input.text() or None
        }

        # Set action-specific parameters
        if "Kirby" in action:
            params["offset"] = 0xC000
            params["size"] = 0x400  # First 32 tiles
        elif "enemy" in action:
            params["offset"] = 0xC800
            params["size"] = 0x800  # 64 tiles
        elif "full" in action:
            params["offset"] = 0xC000
            params["size"] = 0x4000  # Full sprite area

        return params


class UnifiedSpriteEditor(QMainWindow):
    """Main unified sprite editor application"""

    def __init__(self):
        super().__init__()
        self.current_project = None
        self.recent_files = []
        self.worker = None

        self.init_ui()
        self.load_settings()

    def init_ui(self):
        """Initialize the user interface"""
        self.setWindowTitle("Kirby Super Star Sprite Editor - Unified")
        self.setGeometry(100, 100, 1200, 800)

        # Create central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # Create menu bar
        self.create_menu_bar()

        # Create toolbar
        self.create_toolbar()

        # Create main content area with splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left panel - Quick actions and info
        left_panel = self.create_left_panel()
        splitter.addWidget(left_panel)

        # Right panel - Main work area with tabs
        self.tab_widget = QTabWidget()
        self.create_tabs()
        splitter.addWidget(self.tab_widget)

        splitter.setSizes([300, 900])
        main_layout.addWidget(splitter)

        # Status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")

        # Progress dialog (hidden by default)
        self.progress_dialog = None

    def create_menu_bar(self):
        """Create application menu bar"""
        menubar = self.menuBar()

        # File menu
        file_menu = menubar.addMenu("&File")

        new_action = QAction("&New Project", self)
        new_action.setShortcut(QKeySequence.StandardKey.New)
        new_action.triggered.connect(self.new_project)
        file_menu.addAction(new_action)

        open_action = QAction("&Open Project", self)
        open_action.setShortcut(QKeySequence.StandardKey.Open)
        open_action.triggered.connect(self.open_project)
        file_menu.addAction(open_action)

        save_action = QAction("&Save Project", self)
        save_action.setShortcut(QKeySequence.StandardKey.Save)
        save_action.triggered.connect(self.save_project)
        file_menu.addAction(save_action)

        file_menu.addSeparator()

        # Recent files submenu
        self.recent_menu = file_menu.addMenu("Recent Projects")

        file_menu.addSeparator()

        exit_action = QAction("E&xit", self)
        exit_action.setShortcut(QKeySequence.StandardKey.Quit)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # Edit menu
        edit_menu = menubar.addMenu("&Edit")

        undo_action = QAction("&Undo", self)
        undo_action.setShortcut(QKeySequence.StandardKey.Undo)
        undo_action.setEnabled(False)  # TODO: Implement undo
        edit_menu.addAction(undo_action)

        redo_action = QAction("&Redo", self)
        redo_action.setShortcut(QKeySequence.StandardKey.Redo)
        redo_action.setEnabled(False)  # TODO: Implement redo
        edit_menu.addAction(redo_action)

        edit_menu.addSeparator()

        prefs_action = QAction("&Preferences", self)
        prefs_action.triggered.connect(self.show_preferences)
        edit_menu.addAction(prefs_action)

        # Tools menu
        tools_menu = menubar.addMenu("&Tools")

        quick_action = QAction("&Quick Action...", self)
        quick_action.setShortcut("Ctrl+Q")
        quick_action.triggered.connect(self.show_quick_action)
        tools_menu.addAction(quick_action)

        tools_menu.addSeparator()

        batch_extract = QAction("&Batch Extract", self)
        batch_extract.triggered.connect(self.batch_extract)
        tools_menu.addAction(batch_extract)

        batch_validate = QAction("Batch &Validate", self)
        batch_validate.triggered.connect(self.batch_validate)
        tools_menu.addAction(batch_validate)

        tools_menu.addSeparator()

        palette_analyzer = QAction("&Palette Analyzer", self)
        palette_analyzer.triggered.connect(self.show_palette_analyzer)
        tools_menu.addAction(palette_analyzer)

        visual_summary = QAction("&Visual Summary", self)
        visual_summary.triggered.connect(self.create_visual_summary)
        tools_menu.addAction(visual_summary)

        # Help menu
        help_menu = menubar.addMenu("&Help")

        guide_action = QAction("&User Guide", self)
        guide_action.setShortcut("F1")
        guide_action.triggered.connect(self.show_user_guide)
        help_menu.addAction(guide_action)

        constraints_action = QAction("&SNES Constraints", self)
        constraints_action.triggered.connect(self.show_constraints)
        help_menu.addAction(constraints_action)

        help_menu.addSeparator()

        about_action = QAction("&About", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)

    def create_toolbar(self):
        """Create application toolbar"""
        toolbar = QToolBar("Main toolbar")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        # Extract action
        extract_action = QAction("Extract", self)
        extract_action.setToolTip("Extract sprites from memory dumps")
        toolbar.addAction(extract_action)
        extract_action.triggered.connect(lambda: self.tab_widget.setCurrentIndex(0))

        # Validate action
        validate_action = QAction("Validate", self)
        validate_action.setToolTip("Validate edited sprites")
        toolbar.addAction(validate_action)
        validate_action.triggered.connect(lambda: self.tab_widget.setCurrentIndex(2))

        # Reinsert action
        reinsert_action = QAction("Reinsert", self)
        reinsert_action.setToolTip("Reinsert sprites to VRAM")
        toolbar.addAction(reinsert_action)
        reinsert_action.triggered.connect(lambda: self.tab_widget.setCurrentIndex(3))

        toolbar.addSeparator()

        # Quick action
        quick_action = QAction("Quick Action", self)
        quick_action.setToolTip("Perform quick sprite operations")
        toolbar.addAction(quick_action)
        quick_action.triggered.connect(self.show_quick_action)

    def create_left_panel(self):
        """Create left panel with quick actions and project info"""
        panel = QWidget()
        layout = QVBoxLayout(panel)

        # Project info group
        project_group = QGroupBox("Project")
        project_layout = QVBoxLayout()

        self.project_label = QLabel("No project loaded")
        project_layout.addWidget(self.project_label)

        new_proj_btn = QPushButton("New Project")
        new_proj_btn.clicked.connect(self.new_project)
        project_layout.addWidget(new_proj_btn)

        open_proj_btn = QPushButton("Open Project")
        open_proj_btn.clicked.connect(self.open_project)
        project_layout.addWidget(open_proj_btn)

        project_group.setLayout(project_layout)
        layout.addWidget(project_group)

        # Quick actions group
        quick_group = QGroupBox("Quick Actions")
        quick_layout = QVBoxLayout()

        extract_kirby_btn = QPushButton("Extract Kirby Sprites")
        extract_kirby_btn.clicked.connect(self.quick_extract_kirby)
        quick_layout.addWidget(extract_kirby_btn)

        extract_enemies_btn = QPushButton("Extract Enemy Sprites")
        extract_enemies_btn.clicked.connect(self.quick_extract_enemies)
        quick_layout.addWidget(extract_enemies_btn)

        validate_btn = QPushButton("Validate Workspace")
        validate_btn.clicked.connect(self.quick_validate)
        quick_layout.addWidget(validate_btn)

        quick_group.setLayout(quick_layout)
        layout.addWidget(quick_group)

        # Recent files list
        recent_group = QGroupBox("Recent Files")
        recent_layout = QVBoxLayout()

        self.recent_list = QListWidget()
        self.recent_list.itemDoubleClicked.connect(self.open_recent_file)
        recent_layout.addWidget(self.recent_list)

        recent_group.setLayout(recent_layout)
        layout.addWidget(recent_group)

        layout.addStretch()

        return panel

    def create_tabs(self):
        """Create main work area tabs"""
        # Extract tab
        extract_tab = self.create_extract_tab()
        self.tab_widget.addTab(extract_tab, "Extract")

        # Edit workflow tab
        workflow_tab = self.create_workflow_tab()
        self.tab_widget.addTab(workflow_tab, "Edit Workflow")

        # Validate tab
        validate_tab = self.create_validate_tab()
        self.tab_widget.addTab(validate_tab, "Validate")

        # Reinsert tab
        reinsert_tab = self.create_reinsert_tab()
        self.tab_widget.addTab(reinsert_tab, "Reinsert")

        # Visual tools tab
        visual_tab = self.create_visual_tab()
        self.tab_widget.addTab(visual_tab, "Visual Tools")

        # Log tab
        log_tab = self.create_log_tab()
        self.tab_widget.addTab(log_tab, "Log")

    def create_extract_tab(self):
        """Create extraction tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # Extraction mode
        mode_group = QGroupBox("Extraction Mode")
        mode_layout = QHBoxLayout()

        # Create button group for mutual exclusivity
        self.extraction_mode_group = QButtonGroup()

        self.tile_mode_radio = QRadioButton("Individual Tiles")
        self.tile_mode_radio.setChecked(True)
        self.extraction_mode_group.addButton(self.tile_mode_radio)
        mode_layout.addWidget(self.tile_mode_radio)

        self.sheet_mode_radio = QRadioButton("Sprite Sheet")
        self.extraction_mode_group.addButton(self.sheet_mode_radio)
        mode_layout.addWidget(self.sheet_mode_radio)

        mode_group.setLayout(mode_layout)
        layout.addWidget(mode_group)

        # File inputs
        files_group = QGroupBox("Input Files")
        files_layout = QFormLayout()

        # VRAM input
        self.extract_vram_input = QLineEdit()
        self.extract_vram_btn = QPushButton("Browse...")
        self.extract_vram_btn.clicked.connect(
            lambda: self._browse_file(self.extract_vram_input, "VRAM dumps (*.dmp *.bin)")
        )
        vram_layout = QHBoxLayout()
        vram_layout.addWidget(self.extract_vram_input)
        vram_layout.addWidget(self.extract_vram_btn)
        files_layout.addRow("VRAM dump:", vram_layout)

        # CGRAM input
        self.extract_cgram_input = QLineEdit()
        self.extract_cgram_btn = QPushButton("Browse...")
        self.extract_cgram_btn.clicked.connect(
            lambda: self._browse_file(self.extract_cgram_input, "CGRAM dumps (*.dmp *.bin)")
        )
        cgram_layout = QHBoxLayout()
        cgram_layout.addWidget(self.extract_cgram_input)
        cgram_layout.addWidget(self.extract_cgram_btn)
        files_layout.addRow("CGRAM dump:", cgram_layout)

        # Palette mappings (optional)
        self.extract_mappings_input = QLineEdit()
        self.extract_mappings_btn = QPushButton("Browse...")
        self.extract_mappings_btn.clicked.connect(
            lambda: self._browse_file(self.extract_mappings_input, "JSON files (*.json)")
        )
        mappings_layout = QHBoxLayout()
        mappings_layout.addWidget(self.extract_mappings_input)
        mappings_layout.addWidget(self.extract_mappings_btn)
        files_layout.addRow("Palette mappings (optional):", mappings_layout)

        files_group.setLayout(files_layout)
        layout.addWidget(files_group)

        # Extraction options
        options_group = QGroupBox("Options")
        options_layout = QFormLayout()

        # Offset
        self.extract_offset_input = QSpinBox()
        self.extract_offset_input.setRange(0, 0xFFFF)
        self.extract_offset_input.setValue(0xC000)
        self.extract_offset_input.setDisplayIntegerBase(16)
        self.extract_offset_input.setPrefix("0x")
        options_layout.addRow("Offset:", self.extract_offset_input)

        # Size
        self.extract_size_input = QSpinBox()
        self.extract_size_input.setRange(0x20, 0x10000)
        self.extract_size_input.setValue(0x1000)
        self.extract_size_input.setSingleStep(0x100)
        self.extract_size_input.setDisplayIntegerBase(16)
        self.extract_size_input.setPrefix("0x")
        options_layout.addRow("Size:", self.extract_size_input)

        # Tiles per row
        self.extract_tiles_row = QSpinBox()
        self.extract_tiles_row.setRange(1, 32)
        self.extract_tiles_row.setValue(16)
        options_layout.addRow("Tiles per row:", self.extract_tiles_row)

        # Create guide checkbox
        self.extract_guide_check = QCheckBox("Create editing guide")
        self.extract_guide_check.setChecked(True)
        options_layout.addRow("", self.extract_guide_check)

        options_group.setLayout(options_layout)
        layout.addWidget(options_group)

        # Extract button
        extract_btn = QPushButton("Extract Sprites")
        extract_btn.clicked.connect(self.perform_extraction)
        layout.addWidget(extract_btn)

        layout.addStretch()

        return tab

    def create_workflow_tab(self):
        """Create edit workflow tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # Workflow description
        desc_label = QLabel(
            "Complete sprite editing workflow:\n"
            "1. Extract sprites (individual tiles or sheet)\n"
            "2. Edit in your favorite image editor\n"
            "3. Validate against SNES constraints\n"
            "4. Reinsert into VRAM"
        )
        desc_label.setWordWrap(True)
        layout.addWidget(desc_label)

        # Current workspace
        workspace_group = QGroupBox("Current Workspace")
        workspace_layout = QFormLayout()

        self.workspace_path_label = QLabel("No workspace loaded")
        workspace_layout.addRow("Path:", self.workspace_path_label)

        self.workspace_tiles_label = QLabel("N/A")
        workspace_layout.addRow("Tiles:", self.workspace_tiles_label)

        self.workspace_status_label = QLabel("N/A")
        workspace_layout.addRow("Status:", self.workspace_status_label)

        workspace_group.setLayout(workspace_layout)
        layout.addWidget(workspace_group)

        # Workflow actions
        actions_group = QGroupBox("Workflow Actions")
        actions_layout = QVBoxLayout()

        load_workspace_btn = QPushButton("Load Workspace")
        load_workspace_btn.clicked.connect(self.load_workspace)
        actions_layout.addWidget(load_workspace_btn)

        open_folder_btn = QPushButton("Open in File Explorer")
        open_folder_btn.clicked.connect(self.open_workspace_folder)
        actions_layout.addWidget(open_folder_btn)

        refresh_btn = QPushButton("Refresh Status")
        refresh_btn.clicked.connect(self.refresh_workspace_status)
        actions_layout.addWidget(refresh_btn)

        actions_group.setLayout(actions_layout)
        layout.addWidget(actions_group)

        # Tips
        tips_group = QGroupBox("Editing Tips")
        tips_layout = QVBoxLayout()

        tips_text = QTextEdit()
        tips_text.setReadOnly(True)
        tips_text.setPlainText(
            "• Work in indexed color mode\n"
            "• Use only colors from the assigned palette\n"
            "• Maximum 15 colors + transparent per tile\n"
            "• Keep 8×8 pixel tile boundaries\n"
            "• Save as indexed PNG to preserve palette\n"
            "• Color index 0 is always transparent"
        )
        tips_text.setMaximumHeight(150)
        tips_layout.addWidget(tips_text)

        tips_group.setLayout(tips_layout)
        layout.addWidget(tips_group)

        layout.addStretch()

        return tab

    def create_validate_tab(self):
        """Create validation tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # Validation input
        input_group = QGroupBox("Select Files to Validate")
        input_layout = QVBoxLayout()

        # Input type selection
        self.validate_type_combo = QComboBox()
        self.validate_type_combo.addItems(["Individual Tiles (Folder)", "Sprite Sheet (PNG)"])
        input_layout.addWidget(self.validate_type_combo)

        # Path input
        path_layout = QHBoxLayout()
        self.validate_input = QLineEdit()
        self.validate_browse_btn = QPushButton("Browse...")
        self.validate_browse_btn.clicked.connect(self.browse_validate_input)
        path_layout.addWidget(self.validate_input)
        path_layout.addWidget(self.validate_browse_btn)
        input_layout.addLayout(path_layout)

        # Validate button
        validate_btn = QPushButton("Validate")
        validate_btn.clicked.connect(self.perform_validation)
        input_layout.addWidget(validate_btn)

        input_group.setLayout(input_layout)
        layout.addWidget(input_group)

        # Results area
        results_group = QGroupBox("Validation Results")
        results_layout = QVBoxLayout()

        self.validate_results = QTextEdit()
        self.validate_results.setReadOnly(True)
        results_layout.addWidget(self.validate_results)

        results_group.setLayout(results_layout)
        layout.addWidget(results_group)

        return tab

    def create_reinsert_tab(self):
        """Create reinsertion tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # Reinsertion input
        input_group = QGroupBox("Select Edited Sprites")
        input_layout = QVBoxLayout()

        # Input type
        self.reinsert_type_combo = QComboBox()
        self.reinsert_type_combo.addItems(["Individual Tiles (Folder)", "Sprite Sheet (PNG)"])
        input_layout.addWidget(self.reinsert_type_combo)

        # Path input
        path_layout = QHBoxLayout()
        self.reinsert_input = QLineEdit()
        self.reinsert_browse_btn = QPushButton("Browse...")
        self.reinsert_browse_btn.clicked.connect(self.browse_reinsert_input)
        path_layout.addWidget(self.reinsert_input)
        path_layout.addWidget(self.reinsert_browse_btn)
        input_layout.addLayout(path_layout)

        # Output VRAM (optional)
        output_layout = QHBoxLayout()
        output_layout.addWidget(QLabel("Output VRAM (optional):"))
        self.reinsert_output = QLineEdit()
        self.reinsert_output_btn = QPushButton("Browse...")
        self.reinsert_output_btn.clicked.connect(
            lambda: self._browse_save_file(self.reinsert_output, "VRAM dumps (*.dmp *.bin)")
        )
        output_layout.addWidget(self.reinsert_output)
        output_layout.addWidget(self.reinsert_output_btn)
        input_layout.addLayout(output_layout)

        # Options
        self.reinsert_backup_check = QCheckBox("Create backup")
        self.reinsert_backup_check.setChecked(True)
        input_layout.addWidget(self.reinsert_backup_check)

        self.reinsert_preview_check = QCheckBox("Generate preview")
        self.reinsert_preview_check.setChecked(True)
        input_layout.addWidget(self.reinsert_preview_check)

        # Reinsert button
        reinsert_btn = QPushButton("Reinsert Sprites")
        reinsert_btn.clicked.connect(self.perform_reinsertion)
        input_layout.addWidget(reinsert_btn)

        input_group.setLayout(input_layout)
        layout.addWidget(input_group)

        # Status area
        status_group = QGroupBox("Reinsertion Status")
        status_layout = QVBoxLayout()

        self.reinsert_status = QTextEdit()
        self.reinsert_status.setReadOnly(True)
        status_layout.addWidget(self.reinsert_status)

        status_group.setLayout(status_layout)
        layout.addWidget(status_group)

        return tab

    def create_visual_tab(self):
        """Create visual tools tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # Visual tools description
        desc = QLabel(
            "Visual tools for sprite analysis and documentation"
        )
        layout.addWidget(desc)

        # Tool buttons
        tools_layout = QVBoxLayout()

        # Palette reference
        palette_ref_btn = QPushButton("Create Palette Reference")
        palette_ref_btn.clicked.connect(self.create_palette_reference)
        tools_layout.addWidget(palette_ref_btn)

        # Coverage map
        coverage_btn = QPushButton("Generate Coverage Map")
        coverage_btn.clicked.connect(self.create_coverage_map)
        tools_layout.addWidget(coverage_btn)

        # Visual summary
        summary_btn = QPushButton("Create Visual Summary")
        summary_btn.clicked.connect(self.create_visual_summary)
        tools_layout.addWidget(summary_btn)

        # Comparison tool
        compare_btn = QPushButton("Compare Before/After")
        compare_btn.clicked.connect(self.create_comparison)
        tools_layout.addWidget(compare_btn)

        layout.addLayout(tools_layout)

        # Preview area
        preview_group = QGroupBox("Preview")
        preview_layout = QVBoxLayout()

        self.preview_label = QLabel("No preview available")
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_label.setMinimumHeight(300)
        self.preview_label.setStyleSheet("border: 1px solid gray;")
        preview_layout.addWidget(self.preview_label)

        preview_group.setLayout(preview_layout)
        layout.addWidget(preview_group)

        return tab

    def create_log_tab(self):
        """Create log tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # Log controls
        controls_layout = QHBoxLayout()

        clear_btn = QPushButton("Clear Log")
        clear_btn.clicked.connect(self.clear_log)
        controls_layout.addWidget(clear_btn)

        save_log_btn = QPushButton("Save Log")
        save_log_btn.clicked.connect(self.save_log)
        controls_layout.addWidget(save_log_btn)

        controls_layout.addStretch()

        self.auto_scroll_check = QCheckBox("Auto-scroll")
        self.auto_scroll_check.setChecked(True)
        controls_layout.addWidget(self.auto_scroll_check)

        layout.addLayout(controls_layout)

        # Log text area
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFont(self.font())  # Use monospace font
        layout.addWidget(self.log_text)

        return tab

    # Helper methods
    def _browse_file(self, line_edit, filter_str):
        """Browse for input file"""
        filename, _ = QFileDialog.getOpenFileName(
            self, "Select file", "", filter_str + ";;All files (*.*)"
        )
        if filename:
            line_edit.setText(filename)

    def _browse_save_file(self, line_edit, filter_str):
        """Browse for output file"""
        filename, _ = QFileDialog.getSaveFileName(
            self, "Save file", "", filter_str + ";;All files (*.*)"
        )
        if filename:
            line_edit.setText(filename)

    def log(self, message):
        """Add message to log"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.append(f"[{timestamp}] {message}")

        if self.auto_scroll_check.isChecked():
            scrollbar = self.log_text.verticalScrollBar()
            scrollbar.setValue(scrollbar.maximum())

    def show_progress(self, title, maximum=100):
        """Show progress dialog"""
        self.progress_dialog = QProgressDialog(title, "Cancel", 0, maximum, self)
        self.progress_dialog.setWindowModality(Qt.WindowModality.WindowModal)
        self.progress_dialog.setMinimumDuration(0)
        self.progress_dialog.show()

    def update_progress(self, value, message):
        """Update progress dialog"""
        if self.progress_dialog:
            self.progress_dialog.setValue(value)
            self.progress_dialog.setLabelText(message)
            QApplication.processEvents()

    def hide_progress(self):
        """Hide progress dialog"""
        if self.progress_dialog:
            self.progress_dialog.close()
            self.progress_dialog = None

    # Action handlers
    def perform_extraction(self):
        """Perform sprite extraction"""
        # Validate inputs
        if not self.extract_vram_input.text() or not self.extract_cgram_input.text():
            QMessageBox.warning(self, "Input Error", "Please select VRAM and CGRAM files")
            return

        # Determine output location
        if self.tile_mode_radio.isChecked():
            output_dir = QFileDialog.getExistingDirectory(
                self, "Select output directory for tiles"
            )
            if not output_dir:
                return

            params = {
                "vram_file": self.extract_vram_input.text(),
                "cgram_file": self.extract_cgram_input.text(),
                "mappings_file": self.extract_mappings_input.text() or None,
                "offset": self.extract_offset_input.value(),
                "size": self.extract_size_input.value(),
                "output_dir": output_dir,
                "tiles_per_row": self.extract_tiles_row.value()
            }
            operation = "extract_tiles"
        else:
            output_file, _ = QFileDialog.getSaveFileName(
                self, "Save sprite sheet", "", "PNG files (*.png)"
            )
            if not output_file:
                return

            params = {
                "vram_file": self.extract_vram_input.text(),
                "cgram_file": self.extract_cgram_input.text(),
                "mappings_file": self.extract_mappings_input.text() or None,
                "offset": self.extract_offset_input.value(),
                "size": self.extract_size_input.value(),
                "output_png": output_file,
                "create_guide": self.extract_guide_check.isChecked()
            }
            operation = "extract_sheet"

        # Start extraction in worker thread
        self.log(f"Starting {operation}...")
        self.show_progress("Extracting sprites...")

        self.worker = WorkflowWorker(operation, params)
        self.worker.progress.connect(self.update_progress)
        self.worker.finished.connect(self.extraction_finished)
        self.worker.log.connect(self.log)
        self.worker.start()

    def extraction_finished(self, success, message):
        """Handle extraction completion"""
        self.hide_progress()

        if success:
            self.log(f"Extraction successful: {message}")
            QMessageBox.information(self, "Success", message)
        else:
            self.log(f"Extraction failed: {message}")
            QMessageBox.critical(self, "Error", f"Extraction failed:\n{message}")

    def perform_validation(self):
        """Perform sprite validation"""
        if not self.validate_input.text():
            QMessageBox.warning(self, "Input Error", "Please select files to validate")
            return

        is_sheet = self.validate_type_combo.currentIndex() == 1

        params = {
            "input_path": self.validate_input.text(),
            "is_sheet": is_sheet
        }

        self.log("Starting validation...")
        self.show_progress("Validating sprites...")

        self.worker = WorkflowWorker("validate", params)
        self.worker.progress.connect(self.update_progress)
        self.worker.finished.connect(self.validation_finished)
        self.worker.log.connect(self.log)
        self.worker.start()

    def validation_finished(self, success, message):
        """Handle validation completion"""
        self.hide_progress()

        self.validate_results.clear()
        self.validate_results.append(message)

        if success:
            self.validate_results.append("\n✓ Validation passed!")
            self.log("Validation passed")
        else:
            self.validate_results.append("\n✗ Validation failed!")
            self.log("Validation failed")

    def perform_reinsertion(self):
        """Perform sprite reinsertion"""
        if not self.reinsert_input.text():
            QMessageBox.warning(self, "Input Error", "Please select sprites to reinsert")
            return

        is_sheet = self.reinsert_type_combo.currentIndex() == 1

        params = {
            "input_path": self.reinsert_input.text(),
            "is_sheet": is_sheet,
            "output_vram": self.reinsert_output.text() or None,
            "backup": self.reinsert_backup_check.isChecked()
        }

        self.log("Starting reinsertion...")
        self.show_progress("Reinserting sprites...")

        self.worker = WorkflowWorker("reinsert", params)
        self.worker.progress.connect(self.update_progress)
        self.worker.finished.connect(self.reinsertion_finished)
        self.worker.log.connect(self.log)
        self.worker.start()

    def reinsertion_finished(self, success, message):
        """Handle reinsertion completion"""
        self.hide_progress()

        self.reinsert_status.clear()
        self.reinsert_status.append(message)

        if success:
            self.log(f"Reinsertion successful: {message}")
            QMessageBox.information(self, "Success", message)
        else:
            self.log(f"Reinsertion failed: {message}")
            QMessageBox.critical(self, "Error", f"Reinsertion failed:\n{message}")

    # Quick actions
    def show_quick_action(self):
        """Show quick action dialog"""
        dialog = QuickActionDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            params = dialog.get_params()
            self.execute_quick_action(params)

    def execute_quick_action(self, params):
        """Execute a quick action"""
        action = params["action"]
        self.log(f"Executing quick action: {action}")

        # TODO: Implement quick actions
        QMessageBox.information(self, "Quick Action", f"Executing: {action}")

    def quick_extract_kirby(self):
        """Quick extract Kirby sprites"""
        # Check for common dump files
        vram_files = ["Cave.SnesVideoRam.dmp", "VRAM.dmp", "sync3_vram.dmp"]
        cgram_files = ["Cave.SnesCgRam.dmp", "CGRAM.dmp", "sync3_cgram.dmp"]

        vram_file = None
        cgram_file = None

        for vf in vram_files:
            if os.path.exists(vf):
                vram_file = vf
                break

        for cf in cgram_files:
            if os.path.exists(cf):
                cgram_file = cf
                break

        if not vram_file or not cgram_file:
            QMessageBox.warning(self, "Files Not Found",
                "Could not find VRAM and CGRAM dumps in current directory")
            return

        # Set up extraction for Kirby sprites
        self.extract_vram_input.setText(vram_file)
        self.extract_cgram_input.setText(cgram_file)
        self.extract_offset_input.setValue(0xC000)
        self.extract_size_input.setValue(0x400)  # First 32 tiles

        # Switch to extract tab
        self.tab_widget.setCurrentIndex(0)

        self.log("Ready to extract Kirby sprites - click Extract Sprites button")

    def quick_extract_enemies(self):
        """Quick extract enemy sprites"""
        # Similar to Kirby but different offset/size
        # Check for files first
        vram_files = ["Cave.SnesVideoRam.dmp", "VRAM.dmp", "sync3_vram.dmp"]
        cgram_files = ["Cave.SnesCgRam.dmp", "CGRAM.dmp", "sync3_cgram.dmp"]

        vram_file = None
        cgram_file = None

        for vf in vram_files:
            if os.path.exists(vf):
                vram_file = vf
                break

        for cf in cgram_files:
            if os.path.exists(cf):
                cgram_file = cf
                break

        if not vram_file or not cgram_file:
            QMessageBox.warning(self, "Files Not Found",
                "Could not find VRAM and CGRAM dumps in current directory")
            return

        # Set up extraction for enemy sprites
        self.extract_vram_input.setText(vram_file)
        self.extract_cgram_input.setText(cgram_file)
        self.extract_offset_input.setValue(0xC800)  # Enemy area
        self.extract_size_input.setValue(0x800)     # 64 tiles

        # Switch to extract tab
        self.tab_widget.setCurrentIndex(0)

        self.log("Ready to extract enemy sprites - click Extract Sprites button")

    def quick_validate(self):
        """Quick validate workspace"""
        # Look for common workspace directories
        workspace_dirs = ["extracted_sprites", "test_workspace", "my_sprites"]

        workspace = None
        for wd in workspace_dirs:
            if os.path.isdir(wd):
                workspace = wd
                break

        if workspace:
            self.validate_input.setText(workspace)
            self.validate_type_combo.setCurrentIndex(0)  # Folder mode
            self.tab_widget.setCurrentIndex(2)  # Switch to validate tab
            self.log(f"Ready to validate {workspace} - click Validate button")
        else:
            QMessageBox.information(self, "No Workspace",
                "No extracted sprites found. Extract sprites first.")

    # File operations
    def browse_validate_input(self):
        """Browse for validation input"""
        if self.validate_type_combo.currentIndex() == 0:
            # Folder mode
            folder = QFileDialog.getExistingDirectory(
                self, "Select folder with edited tiles"
            )
            if folder:
                self.validate_input.setText(folder)
        else:
            # File mode
            filename, _ = QFileDialog.getOpenFileName(
                self, "Select sprite sheet", "", "PNG files (*.png)"
            )
            if filename:
                self.validate_input.setText(filename)

    def browse_reinsert_input(self):
        """Browse for reinsertion input"""
        if self.reinsert_type_combo.currentIndex() == 0:
            # Folder mode
            folder = QFileDialog.getExistingDirectory(
                self, "Select folder with edited tiles"
            )
            if folder:
                self.reinsert_input.setText(folder)
        else:
            # File mode
            filename, _ = QFileDialog.getOpenFileName(
                self, "Select edited sprite sheet", "", "PNG files (*.png)"
            )
            if filename:
                self.reinsert_input.setText(filename)

    # Project management
    def new_project(self):
        """Create new project"""
        # TODO: Implement project creation
        self.log("Creating new project...")
        self.current_project = {
            "name": "New Project",
            "created": datetime.now().isoformat(),
            "files": {}
        }
        self.project_label.setText("New Project")

    def open_project(self):
        """Open existing project"""
        filename, _ = QFileDialog.getOpenFileName(
            self, "Open project", "", "Project files (*.ksproj);;JSON files (*.json)"
        )
        if filename:
            self.load_project(filename)

    def save_project(self):
        """Save current project"""
        if not self.current_project:
            QMessageBox.information(self, "No Project", "No project to save")
            return

        filename, _ = QFileDialog.getSaveFileName(
            self, "Save project", "", "Project files (*.ksproj);;JSON files (*.json)"
        )
        if filename:
            with open(filename, "w") as f:
                json.dump(self.current_project, f, indent=2)
            self.log(f"Project saved: {filename}")

    def load_project(self, filename):
        """Load project from file"""
        try:
            with open(filename) as f:
                self.current_project = json.load(f)

            self.project_label.setText(self.current_project.get("name", "Unnamed"))
            self.log(f"Project loaded: {filename}")

            # Update recent files
            if filename in self.recent_files:
                self.recent_files.remove(filename)  # Remove from current position
            self.recent_files.insert(0, filename)  # Add to top
            self.recent_files = self.recent_files[:10]  # Keep last 10
            self.update_recent_menu()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load project:\n{e}")

    def open_recent_file(self, item):
        """Open recent file from list"""
        filename = item.text()
        if os.path.exists(filename):
            self.load_project(filename)

    def update_recent_menu(self):
        """Update recent files menu"""
        self.recent_menu.clear()

        # Check if recent_list exists (it may not during initial UI setup)
        if hasattr(self, "recent_list"):
            self.recent_list.clear()

            for filename in self.recent_files:
                # Menu action
                action = QAction(os.path.basename(filename), self)
                action.setData(filename)
                action.triggered.connect(
                    lambda checked, f=filename: self.load_project(f)
                )
                self.recent_menu.addAction(action)

                # List item
                self.recent_list.addItem(filename)
        else:
            # Just update menu if recent_list doesn't exist yet
            for filename in self.recent_files:
                action = QAction(os.path.basename(filename), self)
                action.setData(filename)
                action.triggered.connect(
                    lambda checked, f=filename: self.load_project(f)
                )
                self.recent_menu.addAction(action)

    # Visual tools
    def create_palette_reference(self):
        """Create palette reference image"""
        self.log("Creating palette reference...")
        # TODO: Implement palette reference generation
        QMessageBox.information(self, "Palette Reference",
            "Palette reference generation not yet implemented")

    def create_coverage_map(self):
        """Create coverage map"""
        self.log("Creating coverage map...")
        # TODO: Implement coverage map
        QMessageBox.information(self, "Coverage Map",
            "Coverage map generation not yet implemented")

    def create_visual_summary(self):
        """Create visual summary"""
        self.log("Creating visual summary...")
        # TODO: Implement visual summary
        QMessageBox.information(self, "Visual Summary",
            "Visual summary generation not yet implemented")

    def create_comparison(self):
        """Create before/after comparison"""
        self.log("Creating comparison...")
        # TODO: Implement comparison
        QMessageBox.information(self, "Comparison",
            "Comparison generation not yet implemented")

    # Other menu actions
    def show_preferences(self):
        """Show preferences dialog"""
        QMessageBox.information(self, "Preferences",
            "Preferences dialog not yet implemented")

    def batch_extract(self):
        """Batch extraction"""
        QMessageBox.information(self, "Batch Extract",
            "Batch extraction not yet implemented")

    def batch_validate(self):
        """Batch validation"""
        QMessageBox.information(self, "Batch Validate",
            "Batch validation not yet implemented")

    def show_palette_analyzer(self):
        """Show palette analyzer"""
        QMessageBox.information(self, "Palette Analyzer",
            "Palette analyzer not yet implemented")

    def show_user_guide(self):
        """Show user guide"""
        guide_text = """
Kirby Super Star Sprite Editor - User Guide

1. EXTRACTION
   - Select VRAM and CGRAM dump files
   - Choose between individual tiles or sprite sheet
   - Set offset (usually 0xC000 for sprites)
   - Set size based on what you want to extract

2. EDITING
   - Edit extracted sprites in your image editor
   - Maintain indexed color mode
   - Use only existing palette colors
   - Keep 8×8 tile boundaries

3. VALIDATION
   - Select edited sprites (folder or PNG)
   - Run validation to check constraints
   - Fix any reported issues

4. REINSERTION
   - Select validated sprites
   - Choose output location (optional)
   - Reinsert creates modified VRAM dump

TIPS:
- Use Quick Actions for common tasks
- Check the Log tab for detailed information
- Create backups before reinsertion
"""
        QMessageBox.information(self, "User Guide", guide_text)

    def show_constraints(self):
        """Show SNES constraints"""
        constraints_text = """
SNES Sprite Constraints:

TILE CONSTRAINTS:
• Size: 8×8 pixels (fixed)
• Colors: Maximum 15 + transparent
• Color 0: Always transparent
• Palette: One palette per tile

PALETTE CONSTRAINTS:
• 8 sprite palettes (8-15 in CGRAM)
• 16 colors per palette
• BGR555 format (5 bits per channel)
• Shared across all sprites

MEMORY CONSTRAINTS:
• VRAM sprite area: Usually 0xC000-0xFFFF
• 4bpp format (4 bits per pixel)
• 32 bytes per tile
• Limited sprite slots (128 max on screen)

EDITING RULES:
• Don't add new colors
• Don't change tile dimensions
• Maintain palette assignments
• Preserve transparency
"""
        QMessageBox.information(self, "SNES Constraints", constraints_text)

    def show_about(self):
        """Show about dialog"""
        about_text = """
Kirby Super Star Sprite Editor
Version 1.0

A unified tool for extracting, editing, and reinserting
sprites for Kirby Super Star (SNES).

Features:
• Palette-aware sprite extraction
• SNES constraint validation
• Safe reinsertion with backups
• Visual analysis tools

Created with PyQt6 and PIL/Pillow
"""
        QMessageBox.about(self, "About", about_text)

    # Workspace management
    def load_workspace(self):
        """Load a workspace directory"""
        folder = QFileDialog.getExistingDirectory(
            self, "Select workspace directory"
        )
        if folder:
            self.current_workspace = folder
            self.workspace_path_label.setText(folder)
            self.refresh_workspace_status()

    def open_workspace_folder(self):
        """Open workspace in file explorer"""
        if hasattr(self, "current_workspace") and self.current_workspace:
            os.startfile(self.current_workspace)  # Windows
            # For cross-platform:
            # import subprocess
            # subprocess.run(['xdg-open', self.current_workspace])  # Linux
            # subprocess.run(['open', self.current_workspace])  # macOS

    def refresh_workspace_status(self):
        """Refresh workspace status"""
        if not hasattr(self, "current_workspace") or not self.current_workspace:
            return

        # Check for metadata
        metadata_file = os.path.join(self.current_workspace, "extraction_metadata.json")
        if os.path.exists(metadata_file):
            with open(metadata_file) as f:
                metadata = json.load(f)

            tile_count = len(metadata.get("tile_palette_mappings", {}))
            self.workspace_tiles_label.setText(str(tile_count))
            self.workspace_status_label.setText("Ready for editing")
        else:
            self.workspace_tiles_label.setText("N/A")
            self.workspace_status_label.setText("No metadata found")

    # Log management
    def clear_log(self):
        """Clear log text"""
        self.log_text.clear()

    def save_log(self):
        """Save log to file"""
        filename, _ = QFileDialog.getSaveFileName(
            self, "Save log", "", "Text files (*.txt);;All files (*.*)"
        )
        if filename:
            with open(filename, "w") as f:
                f.write(self.log_text.toPlainText())
            self.log(f"Log saved to: {filename}")

    # Settings
    def load_settings(self):
        """Load application settings"""
        # TODO: Implement full settings loading

        # Update recent files menu now that UI is fully initialized
        self.update_recent_menu()

    def save_settings(self):
        """Save application settings"""
        # TODO: Implement settings saving

    def closeEvent(self, event):
        """Handle application close"""
        self.save_settings()
        event.accept()


def main():
    """Main entry point"""
    app = QApplication(sys.argv)
    app.setApplicationName("Kirby Super Star Sprite Editor")

    # Set application style
    app.setStyle("Fusion")

    # Create and show main window
    window = UnifiedSpriteEditor()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
