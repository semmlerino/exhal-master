"""
Worker threads for async file operations in the pixel editor.

This module provides thread-based workers for handling file I/O operations
asynchronously, preventing UI freezing during long operations.
"""

# Standard library imports
import json
import traceback
from pathlib import Path
from typing import Optional, Union

# Third-party imports
import numpy as np
from PIL import Image
from PyQt6.QtCore import QObject, QThread, pyqtSignal

from .pixel_editor_utils import debug_log, sanitize_for_json


class BaseWorker(QThread):
    """Base worker class for async operations.

    Signals:
        progress: Emitted with progress percentage (0-100)
        error: Emitted with error message when operation fails
        finished: Emitted when operation completes successfully
    """

    progress = pyqtSignal(int, str)  # Progress percentage 0-100, optional message
    error = pyqtSignal(str)  # Error message
    finished = pyqtSignal()  # Operation completed

    def __init__(
        self,
        file_path: Optional[Union[str, Path]] = None,
        parent: Optional[QObject] = None,
    ):
        """Initialize the base worker.

        Args:
            file_path: Optional file path (string or Path object)
            parent: Parent QObject for proper cleanup
        """
        super().__init__(parent)
        self._is_cancelled = False
        self._file_path: Optional[Path] = None

        # Convert file_path to Path object if provided
        if file_path is not None:
            self._file_path = (
                Path(file_path) if not isinstance(file_path, Path) else file_path
            )

    def cancel(self) -> None:
        """Cancel the operation."""
        self._is_cancelled = True

    def is_cancelled(self) -> bool:
        """Check if operation was cancelled.

        Returns:
            True if operation was cancelled
        """
        return self._is_cancelled

    @property
    def file_path(self) -> Optional[Path]:
        """Get the file path as a Path object (read-only).

        Returns:
            Path object or None if no file path was provided
        """
        return self._file_path

    def validate_file_path(self, must_exist: bool = True) -> bool:
        """Validate the file path.

        Args:
            must_exist: If True, check that the file exists

        Returns:
            True if valid, False otherwise
        """
        if self._file_path is None:
            self.emit_error("No file path provided")
            return False

        if must_exist and not self._file_path.exists():
            self.emit_error(f"File not found: {self._file_path}")
            return False

        return True

    def emit_progress(self, value: int, message: str = "") -> None:
        """Emit progress signal if not cancelled.

        Args:
            value: Progress percentage (0-100)
            message: Optional progress message
        """
        if not self._is_cancelled:
            self.progress.emit(value, message)

    def emit_error(self, message: str) -> None:
        """Emit error signal with formatted message.

        Args:
            message: Error message to emit
        """
        if not self._is_cancelled:
            self.error.emit(message)

    def emit_finished(self) -> None:
        """Emit finished signal if not cancelled."""
        if not self._is_cancelled:
            self.finished.emit()


class FileLoadWorker(BaseWorker):
    """Worker for loading image files asynchronously.

    Signals:
        result: Emitted with loaded image data and metadata
    """

    result = pyqtSignal(object, dict)  # Image array, metadata

    def __init__(self, file_path: Union[str, Path], parent: Optional[QObject] = None):
        """Initialize the file load worker.

        Args:
            file_path: Path to the image file to load (string or Path object)
            parent: Parent QObject for proper cleanup
        """
        super().__init__(file_path, parent)

    def _open_image(self) -> Optional[Image.Image]:
        """Open the image file with PIL.

        Returns:
            PIL Image object or None if opening failed
        """
        try:
            debug_log("WORKER", "Opening image with PIL...", "DEBUG")
            image = Image.open(str(self.file_path))
            debug_log(
                "WORKER",
                f"Image opened: size={image.size}, mode={image.mode}, format={image.format}",
                "DEBUG",
            )
            return image
        except Exception as e:
            debug_log(
                "WORKER", f"Failed to open image: {type(e).__name__}: {e}", "ERROR"
            )
            self.emit_error(f"Failed to open image: {e!s}")
            return None

    def _convert_to_indexed(self, image: Image.Image) -> Optional[Image.Image]:
        """Convert image to indexed color if necessary.

        Args:
            image: PIL Image to convert

        Returns:
            Indexed PIL Image or None if conversion failed
        """
        if image.mode == "P":
            # Check if already indexed image has more than 16 colors
            palette = image.getpalette()
            if palette:
                # Count unique colors in the image
                unique_colors = len(set(image.getdata()))
                if unique_colors > 16:
                    debug_log(
                        "WORKER",
                        f"Warning: Image has {unique_colors} colors, will be reduced to 16 for SNES compatibility",
                        "WARNING"
                    )
                    self.emit_progress(
                        30,
                        f"Reducing {unique_colors} colors to 16 for SNES compatibility..."
                    )
                    # Convert to RGB then back to P with 16 colors
                    try:
                        return image.convert("RGB").convert("P", palette=Image.ADAPTIVE, colors=16)
                    except Exception as e:
                        self.emit_error(f"Failed to reduce colors: {e!s}")
                        return None
            return image

        try:
            # For non-indexed images, check color count before conversion
            if image.mode in {"RGB", "RGBA"}:
                # Get unique colors
                unique_colors = len(set(image.convert("RGB").getdata()))
                if unique_colors > 16:
                    debug_log(
                        "WORKER",
                        f"Warning: Image has {unique_colors} colors, will be reduced to 16 for SNES compatibility",
                        "WARNING"
                    )
                    self.emit_progress(
                        30,
                        f"Reducing {unique_colors} colors to 16 for SNES compatibility..."
                    )

            # Convert to indexed color with 16 colors (SNES sprite limit)
            return image.convert("P", palette=Image.ADAPTIVE, colors=16)
        except Exception as e:
            self.emit_error(f"Failed to convert image to indexed color: {e!s}")
            return None

    def _extract_image_data(self, image: Image.Image) -> np.ndarray:
        """Extract image data as numpy array.

        Args:
            image: PIL Image to extract data from

        Returns:
            Numpy array of image data
        """
        return np.array(image, dtype=np.uint8)

    def _extract_palette_data(self, image: Image.Image) -> Optional[list[int]]:
        """Extract palette data from image.

        Args:
            image: PIL Image to extract palette from

        Returns:
            List of palette RGB values or None if no palette
        """
        palette_data = image.getpalette()
        if palette_data is None:
            self.emit_error("Image has no palette data")
            return None
        return palette_data

    def _build_metadata(self, image: Image.Image, palette_data: list[int]) -> dict:
        """Build metadata dictionary from image.

        Args:
            image: PIL Image to extract metadata from
            palette_data: Palette data for the image

        Returns:
            Dictionary containing image metadata
        """
        debug_log("WORKER", "Preparing metadata...", "DEBUG")
        metadata = {
            "width": image.width,
            "height": image.height,
            "mode": image.mode,
            "format": (
                image.format
                if isinstance(image.format, str)
                else str(image.format) if image.format else None
            ),
            "palette": palette_data,
            "file_path": str(self.file_path) if self.file_path else "",
            "file_name": str(self.file_path.name) if self.file_path else "unknown",
        }
        debug_log(
            "WORKER",
            f"Basic metadata prepared: {image.width}x{image.height}, mode={image.mode}",
            "DEBUG",
        )
        return metadata

    def _process_image_info(self, image: Image.Image, metadata: dict) -> dict:
        """Process image.info dictionary and add to metadata.

        Args:
            image: PIL Image to extract info from
            metadata: Metadata dictionary to update

        Returns:
            Updated metadata dictionary
        """
        if hasattr(image, "info"):
            debug_log(
                "WORKER",
                f"Image has info dict with {len(image.info)} keys",
                "DEBUG",
            )
            debug_log(
                "WORKER", f"Info keys: {list(image.info.keys())[:10]}", "DEBUG"
            )  # First 10 keys
            # Check for problematic types in info
            for key, value in image.info.items():
                if not isinstance(
                    value, (str, int, float, bool, type(None), list, dict)
                ):
                    debug_log(
                        "WORKER",
                        f"Info key '{key}' has type {type(value).__name__}",
                        "WARNING",
                    )

            metadata["info"] = sanitize_for_json(image.info)
            debug_log("WORKER", "Image info sanitized", "DEBUG")

        # Sanitize the entire metadata dictionary
        metadata = sanitize_for_json(metadata)
        debug_log("WORKER", "Metadata fully sanitized", "DEBUG")
        return metadata

    def run(self) -> None:
        """Load the image file in background thread."""
        try:
            debug_log("WORKER", f"Starting to load file: {self.file_path}", "DEBUG")
            debug_log(
                "WORKER", f"File path type: {type(self.file_path).__name__}", "DEBUG"
            )

            # Validate file path
            if not self.validate_file_path(must_exist=True):
                return

            self.emit_progress(0, f"Loading {self.file_path.name if self.file_path else 'file'}...")
            if self.is_cancelled():
                return

            # Open image
            self.emit_progress(20, "Opening image file...")
            image = self._open_image()
            if image is None:
                return
            if self.is_cancelled():
                return

            # Convert to indexed color if necessary
            self.emit_progress(40, "Processing image format...")
            image = self._convert_to_indexed(image)
            if image is None:
                return
            if self.is_cancelled():
                return

            # Extract image data
            self.emit_progress(60, "Extracting image data...")
            image_array = self._extract_image_data(image)

            # Extract palette
            palette_data = self._extract_palette_data(image)
            if palette_data is None:
                return
            if self.is_cancelled():
                return

            # Prepare metadata
            self.emit_progress(80, "Preparing metadata...")
            metadata = self._build_metadata(image, palette_data)
            metadata = self._process_image_info(image, metadata)

            if self.is_cancelled():
                return

            self.emit_progress(100, "Loading complete!")

            # Emit results
            debug_log(
                "WORKER",
                f"Emitting results: array shape={image_array.shape}, metadata keys={list(metadata.keys())}",
                "DEBUG",
            )
            self.result.emit(image_array, metadata)
            self.emit_finished()
            debug_log("WORKER", "File load completed successfully", "INFO")

        except Exception as e:
            # Sanitize the exception message in case it contains Path objects
            debug_log("WORKER", f"Exception in file load: {type(e).__name__}", "ERROR")
            error_msg = str(e)
            try:
                # Try to extract just the message without object representations
                if hasattr(e, "args") and e.args:
                    error_msg = str(e.args[0]) if e.args else str(e)
                debug_log("WORKER", f"Exception args: {e.args}", "DEBUG")
            except Exception:
                error_msg = "Unknown error"
                debug_log("WORKER", "Failed to extract exception message", "ERROR")

            debug_log("WORKER", f"Emitting error: {error_msg}", "ERROR")
            self.emit_error(
                f"Unexpected error loading file: {error_msg}\n{traceback.format_exc()}"
            )


class FileSaveWorker(BaseWorker):
    """Worker for saving image files asynchronously.

    Signals:
        saved: Emitted when file is successfully saved
    """

    saved = pyqtSignal(str)  # Saved file path

    def __init__(
        self,
        image_array: np.ndarray,
        palette: list,
        file_path: Union[str, Path],
        parent: Optional[QObject] = None,
    ):
        """Initialize the file save worker.

        Args:
            image_array: Indexed image data to save
            palette: Color palette (768 RGB values)
            file_path: Path where to save the image (string or Path object)
            parent: Parent QObject for proper cleanup
        """
        super().__init__(file_path, parent)
        self.image_array = image_array
        self.palette = palette

    def run(self) -> None:
        """Save the image file in background thread."""
        try:
            debug_log("WORKER", f"Starting to save file: {self.file_path}", "DEBUG")
            debug_log(
                "WORKER",
                f"Image shape: {self.image_array.shape if self.image_array is not None else 'None'}",
                "DEBUG",
            )

            # Validate file path (but file doesn't need to exist for saving)
            if not self.validate_file_path(must_exist=False):
                return

            self.emit_progress(0, "Preparing to save...")

            # Validate input data
            if self.image_array is None or len(self.image_array) == 0:
                debug_log("WORKER", "No image data to save", "ERROR")
                self.emit_error("No image data to save")
                return

            if self.palette is None or len(self.palette) != 768:
                debug_log(
                    "WORKER",
                    f"Invalid palette data: length={len(self.palette) if self.palette else 0}",
                    "ERROR",
                )
                self.emit_error("Invalid palette data")
                return

            if self.is_cancelled():
                return

            self.emit_progress(20, "Validating image data...")

            # Create PIL image from array
            try:
                debug_log("WORKER", "Creating PIL image from array...", "DEBUG")
                image = Image.fromarray(self.image_array, mode="P")
                debug_log(
                    "WORKER", f"PIL image created: {image.size} {image.mode}", "DEBUG"
                )
            except Exception as e:
                self.emit_error(f"Failed to create image from data: {e!s}")
                return

            if self.is_cancelled():
                return

            self.emit_progress(40, "Creating indexed image...")

            # Apply palette
            try:
                debug_log("WORKER", "Applying palette...", "DEBUG")
                image.putpalette(self.palette)
                debug_log("WORKER", "Palette applied successfully", "DEBUG")
            except Exception as e:
                debug_log("WORKER", f"Failed to apply palette: {e}", "ERROR")
                self.emit_error(f"Failed to apply palette: {e!s}")
                return

            if self.is_cancelled():
                return

            self.emit_progress(60, "Applying color palette...")

            # Ensure parent directory exists
            if self.file_path:
                self.file_path.parent.mkdir(parents=True, exist_ok=True)

            # Save image
            try:
                # Determine format from extension
                format_map = {
                    ".png": "PNG",
                    ".gif": "GIF",
                    ".bmp": "BMP",
                    ".tiff": "TIFF",
                    ".tif": "TIFF",
                }

                file_format = format_map.get(self.file_path.suffix.lower(), "PNG")

                # Save with appropriate options
                save_kwargs = {}
                if file_format == "PNG":
                    save_kwargs["optimize"] = True
                    # Set transparency for palette index 0
                    save_kwargs["transparency"] = 0

                self.emit_progress(80, f"Writing {file_format} to disk...")
                debug_log(
                    "WORKER", f"Saving as {file_format} to: {self.file_path}", "DEBUG"
                )
                debug_log("WORKER", f"Save options: {save_kwargs}", "DEBUG")
                image.save(str(self.file_path), format=file_format, **save_kwargs)
                debug_log("WORKER", "Image saved successfully", "INFO")

            except Exception as e:
                debug_log(
                    "WORKER", f"Failed to save image: {type(e).__name__}: {e}", "ERROR"
                )
                self.emit_error(f"Failed to save image: {e!s}")
                return

            if self.is_cancelled():
                return

            self.emit_progress(100, "Save complete!")

            # Emit success
            self.saved.emit(str(self.file_path))
            self.emit_finished()

        except Exception as e:
            self.emit_error(
                f"Unexpected error saving file: {e!s}\n{traceback.format_exc()}"
            )


class PaletteLoadWorker(BaseWorker):
    """Worker for loading palette files asynchronously.

    Signals:
        result: Emitted with loaded palette data
    """

    result = pyqtSignal(dict)  # Palette data dictionary

    def __init__(self, file_path: Union[str, Path], parent: Optional[QObject] = None):
        """Initialize the palette load worker.

        Args:
            file_path: Path to the palette file to load (string or Path object)
            parent: Parent QObject for proper cleanup
        """
        super().__init__(file_path, parent)

    def _determine_palette_format(self) -> str:
        """Determine the palette format based on file extension.

        Returns:
            String identifying the palette format
        """
        return self.file_path.suffix.lower()

    def _load_json_palette(self) -> Optional[dict]:
        """Load JSON palette file.

        Returns:
            Dictionary containing palette data or None if failed
        """
        try:
            with open(self.file_path) as f:
                data = json.load(f)

            if self.is_cancelled():
                return None

            self.emit_progress(60, "Parsing JSON palette data...")

            # Validate JSON structure
            if "colors" not in data:
                self.emit_error("Invalid palette JSON: missing 'colors' field")
                return None

            return data

        except json.JSONDecodeError as e:
            self.emit_error(f"Invalid JSON format: {e!s}")
            return None
        except Exception as e:
            self.emit_error(f"Failed to load JSON palette: {e!s}")
            return None

    def _load_binary_palette(self) -> Optional[dict]:
        """Load ACT/PAL palette file (raw RGB data).

        Returns:
            Dictionary containing palette data or None if failed
        """
        try:
            with open(self.file_path, "rb") as f:
                raw_data = f.read()

            if self.is_cancelled():
                return None

            self.emit_progress(60, "Converting binary palette data...")

            # Convert to color list
            if len(raw_data) < 768:
                self.emit_error(
                    f"Invalid palette file: expected 768 bytes, got {len(raw_data)}"
                )
                return None

            colors = []
            for i in range(0, min(768, len(raw_data)), 3):
                r = raw_data[i]
                g = raw_data[i + 1]
                b = raw_data[i + 2]
                colors.append([r, g, b])

            return {
                "name": self.file_path.stem,
                "colors": colors,
                "format": "ACT",
            }

        except Exception as e:
            self.emit_error(f"Failed to load PAL/ACT palette: {e!s}")
            return None

    def _load_gimp_palette(self) -> Optional[dict]:
        """Load GIMP palette file (.gpl format).

        Returns:
            Dictionary containing palette data or None if failed
        """
        try:
            colors = []
            name = self.file_path.stem

            with open(self.file_path) as f:
                lines = f.readlines()

            if self.is_cancelled():
                return None

            self.emit_progress(60, "Parsing GIMP palette format...")

            # Parse GIMP palette format
            if not lines or not lines[0].strip().startswith("GIMP Palette"):
                self.emit_error("Invalid GIMP palette file")
                return None

            for line in lines[1:]:
                line = line.strip()
                if line.startswith("#") or not line:
                    continue
                if line.startswith("Name:"):
                    name = line[5:].strip()
                    continue

                # Parse color line
                parts = line.split()
                if len(parts) >= 3:
                    try:
                        r = int(parts[0])
                        g = int(parts[1])
                        b = int(parts[2])
                        colors.append([r, g, b])
                    except ValueError:
                        continue

            return {"name": name, "colors": colors, "format": "GIMP"}

        except Exception as e:
            self.emit_error(f"Failed to load GIMP palette: {e!s}")
            return None

    def _add_file_metadata(self, palette_data: dict) -> dict:
        """Add file metadata to palette data.

        Args:
            palette_data: Dictionary containing palette data

        Returns:
            Updated palette data with file metadata
        """
        palette_data["file_path"] = str(self.file_path)
        palette_data["file_name"] = self.file_path.name
        return palette_data

    def run(self) -> None:
        """Load the palette file in background thread."""
        try:
            # Validate file path
            if not self.validate_file_path(must_exist=True):
                return

            self.emit_progress(0, f"Loading palette from {self.file_path.name}...")
            if self.is_cancelled():
                return

            self.emit_progress(30, "Reading palette file...")

            # Determine file type and load accordingly
            suffix = self._determine_palette_format()
            palette_data = None

            if suffix == ".json":
                palette_data = self._load_json_palette()
            elif suffix == ".pal":
                palette_data = self._load_binary_palette()
            elif suffix == ".gpl":
                palette_data = self._load_gimp_palette()
            else:
                self.emit_error(f"Unsupported palette format: {suffix}")
                return

            if palette_data is None:
                return
            if self.is_cancelled():
                return

            self.emit_progress(90, "Validating palette colors...")

            # Add file metadata
            palette_data = self._add_file_metadata(palette_data)

            self.emit_progress(100, "Palette loaded successfully!")

            # Emit results
            self.result.emit(palette_data)
            self.emit_finished()

        except Exception as e:
            self.emit_error(
                f"Unexpected error loading palette: {e!s}\n{traceback.format_exc()}"
            )
