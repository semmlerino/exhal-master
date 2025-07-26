"""
Injection dialog for SpritePal
Allows users to configure sprite injection parameters
"""

import builtins
import contextlib
import json
import os
import time

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from spritepal.core.rom_injector import ROMInjector
from spritepal.core.sprite_validator import SpriteValidator
from spritepal.ui.widgets.sprite_preview_widget import SpritePreviewWidget
from spritepal.utils.constants import (
    SETTINGS_KEY_FAST_COMPRESSION,
    SETTINGS_KEY_LAST_CUSTOM_OFFSET,
    SETTINGS_KEY_LAST_INPUT_ROM,
    SETTINGS_KEY_LAST_INPUT_VRAM,
    SETTINGS_KEY_LAST_OUTPUT_VRAM,
    SETTINGS_KEY_LAST_SPRITE_LOCATION,
    SETTINGS_KEY_VRAM_PATH,
    SETTINGS_NS_ROM_INJECTION,
)
from spritepal.utils.logging_config import get_logger
from spritepal.utils.settings_manager import get_settings_manager

logger = get_logger(__name__)


class InjectionDialog(QDialog):
    """Dialog for configuring sprite injection parameters"""

    def __init__(
        self,
        parent=None,
        sprite_path: str = "",
        metadata_path: str = "",
        input_vram: str = "",
    ):
        super().__init__(parent)
        self.sprite_path = sprite_path
        self.metadata_path = metadata_path
        self.suggested_input_vram = input_vram
        self.metadata = None
        self.extraction_vram_offset = None

        # Initialize UI components that will be created in setup methods
        self.extraction_group: QGroupBox | None = None
        self.extraction_info: QTextEdit | None = None
        self.input_vram_edit: QLineEdit | None = None
        self.preview_widget: SpritePreviewWidget | None = None

        self._setup_ui()
        self._load_metadata()
        self._set_initial_paths()

    def _setup_ui(self):
        """Initialize the user interface"""
        self.setWindowTitle("Inject Sprite")
        self.setModal(True)
        self.setMinimumWidth(900)
        self.setMinimumHeight(600)

        main_layout = QVBoxLayout(self)

        # Create splitter for controls and preview
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left panel for controls
        left_widget = QWidget()
        layout = QVBoxLayout(left_widget)

        # Sprite file info (common to both tabs)
        sprite_group = QGroupBox("Sprite File")
        sprite_layout = QVBoxLayout()

        sprite_path_layout = QHBoxLayout()
        sprite_path_layout.addWidget(QLabel("Path:"))
        self.sprite_path_edit = QLineEdit(self.sprite_path)
        self.sprite_path_edit.setReadOnly(True)
        sprite_path_layout.addWidget(self.sprite_path_edit)

        self.browse_sprite_btn = QPushButton("Browse...")
        self.browse_sprite_btn.clicked.connect(self._browse_sprite)
        sprite_path_layout.addWidget(self.browse_sprite_btn)

        sprite_layout.addLayout(sprite_path_layout)
        sprite_group.setLayout(sprite_layout)
        layout.addWidget(sprite_group)

        # Create tab widget
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        # Create VRAM tab
        self.vram_tab = QWidget()
        self._setup_vram_tab()
        self.tabs.addTab(self.vram_tab, "VRAM Injection")

        # Create ROM tab
        self.rom_tab = QWidget()
        self._setup_rom_tab()
        self.tabs.addTab(self.rom_tab, "ROM Injection")

        # Set ROM injection tab as default
        self.tabs.setCurrentIndex(1)

        # Dialog buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        # Add preview widget to right side
        self.preview_widget = SpritePreviewWidget("Sprite to Inject")

        # Add panels to splitter
        splitter.addWidget(left_widget)
        splitter.addWidget(self.preview_widget)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 1)

        # Add splitter to main layout
        main_layout.addWidget(splitter)

        # Load sprite preview and validate if available
        if self.sprite_path and os.path.exists(self.sprite_path):
            self._load_sprite_preview()
            self._validate_sprite()

    def _setup_vram_tab(self):
        """Setup VRAM injection tab"""
        layout = QVBoxLayout(self.vram_tab)

        # Extraction info (if metadata available)
        self.extraction_group = QGroupBox("Original Extraction Info")
        extraction_layout = QVBoxLayout()

        self.extraction_info = QTextEdit()
        self.extraction_info.setMaximumHeight(80)
        self.extraction_info.setReadOnly(True)
        extraction_layout.addWidget(self.extraction_info)

        self.extraction_group.setLayout(extraction_layout)
        layout.addWidget(self.extraction_group)

        # VRAM settings
        vram_group = QGroupBox("VRAM Settings")
        vram_layout = QVBoxLayout()

        # Input VRAM
        input_layout = QHBoxLayout()
        input_layout.addWidget(QLabel("Input VRAM:"))
        self.input_vram_edit = QLineEdit()
        self.input_vram_edit.setPlaceholderText("Select VRAM file to modify...")
        input_layout.addWidget(self.input_vram_edit)

        self.browse_input_btn = QPushButton("Browse...")
        self.browse_input_btn.clicked.connect(self._browse_input_vram)
        input_layout.addWidget(self.browse_input_btn)

        vram_layout.addLayout(input_layout)

        # Output VRAM
        output_layout = QHBoxLayout()
        output_layout.addWidget(QLabel("Output VRAM:"))
        self.output_vram_edit = QLineEdit()
        self.output_vram_edit.setPlaceholderText("Save modified VRAM as...")
        output_layout.addWidget(self.output_vram_edit)

        self.browse_output_btn = QPushButton("Browse...")
        self.browse_output_btn.clicked.connect(self._browse_output_vram)
        output_layout.addWidget(self.browse_output_btn)

        vram_layout.addLayout(output_layout)

        # Offset
        offset_layout = QHBoxLayout()
        offset_layout.addWidget(QLabel("Injection Offset:"))

        self.offset_hex_edit = QLineEdit()
        self.offset_hex_edit.setPlaceholderText("0xC000")
        self.offset_hex_edit.setMaximumWidth(100)
        self.offset_hex_edit.textChanged.connect(self._on_offset_changed)
        offset_layout.addWidget(self.offset_hex_edit)

        offset_layout.addWidget(QLabel("(hex) = "))

        self.offset_dec_label = QLabel("49152")
        self.offset_dec_label.setMinimumWidth(60)
        offset_layout.addWidget(self.offset_dec_label)

        offset_layout.addWidget(QLabel("(decimal)"))
        offset_layout.addStretch()

        vram_layout.addLayout(offset_layout)

        vram_group.setLayout(vram_layout)
        layout.addWidget(vram_group)

        # Set initial focus
        self.input_vram_edit.setFocus()

    def _setup_rom_tab(self):
        """Setup ROM injection tab"""
        layout = QVBoxLayout(self.rom_tab)

        # ROM settings
        rom_group = QGroupBox("ROM Settings")
        rom_layout = QVBoxLayout()

        # Input ROM
        input_layout = QHBoxLayout()
        input_layout.addWidget(QLabel("Input ROM:"))
        self.input_rom_edit = QLineEdit()
        self.input_rom_edit.setPlaceholderText("Select ROM file to modify...")
        input_layout.addWidget(self.input_rom_edit)

        self.browse_input_rom_btn = QPushButton("Browse...")
        self.browse_input_rom_btn.clicked.connect(self._browse_input_rom)
        input_layout.addWidget(self.browse_input_rom_btn)

        rom_layout.addLayout(input_layout)

        # Output ROM
        output_layout = QHBoxLayout()
        output_layout.addWidget(QLabel("Output ROM:"))
        self.output_rom_edit = QLineEdit()
        self.output_rom_edit.setPlaceholderText("Save modified ROM as...")
        output_layout.addWidget(self.output_rom_edit)

        self.browse_output_rom_btn = QPushButton("Browse...")
        self.browse_output_rom_btn.clicked.connect(self._browse_output_rom)
        output_layout.addWidget(self.browse_output_rom_btn)

        rom_layout.addLayout(output_layout)

        # Sprite location selector
        location_layout = QHBoxLayout()
        location_layout.addWidget(QLabel("Sprite Location:"))

        self.sprite_location_combo = QComboBox()
        self.sprite_location_combo.setMinimumWidth(200)
        # These will be populated dynamically when ROM is loaded
        self.sprite_location_combo.addItem("Select sprite location...", None)
        self.sprite_location_combo.currentIndexChanged.connect(
            self._on_sprite_location_changed
        )
        location_layout.addWidget(self.sprite_location_combo)

        location_layout.addWidget(QLabel("or Custom Offset:"))

        self.rom_offset_hex_edit = QLineEdit()
        self.rom_offset_hex_edit.setPlaceholderText("0x0")
        self.rom_offset_hex_edit.setMaximumWidth(100)
        self.rom_offset_hex_edit.textChanged.connect(self._on_rom_offset_changed)
        location_layout.addWidget(self.rom_offset_hex_edit)

        location_layout.addStretch()
        rom_layout.addLayout(location_layout)

        # Compression options
        compression_layout = QHBoxLayout()
        self.fast_compression_check = QCheckBox("Fast compression (larger file size)")
        compression_layout.addWidget(self.fast_compression_check)
        compression_layout.addStretch()
        rom_layout.addLayout(compression_layout)

        rom_group.setLayout(rom_layout)
        layout.addWidget(rom_group)

        # ROM info display
        self.rom_info_group = QGroupBox("ROM Information")
        rom_info_layout = QVBoxLayout()

        self.rom_info_text = QTextEdit()
        self.rom_info_text.setMaximumHeight(100)
        self.rom_info_text.setReadOnly(True)
        rom_info_layout.addWidget(self.rom_info_text)

        self.rom_info_group.setLayout(rom_info_layout)
        self.rom_info_group.hide()  # Hidden until ROM is loaded
        layout.addWidget(self.rom_info_group)

        layout.addStretch()

    def _load_metadata(self):
        """Load metadata if available"""
        if self.metadata_path and os.path.exists(self.metadata_path):
            try:
                with open(self.metadata_path) as f:
                    self.metadata = json.load(f)

                # Display extraction info
                if "extraction" in self.metadata:
                    extraction = self.metadata["extraction"]
                    source_type = extraction.get("source_type", "vram")

                    if source_type == "rom":
                        # ROM extraction metadata
                        info_text = (
                            f"Original ROM: {extraction.get('rom_source', 'Unknown')}\n"
                        )
                        info_text += (
                            f"Sprite: {extraction.get('sprite_name', 'Unknown')}\n"
                        )
                        info_text += (
                            f"ROM Offset: {extraction.get('rom_offset', 'Unknown')}\n"
                        )
                        info_text += f"Tiles: {extraction.get('tile_count', 'Unknown')}"
                        self.extraction_info.setText(info_text)

                        # Store ROM extraction info for auto-population
                        self.rom_extraction_info = {
                            "rom_source": extraction.get("rom_source", ""),
                            "rom_offset": extraction.get("rom_offset", "0x0"),
                            "sprite_name": extraction.get("sprite_name", ""),
                        }

                        # No direct VRAM offset for ROM extractions
                        self.extraction_vram_offset = None
                        # Default VRAM offset for VRAM injection
                        self.offset_hex_edit.setText("0xC000")
                    else:
                        # VRAM extraction metadata
                        info_text = f"Original VRAM: {extraction.get('vram_source', 'Unknown')}\n"
                        info_text += (
                            f"Offset: {extraction.get('vram_offset', '0xC000')}\n"
                        )
                        info_text += f"Tiles: {extraction.get('tile_count', 'Unknown')}"
                        self.extraction_info.setText(info_text)

                        # Set default offset for VRAM injection
                        vram_offset = extraction.get("vram_offset", "0xC000")
                        self.offset_hex_edit.setText(vram_offset)

                        # Store extraction offset for ROM injection
                        self.extraction_vram_offset = vram_offset
                        self.rom_extraction_info = None
                else:
                    self.extraction_group.hide()
                    self.extraction_vram_offset = None
                    self.rom_extraction_info = None
            except Exception:
                self.extraction_group.hide()
                self.extraction_vram_offset = None
                self.rom_extraction_info = None
        else:
            self.extraction_group.hide()
            # Set default offset
            self.offset_hex_edit.setText("0xC000")
            self.extraction_vram_offset = None
            self.rom_extraction_info = None

    def _browse_sprite(self):
        """Browse for sprite file"""
        settings = get_settings_manager()
        default_dir = (
            os.path.dirname(self.sprite_path)
            if self.sprite_path
            else settings.get_default_directory()
        )

        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Select Sprite File",
            default_dir,
            "PNG Files (*.png);;All Files (*.*)",
        )
        if filename:
            self.sprite_path = filename
            self.sprite_path_edit.setText(filename)
            settings.set_last_used_directory(os.path.dirname(filename))
            self._load_sprite_preview()
            self._validate_sprite()

    def _browse_input_vram(self):
        """Browse for input VRAM file with enhanced fallback logic"""
        settings = get_settings_manager()

        # Try multiple fallback paths in order of preference
        suggested_path = self._find_suggested_input_vram()
        suggested_dir = (
            os.path.dirname(suggested_path)
            if suggested_path
            else settings.get_default_directory()
        )

        # If we found a specific file, use it as the initial selection
        initial_path = suggested_path if suggested_path else suggested_dir

        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Select Input VRAM File",
            initial_path,
            "VRAM Files (*.dmp *.bin);;All Files (*.*)",
        )
        if filename:
            self.input_vram_edit.setText(filename)
            settings.set_last_used_directory(os.path.dirname(filename))

            # Save as last used input VRAM for future suggestions (using ROM injection namespace)
            settings.set_value(
                SETTINGS_NS_ROM_INJECTION, SETTINGS_KEY_LAST_INPUT_VRAM, filename
            )

            # Auto-suggest output filename with smart naming
            if not self.output_vram_edit.text():
                self.output_vram_edit.setText(self._suggest_output_vram_path(filename))

    def _browse_output_vram(self):
        """Browse for output VRAM file with enhanced suggestions"""
        settings = get_settings_manager()
        suggested_path = self.output_vram_edit.text()

        # If no suggested path, create one based on input or sprite
        if not suggested_path:
            if self.input_vram_edit.text():
                suggested_path = self._suggest_output_vram_path(
                    self.input_vram_edit.text()
                )
            else:
                # Use sprite directory if available
                sprite_dir = (
                    os.path.dirname(self.sprite_path)
                    if self.sprite_path
                    else settings.get_default_directory()
                )
                sprite_base = (
                    os.path.splitext(os.path.basename(self.sprite_path))[0]
                    if self.sprite_path
                    else "sprite"
                )
                suggested_path = os.path.join(sprite_dir, f"{sprite_base}_injected.dmp")

        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Save Modified VRAM As",
            suggested_path,
            "VRAM Files (*.dmp);;All Files (*.*)",
        )
        if filename:
            self.output_vram_edit.setText(filename)
            settings.set_last_used_directory(os.path.dirname(filename))

            # Save as last used output VRAM for future suggestions (using ROM injection namespace)
            settings.set_value(
                SETTINGS_NS_ROM_INJECTION, SETTINGS_KEY_LAST_OUTPUT_VRAM, filename
            )

    def _parse_hex_offset(self, text: str) -> int | None:
        """Parse hex offset string to integer with robust error handling

        Args:
            text: Hex string like "0x8000", "8000", "0X8000", etc.

        Returns:
            Integer value or None if invalid
        """
        logger.debug(f"Parsing hex offset: '{text}'")

        if not text:
            logger.debug("Empty text, returning None")
            return None

        # Strip whitespace
        text = text.strip()
        if not text:
            logger.debug("Empty text after strip, returning None")
            return None

        try:
            # Handle both 0x prefixed and non-prefixed hex
            if text.lower().startswith(("0x", "0X")):
                logger.debug(f"Parsing as prefixed hex: '{text}'")
                result = int(text, 16)
                logger.debug(f"Successfully parsed prefixed hex: 0x{result:X} ({result})")
                return result
            # Assume hex if no prefix
            logger.debug(f"Parsing as non-prefixed hex: '{text}'")
            result = int(text, 16)
            logger.debug(f"Successfully parsed non-prefixed hex: 0x{result:X} ({result})")
            return result
        except ValueError as e:
            logger.debug(f"Failed to parse hex offset '{text}': {e}")
            return None
        except Exception as e:
            logger.warning(f"Unexpected error parsing hex offset '{text}': {e}")
            return None

    def _on_offset_changed(self, text):
        """Update decimal display when hex offset changes"""
        logger.debug(f"VRAM offset changed to: '{text}'")
        try:
            value = self._parse_hex_offset(text)
            logger.debug(f"Parsed hex offset: {value}")

            if value is not None:
                decimal_str = str(value)
                logger.debug(f"Setting decimal label to: {decimal_str}")
                self.offset_dec_label.setText(decimal_str)
                logger.debug(f"Valid VRAM offset: 0x{value:X} ({value} decimal)")
            else:
                display_text = "Invalid" if text.strip() else ""
                logger.debug(f"Setting decimal label to: '{display_text}'")
                self.offset_dec_label.setText(display_text)
                if text.strip():
                    logger.warning(f"Invalid VRAM offset format: '{text}'")

            logger.debug("VRAM offset change handled successfully")

        except Exception:
            logger.exception("Error in VRAM offset change handler")
            # Try to set error state
            with contextlib.suppress(builtins.BaseException):
                self.offset_dec_label.setText("Error")
            # Don't re-raise to prevent crash

    def _browse_input_rom(self):
        """Browse for input ROM file"""
        settings = get_settings_manager()
        default_dir = settings.get_default_directory()

        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Select ROM File",
            default_dir,
            "SNES ROM Files (*.sfc *.smc);;All Files (*.*)",
        )
        if filename:
            self.input_rom_edit.setText(filename)
            settings.set_last_used_directory(os.path.dirname(filename))

            # Load ROM info and populate sprite locations
            self._load_rom_info(filename)

            # Auto-suggest output filename
            if not self.output_rom_edit.text():
                base = os.path.splitext(filename)[0]
                self.output_rom_edit.setText(f"{base}_modified.sfc")

    def _browse_output_rom(self):
        """Browse for output ROM file"""
        settings = get_settings_manager()
        suggested_path = self.output_rom_edit.text()

        if not suggested_path and self.input_rom_edit.text():
            base = os.path.splitext(self.input_rom_edit.text())[0]
            suggested_path = f"{base}_modified.sfc"

        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Save Modified ROM As",
            suggested_path,
            "SNES ROM Files (*.sfc *.smc);;All Files (*.*)",
        )
        if filename:
            self.output_rom_edit.setText(filename)
            settings.set_last_used_directory(os.path.dirname(filename))

    def _load_rom_info(self, rom_path: str):
        """Load ROM information and populate sprite locations"""
        # Clear UI state first in case of errors
        self._clear_rom_ui_state()

        try:
            # Validate ROM file exists and is readable
            if not os.path.exists(rom_path):
                raise FileNotFoundError(f"ROM file not found: {rom_path}")

            if not os.access(rom_path, os.R_OK):
                raise PermissionError(f"Cannot read ROM file: {rom_path}")

            # Check file size is reasonable for a SNES ROM
            file_size = os.path.getsize(rom_path)
            if file_size < 0x8000:  # Minimum reasonable SNES ROM size (32KB)
                raise ValueError(f"File too small to be a valid SNES ROM: {file_size} bytes")
            if file_size > 0x600000:  # Maximum reasonable size (6MB)
                raise ValueError(f"File too large to be a valid SNES ROM: {file_size} bytes")

            injector = ROMInjector()
            header = injector.read_rom_header(rom_path)

            # Display ROM info
            info_text = f"Title: {header.title}\n"
            info_text += f"ROM Type: 0x{header.rom_type:02X}\n"
            info_text += f"Checksum: 0x{header.checksum:04X}"
            self.rom_info_text.setText(info_text)
            self.rom_info_group.show()

            # Populate sprite locations if this is Kirby Super Star
            if "KIRBY" in header.title.upper():
                self.sprite_location_combo.addItem("Select sprite location...", None)

                # Get known sprite locations
                try:
                    locations = injector.find_sprite_locations(rom_path)
                    for name, pointer in locations.items():
                        display_name = name.replace("_", " ").title()
                        self.sprite_location_combo.addItem(
                            f"{display_name} (0x{pointer.offset:06X})", pointer.offset
                        )
                except Exception as sprite_error:
                    logger.warning(f"Failed to load sprite locations: {sprite_error}")
                    self.sprite_location_combo.addItem("Error loading sprite locations", None)

                # Now restore the saved sprite location if we were loading defaults
                try:
                    self._restore_saved_sprite_location()
                except Exception as restore_error:
                    logger.warning(f"Failed to restore sprite location: {restore_error}")
            else:
                # Not a Kirby ROM
                self.sprite_location_combo.addItem(f"No sprite data available for: {header.title}", None)

        except FileNotFoundError as e:
            logger.exception("ROM file not found")
            QMessageBox.critical(
                self, "ROM File Not Found", f"The selected ROM file could not be found:\n\n{e}"
            )
        except PermissionError as e:
            logger.exception("ROM file permission error")
            QMessageBox.critical(
                self, "ROM File Access Error", f"Cannot access the ROM file:\n\n{e}"
            )
        except ValueError as e:
            logger.exception("Invalid ROM file")
            QMessageBox.warning(
                self, "Invalid ROM File", f"The selected file is not a valid SNES ROM:\n\n{e}"
            )
        except Exception as e:
            logger.exception("Failed to load ROM info")
            QMessageBox.warning(
                self, "ROM Load Error", f"Failed to load ROM information:\n\n{e!s}"
            )

    def _clear_rom_ui_state(self):
        """Clear ROM-related UI state"""
        self.sprite_location_combo.clear()
        self.sprite_location_combo.addItem("Load ROM file first...", None)
        self.rom_info_text.clear()
        self.rom_info_group.hide()

    def _on_sprite_location_changed(self, index: int):
        """Update offset field when sprite location is selected"""
        if index > 0:  # Skip "Select sprite location..."
            offset = self.sprite_location_combo.currentData()
            if offset is not None:
                # Block signals to prevent recursion with _on_rom_offset_changed
                self.rom_offset_hex_edit.blockSignals(True)
                try:
                    self.rom_offset_hex_edit.setText(f"0x{offset:X}")
                finally:
                    self.rom_offset_hex_edit.blockSignals(False)

    def _on_rom_offset_changed(self, text: str):
        """Handle ROM offset changes"""
        logger.debug(f"ROM offset changed to: '{text}'")
        try:
            # Clear combo box selection when manual offset is entered
            current_index = self.sprite_location_combo.currentIndex()
            logger.debug(f"Current sprite location combo index: {current_index}")

            if text and current_index > 0:
                logger.debug("Manual ROM offset entered, clearing sprite location selection")
                # Block signals to prevent recursion with _on_sprite_location_changed
                self.sprite_location_combo.blockSignals(True)
                logger.debug("Blocked sprite location combo signals")

                try:
                    self.sprite_location_combo.setCurrentIndex(0)
                    logger.debug("Reset sprite location combo to index 0")
                except Exception:
                    logger.exception("Failed to reset sprite location combo")
                    raise
                finally:
                    self.sprite_location_combo.blockSignals(False)
                    logger.debug("Unblocked sprite location combo signals")

            # Validate the ROM offset if not empty
            if text.strip():
                parsed_offset = self._parse_hex_offset(text)
                if parsed_offset is not None:
                    logger.debug(f"Valid ROM offset: 0x{parsed_offset:X} ({parsed_offset} decimal)")
                else:
                    logger.warning(f"Invalid ROM offset format: '{text}'")

            logger.debug("ROM offset change handled successfully")

        except Exception:
            logger.exception("Error in ROM offset change handler")
            # Try to reset combo signals state on error
            with contextlib.suppress(builtins.BaseException):
                self.sprite_location_combo.blockSignals(False)
            # Don't re-raise to prevent crash

    def get_parameters(self) -> dict | None:
        """Get injection parameters if dialog accepted"""
        if self.result() != QDialog.DialogCode.Accepted:
            return None

        # Validate sprite input (common)
        if not self.sprite_path_edit.text():
            QMessageBox.warning(self, "Invalid Input", "Please select a sprite file")
            return None

        # Check which tab is active
        current_tab = self.tabs.currentIndex()

        if current_tab == 0:  # VRAM injection
            if not self.input_vram_edit.text():
                QMessageBox.warning(
                    self, "Invalid Input", "Please select an input VRAM file"
                )
                return None

            if not self.output_vram_edit.text():
                QMessageBox.warning(
                    self, "Invalid Input", "Please specify an output VRAM file"
                )
                return None

            # Parse offset
            offset_text = self.offset_hex_edit.text() or "0xC000"
            offset = self._parse_hex_offset(offset_text)
            if offset is None:
                QMessageBox.warning(
                    self,
                    "Invalid Input",
                    f"Invalid VRAM offset value: '{offset_text}'\n"
                    "Please enter a valid hexadecimal value (e.g., 0xC000, C000)"
                )
                return None

            return {
                "mode": "vram",
                "sprite_path": self.sprite_path_edit.text(),
                "input_vram": self.input_vram_edit.text(),
                "output_vram": self.output_vram_edit.text(),
                "offset": offset,
                "metadata_path": self.metadata_path if self.metadata else None,
            }

        # ROM injection
        if not self.input_rom_edit.text():
            QMessageBox.warning(
                self, "Invalid Input", "Please select an input ROM file"
            )
            return None

        if not self.output_rom_edit.text():
            QMessageBox.warning(
                self, "Invalid Input", "Please specify an output ROM file"
            )
            return None

        # Get offset from combo box or manual entry
        offset = None
        if self.sprite_location_combo.currentIndex() > 0:
            offset = self.sprite_location_combo.currentData()
        elif self.rom_offset_hex_edit.text():
            offset_text = self.rom_offset_hex_edit.text()
            offset = self._parse_hex_offset(offset_text)
            if offset is None:
                QMessageBox.warning(
                    self,
                    "Invalid Input",
                    f"Invalid ROM offset value: '{offset_text}'\n"
                    "Please enter a valid hexadecimal value (e.g., 0x8000, 8000)"
                )
                return None

        if offset is None:
            QMessageBox.warning(
                self,
                "Invalid Input",
                "Please select a sprite location or enter a custom offset",
            )
            return None

        return {
            "mode": "rom",
            "sprite_path": self.sprite_path_edit.text(),
            "input_rom": self.input_rom_edit.text(),
            "output_rom": self.output_rom_edit.text(),
            "offset": offset,
            "fast_compression": self.fast_compression_check.isChecked(),
            "metadata_path": self.metadata_path if self.metadata else None,
        }

    def _set_initial_paths(self):
        """Set initial paths based on suggestions"""
        # Set input VRAM if we have a suggestion
        if self.suggested_input_vram:
            self.input_vram_edit.setText(self.suggested_input_vram)
        else:
            # Try to find and auto-fill input VRAM
            suggested_input = self._find_suggested_input_vram()
            if suggested_input:
                self.input_vram_edit.setText(suggested_input)

        # Set ROM injection parameters from saved settings or metadata
        self._set_rom_injection_defaults()

        # Set output VRAM suggestion
        if self.input_vram_edit.text():
            self.output_vram_edit.setText(
                self._suggest_output_vram_path(self.input_vram_edit.text())
            )

    def _set_rom_injection_defaults(self):
        """Set ROM injection parameters from saved settings or metadata"""
        settings = get_settings_manager()

        # Check if we have ROM extraction metadata
        if hasattr(self, "rom_extraction_info") and self.rom_extraction_info:
            # Auto-populate from ROM extraction metadata
            rom_source = self.rom_extraction_info.get("rom_source", "")
            rom_offset_str = self.rom_extraction_info.get("rom_offset", "0x0")

            # Look for the ROM file in the sprite's directory
            if rom_source and self.sprite_path:
                sprite_dir = os.path.dirname(self.sprite_path)
                possible_rom_path = os.path.join(sprite_dir, rom_source)
                if os.path.exists(possible_rom_path):
                    self.input_rom_edit.setText(possible_rom_path)
                    self.output_rom_edit.setText(
                        self._suggest_output_rom_path(possible_rom_path)
                    )
                    # Load ROM info to populate sprite locations
                    self._load_rom_info(possible_rom_path)

                    # After ROM is loaded, set the offset
                    # Parse the ROM offset string
                    try:
                        if rom_offset_str.startswith(("0x", "0X")):
                            rom_offset = int(rom_offset_str, 16)
                        else:
                            rom_offset = int(rom_offset_str, 16)

                        # Find matching sprite location in combo box
                        sprite_found = False
                        for i in range(self.sprite_location_combo.count()):
                            offset_data = self.sprite_location_combo.itemData(i)
                            if offset_data == rom_offset:
                                self.sprite_location_combo.setCurrentIndex(i)
                                sprite_found = True
                                break

                        # If no exact match in combo, set custom offset
                        if not sprite_found:
                            self.rom_offset_hex_edit.setText(rom_offset_str)
                    except (ValueError, TypeError):
                        pass

                    return  # Skip loading from saved settings

        # Fall back to saved settings
        last_input_rom = settings.get_value(
            SETTINGS_NS_ROM_INJECTION, SETTINGS_KEY_LAST_INPUT_ROM, ""
        )
        if last_input_rom and os.path.exists(last_input_rom):
            self.input_rom_edit.setText(last_input_rom)
            # Auto-suggest output ROM path
            self.output_rom_edit.setText(self._suggest_output_rom_path(last_input_rom))
            # Load ROM and populate sprite locations (sprite location will be restored after loading)
            self._load_rom_info(last_input_rom)
        else:
            # No ROM to load, but still restore other settings
            self._restore_saved_sprite_location()

        # Load last used custom offset
        last_custom_offset = settings.get_value(
            SETTINGS_NS_ROM_INJECTION, SETTINGS_KEY_LAST_CUSTOM_OFFSET, ""
        )
        if last_custom_offset:
            self.rom_offset_hex_edit.setText(last_custom_offset)

        # Load fast compression setting
        fast_compression = settings.get_value(
            SETTINGS_NS_ROM_INJECTION, SETTINGS_KEY_FAST_COMPRESSION, False
        )
        self.fast_compression_check.setChecked(fast_compression)

    def _restore_saved_sprite_location(self):
        """Restore saved sprite location in combo box"""
        settings = get_settings_manager()

        # First, try to use extraction offset if available
        if hasattr(self, "extraction_vram_offset") and self.extraction_vram_offset:
            # Convert VRAM offset to ROM offset and select matching sprite location
            rom_offset = self._get_rom_offset_from_vram(self.extraction_vram_offset)
            if rom_offset is not None:
                # Find sprite location that matches this offset
                for i in range(self.sprite_location_combo.count()):
                    offset_data = self.sprite_location_combo.itemData(i)
                    if offset_data == rom_offset:
                        self.sprite_location_combo.setCurrentIndex(i)
                        return
                # If no exact match, set custom offset
                self.rom_offset_hex_edit.setText(f"0x{rom_offset:X}")
                return

        # Fall back to saved sprite location
        last_sprite_location = settings.get_value(
            SETTINGS_NS_ROM_INJECTION, SETTINGS_KEY_LAST_SPRITE_LOCATION, ""
        )
        if last_sprite_location:
            # Find and select the matching sprite location in combo box
            for i in range(self.sprite_location_combo.count()):
                if self.sprite_location_combo.itemText(i) == last_sprite_location:
                    self.sprite_location_combo.setCurrentIndex(i)
                    break

    def _find_suggested_input_vram(self) -> str:
        """Find the best suggestion for input VRAM path"""
        # If we already have a suggestion, use it
        if self.suggested_input_vram and os.path.exists(self.suggested_input_vram):
            return self.suggested_input_vram

        # Try metadata first (existing logic)
        if self.metadata and "extraction" in self.metadata:
            vram_source = self.metadata["extraction"].get("vram_source", "")
            if vram_source:
                # Look for the file in the sprite's directory
                sprite_dir = os.path.dirname(self.sprite_path)
                possible_path = os.path.join(sprite_dir, vram_source)
                if os.path.exists(possible_path):
                    return possible_path

        # Try to find VRAM file with same base name as sprite
        if self.sprite_path:
            sprite_dir = os.path.dirname(self.sprite_path)
            sprite_base = os.path.splitext(os.path.basename(self.sprite_path))[0]

            # Remove common sprite suffixes to find original base
            for suffix in ["_sprites_editor", "_sprites", "_editor", "Edited"]:
                if sprite_base.endswith(suffix):
                    sprite_base = sprite_base[: -len(suffix)]
                    break

            # Try common VRAM file patterns
            vram_patterns = [
                f"{sprite_base}.dmp",
                f"{sprite_base}.SnesVideoRam.dmp",
                f"{sprite_base}_VRAM.dmp",
                f"{sprite_base}.VideoRam.dmp",
                f"{sprite_base}.VRAM.dmp",
            ]

            for pattern in vram_patterns:
                possible_path = os.path.join(sprite_dir, pattern)
                if os.path.exists(possible_path):
                    return possible_path

        # Check session data from settings manager
        settings = get_settings_manager()
        session_data = settings.get_session_data()
        if SETTINGS_KEY_VRAM_PATH in session_data:
            vram_path = session_data[SETTINGS_KEY_VRAM_PATH]
            if vram_path and os.path.exists(vram_path):
                return vram_path

        # Check last used injection VRAM (using ROM injection namespace)
        last_injection_vram = settings.get_value(
            SETTINGS_NS_ROM_INJECTION, SETTINGS_KEY_LAST_INPUT_VRAM, ""
        )
        if last_injection_vram and os.path.exists(last_injection_vram):
            return last_injection_vram

        return ""

    def _suggest_output_vram_path(self, input_vram_path: str) -> str:
        """Suggest output VRAM path based on input path with smart numbering"""
        base = os.path.splitext(input_vram_path)[0]

        # Check if base already ends with "_injected" to avoid duplication
        if base.endswith("_injected"):
            base = base[:-9]  # Remove "_injected"

        # Try _injected first
        suggested_path = f"{base}_injected.dmp"
        if not os.path.exists(suggested_path):
            return suggested_path

        # If _injected exists, try _injected2, _injected3, etc.
        counter = 2
        while counter <= 10:  # Reasonable limit
            suggested_path = f"{base}_injected{counter}.dmp"
            if not os.path.exists(suggested_path):
                return suggested_path
            counter += 1

        # If all numbered versions exist, just use the base with timestamp
        timestamp = int(time.time())
        return f"{base}_injected_{timestamp}.dmp"

    def _suggest_output_rom_path(self, input_rom_path: str) -> str:
        """Suggest output ROM path based on input path with smart numbering"""
        base = os.path.splitext(input_rom_path)[0]
        ext = os.path.splitext(input_rom_path)[1]

        # Check if base already ends with "_modified" to avoid duplication
        if base.endswith("_modified"):
            base = base[:-9]  # Remove "_modified"

        # Try _modified first
        suggested_path = f"{base}_modified{ext}"
        if not os.path.exists(suggested_path):
            return suggested_path

        # If _modified exists, try _modified2, _modified3, etc.
        counter = 2
        while counter <= 10:  # Reasonable limit
            suggested_path = f"{base}_modified{counter}{ext}"
            if not os.path.exists(suggested_path):
                return suggested_path
            counter += 1

        # If all numbered versions exist, just use the base with timestamp
        timestamp = int(time.time())
        return f"{base}_modified_{timestamp}{ext}"

    def _get_rom_offset_from_vram(self, vram_offset_str: str) -> int | None:
        """Convert VRAM offset to ROM offset based on known mappings

        Args:
            vram_offset_str: VRAM offset as string (e.g., "0xC000")

        Returns:
            ROM offset as integer, or None if no mapping found
        """
        try:
            # Parse VRAM offset
            if isinstance(vram_offset_str, str):
                vram_offset = int(vram_offset_str, 16)
            else:
                vram_offset = vram_offset_str

            # Known VRAM to ROM mappings for Kirby Super Star
            # VRAM 0xC000 (sprite area) typically maps to ROM locations for sprite data
            if vram_offset == 0xC000:
                # Default to Kirby Normal sprite location
                return 0x0C8000

            # For other offsets, no direct mapping available
            # Could be extended with more mappings in the future
            return None

        except (ValueError, TypeError):
            return None

    def save_rom_injection_parameters(self):
        """Save ROM injection parameters to settings for future use"""
        settings = get_settings_manager()

        # Save input ROM path
        input_rom = self.input_rom_edit.text()
        if input_rom:
            settings.set_value(
                SETTINGS_NS_ROM_INJECTION, SETTINGS_KEY_LAST_INPUT_ROM, input_rom
            )

        # Save sprite location (from combo box)
        sprite_location_text = self.sprite_location_combo.currentText()
        if sprite_location_text and sprite_location_text != "Select sprite location...":
            settings.set_value(
                SETTINGS_NS_ROM_INJECTION,
                SETTINGS_KEY_LAST_SPRITE_LOCATION,
                sprite_location_text,
            )

        # Save custom offset if used
        custom_offset = self.rom_offset_hex_edit.text()
        if custom_offset:
            settings.set_value(
                SETTINGS_NS_ROM_INJECTION,
                SETTINGS_KEY_LAST_CUSTOM_OFFSET,
                custom_offset,
            )

        # Save fast compression setting
        fast_compression = self.fast_compression_check.isChecked()
        settings.set_value(
            SETTINGS_NS_ROM_INJECTION, SETTINGS_KEY_FAST_COMPRESSION, fast_compression
        )

        # Save settings to file
        try:
            settings.save()
        except Exception:
            logger.exception("Failed to save ROM injection parameters")

    def _load_sprite_preview(self):
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

    def _validate_sprite(self):
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
                QMessageBox.critical(
                    self, "Sprite Validation Failed", "\n".join(msg_parts)
                )
            else:
                # Just warnings - show as information
                QMessageBox.information(
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
