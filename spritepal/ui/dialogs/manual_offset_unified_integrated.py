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

from __future__ import annotations

import contextlib
import os
import time
from datetime import datetime, timezone
from functools import partial
from typing import TYPE_CHECKING

try:
    from typing import override
except ImportError:
    from typing_extensions import override

if TYPE_CHECKING:
    from core.managers.extraction_manager import ExtractionManager
    from core.rom_extractor import ROMExtractor

from utils.sprite_history_manager import SpriteHistoryManager

from PyQt6.QtCore import QMutex, QMutexLocker, Qt, QThread, QTimer, pyqtSignal

if TYPE_CHECKING:
    from PyQt6.QtGui import QAction, QCloseEvent, QFont, QHideEvent, QKeyEvent
else:
    from PyQt6.QtGui import QAction, QCloseEvent, QFont, QHideEvent, QKeyEvent
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMenu,
    QMessageBox,
    QPushButton,
    QSlider,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from ui.common import WorkerManager
from ui.common.collapsible_group_box import CollapsibleGroupBox
from ui.common.smart_preview_coordinator import SmartPreviewCoordinator
from ui.components import DialogBase
from ui.components.panels import StatusPanel
from ui.components.visualization.rom_map_widget import ROMMapWidget
from ui.dialogs.advanced_search_dialog import AdvancedSearchDialog
from ui.dialogs.services import ViewStateManager
from ui.rom_extraction.workers import SpritePreviewWorker, SpriteSearchWorker
from ui.widgets.sprite_preview_widget import SpritePreviewWidget
from utils.logging_config import get_logger
from utils.rom_cache import get_rom_cache
from utils.sprite_regions import SpriteRegion

logger = get_logger(__name__)


# MinimalSignalCoordinator removed - SmartPreviewCoordinator handles all timing and debouncing


class SimpleBrowseTab(QWidget):
    """Simple browse tab with essential navigation controls."""

    offset_changed = pyqtSignal(int)
    find_next_clicked = pyqtSignal()
    find_prev_clicked = pyqtSignal()
    advanced_search_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)

        # State
        self._current_offset = 0x200000
        self._rom_size = 0x400000
        self._step_size = 0x1000
        self._rom_path = ""
        self._advanced_search_dialog = None

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
        self.prev_button.setToolTip("Find previous sprite (skip empty areas)")
        self.prev_button.clicked.connect(self.find_prev_clicked.emit)
        nav_row.addWidget(self.prev_button)

        self.next_button = QPushButton("Next ▶")
        self.next_button.setMinimumHeight(28)  # Reduced from 36px
        self.next_button.setToolTip("Find next sprite (skip empty areas)")
        self.next_button.clicked.connect(self.find_next_clicked.emit)
        nav_row.addWidget(self.next_button)

        # Advanced Search button
        self.advanced_search_button = QPushButton("🔍 Advanced")
        self.advanced_search_button.setMinimumHeight(28)
        self.advanced_search_button.setToolTip("Open advanced search dialog with filtering and batch operations")
        self.advanced_search_button.clicked.connect(self._open_advanced_search)
        nav_row.addWidget(self.advanced_search_button)

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
        go_button.clicked.connect(self._on_go_button_clicked)
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
        logger.debug(f"[DEBUG] _on_slider_changed called with value: 0x{value:06X}")
        self._current_offset = value
        self._update_displays()

        # Update manual spinbox without triggering signal
        self.manual_spinbox.blockSignals(True)
        self.manual_spinbox.setValue(value)
        self.manual_spinbox.blockSignals(False)

        # Emit offset changed signal for external listeners
        logger.debug(f"[DEBUG] Emitting offset_changed signal with value: 0x{value:06X}")
        self.offset_changed.emit(value)

        # Note: SmartPreviewCoordinator handles preview updates automatically via
        # sliderMoved signal - no need to manually request here
        logger.debug("[DEBUG] _on_slider_changed complete, coordinator should handle preview")

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
        if self._smart_preview_coordinator is not None:
            self._smart_preview_coordinator.request_manual_preview(value)

    def _update_displays(self):
        """Update position displays."""
        self.position_label.setText(self._format_position(self._current_offset))
        self.offset_label.setText(f"0x{self._current_offset:06X}")

    def _on_go_button_clicked(self):
        """Handle go button click without lambda."""
        self.set_offset(self.manual_spinbox.value())

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
            if self._smart_preview_coordinator is not None:
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

    def set_rom_path(self, rom_path: str):
        """Set ROM path for advanced search."""
        self._rom_path = rom_path

    def _open_advanced_search(self):
        """Open the advanced search dialog."""
        if not self._rom_path:
            logger.warning("No ROM path available for advanced search")
            return

        # Create or reuse advanced search dialog
        if self._advanced_search_dialog is None:
            self._advanced_search_dialog = AdvancedSearchDialog(self._rom_path, self)
            # Connect sprite selection signal
            self._advanced_search_dialog.sprite_selected.connect(self._on_advanced_search_sprite_selected)

        # Show the dialog
        self._advanced_search_dialog.show()
        self._advanced_search_dialog.raise_()
        self._advanced_search_dialog.activateWindow()

    def _on_advanced_search_sprite_selected(self, offset: int):
        """Handle sprite selection from advanced search dialog."""
        # Update the manual offset dialog's position
        self.set_offset(offset)

        # Log the action
        logger.debug(f"Advanced search selected sprite at offset 0x{offset:06X}")

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

        # Use the sprite history manager
        self._history_manager = SpriteHistoryManager()

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
        # Use manager to add sprite (handles duplicates and limits)
        if self._history_manager.add_sprite(offset, quality):
            # Only add to UI if successfully added to manager
            item_text = f"0x{offset:06X} - Quality: {quality:.2f}"
            self.sprite_list.addItem(item_text)

    def clear_history(self):
        """Clear sprite history."""
        self._history_manager.clear_history()
        self.sprite_list.clear()

    def get_sprites(self) -> list[tuple[int, float]]:
        """Get all sprites as (offset, quality) tuples."""
        return self._history_manager.get_sprites()

    def set_sprites(self, sprites: list[tuple[int, float]]):
        """Set sprites from list."""
        self.clear_history()
        for offset, quality in sprites:
            self.add_sprite(offset, quality)

    def get_sprite_count(self) -> int:
        """Get number of found sprites."""
        return self._history_manager.get_sprite_count()


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
        self.mini_rom_map: ROMMapWidget | None = None
        self.bookmarks_menu: QMenu | None = None
        self.bookmarks: list[tuple[int, str]] = []  # (offset, name) pairs

        # Business logic state
        self.rom_path: str = ""
        self.rom_size: int = 0x400000

        # Manager references with thread safety
        self.extraction_manager: ExtractionManager | None = None
        self.rom_extractor: ROMExtractor | None = None
        self._manager_mutex = QMutex()

        # ROM cache integration
        self.rom_cache = get_rom_cache()
        self._cache_stats = {"hits": 0, "misses": 0, "total_requests": 0}
        self._adjacent_offsets_cache = set()  # Track preloaded offsets

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

        # Add context menu for cache management
        self._setup_cache_context_menu()

        layout.addWidget(self.status_collapsible)

        # Mini ROM map for position context
        self.mini_rom_map = ROMMapWidget()
        self.mini_rom_map.setMaximumHeight(40)
        self.mini_rom_map.setMinimumHeight(30)
        layout.addWidget(self.mini_rom_map)

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
        self.preview_widget.similarity_search_requested.connect(self._on_similarity_search_requested)
        layout.addWidget(self.preview_widget)

        return panel

    def _setup_custom_buttons(self):
        """Set up custom dialog buttons."""
        self.apply_btn = QPushButton("Apply Offset")
        self.apply_btn.clicked.connect(self._apply_offset)
        self.button_box.addButton(self.apply_btn, self.button_box.ButtonRole.AcceptRole)

        # Bookmark button
        bookmark_btn = QPushButton("Bookmark")
        bookmark_btn.setToolTip("Save current offset to bookmarks (Ctrl+D)")
        bookmark_btn.clicked.connect(self._add_bookmark)
        self.button_box.addButton(bookmark_btn, self.button_box.ButtonRole.ActionRole)

        # Bookmarks menu button
        bookmarks_menu_btn = QPushButton("Bookmarks ▼")
        bookmarks_menu_btn.setToolTip("Show saved bookmarks (Ctrl+B)")
        self.bookmarks_menu = QMenu(self)
        self._update_bookmarks_menu()
        bookmarks_menu_btn.setMenu(self.bookmarks_menu)
        self.button_box.addButton(bookmarks_menu_btn, self.button_box.ButtonRole.ActionRole)

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.hide)
        self.button_box.addButton(close_btn, self.button_box.ButtonRole.RejectRole)

    # _setup_signal_coordinator removed - SmartPreviewCoordinator handles all coordination

    def _setup_smart_preview_coordinator(self):
        """Set up smart preview coordination for real-time updates."""
        self._smart_preview_coordinator = SmartPreviewCoordinator(self, rom_cache=self.rom_cache)

        # Connect preview signals with QueuedConnection for thread safety
        self._smart_preview_coordinator.preview_ready.connect(
            self._on_smart_preview_ready, Qt.ConnectionType.QueuedConnection
        )
        self._smart_preview_coordinator.preview_cached.connect(
            self._on_smart_preview_cached, Qt.ConnectionType.QueuedConnection
        )
        self._smart_preview_coordinator.preview_error.connect(
            self._on_smart_preview_error, Qt.ConnectionType.QueuedConnection
        )

        # Setup ROM data provider with cache support
        self._smart_preview_coordinator.set_rom_data_provider(self._get_rom_data_for_preview)

        # Connect cache-related signals
        self._smart_preview_coordinator.preview_ready.connect(self._on_cache_miss)
        self._smart_preview_coordinator.preview_cached.connect(self._on_cache_hit)

        logger.debug("Smart preview coordinator setup complete with ROM cache integration")

    def _setup_preview_timer(self):
        """Set up preview update timer."""
        self._preview_timer = QTimer(self)
        self._preview_timer.setSingleShot(True)
        self._preview_timer.timeout.connect(self._update_preview)

    def _connect_signals(self):
        """Connect internal signals."""
        if self.browse_tab is None or self.smart_tab is None or self.history_tab is None:
            return

        # Browse tab signals
        self.browse_tab.offset_changed.connect(self._on_offset_changed)
        self.browse_tab.find_next_clicked.connect(self._find_next_sprite)
        self.browse_tab.find_prev_clicked.connect(self._find_prev_sprite)

        # Connect smart preview coordinator to browse tab
        if self._smart_preview_coordinator and self.browse_tab is not None:
            self.browse_tab.connect_smart_preview_coordinator(self._smart_preview_coordinator)

        # Smart tab signals
        self.smart_tab.smart_mode_changed.connect(self._on_smart_mode_changed)
        self.smart_tab.region_changed.connect(self._on_region_changed)
        self.smart_tab.offset_requested.connect(self._on_offset_requested)

        # History tab signals
        self.history_tab.sprite_selected.connect(self._on_sprite_selected)

    def _on_offset_changed(self, offset: int):
        """Handle offset changes from browse tab."""
        logger.debug(f"[DEBUG] Dialog._on_offset_changed called with offset: 0x{offset:06X}")
        # Update cache stats
        self._cache_stats["total_requests"] += 1

        # Update mini ROM map
        if self.mini_rom_map is not None:
            self.mini_rom_map.set_current_offset(offset)
            logger.debug(f"[DEBUG] Updated mini ROM map to offset: 0x{offset:06X}")

        # Update preview widget with current offset for similarity search
        if self.preview_widget is not None:
            self.preview_widget.set_current_offset(offset)

        # Emit signal immediately for external listeners
        self.offset_changed.emit(offset)

        # CRITICAL FIX: Request preview when offset changes!
        # Use request_manual_preview for immediate response without debounce
        if self._smart_preview_coordinator is not None:
            logger.debug(f"[DEBUG] Requesting immediate preview for offset 0x{offset:06X}")
            self._smart_preview_coordinator.request_manual_preview(offset)
        else:
            logger.error("[DEBUG] No smart preview coordinator available!")

        # Schedule predictive preloading for adjacent offsets
        self._schedule_adjacent_preloading(offset)

    def _on_offset_requested(self, offset: int):
        """Handle offset request from smart tab."""
        if self.browse_tab is not None:
            self.browse_tab.set_offset(offset)

    def _on_sprite_selected(self, offset: int):
        """Handle sprite selection from history."""
        if self.browse_tab is not None:
            self.browse_tab.set_offset(offset)
        # Switch to browse tab
        if self.tab_widget is not None:
            self.tab_widget.setCurrentIndex(0)

    def _on_smart_mode_changed(self, enabled: bool):
        """Handle smart mode toggle."""
        # Could implement smart mode behavior here

    def _on_region_changed(self, region_index: int):
        """Handle region change."""
        # Could implement region-specific behavior here

    def _find_next_sprite(self):
        """Find next sprite with region awareness."""
        if not self.browse_tab or not self._has_rom_data():
            return

        current_offset = self.browse_tab.get_current_offset()

        # Clean up existing search worker
        if self.search_worker is not None:
            WorkerManager.cleanup_worker(self.search_worker)
            self.search_worker = None

        # Create search worker for forward search
        with QMutexLocker(self._manager_mutex):
            if self.rom_extractor is not None:
                self.search_worker = SpriteSearchWorker(
                    self.rom_path,
                    current_offset,
                    self.rom_size,
                    1,  # Forward direction
                    self.rom_extractor,
                    parent=self
                )
                self.search_worker.sprite_found.connect(self._on_search_sprite_found)
                self.search_worker.search_complete.connect(self._on_search_complete)
                self.search_worker.start()

                self._update_status("Searching for next sprite...")

    def _find_prev_sprite(self):
        """Find previous sprite with region awareness."""
        if not self.browse_tab or not self._has_rom_data():
            return

        current_offset = self.browse_tab.get_current_offset()

        # Clean up existing search worker
        if self.search_worker is not None:
            WorkerManager.cleanup_worker(self.search_worker)
            self.search_worker = None

        # Create search worker for backward search
        with QMutexLocker(self._manager_mutex):
            if self.rom_extractor is not None:
                self.search_worker = SpriteSearchWorker(
                    self.rom_path,
                    current_offset,
                    0,  # Search back to start
                    -1,  # Backward direction
                    self.rom_extractor,
                    parent=self
                )
                self.search_worker.sprite_found.connect(self._on_search_sprite_found)
                self.search_worker.search_complete.connect(self._on_search_complete)
                self.search_worker.start()

                self._update_status("Searching for previous sprite...")

    def _request_preview_update(self, delay_ms: int = 100):
        """Request preview update with debouncing."""
        if self._preview_timer is not None:
            self._preview_timer.stop()
            self._preview_timer.start(delay_ms)

    def _update_preview(self):
        """Update sprite preview."""
        if not self._has_rom_data() or self.browse_tab is None:
            return

        current_offset = self.browse_tab.get_current_offset()
        self._update_status(f"Loading preview for 0x{current_offset:06X}...")

        # Clean up existing preview worker
        if self.preview_worker is not None:
            WorkerManager.cleanup_worker(self.preview_worker, timeout=1000)
            self.preview_worker = None

        # Create new preview worker
        with QMutexLocker(self._manager_mutex):
            if self.rom_extractor is not None:
                sprite_name = f"manual_0x{current_offset:X}"
                self.preview_worker = SpritePreviewWorker(
                    self.rom_path, current_offset, sprite_name, self.rom_extractor, None, parent=self
                )
                self.preview_worker.preview_ready.connect(self._on_preview_ready)
                self.preview_worker.preview_error.connect(self._on_preview_error)
                self.preview_worker.start()

    def _on_preview_ready(self, tile_data: bytes, width: int, height: int, sprite_name: str):
        """Handle preview ready."""
        if self.preview_widget is not None:
            self.preview_widget.load_sprite_from_4bpp(tile_data, width, height, sprite_name)

        current_offset = self.get_current_offset()
        self._update_status(f"Sprite found at 0x{current_offset:06X}")

    def _on_preview_error(self, error_msg: str):
        """Handle preview error."""
        # Don't clear the preview widget on errors - keep the last valid preview visible
        # This prevents black flashing when rapidly moving the slider
        if self.preview_widget is not None:
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
        if self.status_panel is not None:
            self.status_panel.update_status(message)

            # Add cache performance tooltip if available
            if hasattr(self.status_panel, "status_label"):
                tooltip = self._build_cache_tooltip()
                self.status_panel.status_label.setToolTip(tooltip)

    def _has_rom_data(self) -> bool:
        """Check if ROM data is available."""
        return bool(self.rom_path and self.rom_size > 0)

    def _cleanup_workers(self):
        """Clean up worker threads."""
        WorkerManager.cleanup_worker(self.preview_worker, timeout=2000)
        self.preview_worker = None

        WorkerManager.cleanup_worker(self.search_worker, timeout=2000)
        self.search_worker = None

        if self._preview_timer is not None:
            self._preview_timer.stop()

        # Signal coordinator cleanup handled by SmartPreviewCoordinator

        if self._smart_preview_coordinator is not None:
            self._smart_preview_coordinator.cleanup()

        # Reset cache stats
        self._cache_stats = {"hits": 0, "misses": 0, "total_requests": 0}
        self._adjacent_offsets_cache.clear()

    def cleanup(self):
        """Clean up resources to prevent memory leaks."""
        logger.debug(f"Cleaning up UnifiedManualOffsetDialog {self._debug_id}")

        # Disconnect signals
        try:
            # Disconnect tab signals
            if self.browse_tab is not None:
                self.browse_tab.offset_changed.disconnect()
                self.browse_tab.find_next_clicked.disconnect()
                self.browse_tab.find_prev_clicked.disconnect()

            if self.smart_tab is not None:
                self.smart_tab.smart_mode_changed.disconnect()
                self.smart_tab.region_changed.disconnect()
                self.smart_tab.offset_requested.disconnect()

            if self.history_tab is not None:
                self.history_tab.sprite_selected.disconnect()

            # Disconnect preview widget signals
            if self.preview_widget is not None:
                self.preview_widget.similarity_search_requested.disconnect()

            # Disconnect smart preview coordinator
            if self._smart_preview_coordinator is not None:
                self._smart_preview_coordinator.preview_ready.disconnect()
                self._smart_preview_coordinator.preview_cached.disconnect()
                self._smart_preview_coordinator.preview_error.disconnect()
        except TypeError:
            pass  # Already disconnected

        # Clean up workers
        self._cleanup_workers()

        # Clear references
        self.extraction_manager = None
        self.rom_extractor = None
        self._manual_offset_dialog = None

        # Clear cache references
        self._adjacent_offsets_cache.clear()

        # Clear bookmarks to prevent reference leaks
        self.bookmarks.clear()

        # Clear preview pixmaps
        if self.preview_widget is not None:
            self.preview_widget.clear()

        # Clear advanced search dialog reference
        if hasattr(self, "_advanced_search_dialog") and self._advanced_search_dialog is not None:
            self._advanced_search_dialog.close()
            self._advanced_search_dialog = None

    # Public interface methods required by ROM extraction panel

    def set_rom_data(self, rom_path: str, rom_size: int, extraction_manager: ExtractionManager) -> None:
        """Set ROM data for the dialog."""
        with QMutexLocker(self._manager_mutex):
            self.rom_path = rom_path
            self.rom_size = rom_size
            self.extraction_manager = extraction_manager
            self.rom_extractor = extraction_manager.get_rom_extractor()

        # Update tabs with new ROM data
        if self.browse_tab is not None:
            self.browse_tab.set_rom_size(rom_size)
            self.browse_tab.set_rom_path(rom_path)

        # Update mini ROM map
        if self.mini_rom_map is not None:
            self.mini_rom_map.set_rom_size(rom_size)

        # Update window title
        self.view_state_manager.update_title_with_rom(rom_path)

        logger.debug(f"ROM data updated: {os.path.basename(rom_path)} ({rom_size} bytes)")

        # Initialize cache for this ROM
        self._initialize_rom_cache(rom_path)

        # Update cache status display
        self._update_cache_status_display()

        # Load any cached sprites for visualization
        self._load_cached_sprites_for_map()

    def _get_rom_data_for_preview(self):
        """Provide ROM data with cache support for smart preview coordinator."""
        with QMutexLocker(self._manager_mutex):
            result = (self.rom_path, self.rom_extractor, self.rom_cache)
            logger.debug(f"[DEBUG] _get_rom_data_for_preview returning: (rom_path={bool(result[0])}, extractor={bool(result[1])}, cache={bool(result[2])})")
            return result

    def _on_smart_preview_ready(self, tile_data: bytes, width: int, height: int, sprite_name: str):
        """Handle preview ready from smart coordinator with guaranteed UI updates."""
        logger.debug(f"[SIGNAL_RECEIVED] _on_smart_preview_ready called: data_len={len(tile_data) if tile_data else 0}, {width}x{height}, name={sprite_name}")
        logger.debug(f"[SIGNAL_RECEIVED] tile_data first 20 bytes: {tile_data[:20].hex() if tile_data else 'None'}")
        
        # CRITICAL: Verify we're on main thread before calling widget methods
        from PyQt6.QtCore import QThread
        if QThread.currentThread() != QApplication.instance().thread():
            logger.warning("[THREAD_SAFETY] _on_smart_preview_ready called from worker thread!")
            return

        if self.preview_widget is not None:
            logger.debug("[SIGNAL_RECEIVED] Preview widget exists, calling load_sprite_from_4bpp")
            logger.debug(f"[SIGNAL_RECEIVED] Preview widget type: {type(self.preview_widget)}")
            logger.debug(f"[SIGNAL_RECEIVED] Preview widget visible: {self.preview_widget.isVisible()}")

            self.preview_widget.load_sprite_from_4bpp(tile_data, width, height, sprite_name)
            
            # CRITICAL: Add explicit widget updates after loading sprite
            logger.debug("[SPRITE_DISPLAY] Forcing widget updates after load_sprite_from_4bpp")
            self.preview_widget.update()
            self.preview_widget.repaint()

            # Ensure UI responsiveness during rapid updates
            QApplication.processEvents()
            logger.debug("[SIGNAL_RECEIVED] load_sprite_from_4bpp completed, processEvents called")
            
            # Log pixmap state after loading for debugging
            if hasattr(self.preview_widget, 'preview_label') and self.preview_widget.preview_label:
                pixmap = self.preview_widget.preview_label.pixmap()
                logger.debug(f"[SPRITE_DISPLAY] Pixmap after load: exists={pixmap is not None}, null={pixmap.isNull() if pixmap else 'N/A'}")
        else:
            logger.error("[SIGNAL_RECEIVED] preview_widget is None!")

        current_offset = self.get_current_offset()
        cache_status = self._get_cache_status_text()
        self._update_status(f"High-quality preview at 0x{current_offset:06X} {cache_status}")
        logger.debug("[SIGNAL_RECEIVED] _on_smart_preview_ready completed")

    def _on_smart_preview_cached(self, tile_data: bytes, width: int, height: int, sprite_name: str):
        """Handle cached preview from smart coordinator."""
        logger.debug(f"[SIGNAL_RECEIVED] _on_smart_preview_cached called: data_len={len(tile_data) if tile_data else 0}, {width}x{height}, name={sprite_name}")
        logger.debug(f"[SIGNAL_RECEIVED] cached tile_data first 20 bytes: {tile_data[:20].hex() if tile_data else 'None'}")
        
        # CRITICAL: Verify we're on main thread before calling widget methods
        from PyQt6.QtCore import QThread
        if QThread.currentThread() != QApplication.instance().thread():
            logger.warning("[THREAD_SAFETY] _on_smart_preview_cached called from worker thread!")
            return
            
        if self.preview_widget is not None:
            logger.debug("[DEBUG] Calling preview_widget.load_sprite_from_4bpp (from cache)")
            self.preview_widget.load_sprite_from_4bpp(tile_data, width, height, sprite_name)
            
            # CRITICAL: Add explicit widget updates after loading sprite
            logger.debug("[SPRITE_DISPLAY] Forcing widget updates after cached load_sprite_from_4bpp")
            self.preview_widget.update()
            self.preview_widget.repaint()
            
            # Ensure UI responsiveness during rapid updates
            QApplication.processEvents()
        else:
            logger.error("[DEBUG] preview_widget is None!")

        current_offset = self.get_current_offset()
        cache_status = self._get_cache_status_text()
        self._update_status(f"Cached preview at 0x{current_offset:06X} {cache_status}")

    def _on_smart_preview_error(self, error_msg: str):
        """Handle preview error from smart coordinator."""
        logger.debug(f"[DEBUG] _on_smart_preview_error called: {error_msg}")
        
        # CRITICAL: Verify we're on main thread before calling widget methods
        from PyQt6.QtCore import QThread
        if QThread.currentThread() != QApplication.instance().thread():
            logger.warning("[THREAD_SAFETY] _on_smart_preview_error called from worker thread!")
            return
            
        if self.preview_widget is not None:
            logger.debug("[DEBUG] Updating status only, not clearing preview")
            # Don't clear - keep last valid preview visible to prevent black flashing
            self.preview_widget.info_label.setText("No sprite found")
            
            # Force widget updates
            self.preview_widget.update()
            self.preview_widget.repaint()
        else:
            logger.error("[DEBUG] preview_widget is None!")

        current_offset = self.get_current_offset()
        self._update_status(f"No sprite at 0x{current_offset:06X}: {error_msg}")

    def set_offset(self, offset: int) -> bool:
        """Set current offset."""
        if self.browse_tab is not None:
            self.browse_tab.set_offset(offset)
            # Manually trigger the offset changed signal since set_offset doesn't emit it
            self._on_offset_changed(offset)
            return True
        return False

    def get_current_offset(self) -> int:
        """Get current offset."""
        if self.browse_tab is not None:
            return self.browse_tab.get_current_offset()
        return 0x200000

    def add_found_sprite(self, offset: int, quality: float = 1.0) -> None:
        """Add found sprite to history."""
        if self.history_tab is not None:
            self.history_tab.add_sprite(offset, quality)

            # Update tab title with count
            count = self.history_tab.get_sprite_count()
            if self.tab_widget is not None:
                self.tab_widget.setTabText(2, f"History ({count})")

    # ROM Cache Integration Methods

    def _initialize_rom_cache(self, rom_path: str) -> None:
        """Initialize ROM cache for the current ROM."""
        try:
            # Reset cache stats for new ROM
            self._cache_stats = {"hits": 0, "misses": 0, "total_requests": 0}
            self._adjacent_offsets_cache.clear()

            # Log cache status
            if self.rom_cache.cache_enabled:
                logger.debug(f"ROM cache initialized for {os.path.basename(rom_path)}")
            else:
                logger.debug("ROM cache is disabled")

        except Exception as e:
            logger.warning(f"Error initializing ROM cache: {e}")

    def _schedule_adjacent_preloading(self, current_offset: int) -> None:
        """Schedule preloading of adjacent offsets for smooth navigation."""
        if not self.rom_cache.cache_enabled:
            return

        try:
            # Calculate adjacent offsets based on typical step sizes
            step_sizes = [0x100, 0x1000, 0x2000]  # Common alignment boundaries
            adjacent_offsets = []

            for step in step_sizes:
                # Previous and next offsets
                prev_offset = max(0, current_offset - step)
                next_offset = min(self.rom_size, current_offset + step)

                # Only preload if not already cached
                if prev_offset not in self._adjacent_offsets_cache:
                    adjacent_offsets.append(prev_offset)
                if next_offset not in self._adjacent_offsets_cache:
                    adjacent_offsets.append(next_offset)

            # Limit preloading to avoid overwhelming the system
            adjacent_offsets = adjacent_offsets[:6]  # Max 6 adjacent offsets

            # Schedule preloading with low priority
            for offset in adjacent_offsets:
                self._preload_offset(offset)
                self._adjacent_offsets_cache.add(offset)

        except Exception as e:
            logger.debug(f"Error scheduling adjacent preloading: {e}")

    def _preload_offset(self, offset: int) -> None:
        """Preload a specific offset using the worker pool."""
        if not self._smart_preview_coordinator:
            return

        # Check if we have ROM data available
        if not hasattr(self, '_get_rom_data_for_preview'):
            return

        rom_data = self._get_rom_data_for_preview()
        if not rom_data or not rom_data[0]:  # No ROM path available
            return

        try:
            # Use SmartPreviewCoordinator's worker pool for background preloading
            # Request with very low priority so it doesn't interfere with user actions
            self._smart_preview_coordinator.request_preview(offset, priority=-1)

        except Exception as e:
            logger.debug(f"Error preloading offset 0x{offset:06X}: {e}")

    def _on_cache_hit(self, *args) -> None:
        """Handle cache hit event."""
        self._cache_stats["hits"] += 1

    def _on_cache_miss(self, *args) -> None:
        """Handle cache miss event."""
        self._cache_stats["misses"] += 1

    def _get_cache_status_text(self) -> str:
        """Get cache status text for display."""
        if not self.rom_cache.cache_enabled:
            return "[Cache: Disabled]"

        total = self._cache_stats["total_requests"]
        hits = self._cache_stats["hits"]

        if total > 0:
            hit_rate = (hits / total) * 100
            return f"[Cache: {hit_rate:.0f}% hit rate]"

        return "[Cache: Ready]"

    def _build_cache_tooltip(self) -> str:
        """Build detailed cache tooltip."""
        if not self.rom_cache.cache_enabled:
            return "ROM caching is disabled"

        try:
            stats = self.rom_cache.get_cache_stats()
            cache_info = [
                f"Cache Directory: {stats.get('cache_dir', 'Unknown')}",
                f"Total Cache Files: {stats.get('total_files', 0)}",
                f"Cache Size: {stats.get('total_size_bytes', 0)} bytes",
                "",
                "Session Stats:",
                f"  Total Requests: {self._cache_stats['total_requests']}",
                f"  Cache Hits: {self._cache_stats['hits']}",
                f"  Cache Misses: {self._cache_stats['misses']}",
            ]

            if self._cache_stats["total_requests"] > 0:
                hit_rate = (self._cache_stats["hits"] / self._cache_stats["total_requests"]) * 100
                cache_info.append(f"  Hit Rate: {hit_rate:.1f}%")

            return "\n".join(cache_info)

        except Exception as e:
            return f"Cache tooltip error: {e}"

    def _update_cache_status_display(self) -> None:
        """Update cache status in the UI."""
        try:
            cache_status = self._get_cache_status_text()

            # Update status panel if collapsed box exists
            if self.status_collapsible and self.rom_cache.cache_enabled:
                # Update collapsible title to show cache status
                current_title = self.status_collapsible.title()
                if "[Cache:" not in current_title:
                    new_title = f"{current_title} {cache_status}"
                    self.status_collapsible.setTitle(new_title)

        except Exception as e:
            logger.debug(f"Error updating cache status display: {e}")

    def _setup_cache_context_menu(self) -> None:
        """Set up context menu for cache management."""
        if self.status_collapsible is None:
            return

        try:
            # Enable context menu on the status collapsible widget
            self.status_collapsible.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            self.status_collapsible.customContextMenuRequested.connect(self._show_cache_context_menu)

        except Exception as e:
            logger.debug(f"Error setting up cache context menu: {e}")

    def _show_cache_context_menu(self, position) -> None:
        """Show cache management context menu."""
        if not self.rom_cache.cache_enabled:
            return

        try:
            menu = QMenu(self)

            # Cache statistics action
            stats_action = QAction("Show Cache Statistics", self)
            stats_action.triggered.connect(self._show_cache_statistics)
            menu.addAction(stats_action)

            # Clear cache action
            clear_action = QAction("Clear Cache", self)
            clear_action.triggered.connect(self._clear_cache_with_confirmation)
            menu.addAction(clear_action)

            # Show at cursor position
            global_pos = self.status_collapsible.mapToGlobal(position)
            menu.exec(global_pos)

        except Exception as e:
            logger.debug(f"Error showing cache context menu: {e}")

    def _show_cache_statistics(self) -> None:
        """Show detailed cache statistics dialog."""
        try:
            stats = self.rom_cache.get_cache_stats()
            session_stats = self._cache_stats

            # Format cache size
            size_bytes = stats.get("total_size_bytes", 0)
            if size_bytes > 1024 * 1024:
                size_str = f"{size_bytes / (1024 * 1024):.1f} MB"
            elif size_bytes > 1024:
                size_str = f"{size_bytes / 1024:.1f} KB"
            else:
                size_str = f"{size_bytes} bytes"

            message = f"""Cache Statistics:

Directory: {stats.get('cache_dir', 'Unknown')}
Total Files: {stats.get('total_files', 0)}
Total Size: {size_str}
Sprite Location Caches: {stats.get('sprite_location_caches', 0)}
ROM Info Caches: {stats.get('rom_info_caches', 0)}
Scan Progress Caches: {stats.get('scan_progress_caches', 0)}

Session Statistics:
Total Requests: {session_stats['total_requests']}
Cache Hits: {session_stats['hits']}
Cache Misses: {session_stats['misses']}"""

            if session_stats["total_requests"] > 0:
                hit_rate = (session_stats["hits"] / session_stats["total_requests"]) * 100
                message += f"\nHit Rate: {hit_rate:.1f}%"

            QMessageBox.information(self, "ROM Cache Statistics", message)

        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to retrieve cache statistics: {e}")

    def _clear_cache_with_confirmation(self) -> None:
        """Clear cache with user confirmation."""
        try:
            reply = QMessageBox.question(
                self,
                "Clear Cache",
                "Are you sure you want to clear the ROM cache?\n\nThis will remove all cached data and may slow down future operations.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )

            if reply == QMessageBox.StandardButton.Yes:
                removed_count = self.rom_cache.clear_cache()
                QMessageBox.information(
                    self,
                    "Cache Cleared",
                    f"Successfully cleared {removed_count} cache files."
                )

                # Reset session stats
                self._cache_stats = {"hits": 0, "misses": 0, "total_requests": 0}
                self._adjacent_offsets_cache.clear()

                # Update status display
                self._update_cache_status_display()

        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to clear cache: {e}")

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
            elif event.key() == Qt.Key.Key_G and event.modifiers() & Qt.KeyboardModifier.ControlModifier:
                # Ctrl+G - Go to offset
                self._show_goto_dialog()
                event.accept()
            elif event.key() == Qt.Key.Key_D and event.modifiers() & Qt.KeyboardModifier.ControlModifier:
                # Ctrl+D - Add bookmark
                self._add_bookmark()
                event.accept()
            elif event.key() == Qt.Key.Key_B and event.modifiers() & Qt.KeyboardModifier.ControlModifier:
                # Ctrl+B - Show bookmarks menu
                if self.bookmarks_menu is not None:
                    self.bookmarks_menu.exec(self.mapToGlobal(self.rect().center()))
                event.accept()

        super().keyPressEvent(event)

    @override
    def closeEvent(self, event: QCloseEvent | None):
        """Handle close event."""
        logger.debug(f"Dialog {self._debug_id} closing")
        self.cleanup()
        if event:
            super().closeEvent(event)

    @override
    def hideEvent(self, event: QHideEvent | None):
        """Handle hide event."""
        logger.debug(f"Dialog {self._debug_id} hiding")
        # Only cleanup workers on hide, not full cleanup (dialog may be shown again)
        self._cleanup_workers()
        self.view_state_manager.handle_hide_event()
        if event:
            super().hideEvent(event)

    def showEvent(self, event):
        """Handle show event."""
        logger.debug(f"Dialog {self._debug_id} showing")
        super().showEvent(event)
        self.view_state_manager.handle_show_event()

    def moveEvent(self, event):
        """Handle dialog move event - constrain to screen bounds"""
        super().moveEvent(event)

        # Skip validation during initialization or if dialog is not visible
        if not self.isVisible():
            return

        from PyQt6.QtGui import QGuiApplication  # noqa: PLC0415
        
        # Defensive check for test environments with mock objects
        try:
            new_pos = event.pos()
            x, y = new_pos.x(), new_pos.y()
        except (AttributeError, TypeError):
            # In test environment with mocks, skip geometry validation
            return

        # Get available screen geometry
        screen = QGuiApplication.primaryScreen()
        if screen:
            available = screen.availableGeometry()
            
            # Defensive check for mock geometry objects in tests
            try:
                available_x = available.x()
                available_y = available.y()
                available_width = available.width()
                available_height = available.height()
                dialog_width = self.width()
                dialog_height = self.height()
                
                # Verify all values are numeric before arithmetic
                if not all(isinstance(v, (int, float)) for v in 
                          [available_x, available_y, available_width, available_height, 
                           dialog_width, dialog_height]):
                    # Skip validation if any values are not numeric (likely mocks)
                    return
                    
                # Ensure dialog stays within screen bounds with small margin
                margin = 50  # Allow some overlap with screen edge
                min_x = available_x - dialog_width + margin
                max_x = available_x + available_width - margin
                min_y = available_y - dialog_height + margin
                max_y = available_y + available_height - margin

                # Constrain position
                constrained_x = max(min_x, min(x, max_x))
                constrained_y = max(min_y, min(y, max_y))
                
                # Move back if position was adjusted
                if constrained_x != x or constrained_y != y:
                    logger.debug(f"Constraining dialog position from ({x},{y}) to ({constrained_x},{constrained_y})")
                    self.move(constrained_x, constrained_y)
                    
            except (AttributeError, TypeError):
                # In test environment with mocks, skip geometry validation
                return

    def _on_search_sprite_found(self, offset: int, quality: float):
        """Handle sprite found during navigation search"""
        if self.browse_tab is not None:
            self.browse_tab.set_offset(offset)

        # Add to history
        self.add_found_sprite(offset, quality)

        self._update_status(f"Found sprite at 0x{offset:06X} (quality: {quality:.2f})")

    def _on_search_complete(self, found: bool):
        """Handle search completion"""
        if not found:
            self._update_status("No sprites found in search direction")

    def _add_bookmark(self):
        """Add current offset to bookmarks"""
        offset = self.get_current_offset()

        # Check if already bookmarked
        for existing_offset, _ in self.bookmarks:
            if existing_offset == offset:
                self._update_status("Offset already bookmarked")
                return

        # Add bookmark with descriptive name
        name, ok = QInputDialog.getText(
            self, "Add Bookmark",
            f"Name for bookmark at 0x{offset:06X}:",
            text=f"Sprite at 0x{offset:06X}"
        )

        if ok and name:
            self.bookmarks.append((offset, name))
            self._update_bookmarks_menu()
            self._update_status(f"Bookmarked: {name}")

    def _update_bookmarks_menu(self):
        """Update bookmarks menu"""
        if self.bookmarks_menu is None:
            return

        self.bookmarks_menu.clear()

        if not self.bookmarks:
            action = self.bookmarks_menu.addAction("No bookmarks")
            action.setEnabled(False)
        else:
            for offset, name in self.bookmarks:
                action = self.bookmarks_menu.addAction(f"{name} (0x{offset:06X})")
                # Use functools.partial to avoid lambda closure
                action.triggered.connect(partial(self._go_to_bookmark, offset))

            self.bookmarks_menu.addSeparator()
            clear_action = self.bookmarks_menu.addAction("Clear All Bookmarks")
            clear_action.triggered.connect(self._clear_bookmarks)

    def _go_to_bookmark(self, offset: int):
        """Go to a bookmarked offset."""
        self.set_offset(offset)

    def _clear_bookmarks(self):
        """Clear all bookmarks"""
        self.bookmarks.clear()
        self._update_bookmarks_menu()
        self._update_status("Bookmarks cleared")

    def _on_similarity_search_requested(self, target_offset: int):
        """Handle similarity search request from preview widget."""
        logger.info(f"Similarity search requested for offset 0x{target_offset:06X}")

        # Navigate to the selected similar sprite
        self.set_offset(target_offset)
        self._update_status(f"Navigated to similar sprite at 0x{target_offset:06X}")

    def _show_goto_dialog(self):
        """Show go to offset dialog"""

        current = self.get_current_offset()
        text, ok = QInputDialog.getText(
            self, "Go to Offset",
            "Enter offset (hex or decimal):",
            text=f"0x{current:06X}"
        )

        if ok and text:
            try:
                # Parse hex or decimal
                offset = int(text, 16) if text.startswith(("0x", "0X")) else int(text)

                # Validate bounds
                if 0 <= offset <= self.rom_size:
                    self.set_offset(offset)
                else:
                    self._update_status(f"Offset out of range: 0x{offset:06X}")
            except ValueError:
                self._update_status(f"Invalid offset: {text}")

    def _load_cached_sprites_for_map(self):
        """Load cached sprites for mini ROM map visualization"""
        if not self.rom_path or not self.mini_rom_map:
            return

        try:
            cached_locations = self.rom_cache.get_sprite_locations(self.rom_path)
            if cached_locations:
                sprites = []
                for _name, info in cached_locations.items():
                    if isinstance(info, dict) and "offset" in info:
                        offset = info["offset"]
                        quality = info.get("quality", 1.0)
                        sprites.append((offset, quality))

                if sprites:
                    self.mini_rom_map.add_found_sprites_batch(sprites)
                    logger.debug(f"Loaded {len(sprites)} sprites to mini map")

        except Exception as e:
            logger.warning(f"Failed to load sprites for mini map: {e}")


def create_manual_offset_dialog(parent: QWidget | None = None) -> UnifiedManualOffsetDialog:
    """Factory function for creating manual offset dialog."""
    return UnifiedManualOffsetDialog(parent)
