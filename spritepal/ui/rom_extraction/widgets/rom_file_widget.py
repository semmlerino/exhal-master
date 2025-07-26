"""ROM file selector widget for ROM extraction"""

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QLineEdit, QPushButton, QVBoxLayout

from .base_widget import BaseExtractionWidget

# UI Spacing Constants (matching main panel)
SPACING_SMALL = 6
SPACING_MEDIUM = 10
SPACING_LARGE = 16
SPACING_XLARGE = 20
BUTTON_MIN_HEIGHT = 32
COMBO_MIN_WIDTH = 200
BUTTON_MAX_WIDTH = 150
LABEL_MIN_WIDTH = 120


class ROMFileWidget(BaseExtractionWidget):
    """Widget for selecting and displaying ROM file information"""

    # Signals
    browse_clicked = pyqtSignal()  # Emitted when browse button clicked

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        """Initialize the user interface"""
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)

        # ROM file selection
        rom_group = self._create_group_box("ROM File")
        rom_layout = QVBoxLayout()
        rom_layout.setSpacing(SPACING_MEDIUM)
        rom_layout.setContentsMargins(SPACING_MEDIUM, SPACING_MEDIUM, SPACING_MEDIUM, SPACING_MEDIUM)

        # ROM path row with simple horizontal layout
        rom_row = QHBoxLayout()
        rom_row.setSpacing(SPACING_MEDIUM)

        rom_label = QLabel("ROM:")
        rom_label.setMinimumWidth(50)
        rom_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        rom_row.addWidget(rom_label)

        self.rom_path_edit = QLineEdit()
        self.rom_path_edit.setPlaceholderText("Select ROM file...")
        self.rom_path_edit.setReadOnly(True)
        self.rom_path_edit.setMinimumWidth(250)
        rom_row.addWidget(self.rom_path_edit, 1)  # Stretch factor 1

        self.browse_rom_btn = QPushButton("Browse...")
        self.browse_rom_btn.setMinimumHeight(BUTTON_MIN_HEIGHT)
        self.browse_rom_btn.setFixedWidth(BUTTON_MAX_WIDTH)
        self.browse_rom_btn.clicked.connect(self.browse_clicked.emit)
        rom_row.addWidget(self.browse_rom_btn)

        rom_layout.addLayout(rom_row)

        # ROM info display
        self.rom_info_label = QLabel("No ROM loaded")
        self.rom_info_label.setWordWrap(True)
        self.rom_info_label.setStyleSheet("QLabel { color: #666; font-size: 11px; padding: 5px; }")
        rom_layout.addWidget(self.rom_info_label)

        rom_group.setLayout(rom_layout)
        layout.addWidget(rom_group)

        self.setLayout(layout)

    def set_rom_path(self, path: str):
        """Set the ROM path display"""
        self.rom_path_edit.setText(path)

    def set_info_text(self, html: str):
        """Set the ROM info display text (supports HTML)"""
        self.rom_info_label.setText(html)

    def clear(self):
        """Clear the ROM selection"""
        self.rom_path_edit.clear()
        self.rom_info_label.setText("No ROM loaded")
