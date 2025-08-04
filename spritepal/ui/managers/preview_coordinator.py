"""
Preview coordination for MainWindow sprite and palette previews
"""

from typing import TYPE_CHECKING

from PyQt6.QtCore import QObject, Qt
from PyQt6.QtWidgets import (
    QGroupBox,
    QLabel,
    QSizePolicy,
    QSplitter,
    QVBoxLayout,
    QWidget,
)
from ui.styles import get_muted_text_style

if TYPE_CHECKING:
    from ui.palette_preview import PalettePreviewWidget
    from ui.zoomable_preview import PreviewPanel


class PreviewCoordinator(QObject):
    """Coordinates sprite and palette preview widgets"""

    def __init__(
        self,
        sprite_preview: "PreviewPanel",
        palette_preview: "PalettePreviewWidget"
    ) -> None:
        """Initialize preview coordinator

        Args:
            sprite_preview: Sprite preview widget
            palette_preview: Palette preview widget
        """
        super().__init__()
        self.sprite_preview = sprite_preview
        self.palette_preview = palette_preview

        # Preview info label
        self.preview_info: QLabel

    def create_preview_panel(self, parent: QWidget) -> QWidget:
        """Create and configure the preview panel

        Args:
            parent: Parent widget

        Returns:
            Configured preview panel widget
        """
        # Create vertical splitter for right panel
        right_splitter = QSplitter(Qt.Orientation.Vertical)

        # Extraction preview group
        preview_group = QGroupBox("Extraction Preview")
        preview_layout = QVBoxLayout()

        preview_layout.addWidget(
            self.sprite_preview, 1
        )  # Give stretch factor to expand

        # Preview info
        self.preview_info = QLabel("No sprites loaded")
        self.preview_info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_info.setStyleSheet(get_muted_text_style())
        self.preview_info.setSizePolicy(
            QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum
        )
        preview_layout.addWidget(self.preview_info, 0)  # No stretch factor

        preview_group.setLayout(preview_layout)
        right_splitter.addWidget(preview_group)

        # Palette preview group
        palette_group = QGroupBox("Palette Preview")
        palette_layout = QVBoxLayout()
        palette_layout.addWidget(self.palette_preview)
        palette_group.setLayout(palette_layout)
        right_splitter.addWidget(palette_group)

        # Configure splitter
        right_splitter.setSizes([400, 200])  # Initial sizes
        right_splitter.setStretchFactor(0, 1)  # Preview panel stretches
        right_splitter.setStretchFactor(1, 0)  # Palette panel doesn't stretch

        # Set minimum sizes
        preview_group.setMinimumHeight(200)
        palette_group.setMinimumHeight(150)

        return right_splitter

    def clear_previews(self) -> None:
        """Clear both sprite and palette previews"""
        self.sprite_preview.clear()
        self.palette_preview.clear()
        self.preview_info.setText("No sprites loaded")

    def update_preview_info(self, message: str) -> None:
        """Update preview info message

        Args:
            message: Message to display
        """
        self.preview_info.setText(message)
