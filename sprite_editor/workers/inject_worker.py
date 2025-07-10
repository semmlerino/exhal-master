#!/usr/bin/env python3
"""
Worker thread for sprite injection operations
Handles background injection of sprites into VRAM dumps
"""

from PyQt6.QtCore import QThread, pyqtSignal

from sprite_editor.sprite_editor_core import SpriteEditorCore


class InjectWorker(QThread):
    """Worker thread for sprite injection"""

    finished = pyqtSignal(str)  # output file
    error = pyqtSignal(str)
    progress = pyqtSignal(str)

    def __init__(self, png_file, vram_file, offset, output_file):
        super().__init__()
        self.png_file = png_file
        self.vram_file = vram_file
        self.offset = offset
        self.output_file = output_file
        self.core = SpriteEditorCore()

    def run(self):
        try:
            # Validate PNG
            self.progress.emit("Validating PNG file...")
            valid, issues = self.core.validate_png_for_snes(self.png_file)
            if not valid:
                self.error.emit("PNG validation failed:\n" + "\n".join(issues))
                return

            # Convert to SNES format
            self.progress.emit("Converting to SNES format...")
            tile_data, tile_count = self.core.png_to_snes(self.png_file)

            # Inject into VRAM
            self.progress.emit(f"Injecting {tile_count} tiles into VRAM...")
            output = self.core.inject_into_vram(
                tile_data, self.vram_file, self.offset, self.output_file
            )

            self.finished.emit(output)
        except Exception as e:
            self.error.emit(str(e))
