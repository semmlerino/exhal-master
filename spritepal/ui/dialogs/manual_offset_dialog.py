"""
Manual Offset Control Dialog

A dedicated window for ROM offset exploration with enhanced controls and visualization.
Refactored to use component-based architecture with SplitterDialog base.
"""

from typing import TYPE_CHECKING, override

if TYPE_CHECKING:
    from spritepal.core.managers.extraction_manager import ExtractionManager

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QCloseEvent, QHideEvent, QKeyEvent, QMouseEvent
from PyQt6.QtWidgets import (
    QDialogButtonBox,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from spritepal.ui.components import SplitterDialog
from spritepal.ui.components.panels import (
    ImportExportPanel,
    ScanControlsPanel,
    StatusPanel,
)
from spritepal.ui.components.visualization import ROMMapWidget
from spritepal.ui.dialogs.services import ViewStateManager
from spritepal.ui.rom_extraction.widgets.manual_offset_widget import ManualOffsetWidget
from spritepal.ui.styles import get_panel_style
from spritepal.ui.widgets.sprite_preview_widget import SpritePreviewWidget
from spritepal.utils.logging_config import get_logger

logger = get_logger(__name__)


class ManualOffsetDialog(SplitterDialog):
    """Dialog window for manual ROM offset control with enhanced features"""

    # Signals
    offset_changed: pyqtSignal = pyqtSignal(int)  # Current offset changed
    sprite_found: pyqtSignal = pyqtSignal(int, str)  # Sprite found at offset with name

    def __init__(self, parent: "QWidget | None" = None) -> None:
        # UI Components - declare BEFORE super().__init__() to avoid overwriting
        self.rom_map: ROMMapWidget | None = None
        self.offset_widget: ManualOffsetWidget | None = None
        self.scan_controls: ScanControlsPanel | None = None
        self.import_export: ImportExportPanel | None = None
        self.status_panel: StatusPanel | None = None
        self.preview_widget: SpritePreviewWidget | None = None
        self.apply_btn: QPushButton | None = None

        super().__init__(
            parent=parent,
            title="Manual Offset Control - SpritePal",
            modal=False,
            size=(1200, 700),  # Fixed reasonable default size
            min_size=(1000, 600),  # Minimum size
            with_status_bar=False,
            orientation=Qt.Orientation.Horizontal,
            splitter_handle_width=6
        )

        # Initialize view state manager for window positioning
        self.view_state_manager = ViewStateManager(self, self)

        self._setup_ui()
        self._connect_signals()

        # Backward compatibility - expose legacy properties for existing code
        self._setup_legacy_compatibility()

    def _connect_controller_signals(self) -> None:
        """Connect controller signals to UI updates (MVP Architecture Phase 2)"""
        # Business operation signals from controller
        self.controller.rom_data_loaded.connect(self._on_rom_data_loaded)
        self.controller.current_offset_updated.connect(self._on_current_offset_updated)
        self.controller.sprite_added_to_collection.connect(self._on_sprite_added_to_collection)

        # Preview signals
        self.controller.preview_updated.connect(self._on_preview_updated)
        self.controller.preview_failed.connect(self._on_preview_failed)

        # Status and progress signals
        self.controller.status_message.connect(self._on_status_message)
        self.controller.progress_updated.connect(self._on_progress_updated)
        self.controller.progress_hidden.connect(self._on_progress_hidden)
        self.controller.cache_status_updated.connect(self._on_cache_status_updated)

        # Search and scan operation signals
        self.controller.search_completed.connect(self._on_search_completed)
        self.controller.scan_started.connect(self._on_scan_started)
        self.controller.scan_finished.connect(self._on_scan_finished)
        self.controller.sprites_imported.connect(self._on_sprites_imported)

        # Business operation signals
        self.controller.offset_applied.connect(self._on_offset_applied)

        # View state manager signals (still connect directly for UI-specific behavior)
        self.view_state_manager.fullscreen_toggled.connect(self._on_fullscreen_toggled)
        self.view_state_manager.title_changed.connect(self.setWindowTitle)

    def _setup_legacy_compatibility(self) -> None:
        """Set up properties for backward compatibility with existing code"""
        # These properties delegate to services for seamless compatibility
        # Properties will be added as needed

    def _on_rom_data_loaded(self, rom_path: str, rom_size: int) -> None:
        """Handle ROM data loaded from controller - pure UI updates"""
        # Update UI components with new ROM data
        if self.offset_widget:
            self.offset_widget.set_rom_size(rom_size)
        if self.rom_map:
            self.rom_map.set_rom_size(rom_size)
        if self.scan_controls:
            extraction_manager, _ = self.rom_data_session.get_managers_safely()
            if extraction_manager:
                self.scan_controls.set_rom_data(rom_path, rom_size, extraction_manager)
                self.scan_controls.set_rom_map(self.rom_map)
        if self.import_export:
            self.import_export.set_rom_data(rom_path, rom_size)
            self.import_export.set_rom_map(self.rom_map)

    def _on_current_offset_updated(self, offset: int) -> None:
        """Handle current offset updated from controller - pure UI updates"""
        # Update UI components with new offset
        if self.rom_map:
            self.rom_map.set_current_offset(offset)
        if self.scan_controls:
            self.scan_controls.set_current_offset(offset)

        # Emit signal for external listeners (backward compatibility)
        self.offset_changed.emit(offset)

    def _on_sprite_added_to_collection(self, offset: int, quality: float) -> None:
        """Handle sprite added to collection from controller - pure UI updates"""
        # Update visualization components
        if self.rom_map:
            self.rom_map.add_found_sprite(offset, quality)
        if self.offset_widget:
            self.offset_widget.add_found_sprite(offset)

    def _on_status_message(self, message: str) -> None:
        """Handle status messages from controller - pure UI updates"""
        if self.status_panel:
            self.status_panel.update_status(message)

    def _on_progress_updated(self, current: int, maximum: int) -> None:
        """Handle progress updates from controller - pure UI updates"""
        if self.status_panel:
            self.status_panel.show_progress(current, maximum)

    def _on_progress_hidden(self) -> None:
        """Handle progress hidden from controller - pure UI updates"""
        if self.status_panel:
            self.status_panel.hide_progress()

    def _on_cache_status_updated(self, message: str, time_saved: float) -> None:
        """Handle cache status updates from controller - pure UI updates"""
        if self.status_panel:
            # Update cache status to reflect any changes
            self.status_panel.update_cache_status()
            # Show cache message in status
            self.status_panel.update_status(message)

    def _on_preview_updated(self, tile_data: bytes, width: int, height: int, sprite_name: str) -> None:
        """Handle preview updated from controller - pure UI updates"""
        if self.preview_widget:
            self.preview_widget.load_sprite_from_4bpp(tile_data, width, height, sprite_name)

    def _on_preview_failed(self, error_msg: str) -> None:
        """Handle preview failed from controller - pure UI updates"""
        if self.preview_widget:
            self.preview_widget.clear()
            self.preview_widget.info_label.setText("No sprite found")

    def _on_search_completed(self, found: bool) -> None:
        """Handle search completed from controller - pure UI updates"""
        if self.offset_widget:
            self.offset_widget.set_navigation_enabled(True)

    def _on_scan_started(self) -> None:
        """Handle scan started from controller - pure UI updates"""
        # Progress is handled by _on_progress_updated

    def _on_scan_finished(self, found_sprites: list) -> None:
        """Handle scan finished from controller - pure UI updates"""
        # Progress hidden is handled by _on_progress_hidden
        # Update import/export with found sprites
        if self.import_export:
            self.import_export.set_found_sprites(found_sprites)

    def _on_sprites_imported(self, sprites: list) -> None:
        """Handle sprites imported from controller - pure UI updates"""
        # Sprites are already added to collection by controller

    def _on_offset_applied(self, offset: int, sprite_name: str) -> None:
        """Handle offset applied from controller - pure UI updates"""
        self.sprite_found.emit(offset, sprite_name)
        self.hide()

    def _on_scan_progress_update(self, current: int) -> None:
        """Handle scan progress update - convert single param to two params for controller"""
        # Get the ROM size as maximum value
        _, rom_size = self.rom_data_session.get_rom_info()
        # Forward to controller with both current and maximum
        self.controller.progress_updated.emit(current, rom_size)

    def _on_fullscreen_toggled(self, is_fullscreen: bool) -> None:
        """Handle fullscreen toggle from view state manager"""
        # UI can react to fullscreen changes if needed

    def _setup_ui(self):
        """Initialize the dialog-specific UI components"""
        # Create left panel with controls
        left_panel = self._create_left_panel()
        self.add_panel(left_panel, stretch_factor=0)

        # Create right panel with preview
        right_panel = self._create_right_panel()
        self.add_panel(right_panel, stretch_factor=1)

        # Set initial panel sizes - optimize for maximum preview area
        self.main_splitter.setSizes([450, 550])  # Give more space to preview panel

        # Override button box to add custom buttons
        self._setup_custom_buttons()

    def _create_left_panel(self) -> QWidget:
        """Create the left control panel"""
        panel = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(3, 3, 3, 3)  # Small margins
        layout.setSpacing(6)  # Tighter spacing between controls

        # ROM Map visualization at the top - more compact
        rom_map_group = QWidget()
        rom_map_group.setStyleSheet(get_panel_style())
        rom_map_layout = QVBoxLayout()
        rom_map_layout.setContentsMargins(8, 6, 8, 6)  # Reduced from 10,10,10,10
        rom_map_layout.setSpacing(3)  # Tighter spacing

        rom_map_label = QLabel("ROM Overview")
        rom_map_label.setStyleSheet("font-weight: bold; font-size: 12px; margin-bottom: 2px;")  # Smaller font and margin
        rom_map_layout.addWidget(rom_map_label)

        self.rom_map = ROMMapWidget(parent=rom_map_group)
        rom_map_layout.addWidget(self.rom_map)

        rom_map_group.setLayout(rom_map_layout)
        layout.addWidget(rom_map_group)

        # Manual offset widget (reusing existing widget) - set proper parent
        self.offset_widget = ManualOffsetWidget(parent=panel)
        layout.addWidget(self.offset_widget)

        # Scan controls panel - set proper parent
        self.scan_controls = ScanControlsPanel(parent=panel)
        layout.addWidget(self.scan_controls)

        # Import/Export panel - set proper parent
        self.import_export = ImportExportPanel(parent=panel)
        layout.addWidget(self.import_export)

        # Status panel - CRITICAL FIX: Pass parent to prevent Qt lifecycle bug
        # Bug #25: StatusPanel QLabel was being deleted prematurely due to missing parent
        self.status_panel = StatusPanel(parent=panel)
        layout.addWidget(self.status_panel)

        # Smaller stretch to reduce empty space
        layout.addStretch(1)  # Minimal stretch factor

        panel.setLayout(layout)
        panel.setMinimumWidth(450)  # Reduced for more preview space
        panel.setMaximumWidth(550)  # Reduced for more preview space

        return panel

    def _create_right_panel(self) -> QWidget:
        """Create the right preview panel - optimized for maximum space efficiency"""
        panel = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)  # Zero margins for maximum efficiency
        layout.setSpacing(0)  # Zero spacing for maximum efficiency

        # Sprite preview - set proper parent to prevent Qt lifecycle bugs
        # Note: Title is no longer used since QGroupBox was removed for efficiency
        self.preview_widget = SpritePreviewWidget("Live Preview", parent=panel)
        layout.addWidget(self.preview_widget)

        panel.setLayout(layout)
        return panel

    def _setup_custom_buttons(self):
        """Set up custom dialog buttons"""
        if self.button_box:
            # Clear existing buttons
            self.button_box.clear()

            # Add custom buttons
            self.apply_btn = self.button_box.addButton("Apply Offset", QDialogButtonBox.ButtonRole.AcceptRole)
            self.apply_btn.setToolTip("Use the current offset for extraction")

            close_btn = self.button_box.addButton("Close", QDialogButtonBox.ButtonRole.RejectRole)
            self.apply_btn.clicked.connect(self._apply_offset)
            if close_btn:
                close_btn.clicked.connect(self.hide)  # Hide instead of close to maintain state

    def _connect_signals(self):
        """Connect internal signals"""
        # Connect offset widget signals
        self.offset_widget.offset_changed.connect(self._on_offset_changed)
        self.offset_widget.find_next_clicked.connect(self._find_next_sprite)
        self.offset_widget.find_prev_clicked.connect(self._find_prev_sprite)

        # Connect ROM map
        self.rom_map.offset_clicked.connect(self._on_map_clicked)

        # Connect scan controls - delegate to controller
        self.scan_controls.sprite_found.connect(self.controller.handle_sprite_found_during_scan)
        self.scan_controls.scan_status_changed.connect(self.controller.status_message)
        # Progress update needs special handling - scan controls only emit current, but we need max too
        self.scan_controls.progress_update.connect(self._on_scan_progress_update)
        self.scan_controls.scan_started.connect(lambda: self.controller.handle_scan_started(self.rom_data_session.get_rom_info()[1]))
        self.scan_controls.scan_finished.connect(lambda sprites: self.controller.handle_scan_finished(sprites))

        # Connect import/export - delegate to controller
        self.import_export.sprites_imported.connect(self.controller.handle_sprites_imported)
        self.import_export.status_changed.connect(self.controller.status_message)

        # Connect custom buttons
        if self.apply_btn:
            _ = self.apply_btn.clicked.connect(self._apply_offset)

    def set_rom_data(self, rom_path: str, rom_size: int, extraction_manager: "ExtractionManager") -> None:
        """Set ROM data for the dialog"""
        # Delegate to controller (MVP Architecture Phase 2)
        self.controller.set_rom_data(rom_path, rom_size, extraction_manager)

    def get_current_offset(self) -> int:
        """Get the current offset value"""
        # Delegate to controller (MVP Architecture Phase 2)
        return self.controller.get_current_offset()

    def set_offset(self, offset: int) -> None:
        """Set the current offset"""
        # Update UI widget first
        if self.offset_widget:
            self.offset_widget.set_offset(offset)
        # Delegate business logic to controller (MVP Architecture Phase 2)
        self.controller.set_current_offset(offset)

    def _on_offset_changed(self, offset: int) -> None:
        """Handle offset changes from the widget"""
        # Delegate to controller (MVP Architecture Phase 2)
        self.controller.set_current_offset(offset)

    def _on_map_clicked(self, offset: int) -> None:
        """Handle clicks on the ROM map"""
        self.set_offset(offset)

    def _find_next_sprite(self) -> None:
        """Find next sprite offset"""
        if self.offset_widget:
            step_size = self.offset_widget.get_step_size()
            # Delegate to controller (MVP Architecture Phase 2)
            self.controller.find_next_sprite(step_size)

    def _find_prev_sprite(self) -> None:
        """Find previous sprite offset"""
        if self.offset_widget:
            step_size = self.offset_widget.get_step_size()
            # Delegate to controller (MVP Architecture Phase 2)
            self.controller.find_previous_sprite(step_size)

    def _apply_offset(self) -> None:
        """Apply the current offset and close dialog"""
        # Delegate to controller (MVP Architecture Phase 2)
        self.controller.apply_current_offset()

    def add_found_sprite(self, offset: int, quality: float = 1.0) -> None:
        """Add a found sprite to the visualization"""
        # Delegate to controller (MVP Architecture Phase 2)
        self.controller.add_found_sprite(offset, quality)

    @override
    def keyPressEvent(self, a0: QKeyEvent | None):
        """Handle keyboard shortcuts"""
        # Let the offset widget handle its shortcuts first
        if a0 and self.offset_widget:
            self.offset_widget.keyPressEvent(a0)

        # Dialog-specific shortcuts - delegate to controller
        if a0:
            if a0.key() == Qt.Key.Key_Escape:
                # Delegate to controller (MVP Architecture Phase 2)
                if self.controller.handle_escape_key():
                    a0.accept()
                else:
                    self.hide()
                    a0.accept()
            elif a0.key() == Qt.Key.Key_F11:
                # Delegate to controller (MVP Architecture Phase 2)
                self.controller.toggle_fullscreen()
                a0.accept()
            elif a0.key() == Qt.Key.Key_R and a0.modifiers() == Qt.KeyboardModifier.ControlModifier:
                # Ctrl+R to reset dialog position if it gets stuck off-screen
                self.view_state_manager.reset_to_safe_position()
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
            # Delegate to controller (MVP Architecture Phase 2)
            self.controller.toggle_fullscreen()
            a0.accept()
            return

        super().mouseDoubleClickEvent(a0)

    def _cleanup_workers(self) -> None:
        """Clean up any running worker threads with timeouts to prevent hangs"""
        # Delegate to controller (MVP Architecture Phase 2)
        self.controller.cleanup_workers()

        # Clean up scan controls workers
        if hasattr(self, "scan_controls") and self.scan_controls:
            try:
                self.scan_controls.cleanup_workers()
            except RuntimeError as e:
                logger.warning(f"Error cleaning up scan controls workers: {e}")

    @override
    def closeEvent(self, a0: QCloseEvent | None):
        """Handle close event - clean up and close properly"""
        self._cleanup_workers()
        if a0:
            super().closeEvent(a0)  # Let parent handle close event normally

    @override
    def hideEvent(self, a0: QHideEvent | None):
        """Handle hide event - cleanup workers and save position"""
        self._cleanup_workers()
        # Delegate to controller (MVP Architecture Phase 2)
        self.controller.handle_hide_event()

        if a0:
            super().hideEvent(a0)

    def showEvent(self, event):  # noqa: N802
        """Handle show event - restore position if available"""
        super().showEvent(event)
        # Delegate to controller (MVP Architecture Phase 2)
        self.controller.handle_show_event()
