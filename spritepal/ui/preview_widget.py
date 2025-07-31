"""
Sprite preview widget for SpritePal
"""

from PyQt6.QtCore import QSize, Qt
from PyQt6.QtGui import QColor, QPainter, QPen, QPixmap
from PyQt6.QtWidgets import QWidget


class SpritePreviewWidget(QWidget):
    """Widget for previewing extracted sprites"""

    def __init__(self) -> None:
        super().__init__()
        self._pixmap = None
        self._tile_count = 0
        self._tiles_per_row = 0
        self.setMinimumSize(QSize(256, 256))
        self.setStyleSheet(
            """
            SpritePreviewWidget {
                background-color: #1e1e1e;
                border: 1px solid #555;
            }
        """
        )

    def paintEvent(self, a0):
        """Paint the preview"""
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(30, 30, 30))

        if self._pixmap:
            # Scale pixmap to fit while maintaining aspect ratio
            scaled_pixmap = self._pixmap.scaled(
                self.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.FastTransformation,
            )

            # Center the pixmap
            x = (self.width() - scaled_pixmap.width()) // 2
            y = (self.height() - scaled_pixmap.height()) // 2

            painter.drawPixmap(x, y, scaled_pixmap)
        else:
            # Draw placeholder
            painter.setPen(QPen(QColor(100, 100, 100), 2))
            painter.drawText(
                self.rect(),
                Qt.AlignmentFlag.AlignCenter,
                "Sprite preview will appear here",
            )

    def set_preview(self, pixmap, tile_count=0, tiles_per_row=0):
        """Set the preview pixmap"""
        self._pixmap = pixmap
        self._tile_count = tile_count
        self._tiles_per_row = tiles_per_row
        self.update()

    def set_preview_from_file(self, file_path: str) -> None:
        """Load preview from file"""
        pixmap = QPixmap(file_path)
        if not pixmap.isNull():
            self.set_preview(pixmap)

    def clear(self) -> None:
        """Clear the preview"""
        self._pixmap = None
        self._tile_count = 0
        self._tiles_per_row = 0
        self.update()

    def get_tile_info(self) -> tuple[int, int]:
        """Get tile information"""
        return self._tile_count, self._tiles_per_row
