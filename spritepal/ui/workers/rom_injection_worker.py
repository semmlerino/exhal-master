"""
Qt worker thread for ROM injection process.
This module contains the Qt-specific worker thread for ROM injection.
"""
from __future__ import annotations

import time
from pathlib import Path

from core.rom_injector import ROMInjector
from core.rom_validator import ROMValidator
from core.sprite_validator import SpriteValidator
from PySide6.QtCore import QThread, Signal
from utils.logging_config import get_logger

logger = get_logger(__name__)


class ROMInjectionWorker(QThread):
    """Worker thread for ROM injection process with detailed progress"""

    progress: Signal = Signal(str)  # Status message
    progress_percent: Signal = Signal(int)  # Progress percentage (0-100)
    compression_info: Signal = Signal(dict)  # Compression statistics
    injection_finished: Signal = Signal(bool, str)  # Success, message

    def __init__(
        self,
        sprite_path: str,
        rom_input: str,
        rom_output: str,
        sprite_offset: int,
        fast_compression: bool = False,
        metadata_path: str | None = None,
    ):
        super().__init__()
        self.sprite_path: str = sprite_path
        self.rom_input: str = rom_input
        self.rom_output: str = rom_output
        self.sprite_offset: int = sprite_offset
        self.fast_compression: bool = fast_compression
        self.metadata_path: str | None = metadata_path
        self.injector: ROMInjector = ROMInjector()

    def run(self) -> None:
        """Run the ROM injection process with detailed progress reporting"""
        logger.info(f"Starting ROM injection worker: sprite={self.sprite_path}, rom={self.rom_input}")
        logger.debug(f"Injection parameters: offset=0x{self.sprite_offset:X}, fast_compression={self.fast_compression}")
        try:
            total_steps = 10
            current_step = 0

            # Step 1: Load metadata if available
            if self.metadata_path:
                self.progress.emit("Loading metadata...")
                self.progress_percent.emit(int((current_step / total_steps) * 100))
                logger.debug(f"Loading metadata from: {self.metadata_path}")
                self.injector.load_metadata(self.metadata_path)
            current_step += 1

            # Step 2: Validate sprite (enhanced validation)
            self.progress.emit("Validating sprite file...")
            self.progress_percent.emit(int((current_step / total_steps) * 100))

            # Basic validation
            valid, message = self.injector.validate_sprite(self.sprite_path)
            if not valid:
                self.injection_finished.emit(False, message)
                return

            # Enhanced validation
            logger.debug("Running comprehensive sprite validation")
            is_valid, errors, warnings = SpriteValidator.validate_sprite_comprehensive(
                self.sprite_path, self.metadata_path
            )
            if not is_valid:
                logger.error(f"Sprite validation failed with {len(errors)} errors")
                for error in errors:
                    logger.error(f"  - {error}")
                error_msg = "Sprite validation failed:\n" + "\n".join(errors)
                self.injection_finished.emit(False, error_msg)
                return
            if warnings:
                logger.warning(f"Sprite validation warnings ({len(warnings)}):")
                for warning in warnings:
                    logger.warning(f"  - {warning}")

            current_step += 1

            # Step 3: Test HAL compression tools
            self.progress.emit("Checking compression tools...")
            self.progress_percent.emit(int((current_step / total_steps) * 100))
            tools_ok, tools_msg = self.injector.hal_compressor.test_tools()
            if not tools_ok:
                self.injection_finished.emit(False, tools_msg)
                return
            current_step += 1

            # Step 4: Validate ROM
            self.progress.emit("Validating ROM file...")
            self.progress_percent.emit(int((current_step / total_steps) * 100))
            try:
                _header_info, header_offset = ROMValidator.validate_rom_for_injection(
                    self.rom_input, self.sprite_offset
                )
            except Exception as e:
                self.injection_finished.emit(False, f"ROM validation failed: {e}")
                return
            current_step += 1

            # Step 5: Read ROM header
            self.progress.emit("Reading ROM header...")
            self.progress_percent.emit(int((current_step / total_steps) * 100))
            header = self.injector.read_rom_header(self.rom_input)
            self.progress.emit(f"ROM: {header.title}")
            current_step += 1

            # Step 6: Compress sprite
            self.progress.emit("Compressing sprite data...")
            self.progress_percent.emit(int((current_step / total_steps) * 100))
            logger.info(f"Compressing sprite with fast_compression={self.fast_compression}")
            start_time = time.time()
            compressed_data = self.injector.compress_sprite(self.sprite_path, self.fast_compression)
            compression_time = time.time() - start_time
            logger.info(f"Compression completed in {compression_time:.2f} seconds")

            # Emit compression statistics
            original_size = Path(self.sprite_path).stat().st_size
            compressed_size = len(compressed_data)
            compression_ratio = original_size / compressed_size if compressed_size > 0 else 0
            compression_stats = {
                "original_size": original_size,
                "compressed_size": compressed_size,
                "compression_ratio": compression_ratio,
                "compression_time": compression_time,
                "fast_mode": self.fast_compression,
            }
            logger.debug(f"Compression stats: {compression_stats}")
            self.compression_info.emit(compression_stats)
            current_step += 1

            # Step 7: Backup ROM
            self.progress.emit("Creating ROM backup...")
            self.progress_percent.emit(int((current_step / total_steps) * 100))
            backup_path = self.injector.backup_rom(self.rom_input)
            self.progress.emit(f"Backup created: {backup_path}")
            current_step += 1

            # Step 8: Inject sprite
            self.progress.emit("Injecting sprite into ROM...")
            self.progress_percent.emit(int((current_step / total_steps) * 100))
            actual_offset = self.sprite_offset
            if header_offset > 0:
                actual_offset += header_offset
                logger.debug(f"Adjusted offset for header: 0x{actual_offset:X}")
            # Fix parameter order: inject_sprite_to_rom(sprite_path, rom_path, output_path, sprite_offset)
            self.injector.inject_sprite_to_rom(
                sprite_path=compressed_data,  # This should be the sprite data path
                rom_path=self.rom_input,
                output_path=self.rom_output or self.rom_input,
                sprite_offset=actual_offset
            )
            current_step += 1

            # Step 9: Update ROM checksum
            self.progress.emit("Updating ROM checksum...")
            self.progress_percent.emit(int((current_step / total_steps) * 100))
            self.injector.update_checksum(self.rom_output or self.rom_input)
            current_step += 1

            # Step 10: Save metadata
            self.progress.emit("Saving metadata...")
            self.progress_percent.emit(int((current_step / total_steps) * 100))
            if self.metadata_path:
                self.injector.save_metadata(self.metadata_path)
            logger.info("ROM injection completed successfully")
            self.injection_finished.emit(True, "Sprite injected successfully!")
            self.progress_percent.emit(100)

        except Exception as e:
            logger.error(f"ROM injection failed: {e}", exc_info=True)
            self.injection_finished.emit(False, f"Injection failed: {e}")
