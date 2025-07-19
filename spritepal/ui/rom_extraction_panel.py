"""
ROM extraction panel for SpritePal
"""

import os
from typing import Optional

from PyQt6.QtCore import pyqtSignal, QThread
from PyQt6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
    QSplitter,
)

from spritepal.core.rom_extractor import ROMExtractor
from spritepal.ui.widgets.sprite_preview_widget import SpritePreviewWidget
from spritepal.utils.logging_config import get_logger
from spritepal.utils.settings_manager import get_settings_manager

logger = get_logger(__name__)


class ROMExtractionPanel(QWidget):
    """Panel for ROM-based sprite extraction"""
    
    # Signals
    files_changed = pyqtSignal()
    extraction_ready = pyqtSignal(bool)
    rom_extraction_requested = pyqtSignal(str, int, str, str)  # rom_path, offset, output_base, sprite_name
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.rom_path = ""
        self.sprite_locations = {}
        self.rom_extractor = ROMExtractor()
        self._setup_ui()
        
    def _setup_ui(self):
        """Initialize the user interface"""
        main_layout = QVBoxLayout()
        
        # Create splitter for left panel and preview
        splitter = QSplitter()
        
        # Left panel for controls
        left_panel = QWidget()
        layout = QVBoxLayout()
        
        # ROM file selection
        rom_group = QGroupBox("ROM File")
        rom_layout = QVBoxLayout()
        
        rom_path_layout = QHBoxLayout()
        rom_path_layout.addWidget(QLabel("ROM:"))
        self.rom_path_edit = QLineEdit()
        self.rom_path_edit.setPlaceholderText("Select ROM file...")
        self.rom_path_edit.setReadOnly(True)
        rom_path_layout.addWidget(self.rom_path_edit)
        
        self.browse_rom_btn = QPushButton("Browse...")
        self.browse_rom_btn.clicked.connect(self._browse_rom)
        rom_path_layout.addWidget(self.browse_rom_btn)
        
        rom_layout.addLayout(rom_path_layout)
        rom_group.setLayout(rom_layout)
        layout.addWidget(rom_group)
        
        # Sprite location selection
        sprite_group = QGroupBox("Sprite Selection")
        sprite_layout = QVBoxLayout()
        
        location_layout = QHBoxLayout()
        location_layout.addWidget(QLabel("Sprite:"))
        self.sprite_combo = QComboBox()
        self.sprite_combo.setMinimumWidth(250)
        self.sprite_combo.addItem("Select ROM file first...", None)
        self.sprite_combo.setEnabled(False)
        self.sprite_combo.currentIndexChanged.connect(self._on_sprite_changed)
        location_layout.addWidget(self.sprite_combo)
        location_layout.addStretch()
        
        sprite_layout.addLayout(location_layout)
        
        # Show selected offset
        offset_layout = QHBoxLayout()
        offset_layout.addWidget(QLabel("Offset:"))
        self.offset_label = QLabel("--")
        self.offset_label.setMinimumWidth(100)
        offset_layout.addWidget(self.offset_label)
        offset_layout.addStretch()
        sprite_layout.addLayout(offset_layout)
        
        sprite_group.setLayout(sprite_layout)
        layout.addWidget(sprite_group)
        
        # Optional CGRAM for palettes
        cgram_group = QGroupBox("Palette Data (Optional)")
        cgram_layout = QVBoxLayout()
        
        # Info label about default palettes
        info_label = QLabel("Note: Palettes will be extracted from ROM when available.\n"
                           "Common sprites also have default palettes as fallback.\n"
                           "CGRAM is optional for custom palette overrides.")
        info_label.setWordWrap(True)
        info_label.setStyleSheet("QLabel { color: #666; font-style: italic; }")
        cgram_layout.addWidget(info_label)
        
        cgram_path_layout = QHBoxLayout()
        cgram_path_layout.addWidget(QLabel("CGRAM:"))
        self.cgram_path_edit = QLineEdit()
        self.cgram_path_edit.setPlaceholderText("Select CGRAM file for custom palettes (optional)...")
        self.cgram_path_edit.setReadOnly(True)
        cgram_path_layout.addWidget(self.cgram_path_edit)
        
        self.browse_cgram_btn = QPushButton("Browse...")
        self.browse_cgram_btn.clicked.connect(self._browse_cgram)
        cgram_path_layout.addWidget(self.browse_cgram_btn)
        
        cgram_layout.addLayout(cgram_path_layout)
        cgram_group.setLayout(cgram_layout)
        layout.addWidget(cgram_group)
        
        # Output name
        output_group = QGroupBox("Output")
        output_layout = QVBoxLayout()
        
        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("Name:"))
        self.output_name_edit = QLineEdit()
        self.output_name_edit.setPlaceholderText("Enter output base name...")
        self.output_name_edit.textChanged.connect(self._check_extraction_ready)
        name_layout.addWidget(self.output_name_edit)
        
        output_layout.addLayout(name_layout)
        output_group.setLayout(output_layout)
        layout.addWidget(output_group)
        
        layout.addStretch()
        left_panel.setLayout(layout)
        
        # Add preview widget to right side
        self.preview_widget = SpritePreviewWidget("Sprite Preview")
        
        # Add panels to splitter
        splitter.addWidget(left_panel)
        splitter.addWidget(self.preview_widget)
        splitter.setStretchFactor(1, 1)  # Make preview expand
        
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
            self.rom_path = filename
            self.rom_path_edit.setText(filename)
            settings.set_last_used_directory(os.path.dirname(filename))
            self._load_rom_sprites()
            self.files_changed.emit()
            
    def _browse_cgram(self):
        """Browse for CGRAM file"""
        settings = get_settings_manager()
        
        # Try to use ROM directory as default
        default_dir = os.path.dirname(self.rom_path) if self.rom_path else settings.get_default_directory()
        
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Select CGRAM File (Optional)",
            default_dir,
            "CGRAM Files (*.dmp *.bin);;All Files (*.*)"
        )
        
        if filename:
            self.cgram_path_edit.setText(filename)
            settings.set_last_used_directory(os.path.dirname(filename))
            
    def _load_rom_sprites(self):
        """Load known sprite locations from ROM"""
        self.sprite_combo.clear()
        self.sprite_locations = {}
        
        if not self.rom_path:
            self.sprite_combo.addItem("Select ROM file first...", None)
            self.sprite_combo.setEnabled(False)
            return
            
        try:
            # Get known sprite locations
            locations = self.rom_extractor.get_known_sprite_locations(self.rom_path)
            
            if locations:
                self.sprite_combo.addItem("Select sprite to extract...", None)
                
                for name, pointer in locations.items():
                    display_name = name.replace("_", " ").title()
                    self.sprite_combo.addItem(
                        f"{display_name} (0x{pointer.offset:06X})",
                        (name, pointer.offset)
                    )
                self.sprite_locations = locations
                self.sprite_combo.setEnabled(True)
            else:
                self.sprite_combo.addItem("No known sprites for this ROM", None)
                self.sprite_combo.setEnabled(False)
                
        except Exception as e:
            logger.error(f"Failed to load sprite locations: {e}")
            self.sprite_combo.addItem("Error loading ROM", None)
            self.sprite_combo.setEnabled(False)
            
    def _on_sprite_changed(self, index: int):
        """Handle sprite selection change"""
        if index > 0:
            data = self.sprite_combo.currentData()
            if data:
                sprite_name, offset = data
                self.offset_label.setText(f"0x{offset:06X}")
                
                # Auto-generate output name based on sprite
                if not self.output_name_edit.text():
                    self.output_name_edit.setText(f"{sprite_name}_sprites")
                    
                # Show preview of selected sprite
                self._preview_sprite(sprite_name, offset)
        else:
            self.offset_label.setText("--")
            self.preview_widget.clear()
            
        self._check_extraction_ready()
        
    def _check_extraction_ready(self):
        """Check if we have all required inputs for extraction"""
        ready = (
            self.rom_path and
            self.sprite_combo.currentIndex() > 0 and
            self.output_name_edit.text()
        )
        self.extraction_ready.emit(ready)
        
    def get_extraction_params(self) -> Optional[dict]:
        """Get parameters for ROM extraction"""
        if not self.rom_path or self.sprite_combo.currentIndex() <= 0:
            return None
            
        data = self.sprite_combo.currentData()
        if not data:
            return None
            
        sprite_name, offset = data
        
        return {
            "rom_path": self.rom_path,
            "sprite_offset": offset,
            "sprite_name": sprite_name,
            "output_base": self.output_name_edit.text(),
            "cgram_path": self.cgram_path_edit.text() if self.cgram_path_edit.text() else None
        }
        
    def clear_files(self):
        """Clear all file selections"""
        self.rom_path = ""
        self.rom_path_edit.clear()
        self.cgram_path_edit.clear()
        self.output_name_edit.clear()
        self.sprite_combo.clear()
        self.sprite_combo.addItem("Select ROM file first...", None)
        self.sprite_combo.setEnabled(False)
        self.offset_label.setText("--")
        self.sprite_locations = {}
        self._check_extraction_ready()
        self.preview_widget.clear()
        
    def _preview_sprite(self, sprite_name: str, offset: int):
        """Preview sprite from ROM"""
        if not self.rom_path:
            return
            
        # Start preview loading in background
        self.preview_widget.info_label.setText("Loading preview...")
        
        # Create and start preview worker
        self.preview_worker = SpritePreviewWorker(
            self.rom_path, offset, sprite_name, self.rom_extractor
        )
        self.preview_worker.preview_ready.connect(self._on_preview_ready)
        self.preview_worker.preview_error.connect(self._on_preview_error)
        self.preview_worker.start()
        
    def _on_preview_ready(self, tile_data: bytes, width: int, height: int, sprite_name: str):
        """Handle preview data ready"""
        self.preview_widget.load_sprite_from_4bpp(tile_data, width, height, sprite_name)
        
    def _on_preview_error(self, error_msg: str):
        """Handle preview error"""
        self.preview_widget.clear()
        self.preview_widget.info_label.setText(f"Preview error: {error_msg}")


class SpritePreviewWorker(QThread):
    """Worker thread for loading sprite previews"""
    
    preview_ready = pyqtSignal(bytes, int, int, str)  # tile_data, width, height, sprite_name
    preview_error = pyqtSignal(str)  # error message
    
    def __init__(self, rom_path: str, offset: int, sprite_name: str, extractor):
        super().__init__()
        self.rom_path = rom_path
        self.offset = offset
        self.sprite_name = sprite_name
        self.extractor = extractor
        
    def run(self):
        """Load sprite preview in background"""
        try:
            # Read ROM data
            with open(self.rom_path, 'rb') as f:
                rom_data = f.read()
            
            # Find and decompress sprite
            compressed_size, tile_data = self.extractor.rom_injector.find_compressed_sprite(
                rom_data, self.offset
            )
            
            # Calculate dimensions (assume standard 128x128 for preview)
            num_tiles = len(tile_data) // 32  # 32 bytes per tile
            tiles_per_row = 16
            tile_rows = (num_tiles + tiles_per_row - 1) // tiles_per_row
            
            width = min(tiles_per_row * 8, 128)
            height = min(tile_rows * 8, 128)
            
            self.preview_ready.emit(tile_data, width, height, self.sprite_name)
            
        except Exception as e:
            self.preview_error.emit(str(e))