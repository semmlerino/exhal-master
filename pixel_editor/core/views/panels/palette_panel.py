"""
Palette panel for the pixel editor
Displays the color palette and handles color selection
"""

# Third-party imports
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QGroupBox, QVBoxLayout, QWidget

# Local imports
from pixel_editor.core.widgets import ColorPaletteWidget


class PalettePanel(QWidget):
    """Panel for color palette display and selection"""

    # Signals
    colorSelected = pyqtSignal(int)  # Emits color index when selected

    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        """Initialize the palette panel UI"""
        # Main layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Palette group box
        palette_group = QGroupBox("Palette")
        palette_layout = QVBoxLayout()

        # Create palette widget
        self.palette_widget = ColorPaletteWidget()
        self.palette_widget.colorSelected.connect(self.colorSelected.emit)

        palette_layout.addWidget(self.palette_widget)
        palette_group.setLayout(palette_layout)

        # Add to main layout
        layout.addWidget(palette_group)

    def get_selected_color(self) -> int:
        """Get the currently selected color index"""
        return self.palette_widget.selected_index

    def set_selected_color(self, index: int):
        """Set the selected color by index"""
        self.palette_widget.selected_index = index
        self.palette_widget.update()
        # Emit signal to notify controller
        self.colorSelected.emit(index)

    def set_palette(self, colors: list, name: str = ""):
        """Update the displayed palette"""
        self.palette_widget.set_palette(colors, name)

    def get_palette_colors(self) -> list:
        """Get the current palette colors"""
        return self.palette_widget.colors

    def get_color_at(self, index: int) -> tuple:
        """Get RGB color at specific index"""
        if 0 <= index < len(self.palette_widget.colors):
            return self.palette_widget.colors[index]
        return (0, 0, 0)
