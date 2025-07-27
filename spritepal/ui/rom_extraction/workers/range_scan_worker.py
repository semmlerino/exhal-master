"""Worker thread for comprehensive range scanning of ROM data"""

from PyQt6.QtCore import QThread, pyqtSignal

from spritepal.utils.logging_config import get_logger

logger = get_logger(__name__)


class RangeScanWorker(QThread):
    """Worker thread for comprehensive scanning of ROM ranges to find all sprites"""

    sprite_found = pyqtSignal(int, float)  # offset, quality
    progress_update = pyqtSignal(int)  # current_offset
    scan_complete = pyqtSignal(bool)  # success
    scan_paused = pyqtSignal()  # scan was paused
    scan_resumed = pyqtSignal()  # scan was resumed
    scan_stopped = pyqtSignal()  # scan was stopped

    def __init__(self, rom_path: str, start_offset: int, end_offset: int,
                 step_size: int, extractor):
        """
        Initialize range scan worker

        Args:
            rom_path: Path to ROM file
            start_offset: Starting offset for scan
            end_offset: Ending offset for scan (inclusive)
            step_size: Step size between offsets to check
            extractor: ROM extractor instance
        """
        super().__init__()
        self.rom_path = rom_path
        self.start_offset = start_offset
        self.end_offset = end_offset
        self.step_size = step_size
        self.extractor = extractor

        # Scan parameters
        self.quality_threshold = 0.5
        self.min_sprite_size = 512  # At least 16 tiles (32 bytes per tile)
        self.max_sprite_size = 32768  # 32KB limit for decompression

        # Control flags
        self._is_paused = False
        self._should_stop = False

    def run(self):
        """Scan the entire specified range for valid sprites"""
        try:
            # Load ROM data once
            with open(self.rom_path, "rb") as f:
                rom_data = f.read()

            sprites_found = 0

            logger.info(f"Starting range scan: 0x{self.start_offset:06X} to 0x{self.end_offset:06X}")

            # Scan through the entire range
            for offset in range(self.start_offset, self.end_offset + 1, self.step_size):
                # Check if we should stop
                if self._should_stop:
                    logger.info("Range scan stopped by user")
                    self.scan_stopped.emit()
                    return

                # Handle pause state
                while self._is_paused and not self._should_stop:
                    self.msleep(100)  # Sleep 100ms while paused

                # Check stop again after potential pause
                if self._should_stop:
                    logger.info("Range scan stopped by user")
                    self.scan_stopped.emit()
                    return

                # Emit progress update periodically (every 1024 steps to avoid too many signals)
                if (offset - self.start_offset) % (self.step_size * 1024) == 0:
                    self.progress_update.emit(offset)

                # Boundary check
                if offset < 0 or offset >= len(rom_data):
                    continue

                try:
                    # Try to find compressed sprite at this offset
                    _, sprite_data = self.extractor.rom_injector.find_compressed_sprite(
                        rom_data, offset, expected_size=self.max_sprite_size
                    )

                    # Check if sprite data meets minimum size requirement
                    if len(sprite_data) >= self.min_sprite_size:
                        # Assess sprite quality
                        quality = self.extractor._assess_sprite_quality(sprite_data)

                        # If quality meets threshold, emit found signal
                        if quality >= self.quality_threshold:
                            self.sprite_found.emit(offset, quality)
                            sprites_found += 1
                            logger.debug(f"Found sprite at 0x{offset:06X} with quality {quality:.2f}")

                except Exception:
                    # Not a valid sprite at this offset, continue scanning
                    pass

            # Final progress update
            self.progress_update.emit(self.end_offset)

            logger.info(f"Range scan complete. Found {sprites_found} sprites in range "
                       f"0x{self.start_offset:06X} to 0x{self.end_offset:06X}")

            # Emit completion signal
            self.scan_complete.emit(True)

        except Exception:
            logger.exception("Error during range scan")
            self.scan_complete.emit(False)

    def pause_scan(self):
        """Pause the scanning process"""
        if not self._is_paused:
            self._is_paused = True
            logger.info("Range scan paused")
            self.scan_paused.emit()

    def resume_scan(self):
        """Resume the scanning process"""
        if self._is_paused:
            self._is_paused = False
            logger.info("Range scan resumed")
            self.scan_resumed.emit()

    def stop_scan(self):
        """Stop the scanning process"""
        self._should_stop = True
        self._is_paused = False  # Ensure we don't stay paused if stopping
        logger.info("Range scan stop requested")

    def is_paused(self) -> bool:
        """Check if scan is currently paused"""
        return self._is_paused

    def is_stopping(self) -> bool:
        """Check if scan is currently stopping"""
        return self._should_stop
