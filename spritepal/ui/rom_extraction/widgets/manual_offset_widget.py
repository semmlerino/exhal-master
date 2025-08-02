"""Manual offset control widget for ROM extraction"""


from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QKeyEvent
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QSlider,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from spritepal.utils.logging_config import get_logger
from spritepal.utils.sprite_regions import SpriteRegion, SpriteRegionDetector

from .base_widget import BaseExtractionWidget

logger = get_logger(__name__)

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
    """Widget for manual ROM offset exploration with smart region-based navigation"""

    # Signals
    offset_changed = pyqtSignal(int)  # Emitted when offset changes (debounced)
    find_next_clicked = pyqtSignal()  # Find next valid sprite
    find_prev_clicked = pyqtSignal()  # Find previous valid sprite
    smart_mode_changed = pyqtSignal(bool)  # Emitted when smart mode is toggled
    region_changed = pyqtSignal(int)  # Emitted when current region changes

    def __init__(self, parent=None):
        super().__init__(parent)
        self._found_sprites = []  # Track found sprite offsets
        self._is_searching = False

        # Smart mode attributes
        self._smart_mode_enabled = False
        self._sprite_regions: list[SpriteRegion] = []
        self._current_region_index = 0
        self._region_detector = SpriteRegionDetector()
        self._region_boundaries: list[int] = []  # Slider positions for region boundaries
        self._region_weights: list[float] = []  # Relative sizes of regions
        self._sprite_data: list[tuple[int, float]] = []  # Raw sprite data

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

        # Smart mode controls
        smart_mode_row = QHBoxLayout()
        smart_mode_row.setSpacing(SPACING_MEDIUM)

        self.smart_mode_checkbox = QCheckBox("Smart Navigation")
        self.smart_mode_checkbox.setToolTip(
            "Navigate only through sprite-containing regions\n"
            "Removes empty areas from the slider range"
        )
        self.smart_mode_checkbox.stateChanged.connect(self._on_smart_mode_toggled)
        smart_mode_row.addWidget(self.smart_mode_checkbox)

        # Region indicator
        self.region_indicator_label = QLabel("Linear Mode")
        self.region_indicator_label.setStyleSheet("""
            color: #66aaff;
            font-weight: bold;
            padding: 2px 6px;
            background: #1a1a1a;
            border: 1px solid #444444;
            border-radius: 3px;
        """)
        smart_mode_row.addWidget(self.region_indicator_label)

        smart_mode_row.addStretch()
        manual_layout.addLayout(smart_mode_row)

        # Region navigation controls (initially hidden)
        self.region_nav_widget = QWidget()
        region_nav_layout = QHBoxLayout()
        region_nav_layout.setContentsMargins(0, 0, 0, 0)
        region_nav_layout.setSpacing(SPACING_MEDIUM)

        self.prev_region_btn = QPushButton("← Prev Region")
        self.prev_region_btn.setToolTip("Jump to previous sprite region (Ctrl+Left)")
        self.prev_region_btn.clicked.connect(self._navigate_prev_region)
        region_nav_layout.addWidget(self.prev_region_btn)

        self.region_info_label = QLabel("")
        self.region_info_label.setStyleSheet("color: #888888;")
        region_nav_layout.addWidget(self.region_info_label)

        self.next_region_btn = QPushButton("Next Region →")
        self.next_region_btn.setToolTip("Jump to next sprite region (Ctrl+Right)")
        self.next_region_btn.clicked.connect(self._navigate_next_region)
        region_nav_layout.addWidget(self.next_region_btn)

        region_nav_layout.addStretch()
        self.region_nav_widget.setLayout(region_nav_layout)
        self.region_nav_widget.setVisible(False)

        manual_layout.addWidget(self.region_nav_widget)

        # Navigation buttons
        nav_row = QHBoxLayout()
        nav_row.setSpacing(SPACING_MEDIUM)

        self.prev_sprite_btn = QPushButton("← Find Previous")
        self.prev_sprite_btn.setMinimumHeight(BUTTON_MIN_HEIGHT)
        _ = self.prev_sprite_btn.clicked.connect(self.find_prev_clicked.emit)
        self.prev_sprite_btn.setToolTip("Find previous sprite (Shortcut: Alt+Left)")
        nav_row.addWidget(self.prev_sprite_btn)

        self.next_sprite_btn = QPushButton("Find Next →")
        self.next_sprite_btn.setMinimumHeight(BUTTON_MIN_HEIGHT)
        _ = self.next_sprite_btn.clicked.connect(self.find_next_clicked.emit)
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

        # Initialize smart mode state
        self.smart_mode_checkbox.setEnabled(False)  # Disabled until sprites detected


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

    def keyPressEvent(self, event: QKeyEvent) -> None:
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

    # Smart mode methods

    def set_sprite_regions(self, sprites: list[tuple[int, float]]):
        """Set sprite data and calculate regions"""
        self._sprite_data = sprites
        self._sprite_regions = []  # Clear existing regions

        if sprites:
            # Enable smart mode checkbox
            self.smart_mode_checkbox.setEnabled(True)

            # Calculate regions
            self._sprite_regions = self._region_detector.detect_regions(sprites)

            if self._sprite_regions:
                # Update UI
                self._update_region_ui()

                # Auto-enable smart mode if significant number of sprites
                if len(sprites) > 10 and len(self._sprite_regions) > 1:
                    self.smart_mode_checkbox.setChecked(True)
            else:
                self.smart_mode_checkbox.setEnabled(False)
        else:
            self.smart_mode_checkbox.setEnabled(False)

    def get_sprite_regions(self) -> list[SpriteRegion]:
        """Get the current sprite regions"""
        return self._sprite_regions

    def _on_smart_mode_toggled(self, checked: int):
        """Handle smart mode toggle"""
        self._smart_mode_enabled = bool(checked)

        if self._smart_mode_enabled:
            if not self._sprite_regions:
                # No regions available
                self.smart_mode_checkbox.setChecked(False)
                self.set_status_text("No sprite regions detected. Run a scan first.")
                return

            self._enable_smart_mode()
        else:
            self._disable_smart_mode()

        self.smart_mode_changed.emit(self._smart_mode_enabled)

    def _enable_smart_mode(self):
        """Enable smart navigation mode"""
        self.region_indicator_label.setText(f"Smart Mode: {len(self._sprite_regions)} regions")
        self.region_indicator_label.setStyleSheet("""
            color: #66ff66;
            font-weight: bold;
            padding: 2px 6px;
            background: #1a2a1a;
            border: 1px solid #448844;
            border-radius: 3px;
        """)

        # Show region navigation controls
        self.region_nav_widget.setVisible(True)

        # Setup region mapping for slider
        self._setup_region_mapping()

        # Update UI with current region
        self._update_region_ui()

        # Jump to first region
        if self._sprite_regions:
            self._jump_to_region(0)

    def _disable_smart_mode(self):
        """Disable smart navigation mode"""
        self.region_indicator_label.setText("Linear Mode")
        self.region_indicator_label.setStyleSheet("""
            color: #66aaff;
            font-weight: bold;
            padding: 2px 6px;
            background: #1a1a1a;
            border: 1px solid #444444;
            border-radius: 3px;
        """)

        # Hide region navigation controls
        self.region_nav_widget.setVisible(False)

        # Clear region boundaries
        self._region_boundaries = []
        self._region_weights = []

        # Force slider repaint
        self.offset_slider.update()

    def _setup_region_mapping(self):
        """Calculate slider mapping for regions"""
        if not self._sprite_regions:
            return

        # Calculate weights based on region size
        total_size = sum(r.size_bytes for r in self._sprite_regions)
        self._region_weights = [r.size_bytes / total_size for r in self._sprite_regions]

        # Calculate slider boundaries for each region
        self._region_boundaries = [0]
        cumulative = 0
        slider_max = self.offset_slider.maximum()

        for weight in self._region_weights:
            cumulative += weight * slider_max
            self._region_boundaries.append(int(cumulative))

        # Force slider repaint
        self.offset_slider.update()

    def _navigate_prev_region(self):
        """Navigate to previous region"""
        if self._current_region_index > 0:
            self._jump_to_region(self._current_region_index - 1)

    def _navigate_next_region(self):
        """Navigate to next region"""
        if self._current_region_index < len(self._sprite_regions) - 1:
            self._jump_to_region(self._current_region_index + 1)

    def _jump_to_region(self, region_index: int):
        """Jump to a specific region"""
        if 0 <= region_index < len(self._sprite_regions):
            self._current_region_index = region_index
            region = self._sprite_regions[region_index]

            # Jump to center of region
            self.set_offset(region.center_offset)

            # Update UI
            self._update_region_ui()

            # Emit signal
            self.region_changed.emit(region_index)

    def _update_region_ui(self):
        """Update region-related UI elements"""
        if not self._sprite_regions or not self._smart_mode_enabled:
            return

        region = self._sprite_regions[self._current_region_index]

        # Update region info label
        self.region_info_label.setText(region.description)

        # Update navigation button states
        self.prev_region_btn.setEnabled(self._current_region_index > 0)
        self.next_region_btn.setEnabled(self._current_region_index < len(self._sprite_regions) - 1)

        # Update status
        status = f"Region {self._current_region_index + 1} of {len(self._sprite_regions)}: "
        status += f"{region.sprite_count} sprites, {region.quality_category} quality"
        self.set_status_text(status)

    def _on_offset_slider_changed(self, value: int):
        """Handle offset slider change with smart mode support"""
        # Map slider value to actual offset based on mode
        if self._smart_mode_enabled:
            actual_offset = self._map_slider_to_offset(value)
        else:
            actual_offset = value

        # Update spinbox without triggering its handler
        self.offset_spinbox.blockSignals(True)
        self.offset_spinbox.setValue(actual_offset)
        self.offset_spinbox.blockSignals(False)

        # Update hex label
        self.manual_offset_hex_label.setText(f"0x{actual_offset:06X}")

        # Update position percentage
        self._update_position_label(actual_offset)

        # Schedule preview update (debounced)
        self._pending_offset = actual_offset
        if hasattr(self, "_offset_timer"):
            self._offset_timer.stop()
            self._offset_timer.start()

        # Check if we entered a new region
        if self._smart_mode_enabled:
            self._check_region_change(actual_offset)

    def _on_offset_spinbox_changed(self, value: int):
        """Handle offset spinbox change with smart mode support"""
        # Map offset to slider position based on mode
        if self._smart_mode_enabled:
            slider_pos = self._map_offset_to_slider(value)
        else:
            slider_pos = value

        # Update slider without triggering its handler
        self.offset_slider.blockSignals(True)
        self.offset_slider.setValue(slider_pos)
        self.offset_slider.blockSignals(False)

        # Update hex label
        self.manual_offset_hex_label.setText(f"0x{value:06X}")

        # Update position percentage
        self._update_position_label(value)

        # Schedule preview update
        self._pending_offset = value
        self._offset_timer.stop()
        self._offset_timer.start()

        # Check if we entered a new region
        if self._smart_mode_enabled:
            self._check_region_change(value)

    def _map_slider_to_offset(self, slider_value: int) -> int:
        """Map slider position to ROM offset based on mode"""
        if not self._smart_mode_enabled or not self._sprite_regions:
            return slider_value  # Linear mapping

        # Find which region this slider value falls into
        for i in range(len(self._region_boundaries) - 1):
            if self._region_boundaries[i] <= slider_value < self._region_boundaries[i + 1]:
                # Interpolate within the region
                region = self._sprite_regions[i]
                region_start_slider = self._region_boundaries[i]
                region_end_slider = self._region_boundaries[i + 1]

                # Calculate position within region (0-1)
                if region_end_slider > region_start_slider:
                    position = (slider_value - region_start_slider) / (region_end_slider - region_start_slider)
                else:
                    position = 0

                # Map to actual offset
                return int(region.start_offset + position * (region.end_offset - region.start_offset))

        # Fallback for edge cases
        return self._sprite_regions[-1].end_offset if self._sprite_regions else slider_value

    def _map_offset_to_slider(self, offset: int) -> int:
        """Map ROM offset to slider position based on mode"""
        if not self._smart_mode_enabled or not self._sprite_regions:
            return offset  # Linear mapping

        # Find which region contains this offset
        region_index = self._region_detector.find_region_for_offset(offset)
        if region_index is None:
            # Offset is outside any region, find nearest
            for i, region in enumerate(self._sprite_regions):
                if offset < region.start_offset:
                    region_index = max(0, i - 1)
                    break
            else:
                region_index = len(self._sprite_regions) - 1

        if 0 <= region_index < len(self._sprite_regions):
            region = self._sprite_regions[region_index]
            region_start_slider = self._region_boundaries[region_index]
            region_end_slider = self._region_boundaries[region_index + 1]

            # Calculate position within region
            if region.end_offset > region.start_offset:
                position = (offset - region.start_offset) / (region.end_offset - region.start_offset)
                position = max(0, min(1, position))  # Clamp to 0-1
            else:
                position = 0

            # Map to slider position
            return int(region_start_slider + position * (region_end_slider - region_start_slider))

        return 0

    def _check_region_change(self, offset: int):
        """Check if offset is in a different region and update UI"""
        if not self._sprite_regions:
            return

        region_index = self._region_detector.find_region_for_offset(offset)
        if region_index is not None and region_index != self._current_region_index:
            self._current_region_index = region_index
            self._update_region_ui()
            self.region_changed.emit(region_index)
