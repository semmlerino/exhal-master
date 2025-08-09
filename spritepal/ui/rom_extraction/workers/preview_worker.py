"""Worker thread for loading sprite previews"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from PyQt6.QtCore import QObject

from PyQt6.QtCore import pyqtSignal

from core.workers.base import BaseWorker, handle_worker_errors
from utils.logging_config import get_logger

logger = get_logger(__name__)


class SpritePreviewWorker(BaseWorker):
    """Worker thread for loading sprite previews"""

    # Custom signals (BaseWorker provides progress, error, warning, operation_finished)
    preview_ready = pyqtSignal(
        bytes, int, int, str
    )  # tile_data, width, height, sprite_name
    preview_error = pyqtSignal(str)  # error message

    def __init__(self, rom_path: str, offset: int, sprite_name: str, extractor, sprite_config=None, parent: QObject | None = None):
        super().__init__(parent)
        self.rom_path = rom_path
        self.offset = offset
        self.sprite_name = sprite_name
        self.extractor = extractor
        self.sprite_config = sprite_config
        self._operation_name = f"SpritePreviewWorker-{sprite_name}"  # For logging

    @handle_worker_errors("sprite preview loading", handle_interruption=True)
    def run(self):
        """Load sprite preview in background"""

        def _validate_rom_path(rom_path: str) -> None:
            """Validate ROM file path exists"""
            if not rom_path or not os.path.exists(rom_path):
                raise FileNotFoundError(f"ROM file not found: {rom_path}")

        def _validate_offset(offset: int) -> None:
            """Validate offset is not negative"""
            if offset < 0:
                raise ValueError(f"Invalid offset: 0x{offset:X} (negative)")

        def _validate_rom_file_access(rom_path: str, e: Exception) -> None:
            """Validate ROM file access and re-raise with context"""
            if isinstance(e, PermissionError):
                raise PermissionError(f"Cannot read ROM file: {rom_path}") from e
            if isinstance(e, OSError):
                raise OSError(f"Error reading ROM file: {e}") from e

        def _validate_rom_size(rom_size: int) -> None:
            """Validate ROM file size"""
            if rom_size < 0x8000:  # Minimum reasonable SNES ROM size
                raise ValueError(f"ROM file too small: {rom_size} bytes")

        def _validate_offset_bounds(offset: int, rom_size: int) -> None:
            """Validate offset is within ROM bounds"""
            if offset >= rom_size:
                raise ValueError(
                    f"Offset 0x{offset:X} is beyond ROM size (0x{rom_size:X})"
                )

        def _validate_sprite_data(tile_data: bytes, offset: int) -> None:
            """Validate extracted sprite data"""
            if not tile_data:
                raise ValueError(f"No sprite data found at offset 0x{offset:X}")

        def _validate_sprite_integrity(tile_data: bytes, offset: int, bytes_per_tile: int) -> None:
            """Validate sprite data integrity"""
            extra_bytes = len(tile_data) % bytes_per_tile
            if extra_bytes > bytes_per_tile // 2:
                raise ValueError(
                    f"Invalid sprite data detected at 0x{offset:X}. "
                    f"Expected multiple of {bytes_per_tile} bytes, got {len(tile_data)} bytes."
                )

        def _validate_tile_count(num_tiles: int, tile_data_length: int) -> None:
            """Validate that we have complete tiles"""
            if num_tiles == 0:
                raise ValueError(f"No complete tiles found in sprite data ({tile_data_length} bytes)")

        def _handle_decompression_error(error: Exception, offset: int) -> None:
            """Handle decompression errors with appropriate messages"""
            if "decompression" in str(error).lower():
                raise ValueError(
                    f"Failed to decompress sprite at 0x{offset:X}: "
                    f"Invalid compressed data format"
                ) from error
            raise ValueError(
                f"Error extracting sprite at 0x{offset:X}: {error}"
            ) from error

        try:
            # Validate inputs
            _validate_rom_path(self.rom_path)
            _validate_offset(self.offset)

            # Initialize variables to prevent unbound errors
            rom_data: bytes = b""
            tile_data: bytes = b""

            # Read ROM data with file size validation
            try:
                with open(self.rom_path, "rb") as f:
                    rom_data = f.read()
            except (PermissionError, OSError) as e:
                _validate_rom_file_access(self.rom_path, e)

            # Validate ROM size
            rom_size = len(rom_data)
            _validate_rom_size(rom_size)

            # Validate offset is within ROM bounds
            _validate_offset_bounds(self.offset, rom_size)

            # Find and decompress sprite with better error handling
            try:
                # Variables already initialized above
                compressed_size = 0

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
                _handle_decompression_error(decomp_error, self.offset)

            # Validate extracted data
            _validate_sprite_data(tile_data, self.offset)

            # Check for data alignment issues
            bytes_per_tile = 32
            extra_bytes = len(tile_data) % bytes_per_tile
            if extra_bytes != 0:
                logger.warning(
                    f"Sprite data size ({len(tile_data)} bytes) is not a multiple of {bytes_per_tile} "
                    f"(tile size). Extra bytes: {extra_bytes}. Data may be corrupted."
                )

                # If significant misalignment, likely wrong offset
                _validate_sprite_integrity(tile_data, self.offset, bytes_per_tile)

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
            _validate_tile_count(num_tiles, len(tile_data))

            tiles_per_row = 16
            tile_rows = (num_tiles + tiles_per_row - 1) // tiles_per_row

            width = min(tiles_per_row * 8, 128)
            height = min(tile_rows * 8, 128)

            self.preview_ready.emit(tile_data, width, height, self.sprite_name)
            self.operation_finished.emit(True, f"Preview loaded for {self.sprite_name}")

        except Exception as e:
            error_msg = f"Failed to load preview for {self.sprite_name}: {e}"
            logger.error(error_msg, exc_info=True)
            self.preview_error.emit(error_msg)
            self.operation_finished.emit(False, error_msg)

    # emit_error is inherited from BaseWorker
