#!/usr/bin/env python3
"""
Palette switcher dialog for selecting between multiple palettes
"""

# Third-party imports
from PyQt6.QtCore import Qt, pyqtSignal
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

# Local imports
from pixel_editor.core.pixel_editor_utils import count_non_black_colors


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

    def update_preview(self, current, _):
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
