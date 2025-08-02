"""Worker thread for scanning ROM for sprite offsets"""

from PyQt6.QtCore import QThread, pyqtSignal

from spritepal.utils.logging_config import get_logger

logger = get_logger(__name__)


class SpriteScanWorker(QThread):
    """Worker thread for scanning ROM for sprite offsets"""

    progress = pyqtSignal(int, int)  # current, total
    sprite_found = pyqtSignal(dict)  # sprite info
    finished = pyqtSignal()
    cache_status = pyqtSignal(str)  # cache status message
    cache_progress = pyqtSignal(int)  # cache save progress 0-100

    def __init__(self, rom_path: str, extractor, use_cache=True):
        super().__init__()
        self.rom_path = rom_path
        self.extractor = extractor
        self.use_cache = use_cache
        self._last_save_progress = 0

    def run(self):
        """Scan ROM for valid sprite offsets with intelligent size limits"""
        try:
            # Define scan range based on known Kirby sprite locations
            # Scan both typical sprite ranges and where we found data in logs
            # PAL ROM seems to have sprites at different locations
            start_offset = 0xC0000  # Start earlier to catch 0xC0200, 0xC0300
            end_offset = 0xF0000   # Extended range to cover all possibilities
            step = 0x100  # Scan every 256 bytes

            # Use more targeted size limits based on known Kirby sprite sizes
            # Most Kirby character sprites are 8KB, enemies/bosses can be larger
            # PAL ROM may have different sizes, so being more permissive
            size_limits = [8192, 16384, 32768, 65536]  # 8KB, 16KB, 32KB, 64KB
            # Note: Larger sizes needed as sprites may be embedded in larger blocks

            total_steps = (end_offset - start_offset) // step
            current_step = 0
            found_sprites = {}  # Track unique sprites by offset

            # Define scan parameters for cache
            scan_params = {
                "start_offset": start_offset,
                "end_offset": end_offset,
                "alignment": step
            }

            # Initialize cache if enabled
            rom_cache = None
            original_start_offset = start_offset  # Save for progress calculations
            if self.use_cache:
                from spritepal.utils.rom_cache import get_rom_cache
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

                    # Calculate current step based on original range
                    current_step = (last_offset - original_start_offset) // step
                    # Update start position to continue from where we left off
                    start_offset = last_offset + step
                    # Keep total_steps based on original range for consistent progress
                    # total_steps already calculated correctly above
                    # Initialize last save progress to the current progress
                    self._last_save_progress = progress_pct
                else:
                    self.cache_status.emit("Starting fresh scan")

            logger.info(f"Starting focused sprite scan: 0x{start_offset:X} to 0x{end_offset:X}")
            logger.info(f"Size limits: {[f'{s//1024}KB' for s in size_limits]}")
            logger.info(f"Total steps: {total_steps}, starting at step: {current_step}")

            # Read ROM data once
            with open(self.rom_path, "rb") as rom_file:
                rom_data = rom_file.read()

            rom_size = len(rom_data)
            if end_offset > rom_size:
                end_offset = rom_size
                # Recalculate total steps based on original range for consistency
                total_steps = (end_offset - original_start_offset) // step

            quality_threshold = 0.3  # Lowered threshold for PAL ROM compatibility

            logger.info("Note: PAL ROM sprites may be embedded within larger compressed blocks")

            # First pass: scan with each size limit
            logger.debug(f"Starting scan loop from 0x{start_offset:X} to 0x{end_offset:X} step 0x{step:X}")
            last_scanned_offset = start_offset - step  # Initialize to one step before start
            for offset in range(start_offset, end_offset, step):
                last_scanned_offset = offset
                # Calculate current step based on original range for consistent progress
                current_step = (offset - original_start_offset) // step
                self.progress.emit(current_step, total_steps)

                # Log every 50 steps for debugging
                if current_step % 50 == 0:
                    logger.debug(f"Scan progress: step {current_step}/{total_steps} at offset 0x{offset:X}")

                # Try each size limit for this offset
                best_quality = 0.0
                best_sprite_info = None

                for size_limit in size_limits:
                    try:
                        # Try to decompress sprite at this offset with size limit
                        compressed_size, sprite_data = self.extractor.rom_injector.find_compressed_sprite(
                            rom_data, offset, expected_size=size_limit
                        )

                        # Skip if no data
                        if len(sprite_data) == 0:
                            continue

                        # Quick pre-validation
                        bytes_per_tile = 32
                        extra_bytes = len(sprite_data) % bytes_per_tile
                        num_tiles = len(sprite_data) // bytes_per_tile

                        # Skip if badly misaligned or too small
                        if extra_bytes > 16 or num_tiles < 16:
                            continue

                        # Calculate quality score with improved validation
                        quality = self.extractor._assess_sprite_quality(sprite_data)

                        # Check if sprite might be embedded within the data
                        # PAL ROMs often have sprites at offsets like 512, 1024, 2048
                        embedded_quality = 0.0
                        embedded_offset = 0

                        for test_offset in [512, 1024, 2048, 4096]:
                            if test_offset + 8192 <= len(sprite_data):
                                embedded_data = sprite_data[test_offset:test_offset + 8192]
                                embedded_score = self.extractor._assess_sprite_quality(embedded_data)
                                if embedded_score > embedded_quality:
                                    embedded_quality = embedded_score
                                    embedded_offset = test_offset

                        # Use the better quality score
                        if embedded_quality > quality:
                            quality = embedded_quality
                            if embedded_offset > 0:
                                logger.debug(f"Found embedded sprite at offset +{embedded_offset} within block")

                        # Only consider if quality meets threshold
                        if quality >= quality_threshold and quality > best_quality:
                            alignment_status = "perfect" if extra_bytes == 0 else f"{extra_bytes} extra bytes"

                            best_sprite_info = {
                                "offset": offset,
                                "offset_hex": f"0x{offset:X}",
                                "compressed_size": compressed_size,
                                "decompressed_size": len(sprite_data),
                                "tile_count": num_tiles,
                                "alignment": alignment_status,
                                "quality": quality,
                                "size_limit_used": size_limit
                            }
                            best_quality = quality

                            # If we found a perfect match (quality >= 0.8), stop trying other sizes
                            if quality >= 0.8:
                                break

                    except Exception:
                        # Decompression failed, try next size
                        continue

                # If we found a good sprite at this offset, add it
                if best_sprite_info:
                    found_sprites[offset] = best_sprite_info
                    self.sprite_found.emit(best_sprite_info)
                    logger.info(
                        f"Found sprite at 0x{offset:X}: quality={best_quality:.2f}, "
                        f"tiles={best_sprite_info['tile_count']}, "
                        f"size_limit={best_sprite_info['size_limit_used']//1024}KB"
                    )

                # Save partial results periodically (every 10% progress)
                if rom_cache and current_step > 0 and total_steps > 0:
                    # Calculate progress based on original range
                    # Account for the fact that range() excludes end_offset
                    actual_end = end_offset - step
                    if offset >= actual_end:
                        # We're at the last offset that will be scanned
                        progress_pct = 100
                    else:
                        progress_pct = min(int(((offset - original_start_offset) / (end_offset - original_start_offset)) * 100), 99)

                    # Save every 10% or if we're at the end
                    should_save = (progress_pct >= self._last_save_progress + 10) or (offset >= actual_end)

                    if should_save and progress_pct > self._last_save_progress:
                        self._last_save_progress = progress_pct
                        self.cache_status.emit(f"Saving progress ({progress_pct}%)...")

                        # Save partial scan results using correct API
                        found_sprites_list = list(found_sprites.values())

                        if rom_cache.save_partial_scan_results(
                            self.rom_path,
                            scan_params,
                            found_sprites_list,
                            offset,  # current_offset
                            False    # not completed
                        ):
                            self.cache_progress.emit(progress_pct)
                            logger.debug(f"Saved partial scan results at {progress_pct}% progress")

            # Scan loop has ended
            logger.info(f"Exited scan loop. Final offset was 0x{last_scanned_offset:X}, current_step={current_step}, total_steps={total_steps}")

            # Save final results after scan completes
            logger.debug(f"Scan loop completed. Found {len(found_sprites)} sprites total")
            if rom_cache:
                self.cache_status.emit("Saving final results...")
                found_sprites_list = list(found_sprites.values())
                logger.debug(f"Saving {len(found_sprites_list)} sprites to cache as completed")
                # Use the last scanned offset + step, or end_offset, whichever is smaller
                final_offset = min(last_scanned_offset + step, end_offset)
                if rom_cache.save_partial_scan_results(
                    self.rom_path,
                    scan_params,
                    found_sprites_list,
                    final_offset,   # final offset
                    True            # completed
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

                    logger.info(f"Scan complete. Found {len(found_sprites)} sprites:")
                    logger.info(f"  - Average quality: {avg_quality:.2f}")
                    logger.info(f"  - High quality (≥0.7): {high_quality_count}")
                    logger.info(f"  - Quality range: {min(qualities):.2f} - {max(qualities):.2f}")
                else:
                    # No quality data available (e.g., all sprites from cache)
                    logger.info(f"Scan complete. Found {len(found_sprites)} sprites (from cache)")
            else:
                logger.info("Scan complete. No valid sprites found.")

            self.finished.emit()

        except Exception as e:
            logger.exception("Error in sprite scan worker")
            # Emit error status so test can see what happened
            self.cache_status.emit(f"Error: {e!s}")
            # Always emit finished signal even on error
            self.finished.emit()
