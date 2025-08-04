"""
Unified Manual Offset Dialog - Integrated Implementation

A consolidated implementation that combines the working UI from the archived
simplified dialog with proper tab integration and signal coordination.

This dialog provides:
- Working slider that updates offset
- Preview widget display
- Three functional tabs (Browse, Smart, History)
- Proper signals (offset_changed, sprite_found)
- Methods needed by ROM extraction panel
"""

import contextlib
import os
import time
import weakref
from datetime import datetime, timezone
from typing import TYPE_CHECKING, override

if TYPE_CHECKING:
    from core.managers.extraction_manager import ExtractionManager
    from core.rom_extractor import ROMExtractor

from PyQt6.QtCore import QMutex, QMutexLocker, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QCloseEvent, QFont, QHideEvent, QKeyEvent
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QSlider,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)
from ui.common import WorkerManager
from ui.common.smart_preview_coordinator import SmartPreviewCoordinator
from ui.components import DialogBase
from ui.components.panels import StatusPanel
from ui.common.collapsible_group_box import CollapsibleGroupBox
from ui.dialogs.services import ViewStateManager
from ui.rom_extraction.workers import SpritePreviewWorker, SpriteSearchWorker
from ui.widgets.sprite_preview_widget import SpritePreviewWidget
from utils.logging_config import get_logger
from utils.sprite_regions import SpriteRegion

logger = get_logger(__name__)


# MinimalSignalCoordinator removed - SmartPreviewCoordinator handles all timing and debouncing


class SimpleBrowseTab(QWidget):
    """Simple browse tab with essential navigation controls."""

    offset_changed = pyqtSignal(int)
    find_next_clicked = pyqtSignal()
    find_prev_clicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)

        # State
        self._current_offset = 0x200000
        self._rom_size = 0x400000
        self._step_size = 0x1000

        self._setup_ui()

    def _setup_ui(self):
        """Set up the space-efficient browse tab UI."""
        layout = QVBoxLayout(self)
        layout.setSpacing(6)  # Reduced from 10px
        layout.setContentsMargins(5, 5, 5, 5)  # Reduced margins

        # Unified control section - consolidates all controls into one compact area
        controls_frame = QFrame()
        controls_frame.setFrameStyle(QFrame.Shape.StyledPanel)
        controls_layout = QVBoxLayout(controls_frame)
        controls_layout.setSpacing(6)  # Compact spacing
        controls_layout.setContentsMargins(8, 8, 8, 8)  # Reduced margins

        # Main title - single title for entire control area
        title = QLabel("ROM Offset Control")
        title_font = QFont()
        title_font.setBold(True)
        title_font.setPointSize(11)  # Slightly smaller
        title.setFont(title_font)
        title.setStyleSheet("color: #4488dd; padding: 2px 4px; border-radius: 3px;")
        controls_layout.addWidget(title)

        # Slider with smart preview support
        self.position_slider = QSlider(Qt.Orientation.Horizontal)
        self.position_slider.setObjectName("manual_offset_rom_slider")  # Unique identifier
        self.position_slider.setMinimum(0)
        self.position_slider.setMaximum(self._rom_size)
        self.position_slider.setValue(self._current_offset)
        self.position_slider.setMinimumHeight(32)  # Reduced from 40px
        
        # Connect to valueChanged for compatibility (used by smart coordinator)
        self.position_slider.valueChanged.connect(self._on_slider_changed)
        
        # Smart preview coordinator will connect to pressed/moved/released signals
        self._smart_preview_coordinator = None
        # Apply distinct styling for ROM offset slider
        self.position_slider.setStyleSheet("""
            QSlider::groove:horizontal {
                border: 2px solid #4488dd;
                height: 8px;
                background: #2b2b2b;
                border-radius: 4px;
            }
            QSlider::handle:horizontal {
                background: #4488dd;
                border: 2px solid #5599ee;
                width: 18px;
                margin: -5px 0;
                border-radius: 9px;
            }
            QSlider::handle:horizontal:hover {
                background: #5599ee;
                border: 2px solid #66aaff;
            }
            QSlider::sub-page:horizontal {
                background: #3377cc;
                border-radius: 4px;
            }
        """)
        controls_layout.addWidget(self.position_slider)

        # Position info row
        info_row = QHBoxLayout()
        info_row.setSpacing(8)
        
        self.position_label = QLabel(self._format_position(self._current_offset))
        position_font = QFont()
        position_font.setBold(True)
        position_font.setPointSize(9)  # Slightly smaller
        self.position_label.setFont(position_font)
        info_row.addWidget(self.position_label)

        info_row.addStretch()

        self.offset_label = QLabel(f"0x{self._current_offset:06X}")
        self.offset_label.setStyleSheet("font-family: monospace; color: #666; font-size: 11px;")
        info_row.addWidget(self.offset_label)

        controls_layout.addLayout(info_row)

        # Compact navigation row - combine navigation and manual input
        nav_row = QHBoxLayout()
        nav_row.setSpacing(6)

        # Navigation buttons - smaller height
        self.prev_button = QPushButton("◀ Prev")
        self.prev_button.setMinimumHeight(28)  # Reduced from 36px
        self.prev_button.clicked.connect(self.find_prev_clicked.emit)
        nav_row.addWidget(self.prev_button)

        self.next_button = QPushButton("Next ▶")
        self.next_button.setMinimumHeight(28)  # Reduced from 36px
        self.next_button.clicked.connect(self.find_next_clicked.emit)
        nav_row.addWidget(self.next_button)

        # Separator
        nav_row.addSpacing(12)

        # Step size control - inline
        nav_row.addWidget(QLabel("Step:"))
        self.step_spinbox = QSpinBox()
        self.step_spinbox.setMinimum(0x100)
        self.step_spinbox.setMaximum(0x100000)
        self.step_spinbox.setValue(self._step_size)
        self.step_spinbox.setDisplayIntegerBase(16)
        self.step_spinbox.setPrefix("0x")
        self.step_spinbox.setMaximumWidth(80)
        nav_row.addWidget(self.step_spinbox)

        nav_row.addStretch()
        controls_layout.addLayout(nav_row)

        # Manual input row - compact horizontal layout
        manual_row = QHBoxLayout()
        manual_row.setSpacing(6)
        
        manual_row.addWidget(QLabel("Go to:"))
        
        self.manual_spinbox = QSpinBox()
        self.manual_spinbox.setMinimum(0)
        self.manual_spinbox.setMaximum(self._rom_size)
        self.manual_spinbox.setValue(self._current_offset)
        self.manual_spinbox.setDisplayIntegerBase(16)
        self.manual_spinbox.setPrefix("0x")
        self.manual_spinbox.valueChanged.connect(self._on_manual_changed)
        manual_row.addWidget(self.manual_spinbox)

        go_button = QPushButton("Go")
        go_button.setMinimumHeight(28)  # Consistent with other buttons
        go_button.clicked.connect(lambda: self.set_offset(self.manual_spinbox.value()))
        manual_row.addWidget(go_button)
        
        manual_row.addStretch()
        controls_layout.addLayout(manual_row)

        layout.addWidget(controls_frame)
        layout.addStretch()

    def _format_position(self, offset: int) -> str:
        """Format position as human-readable text."""
        if self._rom_size > 0:
            mb_position = offset / (1024 * 1024)
            percentage = (offset / self._rom_size) * 100
            return f"{mb_position:.1f}MB through ROM ({percentage:.0f}%)"
        return "Unknown position"

    def _on_slider_changed(self, value: int):
        """Handle slider changes - smart preview coordinator handles preview updates automatically."""
        self._current_offset = value
        self._update_displays()

        # Update manual spinbox without triggering signal
        self.manual_spinbox.blockSignals(True)
        self.manual_spinbox.setValue(value)
        self.manual_spinbox.blockSignals(False)

        # Emit offset changed signal for external listeners
        self.offset_changed.emit(value)
        
        # Note: SmartPreviewCoordinator handles preview updates automatically via
        # sliderMoved signal - no need to manually request here

    def _on_manual_changed(self, value: int):
        """Handle manual spinbox changes."""
        self._current_offset = value
        self._update_displays()

        # Update slider without triggering signal
        self.position_slider.blockSignals(True)
        self.position_slider.setValue(value)
        self.position_slider.blockSignals(False)

        self.offset_changed.emit(value)
        
        # Request immediate high-quality preview for manual changes
        if self._smart_preview_coordinator:
            self._smart_preview_coordinator.request_manual_preview(value)

    def _update_displays(self):
        """Update position displays."""
        self.position_label.setText(self._format_position(self._current_offset))
        self.offset_label.setText(f"0x{self._current_offset:06X}")

    def get_current_offset(self) -> int:
        """Get current offset."""
        return self._current_offset

    def set_offset(self, offset: int):
        """Set current offset."""
        if offset != self._current_offset:
            self._current_offset = offset

            # Update controls without triggering signals
            self.position_slider.blockSignals(True)
            self.manual_spinbox.blockSignals(True)

            self.position_slider.setValue(offset)
            self.manual_spinbox.setValue(offset)

            self.position_slider.blockSignals(False)
            self.manual_spinbox.blockSignals(False)

            self._update_displays()
            
            # Request immediate high-quality preview for programmatic changes
            if self._smart_preview_coordinator:
                self._smart_preview_coordinator.request_manual_preview(offset)

    def get_step_size(self) -> int:
        """Get step size."""
        return self.step_spinbox.value()

    def set_rom_size(self, size: int):
        """Set ROM size."""
        self._rom_size = size
        self.position_slider.setMaximum(size)
        self.manual_spinbox.setMaximum(size)
        self._update_displays()

    def set_navigation_enabled(self, enabled: bool):
        """Enable/disable navigation."""
        self.prev_button.setEnabled(enabled)
        self.next_button.setEnabled(enabled)
    
    def connect_smart_preview_coordinator(self, coordinator):
        """Connect smart preview coordinator for enhanced preview updates."""
        self._smart_preview_coordinator = coordinator
        if coordinator:
            # Connect coordinator to slider for drag detection
            coordinator.connect_slider(self.position_slider)
            
            # Setup UI update callback for immediate feedback
            coordinator.set_ui_update_callback(self._on_smart_ui_update)
            
            logger.debug("Smart preview coordinator connected to browse tab")
    
    def _on_smart_ui_update(self, offset: int):
        """Handle immediate UI updates from smart coordinator."""
        if offset != self._current_offset:
            # Update displays without triggering signals
            self._current_offset = offset
            
            self.position_slider.blockSignals(True)
            self.manual_spinbox.blockSignals(True)
            
            self.position_slider.setValue(offset)
            self.manual_spinbox.setValue(offset)
            self._update_displays()
            
            self.position_slider.blockSignals(False)
            self.manual_spinbox.blockSignals(False)


class SimpleSmartTab(QWidget):
    """Simple smart tab with region-based navigation."""

    smart_mode_changed = pyqtSignal(bool)
    region_changed = pyqtSignal(int)
    offset_requested = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)

        # State
        self._sprite_regions = []
        self._current_region_index = 0

        self._setup_ui()

    def _setup_ui(self):
        """Set up space-efficient smart tab UI."""
        layout = QVBoxLayout(self)
        layout.setSpacing(6)  # Reduced spacing
        layout.setContentsMargins(5, 5, 5, 5)  # Reduced margins

        # Unified smart controls frame
        smart_frame = QFrame()
        smart_frame.setFrameStyle(QFrame.Shape.StyledPanel)
        smart_layout = QVBoxLayout(smart_frame)
        smart_layout.setSpacing(6)  # Compact spacing
        smart_layout.setContentsMargins(8, 8, 8, 8)  # Reduced margins

        # Single title for the entire smart tab
        title = QLabel("Smart Navigation")
        title_font = QFont()
        title_font.setBold(True)
        title_font.setPointSize(11)  # Slightly smaller
        title.setFont(title_font)
        title.setStyleSheet("color: #4488dd; padding: 2px 4px; border-radius: 3px;")
        smart_layout.addWidget(title)

        # Smart mode checkbox
        self.smart_checkbox = QCheckBox("Enable Smart Mode")
        self.smart_checkbox.setToolTip("Navigate through detected sprite regions")
        self.smart_checkbox.toggled.connect(self.smart_mode_changed.emit)
        smart_layout.addWidget(self.smart_checkbox)

        # Compact region selection row
        region_row = QHBoxLayout()
        region_row.setSpacing(6)
        
        region_row.addWidget(QLabel("Region:"))
        
        self.region_combo = QComboBox()
        self.region_combo.currentIndexChanged.connect(self._on_region_changed)
        region_row.addWidget(self.region_combo)

        # Compact go button
        go_region_button = QPushButton("Go")
        go_region_button.setMinimumHeight(28)  # Consistent with browse tab
        go_region_button.clicked.connect(self._go_to_current_region)
        region_row.addWidget(go_region_button)

        smart_layout.addLayout(region_row)
        layout.addWidget(smart_frame)
        layout.addStretch()

    def _on_region_changed(self, index: int):
        """Handle region selection change."""
        self._current_region_index = index
        self.region_changed.emit(index)

    def _go_to_current_region(self):
        """Go to the currently selected region."""
        if 0 <= self._current_region_index < len(self._sprite_regions):
            region = self._sprite_regions[self._current_region_index]
            if hasattr(region, "offset"):
                self.offset_requested.emit(region.offset)
            elif isinstance(region, tuple) and len(region) >= 2:
                self.offset_requested.emit(region[0])  # Assume (offset, quality) tuple

    def set_sprite_regions(self, sprites: list[tuple[int, float]]):
        """Set sprite regions from sprite data."""
        self._sprite_regions = sprites

        # Update combo box
        self.region_combo.clear()
        for i, (offset, quality) in enumerate(sprites):
            self.region_combo.addItem(f"Region {i+1}: 0x{offset:06X} (Q: {quality:.2f})")

    def get_sprite_regions(self) -> list[SpriteRegion]:
        """Get sprite regions in expected format."""
        regions = []
        for i, (offset, quality) in enumerate(self._sprite_regions):
            # Create a SpriteRegion with proper constructor parameters
            region = SpriteRegion(
                region_id=i,
                start_offset=offset,
                end_offset=offset + 0x1000,  # Assume 4KB regions
                sprite_offsets=[offset],
                sprite_qualities=[quality],
                average_quality=quality,
                sprite_count=1,
                size_bytes=0x1000,
                density=quality,
                custom_name=f"Region {i+1}"
            )
            regions.append(region)
        return regions

    def is_smart_mode_enabled(self) -> bool:
        """Check if smart mode is enabled."""
        return self.smart_checkbox.isChecked()

    def get_current_region_index(self) -> int:
        """Get current region index."""
        return self._current_region_index


class SimpleHistoryTab(QWidget):
    """Simple history tab for found sprites."""

    sprite_selected = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)

        # State
        self._found_sprites = []

        self._setup_ui()

    def _setup_ui(self):
        """Set up space-efficient history tab UI."""
        layout = QVBoxLayout(self)
        layout.setSpacing(6)  # Reduced spacing
        layout.setContentsMargins(5, 5, 5, 5)  # Reduced margins

        # Compact title
        title = QLabel("Found Sprites")
        title_font = QFont()
        title_font.setBold(True)
        title_font.setPointSize(11)  # Slightly smaller
        title.setFont(title_font)
        title.setStyleSheet("color: #4488dd; padding: 2px 4px; border-radius: 3px;")
        layout.addWidget(title)

        # Sprite list
        self.sprite_list = QListWidget()
        self.sprite_list.itemDoubleClicked.connect(self._on_sprite_double_clicked)
        layout.addWidget(self.sprite_list)

        # Compact controls row
        controls_layout = QHBoxLayout()
        controls_layout.setSpacing(6)

        clear_button = QPushButton("Clear")
        clear_button.setMinimumHeight(28)  # Consistent height
        clear_button.clicked.connect(self.clear_history)
        controls_layout.addWidget(clear_button)

        go_button = QPushButton("Go to Selected")
        go_button.setMinimumHeight(28)  # Consistent height
        go_button.clicked.connect(self._go_to_selected)
        controls_layout.addWidget(go_button)

        controls_layout.addStretch()
        layout.addLayout(controls_layout)

    def _on_sprite_double_clicked(self, item: QListWidgetItem):
        """Handle double-click on sprite item."""
        try:
            # Extract offset from item text
            text = item.text()
            if "0x" in text:
                offset_str = text.split("0x")[1].split(" ")[0]
                offset = int(offset_str, 16)
                self.sprite_selected.emit(offset)
        except (ValueError, IndexError) as e:
            logger.warning(f"Failed to extract offset from item: {e}")

    def _go_to_selected(self):
        """Go to selected sprite."""
        current_item = self.sprite_list.currentItem()
        if current_item:
            self._on_sprite_double_clicked(current_item)

    def add_sprite(self, offset: int, quality: float = 1.0):
        """Add a sprite to history."""
        sprite_info = {
            "offset": offset,
            "quality": quality,
            "timestamp": datetime.now(tz=timezone.utc)
        }

        # Avoid duplicates
        if not any(s["offset"] == offset for s in self._found_sprites):
            self._found_sprites.append(sprite_info)

            # Add to list widget
            item_text = f"0x{offset:06X} - Quality: {quality:.2f}"
            self.sprite_list.addItem(item_text)

    def clear_history(self):
        """Clear sprite history."""
        self._found_sprites.clear()
        self.sprite_list.clear()

    def get_sprites(self) -> list[tuple[int, float]]:
        """Get all sprites as (offset, quality) tuples."""
        return [(s["offset"], s["quality"]) for s in self._found_sprites]

    def set_sprites(self, sprites: list[tuple[int, float]]):
        """Set sprites from list."""
        self.clear_history()
        for offset, quality in sprites:
            self.add_sprite(offset, quality)

    def get_sprite_count(self) -> int:
        """Get number of found sprites."""
        return len(self._found_sprites)


class UnifiedManualOffsetDialog(DialogBase):
    """
    Unified Manual Offset Dialog combining simplified architecture with tab-based navigation.

    This dialog consolidates functionality from the archived simplified dialog while
    providing a clean, working interface with proper signal coordination.
    """

    # External signals for ROM extraction panel integration
    offset_changed = pyqtSignal(int)
    sprite_found = pyqtSignal(int, str)  # offset, name
    validation_failed = pyqtSignal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        # Debug logging for singleton tracking
        logger.debug(f"Creating UnifiedManualOffsetDialog instance (parent: {parent.__class__.__name__ if parent else 'None'})")

        # UI Components - declare BEFORE super().__init__()
        self.tab_widget: QTabWidget | None = None
        self.browse_tab: SimpleBrowseTab | None = None
        self.smart_tab: SimpleSmartTab | None = None
        self.history_tab: SimpleHistoryTab | None = None
        self.preview_widget: SpritePreviewWidget | None = None
        self.status_panel: StatusPanel | None = None
        self.status_collapsible: CollapsibleGroupBox | None = None
        self.apply_btn: QPushButton | None = None

        # Business logic state
        self.rom_path: str = ""
        self.rom_size: int = 0x400000

        # Manager references with thread safety
        self.extraction_manager: ExtractionManager | None = None
        self.rom_extractor: ROMExtractor | None = None
        self._manager_mutex = QMutex()

        # Worker references
        self.preview_worker: SpritePreviewWorker | None = None
        self.search_worker: SpriteSearchWorker | None = None

        # Smart preview coordinator handles all timing and signal coordination
        self._smart_preview_coordinator: SmartPreviewCoordinator | None = None

        # Preview update timer (legacy - kept for compatibility)
        self._preview_timer: QTimer | None = None

        # Debug ID for tracking
        self._debug_id = f"dialog_{int(time.time()*1000)}"
        logger.debug(f"Dialog debug ID: {self._debug_id}")

        super().__init__(
            parent=parent,
            title="Manual Offset Control - SpritePal",
            modal=False,
            size=(900, 600),
            min_size=(800, 500),
            with_status_bar=False,
            orientation=Qt.Orientation.Horizontal,
            splitter_handle_width=4  # Slightly thinner splitter
        )

        # Initialize view state manager
        self.view_state_manager = ViewStateManager(self, self)

        # Note: _setup_ui() is called by DialogBase.__init__() automatically
        self._setup_smart_preview_coordinator()
        self._setup_preview_timer()
        self._connect_signals()

    def __del__(self):
        """Destructor for tracking dialog destruction."""
        with contextlib.suppress(BaseException):
            logger.debug(f"Dialog {self._debug_id} being destroyed")

    def _setup_ui(self):
        """Set up the dialog UI."""
        # Left panel with tabs
        left_panel = self._create_left_panel()
        self.add_panel(left_panel, stretch_factor=0)

        # Right panel with preview
        right_panel = self._create_right_panel()
        self.add_panel(right_panel, stretch_factor=1)

        # Set initial panel sizes (30% left, 70% right)
        total_width = self.width()
        left_width = int(total_width * 0.30)
        right_width = total_width - left_width
        self.main_splitter.setSizes([left_width, right_width])

        # Set up custom buttons
        self._setup_custom_buttons()

    def _create_left_panel(self) -> QWidget:
        """Create the left panel with tabs and collapsible status."""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setSpacing(8)  # Reduced spacing
        layout.setContentsMargins(5, 5, 5, 5)  # Reduced margins

        # Tab widget
        self.tab_widget = QTabWidget()

        # Create and add tabs
        self.browse_tab = SimpleBrowseTab()
        self.smart_tab = SimpleSmartTab()
        self.history_tab = SimpleHistoryTab()

        self.tab_widget.addTab(self.browse_tab, "Browse")
        self.tab_widget.addTab(self.smart_tab, "Smart")
        self.tab_widget.addTab(self.history_tab, "History")

        layout.addWidget(self.tab_widget)

        # Collapsible status panel - defaults to collapsed to save space
        self.status_collapsible = CollapsibleGroupBox("Status", collapsed=True)
        self.status_panel = StatusPanel()
        self.status_collapsible.add_widget(self.status_panel)
        
        layout.addWidget(self.status_collapsible)

        return panel

    def _create_right_panel(self) -> QWidget:
        """Create the right panel with preview."""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setSpacing(8)  # Reduced spacing
        layout.setContentsMargins(5, 5, 5, 5)  # Reduced margins

        # Compact title
        title = QLabel("Sprite Preview")
        title_font = QFont()
        title_font.setBold(True)
        title_font.setPointSize(12)  # Slightly smaller
        title.setFont(title_font)
        title.setStyleSheet("color: #4488dd; padding: 4px 6px; border-radius: 3px;")
        layout.addWidget(title)

        # Preview widget
        self.preview_widget = SpritePreviewWidget()
        layout.addWidget(self.preview_widget)

        return panel

    def _setup_custom_buttons(self):
        """Set up custom dialog buttons."""
        self.apply_btn = QPushButton("Apply Offset")
        self.apply_btn.clicked.connect(self._apply_offset)
        self.button_box.addButton(self.apply_btn, self.button_box.ButtonRole.AcceptRole)

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.hide)
        self.button_box.addButton(close_btn, self.button_box.ButtonRole.RejectRole)

    # _setup_signal_coordinator removed - SmartPreviewCoordinator handles all coordination
    
    def _setup_smart_preview_coordinator(self):
        """Set up smart preview coordination for real-time updates."""
        self._smart_preview_coordinator = SmartPreviewCoordinator(self)
        
        # Connect preview signals
        self._smart_preview_coordinator.preview_ready.connect(self._on_smart_preview_ready)
        self._smart_preview_coordinator.preview_cached.connect(self._on_smart_preview_cached)
        self._smart_preview_coordinator.preview_error.connect(self._on_smart_preview_error)
        
        # Setup ROM data provider
        self._smart_preview_coordinator.set_rom_data_provider(self._get_rom_data_for_preview)
        
        logger.debug("Smart preview coordinator setup complete")

    def _setup_preview_timer(self):
        """Set up preview update timer."""
        self._preview_timer = QTimer(self)
        self._preview_timer.setSingleShot(True)
        self._preview_timer.timeout.connect(self._update_preview)

    def _connect_signals(self):
        """Connect internal signals."""
        if not self.browse_tab or not self.smart_tab or not self.history_tab:
            return

        # Browse tab signals
        self.browse_tab.offset_changed.connect(self._on_offset_changed)
        self.browse_tab.find_next_clicked.connect(self._find_next_sprite)
        self.browse_tab.find_prev_clicked.connect(self._find_prev_sprite)
        
        # Connect smart preview coordinator to browse tab
        if self._smart_preview_coordinator and self.browse_tab:
            self.browse_tab.connect_smart_preview_coordinator(self._smart_preview_coordinator)

        # Smart tab signals
        self.smart_tab.smart_mode_changed.connect(self._on_smart_mode_changed)
        self.smart_tab.region_changed.connect(self._on_region_changed)
        self.smart_tab.offset_requested.connect(self._on_offset_requested)

        # History tab signals
        self.history_tab.sprite_selected.connect(self._on_sprite_selected)

    def _on_offset_changed(self, offset: int):
        """Handle offset changes from browse tab."""
        # Emit signal immediately for external listeners
        self.offset_changed.emit(offset)

        # SmartPreviewCoordinator handles all preview updates automatically
        # No fallback needed - coordinator is always initialized

    def _on_offset_requested(self, offset: int):
        """Handle offset request from smart tab."""
        if self.browse_tab:
            self.browse_tab.set_offset(offset)

    def _on_sprite_selected(self, offset: int):
        """Handle sprite selection from history."""
        if self.browse_tab:
            self.browse_tab.set_offset(offset)
        # Switch to browse tab
        if self.tab_widget:
            self.tab_widget.setCurrentIndex(0)

    def _on_smart_mode_changed(self, enabled: bool):
        """Handle smart mode toggle."""
        # Could implement smart mode behavior here

    def _on_region_changed(self, region_index: int):
        """Handle region change."""
        # Could implement region-specific behavior here

    def _find_next_sprite(self):
        """Find next sprite (placeholder)."""
        if self.browse_tab:
            current_offset = self.browse_tab.get_current_offset()
            step_size = self.browse_tab.get_step_size()
            new_offset = current_offset + step_size
            if new_offset <= self.rom_size:
                self.browse_tab.set_offset(new_offset)

    def _find_prev_sprite(self):
        """Find previous sprite (placeholder)."""
        if self.browse_tab:
            current_offset = self.browse_tab.get_current_offset()
            step_size = self.browse_tab.get_step_size()
            new_offset = max(0, current_offset - step_size)
            self.browse_tab.set_offset(new_offset)

    def _request_preview_update(self, delay_ms: int = 100):
        """Request preview update with debouncing."""
        if self._preview_timer:
            self._preview_timer.stop()
            self._preview_timer.start(delay_ms)

    def _update_preview(self):
        """Update sprite preview."""
        if not self._has_rom_data() or not self.browse_tab:
            return

        current_offset = self.browse_tab.get_current_offset()
        self._update_status(f"Loading preview for 0x{current_offset:06X}...")

        # Clean up existing preview worker
        if self.preview_worker:
            WorkerManager.cleanup_worker(self.preview_worker, timeout=1000)
            self.preview_worker = None

        # Create new preview worker
        with QMutexLocker(self._manager_mutex):
            if self.rom_extractor:
                sprite_name = f"manual_0x{current_offset:X}"
                self.preview_worker = SpritePreviewWorker(
                    self.rom_path, current_offset, sprite_name, self.rom_extractor, None
                )
                self.preview_worker.preview_ready.connect(self._on_preview_ready)
                self.preview_worker.preview_error.connect(self._on_preview_error)
                self.preview_worker.start()

    def _on_preview_ready(self, tile_data: bytes, width: int, height: int, sprite_name: str):
        """Handle preview ready."""
        if self.preview_widget:
            self.preview_widget.load_sprite_from_4bpp(tile_data, width, height, sprite_name)

        current_offset = self.get_current_offset()
        self._update_status(f"Sprite found at 0x{current_offset:06X}")

    def _on_preview_error(self, error_msg: str):
        """Handle preview error."""
        if self.preview_widget:
            self.preview_widget.clear()
            self.preview_widget.info_label.setText("No sprite found")

        current_offset = self.get_current_offset()
        self._update_status(f"No sprite at 0x{current_offset:06X}")

    def _apply_offset(self):
        """Apply current offset and close dialog."""
        offset = self.get_current_offset()
        sprite_name = f"manual_0x{offset:X}"
        self.sprite_found.emit(offset, sprite_name)
        self.hide()

    def _update_status(self, message: str):
        """Update status message."""
        if self.status_panel:
            self.status_panel.update_status(message)

    def _has_rom_data(self) -> bool:
        """Check if ROM data is available."""
        return bool(self.rom_path and self.rom_size > 0)

    def _cleanup_workers(self):
        """Clean up worker threads."""
        WorkerManager.cleanup_worker(self.preview_worker, timeout=2000)
        self.preview_worker = None

        WorkerManager.cleanup_worker(self.search_worker, timeout=2000)
        self.search_worker = None

        if self._preview_timer:
            self._preview_timer.stop()

        # Signal coordinator cleanup handled by SmartPreviewCoordinator
            
        if self._smart_preview_coordinator:
            self._smart_preview_coordinator.cleanup()

    # Public interface methods required by ROM extraction panel

    def set_rom_data(self, rom_path: str, rom_size: int, extraction_manager: "ExtractionManager") -> None:
        """Set ROM data for the dialog."""
        with QMutexLocker(self._manager_mutex):
            self.rom_path = rom_path
            self.rom_size = rom_size
            self.extraction_manager = extraction_manager
            self.rom_extractor = extraction_manager.get_rom_extractor()

        # Update tabs with new ROM data
        if self.browse_tab:
            self.browse_tab.set_rom_size(rom_size)

        # Update window title
        self.view_state_manager.update_title_with_rom(rom_path)

        logger.debug(f"ROM data updated: {os.path.basename(rom_path)} ({rom_size} bytes)")
    
    def _get_rom_data_for_preview(self):
        """Provide ROM data for smart preview coordinator."""
        with QMutexLocker(self._manager_mutex):
            return (self.rom_path, self.rom_extractor)
    
    def _on_smart_preview_ready(self, tile_data: bytes, width: int, height: int, sprite_name: str):
        """Handle preview ready from smart coordinator."""
        if self.preview_widget:
            self.preview_widget.load_sprite_from_4bpp(tile_data, width, height, sprite_name)
        
        current_offset = self.get_current_offset()
        self._update_status(f"High-quality preview at 0x{current_offset:06X}")
    
    def _on_smart_preview_cached(self, tile_data: bytes, width: int, height: int, sprite_name: str):
        """Handle cached preview from smart coordinator."""
        if self.preview_widget:
            self.preview_widget.load_sprite_from_4bpp(tile_data, width, height, sprite_name)
        
        current_offset = self.get_current_offset()
        self._update_status(f"Cached preview at 0x{current_offset:06X}")
    
    def _on_smart_preview_error(self, error_msg: str):
        """Handle preview error from smart coordinator."""
        if self.preview_widget:
            self.preview_widget.clear()
            self.preview_widget.info_label.setText("No sprite found")
        
        current_offset = self.get_current_offset()
        self._update_status(f"No sprite at 0x{current_offset:06X}: {error_msg}")

    def set_offset(self, offset: int) -> bool:
        """Set current offset."""
        if self.browse_tab:
            self.browse_tab.set_offset(offset)
            # Manually trigger the offset changed signal since set_offset doesn't emit it
            self._on_offset_changed(offset)
            return True
        return False

    def get_current_offset(self) -> int:
        """Get current offset."""
        if self.browse_tab:
            return self.browse_tab.get_current_offset()
        return 0x200000

    def add_found_sprite(self, offset: int, quality: float = 1.0) -> None:
        """Add found sprite to history."""
        if self.history_tab:
            self.history_tab.add_sprite(offset, quality)

            # Update tab title with count
            count = self.history_tab.get_sprite_count()
            if self.tab_widget:
                self.tab_widget.setTabText(2, f"History ({count})")

    # Event handlers

    @override
    def keyPressEvent(self, event: QKeyEvent | None):
        """Handle keyboard shortcuts."""
        if event:
            if event.key() == Qt.Key.Key_Escape:
                if self.view_state_manager.handle_escape_key():
                    event.accept()
                else:
                    self.hide()
                    event.accept()
            elif event.key() == Qt.Key.Key_F11:
                self.view_state_manager.toggle_fullscreen()
                event.accept()
            elif event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
                self._apply_offset()
                event.accept()

        super().keyPressEvent(event)

    @override
    def closeEvent(self, event: QCloseEvent | None):
        """Handle close event."""
        logger.debug(f"Dialog {self._debug_id} closing")
        self._cleanup_workers()
        if event:
            super().closeEvent(event)

    @override
    def hideEvent(self, event: QHideEvent | None):
        """Handle hide event."""
        logger.debug(f"Dialog {self._debug_id} hiding")
        self._cleanup_workers()
        self.view_state_manager.handle_hide_event()
        if event:
            super().hideEvent(event)

    def showEvent(self, event):  # noqa: N802
        """Handle show event."""
        logger.debug(f"Dialog {self._debug_id} showing")
        super().showEvent(event)
        self.view_state_manager.handle_show_event()


def create_manual_offset_dialog(parent: QWidget | None = None) -> UnifiedManualOffsetDialog:
    """Factory function for creating manual offset dialog."""
    return UnifiedManualOffsetDialog(parent)
