"""Worker thread for searching next/previous valid sprite"""

from PyQt6.QtCore import QThread, pyqtSignal

from spritepal.utils.logging_config import get_logger

logger = get_logger(__name__)


class SpriteSearchWorker(QThread):
    """Worker thread for searching next/previous valid sprite"""

    sprite_found = pyqtSignal(int, float)  # offset, quality
    search_complete = pyqtSignal(bool)  # found

    def __init__(self, rom_path: str, start_offset: int, step: int, rom_size: int,
                 extractor, forward: bool = True):
        super().__init__()
        self.rom_path = rom_path
        self.start_offset = start_offset
        self.step = step
        self.rom_size = rom_size
        self.extractor = extractor
        self.forward = forward

    def run(self):
        """Search for valid sprite in the specified direction"""
        try:
            with open(self.rom_path, "rb") as f:
                rom_data = f.read()

            # Search parameters
            max_search_distance = 0x100000  # Search up to 1MB away
            quality_threshold = 0.5

            # Determine search range
            if self.forward:
                search_start = self.start_offset + self.step
                search_end = min(self.start_offset + max_search_distance, self.rom_size)
                step = self.step
            else:
                # For backward search, start from current position and go backwards
                search_start = self.start_offset - self.step
                search_end = max(-1, self.start_offset - max_search_distance)  # -1 so range stops at 0
                step = -self.step

            # Search for valid sprite
            for offset in range(search_start, search_end, step):
                if offset < 0 or offset >= self.rom_size:
                    continue

                try:
                    # Try to decompress with a reasonable size limit
                    _, sprite_data = self.extractor.rom_injector.find_compressed_sprite(
                        rom_data, offset, expected_size=32768  # 32KB limit for search
                    )

                    if len(sprite_data) >= 512:  # At least 16 tiles
                        # Assess quality
                        quality = self.extractor._assess_sprite_quality(sprite_data)

                        if quality >= quality_threshold:
                            self.sprite_found.emit(offset, quality)
                            self.search_complete.emit(True)
                            return

                except Exception:
                    # Not a valid sprite, continue searching
                    pass

            # No valid sprite found
            self.search_complete.emit(False)

        except Exception:
            logger.exception("Error in sprite search")
            self.search_complete.emit(False)
