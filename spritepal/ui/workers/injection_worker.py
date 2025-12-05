"""
Qt worker thread for sprite injection process.
This module contains the Qt-specific worker thread for sprite injection.
"""
from __future__ import annotations

from core.injector import SpriteInjector
from PySide6.QtCore import QThread, Signal
from typing_extensions import override
from utils.logging_config import get_logger

logger = get_logger(__name__)


class InjectionWorker(QThread):
    """Worker thread for sprite injection process"""

    progress: Signal = Signal(str)  # status message
    injection_finished: Signal = Signal(bool, str)  # success, message

    def __init__(
        self,
        sprite_path: str,
        vram_input: str,
        vram_output: str,
        offset: int,
        metadata_path: str | None = None,
    ):
        super().__init__()
        self.sprite_path: str = sprite_path
        self.vram_input: str = vram_input
        self.vram_output: str = vram_output
        self.offset: int = offset
        self.metadata_path: str | None = metadata_path
        self.injector: SpriteInjector = SpriteInjector()

    @override
    def run(self) -> None:
        """Run the injection process"""
        logger.info(f"Starting injection worker: sprite={self.sprite_path}, vram_in={self.vram_input}, vram_out={self.vram_output}")
        try:
            # Load metadata if available
            if self.metadata_path:
                self.progress.emit("Loading metadata...")
                logger.debug(f"Loading metadata from {self.metadata_path}")
                self.injector.load_metadata(self.metadata_path)

            # Validate sprite
            self.progress.emit("Validating sprite file...")
            logger.debug(f"Validating sprite: {self.sprite_path}")
            valid, message = self.injector.validate_sprite(self.sprite_path)
            if not valid:
                logger.error(f"Sprite validation failed: {message}")
                self.injection_finished.emit(False, message)
                return

            # Perform injection
            self.progress.emit("Converting sprite to 4bpp format...")
            self.progress.emit(f"Injecting into VRAM at offset 0x{self.offset:04X}...")

            success, message = self.injector.inject_sprite(
                self.sprite_path, self.vram_input, self.vram_output, self.offset
            )

            if success:
                self.progress.emit("Injection complete!")
                logger.info(f"Injection completed successfully: {message}")
            else:
                logger.error(f"Injection failed: {message}")

            self.injection_finished.emit(success, message)

        except Exception as e:
            logger.exception("Injection worker encountered unexpected error")
            self.injection_finished.emit(False, f"Unexpected error: {e!s}")
