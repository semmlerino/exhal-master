"""Worker thread for searching next/previous valid sprite"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.rom_extractor import ROMExtractor

from PyQt6.QtCore import QThread, pyqtSignal
from utils.logging_config import get_logger

logger = get_logger(__name__)


class SpriteSearchWorker(QThread):
    """Worker thread for searching next/previous valid sprite"""

    sprite_found = pyqtSignal(int, float)  # offset, quality
    search_complete = pyqtSignal(bool)  # found
    error = pyqtSignal(str, Exception)  # error message, exception
    progress = pyqtSignal(int, int)  # current, total

    def __init__(self, rom_path: str, start_offset: int, end_offset: int,
                 direction: int, extractor: "ROMExtractor", parent=None):
        super().__init__(parent)
        self.rom_path = rom_path
        self.start_offset = start_offset
        self.end_offset = end_offset
        self.direction = direction  # 1 for forward, -1 for backward
        self.extractor = extractor
        self._cancelled = False

        # Default step size
        self.step = 0x100  # 256-byte alignment

    def run(self):
        """Search for valid sprite in the specified direction"""
        try:
            with open(self.rom_path, "rb") as f:
                rom_data = f.read()

            # Search parameters
            max_search_distance = 0x100000  # Search up to 1MB away
            quality_threshold = 0.3  # Lower threshold for better detection
            rom_size = len(rom_data)

            # Determine search range
            if self.direction > 0:
                search_start = self.start_offset + self.step
                search_end = min(self.end_offset, self.start_offset + max_search_distance, rom_size)
                step = self.step
            else:
                # For backward search
                search_start = self.start_offset - self.step
                search_end = max(self.end_offset, self.start_offset - max_search_distance, -1)
                step = -self.step

            # Calculate total steps for progress
            total_steps = abs((search_end - search_start) // step)
            current_step = 0

            # Search for valid sprite
            for offset in range(search_start, search_end, step):
                if self._cancelled:
                    logger.debug("Search cancelled")
                    break

                if offset < 0 or offset >= rom_size:
                    continue

                # Update progress periodically
                current_step += 1
                if current_step % 10 == 0:
                    self.progress.emit(current_step, total_steps)

                try:
                    # Quick pre-check to avoid expensive operations
                    if not self._quick_check(rom_data, offset):
                        continue

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

                except Exception as e:
                    # Not a valid sprite, continue searching
                    logger.debug(f"Search check failed at 0x{offset:06X}: {e}")

            # No valid sprite found
            self.search_complete.emit(False)

        except Exception as e:
            logger.exception("Error in sprite search")
            self.error.emit("Search failed", e)
            self.search_complete.emit(False)

    def _quick_check(self, rom_data: bytes, offset: int) -> bool:
        """Quick validation to skip obviously empty areas"""
        if offset + 0x20 > len(rom_data):
            return False

        # Check for empty or uniform data
        chunk = rom_data[offset:offset+0x20]
        if all(b == 0 for b in chunk) or all(b == 0xFF for b in chunk):
            return False

        # Look for compression headers
        if chunk[0] == 0x10:  # LZ compression
            return True

        # Check for reasonable data variety
        unique_bytes = len(set(chunk))
        return unique_bytes > 4

    def cancel(self):
        """Cancel the search"""
        self._cancelled = True
