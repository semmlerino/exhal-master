"""
Manager for handling all extraction operations
"""

import os
import time
from dataclasses import asdict
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from core.extractor import SpriteExtractor
    from core.palette_manager import PaletteManager
    from core.rom_extractor import ROMExtractor

from PIL import Image
from PyQt6.QtCore import QObject, pyqtSignal

from core.extractor import SpriteExtractor
from core.palette_manager import PaletteManager
from core.rom_extractor import ROMExtractor
from utils.constants import (
    BYTES_PER_TILE,
    DEFAULT_PREVIEW_HEIGHT,
    DEFAULT_PREVIEW_WIDTH,
    SPRITE_PALETTE_END,
    SPRITE_PALETTE_START,
)
from utils.file_validator import FileValidator
from utils.rom_cache import get_rom_cache

from .base_manager import BaseManager
from .exceptions import ExtractionError, ValidationError


class ExtractionManager(BaseManager):
    """Manages all extraction workflows (VRAM and ROM)"""

    # Additional signals specific to extraction
    extraction_progress: pyqtSignal = pyqtSignal(str)  # Progress message
    preview_generated: pyqtSignal = pyqtSignal(object, int)  # PIL Image, tile count
    palettes_extracted: pyqtSignal = pyqtSignal(dict)  # Palette data
    active_palettes_found: pyqtSignal = pyqtSignal(list)  # Active palette indices
    files_created: pyqtSignal = pyqtSignal(list)  # List of created files
    cache_operation_started: pyqtSignal = pyqtSignal(str, str)  # Operation type, cache type
    cache_hit: pyqtSignal = pyqtSignal(str, float)  # Cache type, time saved in seconds
    cache_miss: pyqtSignal = pyqtSignal(str)  # Cache type
    cache_saved: pyqtSignal = pyqtSignal(str, int)  # Cache type, number of items saved

    def __init__(self, parent: QObject | None = None) -> None:
        """Initialize the extraction manager"""
        # Declare instance variables with type hints
        self._sprite_extractor: SpriteExtractor
        self._rom_extractor: ROMExtractor
        self._palette_manager: PaletteManager
        
        super().__init__("ExtractionManager", parent)

    def _initialize(self) -> None:
        """Initialize extraction components"""
        self._sprite_extractor = SpriteExtractor()
        self._rom_extractor = ROMExtractor()
        self._palette_manager = PaletteManager()
        self._is_initialized = True
        self._logger.info("ExtractionManager initialized")

    def cleanup(self) -> None:
        """Cleanup extraction resources"""
        # Clear any active operations to prevent "already active" warnings
        with self._lock:
            self._active_operations.clear()
        # Currently no other resources to cleanup

    def extract_from_vram(self, vram_path: str, output_base: str,
                         cgram_path: str | None = None,
                         oam_path: str | None = None,
                         vram_offset: int | None = None,
                         create_grayscale: bool = True,
                         create_metadata: bool = True,
                         grayscale_mode: bool = False) -> list[str]:
        """
        Extract sprites from VRAM dump

        Args:
            vram_path: Path to VRAM dump file
            output_base: Base name for output files (without extension)
            cgram_path: path to CGRAM dump for palette extraction
            oam_path: path to OAM dump for palette analysis
            vram_offset: offset in VRAM (default: 0xC000)
            create_grayscale: Create grayscale palette files
            create_metadata: Create metadata JSON file
            grayscale_mode: Skip palette extraction entirely

        Returns:
            List of created file paths

        Raises:
            ExtractionError: If extraction fails
            ValidationError: If parameters are invalid
        """
        operation = "vram_extraction"

        # Validate parameters
        try:
            self._validate_required({"vram_path": vram_path, "output_base": output_base},
                                   ["vram_path", "output_base"])
            
            # Use FileValidator for comprehensive file validation
            vram_result = FileValidator.validate_vram_file(vram_path)
            if not vram_result.is_valid:
                raise ValidationError(f"VRAM file validation failed: {vram_result.error_message}")
                
            if cgram_path:
                cgram_result = FileValidator.validate_cgram_file(cgram_path)
                if not cgram_result.is_valid:
                    raise ValidationError(f"CGRAM file validation failed: {cgram_result.error_message}")
                    
            if oam_path:
                oam_result = FileValidator.validate_oam_file(oam_path)
                if not oam_result.is_valid:
                    raise ValidationError(f"OAM file validation failed: {oam_result.error_message}")
        except ValidationError as e:
            self._handle_error(e, operation)
            raise

        if not self._start_operation(operation):
            raise ExtractionError("VRAM extraction already in progress")

        try:
            extracted_files = []

            # Extract sprites
            self._update_progress(operation, 0, 100)
            self.extraction_progress.emit("Extracting sprites from VRAM...")

            output_file = f"{output_base}.png"
            img, num_tiles = self._sprite_extractor.extract_sprites_grayscale(
                vram_path, output_file, offset=vram_offset
            )
            extracted_files.append(output_file)

            # Generate preview
            self._update_progress(operation, 25, 100)
            self.extraction_progress.emit("Creating preview...")
            self.preview_generated.emit(img, num_tiles)

            # Extract palettes if requested
            if not grayscale_mode and cgram_path:
                self._update_progress(operation, 50, 100)
                extracted_files.extend(
                    self._extract_palettes(
                        cgram_path, output_base, output_file,
                        oam_path, vram_path, vram_offset,
                        num_tiles, create_grayscale, create_metadata
                    )
                )

            self._update_progress(operation, 100, 100)
            self.extraction_progress.emit("Extraction complete!")
            self.files_created.emit(extracted_files)

        except (OSError, IOError, PermissionError) as e:
            self._handle_file_io_error(e, operation, "VRAM extraction")
        except (ValueError, TypeError) as e:
            self._handle_data_format_error(e, operation, "VRAM extraction")
        except Exception as e:
            self._handle_operation_error(e, operation, ExtractionError, "VRAM extraction")
        else:
            return extracted_files
        finally:
            self._finish_operation(operation)

    def extract_from_rom(self, rom_path: str, offset: int,
                        output_base: str, sprite_name: str,
                        cgram_path: str | None = None) -> list[str]:
        """
        Extract sprites from ROM at specific offset

        Args:
            rom_path: Path to ROM file
            offset: Offset in ROM to extract from
            output_base: Base name for output files
            sprite_name: Name of the sprite being extracted
            cgram_path: CGRAM dump for palette extraction

        Returns:
            List of created file paths

        Raises:
            ExtractionError: If extraction fails
            ValidationError: If parameters are invalid
        """
        operation = "rom_extraction"

        # Validate parameters
        try:
            params = {
                "rom_path": rom_path,
                "offset": offset,
                "output_base": output_base,
                "sprite_name": sprite_name
            }
            self._validate_required(params, list(params.keys()))
            
            # Use FileValidator for comprehensive ROM file validation
            rom_result = FileValidator.validate_rom_file(rom_path)
            if not rom_result.is_valid:
                raise ValidationError(f"ROM file validation failed: {rom_result.error_message}")
                
            self._validate_type(offset, "offset", int)
            self._validate_range(offset, "offset", min_val=0)
            
            if cgram_path:
                cgram_result = FileValidator.validate_cgram_file(cgram_path)
                if not cgram_result.is_valid:
                    raise ValidationError(f"CGRAM file validation failed: {cgram_result.error_message}")
        except ValidationError as e:
            self._handle_error(e, operation)
            raise

        if not self._start_operation(operation):
            raise ExtractionError("ROM extraction already in progress")

        try:
            extracted_files = []

            # Extract from ROM
            self._update_progress(operation, 0, 100)
            self.extraction_progress.emit(f"Extracting {sprite_name} from ROM...")

            output_file = f"{output_base}.png"
            try:
                result = self._rom_extractor.extract_sprite_from_rom(
                    rom_path, offset, output_file
                )

                if result:
                    # Create PIL image for preview
                    img = Image.open(output_file)
                    tile_count = (img.width * img.height) // (8 * 8)

                    extracted_files.append(output_file)
                    self.preview_generated.emit(img, tile_count)

                    # Extract palettes if CGRAM provided
                    if cgram_path:
                        self._update_progress(operation, 50, 100)
                        extracted_files.extend(
                            self._extract_palettes(
                                cgram_path, output_base, output_file,
                                None, rom_path, offset,
                                tile_count, True, True
                            )
                        )
                else:
                    self._raise_extraction_failed("Failed to extract sprite from ROM")

            except (OSError, IOError, PermissionError) as e:
                self._handle_file_io_error(e, operation, "ROM extraction")
            except (ValueError, TypeError) as e:
                self._handle_data_format_error(e, operation, "ROM extraction")
            except Exception as e:
                self._handle_operation_error(e, operation, ExtractionError, "ROM extraction")

            self._update_progress(operation, 100, 100)
            self.extraction_progress.emit("ROM extraction complete!")
            self.files_created.emit(extracted_files)

        except (OSError, IOError, PermissionError) as e:
            self._handle_file_io_error(e, operation, "ROM extraction")
        except (ValueError, TypeError) as e:
            self._handle_data_format_error(e, operation, "ROM extraction")
        except Exception as e:
            if not isinstance(e, ExtractionError):
                self._handle_operation_error(e, operation, ExtractionError, "ROM extraction")
            else:
                self._handle_error(e, operation)
                raise
        else:
            return extracted_files
        finally:
            self._finish_operation(operation)

    def get_sprite_preview(self, rom_path: str, offset: int,
                          sprite_name: str | None = None) -> tuple[bytes, int, int]:
        """
        Get a preview of sprite data from ROM without saving files

        Args:
            rom_path: Path to ROM file
            offset: Offset in ROM
            sprite_name: sprite name for logging

        Returns:
            Tuple of (tile_data, width, height)

        Raises:
            ExtractionError: If preview generation fails
        """
        operation = "sprite_preview"

        try:
            # Use FileValidator for ROM file validation
            rom_result = FileValidator.validate_file_existence(rom_path, "ROM file")
            if not rom_result.is_valid:
                raise ValidationError(f"ROM file validation failed: {rom_result.error_message}")
                
            self._validate_type(offset, "offset", int)
            self._validate_range(offset, "offset", min_val=0)
        except ValidationError as e:
            self._handle_error(e, operation)
            raise

        if not self._start_operation(operation):
            # Allow multiple preview operations
            self._logger.debug("Preview operation already running, allowing concurrent preview")

        try:
            name = sprite_name or f"offset_0x{offset:X}"
            self._logger.debug(f"Generating preview for {name} at offset 0x{offset:X}")

            # Use ROM extractor to get raw tile data
            # This would need to be implemented in ROMExtractor
            # For now, we'll use a simplified approach
            width = DEFAULT_PREVIEW_WIDTH
            height = DEFAULT_PREVIEW_HEIGHT
            tile_count = (width * height) // (8 * 8)

            # Read raw data from ROM
            with open(rom_path, "rb") as f:
                f.seek(offset)
                # 4bpp = 32 bytes per tile
                tile_data = f.read(tile_count * BYTES_PER_TILE)

        except (OSError, IOError, PermissionError) as e:
            self._handle_file_io_error(e, operation, "preview generation")
        except (ValueError, TypeError) as e:
            self._handle_data_format_error(e, operation, "preview generation")
        except Exception as e:
            self._handle_operation_error(e, operation, ExtractionError, "preview generation")
        else:
            return tile_data, width, height
        finally:
            self._finish_operation(operation)

    def validate_extraction_params(self, params: dict[str, Any]) -> bool:
        """
        Validate extraction parameters

        Args:
            params: Parameters to validate

        Returns:
            True if validation passes

        Raises:
            ValidationError: If validation fails
        """
        # Validate input type
        if not isinstance(params, dict):
            raise ValidationError("params must be a dictionary")
        
        # Determine extraction type
        if "vram_path" in params:
            # VRAM extraction - check for missing VRAM file specifically
            if not params.get("vram_path"):
                raise ValidationError("VRAM file is required for extraction")
            self._validate_required(params, ["output_base"])
        elif "rom_path" in params:
            # ROM extraction
            self._validate_required(params, ["rom_path", "offset", "output_base"])
            
            # Use FileValidator for ROM file validation
            rom_result = FileValidator.validate_file_existence(params["rom_path"], "ROM file")
            if not rom_result.is_valid:
                raise ValidationError(f"ROM file validation failed: {rom_result.error_message}")
                
            self._validate_type(params["offset"], "offset", int)
            self._validate_range(params["offset"], "offset", min_val=0)
        else:
            raise ValidationError("Must provide either vram_path or rom_path")

        # Validate CGRAM requirements for VRAM extraction
        if "vram_path" in params:
            grayscale_mode = params.get("grayscale_mode", False)
            cgram_path = params.get("cgram_path")

            # CGRAM is required for full color mode
            if not grayscale_mode and not cgram_path:
                raise ValidationError(
                    "CGRAM file is required for Full Color mode.\n"
                    "Please provide a CGRAM file or switch to Grayscale Only mode."
                )

            # Note: File existence validation is now handled by controller
            # to provide better fail-fast behavior and avoid blocking I/O

        # Validate output_base is provided and not empty
        output_base = params.get("output_base", "")
        if not output_base or not output_base.strip():
            raise ValidationError("Output name is required for extraction")

        # Note: Optional file existence validation is now handled by controller

        # Return True if all validation passes
        return True

    def _extract_palettes(self, cgram_path: str, output_base: str,
                         png_file: str, oam_path: str | None,
                         source_path: str, source_offset: int | None,
                         num_tiles: int, create_grayscale: bool,
                         create_metadata: bool) -> list[str]:
        """
        Extract palettes and create palette/metadata files

        Returns:
            List of created file paths
        """
        created_files = []

        self.extraction_progress.emit("Extracting palettes...")
        self._palette_manager.load_cgram(cgram_path)

        # Get sprite palettes
        sprite_palettes = self._palette_manager.get_sprite_palettes()
        self.palettes_extracted.emit(sprite_palettes)

        # Create palette files
        if create_grayscale:
            self.extraction_progress.emit("Creating palette files...")

            # Create main palette file (default to palette 8)
            main_pal_file = f"{output_base}.pal.json"
            self._palette_manager.create_palette_json(8, main_pal_file, png_file)
            created_files.append(main_pal_file)

            # Create individual palette files
            palette_files = {}
            for pal_idx in range(SPRITE_PALETTE_START, SPRITE_PALETTE_END):
                pal_file = f"{output_base}_pal{pal_idx}.pal.json"
                self._palette_manager.create_palette_json(pal_idx, pal_file, png_file)
                created_files.append(pal_file)
                palette_files[pal_idx] = pal_file

            # Create metadata file
            if create_metadata:
                self.extraction_progress.emit("Creating metadata file...")

                # Prepare extraction parameters
                extraction_params = {
                    "source": os.path.basename(source_path),
                    "offset": source_offset if source_offset is not None else 0xC000,
                    "tile_count": num_tiles,
                    "extraction_size": num_tiles * BYTES_PER_TILE,
                }

                metadata_file = self._palette_manager.create_metadata_json(
                    output_base, palette_files, extraction_params
                )
                created_files.append(metadata_file)

        # Analyze OAM if available
        if oam_path:
            self.extraction_progress.emit("Analyzing sprite palette usage...")
            active_palettes = self._palette_manager.analyze_oam_palettes(oam_path)
            self.active_palettes_found.emit(active_palettes)

        return created_files

    def generate_preview(self, vram_path: str, offset: int) -> tuple[Image.Image, int]:
        """Generate a preview image from VRAM at the specified offset

        Args:
            vram_path: Path to VRAM dump file
            offset: Offset in VRAM to start extracting from

        Returns:
            Tuple of (PIL image, tile count)

        Raises:
            ExtractionError: If preview generation fails
        """
        try:
            # Load VRAM
            self._sprite_extractor.load_vram(vram_path)

            # Extract tiles with new offset
            tiles, num_tiles = self._sprite_extractor.extract_tiles(offset=offset)

            # Create grayscale image
            img = self._sprite_extractor.create_grayscale_image(tiles)

        except (OSError, IOError, PermissionError) as e:
            self._handle_file_io_error(e, "preview_generation", "generating preview")
        except (ValueError, TypeError) as e:
            self._handle_data_format_error(e, "preview_generation", "generating preview")
        except Exception as e:
            self._handle_operation_error(e, "preview_generation", ExtractionError, "generating preview")
        else:
            return img, num_tiles

    def get_rom_extractor(self) -> 'ROMExtractor':
        """
        Get the ROM extractor instance for advanced operations

        Returns:
            ROMExtractor instance

        Note:
            This method provides access to the underlying ROM extractor
            for UI components that need direct access to ROM operations.
            Consider using the manager methods when possible.
        """
        if not self._is_initialized:
            raise ExtractionError("ExtractionManager not initialized")
        return self._rom_extractor

    def get_known_sprite_locations(self, rom_path: str) -> dict[str, Any]:
        """
        Get known sprite locations for a ROM with caching

        Args:
            rom_path: Path to ROM file

        Returns:
            Dictionary of known sprite locations

        Raises:
            ExtractionError: If operation fails
        """
        try:
            # Use FileValidator for ROM file validation
            rom_result = FileValidator.validate_file_existence(rom_path, "ROM file")
            if not rom_result.is_valid:
                raise ValidationError(f"ROM file validation failed: {rom_result.error_message}")

            # Try to load from cache first
            start_time = time.time()
            rom_cache = get_rom_cache()

            # Signal that cache loading operation is starting
            self.cache_operation_started.emit("Loading", "sprite_locations")
            cached_locations = rom_cache.get_sprite_locations(rom_path)

            if cached_locations:
                time_saved = 2.5  # Estimated time saved by not scanning ROM
                self._logger.debug(f"Loaded sprite locations from cache: {rom_path}")
                self.cache_hit.emit("sprite_locations", time_saved)
                # Convert cached dict back to SpritePointer-like objects if needed
                # For now, return the cached dict directly since the callers expect a dict
                return cached_locations

            # Cache miss - scan ROM file
            self._logger.debug(f"Cache miss, scanning ROM for sprite locations: {rom_path}")
            self.cache_miss.emit("sprite_locations")
            locations = self._rom_extractor.get_known_sprite_locations(rom_path)
            scan_time = time.time() - start_time

            # Save to cache for future use
            if locations:
                # Signal that cache saving operation is starting
                self.cache_operation_started.emit("Saving", "sprite_locations")
                cache_success = rom_cache.save_sprite_locations(rom_path, locations)
                if cache_success:
                    self._logger.debug(f"Cached {len(locations)} sprite locations for future use (scan took {scan_time:.1f}s)")
                    self.cache_saved.emit("sprite_locations", len(locations))

        except (OSError, IOError, PermissionError) as e:
            self._handle_file_io_error(e, "get_known_sprite_locations", "getting sprite locations")
        except (ImportError, AttributeError) as e:
            self._handle_operation_error(e, "get_known_sprite_locations", ExtractionError, "ROM analysis not available")
        except Exception as e:
            self._handle_operation_error(e, "get_known_sprite_locations", ExtractionError, "getting sprite locations")
        else:
            return locations

    def read_rom_header(self, rom_path: str) -> dict[str, Any]:
        """
        Read ROM header information

        Args:
            rom_path: Path to ROM file

        Returns:
            Dictionary containing ROM header information

        Raises:
            ExtractionError: If operation fails
        """
        try:
            # Use FileValidator for ROM file validation
            rom_result = FileValidator.validate_file_existence(rom_path, "ROM file")
            if not rom_result.is_valid:
                raise ValidationError(f"ROM file validation failed: {rom_result.error_message}")
                
            header = self._rom_extractor.rom_injector.read_rom_header(rom_path)
            return asdict(header)
        except (OSError, IOError, PermissionError) as e:
            self._handle_file_io_error(e, "read_rom_header", "reading ROM header")
        except (ValueError, TypeError) as e:
            self._handle_data_format_error(e, "read_rom_header", "reading ROM header")
        except Exception as e:
            self._handle_operation_error(e, "read_rom_header", ExtractionError, "reading ROM header")

    def _raise_extraction_failed(self, message: str) -> None:
        """Helper method to raise ExtractionError (for TRY301 compliance)"""
        raise ExtractionError(message)
