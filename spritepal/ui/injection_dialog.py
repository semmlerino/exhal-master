"""
Injection dialog for SpritePal
Allows users to configure sprite injection parameters
"""

import os
from typing import Any

from core.managers import get_injection_manager
from core.sprite_validator import SpriteValidator
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)
from ui.components import (
    FileSelector,
    FormRow,
    HexOffsetInput,
    StyledSplitter,
    TabbedDialog,
)
from ui.widgets.sprite_preview_widget import SpritePreviewWidget
from utils.logging_config import get_logger

logger = get_logger(__name__)


class InjectionDialog(TabbedDialog):
    """Dialog for configuring sprite injection parameters"""

    def __init__(
        self,
        parent=None,
        sprite_path: str = "",
        metadata_path: str = "",
        input_vram: str = "",
    ):
        # Step 1: Declare instance variables BEFORE super().__init__()
        self.sprite_path = sprite_path
        self.metadata_path = metadata_path
        self.suggested_input_vram = input_vram
        self.metadata = None
        self.extraction_vram_offset = None
        self.rom_extraction_info = None

        # Initialize UI components that will be created in setup methods
        self.extraction_group: QGroupBox | None = None
        self.extraction_info: QTextEdit | None = None
        self.tab_widget: QTabWidget | None = None
        self.preview_widget: SpritePreviewWidget | None = None
        self.rom_info_group: QGroupBox | None = None
        self.rom_info_text: QTextEdit | None = None

        # File selectors
        self.sprite_file_selector: FileSelector | None = None
        self.input_vram_selector: FileSelector | None = None
        self.output_vram_selector: FileSelector | None = None
        self.input_rom_selector: FileSelector | None = None
        self.output_rom_selector: FileSelector | None = None

        # Input widgets
        self.vram_offset_input: HexOffsetInput | None = None
        self.rom_offset_input: HexOffsetInput | None = None
        self.sprite_location_combo: QComboBox | None = None
        self.fast_compression_check: QCheckBox | None = None

        # Get injection manager instance
        self.injection_manager = get_injection_manager()

        # Step 2: Call parent init (this will call _setup_ui)
        super().__init__(
            parent=parent,
            title="Inject Sprite",
            modal=True,
            size=(900, 600),
            min_size=(900, 600),
            with_status_bar=False,
            default_tab=1,  # ROM injection tab as default
        )
        self._load_metadata()
        self._set_initial_paths()

    def _setup_ui(self) -> None:
        """Initialize the user interface"""
        # Create shared preview widget
        self.preview_widget = SpritePreviewWidget("Sprite to Inject")

        # Create VRAM injection tab
        vram_tab_widget = self._create_vram_tab()
        self.add_tab(vram_tab_widget, "VRAM Injection")

        # Create ROM injection tab
        rom_tab_widget = self._create_rom_tab()
        self.add_tab(rom_tab_widget, "ROM Injection")

        # Load sprite preview and validate if available
        if self.sprite_path and os.path.exists(self.sprite_path):
            self._load_sprite_preview()
            self._validate_sprite()

    def _create_vram_tab(self) -> QWidget:
        """Create VRAM injection tab with splitter layout"""
        # Create splitter for this tab
        splitter = StyledSplitter(Qt.Orientation.Horizontal)

        # Create left panel for controls
        left_widget = QWidget(self)
        layout = QVBoxLayout(left_widget)

        # Add sprite file selector
        self._add_sprite_file_selector(layout)

        # Add VRAM-specific controls
        self._add_vram_controls(layout)

        # Add left panel to splitter
        splitter.add_widget(left_widget, stretch_factor=1)

        # Add shared preview widget to splitter
        splitter.add_widget(self.preview_widget, stretch_factor=1)

        return splitter

    def _create_rom_tab(self) -> QWidget:
        """Create ROM injection tab with splitter layout"""
        # Create splitter for this tab
        splitter = StyledSplitter(Qt.Orientation.Horizontal)

        # Create left panel for controls
        left_widget = QWidget(self)
        layout = QVBoxLayout(left_widget)

        # Add sprite file selector
        self._add_sprite_file_selector(layout)

        # Add ROM-specific controls
        self._add_rom_controls(layout)

        # Add left panel to splitter
        splitter.add_widget(left_widget, stretch_factor=1)

        # Add shared preview widget to splitter
        splitter.add_widget(self.preview_widget, stretch_factor=1)

        return splitter

    def _add_sprite_file_selector(self, layout: QVBoxLayout) -> None:
        """Add sprite file selector to a tab layout"""
        sprite_group = QGroupBox("Sprite File", self)
        sprite_layout = QVBoxLayout()

        self.sprite_file_selector = FileSelector(
            label_text="Path:",
            placeholder="Select sprite file...",
            browse_text="Browse...",
            mode="open",
            file_filter="PNG Files (*.png);;All Files (*.*)",
            read_only=False
        )
        self.sprite_file_selector.set_path(self.sprite_path)
        self.sprite_file_selector.path_changed.connect(self._on_sprite_path_changed)

        sprite_layout.addWidget(self.sprite_file_selector)
        sprite_group.setLayout(sprite_layout)
        layout.addWidget(sprite_group)

    def _add_vram_controls(self, layout: QVBoxLayout) -> None:
        """Add VRAM-specific controls to layout"""
        # Extraction info (if metadata available)
        self.extraction_group = QGroupBox("Original Extraction Info", self)
        extraction_layout = QVBoxLayout()

        self.extraction_info = QTextEdit()
        self.extraction_info.setMaximumHeight(80)
        self.extraction_info.setReadOnly(True)
        extraction_layout.addWidget(self.extraction_info)

        self.extraction_group.setLayout(extraction_layout)
        layout.addWidget(self.extraction_group)

        # VRAM settings
        vram_group = QGroupBox("VRAM Settings", self)
        vram_layout = QVBoxLayout()

        # Input VRAM
        self.input_vram_selector = FileSelector(
            label_text="Input VRAM:",
            placeholder="Select VRAM file to modify...",
            browse_text="Browse...",
            mode="open",
            file_filter="VRAM Files (*.dmp *.bin);;All Files (*.*)"
        )
        self.input_vram_selector.path_changed.connect(self._on_input_vram_changed)

        vram_layout.addWidget(self.input_vram_selector)

        # Output VRAM
        self.output_vram_selector = FileSelector(
            label_text="Output VRAM:",
            placeholder="Save modified VRAM as...",
            browse_text="Browse...",
            mode="save",
            file_filter="VRAM Files (*.dmp);;All Files (*.*)"
        )
        self.output_vram_selector.path_changed.connect(self._on_output_vram_changed)

        vram_layout.addWidget(self.output_vram_selector)

        # Offset
        offset_row = FormRow(
            label_text="Injection Offset:",
            input_widget=None,  # Will be set below
            orientation="horizontal"
        )

        self.vram_offset_input = HexOffsetInput(
            placeholder="0xC000",
            with_decimal_display=True,
            input_width=100,
            decimal_width=60
        )
        self.vram_offset_input.text_changed.connect(self._on_vram_offset_changed)
        offset_row.set_input_widget(self.vram_offset_input)

        vram_layout.addWidget(offset_row)

        vram_group.setLayout(vram_layout)
        layout.addWidget(vram_group)

        # Set initial focus
        self.input_vram_selector.setFocus()

    def _add_rom_controls(self, layout: QVBoxLayout) -> None:
        """Add ROM-specific controls to layout"""
        # ROM settings
        rom_group = QGroupBox("ROM Settings", self)
        rom_layout = QVBoxLayout()

        # Input ROM
        self.input_rom_selector = FileSelector(
            label_text="Input ROM:",
            placeholder="Select ROM file to modify...",
            browse_text="Browse...",
            mode="open",
            file_filter="SNES ROM Files (*.sfc *.smc);;All Files (*.*)"
        )
        self.input_rom_selector.path_changed.connect(self._on_input_rom_changed)

        rom_layout.addWidget(self.input_rom_selector)

        # Output ROM
        self.output_rom_selector = FileSelector(
            label_text="Output ROM:",
            placeholder="Save modified ROM as...",
            browse_text="Browse...",
            mode="save",
            file_filter="SNES ROM Files (*.sfc *.smc);;All Files (*.*)"
        )
        self.output_rom_selector.path_changed.connect(self._on_output_rom_changed)

        rom_layout.addWidget(self.output_rom_selector)

        # Sprite location selector
        location_layout = QHBoxLayout()
        location_layout.addWidget(QLabel("Sprite Location:", self))

        self.sprite_location_combo = QComboBox(self)
        self.sprite_location_combo.setMinimumWidth(200)
        # These will be populated dynamically when ROM is loaded
        self.sprite_location_combo.addItem("Select sprite location...", None)
        self.sprite_location_combo.currentIndexChanged.connect(
            self._on_sprite_location_changed
        )
        location_layout.addWidget(self.sprite_location_combo)

        location_layout.addWidget(QLabel("or Custom Offset:", self))

        self.rom_offset_input = HexOffsetInput(
            placeholder="0x0",
            with_decimal_display=False,
            input_width=100
        )
        self.rom_offset_input.text_changed.connect(self._on_rom_offset_changed)
        location_layout.addWidget(self.rom_offset_input)

        location_layout.addStretch()
        rom_layout.addLayout(location_layout)

        # Compression options
        compression_layout = QHBoxLayout()
        self.fast_compression_check = QCheckBox("Fast compression (larger file size)", self)
        compression_layout.addWidget(self.fast_compression_check)
        compression_layout.addStretch()
        rom_layout.addLayout(compression_layout)

        rom_group.setLayout(rom_layout)
        layout.addWidget(rom_group)

        # ROM info display
        self.rom_info_group = QGroupBox("ROM Information", self)
        rom_info_layout = QVBoxLayout()

        self.rom_info_text = QTextEdit()
        self.rom_info_text.setMaximumHeight(100)
        self.rom_info_text.setReadOnly(True)
        rom_info_layout.addWidget(self.rom_info_text)

        self.rom_info_group.setLayout(rom_info_layout)
        self.rom_info_group.hide()  # Hidden until ROM is loaded
        layout.addWidget(self.rom_info_group)

        layout.addStretch()

    def _load_metadata(self) -> None:
        """Load metadata if available"""
        metadata_info = self.injection_manager.load_metadata(self.metadata_path)

        if metadata_info:
            self.metadata = metadata_info.get("metadata")
            self.extraction_vram_offset = metadata_info.get("extraction_vram_offset")
            self.rom_extraction_info = metadata_info.get("rom_extraction_info")

            # Display extraction info
            if metadata_info.get("extraction"):
                extraction = metadata_info["extraction"]
                source_type = metadata_info["source_type"]

                if source_type == "rom" and self.rom_extraction_info:
                    # ROM extraction metadata
                    info_text = (
                        f"Original ROM: {self.rom_extraction_info.get('rom_source', 'Unknown')}\n"
                    )
                    info_text += (
                        f"Sprite: {self.rom_extraction_info.get('sprite_name', 'Unknown')}\n"
                    )
                    info_text += (
                        f"ROM Offset: {self.rom_extraction_info.get('rom_offset', 'Unknown')}\n"
                    )
                    info_text += f"Tiles: {self.rom_extraction_info.get('tile_count', 'Unknown')}"
                    self.extraction_info.setText(info_text)

                    # Set default VRAM offset
                    self.vram_offset_input.set_text(metadata_info.get("default_vram_offset", "0xC000"))
                else:
                    # VRAM extraction metadata
                    info_text = f"Original VRAM: {extraction.get('vram_source', 'Unknown')}\n"
                    info_text += (
                        f"Offset: {extraction.get('vram_offset', '0xC000')}\n"
                    )
                    info_text += f"Tiles: {extraction.get('tile_count', 'Unknown')}"
                    self.extraction_info.setText(info_text)

                    # Set VRAM offset from extraction
                    if self.extraction_vram_offset:
                        self.vram_offset_input.set_text(self.extraction_vram_offset)
            else:
                self.extraction_group.hide()
        else:
            self.extraction_group.hide()
            # Set default offset
            self.vram_offset_input.set_text("0xC000")
            self.extraction_vram_offset = None
            self.rom_extraction_info = None
            self.metadata = None


    def _on_vram_offset_changed(self, text: str) -> None:
        """Handle VRAM offset changes (callback for HexOffsetInput)"""
        logger.debug(f"VRAM offset changed to: '{text}' via HexOffsetInput")
        # HexOffsetInput handles all validation and decimal display internally
        # This method is just for logging and any additional processing if needed

    def _on_rom_offset_changed(self, text: str) -> None:
        """Handle ROM offset changes (callback for HexOffsetInput)"""
        logger.debug(f"ROM offset changed to: '{text}' via HexOffsetInput")
        # Clear combo box selection when manual offset is entered
        if text and self.sprite_location_combo.currentIndex() > 0:
            logger.debug("Manual ROM offset entered, clearing sprite location selection")
            self.sprite_location_combo.blockSignals(True)
            try:
                self.sprite_location_combo.setCurrentIndex(0)
            finally:
                self.sprite_location_combo.blockSignals(False)

    def _on_sprite_path_changed(self, path: str) -> None:
        """Handle sprite file path changes"""
        logger.debug(f"Sprite path changed to: '{path}'")
        self.sprite_path = path
        if path and os.path.exists(path):
            self._load_sprite_preview()
            self._validate_sprite()

    def _on_input_vram_changed(self, path: str) -> None:
        """Handle input VRAM path changes"""
        logger.debug(f"Input VRAM path changed to: '{path}'")
        if path and not self.output_vram_selector.get_path():
            # Auto-suggest output filename
            self.output_vram_selector.set_path(self.injection_manager.suggest_output_vram_path(path))

    def _on_output_vram_changed(self, path: str) -> None:
        """Handle output VRAM path changes"""
        logger.debug(f"Output VRAM path changed to: '{path}'")

    def _on_input_rom_changed(self, path: str) -> None:
        """Handle input ROM path changes"""
        logger.debug(f"Input ROM path changed to: '{path}'")
        if path:
            # Load ROM info and populate sprite locations
            self._load_rom_info(path)
            # Auto-suggest output filename
            if not self.output_rom_selector.get_path():
                self.output_rom_selector.set_path(self.injection_manager.suggest_output_rom_path(path))

    def _on_output_rom_changed(self, path: str) -> None:
        """Handle output ROM path changes"""
        logger.debug(f"Output ROM path changed to: '{path}'")

    def _load_rom_info(self, rom_path: str) -> None:
        """Load ROM information and populate sprite locations"""
        # Clear UI state first in case of errors
        self._clear_rom_ui_state()

        rom_info = self.injection_manager.load_rom_info(rom_path)

        if not rom_info:
            return

        # Check for errors
        if "error" in rom_info:
            error_msg = rom_info["error"]
            error_type = rom_info.get("error_type", "Exception")

            if error_type == "FileNotFoundError":
                logger.exception("ROM file not found")
                _ = QMessageBox.critical(
                    self, "ROM File Not Found", f"The selected ROM file could not be found:\n\n{error_msg}"
                )
            elif error_type == "PermissionError":
                logger.exception("ROM file permission error")
                _ = QMessageBox.critical(
                    self, "ROM File Access Error", f"Cannot access the ROM file:\n\n{error_msg}"
                )
            elif error_type == "ValueError":
                logger.exception("Invalid ROM file")
                _ = QMessageBox.warning(
                    self, "Invalid ROM File", f"The selected file is not a valid SNES ROM:\n\n{error_msg}"
                )
            else:
                logger.exception("Failed to load ROM info")
                _ = QMessageBox.warning(
                    self, "ROM Load Error", f"Failed to load ROM information:\n\n{error_msg}"
                )
            return

        # Display ROM info
        header = rom_info["header"]
        info_text = f"Title: {header['title']}\n"
        info_text += f"ROM Type: 0x{header['rom_type']:02X}\n"
        info_text += f"Checksum: 0x{header['checksum']:04X}"
        self.rom_info_text.setText(info_text)
        self.rom_info_group.show()

        # Populate sprite locations
        sprite_locations = rom_info.get("sprite_locations", {})
        if sprite_locations:
            self.sprite_location_combo.addItem("Select sprite location...", None)

            for display_name, offset in sprite_locations.items():
                self.sprite_location_combo.addItem(
                    f"{display_name} (0x{offset:06X})", offset
                )

            # Check for sprite location loading error
            if "sprite_locations_error" in rom_info:
                logger.warning(f"Failed to load some sprite locations: {rom_info['sprite_locations_error']}")

            # Now restore the saved sprite location if we were loading defaults
            try:
                self._restore_saved_sprite_location()
            except Exception as restore_error:
                logger.warning(f"Failed to restore sprite location: {restore_error}")
        # Not a Kirby ROM or no sprite locations
        elif "KIRBY" not in header["title"].upper():
            self.sprite_location_combo.addItem(f"No sprite data available for: {header['title']}", None)
        else:
            self.sprite_location_combo.addItem("Error loading sprite locations", None)

    def _clear_rom_ui_state(self) -> None:
        """Clear ROM-related UI state"""
        self.sprite_location_combo.clear()
        self.sprite_location_combo.addItem("Load ROM file first...", None)
        self.rom_info_text.clear()
        self.rom_info_group.hide()

    def _on_sprite_location_changed(self, index: int) -> None:
        """Update offset field when sprite location is selected"""
        if index > 0:  # Skip "Select sprite location..."
            offset = self.sprite_location_combo.currentData()
            if offset is not None:
                # Block signals to prevent recursion with _on_rom_offset_changed
                self.rom_offset_input.hex_edit.blockSignals(True)
                try:
                    self.rom_offset_input.set_text(f"0x{offset:X}")
                finally:
                    self.rom_offset_input.hex_edit.blockSignals(False)

    def get_parameters(self) -> dict[str, Any] | None:
        """Get injection parameters if dialog accepted"""
        if self.result() != QDialog.DialogCode.Accepted:
            return None

        # Validate sprite input (common)
        if not self.sprite_file_selector.get_path():
            _ = QMessageBox.warning(self, "Invalid Input", "Please select a sprite file")
            return None

        # Check which tab is active
        current_tab = self.get_current_tab_index()

        if current_tab == 0:  # VRAM injection
            if not self.input_vram_selector.get_path():
                _ = QMessageBox.warning(
                    self, "Invalid Input", "Please select an input VRAM file"
                )
                return None

            if not self.output_vram_selector.get_path():
                _ = QMessageBox.warning(
                    self, "Invalid Input", "Please specify an output VRAM file"
                )
                return None

            # Parse offset
            offset_text = self.vram_offset_input.get_text() or "0xC000"
            offset = self.vram_offset_input.get_value()
            if offset is None:
                _ = QMessageBox.warning(
                    self,
                    "Invalid Input",
                    f"Invalid VRAM offset value: '{offset_text}'\n"
                    "Please enter a valid hexadecimal value (e.g., 0xC000, C000)"
                )
                return None

            return {
                "mode": "vram",
                "sprite_path": self.sprite_file_selector.get_path(),
                "input_vram": self.input_vram_selector.get_path(),
                "output_vram": self.output_vram_selector.get_path(),
                "offset": offset,
                "metadata_path": self.metadata_path if self.metadata else None,
            }

        # ROM injection
        if not self.input_rom_selector.get_path():
            _ = QMessageBox.warning(
                self, "Invalid Input", "Please select an input ROM file"
            )
            return None

        if not self.output_rom_selector.get_path():
            _ = QMessageBox.warning(
                self, "Invalid Input", "Please specify an output ROM file"
            )
            return None

        # Get offset from combo box or manual entry
        offset = None
        if self.sprite_location_combo.currentIndex() > 0:
            offset = self.sprite_location_combo.currentData()
        elif self.rom_offset_input.get_text():
            offset_text = self.rom_offset_input.get_text()
            offset = self.rom_offset_input.get_value()
            if offset is None:
                _ = QMessageBox.warning(
                    self,
                    "Invalid Input",
                    f"Invalid ROM offset value: '{offset_text}'\n"
                    "Please enter a valid hexadecimal value (e.g., 0x8000, 8000)"
                )
                return None

        if offset is None:
            _ = QMessageBox.warning(
                self,
                "Invalid Input",
                "Please select a sprite location or enter a custom offset",
            )
            return None

        return {
            "mode": "rom",
            "sprite_path": self.sprite_file_selector.get_path(),
            "input_rom": self.input_rom_selector.get_path(),
            "output_rom": self.output_rom_selector.get_path(),
            "offset": offset,
            "fast_compression": self.fast_compression_check.isChecked(),
            "metadata_path": self.metadata_path if self.metadata else None,
        }

    def _set_initial_paths(self) -> None:
        """Set initial paths based on suggestions"""
        # Set input VRAM if we have a suggestion
        if self.suggested_input_vram:
            self.input_vram_selector.set_path(self.suggested_input_vram)
        else:
            # Try to find and auto-fill input VRAM
            suggested_input = self.injection_manager.find_suggested_input_vram(
                self.sprite_path,
                self.metadata if hasattr(self, "metadata") else None,
                self.suggested_input_vram
            )
            if suggested_input:
                self.input_vram_selector.set_path(suggested_input)

        # Set ROM injection parameters from saved settings or metadata
        self._set_rom_injection_defaults()

        # Set output VRAM suggestion
        if self.input_vram_selector.get_path():
            self.output_vram_selector.set_path(
                self.injection_manager.suggest_output_vram_path(self.input_vram_selector.get_path())
            )

    def _set_rom_injection_defaults(self) -> None:
        """Set ROM injection parameters from saved settings or metadata"""
        metadata_dict = None
        if hasattr(self, "metadata"):
            metadata_dict = {
                "metadata": self.metadata,
                "rom_extraction_info": self.rom_extraction_info,
                "extraction_vram_offset": self.extraction_vram_offset
            }

        defaults = self.injection_manager.load_rom_injection_defaults(self.sprite_path, metadata_dict)

        # Set input ROM
        if defaults["input_rom"]:
            self.input_rom_selector.set_path(defaults["input_rom"])
            if defaults["output_rom"]:
                self.output_rom_selector.set_path(defaults["output_rom"])
            # Load ROM info to populate sprite locations
            self._load_rom_info(defaults["input_rom"])

            # After ROM is loaded, set the offset if we have one
            if defaults["rom_offset"] is not None:
                # Find matching sprite location in combo box
                sprite_found = False
                for i in range(self.sprite_location_combo.count()):
                    offset_data = self.sprite_location_combo.itemData(i)
                    if offset_data == defaults["rom_offset"]:
                        self.sprite_location_combo.setCurrentIndex(i)
                        sprite_found = True
                        break

                # If no exact match in combo, set custom offset
                if not sprite_found and defaults["custom_offset"]:
                    self.rom_offset_input.set_text(defaults["custom_offset"])
        else:
            # No ROM to load, but still restore other settings
            self._restore_saved_sprite_location()

        # Set custom offset if we don't have a ROM offset match
        if defaults["custom_offset"] and defaults["rom_offset"] is None:
            self.rom_offset_input.set_text(defaults["custom_offset"])

        # Set fast compression
        self.fast_compression_check.setChecked(defaults["fast_compression"])

    def _restore_saved_sprite_location(self) -> None:
        """Restore saved sprite location in combo box"""
        # Build sprite locations dict from combo box
        sprite_locations = {}
        for i in range(1, self.sprite_location_combo.count()):  # Skip index 0 ("Select sprite location...")
            text = self.sprite_location_combo.itemText(i)
            offset = self.sprite_location_combo.itemData(i)
            if offset is not None:
                # Extract display name (before the offset in parentheses)
                display_name = text.split(" (0x")[0] if " (0x" in text else text
                sprite_locations[display_name] = offset

        restore_info = self.injection_manager.restore_saved_sprite_location(
            self.extraction_vram_offset,
            sprite_locations
        )

        if restore_info["sprite_location_index"] is not None:
            self.sprite_location_combo.setCurrentIndex(restore_info["sprite_location_index"])
        elif restore_info["custom_offset"]:
            self.rom_offset_input.set_text(restore_info["custom_offset"])


    def save_rom_injection_parameters(self) -> None:
        """Save ROM injection parameters to settings for future use"""
        self.injection_manager.save_rom_injection_settings(
            input_rom=self.input_rom_selector.get_path(),
            sprite_location_text=self.sprite_location_combo.currentText(),
            custom_offset=self.rom_offset_input.get_text(),
            fast_compression=self.fast_compression_check.isChecked()
        )

    def _load_sprite_preview(self) -> None:
        """Load and display sprite preview"""
        if not self.sprite_path or not os.path.exists(self.sprite_path):
            self.preview_widget.clear()
            return

        try:
            # Try to detect sprite name from metadata or filename
            sprite_name = None
            if self.metadata and "extraction" in self.metadata:
                sprite_name = self.metadata["extraction"].get("sprite_name", "")

            if not sprite_name:
                # Extract from filename (e.g., "kirby_normal_sprites.png" -> "kirby_normal")
                base_name = os.path.splitext(os.path.basename(self.sprite_path))[0]
                for suffix in ["_sprites_editor", "_sprites", "_editor"]:
                    if base_name.endswith(suffix):
                        sprite_name = base_name[: -len(suffix)]
                        break
                else:
                    sprite_name = base_name

            # Load the sprite preview
            self.preview_widget.load_sprite_from_png(self.sprite_path, sprite_name)

        except Exception as e:
            logger.exception("Failed to load sprite preview")
            self.preview_widget.clear()
            self.preview_widget.info_label.setText(f"Error loading preview: {e}")

    def _validate_sprite(self) -> None:
        """Validate sprite and show warnings/errors"""
        if not self.sprite_path or not os.path.exists(self.sprite_path):
            return

        # Perform validation
        is_valid, errors, warnings = SpriteValidator.validate_sprite_comprehensive(
            self.sprite_path, self.metadata_path
        )

        # Create validation message
        if errors or warnings:
            msg_parts = []

            if errors:
                msg_parts.append("ERRORS:")
                for error in errors:
                    msg_parts.append(f"  • {error}")

            if warnings:
                if errors:
                    msg_parts.append("")  # Empty line
                msg_parts.append("WARNINGS:")
                for warning in warnings:
                    msg_parts.append(f"  • {warning}")

            # Show validation results in a message box
            if errors:
                _ = QMessageBox.critical(
                    self, "Sprite Validation Failed", "\n".join(msg_parts)
                )
            else:
                # Just warnings - show as information
                _ = QMessageBox.information(
                    self, "Sprite Validation Warnings", "\n".join(msg_parts)
                )

        # Also estimate compressed size
        uncompressed, estimated_compressed = SpriteValidator.estimate_compressed_size(
            self.sprite_path
        )
        if uncompressed > 0:
            size_info = f"Estimated size: {uncompressed} bytes uncompressed, ~{estimated_compressed} bytes compressed"

            # Update preview widget info
            current_info = self.preview_widget.info_label.text()
            if "Size:" in current_info:
                # Append to existing info
                self.preview_widget.info_label.setText(f"{current_info} | {size_info}")
            else:
                self.preview_widget.info_label.setText(size_info)
