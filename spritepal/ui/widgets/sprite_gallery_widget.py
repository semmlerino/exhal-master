"""
Sprite gallery widget for displaying multiple sprite thumbnails.
Provides grid layout with virtual scrolling and lazy loading.
"""

from typing import Any, Optional

from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from ui.widgets.sprite_thumbnail_widget import SpriteThumbnailWidget
from utils.logging_config import get_logger

logger = get_logger(__name__)


class SpriteGalleryWidget(QScrollArea):
    """Widget displaying a gallery of sprite thumbnails."""

    # Signals
    sprite_selected = pyqtSignal(int)  # Emits offset when sprite selected
    sprite_double_clicked = pyqtSignal(int)  # Emits offset on double-click
    selection_changed = pyqtSignal(list)  # Emits list of selected offsets

    def __init__(self, parent: Optional[QWidget] = None):
        """
        Initialize the sprite gallery widget.

        Args:
            parent: Parent widget
        """
        super().__init__(parent)

        # Gallery state
        self.thumbnails: dict[int, SpriteThumbnailWidget] = {}
        self.sprite_data: list[dict[str, Any]] = []
        self.selected_offsets: list[int] = []

        # Display settings
        self.thumbnail_size = 128
        self.columns = 6
        self.spacing = 8

        # Filtering
        self.filter_text = ""
        self.filter_compressed_only = False
        self.filter_size_min = 0
        self.filter_size_max = float('inf')

        # Performance
        self.lazy_load_timer = QTimer()
        self.lazy_load_timer.timeout.connect(self._load_visible_thumbnails)
        self.lazy_load_timer.setInterval(100)

        # UI components
        self.container_widget: Optional[QWidget] = None
        self.grid_layout: Optional[QGridLayout] = None
        self.controls_widget: Optional[QWidget] = None

        self._setup_ui()

    def _setup_ui(self):
        """Setup the gallery UI."""
        # Configure scroll area
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        # Main container
        main_widget = QWidget()
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(4, 4, 4, 4)

        # Controls bar
        self.controls_widget = self._create_controls()
        main_layout.addWidget(self.controls_widget)

        # Gallery container
        self.container_widget = QWidget()
        self.grid_layout = QGridLayout()
        self.grid_layout.setSpacing(self.spacing)
        self.grid_layout.setContentsMargins(4, 4, 4, 4)
        self.container_widget.setLayout(self.grid_layout)

        main_layout.addWidget(self.container_widget)
        main_layout.addStretch()

        main_widget.setLayout(main_layout)
        self.setWidget(main_widget)

        # Style
        self.setStyleSheet("""
            QScrollArea {
                background-color: #1e1e1e;
                border: 1px solid #333;
            }
        """)

    def _create_controls(self) -> QWidget:
        """Create the controls bar for the gallery."""
        controls = QWidget()
        layout = QHBoxLayout()
        layout.setContentsMargins(4, 4, 4, 4)

        # Thumbnail size slider
        size_label = QLabel("Size:")
        layout.addWidget(size_label)

        self.size_slider = QSlider(Qt.Orientation.Horizontal)
        self.size_slider.setRange(64, 256)
        self.size_slider.setValue(self.thumbnail_size)
        self.size_slider.setTickInterval(32)
        self.size_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.size_slider.setFixedWidth(150)
        self.size_slider.valueChanged.connect(self._on_size_changed)
        layout.addWidget(self.size_slider)

        # Size display
        self.size_label = QLabel(f"{self.thumbnail_size}px")
        self.size_label.setFixedWidth(40)
        layout.addWidget(self.size_label)

        layout.addSpacing(20)

        # Filter controls
        filter_label = QLabel("Filter:")
        layout.addWidget(filter_label)

        self.filter_input = QLineEdit()
        self.filter_input.setPlaceholderText("Search by offset...")
        self.filter_input.setFixedWidth(150)
        self.filter_input.textChanged.connect(self._apply_filters)
        layout.addWidget(self.filter_input)

        self.compressed_check = QCheckBox("HAL only")
        self.compressed_check.toggled.connect(self._apply_filters)
        layout.addWidget(self.compressed_check)

        layout.addSpacing(20)

        # Sort controls
        sort_label = QLabel("Sort:")
        layout.addWidget(sort_label)

        self.sort_combo = QComboBox()
        self.sort_combo.addItems(["Offset", "Size", "Tiles"])
        self.sort_combo.currentTextChanged.connect(self._apply_sort)
        layout.addWidget(self.sort_combo)

        layout.addStretch()

        # Selection actions
        self.select_all_btn = QPushButton("Select All")
        self.select_all_btn.clicked.connect(self._select_all)
        layout.addWidget(self.select_all_btn)

        self.clear_btn = QPushButton("Clear")
        self.clear_btn.clicked.connect(self._clear_selection)
        layout.addWidget(self.clear_btn)

        # Status
        self.status_label = QLabel("0 sprites")
        layout.addWidget(self.status_label)

        controls.setLayout(layout)
        return controls

    def set_sprites(self, sprites: list[dict[str, Any]]):
        """
        Set the sprites to display in the gallery.

        Args:
            sprites: List of sprite dictionaries with offset, size, etc.
        """
        # Clear existing thumbnails
        self._clear_gallery()

        # Store sprite data
        self.sprite_data = sprites

        # Apply initial sort
        self._apply_sort()

        # Create thumbnails
        self._create_thumbnails()

        # Update status
        self._update_status()

        # Don't start lazy loading timer - parent will handle thumbnail generation
        # self.lazy_load_timer.start()
        logger.debug(f"Gallery populated with {len(sprites)} sprites, waiting for thumbnail generation")

    def _clear_gallery(self):
        """Clear all thumbnails from the gallery."""
        for thumbnail in self.thumbnails.values():
            thumbnail.deleteLater()
        self.thumbnails.clear()

        # Clear layout
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _create_thumbnails(self):
        """Create thumbnail widgets for all sprites."""
        row = 0
        col = 0

        for sprite_info in self.sprite_data:
            offset = sprite_info.get('offset', 0)
            if isinstance(offset, str):
                # Convert hex string to int
                offset = int(offset, 16) if offset.startswith('0x') else int(offset)

            # Create thumbnail
            thumbnail = SpriteThumbnailWidget(
                offset=offset,
                size=self.thumbnail_size
            )

            # Connect signals
            thumbnail.clicked.connect(self._on_thumbnail_clicked)
            thumbnail.double_clicked.connect(self._on_thumbnail_double_clicked)
            thumbnail.selected.connect(lambda sel, off=offset: self._on_thumbnail_selected(off, sel))

            # Set sprite info (without pixmap yet - lazy load)
            thumbnail.set_sprite_data(QPixmap(), sprite_info)

            # Add to grid
            self.grid_layout.addWidget(thumbnail, row, col)
            self.thumbnails[offset] = thumbnail

            # Update position
            col += 1
            if col >= self.columns:
                col = 0
                row += 1

    def _load_visible_thumbnails(self):
        """Load pixmaps for visible thumbnails (lazy loading)."""
        # Get visible area
        visible_rect = self.viewport().rect()

        for offset, thumbnail in self.thumbnails.items():
            # Check if thumbnail is visible
            thumbnail_pos = thumbnail.mapTo(self.widget(), thumbnail.pos())
            thumbnail_rect = thumbnail.rect().translated(thumbnail_pos)

            if visible_rect.intersects(thumbnail_rect):
                # Load pixmap if not already loaded
                if not thumbnail.sprite_pixmap or thumbnail.sprite_pixmap.isNull():
                    # This would be replaced with actual sprite loading
                    # For now, create a placeholder
                    self._load_thumbnail_pixmap(thumbnail, offset)

    def _load_thumbnail_pixmap(self, thumbnail: SpriteThumbnailWidget, offset: int):
        """
        Load the actual sprite pixmap for a thumbnail.

        Args:
            thumbnail: The thumbnail widget
            offset: The sprite offset
        """
        # This is a placeholder - actual implementation would load from ROM
        # and generate the sprite preview
        pixmap = QPixmap(128, 128)
        pixmap.fill(Qt.GlobalColor.darkGray)
        thumbnail.set_sprite_data(pixmap, thumbnail.sprite_info)

    def _on_size_changed(self, value: int):
        """Handle thumbnail size change."""
        self.thumbnail_size = value
        self.size_label.setText(f"{value}px")

        # Update all thumbnails
        for thumbnail in self.thumbnails.values():
            thumbnail.thumbnail_size = value
            thumbnail.setFixedSize(value, value + 20)
            thumbnail._setup_ui()  # Recreate UI with new size

        # Adjust columns based on new size
        self._update_columns()

    def _update_columns(self):
        """Update the number of columns based on widget width and thumbnail size."""
        if self.width() > 0:
            available_width = self.viewport().width() - 20
            self.columns = max(1, available_width // (self.thumbnail_size + self.spacing))
            self._reorganize_grid()

    def _reorganize_grid(self):
        """Reorganize thumbnails in the grid with new column count."""
        # Remove all widgets from grid
        for thumbnail in self.thumbnails.values():
            self.grid_layout.removeWidget(thumbnail)

        # Re-add in new arrangement
        row = 0
        col = 0
        for sprite_info in self.sprite_data:
            offset = sprite_info.get('offset', 0)
            if isinstance(offset, str):
                offset = int(offset, 16) if offset.startswith('0x') else int(offset)

            if offset in self.thumbnails:
                self.grid_layout.addWidget(self.thumbnails[offset], row, col)
                col += 1
                if col >= self.columns:
                    col = 0
                    row += 1

    def _apply_filters(self):
        """Apply current filters to the gallery."""
        filter_text = self.filter_input.text().lower()
        compressed_only = self.compressed_check.isChecked()

        for sprite_info in self.sprite_data:
            offset = sprite_info.get('offset', 0)
            if isinstance(offset, str):
                offset_int = int(offset, 16) if offset.startswith('0x') else int(offset)
                offset_str = offset
            else:
                offset_int = offset
                offset_str = f"0x{offset:06X}"

            if offset_int not in self.thumbnails:
                continue

            thumbnail = self.thumbnails[offset_int]

            # Check filters
            show = True

            # Text filter
            if filter_text and filter_text not in offset_str.lower():
                show = False

            # Compression filter
            if compressed_only and not sprite_info.get('compressed', False):
                show = False

            # Show/hide thumbnail
            thumbnail.setVisible(show)

        self._update_status()

    def _apply_sort(self):
        """Apply sorting to the sprite data."""
        sort_key = self.sort_combo.currentText()

        if sort_key == "Offset":
            self.sprite_data.sort(key=lambda x: x.get('offset', 0) if isinstance(x.get('offset', 0), int) else int(x.get('offset', '0'), 16))
        elif sort_key == "Size":
            self.sprite_data.sort(key=lambda x: x.get('decompressed_size', 0), reverse=True)
        elif sort_key == "Tiles":
            self.sprite_data.sort(key=lambda x: x.get('tile_count', 0), reverse=True)

        # Recreate thumbnails with new order
        self._create_thumbnails()

    def _on_thumbnail_clicked(self, offset: int):
        """Handle thumbnail click."""
        self.sprite_selected.emit(offset)

    def _on_thumbnail_double_clicked(self, offset: int):
        """Handle thumbnail double-click."""
        self.sprite_double_clicked.emit(offset)

    def _on_thumbnail_selected(self, offset: int, selected: bool):
        """Handle thumbnail selection change."""
        if selected and offset not in self.selected_offsets:
            self.selected_offsets.append(offset)
        elif not selected and offset in self.selected_offsets:
            self.selected_offsets.remove(offset)

        self.selection_changed.emit(self.selected_offsets)
        self._update_status()

    def _select_all(self):
        """Select all visible thumbnails."""
        for thumbnail in self.thumbnails.values():
            if thumbnail.isVisible():
                thumbnail.set_selected(True)

    def _clear_selection(self):
        """Clear all selections."""
        for thumbnail in self.thumbnails.values():
            thumbnail.set_selected(False)
        self.selected_offsets.clear()
        self.selection_changed.emit([])
        self._update_status()

    def _update_status(self):
        """Update the status label."""
        visible_count = sum(1 for t in self.thumbnails.values() if t.isVisible())
        selected_count = len(self.selected_offsets)

        status = f"{visible_count} sprites"
        if selected_count > 0:
            status += f" ({selected_count} selected)"

        self.status_label.setText(status)

    def resizeEvent(self, a0):
        """Handle resize event to adjust columns."""
        super().resizeEvent(a0)
        self._update_columns()

    def get_selected_sprites(self) -> list[dict[str, Any]]:
        """Get information for all selected sprites."""
        selected = []
        for offset in self.selected_offsets:
            for sprite_info in self.sprite_data:
                sprite_offset = sprite_info.get('offset', 0)
                if isinstance(sprite_offset, str):
                    sprite_offset = int(sprite_offset, 16) if sprite_offset.startswith('0x') else int(sprite_offset)
                if sprite_offset == offset:
                    selected.append(sprite_info)
                    break
        return selected
