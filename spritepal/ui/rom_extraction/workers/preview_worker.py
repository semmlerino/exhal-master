"""Worker thread for loading sprite previews"""

import os

from PyQt6.QtCore import QThread, pyqtSignal

from spritepal.utils.logging_config import get_logger

logger = get_logger(__name__)


class SpritePreviewWorker(QThread):
    """Worker thread for loading sprite previews"""

    preview_ready = pyqtSignal(
        bytes, int, int, str
    )  # tile_data, width, height, sprite_name
    preview_error = pyqtSignal(str)  # error message

    def __init__(self, rom_path: str, offset: int, sprite_name: str, extractor, sprite_config=None):
        super().__init__()
        self.rom_path = rom_path
        self.offset = offset
        self.sprite_name = sprite_name
        self.extractor = extractor
        self.sprite_config = sprite_config

    def run(self):
        """Load sprite preview in background"""
        try:
            # Validate inputs
            if not self.rom_path or not os.path.exists(self.rom_path):
                raise FileNotFoundError(f"ROM file not found: {self.rom_path}")

            if self.offset < 0:
                raise ValueError(f"Invalid offset: 0x{self.offset:X} (negative)")

            # Read ROM data with file size validation
            try:
                with open(self.rom_path, "rb") as f:
                    rom_data = f.read()
            except PermissionError as e:
                raise PermissionError(f"Cannot read ROM file: {self.rom_path}") from e
            except OSError as e:
                raise OSError(f"Error reading ROM file: {e}") from e

            # Validate ROM size
            rom_size = len(rom_data)
            if rom_size < 0x8000:  # Minimum reasonable SNES ROM size
                raise ValueError(f"ROM file too small: {rom_size} bytes")

            # Validate offset is within ROM bounds
            if self.offset >= rom_size:
                raise ValueError(
                    f"Offset 0x{self.offset:X} is beyond ROM size (0x{rom_size:X})"
                )

            # Find and decompress sprite with better error handling
            try:
                # Check if we have offset variants and expected size from sprite config
                offset_variants = []
                expected_size = None
                if hasattr(self, "sprite_config") and self.sprite_config:
                    offset_variants = getattr(self.sprite_config, "offset_variants", [])
                    expected_size = getattr(self.sprite_config, "estimated_size", None)
                    if expected_size:
                        logger.debug(f"Using expected size from config: {expected_size} bytes")
                    else:
                        # Try to get expected size from sprite configurations
                        header = self.extractor.rom_injector.read_rom_header(self.rom_path)
                        sprite_configs = self.extractor.sprite_config_loader.get_game_sprites(
                            header.title, header.checksum
                        )
                        if self.sprite_name in sprite_configs:
                            expected_size = sprite_configs[self.sprite_name].estimated_size
                            logger.debug(f"Got expected size from config: {expected_size} bytes")

                # Apply default fallback if no expected size found
                if not expected_size:
                    # Use more conservative default for manual/unknown offsets
                    if self.sprite_name.startswith("manual_"):
                        expected_size = 4096  # More conservative 4KB for manual exploration
                        logger.debug(f"Using conservative 4KB limit for manual offset {self.sprite_name}")
                    else:
                        expected_size = 8192  # Default 8KB for Kirby sprites
                        logger.warning(
                            f"No expected size found for {self.sprite_name}, using default: {expected_size} bytes. "
                            "This prevents oversized decompression but may need adjustment."
                        )

                if offset_variants:
                    # Use fallback mechanism with expected size
                    compressed_size, tile_data, successful_offset = (
                        self.extractor.rom_injector.find_compressed_sprite_with_fallback(
                            rom_data, self.offset, offset_variants, expected_size
                        )
                    )
                    if successful_offset != self.offset:
                        logger.info(f"Used alternate offset 0x{successful_offset:X} for {self.sprite_name}")
                else:
                    # Use standard method with expected size
                    compressed_size, tile_data = (
                        self.extractor.rom_injector.find_compressed_sprite(
                            rom_data, self.offset, expected_size
                        )
                    )
            except Exception as decomp_error:
                # Provide more specific error based on the type
                if "decompression" in str(decomp_error).lower():
                    raise ValueError(
                        f"Failed to decompress sprite at 0x{self.offset:X}: "
                        f"Invalid compressed data or wrong offset"
                    ) from decomp_error
                raise ValueError(
                    f"Error extracting sprite at 0x{self.offset:X}: {decomp_error}"
                ) from decomp_error

            # Validate extracted data
            if not tile_data:
                raise ValueError(f"No sprite data found at offset 0x{self.offset:X}")

            # Check for data alignment issues
            bytes_per_tile = 32
            extra_bytes = len(tile_data) % bytes_per_tile
            if extra_bytes != 0:
                logger.warning(
                    f"Sprite data size ({len(tile_data)} bytes) is not a multiple of {bytes_per_tile} "
                    f"(tile size). Extra bytes: {extra_bytes}. Data may be corrupted."
                )

                # If significant misalignment, likely wrong offset
                if extra_bytes > bytes_per_tile // 2:
                    raise ValueError(
                        f"Invalid sprite data detected at 0x{self.offset:X}. "
                        f"Data size ({len(tile_data)} bytes) has {extra_bytes} extra bytes, "
                        f"indicating the offset may be incorrect for this ROM version. "
                        f"Please verify the sprite offset or ROM version."
                    )

            # Validate size against expected size if available
            if expected_size:
                size_ratio = len(tile_data) / expected_size
                if size_ratio < 0.5:
                    logger.warning(
                        f"Decompressed size ({len(tile_data)} bytes) is significantly smaller "
                        f"than expected ({expected_size} bytes). Sprite may be incomplete."
                    )
                elif size_ratio > 2.0:
                    logger.warning(
                        f"Decompressed size ({len(tile_data)} bytes) is significantly larger "
                        f"than expected ({expected_size} bytes). May contain extra data."
                    )
                else:
                    logger.debug(
                        f"Decompressed size ({len(tile_data)} bytes) is within acceptable range "
                        f"of expected size ({expected_size} bytes)"
                    )

            # Calculate dimensions (assume standard preview size)
            num_tiles = len(tile_data) // 32  # 32 bytes per tile
            if num_tiles == 0:
                raise ValueError(f"No complete tiles found in sprite data ({len(tile_data)} bytes)")

            tiles_per_row = 16
            tile_rows = (num_tiles + tiles_per_row - 1) // tiles_per_row

            width = min(tiles_per_row * 8, 128)
            height = min(tile_rows * 8, 128)

            self.preview_ready.emit(tile_data, width, height, self.sprite_name)

        except FileNotFoundError as e:
            self.preview_error.emit(f"ROM file not found: {e}")
        except PermissionError as e:
            self.preview_error.emit(f"Cannot access ROM file: {e}")
        except ValueError as e:
            self.preview_error.emit(f"Invalid sprite data: {e}")
        except OSError as e:
            self.preview_error.emit(f"File system error: {e}")
        except Exception as e:
            logger.exception("Unexpected error in sprite preview worker")
            self.preview_error.emit(f"Unexpected error loading sprite preview: {e}")
