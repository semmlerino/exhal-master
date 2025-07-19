"""
ROM injection functionality for SpritePal.
Handles injection of edited sprites directly into ROM files.
"""

import os
import struct
import tempfile
from dataclasses import dataclass
from typing import Optional

from PyQt6.QtCore import QThread, pyqtSignal

from spritepal.core.hal_compression import HALCompressionError, HALCompressor
from spritepal.core.injector import SpriteInjector
from spritepal.core.rom_validator import ROMValidator
from spritepal.core.sprite_config_loader import SpriteConfigLoader
from spritepal.core.sprite_validator import SpriteValidator
from spritepal.utils.rom_backup import ROMBackupManager
from spritepal.utils.rom_exceptions import (
    ROMInjectionError,
    ROMCompressionError,
    ROMOffsetError
)
from spritepal.utils.logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class ROMHeader:
    """SNES ROM header information"""
    title: str
    rom_type: int
    rom_size: int
    sram_size: int
    checksum: int
    checksum_complement: int
    header_offset: int


@dataclass
class SpritePointer:
    """Sprite data pointer in ROM"""
    offset: int
    bank: int
    address: int
    compressed_size: Optional[int] = None


class ROMInjector(SpriteInjector):
    """Handles sprite injection directly into ROM files"""

    def __init__(self):
        super().__init__()
        self.hal_compressor = HALCompressor()
        self.rom_data: Optional[bytearray] = None
        self.header: Optional[ROMHeader] = None
        self.sprite_config_loader = SpriteConfigLoader()

    def read_rom_header(self, rom_path: str) -> ROMHeader:
        """Read and parse SNES ROM header"""
        with open(rom_path, "rb") as f:
            # Try to detect header offset (SMC header is 512 bytes)
            f.seek(0)
            f.read(512)

            # Check for SMC header
            header_offset = 0
            rom_size = os.path.getsize(rom_path)
            if rom_size % 1024 == 512:
                header_offset = 512

            # Read header at expected location
            # SNES header is typically at 0x7FC0 or 0xFFC0 depending on ROM type
            for offset in [0x7FC0, 0xFFC0]:
                f.seek(header_offset + offset)
                header_data = f.read(32)

                # Parse header
                title = header_data[0:21].decode("ascii", errors="ignore").strip()
                rom_type = header_data[21]
                rom_size = header_data[23]
                sram_size = header_data[24]
                checksum_complement = struct.unpack("<H", header_data[28:30])[0]
                checksum = struct.unpack("<H", header_data[30:32])[0]

                # Verify checksum to ensure valid header
                if (checksum ^ checksum_complement) == 0xFFFF:
                    self.header = ROMHeader(
                        title=title,
                        rom_type=rom_type,
                        rom_size=rom_size,
                        sram_size=sram_size,
                        checksum=checksum,
                        checksum_complement=checksum_complement,
                        header_offset=header_offset
                    )
                    return self.header

        raise ValueError("Could not find valid SNES ROM header")

    def calculate_checksum(self, rom_data: bytes) -> tuple[int, int]:
        """Calculate SNES ROM checksum and complement"""
        # Skip SMC header if present
        offset = self.header.header_offset if self.header else 0
        data = rom_data[offset:]

        # Calculate checksum
        checksum = 0
        for i in range(0, len(data), 2):
            word = data[i + 1] << 8 | data[i] if i + 1 < len(data) else data[i]
            checksum = (checksum + word) & 0xFFFF

        # Calculate complement
        complement = checksum ^ 0xFFFF

        return checksum, complement

    def update_rom_checksum(self, rom_data: bytearray) -> None:
        """Update ROM checksum after modification"""
        if not self.header:
            raise ValueError("ROM header not loaded")

        # Calculate new checksum
        checksum, complement = self.calculate_checksum(rom_data)

        # Find header location
        header_base = self.header.header_offset + (0x7FC0 if len(rom_data) <= 0x8000 else 0xFFC0)

        # Update checksum in ROM
        struct.pack_into("<H", rom_data, header_base + 28, complement)
        struct.pack_into("<H", rom_data, header_base + 30, checksum)

        # Update header
        self.header.checksum = checksum
        self.header.checksum_complement = complement

    def find_compressed_sprite(self, rom_data: bytes, offset: int) -> tuple[int, bytes]:
        """
        Find and decompress sprite data at given offset.

        Returns:
            Tuple of (compressed_size, decompressed_data)
        """
        # Create temp file for decompression
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp.write(rom_data)
            tmp_rom = tmp.name

        try:
            # Decompress sprite data
            decompressed = self.hal_compressor.decompress_from_rom(tmp_rom, offset)

            # Estimate compressed size by searching for next compressed data
            # This is a heuristic - in practice we'd need better tracking
            compressed_size = self._estimate_compressed_size(rom_data, offset)

            return compressed_size, decompressed

        finally:
            os.unlink(tmp_rom)

    def _estimate_compressed_size(self, rom_data: bytes, offset: int) -> int:
        """Estimate size of compressed data (heuristic)"""
        # This is a simplified approach - real implementation would need
        # to parse the compression format or use known sizes
        # For now, scan for typical compression end patterns
        max_size = min(0x10000, len(rom_data) - offset)  # Max 64KB

        # Look for common patterns that indicate end of compressed data
        for i in range(32, max_size, 2):
            # Check for alignment padding (series of 0xFF or 0x00)
            if rom_data[offset + i:offset + i + 16] == b"\xFF" * 16:
                return i
            if rom_data[offset + i:offset + i + 16] == b"\x00" * 16:
                return i

        # Default estimate
        return 0x1000  # 4KB default

    def inject_sprite_to_rom(
        self,
        sprite_path: str,
        rom_path: str,
        output_path: str,
        sprite_offset: int,
        fast_compression: bool = False,
        create_backup: bool = True
    ) -> tuple[bool, str]:
        """
        Inject sprite directly into ROM file with validation and backup.

        Args:
            sprite_path: Path to edited sprite PNG
            rom_path: Path to input ROM
            output_path: Path for output ROM
            sprite_offset: Offset in ROM where sprite data is located
            fast_compression: Use fast compression mode
            create_backup: Create backup before modification

        Returns:
            Tuple of (success, message)
        """
        try:
            logger.info(f"Starting ROM injection: {os.path.basename(sprite_path)} -> offset 0x{sprite_offset:X}")
            
            # Validate ROM before modification
            header_info, header_offset = ROMValidator.validate_rom_for_injection(rom_path, sprite_offset)
            
            # Create backup if requested
            backup_path = None
            if create_backup:
                try:
                    backup_path = ROMBackupManager.create_backup(rom_path)
                    logger.info(f"Created backup: {backup_path}")
                except Exception as e:
                    logger.warning(f"Failed to create backup: {e}")
                    # Continue without backup but warn user
            
            # Read ROM header (using improved method)
            self.header = self.read_rom_header(rom_path)

            # Load ROM data
            with open(rom_path, "rb") as f:
                self.rom_data = bytearray(f.read())

            # Convert PNG to 4bpp
            tile_data = self.convert_png_to_4bpp(sprite_path)

            # Find and decompress original sprite for size comparison
            original_size, original_data = self.find_compressed_sprite(self.rom_data, sprite_offset)

            # Compress new sprite data
            with tempfile.NamedTemporaryFile(delete=False, suffix=".bin") as tmp:
                compressed_path = tmp.name

            compressed_size = self.hal_compressor.compress_to_file(
                tile_data, compressed_path, fast=fast_compression
            )
            
            # Calculate compression statistics
            uncompressed_size = len(tile_data)
            compression_ratio = (uncompressed_size - compressed_size) / uncompressed_size * 100
            space_saved = original_size - compressed_size
            compression_mode = "fast" if fast_compression else "standard"
            
            logger.info(f"Compression statistics ({compression_mode} mode):")
            logger.info(f"  - Uncompressed size: {uncompressed_size} bytes")
            logger.info(f"  - Compressed size: {compressed_size} bytes")
            logger.info(f"  - Compression ratio: {compression_ratio:.1f}%")
            logger.info(f"  - Space saved vs original: {space_saved} bytes")

            # Check if compressed data fits
            if compressed_size > original_size:
                os.unlink(compressed_path)
                suggestion = "standard compression" if fast_compression else "a smaller sprite or split it into parts"
                return False, (f"Compressed sprite too large: {compressed_size} bytes "
                             f"(original: {original_size} bytes).\n"
                             f"Compression ratio: {compression_ratio:.1f}%\n"
                             f"Try using {suggestion}.")

            # Read compressed data
            with open(compressed_path, "rb") as f:
                compressed_data = f.read()
            os.unlink(compressed_path)

            # Inject compressed data into ROM
            self.rom_data[sprite_offset:sprite_offset + compressed_size] = compressed_data

            # Pad remaining space if needed
            if compressed_size < original_size:
                padding = b"\xFF" * (original_size - compressed_size)
                self.rom_data[sprite_offset + compressed_size:sprite_offset + original_size] = padding
                logger.info(f"Padded {original_size - compressed_size} bytes with 0xFF")

            # Update checksum
            self.update_rom_checksum(self.rom_data)

            # Write output ROM
            with open(output_path, "wb") as f:
                f.write(self.rom_data)

            return True, (f"Successfully injected sprite at 0x{sprite_offset:X}\n"
                        f"Original size: {original_size} bytes\n"
                        f"New size: {compressed_size} bytes ({compression_ratio:.1f}% compression)\n"
                        f"Space saved: {space_saved} bytes\n"
                        f"Compression mode: {compression_mode}\n"
                        f"Checksum updated: 0x{self.header.checksum:04X}")

        except HALCompressionError as e:
            return False, f"Compression error: {e!s}"
        except Exception as e:
            return False, f"ROM injection error: {e!s}"

    def find_sprite_locations(self, rom_path: str) -> dict[str, SpritePointer]:
        """
        Find sprite locations for the given ROM using configuration data.
        """
        pointers = {}
        
        # Read ROM header to get title and checksum
        try:
            header = self.read_rom_header(rom_path)
            
            # Get sprite configurations for this ROM
            sprite_configs = self.sprite_config_loader.get_game_sprites(
                header.title, header.checksum
            )
            
            # Convert configs to SpritePointer objects
            for name, config in sprite_configs.items():
                bank = (config.offset >> 16) & 0xFF
                address = config.offset & 0xFFFF
                pointers[name] = SpritePointer(
                    offset=config.offset,
                    bank=bank,
                    address=address,
                    compressed_size=config.estimated_size
                )
            
            if not pointers:
                logger.warning(f"No sprite locations found for ROM: {header.title}")
            
        except Exception as e:
            logger.error(f"Failed to find sprite locations: {e}")
        
        return pointers


class ROMInjectionWorker(QThread):
    """Worker thread for ROM injection process with detailed progress"""

    progress = pyqtSignal(str)  # Status message
    progress_percent = pyqtSignal(int)  # Progress percentage (0-100)
    compression_info = pyqtSignal(dict)  # Compression statistics
    finished = pyqtSignal(bool, str)  # Success, message

    def __init__(
        self,
        sprite_path: str,
        rom_input: str,
        rom_output: str,
        sprite_offset: int,
        fast_compression: bool = False,
        metadata_path: Optional[str] = None
    ):
        super().__init__()
        self.sprite_path = sprite_path
        self.rom_input = rom_input
        self.rom_output = rom_output
        self.sprite_offset = sprite_offset
        self.fast_compression = fast_compression
        self.metadata_path = metadata_path
        self.injector = ROMInjector()

    def run(self):
        """Run the ROM injection process with detailed progress reporting"""
        try:
            total_steps = 10
            current_step = 0
            
            # Step 1: Load metadata if available
            if self.metadata_path:
                self.progress.emit("Loading metadata...")
                self.progress_percent.emit(int((current_step / total_steps) * 100))
                self.injector.load_metadata(self.metadata_path)
            current_step += 1

            # Step 2: Validate sprite (enhanced validation)
            self.progress.emit("Validating sprite file...")
            self.progress_percent.emit(int((current_step / total_steps) * 100))
            
            # Basic validation
            valid, message = self.injector.validate_sprite(self.sprite_path)
            if not valid:
                self.finished.emit(False, message)
                return
                
            # Enhanced validation
            is_valid, errors, warnings = SpriteValidator.validate_sprite_comprehensive(
                self.sprite_path, self.metadata_path
            )
            if not is_valid:
                error_msg = "Sprite validation failed:\n" + "\n".join(errors)
                self.finished.emit(False, error_msg)
                return
                
            current_step += 1

            # Step 3: Test HAL compression tools
            self.progress.emit("Checking compression tools...")
            self.progress_percent.emit(int((current_step / total_steps) * 100))
            tools_ok, tools_msg = self.injector.hal_compressor.test_tools()
            if not tools_ok:
                self.finished.emit(False, tools_msg)
                return
            current_step += 1

            # Step 4: Validate ROM
            self.progress.emit("Validating ROM file...")
            self.progress_percent.emit(int((current_step / total_steps) * 100))
            try:
                header_info, header_offset = ROMValidator.validate_rom_for_injection(
                    self.rom_input, self.sprite_offset
                )
            except Exception as e:
                self.finished.emit(False, f"ROM validation failed: {e}")
                return
            current_step += 1

            # Step 5: Read ROM header
            self.progress.emit("Reading ROM header...")
            self.progress_percent.emit(int((current_step / total_steps) * 100))
            header = self.injector.read_rom_header(self.rom_input)
            self.progress.emit(f"ROM: {header.title}")
            current_step += 1

            # Step 6: Create backup
            self.progress.emit("Creating backup...")
            self.progress_percent.emit(int((current_step / total_steps) * 100))
            backup_path = ROMBackupManager.create_backup(self.rom_input)
            current_step += 1

            # Step 7-10: Perform injection with sub-progress
            injection_steps = [
                "Converting sprite to 4bpp format...",
                "Analyzing original sprite data...",
                "Compressing sprite data...",
                f"Injecting into ROM at offset 0x{self.sprite_offset:X}..."
            ]
            
            # Create a custom injection method that reports progress
            for i, step_msg in enumerate(injection_steps):
                self.progress.emit(step_msg)
                progress = int(((current_step + i * 0.25) / total_steps) * 100)
                self.progress_percent.emit(progress)

            # Perform actual injection
            success, message = self.injector.inject_sprite_to_rom(
                self.sprite_path,
                self.rom_input,
                self.rom_output,
                self.sprite_offset,
                self.fast_compression,
                create_backup=False  # Already created backup
            )

            if success:
                self.progress.emit("Updating ROM checksum...")
                self.progress.emit("ROM injection complete!")
                self.progress_percent.emit(100)
                
                # Extract compression info from message
                compression_info = self._extract_compression_info(message)
                if compression_info:
                    self.compression_info.emit(compression_info)

            self.finished.emit(success, message)

        except Exception as e:
            self.finished.emit(False, f"Unexpected error: {e!s}")
    
    def _extract_compression_info(self, message: str) -> Optional[dict]:
        """Extract compression statistics from success message"""
        try:
            info = {}
            lines = message.split('\n')
            
            for line in lines:
                if "Original size:" in line:
                    info["original_size"] = int(line.split(":")[1].strip().split()[0])
                elif "New size:" in line:
                    # Extract size and compression ratio
                    parts = line.split(":")
                    size_part = parts[1].strip().split()
                    info["new_size"] = int(size_part[0])
                    # Look for compression ratio in parentheses
                    if "(" in line and "%" in line:
                        ratio_str = line[line.find("(")+1:line.find("%")]
                        info["compression_ratio"] = float(ratio_str)
                elif "Space saved:" in line:
                    info["space_saved"] = int(line.split(":")[1].strip().split()[0])
                elif "Compression mode:" in line:
                    info["compression_mode"] = line.split(":")[1].strip()
            
            return info if info else None
            
        except Exception as e:
            logger.warning(f"Failed to extract compression info: {e}")
            return None
