"""Worker thread for scanning ROM for sprite offsets"""

from PyQt6.QtCore import QThread, pyqtSignal

from spritepal.utils.logging_config import get_logger

logger = get_logger(__name__)


class SpriteScanWorker(QThread):
    """Worker thread for scanning ROM for sprite offsets"""

    progress = pyqtSignal(int, int)  # current, total
    sprite_found = pyqtSignal(dict)  # sprite info
    finished = pyqtSignal()

    def __init__(self, rom_path: str, extractor):
        super().__init__()
        self.rom_path = rom_path
        self.extractor = extractor

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

            logger.info(f"Starting focused sprite scan: 0x{start_offset:X} to 0x{end_offset:X}")
            logger.info(f"Size limits: {[f'{s//1024}KB' for s in size_limits]}")

            # Read ROM data once
            with open(self.rom_path, "rb") as rom_file:
                rom_data = rom_file.read()

            rom_size = len(rom_data)
            if end_offset > rom_size:
                end_offset = rom_size
                total_steps = (end_offset - start_offset) // step

            found_sprites = {}  # Track unique sprites by offset
            quality_threshold = 0.3  # Lowered threshold for PAL ROM compatibility

            logger.info("Note: PAL ROM sprites may be embedded within larger compressed blocks")

            # First pass: scan with each size limit
            for offset in range(start_offset, end_offset, step):
                current_step += 1
                self.progress.emit(current_step, total_steps)

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

            # Log summary statistics
            if found_sprites:
                qualities = [s["quality"] for s in found_sprites.values()]
                avg_quality = sum(qualities) / len(qualities)
                high_quality_count = sum(1 for q in qualities if q >= 0.7)

                logger.info(f"Scan complete. Found {len(found_sprites)} sprites:")
                logger.info(f"  - Average quality: {avg_quality:.2f}")
                logger.info(f"  - High quality (≥0.7): {high_quality_count}")
                logger.info(f"  - Quality range: {min(qualities):.2f} - {max(qualities):.2f}")
            else:
                logger.info("Scan complete. No valid sprites found.")

            self.finished.emit()

        except Exception:
            logger.exception("Error in sprite scan worker")
            self.finished.emit()
