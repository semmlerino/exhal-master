"""
Sprite preview widget for SpritePal
Shows visual preview of sprites with optional palette support
"""


from PIL import Image
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QImage, QPixmap
from PyQt6.QtWidgets import (
    QComboBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from spritepal.core.default_palette_loader import DefaultPaletteLoader
from spritepal.core.rom_extractor import ROMExtractor
from spritepal.utils.logging_config import get_logger

logger = get_logger(__name__)


class SpritePreviewWidget(QWidget):
    """Widget for displaying sprite previews with palette selection"""

    palette_changed = pyqtSignal(int)  # Emitted when palette selection changes

    def __init__(self, title: str = "Sprite Preview", parent=None):
        super().__init__(parent)
        self.title = title
        self.sprite_pixmap: QPixmap | None = None
        self.palettes: list[list[list[int]]] = []
        self.current_palette_index = 8  # Default sprite palette
        self.sprite_data: bytes | None = None
        self.default_palette_loader = DefaultPaletteLoader()
        self._setup_ui()

    def _setup_ui(self):
        """Initialize the user interface"""
        layout = QVBoxLayout()

        # Group box
        group = QGroupBox(self.title)
        group_layout = QVBoxLayout()

        # Preview label
        self.preview_label = QLabel()
        self.preview_label.setMinimumSize(256, 256)
        self.preview_label.setMaximumSize(512, 512)
        self.preview_label.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_label.setStyleSheet(
            """
            QLabel {
                border: 2px solid #ccc;
                background-color: #f0f0f0;
                background-image: qlineargradient(x1:0, y1:0, x2:16, y2:16,
                    stop:0 #e0e0e0, stop:0.5 #e0e0e0, stop:0.51 #f0f0f0, stop:1 #f0f0f0);
            }
        """
        )
        group_layout.addWidget(self.preview_label)

        # Palette selector
        palette_layout = QHBoxLayout()
        palette_layout.addWidget(QLabel("Palette:"))
        self.palette_combo = QComboBox()
        self.palette_combo.setMinimumWidth(150)
        self.palette_combo.currentIndexChanged.connect(self._on_palette_changed)
        palette_layout.addWidget(self.palette_combo)
        palette_layout.addStretch()

        group_layout.addLayout(palette_layout)

        # Info label
        self.info_label = QLabel("No sprite loaded")
        self.info_label.setStyleSheet("QLabel { color: #666; }")
        group_layout.addWidget(self.info_label)

        group.setLayout(group_layout)
        layout.addWidget(group)

        self.setLayout(layout)

    def load_sprite_from_png(self, png_path: str, sprite_name: str | None = None):
        """Load sprite from PNG file"""
        try:
            # Load image
            img = Image.open(png_path)

            # Check if grayscale or indexed
            if img.mode == "L":
                # Grayscale - need palettes for color
                self._load_grayscale_sprite(img, sprite_name)
            elif img.mode == "P":
                # Indexed - has built-in palette
                self._load_indexed_sprite(img)
            else:
                # Convert to indexed
                img = img.convert("P", palette=Image.Palette.ADAPTIVE, colors=16)
                self._load_indexed_sprite(img)

            # Update info
            self.info_label.setText(
                f"Size: {img.size[0]}x{img.size[1]} | Mode: {img.mode}"
            )

        except Exception as e:
            logger.exception("Failed to load sprite preview")
            self.info_label.setText(f"Error loading sprite: {e}")

    def _load_grayscale_sprite(
        self, img: Image.Image, sprite_name: str | None = None
    ):
        """Load grayscale sprite and apply palettes"""
        # Convert to QImage
        width, height = img.size

        # Get default palettes if available
        if sprite_name:
            default_palettes = self.default_palette_loader.get_all_kirby_palettes()
            if default_palettes:
                # Convert dict values to list maintaining type compatibility
                palette_list = []
                for palette in default_palettes.values():
                    if isinstance(palette, list):
                        palette_list.append(palette)
                self.palettes = palette_list

                # Update combo box
                self.palette_combo.clear()
                for idx, _colors in default_palettes.items():
                    self.palette_combo.addItem(f"Palette {idx}", idx)

                # Select default Kirby palette
                if 8 in default_palettes:
                    combo_idx = list(default_palettes.keys()).index(8)
                    self.palette_combo.setCurrentIndex(combo_idx)

        # Store grayscale data for palette swapping
        self.sprite_data = img.tobytes()

        # Apply current palette
        self._update_preview_with_palette(img)

    def _load_indexed_sprite(self, img: Image.Image):
        """Load indexed sprite with its palette"""
        # Convert to RGBA for display
        img_rgba = img.convert("RGBA")

        # Convert to QPixmap
        qimg = QImage(
            img_rgba.tobytes(),
            img_rgba.width,
            img_rgba.height,
            img_rgba.width * 4,
            QImage.Format.Format_RGBA8888,
        )
        pixmap = QPixmap.fromImage(qimg)

        # Scale for preview
        scaled = pixmap.scaled(
            256,
            256,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.FastTransformation,
        )

        self.preview_label.setPixmap(scaled)
        self.sprite_pixmap = pixmap

        # No palette selection for indexed sprites
        self.palette_combo.setEnabled(False)
        self.palette_combo.clear()
        self.palette_combo.addItem("Built-in Palette")

    def _update_preview_with_palette(self, grayscale_img: Image.Image):
        """Update preview by applying selected palette to grayscale image"""
        if not self.palettes or self.current_palette_index >= len(self.palettes):
            # No palette - show grayscale
            img_rgba = grayscale_img.convert("RGBA")
        else:
            # Apply palette
            palette_colors = self.palettes[self.palette_combo.currentIndex()]

            # Create indexed image
            indexed = Image.new("P", grayscale_img.size)
            indexed.putdata(list(grayscale_img.getdata()))

            # Create palette (16 colors -> 256 color palette)
            full_palette = []
            for i in range(256):
                if i < len(palette_colors):
                    full_palette.extend(palette_colors[i])
                else:
                    full_palette.extend([0, 0, 0])

            indexed.putpalette(full_palette)

            # Convert to RGBA for display
            img_rgba = indexed.convert("RGBA")

        # Convert to QPixmap
        qimg = QImage(
            img_rgba.tobytes(),
            img_rgba.width,
            img_rgba.height,
            img_rgba.width * 4,
            QImage.Format.Format_RGBA8888,
        )
        pixmap = QPixmap.fromImage(qimg)

        # Scale for preview
        scaled = pixmap.scaled(
            256,
            256,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.FastTransformation,
        )

        self.preview_label.setPixmap(scaled)
        self.sprite_pixmap = pixmap

    def _on_palette_changed(self, index: int):
        """Handle palette selection change"""
        if index >= 0 and self.sprite_data:
            self.current_palette_index = self.palette_combo.currentData() or 8
            # Recreate image from grayscale data
            # Assume square sprite for now
            size = int(len(self.sprite_data) ** 0.5)
            img = Image.frombytes("L", (size, size), self.sprite_data)
            self._update_preview_with_palette(img)
            self.palette_changed.emit(self.current_palette_index)

    def load_sprite_from_4bpp(
        self,
        tile_data: bytes,
        width: int = 128,
        height: int = 128,
        sprite_name: str | None = None,
    ):
        """Load sprite from 4bpp tile data"""
        try:
            # Validate tile data
            if not tile_data:
                self.clear()
                self.info_label.setText("No sprite data available")
                return

            bytes_per_tile = 32
            extra_bytes = len(tile_data) % bytes_per_tile
            if extra_bytes > bytes_per_tile // 2:  # More than half a tile of extra data
                self.clear()
                self.info_label.setText(
                    "Unable to display sprite - data appears corrupted"
                )
                return

            # Use ROM extractor's conversion method
            extractor = ROMExtractor()

            # Create temporary image from 4bpp data
            img = Image.new("L", (width, height), 0)

            # Process tiles (simplified - assumes data is already in correct format)
            tiles_per_row = width // 8
            num_tiles = len(tile_data) // bytes_per_tile

            if num_tiles == 0:
                self.clear()
                self.info_label.setText("No valid sprite tiles found")
                return

            for tile_idx in range(num_tiles):
                tile_x = (tile_idx % tiles_per_row) * 8
                tile_y = (tile_idx // tiles_per_row) * 8

                if tile_y >= height:
                    break

                tile_offset = tile_idx * bytes_per_tile
                tile_bytes = tile_data[tile_offset : tile_offset + bytes_per_tile]

                # Decode 4bpp tile
                for y in range(8):
                    for x in range(8):
                        pixel = extractor._get_4bpp_pixel(tile_bytes, x, y)
                        gray_value = pixel * 17  # Convert to grayscale
                        if tile_x + x < width and tile_y + y < height:
                            img.putpixel((tile_x + x, tile_y + y), gray_value)

            # Load as grayscale sprite
            self._load_grayscale_sprite(img, sprite_name)

            info_text = f"Size: {width}x{height} | Tiles: {num_tiles}"
            if extra_bytes > 0:
                info_text += f" | Warning: {extra_bytes} extra bytes"
            self.info_label.setText(info_text)

        except Exception as e:
            logger.exception("Failed to load 4bpp sprite")
            self.clear()
            self.info_label.setText(f"Error loading sprite: {e}")

    def clear(self):
        """Clear the preview"""
        self.preview_label.clear()
        self.preview_label.setText("No preview")
        self.palette_combo.clear()
        self.palette_combo.setEnabled(False)
        self.info_label.setText("No sprite loaded")
        self.sprite_pixmap = None
        self.sprite_data = None
        self.palettes = []

    def get_current_pixmap(self) -> QPixmap | None:
        """Get the current preview pixmap"""
        return self.sprite_pixmap
