"""
Manual Offset Control Dialog

A dedicated window for ROM offset exploration with enhanced controls and visualization.
"""

import json
import os
from datetime import datetime
from typing import TYPE_CHECKING, ClassVar, override

if TYPE_CHECKING:
    from spritepal.core.managers.extraction_manager import ExtractionManager
    from spritepal.core.rom_extractor import ROMExtractor

from PyQt6.QtCore import QRect, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import (
    QCloseEvent,
    QColor,
    QHideEvent,
    QKeyEvent,
    QMouseEvent,
    QPainter,
    QPaintEvent,
)
from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSizePolicy,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from spritepal.ui.rom_extraction.widgets.manual_offset_widget import ManualOffsetWidget
from spritepal.ui.rom_extraction.workers import (
    RangeScanWorker,
    SpritePreviewWorker,
    SpriteSearchWorker,
)
from spritepal.ui.styles import (
    get_dialog_button_box_style,
    get_panel_style,
    get_preview_panel_style,
)
from spritepal.ui.widgets.sprite_preview_widget import SpritePreviewWidget
from spritepal.utils.logging_config import get_logger

logger = get_logger(__name__)


class ROMMapWidget(QWidget):
    """Visual representation of ROM with sprite locations"""

    offset_clicked: pyqtSignal = pyqtSignal(int)  # Emitted when user clicks on the ROM map

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.rom_size: int = 0x400000  # Default 4MB
        self.current_offset: int = 0
        self.found_sprites: list[tuple[int, float]] = []  # List of (offset, quality) tuples
        self.setMinimumHeight(60)
        self.setMaximumHeight(80)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        # Enable mouse tracking for hover effects
        self.setMouseTracking(True)
        self.hover_offset: int | None = None

    def set_rom_size(self, size: int):
        """Update the ROM size"""
        self.rom_size = size
        self.update()

    def set_current_offset(self, offset: int):
        """Update the current offset position"""
        self.current_offset = offset
        self.update()

    def add_found_sprite(self, offset: int, quality: float = 1.0):
        """Add a found sprite location"""
        self.found_sprites.append((offset, quality))
        self.update()

    def clear_sprites(self):
        """Clear all found sprite markers"""
        self.found_sprites = []
        self.update()

    @override
    def paintEvent(self, a0: QPaintEvent | None):
        """Paint the ROM map visualization"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Get widget dimensions
        width = self.width()
        height = self.height()

        # Draw background
        painter.fillRect(0, 0, width, height, Qt.GlobalColor.black)

        # Draw ROM regions
        # Common sprite areas (based on typical SNES ROM layout)
        regions = [
            (0x000000, 0x100000, "#2b2b2b", "Low ROM"),
            (0x100000, 0x200000, "#3b3b3b", "Mid ROM"),
            (0x200000, 0x300000, "#4b4b4b", "High ROM"),
            (0x300000, 0x400000, "#5b5b5b", "Extended ROM"),
        ]

        for start, end, color, _label in regions:
            if start < self.rom_size:
                x_start = int((start / self.rom_size) * width)
                x_end = int((min(end, self.rom_size) / self.rom_size) * width)
                painter.fillRect(x_start, 20, x_end - x_start, height - 40, QColor(color))

        # Draw found sprites
        painter.setPen(Qt.PenStyle.NoPen)
        for offset, quality in self.found_sprites:
            if offset < self.rom_size:
                x = int((offset / self.rom_size) * width)
                # Color based on quality (green = high, yellow = medium, red = low)
                if quality > 0.8:
                    painter.setBrush(Qt.GlobalColor.green)
                elif quality > 0.5:
                    painter.setBrush(Qt.GlobalColor.yellow)
                else:
                    painter.setBrush(Qt.GlobalColor.red)
                painter.drawRect(x - 2, 15, 4, height - 30)

        # Draw current position indicator
        if self.current_offset < self.rom_size:
            x = int((self.current_offset / self.rom_size) * width)
            painter.setPen(Qt.GlobalColor.cyan)
            painter.setPen(painter.pen())
            painter.pen().setWidth(2)
            painter.drawLine(x, 0, x, height)

            # Draw position label
            painter.setPen(Qt.GlobalColor.white)
            offset_text = f"0x{self.current_offset:06X}"
            painter.drawText(max(5, min(x - 30, width - 65)), 12, offset_text)

        # Draw scale markers
        painter.setPen(Qt.GlobalColor.gray)
        for i in range(5):  # 0%, 25%, 50%, 75%, 100%
            x = int((i / 4) * width)
            painter.drawLine(x, height - 10, x, height)
            # Draw MB labels
            mb_value = int((i / 4) * (self.rom_size / 0x100000))
            painter.drawText(x - 15, height - 12, f"{mb_value}MB")

    @override
    def mousePressEvent(self, a0: QMouseEvent | None):
        """Handle mouse clicks on the ROM map"""
        if a0 and a0.button() == Qt.MouseButton.LeftButton:
            # Calculate offset from click position
            offset = int((a0.position().x() / self.width()) * self.rom_size)
            offset = max(0, min(offset, self.rom_size - 1))
            self.offset_clicked.emit(offset)

    @override
    def mouseMoveEvent(self, a0: QMouseEvent | None):
        """Handle mouse hover to show offset preview"""
        if a0:
            self.hover_offset = int((a0.position().x() / self.width()) * self.rom_size)
            self.setToolTip(f"Click to jump to 0x{self.hover_offset:06X}")


class RangeScanDialog(QDialog):
    """Dialog for selecting range scanning parameters"""

    def __init__(self, current_offset: int, rom_size: int, parent: QWidget | None = None):
        super().__init__(parent)
        self.current_offset = current_offset
        self.rom_size = rom_size
        self.setWindowTitle("Range Scan Configuration")
        self.setModal(True)
        self.resize(400, 200)

        layout = QVBoxLayout()

        # Form layout for parameters
        form_layout = QFormLayout()

        # Range size selection
        self.range_combo = QComboBox()
        self.range_combo.addItems([
            "±1 KB (±0x400)",
            "±4 KB (±0x1000)",
            "±16 KB (±0x4000)",
            "±64 KB (±0x10000)",
            "±256 KB (±0x40000)"
        ])
        self.range_combo.setCurrentIndex(2)  # Default to ±16KB
        form_layout.addRow("Scan Range:", self.range_combo)

        # Current offset display
        offset_label = QLabel(f"0x{current_offset:06X}")
        offset_label.setStyleSheet("font-family: monospace; font-weight: bold;")
        form_layout.addRow("Center Offset:", offset_label)

        # Range preview
        self.range_label = QLabel()
        self.range_label.setStyleSheet("color: #666; font-family: monospace;")
        form_layout.addRow("Scan Range:", self.range_label)

        layout.addLayout(form_layout)

        # Update range display when selection changes
        self.range_combo.currentIndexChanged.connect(self._update_range_display)
        self._update_range_display()

        # Buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

        self.setLayout(layout)

    def _update_range_display(self):
        """Update the range display based on current selection"""
        range_sizes = [0x400, 0x1000, 0x4000, 0x10000, 0x40000]
        range_size = range_sizes[self.range_combo.currentIndex()]

        start_offset = max(0, self.current_offset - range_size)
        end_offset = min(self.rom_size - 1, self.current_offset + range_size)

        self.range_label.setText(f"0x{start_offset:06X} - 0x{end_offset:06X}")

    def get_range(self) -> tuple[int, int]:
        """Get the selected scan range"""
        range_sizes = [0x400, 0x1000, 0x4000, 0x10000, 0x40000]
        range_size = range_sizes[self.range_combo.currentIndex()]

        start_offset = max(0, self.current_offset - range_size)
        end_offset = min(self.rom_size - 1, self.current_offset + range_size)

        return start_offset, end_offset


class ManualOffsetDialog(QDialog):
    """Dialog window for manual ROM offset control with enhanced features"""

    # Signals
    offset_changed: pyqtSignal = pyqtSignal(int)  # Current offset changed
    sprite_found: pyqtSignal = pyqtSignal(int, str)  # Sprite found at offset with name

    # Singleton instance
    _instance: ClassVar["ManualOffsetDialog | None"] = None

    @classmethod
    def get_instance(cls, parent: "QWidget | None" = None) -> "ManualOffsetDialog":
        """Get or create singleton instance"""
        if cls._instance is None:
            cls._instance = cls(parent)
        return cls._instance

    def __init__(self, parent: "QWidget | None" = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Manual Offset Control - SpritePal")
        self.setMinimumSize(1000, 600)  # Reduced minimum height
        self.resize(1200, 700)  # Reduced default height

        # State
        self.rom_path: str = ""
        self.rom_size: int = 0x400000  # Default 4MB
        self._preview_timer: QTimer = QTimer()
        self._preview_timer.setSingleShot(True)
        self._preview_timer.timeout.connect(self._update_preview)

        # Manager references (set by set_rom_data)
        self.extraction_manager: ExtractionManager | None = None
        self.rom_extractor: ROMExtractor | None = None

        # Worker references
        self.preview_worker: SpritePreviewWorker | None = None
        self.search_worker: SpriteSearchWorker | None = None
        self.range_scan_worker: RangeScanWorker | None = None

        # Scanning state
        self.scan_progress: QProgressBar | None = None
        self.found_sprites: list[tuple[int, float]] = []  # (offset, quality) pairs
        self.is_scanning: bool = False

        # Fullscreen state
        self._is_fullscreen: bool = False
        self._normal_geometry: QRect | None = None

        self._setup_ui()
        self._connect_signals()

        # Make dialog non-modal so it can stay open alongside main window
        self.setModal(False)

        # Add window flags to keep it on top if desired
        self.setWindowFlags(
            self.windowFlags() |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )

    def _setup_ui(self):
        """Initialize the user interface"""
        main_layout = QVBoxLayout()
        main_layout.setSpacing(5)  # Reduced from 10
        main_layout.setContentsMargins(5, 5, 5, 5)  # Add smaller margins

        # ROM Map visualization at the top - more compact
        rom_map_group = QWidget()
        rom_map_group.setStyleSheet(get_panel_style())
        rom_map_layout = QVBoxLayout()
        rom_map_layout.setContentsMargins(8, 6, 8, 6)  # Reduced from 10,10,10,10
        rom_map_layout.setSpacing(3)  # Tighter spacing

        rom_map_label = QLabel("ROM Overview")
        rom_map_label.setStyleSheet("font-weight: bold; font-size: 12px; margin-bottom: 2px;")  # Smaller font and margin
        rom_map_layout.addWidget(rom_map_label)

        self.rom_map: ROMMapWidget = ROMMapWidget()
        rom_map_layout.addWidget(self.rom_map)

        rom_map_group.setLayout(rom_map_layout)
        main_layout.addWidget(rom_map_group)

        # Main content splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(6)  # Thinner splitter handle

        # Left panel - Controls
        left_panel = QWidget()
        left_layout = QVBoxLayout()
        left_layout.setContentsMargins(3, 3, 3, 3)  # Small margins instead of 0
        left_layout.setSpacing(6)  # Tighter spacing between controls

        # Manual offset widget (reusing existing widget)
        self.offset_widget: ManualOffsetWidget = ManualOffsetWidget()
        left_layout.addWidget(self.offset_widget)

        # Additional controls group
        extra_controls = QWidget()
        extra_controls.setStyleSheet(get_panel_style())
        extra_layout = QVBoxLayout()
        extra_layout.setContentsMargins(8, 6, 8, 6)  # Reduced padding
        extra_layout.setSpacing(4)  # Tighter spacing

        extra_label = QLabel("Enhanced Controls")
        extra_label.setStyleSheet("font-weight: bold; font-size: 12px; margin-bottom: 4px;")  # Smaller and tighter
        extra_layout.addWidget(extra_label)

        # Scan controls
        scan_row = QHBoxLayout()
        self.scan_range_btn: QPushButton = QPushButton("Scan Range")
        self.scan_range_btn.setToolTip("Scan a range around current offset for sprites")
        scan_row.addWidget(self.scan_range_btn)

        self.scan_all_btn: QPushButton = QPushButton("Scan Entire ROM")
        self.scan_all_btn.setToolTip("Scan the entire ROM for sprite locations (slow)")
        scan_row.addWidget(self.scan_all_btn)
        extra_layout.addLayout(scan_row)

        # Scan control buttons (pause/stop)
        control_row = QHBoxLayout()
        self.pause_btn: QPushButton = QPushButton("Pause")
        self.pause_btn.setToolTip("Pause or resume the current scan")
        self.pause_btn.setVisible(False)  # Hidden by default
        control_row.addWidget(self.pause_btn)

        self.stop_btn: QPushButton = QPushButton("Stop")
        self.stop_btn.setToolTip("Stop the current scan")
        self.stop_btn.setVisible(False)  # Hidden by default
        control_row.addWidget(self.stop_btn)

        control_row.addStretch()  # Push buttons to left
        extra_layout.addLayout(control_row)

        # Export/Import controls
        io_row = QHBoxLayout()
        self.export_btn: QPushButton = QPushButton("Export Offsets")
        self.export_btn.setToolTip("Export found sprite offsets to file")
        io_row.addWidget(self.export_btn)

        self.import_btn: QPushButton = QPushButton("Import Offsets")
        self.import_btn.setToolTip("Import sprite offsets from file")
        io_row.addWidget(self.import_btn)
        extra_layout.addLayout(io_row)

        extra_controls.setLayout(extra_layout)
        left_layout.addWidget(extra_controls)

        # Status panel
        status_panel = QWidget()
        status_panel.setStyleSheet(get_panel_style())
        status_layout = QVBoxLayout()
        status_layout.setContentsMargins(8, 6, 8, 6)  # Reduced padding
        status_layout.setSpacing(3)  # Tighter spacing

        status_label = QLabel("Detection Status")
        status_label.setStyleSheet("font-weight: bold; font-size: 12px; margin-bottom: 3px;")  # Smaller and tighter
        status_layout.addWidget(status_label)

        self.detection_info: QLabel = QLabel("Ready to search for sprites")
        self.detection_info.setWordWrap(True)
        self.detection_info.setStyleSheet("color: #cccccc;")
        status_layout.addWidget(self.detection_info)

        status_panel.setLayout(status_layout)
        left_layout.addWidget(status_panel)

        # Smaller stretch to reduce empty space
        left_layout.addStretch(1)  # Minimal stretch factor
        left_panel.setLayout(left_layout)
        left_panel.setMinimumWidth(500)
        left_panel.setMaximumWidth(600)

        # Right panel - Preview
        right_panel = QWidget()
        right_layout = QVBoxLayout()
        right_layout.setContentsMargins(3, 3, 3, 3)  # Small margins
        right_layout.setSpacing(4)  # Tighter spacing

        # Sprite preview
        self.preview_widget: SpritePreviewWidget = SpritePreviewWidget("Live Preview")
        self.preview_widget.setStyleSheet(get_preview_panel_style())
        right_layout.addWidget(self.preview_widget)

        right_panel.setLayout(right_layout)

        # Add panels to splitter
        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setStretchFactor(0, 0)  # Fixed size for controls
        splitter.setStretchFactor(1, 1)  # Preview expands
        splitter.setSizes([500, 400])  # Better proportions for more compact layout

        main_layout.addWidget(splitter)

        # Dialog buttons
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        button_box.setStyleSheet(get_dialog_button_box_style())

        # Add custom buttons
        self.apply_btn: QPushButton | None = button_box.addButton("Apply Offset", QDialogButtonBox.ButtonRole.AcceptRole)
        if self.apply_btn:
            self.apply_btn.setToolTip("Use the current offset for extraction")

        button_box.rejected.connect(self.hide)  # Hide instead of close to maintain state
        main_layout.addWidget(button_box)

        self.setLayout(main_layout)

    def _connect_signals(self):
        """Connect internal signals"""
        # Connect offset widget signals
        self.offset_widget.offset_changed.connect(self._on_offset_changed)
        self.offset_widget.find_next_clicked.connect(self._find_next_sprite)
        self.offset_widget.find_prev_clicked.connect(self._find_prev_sprite)

        # Connect ROM map
        self.rom_map.offset_clicked.connect(self._on_map_clicked)

        # Connect buttons
        if self.apply_btn:
            self.apply_btn.clicked.connect(self._apply_offset)
        self.scan_range_btn.clicked.connect(self._scan_range)
        self.scan_all_btn.clicked.connect(self._scan_all)
        self.pause_btn.clicked.connect(self._toggle_pause)
        self.stop_btn.clicked.connect(self._stop_scan)
        self.export_btn.clicked.connect(self._export_offsets)
        self.import_btn.clicked.connect(self._import_offsets)

    def set_rom_data(self, rom_path: str, rom_size: int, extraction_manager: "ExtractionManager") -> None:
        """Set ROM data for the dialog"""
        self.rom_path = rom_path
        self.rom_size = rom_size
        self.extraction_manager = extraction_manager
        self.rom_extractor = extraction_manager.get_rom_extractor()

        # Update widgets
        self.offset_widget.set_rom_size(rom_size)
        self.rom_map.set_rom_size(rom_size)

        # Update window title with ROM name
        if rom_path:
            rom_name = os.path.basename(rom_path)
            self.setWindowTitle(f"Manual Offset Control - {rom_name}")

    def get_current_offset(self) -> int:
        """Get the current offset value"""
        return self.offset_widget.get_current_offset()

    def set_offset(self, offset: int):
        """Set the current offset"""
        self.offset_widget.set_offset(offset)

    def _on_offset_changed(self, offset: int):
        """Handle offset changes from the widget"""
        # Update ROM map
        self.rom_map.set_current_offset(offset)

        # Schedule preview update
        self._preview_timer.stop()
        self._preview_timer.start(50)  # 50ms delay

        # Emit signal for external listeners
        self.offset_changed.emit(offset)

    def _on_map_clicked(self, offset: int):
        """Handle clicks on the ROM map"""
        self.offset_widget.set_offset(offset)

    def _update_preview(self):
        """Update the sprite preview"""
        if not self.rom_path:
            return

        offset = self.get_current_offset()
        self.detection_info.setText(f"Loading preview for 0x{offset:06X}...")

        # Clean up any existing preview worker
        if self.preview_worker:
            self.preview_worker.quit()
            self.preview_worker.wait()

        # Try to find sprite configuration for this offset
        sprite_config = None
        sprite_name = f"manual_0x{offset:X}"

        # Look up known sprite configurations to see if this offset matches
        try:
            if self.extraction_manager and self.rom_path:
                sprite_locations = self.extraction_manager.get_known_sprite_locations(self.rom_path)
                if sprite_locations:
                    for name, pointer in sprite_locations.items():
                        if pointer.offset == offset:
                            sprite_config = pointer
                            sprite_name = name
                            logger.debug(f"Found matching sprite config: {name} at 0x{offset:06X}")
                            break
        except Exception as e:
            logger.debug(f"Error looking up sprite config: {e}")

        # Create and start preview worker with sprite config if found
        self.preview_worker = SpritePreviewWorker(
            self.rom_path, offset, sprite_name, self.rom_extractor, sprite_config
        )
        self.preview_worker.preview_ready.connect(self._on_preview_ready)
        self.preview_worker.preview_error.connect(self._on_preview_error)
        self.preview_worker.start()

    def _on_preview_ready(self, tile_data: bytes, width: int, height: int, sprite_name: str):
        """Handle preview data ready"""
        self.preview_widget.load_sprite_from_4bpp(tile_data, width, height, sprite_name)
        self.detection_info.setText(f"Sprite found at 0x{self.get_current_offset():06X}")

    def _on_preview_error(self, error_msg: str):
        """Handle preview error"""
        self.preview_widget.clear()
        self.preview_widget.info_label.setText("No sprite found")

        # Update status with user-friendly message
        offset = self.get_current_offset()
        if "decompression" in error_msg.lower() or "hal" in error_msg.lower():
            self.detection_info.setText(
                f"No sprite data at 0x{offset:06X}. Use navigation to search."
            )
        else:
            self.detection_info.setText(
                f"Cannot read offset 0x{offset:06X}: {error_msg}"
            )

    def _find_next_sprite(self):
        """Find next sprite offset"""
        if not self.rom_path:
            return

        current_offset = self.get_current_offset()
        step = self.offset_widget.get_step_size()

        self.detection_info.setText(f"Searching forward from 0x{current_offset:06X}...")
        self.offset_widget.set_navigation_enabled(False)

        # Clean up any existing search worker
        if self.search_worker:
            self.search_worker.quit()
            self.search_worker.wait()

        # Create worker to search for next sprite
        self.search_worker = SpriteSearchWorker(
            self.rom_path, current_offset, step, self.rom_size, self.rom_extractor, forward=True
        )
        self.search_worker.sprite_found.connect(self._on_sprite_found)
        self.search_worker.search_complete.connect(self._on_search_complete)
        self.search_worker.start()

    def _find_prev_sprite(self):
        """Find previous sprite offset"""
        if not self.rom_path:
            return

        current_offset = self.get_current_offset()
        step = self.offset_widget.get_step_size()

        self.detection_info.setText(f"Searching backward from 0x{current_offset:06X}...")
        self.offset_widget.set_navigation_enabled(False)

        # Clean up any existing search worker
        if self.search_worker:
            self.search_worker.quit()
            self.search_worker.wait()

        # Create worker to search for previous sprite
        self.search_worker = SpriteSearchWorker(
            self.rom_path, current_offset, step, self.rom_size, self.rom_extractor, forward=False
        )
        self.search_worker.sprite_found.connect(self._on_sprite_found)
        self.search_worker.search_complete.connect(self._on_search_complete)
        self.search_worker.start()

    def _on_sprite_found(self, offset: int, quality: float):
        """Handle sprite found during search"""
        self.offset_widget.set_offset(offset)
        self.add_found_sprite(offset, quality)
        self.detection_info.setText(
            f"Found sprite at 0x{offset:06X} (quality: {quality:.2f})"
        )

    def _on_search_complete(self, found: bool):
        """Handle search completion"""
        self.offset_widget.set_navigation_enabled(True)

        if not found:
            self.detection_info.setText(
                "No valid sprites found in search range. Try a different area."
            )

    def _apply_offset(self):
        """Apply the current offset and close dialog"""
        offset = self.get_current_offset()
        self.sprite_found.emit(offset, f"manual_0x{offset:X}")
        self.hide()

    def _scan_range(self):
        """Scan a range around current offset"""
        if not self.rom_path or not self.rom_extractor:
            self.detection_info.setText("No ROM loaded")
            return

        if self.is_scanning:
            self.detection_info.setText("Scan already in progress")
            return

        current_offset = self.get_current_offset()

        # Show range selection dialog
        dialog = RangeScanDialog(current_offset, self.rom_size, self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        start_offset, end_offset = dialog.get_range()

        # Confirm the scan
        range_kb = (end_offset - start_offset) // 1024
        result = QMessageBox.question(
            self,
            "Confirm Range Scan",
            f"Scan range 0x{start_offset:06X} - 0x{end_offset:06X} ({range_kb} KB)?\n\n"
            f"This may take a few moments depending on the range size.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes
        )

        if result != QMessageBox.StandardButton.Yes:
            return

        self._start_range_scan(start_offset, end_offset)

    def _start_range_scan(self, start_offset: int, end_offset: int):
        """Start scanning a specific range"""
        self.is_scanning = True
        self.found_sprites.clear()

        # Clear existing sprites from ROM map
        self.rom_map.clear_sprites()

        # Add progress bar to status area
        if not self.scan_progress:
            self.scan_progress = QProgressBar()
            self.scan_progress.setVisible(False)
            # Insert progress bar in the status panel (after detection_info)
            status_layout = self.detection_info.parent().layout()
            status_layout.addWidget(self.scan_progress)

        self.scan_progress.setVisible(True)
        self.scan_progress.setRange(start_offset, end_offset)
        self.scan_progress.setValue(start_offset)

        # Update status
        range_kb = (end_offset - start_offset) // 1024
        self.detection_info.setText(f"Scanning {range_kb} KB range...")

        # Disable scan buttons during operation and show control buttons
        self.scan_range_btn.setEnabled(False)
        self.scan_all_btn.setEnabled(False)
        self.pause_btn.setVisible(True)
        self.stop_btn.setVisible(True)
        self.pause_btn.setText("Pause")  # Reset pause button text

        # Create range scanning worker
        self._start_range_scan_worker(start_offset, end_offset)

    def _start_range_scan_worker(self, start_offset: int, end_offset: int):
        """Start the worker thread for range scanning"""
        # Clean up existing range scan worker
        if self.range_scan_worker:
            self.range_scan_worker.quit()
            self.range_scan_worker.wait()

        # Create range scan worker with proper bounds
        step_size = 0x100  # 256 byte steps for comprehensive scanning
        self.range_scan_worker = RangeScanWorker(
            self.rom_path, start_offset, end_offset, step_size, self.rom_extractor
        )

        # Connect signals
        self.range_scan_worker.sprite_found.connect(self._on_range_sprite_found)
        self.range_scan_worker.progress_update.connect(self._on_range_scan_progress)
        self.range_scan_worker.scan_complete.connect(self._on_range_scan_complete)
        self.range_scan_worker.scan_paused.connect(self._on_scan_paused)
        self.range_scan_worker.scan_resumed.connect(self._on_scan_resumed)
        self.range_scan_worker.scan_stopped.connect(self._on_scan_stopped)

        # Start the worker
        self.range_scan_worker.start()

    def _on_range_sprite_found(self, offset: int, quality: float):
        """Handle sprite found during range scan"""
        # Add to our found sprites list
        self.found_sprites.append((offset, quality))

        # Add to ROM map visualization
        self.rom_map.add_found_sprite(offset, quality)

        # Update progress
        if self.scan_progress:
            self.scan_progress.setValue(offset)

        # Update status
        count = len(self.found_sprites)
        self.detection_info.setText(f"Scanning... Found {count} sprite{'s' if count != 1 else ''}")

    def _on_range_scan_progress(self, current_offset: int):
        """Handle progress updates during range scan"""
        # Update progress bar
        if self.scan_progress:
            self.scan_progress.setValue(current_offset)

    def _on_range_scan_complete(self, found: bool):
        """Handle range scan completion"""
        self.is_scanning = False

        # Hide progress bar
        if self.scan_progress:
            self.scan_progress.setVisible(False)

        # Re-enable scan buttons and hide control buttons
        self.scan_range_btn.setEnabled(True)
        self.scan_all_btn.setEnabled(True)
        self.pause_btn.setVisible(False)
        self.stop_btn.setVisible(False)

        # Update final status
        sprite_count = len(self.found_sprites)
        if sprite_count > 0:
            self.detection_info.setText(f"Range scan complete: {sprite_count} sprites found")
        else:
            self.detection_info.setText("Range scan complete: No sprites found")

    def _toggle_pause(self):
        """Toggle pause/resume for the current scan"""
        if not self.range_scan_worker:
            return

        if self.range_scan_worker.is_paused():
            self.range_scan_worker.resume_scan()
        else:
            self.range_scan_worker.pause_scan()

    def _stop_scan(self):
        """Stop the current scan"""
        if self.range_scan_worker:
            self.range_scan_worker.stop_scan()

    def _on_scan_paused(self):
        """Handle scan paused signal"""
        self.pause_btn.setText("Resume")
        self.detection_info.setText("Scan paused - click Resume to continue")

    def _on_scan_resumed(self):
        """Handle scan resumed signal"""
        self.pause_btn.setText("Pause")
        count = len(self.found_sprites)
        self.detection_info.setText(f"Scanning... Found {count} sprite{'s' if count != 1 else ''}")

    def _on_scan_stopped(self):
        """Handle scan stopped signal"""
        self.is_scanning = False

        # Hide progress bar
        if self.scan_progress:
            self.scan_progress.setVisible(False)

        # Re-enable scan buttons and hide control buttons
        self.scan_range_btn.setEnabled(True)
        self.scan_all_btn.setEnabled(True)
        self.pause_btn.setVisible(False)
        self.stop_btn.setVisible(False)

        # Update status
        sprite_count = len(self.found_sprites)
        self.detection_info.setText(f"Scan stopped by user: {sprite_count} sprites found")

    def _scan_all(self):
        """Scan entire ROM"""
        if not self.rom_path or not self.rom_extractor:
            self.detection_info.setText("No ROM loaded")
            return

        if self.is_scanning:
            self.detection_info.setText("Scan already in progress")
            return

        # Warn about performance impact
        rom_mb = self.rom_size // (1024 * 1024)
        result = QMessageBox.question(
            self,
            "Confirm Full ROM Scan",
            f"Scan entire ROM ({rom_mb} MB)?\n\n"
            f"This will scan the full ROM for sprite data and may take several minutes.\n"
            f"The UI will remain responsive during scanning.\n\n"
            f"Continue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No  # Default to No for safety
        )

        if result != QMessageBox.StandardButton.Yes:
            return

        # Start full ROM scan
        self._start_range_scan(0, self.rom_size - 1)

    def _export_offsets(self):
        """Export found offsets to file"""
        if not self.found_sprites:
            QMessageBox.information(
                self,
                "No Data to Export",
                "No sprite offsets found. Run a scan first to find sprites.",
                QMessageBox.StandardButton.Ok
            )
            return

        # Get save file path
        default_name = f"sprite_offsets_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Sprite Offsets",
            default_name,
            "JSON Files (*.json);;All Files (*)"
        )

        if not file_path:
            return

        try:
            # Prepare export data
            export_data = {
                "metadata": {
                    "rom_path": self.rom_path,
                    "rom_size": self.rom_size,
                    "export_timestamp": datetime.now().isoformat(),
                    "spritepal_version": "1.0.0",
                    "total_sprites": len(self.found_sprites)
                },
                "sprites": [
                    {
                        "offset": f"0x{offset:06X}",
                        "offset_decimal": offset,
                        "quality": round(quality, 3),
                        "name": f"sprite_{i+1:03d}_0x{offset:06X}"
                    }
                    for i, (offset, quality) in enumerate(self.found_sprites)
                ]
            }

            # Write to file
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)

            # Success message
            sprite_count = len(self.found_sprites)
            self.detection_info.setText(f"Exported {sprite_count} sprite offsets to {os.path.basename(file_path)}")

            QMessageBox.information(
                self,
                "Export Successful",
                f"Successfully exported {sprite_count} sprite offsets to:\n{file_path}",
                QMessageBox.StandardButton.Ok
            )

        except Exception as e:
            error_msg = f"Failed to export offsets: {e}"
            self.detection_info.setText(error_msg)
            QMessageBox.critical(
                self,
                "Export Failed",
                error_msg,
                QMessageBox.StandardButton.Ok
            )

    def _import_offsets(self):
        """Import offsets from file"""
        # Get file path
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Import Sprite Offsets",
            "",
            "JSON Files (*.json);;All Files (*)"
        )

        if not file_path:
            return

        try:
            # Read and parse JSON file
            with open(file_path, encoding="utf-8") as f:
                import_data = json.load(f)

            # Validate file format
            if not isinstance(import_data, dict) or "sprites" not in import_data:
                raise ValueError("Invalid file format: missing 'sprites' key")

            sprites_data = import_data["sprites"]
            if not isinstance(sprites_data, list):
                raise ValueError("Invalid file format: 'sprites' must be a list")

            # Check ROM compatibility if metadata is present
            if "metadata" in import_data:
                metadata = import_data["metadata"]
                if "rom_size" in metadata and metadata["rom_size"] != self.rom_size:
                    result = QMessageBox.question(
                        self,
                        "ROM Size Mismatch",
                        f"The imported data is from a ROM of size {metadata['rom_size']} bytes,\n"
                        f"but current ROM is {self.rom_size} bytes.\n\n"
                        f"Import anyway? Some offsets may be invalid.",
                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                        QMessageBox.StandardButton.No
                    )
                    if result != QMessageBox.StandardButton.Yes:
                        return

            # Clear existing sprites
            self.found_sprites.clear()
            self.rom_map.clear_sprites()

            # Import sprites
            imported_count = 0
            skipped_count = 0

            for sprite_data in sprites_data:
                try:
                    # Parse offset (support both hex string and decimal)
                    if "offset_decimal" in sprite_data:
                        offset = int(sprite_data["offset_decimal"])
                    elif "offset" in sprite_data:
                        offset_str = sprite_data["offset"]
                        if offset_str.startswith("0x"):
                            offset = int(offset_str, 16)
                        else:
                            offset = int(offset_str)
                    else:
                        continue

                    # Validate offset is within ROM bounds
                    if offset < 0 or offset >= self.rom_size:
                        skipped_count += 1
                        continue

                    # Get quality (default to 1.0 if not present)
                    quality = float(sprite_data.get("quality", 1.0))

                    # Add to found sprites
                    self.found_sprites.append((offset, quality))
                    self.rom_map.add_found_sprite(offset, quality)
                    imported_count += 1

                except (ValueError, KeyError):
                    skipped_count += 1
                    continue

            # Update status
            if imported_count > 0:
                status_msg = f"Imported {imported_count} sprite offsets"
                if skipped_count > 0:
                    status_msg += f" ({skipped_count} skipped)"
                self.detection_info.setText(status_msg)

                QMessageBox.information(
                    self,
                    "Import Successful",
                    f"Successfully imported {imported_count} sprite offsets from:\n{os.path.basename(file_path)}\n\n"
                    f"{skipped_count} entries were skipped due to invalid data or out-of-bounds offsets.",
                    QMessageBox.StandardButton.Ok
                )
            else:
                self.detection_info.setText("No valid sprite offsets found in file")
                QMessageBox.warning(
                    self,
                    "No Data Imported",
                    "No valid sprite offsets were found in the file.",
                    QMessageBox.StandardButton.Ok
                )

        except json.JSONDecodeError as e:
            error_msg = f"Invalid JSON file: {e}"
            self.detection_info.setText(error_msg)
            QMessageBox.critical(
                self,
                "Import Failed",
                f"Failed to parse JSON file:\n{error_msg}",
                QMessageBox.StandardButton.Ok
            )
        except Exception as e:
            error_msg = f"Failed to import offsets: {e}"
            self.detection_info.setText(error_msg)
            QMessageBox.critical(
                self,
                "Import Failed",
                error_msg,
                QMessageBox.StandardButton.Ok
            )

    def add_found_sprite(self, offset: int, quality: float = 1.0):
        """Add a found sprite to the visualization"""
        self.rom_map.add_found_sprite(offset, quality)
        self.offset_widget.add_found_sprite(offset)

    @override
    def keyPressEvent(self, a0: QKeyEvent | None):
        """Handle keyboard shortcuts"""
        # Let the offset widget handle its shortcuts first
        if a0:
            self.offset_widget.keyPressEvent(a0)

        # Dialog-specific shortcuts
        if a0:
            if a0.key() == Qt.Key.Key_Escape:
                if self._is_fullscreen:
                    self._toggle_fullscreen()
                    a0.accept()
                else:
                    self.hide()
                    a0.accept()
            elif a0.key() == Qt.Key.Key_F11:
                self._toggle_fullscreen()
                a0.accept()
            elif (a0.key() == Qt.Key.Key_Return or a0.key() == Qt.Key.Key_Enter) and a0.modifiers() == Qt.KeyboardModifier.NoModifier:
                self._apply_offset()
                a0.accept()

        super().keyPressEvent(a0)

    @override
    def mouseDoubleClickEvent(self, a0: QMouseEvent | None):
        """Handle double-click on title bar to toggle fullscreen"""
        if a0 and a0.button() == Qt.MouseButton.LeftButton and a0.position().y() <= 30:
            # Double-click on title bar area (top 30 pixels)
            self._toggle_fullscreen()
            a0.accept()
            return

        super().mouseDoubleClickEvent(a0)

    def _toggle_fullscreen(self):
        """Toggle between fullscreen and normal window mode"""
        if self._is_fullscreen:
            # Exit fullscreen
            self.setWindowFlags(
                self.windowFlags() |
                Qt.WindowType.WindowStaysOnTopHint |
                Qt.WindowType.Tool
            )
            self.showNormal()
            if self._normal_geometry:
                self.setGeometry(self._normal_geometry)
            self._is_fullscreen = False
            self.setWindowTitle("Manual Offset Control - SpritePal")
        else:
            # Enter fullscreen
            self._normal_geometry = self.geometry()
            self.setWindowFlags(
                Qt.WindowType.Window |
                Qt.WindowType.WindowStaysOnTopHint
            )
            self.showFullScreen()
            self._is_fullscreen = True
            self.setWindowTitle("Manual Offset Control - SpritePal (Fullscreen - F11 or Esc to exit)")

    def _cleanup_workers(self):
        """Clean up any running worker threads"""
        # Stop preview worker
        if self.preview_worker:
            self.preview_worker.quit()
            self.preview_worker.wait()
            self.preview_worker = None

        # Stop search worker
        if self.search_worker:
            self.search_worker.quit()
            self.search_worker.wait()
            self.search_worker = None

        # Stop range scan worker
        if self.range_scan_worker:
            self.range_scan_worker.quit()
            self.range_scan_worker.wait()
            self.range_scan_worker = None

    @override
    def closeEvent(self, a0: QCloseEvent | None):
        """Handle close event - hide instead of destroying"""
        self._cleanup_workers()
        if a0:
            a0.ignore()
        self.hide()

    @override
    def hideEvent(self, a0: QHideEvent | None):
        """Handle hide event - cleanup workers"""
        self._cleanup_workers()
        if a0:
            super().hideEvent(a0)
