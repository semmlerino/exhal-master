#!/usr/bin/env python3
"""
Worker thread for sprite extraction operations
Handles background extraction of sprites from VRAM dumps
"""

import os

from PyQt6.QtCore import QThread, pyqtSignal

from sprite_editor.sprite_editor_core import SpriteEditorCore


class ExtractWorker(QThread):
    """Worker thread for sprite extraction"""

    finished = pyqtSignal(object, int)  # image, tile_count
    error = pyqtSignal(str)
    progress = pyqtSignal(str)

    def __init__(
        self, vram_file, offset, size, tiles_per_row, palette_num=None, cgram_file=None
    ):
        super().__init__()
        self.vram_file = vram_file
        self.offset = offset
        self.size = size
        self.tiles_per_row = tiles_per_row
        self.palette_num = palette_num
        self.cgram_file = cgram_file
        self.core = SpriteEditorCore()

    def run(self):
        try:
            self.progress.emit("Extracting sprites from VRAM...")
            image, tile_count = self.core.extract_sprites(
                self.vram_file, self.offset, self.size, self.tiles_per_row
            )

            # Apply palette if requested
            if (
                self.palette_num is not None
                and self.cgram_file
                and os.path.exists(self.cgram_file)
            ):
                self.progress.emit(f"Applying palette {self.palette_num}...")
                palette = self.core.read_cgram_palette(
                    self.cgram_file, self.palette_num
                )
                if palette:
                    image.putpalette(palette)

            self.finished.emit(image, tile_count)
        except Exception as e:
            self.error.emit(str(e))
