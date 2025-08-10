"""Worker thread for scanning ROM for sprite offsets"""

import threading
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from PySide6.QtCore import QObject

from PySide6.QtCore import Signal

from core.parallel_sprite_finder import ParallelSpriteFinder
from core.workers.base import BaseWorker, handle_worker_errors
from utils.logging_config import get_logger

logger = get_logger(__name__)


class SpriteScanWorker(BaseWorker):
    """Worker thread for scanning ROM for sprite offsets"""

    # Custom signals (BaseWorker provides progress, error, warning, operation_finished)
    sprite_found = Signal(dict)  # sprite info
    finished = Signal()  # Legacy compatibility - maps to operation_finished
    cache_status = Signal(str)  # cache status message
    cache_progress = Signal(int)  # cache save progress 0-100

    # For compatibility with existing code that expects (current, total) progress
    progress_detailed = Signal(int, int)  # current, total

    def __init__(self, rom_path: str, extractor, use_cache: bool = True, parent: "QObject | None" = None):
        super().__init__(parent)
        self.rom_path = rom_path
        self.extractor = extractor
        self.use_cache = use_cache
        self._last_save_progress = 0
        self._cancellation_token = threading.Event()
        self._parallel_finder = ParallelSpriteFinder(
            num_workers=4,
            chunk_size=0x40000,  # 256KB chunks
            step_size=0x100      # 256-byte alignment
        )

    @handle_worker_errors("sprite scanning", handle_interruption=True)
    def run(self):
        """Scan ROM for valid sprite offsets using parallel processing"""
        self._cancellation_token.clear()

        # Define scan range based on known Kirby sprite locations
        # Scan both typical sprite ranges and where we found data in logs
        # PAL ROM seems to have sprites at different locations
        start_offset = 0xC0000  # Start earlier to catch 0xC0200, 0xC0300
        end_offset = 0xF0000   # Extended range to cover all possibilities

        found_sprites = {}  # Track unique sprites by offset

        # Define scan parameters for cache
        scan_params = {
            "start_offset": start_offset,
            "end_offset": end_offset,
            "alignment": 0x100
        }

        # Initialize cache if enabled
        rom_cache = None
        original_start_offset = start_offset  # Save for progress calculations
        if self.use_cache:
            from utils.rom_cache import (
                get_rom_cache,  # Delayed import to avoid circular dependency
            )
            rom_cache = get_rom_cache()
            self.cache_status.emit("Checking cache...")
            logger.debug(f"Checking cache with params: {scan_params}")
            partial_cache = rom_cache.get_partial_scan_results(self.rom_path, scan_params)
            logger.debug(f"Cache lookup result: {partial_cache is not None}")

            if partial_cache:
                # Resume from cache - use correct field names
                cached_sprites = partial_cache.get("found_sprites", [])
                found_count = len(cached_sprites)
                last_offset = partial_cache.get("current_offset", start_offset)
                progress_pct = int(((last_offset - original_start_offset) / (end_offset - original_start_offset)) * 100)

                self.cache_status.emit(f"Resuming from {progress_pct}% (found {found_count} sprites)")
                logger.info(f"Resuming scan from offset 0x{last_offset:X}")

                # Load already-found sprites
                for sprite_info in cached_sprites:
                    offset = sprite_info.get("offset")
                    if offset:
                        found_sprites[offset] = sprite_info
                        # Emit the cached sprites immediately so they appear in the dialog
                        self.sprite_found.emit(sprite_info)

                # Update start position to continue from where we left off
                start_offset = last_offset + 0x100
                # Initialize last save progress to the current progress
                self._last_save_progress = progress_pct
            else:
                self.cache_status.emit("Starting fresh scan")

        logger.info(f"Starting parallel sprite scan: 0x{start_offset:X} to 0x{end_offset:X}")

        # Progress callback to handle results as they come in
        def progress_callback(current_progress, total_progress):
            # Map parallel finder progress to our progress signals
            total_range = end_offset - original_start_offset  # Use original for consistency
            current_range = (current_progress / 100) * total_range
            current_step = int(current_range // 0x100)
            total_steps = int(total_range // 0x100)
            # Emit both legacy and new progress signals
            self.progress_detailed.emit(current_step, total_steps)
            percent = int((current_progress / 100) * 100)  # Already a percentage
            self.emit_progress(percent, f"Scanning... ({current_step}/{total_steps})")

            # Save partial results periodically based on progress
            if rom_cache and current_progress >= self._last_save_progress + 10:
                self._last_save_progress = current_progress
                self.cache_status.emit(f"Saving progress ({current_progress}%)...")

                found_sprites_list = list(found_sprites.values())
                current_offset = original_start_offset + int(current_range)

                if rom_cache.save_partial_scan_results(
                    self.rom_path,
                    scan_params,
                    found_sprites_list,
                    current_offset,
                    False  # not completed
                ):
                    self.cache_progress.emit(current_progress)
                    logger.debug(f"Saved partial scan results at {current_progress}% progress")

        # Execute parallel search
        search_results = self._parallel_finder.search_parallel(
            self.rom_path,
            start_offset=start_offset,
            end_offset=end_offset,
            progress_callback=progress_callback,
            cancellation_token=self._cancellation_token
        )

        # Convert SearchResult objects to legacy sprite info format and emit
        for result in search_results:
            sprite_info = {
                "offset": result.offset,
                "offset_hex": f"0x{result.offset:X}",
                "compressed_size": result.compressed_size,
                "decompressed_size": result.size,
                "tile_count": result.tile_count,
                "alignment": "perfect" if result.size % 32 == 0 else f"{result.size % 32} extra bytes",
                "quality": result.confidence
            }

            found_sprites[result.offset] = sprite_info
            self.sprite_found.emit(sprite_info)

            logger.info(
                f"Found sprite at 0x{result.offset:X}: quality={result.confidence:.2f}, "
                f"tiles={result.tile_count}"
            )

        # Save final results after scan completes
        logger.debug(f"Parallel scan completed. Found {len(found_sprites)} sprites total")
        if rom_cache:
            self.cache_status.emit("Saving final results...")
            found_sprites_list = list(found_sprites.values())
            logger.debug(f"Saving {len(found_sprites_list)} sprites to cache as completed")

            if rom_cache.save_partial_scan_results(
                self.rom_path,
                scan_params,
                found_sprites_list,
                end_offset,   # final offset
                True          # completed
            ):
                # Ensure we emit 100% progress for the final save
                self.cache_progress.emit(100)
                logger.info("Saved final scan results to cache")

        # Log summary statistics
        logger.debug("Preparing summary statistics")
        if found_sprites:
            # Filter out sprites that don't have quality (e.g., from cache)
            sprites_with_quality = [s for s in found_sprites.values() if "quality" in s]
            if sprites_with_quality:
                qualities = [s["quality"] for s in sprites_with_quality]
                avg_quality = sum(qualities) / len(qualities)
                high_quality_count = sum(1 for q in qualities if q >= 0.7)

                logger.info(f"Parallel scan complete. Found {len(found_sprites)} sprites:")
                logger.info(f"  - Average quality: {avg_quality:.2f}")
                logger.info(f"  - High quality (≥0.7): {high_quality_count}")
                logger.info(f"  - Quality range: {min(qualities):.2f} - {max(qualities):.2f}")
            else:
                # No quality data available (e.g., all sprites from cache)
                logger.info(f"Parallel scan complete. Found {len(found_sprites)} sprites (from cache)")
        else:
            logger.info("Parallel scan complete. No valid sprites found.")

        self.finished.emit()
        self.operation_finished.emit(True, f"Scan complete. Found {len(found_sprites)} sprites.")

        # Cleanup parallel finder resources
        if hasattr(self, "_parallel_finder"):
            try:
                self._parallel_finder.shutdown()
            except Exception as cleanup_error:
                logger.warning(f"Error during parallel finder cleanup: {cleanup_error}")

    def cancel(self):
        """Cancel the scanning operation"""
        # Call parent cancel method first
        super().cancel()
        # Also set our cancellation token for the parallel finder
        if hasattr(self, "_cancellation_token"):
            self._cancellation_token.set()
            logger.debug("Sprite scan cancellation requested")
