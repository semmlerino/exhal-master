"""Worker thread for comprehensive range scanning of ROM data"""

from typing import Any

from PyQt6.QtCore import QThread, pyqtSignal

from utils.logging_config import get_logger
from utils.rom_cache import get_rom_cache

logger = get_logger(__name__)


class RangeScanWorker(QThread):
    """Worker thread for comprehensive scanning of ROM ranges to find all sprites"""

    sprite_found = pyqtSignal(int, float)  # offset, quality
    progress_update = pyqtSignal(int, int)  # current_offset, progress_percentage
    scan_complete = pyqtSignal(bool)  # success
    scan_paused = pyqtSignal()  # scan was paused
    scan_resumed = pyqtSignal()  # scan was resumed
    scan_stopped = pyqtSignal()  # scan was stopped
    cache_status = pyqtSignal(str)  # cache status message
    cache_progress_saved = pyqtSignal(int, int, int)  # current_offset, total_sprites_found, progress_percentage

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

        # Cache integration
        self.rom_cache = get_rom_cache()
        self.found_sprites: list[dict[str, Any]] = []
        self.current_offset = start_offset
        self.scan_params: dict[str, Any] = {}

    def run(self):
        """Scan the entire specified range for valid sprites"""
        try:
            # Load ROM data once
            with open(self.rom_path, "rb") as f:
                rom_data = f.read()

            # Check for cached partial results
            self.scan_params = {
                "start_offset": self.start_offset,
                "end_offset": self.end_offset,
                "step": self.step_size,
                "quality_threshold": self.quality_threshold,
                "min_sprite_size": self.min_sprite_size,
                "max_sprite_size": self.max_sprite_size
            }

            cached_progress = self.rom_cache.get_partial_scan_results(self.rom_path, self.scan_params)
            if cached_progress and not cached_progress.get("completed", False):
                # Resume from cached progress
                self.found_sprites = cached_progress.get("found_sprites", [])
                self.current_offset = cached_progress.get("current_offset", self.start_offset)
                progress_pct = int(((self.current_offset - self.start_offset) / (self.end_offset - self.start_offset)) * 100)
                self.cache_status.emit(f"Resumed from cache: {progress_pct}% complete, {len(self.found_sprites)} sprites found")
                logger.info(f"Resuming scan from cached progress: 0x{self.current_offset:06X}, {len(self.found_sprites)} sprites found")
            else:
                self.current_offset = self.start_offset
                self.found_sprites = []
                if cached_progress and cached_progress.get("completed", False):
                    self.cache_status.emit("Starting fresh scan (completed cache found but ignored)")
                    logger.info("Found completed scan in cache, but rescanning per user request")
                else:
                    self.cache_status.emit("Starting fresh scan (no cache found)")

            sprites_found = len(self.found_sprites)

            logger.info(f"Starting range scan: 0x{self.current_offset:06X} to 0x{self.end_offset:06X}")

            # Scan through the range starting from current_offset
            for offset in range(self.current_offset, self.end_offset + 1, self.step_size):
                self.current_offset = offset
                # Check if we should stop
                if self._should_stop:
                    logger.info("Range scan stopped by user")
                    # Save progress to cache before stopping
                    self._save_progress(self.scan_params, completed=False)
                    self.scan_stopped.emit()
                    return

                # Handle pause state
                while self._is_paused and not self._should_stop:
                    self.msleep(100)  # Sleep 100ms while paused

                # Check stop again after potential pause
                if self._should_stop:
                    logger.info("Range scan stopped by user")
                    # Save progress to cache before stopping
                    self._save_progress(self.scan_params, completed=False)
                    self.scan_stopped.emit()
                    return

                # Emit progress update periodically (every 1024 steps to avoid too many signals)
                if (offset - self.start_offset) % (self.step_size * 1024) == 0:
                    # Calculate progress as percentage of scan range
                    scan_range = self.end_offset - self.start_offset
                    progress_pct = int(((offset - self.start_offset) / scan_range) * 100) if scan_range > 0 else 0
                    self.progress_update.emit(offset, progress_pct)
                    # Also save progress to cache periodically
                    if self._save_progress(self.scan_params, completed=False):
                        self.cache_progress_saved.emit(offset, len(self.found_sprites), progress_pct)

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
                            # Add to cached sprites list
                            sprite_info = {
                                "offset": offset,
                                "quality": quality,
                                "size": len(sprite_data)
                            }
                            self.found_sprites.append(sprite_info)
                            logger.debug(f"Found sprite at 0x{offset:06X} with quality {quality:.2f}")

                except (ValueError, IndexError, KeyError):
                    # Expected errors: invalid sprite data, invalid offset, etc.
                    # These are normal during scanning, continue silently
                    pass
                except (MemoryError, OSError) as e:
                    # Serious errors that might indicate system issues
                    logger.warning(f"System error at offset 0x{offset:06X}: {e}")
                    # Continue scanning but log the issue
                except Exception as e:
                    # Unexpected errors - log but continue
                    logger.debug(f"Unexpected error at offset 0x{offset:06X}: {e}")

            # Final progress update
            self.progress_update.emit(self.end_offset, 100)

            logger.info(f"Range scan complete. Found {sprites_found} sprites in range "
                       f"0x{self.start_offset:06X} to 0x{self.end_offset:06X}")

            # Save completed scan to cache
            if self._save_progress(self.scan_params, completed=True):
                self.cache_status.emit(f"Scan complete - saved {len(self.found_sprites)} sprites to cache")

            # Emit completion signal
            self.scan_complete.emit(True)

        except OSError:
            logger.exception("File I/O error during range scan")
            self.scan_complete.emit(False)
        except MemoryError:
            logger.exception("Memory error during range scan")
            self.scan_complete.emit(False)
        except Exception:
            logger.exception("Unexpected error during range scan")
            self.scan_complete.emit(False)

    def pause_scan(self):
        """Pause the scanning process"""
        if not self._is_paused:
            self._is_paused = True
            logger.info("Range scan paused")
            # Save progress when pausing
            if self.scan_params:  # Only save if scan has started
                self._save_progress(self.scan_params, completed=False)
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

    def _save_progress(self, scan_params: dict[str, Any], completed: bool = False) -> bool:
        """Save current scan progress to cache"""
        try:
            return self.rom_cache.save_partial_scan_results(
                self.rom_path,
                scan_params,
                self.found_sprites,
                self.current_offset,
                completed
            )
        except Exception as e:
            logger.warning(f"Failed to save scan progress to cache: {e}")
            return False
