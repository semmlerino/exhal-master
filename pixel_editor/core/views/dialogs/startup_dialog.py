#!/usr/bin/env python3
"""
Startup dialog for the pixel editor
Shows recent files and quick actions
"""

# Standard library imports
import os

# Third-party imports
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
)


class StartupDialog(QDialog):
    """Startup dialog showing recent files and quick actions"""

    def __init__(self, settings_manager, parent=None):
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
