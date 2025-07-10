#!/usr/bin/env python3
"""
Main window for the sprite editor
Refactored to use MVC architecture with separated components
"""

import os

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import QMainWindow, QStatusBar, QTabWidget, QVBoxLayout, QWidget

from .tabs.extract_tab import ExtractTab
from .tabs.inject_tab import InjectTab
from .tabs.multi_palette_tab import MultiPaletteTab
from .tabs.viewer_tab import ViewerTab


class MainWindow(QMainWindow):
    """Main application window using MVC architecture"""

    # Signals
    recent_vram_selected = pyqtSignal(str)
    recent_cgram_selected = pyqtSignal(str)
    recent_oam_selected = pyqtSignal(str)
    reset_settings_requested = pyqtSignal()
    clear_recent_requested = pyqtSignal()
    closing = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
        self._create_menus()
        self._create_toolbar()
        self._apply_theme()

    def _setup_ui(self):
        """Initialize the user interface"""
        self.setWindowTitle("Kirby Super Star Sprite Editor")
        self.setGeometry(100, 100, 1200, 800)

        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Create main layout
        main_layout = QVBoxLayout(central_widget)

        # Create tab widget
        self.tab_widget = QTabWidget()

        # Create tabs
        self.extract_tab = ExtractTab()
        self.inject_tab = InjectTab()
        self.viewer_tab = ViewerTab()
        self.multi_palette_tab = MultiPaletteTab()

        # Add tabs
        self.tab_widget.addTab(self.extract_tab, "Extract")
        self.tab_widget.addTab(self.inject_tab, "Inject")
        self.tab_widget.addTab(self.viewer_tab, "View/Edit")
        self.tab_widget.addTab(self.multi_palette_tab, "Multi-Palette")

        main_layout.addWidget(self.tab_widget)

        # Create status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")

    def _create_menus(self):
        """Create menu bar"""
        menubar = self.menuBar()

        # File menu
        file_menu = menubar.addMenu("File")

        # Open actions
        self.action_open_vram = QAction("Open VRAM", self)
        self.action_open_vram.setShortcut("Ctrl+O")
        file_menu.addAction(self.action_open_vram)

        self.action_open_cgram = QAction("Open CGRAM", self)
        file_menu.addAction(self.action_open_cgram)

        file_menu.addSeparator()

        # Recent files submenu
        self.recent_menu = file_menu.addMenu("Recent Files")

        file_menu.addSeparator()

        # Exit action
        exit_action = QAction("Exit", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # Settings menu
        settings_menu = menubar.addMenu("Settings")

        # Reset settings action
        reset_action = QAction("Reset All Settings", self)
        reset_action.triggered.connect(self.reset_settings_requested.emit)
        settings_menu.addAction(reset_action)

        # Clear recent files
        clear_recent_action = QAction("Clear Recent Files", self)
        clear_recent_action.triggered.connect(self.clear_recent_requested.emit)
        settings_menu.addAction(clear_recent_action)

        settings_menu.addSeparator()

        # Preferences will be added by controller
        self.settings_menu = settings_menu

    def _create_toolbar(self):
        """Create the toolbar"""
        toolbar = self.addToolBar("Main")
        toolbar.setMovable(False)

        # Quick actions will be connected by controller
        self.action_quick_extract = QAction("Quick Extract", self)
        self.action_quick_extract.setShortcut("Ctrl+E")
        toolbar.addAction(self.action_quick_extract)

        self.action_quick_inject = QAction("Quick Inject", self)
        self.action_quick_inject.setShortcut("Ctrl+I")
        toolbar.addAction(self.action_quick_inject)

    def _apply_theme(self):
        """Apply dark theme"""
        self.setStyleSheet(
            """
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
        """
        )

    def update_recent_files_menu(self, recent_files):
        """Update recent files menu"""
        self.recent_menu.clear()

        # Add recent VRAM files
        if recent_files.get("vram"):
            self.recent_menu.addAction("VRAM Files:").setEnabled(False)
            for path in recent_files["vram"][:5]:
                if os.path.exists(path):
                    action = QAction(os.path.basename(path), self)
                    action.setToolTip(path)
                    action.triggered.connect(
                        lambda checked, p=path: self.recent_vram_selected.emit(p)
                    )
                    self.recent_menu.addAction(action)
            self.recent_menu.addSeparator()

        # Add recent CGRAM files
        if recent_files.get("cgram"):
            self.recent_menu.addAction("CGRAM Files:").setEnabled(False)
            for path in recent_files["cgram"][:5]:
                if os.path.exists(path):
                    action = QAction(os.path.basename(path), self)
                    action.setToolTip(path)
                    action.triggered.connect(
                        lambda checked, p=path: self.recent_cgram_selected.emit(p)
                    )
                    self.recent_menu.addAction(action)
            self.recent_menu.addSeparator()

        # Add recent OAM files
        if recent_files.get("oam"):
            self.recent_menu.addAction("OAM Files:").setEnabled(False)
            for path in recent_files["oam"][:5]:
                if os.path.exists(path):
                    action = QAction(os.path.basename(path), self)
                    action.setToolTip(path)
                    action.triggered.connect(
                        lambda checked, p=path: self.recent_oam_selected.emit(p)
                    )
                    self.recent_menu.addAction(action)

        if not any(recent_files.values()):
            self.recent_menu.addAction("No recent files").setEnabled(False)

    def show_viewer_tab(self):
        """Switch to viewer tab"""
        self.tab_widget.setCurrentIndex(2)

    def show_inject_tab(self):
        """Switch to inject tab"""
        self.tab_widget.setCurrentIndex(1)

    def show_status_message(self, message, timeout=0):
        """Show message in status bar"""
        self.status_bar.showMessage(message, timeout)

    def closeEvent(self, event):
        """Handle window close event"""
        self.closing.emit()
        event.accept()

    def get_tabs(self):
        """Get all tab widgets"""
        return {
            "extract": self.extract_tab,
            "inject": self.inject_tab,
            "viewer": self.viewer_tab,
            "multi_palette": self.multi_palette_tab,
        }
