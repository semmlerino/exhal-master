"""
ROM extraction panel for SpritePal
"""

import os
from typing import Any

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtGui import QCloseEvent
from PyQt6.QtWidgets import (
    QApplication,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QLabel,
    QProgressBar,
    QPushButton,
    QSizePolicy,
    QSpacerItem,
    QSplitter,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from spritepal.core.managers import get_extraction_manager
from spritepal.ui.dialogs import UserErrorDialog
from spritepal.ui.dialogs.manual_offset_dialog import ManualOffsetDialog
from spritepal.ui.rom_extraction.state_manager import (
    ExtractionState,
    ExtractionStateManager,
)
from spritepal.ui.rom_extraction.widgets import (
    CGRAMSelectorWidget,
    ModeSelectorWidget,
    OutputNameWidget,
    ROMFileWidget,
    SpriteSelectorWidget,
)
from spritepal.ui.rom_extraction.workers import SpritePreviewWorker, SpriteScanWorker
from spritepal.ui.widgets.sprite_preview_widget import SpritePreviewWidget
from spritepal.utils.constants import (
    SETTINGS_KEY_LAST_INPUT_ROM,
    SETTINGS_NS_ROM_INJECTION,
)
from spritepal.utils.logging_config import get_logger
from spritepal.utils.settings_manager import get_settings_manager

logger = get_logger(__name__)

# UI Spacing Constants
SPACING_SMALL = 6
SPACING_MEDIUM = 10
SPACING_LARGE = 16
SPACING_XLARGE = 20
BUTTON_MIN_HEIGHT = 32
COMBO_MIN_WIDTH = 200
BUTTON_MAX_WIDTH = 150
LABEL_MIN_WIDTH = 120


class ROMExtractionPanel(QWidget):
    """Panel for ROM-based sprite extraction"""

    # Signals
    files_changed = pyqtSignal()
    extraction_ready = pyqtSignal(bool)
    rom_extraction_requested = pyqtSignal(
        str, int, str, str
    )  # rom_path, offset, output_base, sprite_name
    output_name_changed = pyqtSignal(str)  # Emit when output name changes in ROM panel

    def __init__(self, parent=None):
        super().__init__(parent)
        self.rom_path = ""
        self.sprite_locations = {}
        # Get extraction manager and ROM extractor
        self.extraction_manager = get_extraction_manager()
        self.rom_extractor = self.extraction_manager.get_rom_extractor()
        self.rom_size = 0  # Track ROM size for slider limits
        self._manual_offset_mode = True  # Default to manual offset mode

        # State manager for coordinating operations
        self.state_manager = ExtractionStateManager()
        self.state_manager.state_changed.connect(self._on_state_changed)

        # Worker references to track and clean up
        self.preview_worker = None
        self.search_worker = None
        self.scan_worker = None

        self._setup_ui()
        self._load_last_rom()

    def _setup_ui(self):
        """Initialize the user interface"""
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)

        # Create splitter for left panel and preview
        splitter = QSplitter()
        splitter.setHandleWidth(SPACING_MEDIUM)

        # Left panel for controls
        left_panel = QWidget()
        layout = QVBoxLayout()
        layout.setSpacing(SPACING_LARGE)
        layout.setContentsMargins(SPACING_MEDIUM, SPACING_MEDIUM, SPACING_MEDIUM, SPACING_MEDIUM)

        # ROM file selection widget
        self.rom_file_widget = ROMFileWidget()
        self.rom_file_widget.browse_clicked.connect(self._browse_rom)
        self.rom_file_widget.partial_scan_detected.connect(self._on_partial_scan_detected)
        layout.addWidget(self.rom_file_widget)

        # Mode selector widget
        self.mode_selector_widget = ModeSelectorWidget()
        self.mode_selector_widget.mode_changed.connect(self._on_mode_changed)
        layout.addWidget(self.mode_selector_widget)

        # Sprite selector widget
        self.sprite_selector_widget = SpriteSelectorWidget()
        self.sprite_selector_widget.sprite_changed.connect(self._on_sprite_changed)
        self.sprite_selector_widget.find_sprites_clicked.connect(self._find_sprites)
        self.sprite_selector_widget.setVisible(False)  # Hide by default (manual mode is default)
        layout.addWidget(self.sprite_selector_widget)

        # Manual offset control button (replaces embedded widget)
        self.manual_offset_button = QPushButton("Open Manual Offset Control")
        self.manual_offset_button.setMinimumHeight(BUTTON_MIN_HEIGHT * 2)  # Make it prominent
        _ = self.manual_offset_button.clicked.connect(self._open_manual_offset_dialog)
        self.manual_offset_button.setVisible(True)  # Show by default (manual mode)
        self.manual_offset_button.setToolTip("Open advanced manual offset control window (Ctrl+M)")
        self.manual_offset_button.setStyleSheet("""
            QPushButton {
                background-color: #4488dd;
                color: white;
                font-weight: bold;
                font-size: 14px;
                border-radius: 6px;
                padding: 10px;
            }
            QPushButton:hover {
                background-color: #5599ee;
            }
            QPushButton:pressed {
                background-color: #3377cc;
            }
        """)
        layout.addWidget(self.manual_offset_button)

        # Manual offset status label
        self.manual_offset_status = QLabel("Use Manual Offset Control to explore ROM offsets")
        self.manual_offset_status.setStyleSheet("""
            padding: 8px;
            background: #2b2b2b;
            border: 1px solid #444444;
            border-radius: 4px;
            color: #cccccc;
        """)
        self.manual_offset_status.setWordWrap(True)
        self.manual_offset_status.setVisible(True)
        layout.addWidget(self.manual_offset_status)

        # Reference to dialog (will be created on demand)
        self._manual_offset_dialog = None
        self._manual_offset = 0x200000  # Default offset

        # CGRAM selector widget
        self.cgram_selector_widget = CGRAMSelectorWidget()
        self.cgram_selector_widget.browse_clicked.connect(self._browse_cgram)
        layout.addWidget(self.cgram_selector_widget)

        # Output name widget
        self.output_name_widget = OutputNameWidget()
        self.output_name_widget.text_changed.connect(self._check_extraction_ready)
        self.output_name_widget.text_changed.connect(self.output_name_changed.emit)
        layout.addWidget(self.output_name_widget)

        # Add smaller vertical spacer at the bottom (reduced to not dominate manual offset widget)
        layout.addItem(QSpacerItem(0, 20, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Preferred))
        left_panel.setLayout(layout)

        # Add preview widget to right side
        self.preview_widget = SpritePreviewWidget("Sprite Preview")
        self.preview_widget.setMinimumWidth(300)

        # Set size constraints for left panel
        left_panel.setMinimumWidth(450)
        left_panel.setMaximumWidth(700)

        # Add panels to splitter
        splitter.addWidget(left_panel)
        splitter.addWidget(self.preview_widget)
        splitter.setStretchFactor(0, 0)  # Don't stretch left panel
        splitter.setStretchFactor(1, 1)  # Make preview expand
        splitter.setSizes([600, 300])  # Better default proportions

        # Add splitter to main layout
        main_layout.addWidget(splitter)
        self.setLayout(main_layout)

    def _browse_rom(self):
        """Browse for ROM file"""
        settings = get_settings_manager()
        default_dir = settings.get_default_directory()

        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Select ROM File",
            default_dir,
            "SNES ROM Files (*.sfc *.smc);;All Files (*.*)"
        )

        if filename:
            self._load_rom_file(filename)

    def _on_partial_scan_detected(self, scan_info: dict[str, Any]):
        """Handle detection of partial scan cache"""
        # Show resume dialog to ask user what to do
        from spritepal.ui.dialogs import ResumeScanDialog
        user_choice = ResumeScanDialog.show_resume_dialog(scan_info, self)

        if user_choice == ResumeScanDialog.RESUME:
            # User wants to resume - trigger scan dialog
            self._find_sprites()
        elif user_choice == ResumeScanDialog.START_FRESH:
            # User wants fresh scan - will be handled when they click Find Sprites
            # Just inform them
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.information(
                self,
                "Fresh Scan",
                "The partial scan cache will be ignored. \n"
                "Click 'Find Sprites' to start a fresh scan."
            )
        # If CANCEL, do nothing

    def _load_last_rom(self):
        """Load the last used ROM file from settings"""
        try:
            settings = get_settings_manager()
            last_rom = settings.get_value(
                SETTINGS_NS_ROM_INJECTION, SETTINGS_KEY_LAST_INPUT_ROM, ""
            )

            if last_rom and os.path.exists(last_rom):
                logger.info(f"Loading last used ROM: {last_rom}")
                self._load_rom_file(last_rom)
            elif last_rom:
                logger.warning(f"Last used ROM not found: {last_rom}")
            else:
                logger.debug("No last used ROM in settings")

        except Exception:
            logger.exception("Error loading last ROM")

    def _load_rom_file(self, filename: str):
        """Load a ROM file and update UI"""
        try:
            logger.info(f"Loading ROM file: {filename}")

            # Update internal state
            self.rom_path = filename
            self.rom_file_widget.set_rom_path(filename)

            # Get ROM size for slider limits
            try:
                with open(filename, "rb") as f:
                    f.seek(0, 2)  # Seek to end
                    self.rom_size = f.tell()
                    # Update dialog if it exists
                    if self._manual_offset_dialog:
                        self._manual_offset_dialog.set_rom_data(self.rom_path, self.rom_size, self.extraction_manager)
                    logger.debug(f"ROM size: {self.rom_size} bytes (0x{self.rom_size:X})")
            except Exception as e:
                logger.warning(f"Could not determine ROM size: {e}")
                self.rom_size = 0x400000  # Default 4MB

            # Save to settings
            settings = get_settings_manager()
            settings.set_value(SETTINGS_NS_ROM_INJECTION, SETTINGS_KEY_LAST_INPUT_ROM, filename)
            settings.set_last_used_directory(os.path.dirname(filename))
            logger.debug(f"Saved ROM to settings: {filename}")

            # Read ROM header for info display
            try:
                header = self.rom_extractor.rom_injector.read_rom_header(filename)

                # Get sprite configurations to check match status
                sprite_configs = self.rom_extractor.sprite_config_loader.get_game_sprites(
                    header.title, header.checksum
                )

                # Update ROM info display
                info_text = f"<b>Title:</b> {header.title}<br>"
                info_text += f"<b>Checksum:</b> 0x{header.checksum:04X}<br>"

                # Check if this matches known configurations
                if sprite_configs:
                    info_text += '<span style="color: green;"><b>Status:</b> Configuration found ✓</span>'
                else:
                    info_text += '<span style="color: orange;"><b>Status:</b> Unknown ROM version - use "Find Sprites" to scan</span>'

                self.rom_file_widget.set_info_text(info_text)

            except Exception as e:
                logger.warning(f"Could not read ROM header: {e}")
                self.rom_file_widget.set_info_text('<span style="color: red;">Error reading ROM header</span>')

            # Load sprite locations from ROM
            self._load_rom_sprites()

            # Notify that files changed
            self.files_changed.emit()

            logger.info(f"Successfully loaded ROM: {os.path.basename(filename)}")

        except Exception:
            logger.exception("Error loading ROM file %s", filename)
            # Clear ROM on error
            self.rom_path = ""
            self.rom_file_widget.set_rom_path("")

    def _open_manual_offset_dialog(self):
        """Open the manual offset control dialog"""
        if not self.rom_path:
            UserErrorDialog.show_error(
                self,
                "Please load a ROM file first",
                "A ROM must be loaded before using manual offset control."
            )
            return

        # Create or get existing dialog instance
        if self._manual_offset_dialog is None:
            self._manual_offset_dialog = ManualOffsetDialog.get_instance(self)
            # Connect signals
            self._manual_offset_dialog.offset_changed.connect(self._on_dialog_offset_changed)
            self._manual_offset_dialog.sprite_found.connect(self._on_dialog_sprite_found)

        # Update dialog with current ROM data
        self._manual_offset_dialog.set_rom_data(
            self.rom_path, self.rom_size, self.extraction_manager
        )

        # Set current offset
        self._manual_offset_dialog.set_offset(self._manual_offset)

        # Show the dialog
        self._manual_offset_dialog.show()
        self._manual_offset_dialog.raise_()
        self._manual_offset_dialog.activateWindow()

    def _on_dialog_offset_changed(self, offset: int):
        """Handle offset changes from the dialog"""
        self._manual_offset = offset
        self._preview_manual_offset(offset)
        # Update status label
        self.manual_offset_status.setText(f"Current offset: 0x{offset:06X}")

    def _on_dialog_sprite_found(self, offset: int, sprite_name: str):
        """Handle sprite found signal from dialog"""
        self._manual_offset = offset
        # Update status to show sprite was selected
        self.manual_offset_status.setText(f"Selected sprite at 0x{offset:06X}")
        # Check extraction readiness
        self._check_extraction_ready()

    def _browse_cgram(self):
        """Browse for CGRAM file"""
        settings = get_settings_manager()

        # Try to use ROM directory as default
        default_dir = (
            os.path.dirname(self.rom_path)
            if self.rom_path
            else settings.get_default_directory()
        )

        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Select CGRAM File ()",
            default_dir,
            "CGRAM Files (*.dmp *.bin);;All Files (*.*)"
        )

        if filename:
            self.cgram_selector_widget.set_cgram_path(filename)
            settings.set_last_used_directory(os.path.dirname(filename))

    def _load_rom_sprites(self):
        """Load known sprite locations from ROM"""
        self.sprite_selector_widget.clear()
        self.sprite_locations = {}

        if not self.rom_path:
            return

        try:
            # Check if sprites come from cache
            from spritepal.utils.rom_cache import get_rom_cache
            rom_cache = get_rom_cache()
            cached_locations = rom_cache.get_sprite_locations(self.rom_path)
            is_from_cache = bool(cached_locations)

            # Get known sprite locations
            locations = self.extraction_manager.get_known_sprite_locations(self.rom_path)

            if locations:
                # Show count of known sprites to make it clear they're available
                cache_text = " (cached)" if is_from_cache else ""
                self.sprite_selector_widget.add_sprite(
                    f"-- {len(locations)} Known Sprites Available{cache_text} --", None
                )

                # Add separator for clarity
                self.sprite_selector_widget.insert_separator(1)

                for name, pointer in locations.items():
                    display_name = name.replace("_", " ").title()
                    # Add cache indicator if sprites came from cache
                    cache_indicator = " 💾" if is_from_cache else ""
                    self.sprite_selector_widget.add_sprite(
                        f"{display_name} (0x{pointer.offset:06X}){cache_indicator}",
                        (name, pointer.offset)
                    )
                self.sprite_locations = locations
                self.sprite_selector_widget.set_enabled(True)

                # Change button text to indicate scanner is optional
                self.sprite_selector_widget.set_find_button_text("Scan for More Sprites")
                self.sprite_selector_widget.set_find_button_tooltip(
                    ": Scan ROM for additional sprites not in the known list"
                )
                self.sprite_selector_widget.set_find_button_enabled(True)
            else:
                self.sprite_selector_widget.add_sprite("No known sprites - use scanner", None)
                self.sprite_selector_widget.set_enabled(False)

                # Change button text to indicate scanner is needed
                self.sprite_selector_widget.set_find_button_text("Find Sprites")
                self.sprite_selector_widget.set_find_button_tooltip(
                    "Scan ROM for valid sprite offsets (required for unknown ROMs)"
                )
                self.sprite_selector_widget.set_find_button_enabled(True)

        except Exception:
            logger.exception("Failed to load sprite locations")
            self.sprite_selector_widget.add_sprite("Error loading ROM", None)
            self.sprite_selector_widget.set_enabled(False)

    def _on_sprite_changed(self, index: int):
        """Handle sprite selection change"""
        logger.debug(f"Sprite selection changed to index: {index}")
        try:
            if index > 0:
                logger.debug("Sprite selected, getting data")
                data = self.sprite_selector_widget.get_current_data()
                logger.debug(f"Combo data: {data}")

                if data:
                    sprite_name, offset = data
                    logger.debug(f"Parsed sprite: {sprite_name}, offset: 0x{offset:06X}")

                    self.sprite_selector_widget.set_offset_text(f"0x{offset:06X}")
                    logger.debug("Updated offset label")

                    # Auto-generate output name based on sprite
                    current_output = self.output_name_widget.get_output_name()
                    if not current_output:
                        new_name = f"{sprite_name}_sprites"
                        logger.debug(f"Auto-generating output name: {new_name}")
                        self.output_name_widget.set_output_name(new_name)

                    # Show preview of selected sprite
                    logger.debug("Showing preview of selected sprite")
                    self._preview_sprite(sprite_name, offset)
                else:
                    logger.warning("No data found for selected sprite")
            else:
                logger.debug("No sprite selected, clearing displays")
                self.sprite_selector_widget.set_offset_text("--")
                self.preview_widget.clear()

            logger.debug("Calling _check_extraction_ready")
            self._check_extraction_ready()
            logger.debug("Sprite change handling completed successfully")

        except Exception:
            logger.exception("Error in _on_sprite_changed")
            # Try to clear displays on error
            try:
                self.sprite_selector_widget.set_offset_text("Error")
                self.preview_widget.clear()
            except Exception:
                pass  # Silently ignore errors when trying to clear displays

    def _check_extraction_ready(self):
        """Check if extraction is ready - override to handle manual mode"""
        try:
            # Check common requirements
            has_rom = bool(self.rom_path)
            has_output_name = bool(self.output_name_widget.get_output_name())

            if self._manual_offset_mode:
                # In manual mode, just need ROM and output name
                ready = has_rom and has_output_name
            else:
                # In preset mode, also need sprite selection
                has_sprite = self.sprite_selector_widget.get_current_index() > 0
                ready = has_rom and has_sprite and has_output_name

            logger.debug(f"Extraction ready: {ready} (manual_mode={self._manual_offset_mode})")
            self.extraction_ready.emit(ready)

        except Exception:
            logger.exception("Error in _check_extraction_ready")
            self.extraction_ready.emit(False)

    def get_extraction_params(self) -> dict[str, Any] | None:
        """Get parameters for ROM extraction"""
        if not self.rom_path:
            return None

        # Handle manual mode
        if self._manual_offset_mode:
            offset = self._manual_offset
            sprite_name = f"manual_0x{offset:X}"
        else:
            # Preset mode
            if self.sprite_selector_widget.get_current_index() <= 0:
                return None
            data = self.sprite_selector_widget.get_current_data()
            if not data:
                return None
            sprite_name, offset = data

        return {
            "rom_path": self.rom_path,
            "sprite_offset": offset,
            "sprite_name": sprite_name,
            "output_base": self.output_name_widget.get_output_name(),
            "cgram_path": (
                self.cgram_selector_widget.get_cgram_path() if self.cgram_selector_widget.get_cgram_path() else None
            ),
        }

    def clear_files(self):
        """Clear all file selections"""
        self.rom_path = ""
        self.rom_file_widget.clear()
        self.cgram_selector_widget.clear()
        self.output_name_widget.clear()
        self.sprite_selector_widget.clear()
        self.sprite_locations = {}
        self._check_extraction_ready()
        self.preview_widget.clear()
        self.rom_file_widget.set_info_text("No ROM loaded")

    def _preview_sprite(self, sprite_name: str, offset: int):
        """Preview sprite from ROM"""
        if not self.rom_path:
            return

        # Check if we can start preview
        if not self.state_manager.can_preview:
            logger.warning("Cannot start preview - another operation is in progress")
            return

        # Transition to preview state
        if not self.state_manager.start_preview():
            logger.error("Failed to transition to preview state")
            return

        # Start preview loading in background
        self.preview_widget.info_label.setText("Loading preview...")

        # Get sprite config with offset variants
        sprite_config = None
        if sprite_name in self.sprite_locations:
            sprite_config = self.sprite_locations[sprite_name]

        # Clean up any existing preview worker
        if self.preview_worker:
            self.preview_worker.quit()
            self.preview_worker.wait()

        # Create and start preview worker
        self.preview_worker = SpritePreviewWorker(
            self.rom_path, offset, sprite_name, self.rom_extractor, sprite_config
        )
        self.preview_worker.preview_ready.connect(self._on_preview_ready)
        self.preview_worker.preview_error.connect(self._on_preview_error)
        self.preview_worker.finished.connect(
            lambda: self.state_manager.finish_preview()
        )
        self.preview_worker.start()

    def _on_preview_ready(
        self, tile_data: bytes, width: int, height: int, sprite_name: str
    ):
        """Handle preview data ready"""
        self.preview_widget.load_sprite_from_4bpp(tile_data, width, height, sprite_name)

    def _on_preview_error(self, error_msg: str):
        """Handle preview error"""
        self.preview_widget.clear()
        self.preview_widget.info_label.setText("Unable to load preview")

        # Show user-friendly error dialog for significant errors
        if "decompression" in error_msg.lower() or "hal" in error_msg.lower():
            # For decompression errors, just update the preview quietly
            # since this is expected when browsing
            pass
        else:
            # For other errors, show dialog
            UserErrorDialog.show_error(self, error_msg, error_msg)

    def _find_sprites(self):
        """Open dialog to scan for sprite offsets"""
        if not self.rom_path:
            return

        # Check if we can start scanning
        if not self.state_manager.can_scan:
            logger.warning("Cannot start scan - another operation is in progress")
            return

        # Transition to scanning state
        if not self.state_manager.start_scanning():
            logger.error("Failed to transition to scanning state")
            return

        try:
            # Create scanning dialog
            dialog = QDialog(self)
            dialog.setWindowTitle("Find Sprites")
            dialog.setMinimumSize(600, 400)

            layout = QVBoxLayout()

            # Cache status label
            cache_status_label = QLabel("Checking cache...")
            cache_status_label.setStyleSheet("""
                QLabel {
                    background-color: #e3f2fd;
                    border: 1px solid #2196f3;
                    border-radius: 4px;
                    padding: 8px;
                    font-weight: bold;
                    color: #1976d2;
                }
            """)
            layout.addWidget(cache_status_label)

            # Progress bar
            progress_bar = QProgressBar()
            progress_bar.setTextVisible(True)
            layout.addWidget(progress_bar)

            # Results text area
            results_text = QTextEdit()
            results_text.setReadOnly(True)
            results_text.setPlainText("Starting sprite scan...\n\n")
            layout.addWidget(results_text)

            # Buttons
            button_box = QDialogButtonBox(
                QDialogButtonBox.StandardButton.Close | QDialogButtonBox.StandardButton.Apply
            )
            apply_btn = button_box.button(QDialogButtonBox.StandardButton.Apply)
            if apply_btn:
                apply_btn.setText("Use Selected Offset")
                apply_btn.setEnabled(False)

            layout.addWidget(button_box)
            dialog.setLayout(layout)

            # Clean up any existing scan worker
            if self.scan_worker:
                self.scan_worker.quit()
                self.scan_worker.wait()

            # Check for cached scan results
            from spritepal.utils.rom_cache import get_rom_cache
            rom_cache = get_rom_cache()

            # Define scan parameters (must match SpriteScanWorker)
            scan_params = {
                "start_offset": 0xC0000,
                "end_offset": 0xF0000,
                "alignment": 0x100
            }
            partial_cache = rom_cache.get_partial_scan_results(self.rom_path, scan_params)

            # Determine whether to use cache based on user choice
            use_cache = True  # Default to using cache

            if partial_cache and not partial_cache.get("completed", False):
                # Show resume dialog to ask user
                from spritepal.ui.dialogs import ResumeScanDialog
                user_choice = ResumeScanDialog.show_resume_dialog(partial_cache, self)

                if user_choice == ResumeScanDialog.CANCEL:
                    # User cancelled - close scan dialog and return
                    dialog.reject()
                    return
                if user_choice == ResumeScanDialog.START_FRESH:
                    use_cache = False
                    cache_status_label.setText("Starting fresh scan (ignoring cache)")
                    cache_status_label.setStyleSheet("""
                        QLabel {
                            background-color: #fff3e0;
                            border: 1px solid #ff9800;
                            border-radius: 4px;
                            padding: 8px;
                            font-weight: bold;
                            color: #e65100;
                        }
                    """)
                else:  # RESUME
                    cache_status_label.setText("📊 Resuming from cached progress...")
                    cache_status_label.setStyleSheet("""
                        QLabel {
                            background-color: #e8f5e9;
                            border: 1px solid #4caf50;
                            border-radius: 4px;
                            padding: 8px;
                            font-weight: bold;
                            color: #2e7d32;
                        }
                    """)
            else:
                cache_status_label.setText("No cache found - starting fresh scan")
                cache_status_label.setStyleSheet("""
                    QLabel {
                        background-color: #fff3e0;
                        border: 1px solid #ff9800;
                        border-radius: 4px;
                        padding: 8px;
                        font-weight: bold;
                        color: #e65100;
                    }
                """)

            # Run scan in worker thread with cache preference
            self.scan_worker = SpriteScanWorker(self.rom_path, self.rom_extractor, use_cache=use_cache)

            found_offsets = []
            selected_offset = None

            # Make scan_params accessible to all handler functions

            def on_progress(current, total):
                progress_bar.setValue(int((current / total) * 100))
                progress_bar.setFormat(f"Scanning... {current}/{total}")

            def on_sprite_found(sprite_info):
                nonlocal found_offsets
                found_offsets.append(sprite_info)

                text = results_text.toPlainText()
                text += f"Found sprite at {sprite_info['offset_hex']}:\n"
                text += f"  - Tiles: {sprite_info['tile_count']}\n"
                text += f"  - Alignment: {sprite_info['alignment']}\n"
                text += f"  - Quality: {sprite_info['quality']:.2f}\n"
                text += f"  - Size: {sprite_info['compressed_size']} bytes compressed\n"
                if "size_limit_used" in sprite_info:
                    text += f"  - Size limit: {sprite_info['size_limit_used']} bytes\n"
                text += "\n"
                results_text.setPlainText(text)

                # Enable apply button after first find
                if len(found_offsets) == 1 and apply_btn:
                    apply_btn.setEnabled(True)

            def on_scan_complete():
                progress_bar.setValue(100)
                progress_bar.setFormat("Scan complete")

                text = results_text.toPlainText()
                text += f"\nScan complete! Found {len(found_offsets)} valid sprite locations.\n"

                if found_offsets:
                    text += "\nBest quality sprites:\n"
                    # Sort by quality before displaying
                    sorted_sprites = sorted(found_offsets, key=lambda x: x["quality"], reverse=True)
                    for i, sprite in enumerate(sorted_sprites[:5]):
                        size_info = f", {sprite['size_limit_used']/1024:.0f}KB limit" if "size_limit_used" in sprite else ""
                        text += f"{i+1}. {sprite['offset_hex']} - Quality: {sprite['quality']:.2f}, {sprite['tile_count']} tiles{size_info}\n"

                    # Save to cache with visual feedback
                    cache_status_label.setText("💾 Saving results to cache...")
                    cache_status_label.setStyleSheet("""
                        QLabel {
                            background-color: #e1f5fe;
                            border: 1px solid #039be5;
                            border-radius: 4px;
                            padding: 8px;
                            font-weight: bold;
                            color: #01579b;
                        }
                    """)
                    QApplication.processEvents()

                    # Convert found sprites to cache format
                    sprite_locations = {}
                    for sprite in found_offsets:
                        name = f"scanned_0x{sprite['offset']:X}"
                        sprite_locations[name] = {
                            "offset": sprite["offset"],
                            "compressed_size": sprite.get("compressed_size"),
                            "quality": sprite.get("quality", 0.0)
                        }

                    # Save to cache (rom_cache is from outer scope)
                    if rom_cache and rom_cache.save_sprite_locations(self.rom_path, sprite_locations):
                        cache_status_label.setText(f"✅ Saved {len(found_offsets)} sprites to cache")
                        cache_status_label.setStyleSheet("""
                            QLabel {
                                background-color: #c8e6c9;
                                border: 1px solid #4caf50;
                                border-radius: 4px;
                                padding: 8px;
                                font-weight: bold;
                                color: #1b5e20;
                            }
                        """)
                        text += "\n✅ Results saved to cache for faster future scans.\n"
                    else:
                        cache_status_label.setText("⚠️ Could not save to cache")
                        text += "\n⚠️ Could not save results to cache.\n"
                else:
                    text += "\nNo valid sprites found in scanned range.\n"
                    if apply_btn:
                        apply_btn.setEnabled(False)

                results_text.setPlainText(text)

            def on_apply():
                nonlocal selected_offset
                if found_offsets:
                    # Use the best quality offset
                    selected_offset = found_offsets[0]["offset"]
                    dialog.accept()

            def on_cache_status(status):
                cache_status_label.setText(f"💾 {status}")
                # Update style based on status
                if "Saving" in status:
                    cache_status_label.setStyleSheet("""
                        QLabel {
                            background-color: #e1f5fe;
                            border: 1px solid #039be5;
                            border-radius: 4px;
                            padding: 8px;
                            font-weight: bold;
                            color: #01579b;
                        }
                    """)
                elif "Resuming" in status:
                    cache_status_label.setStyleSheet("""
                        QLabel {
                            background-color: #e8f5e9;
                            border: 1px solid #4caf50;
                            border-radius: 4px;
                            padding: 8px;
                            font-weight: bold;
                            color: #2e7d32;
                        }
                    """)

            def on_cache_progress(progress):
                # Update cache save progress indicator
                if progress > 0:
                    cache_status_label.setText(f"💾 Saving progress ({progress}%)...")

            # Connect signals
            self.scan_worker.progress.connect(on_progress)
            self.scan_worker.sprite_found.connect(on_sprite_found)
            self.scan_worker.finished.connect(on_scan_complete)
            self.scan_worker.cache_status.connect(on_cache_status)
            self.scan_worker.cache_progress.connect(on_cache_progress)

            def on_dialog_finished(result):
                # Clean up worker
                if self.scan_worker:
                    self.scan_worker.quit()
                    self.scan_worker.wait()
                    self.scan_worker = None

                # Transition back to idle state
                self.state_manager.finish_scanning()

            dialog.finished.connect(on_dialog_finished)
            button_box.rejected.connect(dialog.reject)
            if apply_btn:
                _ = apply_btn.clicked.connect(on_apply)

            # Start scanning
            self.scan_worker.start()

            # Show dialog
            if dialog.exec() == QDialog.DialogCode.Accepted and selected_offset is not None:
                # Add custom sprite to combo box
                sprite_name = f"custom_0x{selected_offset:X}"
                display_name = f"Custom Sprite (0x{selected_offset:06X})"

                # Check if already exists
                exists = False
                for i in range(self.sprite_selector_widget.count()):
                    if self.sprite_selector_widget.item_data(i) and self.sprite_selector_widget.item_data(i)[0] == sprite_name:
                        exists = True
                        self.sprite_selector_widget.set_current_index(i)
                        break

                if not exists:
                    # Add separator before scanner results if we have known sprites
                    if self.sprite_locations and self.sprite_selector_widget.count() > 2:
                        # Find if we already have a scanner section
                        has_scanner_section = False
                        for i in range(self.sprite_selector_widget.count()):
                            text = self.sprite_selector_widget.item_text(i)
                            if "Scanner Results" in text:
                                has_scanner_section = True
                                break

                        if not has_scanner_section:
                            self.sprite_selector_widget.add_sprite("-- Scanner Results (now cached) --", None)

                    # Add new sprite with cache indicator since it was just saved
                    self.sprite_selector_widget.add_sprite(f"{display_name} 💾", (sprite_name, selected_offset))
                    self.sprite_selector_widget.set_current_index(self.sprite_selector_widget.count() - 1)

                logger.info(f"User selected custom sprite offset: 0x{selected_offset:X}")

        except Exception as e:
            logger.exception("Error in sprite scanning")
            # Transition to error state
            self.state_manager.finish_scanning(success=False, error=str(e))

            UserErrorDialog.show_error(
                self,
                "Failed to scan for sprites",
                f"Technical details: {e!s}"
            )

    def _on_mode_changed(self, index: int):
        """Handle extraction mode change"""
        self._manual_offset_mode = (index == 1)

        # Show/hide appropriate controls
        self.sprite_selector_widget.setVisible(not self._manual_offset_mode)
        self.manual_offset_button.setVisible(self._manual_offset_mode)
        self.manual_offset_status.setVisible(self._manual_offset_mode)

        # Clear preview when switching modes
        self.preview_widget.clear()

        # Update extraction ready state
        self._check_extraction_ready()

        # If switching to manual mode with ROM loaded, show current offset preview
        if self._manual_offset_mode and self.rom_path:
            self._preview_manual_offset()


    def _preview_manual_offset(self, offset: int | None = None):
        """Preview sprite at manual offset"""
        if not self.rom_path:
            return

        # Check if we can start preview
        if not self.state_manager.can_preview:
            logger.warning("Cannot start preview - another operation is in progress")
            return

        # Transition to preview state
        if not self.state_manager.start_preview():
            logger.error("Failed to transition to preview state")
            return

        if offset is None:
            offset = self._manual_offset

        # Update status
        self.manual_offset_status.setText(f"Attempting to decompress at 0x{offset:06X}...")

        # Clean up any existing preview worker
        if self.preview_worker:
            self.preview_worker.quit()
            self.preview_worker.wait()

        # Try to find sprite configuration for this offset
        sprite_config = None
        sprite_name = f"manual_0x{offset:X}"

        # Look up known sprite configurations to see if this offset matches
        try:
            if hasattr(self, "sprite_locations") and self.sprite_locations:
                for name, pointer in self.sprite_locations.items():
                    if pointer.offset == offset:
                        sprite_config = pointer
                        sprite_name = name
                        logger.debug(f"Found matching sprite config: {name} at 0x{offset:06X}")
                        break
        except Exception as e:
            logger.debug(f"Error looking up sprite config: {e}")

        # Create preview worker for manual offset with sprite config if found
        self.preview_worker = SpritePreviewWorker(
            self.rom_path, offset, sprite_name, self.rom_extractor, sprite_config
        )
        self.preview_worker.preview_ready.connect(self._on_preview_ready)
        self.preview_worker.preview_error.connect(self._on_manual_preview_error)
        self.preview_worker.finished.connect(
            lambda: self.state_manager.finish_preview()
        )
        self.preview_worker.start()

    def _on_manual_preview_error(self, error_msg: str):
        """Handle preview error in manual mode"""
        self.preview_widget.clear()
        self.preview_widget.info_label.setText("No sprite found")

        # Update status with user-friendly message
        offset = self._manual_offset
        if "decompression" in error_msg.lower() or "hal" in error_msg.lower():
            self.manual_offset_status.setText(
                f"No sprite data at 0x{offset:06X}. Use Manual Offset Control to search."
            )
        else:
            # For unexpected errors, show more detail
            self.manual_offset_status.setText(
                f"Cannot read offset 0x{offset:06X}. Try a different location."
            )

    def _find_next_sprite(self):
        """Find next valid sprite offset - now handled by dialog"""
        # Open dialog if not already open
        if self._manual_offset_dialog and self._manual_offset_dialog.isVisible():
            # Dialog will handle the search
            pass
        else:
            self._open_manual_offset_dialog()

    def _find_prev_sprite(self):
        """Find previous valid sprite offset - now handled by dialog"""
        # Open dialog if not already open
        if self._manual_offset_dialog and self._manual_offset_dialog.isVisible():
            # Dialog will handle the search
            pass
        else:
            self._open_manual_offset_dialog()

    def _on_sprite_found(self, offset: int, quality: float):
        """Handle sprite found during search"""
        self._manual_offset = offset
        self.manual_offset_status.setText(
            f"Found sprite at 0x{offset:06X} (quality: {quality:.2f})"
        )
        # Update dialog if open
        if self._manual_offset_dialog:
            self._manual_offset_dialog.set_offset(offset)
            self._manual_offset_dialog.add_found_sprite(offset, quality)

    def _on_search_complete(self, found: bool):
        """Handle search completion"""
        if not found:
            self.manual_offset_status.setText(
                "No valid sprites found in search range. Try a different area."
            )

    def _on_state_changed(self, old_state: ExtractionState, new_state: ExtractionState):
        """Handle state changes to update UI accordingly"""
        # Update UI elements based on state
        if new_state == ExtractionState.IDLE:
            # Re-enable all controls
            self.rom_file_widget.setEnabled(True)
            self.mode_selector_widget.setEnabled(True)
            self.sprite_selector_widget.set_find_button_enabled(True)
            self.manual_offset_button.setEnabled(True)

        elif new_state in {ExtractionState.LOADING_ROM, ExtractionState.EXTRACTING}:
            # Disable all controls during critical operations
            self.rom_file_widget.setEnabled(False)
            self.mode_selector_widget.setEnabled(False)
            self.sprite_selector_widget.set_find_button_enabled(False)
            self.manual_offset_button.setEnabled(False)

        elif new_state == ExtractionState.SCANNING_SPRITES:
            # Disable sprite selection during scan
            self.sprite_selector_widget.set_find_button_enabled(False)

        elif new_state == ExtractionState.SEARCHING_SPRITE:
            # Disable navigation during search
            self.manual_offset_button.setEnabled(False)

        # Log state transitions for debugging
        logger.debug(f"State transition: {old_state.name} -> {new_state.name}")

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

        # Stop scan worker
        if self.scan_worker:
            self.scan_worker.quit()
            self.scan_worker.wait()
            self.scan_worker = None

    def closeEvent(self, a0: QCloseEvent | None) -> None:
        """Handle panel close event"""
        # Clean up workers before closing
        self._cleanup_workers()
        if a0:
            super().closeEvent(a0)

