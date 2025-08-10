"""
Sprite thumbnail widget for gallery display.
Compact version of SpritePreviewWidget optimized for grid layouts.
"""

from typing import Optional

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QPainter, QPen, QPixmap
from PyQt6.QtWidgets import QLabel, QVBoxLayout, QWidget

from utils.logging_config import get_logger

logger = get_logger(__name__)


class SpriteThumbnailWidget(QWidget):
    """Compact sprite thumbnail for gallery display."""

    # Signals
    clicked = pyqtSignal(int)  # Emits offset when clicked
    double_clicked = pyqtSignal(int)  # Emits offset when double-clicked
    selected = pyqtSignal(bool)  # Emits selection state

    def __init__(
        self,
        offset: int = 0,
        size: int = 128,
        parent: Optional[QWidget] = None
    ):
        """
        Initialize sprite thumbnail widget.

        Args:
            offset: ROM offset of the sprite
            size: Size of the thumbnail (square)
            parent: Parent widget
        """
        super().__init__(parent)

        self.offset = offset
        self.thumbnail_size = size
        self.sprite_pixmap: Optional[QPixmap] = None
        self.is_selected = False
        self.is_hovered = False
        self.sprite_info = {}

        # Thumbnail display label
        self.thumbnail_label: Optional[QLabel] = None

        # Info text
        self.offset_text = f"0x{offset:06X}"
        self.size_text = ""
        self.compression_text = ""

        self._setup_ui()

    def _setup_ui(self):
        """Setup the thumbnail UI."""
        # Fixed size for consistent grid
        self.setFixedSize(self.thumbnail_size, self.thumbnail_size + 20)

        # Main layout
        layout = QVBoxLayout()
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(2)

        # Thumbnail display
        self.thumbnail_label = QLabel()
        self.thumbnail_label.setFixedSize(self.thumbnail_size - 4, self.thumbnail_size - 24)
        self.thumbnail_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.thumbnail_label.setStyleSheet("""
            QLabel {
                background-color: #2b2b2b;
                border: 1px solid #444;
                border-radius: 2px;
            }
        """)
        self.thumbnail_label.setScaledContents(True)
        layout.addWidget(self.thumbnail_label)

        # Offset label
        self.info_label = QLabel(self.offset_text)
        self.info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.info_label.setStyleSheet("""
            QLabel {
                color: #888;
                font-size: 10px;
                font-family: monospace;
            }
        """)
        self.info_label.setFixedHeight(16)
        layout.addWidget(self.info_label)

        self.setLayout(layout)

        # Enable mouse tracking for hover effects
        self.setMouseTracking(True)
        self.thumbnail_label.setMouseTracking(True)

        # Set tooltip
        self.setToolTip(f"Offset: {self.offset_text}")

    def set_sprite_data(
        self,
        pixmap: QPixmap,
        sprite_info: Optional[dict] = None
    ):
        """
        Set the sprite thumbnail data.

        Args:
            pixmap: Sprite pixmap to display
            sprite_info: Optional sprite metadata
        """
        self.sprite_pixmap = pixmap

        if sprite_info:
            self.sprite_info = sprite_info
            self._update_info_display()

        # Scale pixmap to fit thumbnail
        if pixmap and not pixmap.isNull():
            scaled = pixmap.scaled(
                self.thumbnail_label.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            self.thumbnail_label.setPixmap(scaled)
        else:
            # Show placeholder
            self._show_placeholder()

    def _show_placeholder(self):
        """Show a placeholder when no sprite is loaded."""
        placeholder = QPixmap(self.thumbnail_label.size())
        placeholder.fill(QColor(40, 40, 40))

        painter = QPainter(placeholder)
        painter.setPen(QPen(QColor(100, 100, 100)))
        painter.setFont(QFont("Arial", 10))
        painter.drawText(
            placeholder.rect(),
            Qt.AlignmentFlag.AlignCenter,
            "Loading..."
        )
        painter.end()

        self.thumbnail_label.setPixmap(placeholder)

    def _update_info_display(self):
        """Update the info display based on sprite metadata."""
        if not self.sprite_info:
            return

        # Update size text
        if 'decompressed_size' in self.sprite_info:
            size_kb = self.sprite_info['decompressed_size'] / 1024
            self.size_text = f"{size_kb:.1f}KB"

        # Update compression status
        if self.sprite_info.get('compressed', False):
            self.compression_text = "HAL"
        else:
            self.compression_text = "Raw"

        # Update tooltip with more details
        tooltip_parts = [
            f"Offset: {self.offset_text}",
            f"Size: {self.size_text}" if self.size_text else "",
            f"Type: {self.compression_text}" if self.compression_text else "",
        ]

        if 'tile_count' in self.sprite_info:
            tooltip_parts.append(f"Tiles: {self.sprite_info['tile_count']}")

        self.setToolTip("\n".join(filter(None, tooltip_parts)))

    def set_selected(self, selected: bool):
        """
        Set the selection state of the thumbnail.

        Args:
            selected: Whether the thumbnail is selected
        """
        self.is_selected = selected
        self._update_style()
        self.selected.emit(selected)

    def _update_style(self):
        """Update the visual style based on state."""
        if self.is_selected:
            border_color = "#4a9eff"
            border_width = "2px"
            bg_color = "#3a3a4a"
        elif self.is_hovered:
            border_color = "#666"
            border_width = "1px"
            bg_color = "#333"
        else:
            border_color = "#444"
            border_width = "1px"
            bg_color = "#2b2b2b"

        self.thumbnail_label.setStyleSheet(f"""
            QLabel {{
                background-color: {bg_color};
                border: {border_width} solid {border_color};
                border-radius: 2px;
            }}
        """)

    def enterEvent(self, event):
        """Handle mouse enter event."""
        self.is_hovered = True
        self._update_style()
        super().enterEvent(event)

    def leaveEvent(self, a0):
        """Handle mouse leave event."""
        self.is_hovered = False
        self._update_style()
        super().leaveEvent(a0)

    def mousePressEvent(self, a0):
        """Handle mouse press event."""
        if a0.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.offset)
            # Toggle selection on click
            self.set_selected(not self.is_selected)
        super().mousePressEvent(a0)

    def mouseDoubleClickEvent(self, a0):
        """Handle double click event."""
        if a0.button() == Qt.MouseButton.LeftButton:
            self.double_clicked.emit(self.offset)
        super().mouseDoubleClickEvent(a0)

    def get_offset(self) -> int:
        """Get the sprite offset."""
        return self.offset

    def get_sprite_info(self) -> dict:
        """Get the sprite metadata."""
        return self.sprite_info
