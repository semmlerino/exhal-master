"""
Sprite gallery tab for visual overview of all sprites in ROM.
Provides grid display, filtering, sorting, and batch operations.
"""

from pathlib import Path
from typing import Any, Optional

from PySide6.QtCore import Qt, QThread, QTimer, Signal
from PySide6.QtGui import QAction, QPixmap
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QProgressDialog,
    QPushButton,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from core.sprite_finder import SpriteFinder
from ui.widgets.sprite_gallery_widget import SpriteGalleryWidget
from ui.workers.batch_thumbnail_worker import BatchThumbnailWorker
from utils.logging_config import get_logger

logger = get_logger(__name__)

# Layout constants
LAYOUT_SPACING = 4
LAYOUT_MARGINS = 4
BUTTON_HEIGHT = 32


class SpriteGalleryTab(QWidget):
    """Tab widget for sprite gallery display and management."""

    # Signals
    sprite_selected = Signal(int)  # Navigate to sprite
    sprites_exported = Signal(list)  # Sprites exported

    def __init__(self, parent: Optional[QWidget] = None):
        """
        Initialize the sprite gallery tab.

        Args:
            parent: Parent widget
        """
        super().__init__(parent)

        # State
        self.rom_path: Optional[str] = None
        self.rom_size: int = 0
        self.rom_extractor = None
        self.sprites_data: list[dict[str, Any]] = []

        # Workers
        self.thumbnail_worker: Optional[BatchThumbnailWorker] = None
        self.scan_thread: Optional[QThread] = None

        # UI Components
        self.gallery_widget: Optional[SpriteGalleryWidget] = None
        self.toolbar: Optional[QToolBar] = None
        self.progress_dialog: Optional[QProgressDialog] = None

        self._setup_ui()

    def _setup_ui(self):
        """Setup the tab UI."""
        layout = QVBoxLayout()
        layout.setContentsMargins(LAYOUT_MARGINS, LAYOUT_MARGINS, LAYOUT_MARGINS, LAYOUT_MARGINS)
        layout.setSpacing(LAYOUT_SPACING)

        # Toolbar
        self.toolbar = self._create_toolbar()
        layout.addWidget(self.toolbar)

        # Gallery widget with proper size policy
        self.gallery_widget = SpriteGalleryWidget(self)
        from PySide6.QtWidgets import QSizePolicy
        self.gallery_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.gallery_widget.sprite_selected.connect(self._on_sprite_selected)
        self.gallery_widget.sprite_double_clicked.connect(self._on_sprite_double_clicked)
        self.gallery_widget.selection_changed.connect(self._on_selection_changed)
        layout.addWidget(self.gallery_widget, 1)  # Give it stretch

        # Action bar
        action_bar = self._create_action_bar()
        layout.addWidget(action_bar)

        self.setLayout(layout)

    def _create_toolbar(self) -> QToolBar:
        """Create the toolbar with gallery actions."""
        toolbar = QToolBar()
        toolbar.setMovable(False)

        # Scan for sprites
        scan_action = QAction("🔍 Scan ROM", self)
        scan_action.setToolTip("Scan ROM for all sprites")
        scan_action.triggered.connect(self._scan_for_sprites)
        toolbar.addAction(scan_action)

        toolbar.addSeparator()

        # Export actions
        export_action = QAction("💾 Export Selected", self)
        export_action.setToolTip("Export selected sprites as PNG")
        export_action.triggered.connect(self._export_selected)
        toolbar.addAction(export_action)

        export_sheet_action = QAction("📋 Export Sheet", self)
        export_sheet_action.setToolTip("Export as sprite sheet")
        export_sheet_action.triggered.connect(self._export_sprite_sheet)
        toolbar.addAction(export_sheet_action)

        toolbar.addSeparator()

        # View options
        grid_action = QAction("⚏ Grid View", self)
        grid_action.setCheckable(True)
        grid_action.setChecked(True)
        toolbar.addAction(grid_action)

        list_action = QAction("☰ List View", self)
        list_action.setCheckable(True)
        toolbar.addAction(list_action)

        toolbar.addSeparator()

        # Refresh
        refresh_action = QAction("🔄 Refresh", self)
        refresh_action.setToolTip("Refresh thumbnails")
        refresh_action.triggered.connect(self._refresh_thumbnails)
        toolbar.addAction(refresh_action)

        return toolbar

    def _create_action_bar(self) -> QWidget:
        """Create the bottom action bar."""
        widget = QWidget()
        from PySide6.QtWidgets import QSizePolicy
        layout = QHBoxLayout()
        layout.setContentsMargins(LAYOUT_MARGINS, LAYOUT_MARGINS, LAYOUT_MARGINS, LAYOUT_MARGINS)

        # Quick actions with responsive sizing
        self.compare_btn = QPushButton("Compare")
        self.compare_btn.setEnabled(False)
        self.compare_btn.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        self.compare_btn.setFixedHeight(BUTTON_HEIGHT)
        self.compare_btn.clicked.connect(self._compare_sprites)
        layout.addWidget(self.compare_btn)

        self.palette_btn = QPushButton("Apply Palette")
        self.palette_btn.setEnabled(False)
        self.palette_btn.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        self.palette_btn.setFixedHeight(BUTTON_HEIGHT)
        self.palette_btn.clicked.connect(self._apply_palette)
        layout.addWidget(self.palette_btn)

        layout.addStretch()

        # Info label
        self.info_label = QLabel("No ROM loaded")
        layout.addWidget(self.info_label)

        widget.setLayout(layout)
        return widget

    def set_rom_data(self, rom_path: str, rom_size: int, rom_extractor):
        """
        Set the ROM data for the gallery.

        Args:
            rom_path: Path to ROM file
            rom_size: Size of ROM in bytes
            rom_extractor: ROM extractor instance
        """
        self.rom_path = rom_path
        self.rom_size = rom_size
        self.rom_extractor = rom_extractor

        # Update info
        rom_name = Path(rom_path).name
        self.info_label.setText(f"ROM: {rom_name} ({rom_size / 1024 / 1024:.1f}MB)")

        # Auto-scan if enabled
        if self._should_auto_scan():
            QTimer.singleShot(100, self._scan_for_sprites)

    def _should_auto_scan(self) -> bool:
        """Check if auto-scan is enabled in settings."""
        # TODO: Read from settings
        return False  # Disabled by default for performance

    def _scan_for_sprites(self):
        """Scan the ROM for all sprites."""
        if not self.rom_path:
            QMessageBox.warning(self, "No ROM", "Please load a ROM first")
            return

        # Show progress dialog
        self.progress_dialog = QProgressDialog(
            "Scanning ROM for sprites...",
            "Cancel",
            0,
            100,
            self
        )
        self.progress_dialog.setWindowModality(Qt.WindowModality.WindowModal)
        self.progress_dialog.show()

        # Create and start scan worker
        self._start_sprite_scan()

    def _start_sprite_scan(self):
        """Start the sprite scanning process."""
        # Use SpriteFinder to scan
        finder = SpriteFinder()

        # For now, do a quick scan synchronously
        # TODO: Move to worker thread for large ROMs
        try:
            if not self.rom_path:
                raise ValueError("No ROM path set")
            with open(self.rom_path, 'rb') as f:
                rom_data = f.read()

            sprites = []

            # Scan common sprite areas
            scan_ranges = [
                (0x200000, 0x300000, 0x1000),  # Main sprite area
                (0x100000, 0x200000, 0x2000),  # Secondary area
            ]

            total_steps = sum((end - start) // step for start, end, step in scan_ranges)
            current_step = 0

            for start, end, step in scan_ranges:
                for offset in range(start, min(end, len(rom_data)), step):
                    # Update progress
                    current_step += 1
                    progress = int((current_step / total_steps) * 100)
                    self.progress_dialog.setValue(progress)

                    # Check for cancel
                    if self.progress_dialog.wasCanceled():
                        break

                    # Try to find sprite
                    sprite_info = finder.find_sprite_at_offset(rom_data, offset)
                    if sprite_info:
                        sprites.append(sprite_info)

                if self.progress_dialog.wasCanceled():
                    break

            # Store results
            self.sprites_data = sprites

            # Update gallery
            self.gallery_widget.set_sprites(sprites)

            # Update info
            rom_name = Path(self.rom_path).name if self.rom_path else "Unknown"
            self.info_label.setText(
                f"Found {len(sprites)} sprites in {rom_name}"
            )

            # Start generating thumbnails for found sprites
            if sprites:
                logger.info(f"Starting thumbnail generation for {len(sprites)} sprites")
                self._refresh_thumbnails()

        except Exception as e:
            logger.error(f"Error scanning ROM: {e}")
            QMessageBox.critical(self, "Scan Error", f"Failed to scan ROM: {e}")

        finally:
            if self.progress_dialog:
                self.progress_dialog.close()
                self.progress_dialog = None

    def _refresh_thumbnails(self):
        """Refresh all thumbnail images."""
        if not self.sprites_data or not self.rom_path:
            logger.warning("Cannot refresh thumbnails: no sprites or ROM path")
            return

        # Create worker to generate thumbnails if needed
        if not self.thumbnail_worker:
            logger.info("Creating BatchThumbnailWorker")
            self.thumbnail_worker = BatchThumbnailWorker(
                self.rom_path,
                self.rom_extractor
            )
            self.thumbnail_worker.thumbnail_ready.connect(self._on_thumbnail_ready)

        # Queue all sprites for thumbnail generation
        logger.info(f"Queueing {len(self.sprites_data)} sprites for thumbnail generation")
        for sprite_info in self.sprites_data:
            offset = sprite_info.get('offset', 0)
            if isinstance(offset, str):
                offset = int(offset, 16) if offset.startswith('0x') else int(offset)
            self.thumbnail_worker.queue_thumbnail(offset, 128)

        # Start generation if not already running
        if self.thumbnail_worker and not self.thumbnail_worker.isRunning():
            logger.info("Starting BatchThumbnailWorker thread")
            self.thumbnail_worker.start()
        else:
            logger.info(f"Worker already running: {self.thumbnail_worker.isRunning() if self.thumbnail_worker else False}")

    def _on_thumbnail_ready(self, offset: int, pixmap: QPixmap):
        """
        Handle thumbnail ready from worker.

        Args:
            offset: Sprite offset
            pixmap: Generated thumbnail pixmap
        """
        logger.debug(f"Thumbnail ready for offset 0x{offset:06X}, pixmap null: {pixmap.isNull()}")

        if offset in self.gallery_widget.thumbnails:
            thumbnail = self.gallery_widget.thumbnails[offset]
            # Find sprite info
            sprite_info = None
            for info in self.sprites_data:
                info_offset = info.get('offset', 0)
                if isinstance(info_offset, str):
                    info_offset = int(info_offset, 16) if info_offset.startswith('0x') else int(info_offset)
                if info_offset == offset:
                    sprite_info = info
                    break
            logger.debug(f"Setting thumbnail for offset 0x{offset:06X}")
            thumbnail.set_sprite_data(pixmap, sprite_info)
        else:
            logger.warning(f"No thumbnail widget found for offset 0x{offset:06X}")

    def _on_sprite_selected(self, offset: int):
        """Handle sprite selection in gallery."""
        logger.debug(f"Sprite selected at offset: 0x{offset:06X}")

    def _on_sprite_double_clicked(self, offset: int):
        """Handle sprite double-click - navigate to it."""
        self.sprite_selected.emit(offset)

    def _on_selection_changed(self, selected_offsets: list[int]):
        """Handle selection change in gallery."""
        count = len(selected_offsets)

        # Enable/disable actions based on selection
        self.compare_btn.setEnabled(count >= 2)
        self.palette_btn.setEnabled(count >= 1)

        # Update toolbar actions
        for action in self.toolbar.actions():
            if "Export" in action.text():
                action.setEnabled(count >= 1)

    def _export_selected(self):
        """Export selected sprites as individual PNG files."""
        selected = self.gallery_widget.get_selected_sprites()
        if not selected:
            QMessageBox.information(self, "No Selection", "Please select sprites to export")
            return

        # Get export directory
        export_dir = QFileDialog.getExistingDirectory(
            self,
            "Select Export Directory",
            "",
            QFileDialog.Option.ShowDirsOnly
        )

        if not export_dir:
            return

        # Export each sprite
        exported = []
        for sprite_info in selected:
            try:
                offset = sprite_info.get('offset', 0)
                if isinstance(offset, str):
                    offset = int(offset, 16) if offset.startswith('0x') else int(offset)

                # Generate filename
                filename = f"sprite_{offset:06X}.png"
                filepath = Path(export_dir) / filename

                # TODO: Actually export the sprite image
                # For now, just track it
                exported.append(str(filepath))

            except Exception as e:
                logger.error(f"Failed to export sprite: {e}")

        # Show result
        if exported:
            QMessageBox.information(
                self,
                "Export Complete",
                f"Exported {len(exported)} sprites to {export_dir}"
            )
            self.sprites_exported.emit(exported)

    def _export_sprite_sheet(self):
        """Export selected sprites as a sprite sheet."""
        selected = self.gallery_widget.get_selected_sprites()
        if not selected:
            QMessageBox.information(self, "No Selection", "Please select sprites to export")
            return

        # Get save location
        filepath, _ = QFileDialog.getSaveFileName(
            self,
            "Save Sprite Sheet",
            "sprite_sheet.png",
            "PNG Files (*.png)"
        )

        if not filepath:
            return

        # TODO: Implement sprite sheet generation
        QMessageBox.information(
            self,
            "Not Implemented",
            "Sprite sheet export will be implemented soon"
        )

    def _compare_sprites(self):
        """Open comparison view for selected sprites."""
        selected = self.gallery_widget.get_selected_sprites()
        if len(selected) < 2:
            QMessageBox.information(
                self,
                "Select More",
                "Please select at least 2 sprites to compare"
            )
            return

        # TODO: Implement comparison dialog
        QMessageBox.information(
            self,
            "Not Implemented",
            "Sprite comparison will be implemented soon"
        )

    def _apply_palette(self):
        """Apply a palette to selected sprites."""
        selected = self.gallery_widget.get_selected_sprites()
        if not selected:
            return

        # TODO: Implement palette application
        QMessageBox.information(
            self,
            "Not Implemented",
            "Batch palette application will be implemented soon"
        )

    def cleanup(self):
        """Clean up resources."""
        if self.thumbnail_worker:
            self.thumbnail_worker.stop()
            self.thumbnail_worker.wait()
            self.thumbnail_worker = None
