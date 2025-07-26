"""Manual offset control widget for ROM extraction"""

from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QKeyEvent
from PyQt6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QSlider,
    QSpinBox,
    QVBoxLayout,
)

from .base_widget import BaseExtractionWidget

# UI Spacing Constants (matching main panel)
SPACING_SMALL = 6
SPACING_MEDIUM = 10
SPACING_LARGE = 16
SPACING_XLARGE = 20
BUTTON_MIN_HEIGHT = 32
COMBO_MIN_WIDTH = 200
BUTTON_MAX_WIDTH = 150
LABEL_MIN_WIDTH = 120


class ManualOffsetWidget(BaseExtractionWidget):
    """Widget for manual ROM offset exploration"""

    # Signals
    offset_changed = pyqtSignal(int)  # Emitted when offset changes (debounced)
    find_next_clicked = pyqtSignal()  # Find next valid sprite
    find_prev_clicked = pyqtSignal()  # Find previous valid sprite

    def __init__(self, parent=None):
        super().__init__(parent)
        self._found_sprites = []  # Track found sprite offsets
        self._is_searching = False
        self._setup_ui()
        self._setup_timer()

        # Enable keyboard focus
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def _setup_timer(self):
        """Setup debouncing timer for offset changes"""
        self._offset_timer = QTimer()
        self._offset_timer.setInterval(16)  # 16ms delay for ~60fps updates
        self._offset_timer.setSingleShot(True)
        self._offset_timer.timeout.connect(self._emit_offset_changed)
        self._pending_offset = None

    def _setup_ui(self):
        """Initialize the user interface"""
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)

        # Manual offset controls
        manual_group = self._create_group_box("Manual Offset Control")
        manual_layout = QVBoxLayout()
        manual_layout.setSpacing(SPACING_MEDIUM)
        manual_layout.setContentsMargins(SPACING_MEDIUM, SPACING_MEDIUM, SPACING_MEDIUM, SPACING_MEDIUM)

        # Offset slider with label
        slider_label = QLabel("ROM Offset:")
        slider_label.setStyleSheet("font-weight: bold;")
        manual_layout.addWidget(slider_label)

        self.offset_slider = QSlider(Qt.Orientation.Horizontal)
        self.offset_slider.setMinimum(0)
        self.offset_slider.setMaximum(0x400000)  # Default 4MB
        self.offset_slider.setValue(0x200000)    # Start at 2MB
        self.offset_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.offset_slider.setTickInterval(0x100000)  # Tick every 1MB
        self.offset_slider.valueChanged.connect(self._on_offset_slider_changed)
        self.offset_slider.setStyleSheet("""
            QSlider::groove:horizontal {
                border: 1px solid #999999;
                height: 8px;
                background: #2b2b2b;
                border-radius: 4px;
            }
            QSlider::handle:horizontal {
                background: #5599ff;
                border: 1px solid #5599ff;
                width: 18px;
                margin: -5px 0;
                border-radius: 9px;
            }
            QSlider::handle:horizontal:hover {
                background: #66aaff;
                border: 1px solid #66aaff;
            }
            QSlider::sub-page:horizontal {
                background: #4488dd;
                border-radius: 4px;
            }
        """)
        manual_layout.addWidget(self.offset_slider)

        # Offset value controls row
        offset_row = QHBoxLayout()
        offset_row.setSpacing(SPACING_MEDIUM)

        # Hex offset display with percentage
        self.manual_offset_hex_label = QLabel("0x200000")
        self.manual_offset_hex_label.setStyleSheet("""
            font-family: monospace;
            font-size: 14px;
            font-weight: bold;
            color: #66aaff;
            padding: 4px 8px;
            background: #1a1a1a;
            border: 1px solid #444444;
            border-radius: 4px;
        """)
        self.manual_offset_hex_label.setMinimumWidth(100)
        self.manual_offset_hex_label.setToolTip("Current offset in ROM")
        offset_row.addWidget(self.manual_offset_hex_label)

        # ROM position percentage
        self.position_label = QLabel("(50%)")
        self.position_label.setStyleSheet("color: #888888;")
        offset_row.addWidget(self.position_label)

        # Offset spinbox
        self.offset_spinbox = QSpinBox()
        self.offset_spinbox.setMinimum(0)
        self.offset_spinbox.setMaximum(0x400000)
        self.offset_spinbox.setValue(0x200000)
        self.offset_spinbox.setSingleStep(0x1000)
        self.offset_spinbox.setDisplayIntegerBase(16)
        self.offset_spinbox.setPrefix("0x")
        self.offset_spinbox.valueChanged.connect(self._on_offset_spinbox_changed)
        self.offset_spinbox.setMinimumWidth(120)
        offset_row.addWidget(self.offset_spinbox)

        # Step size selector
        offset_row.addWidget(QLabel("Step:"))
        self.step_combo = QComboBox()
        self.step_combo.addItems(["0x100", "0x1000", "0x10000"])
        self.step_combo.setCurrentIndex(1)  # Default to 0x1000
        self.step_combo.currentIndexChanged.connect(self._on_step_changed)
        offset_row.addWidget(self.step_combo)

        offset_row.addStretch()
        manual_layout.addLayout(offset_row)

        # Navigation buttons
        nav_row = QHBoxLayout()
        nav_row.setSpacing(SPACING_MEDIUM)

        self.prev_sprite_btn = QPushButton("← Find Previous")
        self.prev_sprite_btn.setMinimumHeight(BUTTON_MIN_HEIGHT)
        self.prev_sprite_btn.clicked.connect(self.find_prev_clicked.emit)
        self.prev_sprite_btn.setToolTip("Find previous sprite (Shortcut: Alt+Left)")
        nav_row.addWidget(self.prev_sprite_btn)

        self.next_sprite_btn = QPushButton("Find Next →")
        self.next_sprite_btn.setMinimumHeight(BUTTON_MIN_HEIGHT)
        self.next_sprite_btn.clicked.connect(self.find_next_clicked.emit)
        self.next_sprite_btn.setToolTip("Find next sprite (Shortcut: Alt+Right)")
        nav_row.addWidget(self.next_sprite_btn)

        manual_layout.addLayout(nav_row)

        # Quick jump locations and history
        jump_row = QHBoxLayout()
        jump_row.setSpacing(SPACING_MEDIUM)

        jump_row.addWidget(QLabel("Quick Jump:"))
        self.jump_combo = QComboBox()
        self.jump_combo.addItems([
            "Select...",
            "0x000000 - Start",
            "0x100000 - 1MB",
            "0x200000 - 2MB",
            "0x300000 - 3MB",
            "0x378000 - Common Sprites",
            "0x3D8000 - Alt Sprites"
        ])
        self.jump_combo.currentIndexChanged.connect(self._on_jump_selected)
        self.jump_combo.setMinimumWidth(150)
        jump_row.addWidget(self.jump_combo)

        # History dropdown
        jump_row.addWidget(QLabel("History:"))
        self.history_combo = QComboBox()
        self.history_combo.addItem("No sprites found yet")
        self.history_combo.setEnabled(False)
        self.history_combo.currentIndexChanged.connect(self._on_history_selected)
        self.history_combo.setMinimumWidth(150)
        self.history_combo.setToolTip("Previously found sprite locations")
        jump_row.addWidget(self.history_combo)

        jump_row.addStretch()

        manual_layout.addLayout(jump_row)

        # Status label
        self.manual_status_label = QLabel("Use the slider or navigation buttons to find sprites")
        self.manual_status_label.setWordWrap(True)
        self.manual_status_label.setStyleSheet("""
            padding: 8px;
            background: #2b2b2b;
            border: 1px solid #444444;
            border-radius: 4px;
            color: #cccccc;
        """)
        manual_layout.addWidget(self.manual_status_label)

        manual_group.setLayout(manual_layout)
        manual_group.setMinimumHeight(250)
        manual_group.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)

        layout.addWidget(manual_group)
        self.setLayout(layout)

    def _on_offset_slider_changed(self, value: int):
        """Handle offset slider change"""
        # Update spinbox without triggering its handler
        self.offset_spinbox.blockSignals(True)
        self.offset_spinbox.setValue(value)
        self.offset_spinbox.blockSignals(False)

        # Update hex label
        self.manual_offset_hex_label.setText(f"0x{value:06X}")

        # Update position percentage
        self._update_position_label(value)

        # Schedule preview update (debounced)
        self._pending_offset = value
        if hasattr(self, "_offset_timer"):
            self._offset_timer.stop()
            self._offset_timer.start()

    def _on_offset_spinbox_changed(self, value: int):
        """Handle offset spinbox change"""
        # Update slider without triggering its handler
        self.offset_slider.blockSignals(True)
        self.offset_slider.setValue(value)
        self.offset_slider.blockSignals(False)

        # Update hex label
        self.manual_offset_hex_label.setText(f"0x{value:06X}")

        # Update position percentage
        self._update_position_label(value)

        # Schedule preview update
        self._pending_offset = value
        self._offset_timer.stop()
        self._offset_timer.start()

    def _on_step_changed(self, index: int):
        """Handle step size change"""
        step_sizes = [0x100, 0x1000, 0x10000]
        self.offset_spinbox.setSingleStep(step_sizes[index])

    def _on_jump_selected(self, index: int):
        """Handle quick jump selection"""
        if index > 0:
            jump_text = self.jump_combo.currentText()
            # Extract hex value from text like "0x200000 - 2MB"
            hex_part = jump_text.split(" - ")[0]
            offset = int(hex_part, 16)
            self.offset_spinbox.setValue(offset)
            # Reset combo to "Select..."
            self.jump_combo.setCurrentIndex(0)

    def _on_history_selected(self, index: int):
        """Handle history selection"""
        if index > 0 and index - 1 < len(self._found_sprites):
            offset = self._found_sprites[index - 1]
            self.offset_spinbox.setValue(offset)
            # Don't reset history combo to allow easy navigation

    def _emit_offset_changed(self):
        """Emit the offset changed signal with the pending offset"""
        if self._pending_offset is not None:
            self.offset_changed.emit(self._pending_offset)
            self._pending_offset = None

    def get_current_offset(self) -> int:
        """Get the current offset value"""
        return self.offset_spinbox.value()

    def set_offset(self, offset: int):
        """Set the offset value"""
        self.offset_spinbox.setValue(offset)

    def get_step_size(self) -> int:
        """Get the current step size"""
        step_sizes = [0x100, 0x1000, 0x10000]
        if hasattr(self, "step_combo"):
            return step_sizes[self.step_combo.currentIndex()]
        return 0x1000  # Default step size

    def set_rom_size(self, size: int):
        """Update the maximum offset based on ROM size"""
        self.offset_slider.setMaximum(size)
        self.offset_spinbox.setMaximum(size)

    def set_status_text(self, text: str):
        """Update the status label text"""
        self.manual_status_label.setText(text)

    def set_navigation_enabled(self, enabled: bool):
        """Enable/disable navigation buttons"""
        self.prev_sprite_btn.setEnabled(enabled)
        self.next_sprite_btn.setEnabled(enabled)
        self._is_searching = not enabled

        # Update button text to show searching state
        if not enabled:
            self.prev_sprite_btn.setText("⏳ Searching...")
            self.next_sprite_btn.setText("⏳ Searching...")
        else:
            self.prev_sprite_btn.setText("← Find Previous")
            self.next_sprite_btn.setText("Find Next →")

    def add_found_sprite(self, offset: int):
        """Add a found sprite offset to history"""
        if offset not in self._found_sprites:
            self._found_sprites.append(offset)
            # Keep only last 20 found sprites
            if len(self._found_sprites) > 20:
                self._found_sprites.pop(0)

            # Update history combo
            self._update_history_combo()

    def keyPressEvent(self, event: QKeyEvent) -> None:  # noqa: N802
        """Handle keyboard shortcuts"""
        if event.modifiers() == Qt.KeyboardModifier.AltModifier:
            if event.key() == Qt.Key.Key_Left and not self._is_searching:
                self.find_prev_clicked.emit()
                event.accept()
                return
            if event.key() == Qt.Key.Key_Right and not self._is_searching:
                self.find_next_clicked.emit()
                event.accept()
                return

        # Page Up/Down for larger jumps
        if not self._is_searching:
            current = self.offset_spinbox.value()
            if event.key() == Qt.Key.Key_PageUp:
                self.offset_spinbox.setValue(max(0, current - 0x10000))
                event.accept()
                return
            if event.key() == Qt.Key.Key_PageDown:
                self.offset_spinbox.setValue(min(self.offset_spinbox.maximum(), current + 0x10000))
                event.accept()
                return

        super().keyPressEvent(event)

    def _update_history_combo(self):
        """Update the history combo box with found sprites"""
        self.history_combo.clear()

        if not self._found_sprites:
            self.history_combo.addItem("No sprites found yet")
            self.history_combo.setEnabled(False)
        else:
            self.history_combo.addItem("Select from history...")
            for offset in reversed(self._found_sprites):  # Show most recent first
                self.history_combo.addItem(f"0x{offset:06X}")
            self.history_combo.setEnabled(True)

    def _update_position_label(self, value: int):
        """Update the position percentage label"""
        max_val = self.offset_slider.maximum()
        if max_val > 0:
            percentage = (value / max_val) * 100
            self.position_label.setText(f"({percentage:.1f}%)")
        else:
            self.position_label.setText("(0%)")
