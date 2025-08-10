"""
Tab Manager Component

Manages the 4 tabs (Browse, Smart, History, Gallery) and their coordination.
Enhanced for superior visual design in composed implementation.
"""

import os
from typing import TYPE_CHECKING

from PySide6.QtWidgets import QPushButton, QTabWidget, QVBoxLayout, QWidget

if TYPE_CHECKING:
    from core.managers.extraction_manager import ExtractionManager

from utils.logging_config import get_logger

logger = get_logger(__name__)


class TabManagerComponent:
    """
    Manages tabs and their interactions for the Manual Offset Dialog.

    Handles Browse, Smart, History, and Gallery tabs with their respective
    functionality and coordination.
    """

    def __init__(self, dialog):
        """Initialize the tab manager."""
        self.dialog = dialog
        self.tab_widget = None
        self.browse_tab = None
        self.smart_tab = None
        self.history_tab = None
        self.gallery_tab = None
        self.status_collapsible = None
        self.status_panel = None
        self.apply_btn = None

    def create_left_panel(self) -> QWidget:
        """Create the left panel with tabs."""
        panel = QWidget()
        layout = QVBoxLayout(panel)

        # Apply enhanced layout for composed implementation
        if self._is_composed_implementation():
            # Enhanced spacing for better visual hierarchy
            layout.setContentsMargins(12, 12, 12, 12)  # More breathing room
            layout.setSpacing(8)                       # Better element separation
        else:
            # Legacy spacing
            layout.setContentsMargins(6, 6, 6, 6)
            layout.setSpacing(6)

    def _is_composed_implementation(self) -> bool:
        """Check if we're using composed implementation."""
        flag_value = os.environ.get('SPRITEPAL_USE_COMPOSED_DIALOGS', '0').lower()
        return flag_value in ('1', 'true', 'yes', 'on')

        # Create tab widget with enhanced styling
        self.tab_widget = QTabWidget()

        # Apply enhanced styling for composed implementation
        if self._is_composed_implementation():
            self._apply_enhanced_tab_styling()
        return None

    def _apply_enhanced_tab_styling(self) -> None:
        """Apply enhanced visual styling to tab widget."""
        self.tab_widget.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #c0c0c0;
                border-radius: 6px;
                background-color: #fafafa;
                padding: 4px;
            }
            QTabBar::tab {
                background-color: #e1e1e1;
                border: 1px solid #c0c0c0;
                border-bottom-color: transparent;
                border-radius: 4px 4px 0 0;
                padding: 8px 16px;
                margin-right: 2px;
                min-width: 80px;
                font-weight: 500;
            }
            QTabBar::tab:selected {
                background-color: #ffffff;
                border-bottom-color: #ffffff;
                font-weight: 600;
            }
            QTabBar::tab:hover:!selected {
                background-color: #f0f0f0;
            }
            QTabWidget::tab-bar {
                alignment: left;
            }
        """)

        # Import and create tab classes
        try:
            from ui.common.collapsible_group_box import CollapsibleGroupBox
            from ui.components.panels import StatusPanel
            from ui.tabs.manual_offset import (
                SimpleBrowseTab,
                SimpleHistoryTab,
                SimpleSmartTab,
            )
            from ui.tabs.sprite_gallery_tab import SpriteGalleryTab

            # Create tabs
            self.browse_tab = SimpleBrowseTab()
            self.smart_tab = SimpleSmartTab()
            self.history_tab = SimpleHistoryTab()
            self.gallery_tab = SpriteGalleryTab()

            # Add tabs
            self.tab_widget.addTab(self.browse_tab, "Browse")
            self.tab_widget.addTab(self.smart_tab, "Smart")
            self.tab_widget.addTab(self.history_tab, "History")
            self.tab_widget.addTab(self.gallery_tab, "Gallery")

            # Add tab widget with stretch to fill available space
            layout.addWidget(self.tab_widget, 1)

            # Add collapsible status panel (collapsed by default like original)
            self.status_collapsible = CollapsibleGroupBox("Status", collapsed=True)
            self.status_panel = StatusPanel()
            self.status_collapsible.add_widget(self.status_panel)
            layout.addWidget(self.status_collapsible, 0)

            logger.debug("Successfully created all tabs")

        except ImportError as e:
            logger.warning(f"Tab implementations not found: {e}, using placeholders")
            # Add placeholder tabs
            self.tab_widget.addTab(QWidget(), "Browse")
            self.tab_widget.addTab(QWidget(), "Smart")
            self.tab_widget.addTab(QWidget(), "History")
            self.tab_widget.addTab(QWidget(), "Gallery")
            layout.addWidget(self.tab_widget)

        return panel

    def setup_custom_buttons(self, button_box):
        """Set up custom dialog buttons."""
        if button_box:
            # Add Apply button like the original
            apply_btn = QPushButton("Apply Offset")
            button_box.addButton(apply_btn, button_box.ButtonRole.AcceptRole)

            # Store reference to apply button
            self.apply_btn = apply_btn

            # Connect apply button if browse tab is available
            if self.browse_tab and hasattr(self.browse_tab, 'apply_current_offset'):
                apply_btn.clicked.connect(self.browse_tab.apply_current_offset)

    def set_rom_data(self, rom_path: str, rom_size: int, extraction_manager: 'ExtractionManager'):
        """Update tabs with ROM data."""
        # Update each tab with ROM data
        if self.browse_tab and hasattr(self.browse_tab, 'set_rom_data'):
            self.browse_tab.set_rom_size(rom_size)
        if self.gallery_tab and hasattr(self.gallery_tab, 'set_rom_data'):
            self.gallery_tab.set_rom_data(rom_path, rom_size, extraction_manager.get_rom_extractor())

    def set_offset(self, offset: int) -> bool:
        """Set current offset in browse tab."""
        if self.browse_tab and hasattr(self.browse_tab, 'set_offset'):
            self.browse_tab.set_offset(offset)
            return True
        return False

    def get_current_offset(self) -> int:
        """Get current offset from browse tab."""
        if self.browse_tab and hasattr(self.browse_tab, 'get_current_offset'):
            return self.browse_tab.get_current_offset()
        return 0x200000

    def add_found_sprite(self, offset: int, quality: float):
        """Add sprite to history tab."""
        if self.history_tab and hasattr(self.history_tab, 'add_sprite'):
            self.history_tab.add_sprite(offset, quality)

    def cleanup(self):
        """Clean up tab resources."""
        logger.debug("Cleaning up tab manager")
        # Clean up each tab
        for tab in [self.browse_tab, self.smart_tab, self.history_tab, self.gallery_tab]:
            if tab and hasattr(tab, 'cleanup'):
                tab.cleanup()
