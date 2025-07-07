#!/usr/bin/env python3
"""
Multi-palette preview widget for SNES sprites
Shows sprites with all 16 palettes and highlights OAM-assigned palettes
"""

from PyQt6.QtWidgets import (
    QWidget, QGridLayout, QLabel, QVBoxLayout,
    QHBoxLayout, QScrollArea, QGroupBox, QCheckBox, QFrame
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QPixmap, QImage, QPainter, QPen, QColor, QFont
from PIL import Image

class PalettePreviewTile(QLabel):
    """Individual palette preview tile"""
    clicked = pyqtSignal(int)  # palette number

    def __init__(self, palette_num, parent=None):
        super().__init__(parent)
        self.palette_num = palette_num
        self.is_active = False
        self.is_selected = False

        self.setFrameStyle(QFrame.Shape.Box)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setScaledContents(True)
        self.setMinimumSize(256, 256)  # Larger preview
        self.setMaximumSize(512, 512)   # Allow growth

        self.update_style()

    def set_active(self, active):
        """Mark this palette as actively used by OAM"""
        self.is_active = active
        self.update_style()

    def set_selected(self, selected):
        """Mark this palette as selected"""
        self.is_selected = selected
        self.update_style()

    def update_style(self):
        """Update visual style based on state"""
        if self.is_selected:
            self.setStyleSheet("""
                QLabel {
                    border: 3px solid #FFD700;
                    background-color: #4a4a4a;
                }
            """)
        elif self.is_active:
            self.setStyleSheet("""
                QLabel {
                    border: 2px solid #00FF00;
                    background-color: #3a3a3a;
                }
            """)
        else:
            self.setStyleSheet("""
                QLabel {
                    border: 1px solid #666;
                    background-color: #2a2a2a;
                }
            """)

    def mousePressEvent(self, event):
        """Handle click events"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.palette_num)

    def set_image(self, image):
        """Set the preview image (PIL Image)"""
        if isinstance(image, Image.Image):
            # Convert PIL to QPixmap
            if image.mode == 'RGBA':
                data = image.tobytes('raw', 'RGBA')
                qimage = QImage(data, image.width, image.height, QImage.Format.Format_RGBA8888)
            elif image.mode == 'RGB':
                data = image.tobytes('raw', 'RGB')
                qimage = QImage(data, image.width, image.height, QImage.Format.Format_RGB888)
            else:
                # Convert to RGB
                image_rgb = image.convert('RGB')
                data = image_rgb.tobytes('raw', 'RGB')
                qimage = QImage(data, image.width, image.height, QImage.Format.Format_RGB888)

            pixmap = QPixmap.fromImage(qimage)

            # Add palette number overlay
            painter = QPainter(pixmap)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)

            # Draw background for text
            painter.fillRect(0, 0, 30, 20, QColor(0, 0, 0, 180))

            # Draw palette number
            painter.setPen(QPen(Qt.GlobalColor.white))
            font = QFont("Arial", 12, QFont.Weight.Bold)
            painter.setFont(font)
            painter.drawText(5, 15, f"P{self.palette_num}")

            # Draw active indicator
            if self.is_active:
                painter.setPen(QPen(QColor(0, 255, 0), 2))
                painter.drawRect(1, 1, pixmap.width()-2, pixmap.height()-2)

            painter.end()

            self.setPixmap(pixmap)

class MultiPaletteViewer(QWidget):
    """Widget showing sprites with all 16 palettes"""

    palette_selected = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)

        self.palette_tiles = []
        self.active_palettes = set()
        self.selected_palette = None

        self.init_ui()

    def init_ui(self):
        """Initialize the UI"""
        layout = QVBoxLayout(self)

        # Title
        title_label = QLabel("Multi-Palette Preview")
        title_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(title_label)

        # Controls
        controls_layout = QHBoxLayout()

        self.highlight_active_check = QCheckBox("Highlight Active Palettes")
        self.highlight_active_check.setChecked(True)
        self.highlight_active_check.toggled.connect(self.update_highlights)
        controls_layout.addWidget(self.highlight_active_check)

        self.show_unused_check = QCheckBox("Show Unused Palettes")
        self.show_unused_check.setChecked(True)
        self.show_unused_check.toggled.connect(self.update_visibility)
        controls_layout.addWidget(self.show_unused_check)

        controls_layout.addStretch()
        layout.addLayout(controls_layout)

        # Scroll area for palette grid
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)

        # Palette grid container
        grid_widget = QWidget()
        self.grid_layout = QGridLayout(grid_widget)
        self.grid_layout.setSpacing(8)

        # Create 16 palette preview tiles (4x4 grid)
        for i in range(16):
            row = i // 4
            col = i % 4

            # Create container for each palette
            container = QGroupBox(f"Palette {i}")
            container_layout = QVBoxLayout(container)

            # Create scrollable area for preview tile
            tile_scroll = QScrollArea()
            tile_scroll.setWidgetResizable(True)
            tile_scroll.setMinimumSize(280, 280)

            # Create preview tile
            tile = PalettePreviewTile(i)
            tile.clicked.connect(self.on_palette_clicked)
            tile_scroll.setWidget(tile)

            container_layout.addWidget(tile_scroll)

            # Add usage info label
            usage_label = QLabel("Not used")
            usage_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            usage_label.setStyleSheet("color: #888;")
            container_layout.addWidget(usage_label)

            self.grid_layout.addWidget(container, row, col)
            self.palette_tiles.append((tile, usage_label, container))

        scroll_area.setWidget(grid_widget)
        layout.addWidget(scroll_area)

        # Info panel
        info_group = QGroupBox("Palette Information")
        info_layout = QVBoxLayout(info_group)

        self.info_label = QLabel("Click on a palette to see details")
        self.info_label.setWordWrap(True)
        info_layout.addWidget(self.info_label)

        layout.addWidget(info_group)

    def set_palette_images(self, palette_images_dict, oam_stats=None):
        """Set images for all palettes

        Args:
            palette_images_dict: dict of palette_num -> PIL Image
            oam_stats: optional OAM statistics dict with palette usage
        """
        # Update active palettes from OAM stats
        if oam_stats and 'active_palettes' in oam_stats:
            self.active_palettes = set(oam_stats['active_palettes'])

        # Set images for each palette
        for i in range(16):
            tile, usage_label, container = self.palette_tiles[i]

            # Check if we have an image for this palette
            if f'palette_{i}' in palette_images_dict:
                img = palette_images_dict[f'palette_{i}']
                tile.set_image(img)
            elif i in palette_images_dict:
                img = palette_images_dict[i]
                tile.set_image(img)

            # Update active status
            is_active = i in self.active_palettes
            tile.set_active(is_active)

            # Update usage label
            if oam_stats and 'palette_counts' in oam_stats:
                if i in oam_stats['palette_counts']:
                    count = oam_stats['palette_counts'][i]
                    usage_label.setText(f"Used by {count} sprites")
                    usage_label.setStyleSheet("color: #0F0;")
                else:
                    usage_label.setText("Not used")
                    usage_label.setStyleSheet("color: #888;")

        self.update_visibility()

    def set_single_image_all_palettes(self, base_image, palettes_list):
        """Show the same image with all 16 different palettes

        Args:
            base_image: PIL Image in indexed mode
            palettes_list: list of 16 palette data arrays
        """
        for i in range(16):
            tile, usage_label, container = self.palette_tiles[i]

            # Create copy with specific palette
            img = base_image.copy()
            if i < len(palettes_list) and palettes_list[i]:
                img.putpalette(palettes_list[i])

            tile.set_image(img)

    def on_palette_clicked(self, palette_num):
        """Handle palette tile click"""
        # Update selection
        for i, (tile, _, _) in enumerate(self.palette_tiles):
            tile.set_selected(i == palette_num)

        self.selected_palette = palette_num
        self.palette_selected.emit(palette_num)

        # Update info
        info_text = f"Selected: Palette {palette_num}"
        if palette_num in self.active_palettes:
            info_text += " (Active in OAM)"
        self.info_label.setText(info_text)

    def update_highlights(self):
        """Update active palette highlights"""
        show_highlights = self.highlight_active_check.isChecked()

        for i, (tile, _, _) in enumerate(self.palette_tiles):
            if show_highlights and i in self.active_palettes:
                tile.set_active(True)
            else:
                tile.set_active(False)

    def update_visibility(self):
        """Update visibility of unused palettes"""
        show_unused = self.show_unused_check.isChecked()

        for i, (tile, usage_label, container) in enumerate(self.palette_tiles):
            if i in self.active_palettes or show_unused:
                container.setVisible(True)
            else:
                container.setVisible(False)

    def get_selected_palette(self):
        """Get the currently selected palette number"""
        return self.selected_palette

    def set_oam_statistics(self, oam_stats):
        """Update display with OAM statistics"""
        if oam_stats:
            self.active_palettes = set(oam_stats.get('active_palettes', []))

            # Update all tiles with usage info
            for i, (tile, usage_label, container) in enumerate(self.palette_tiles):
                if 'palette_counts' in oam_stats and i in oam_stats['palette_counts']:
                    count = oam_stats['palette_counts'][i]
                    usage_label.setText(f"Used by {count} sprites")
                    usage_label.setStyleSheet("color: #0F0;")
                    tile.set_active(True)
                else:
                    usage_label.setText("Not used")
                    usage_label.setStyleSheet("color: #888;")
                    tile.set_active(False)

            self.update_visibility()