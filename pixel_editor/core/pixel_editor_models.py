#!/usr/bin/env python3
"""
Core data models for the pixel editor
These models handle the business logic without any UI dependencies
"""

# Standard library imports
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

# Third-party imports
import numpy as np
from PIL import Image

from .pixel_editor_utils import sanitize_for_json


@dataclass
class ImageModel:
    """
    Model for managing image data and operations
    Handles indexed images with 4bpp format
    """

    width: int = 8
    height: int = 8
    data: np.ndarray = field(default_factory=lambda: np.zeros((8, 8), dtype=np.uint8))
    modified: bool = False
    file_path: Optional[str] = None

    def __post_init__(self):
        """Ensure data array matches dimensions"""
        if self.data.shape != (self.height, self.width):
            self.data = np.zeros((self.height, self.width), dtype=np.uint8)

    def new_image(self, width: int, height: int) -> None:
        """Create a new blank image"""
        self.width = width
        self.height = height
        self.data = np.zeros((height, width), dtype=np.uint8)
        self.modified = True
        self.file_path = None

    def load_from_pil(self, pil_image: Image.Image) -> dict[str, Any]:
        """
        Load image data from a PIL Image
        Returns metadata including palette information
        """
        if pil_image.mode != "P":
            raise ValueError(
                f"Expected indexed image (mode 'P'), got mode '{pil_image.mode}'"
            )

        self.width = pil_image.width
        self.height = pil_image.height
        self.data = np.array(pil_image, dtype=np.uint8)
        self.modified = False

        # Extract metadata
        metadata = {"width": self.width, "height": self.height, "mode": pil_image.mode}

        # Get palette if available
        palette_data = pil_image.getpalette()
        if palette_data:
            metadata["palette"] = palette_data

        # Get any custom info
        if hasattr(pil_image, "info"):
            metadata["info"] = sanitize_for_json(pil_image.info)

        return metadata

    def to_pil_image(self, palette: Optional[list[int]] = None) -> Image.Image:
        """Convert to PIL Image with optional palette"""
        img = Image.fromarray(self.data, mode="P")

        if palette:
            img.putpalette(palette)

        return img

    def get_pixel(self, x: int, y: int) -> int:
        """Get pixel value at coordinates"""
        if 0 <= x < self.width and 0 <= y < self.height:
            return int(self.data[y, x])
        return 0

    def set_pixel(self, x: int, y: int, value: int) -> bool:
        """
        Set pixel value at coordinates
        Returns True if pixel was changed
        """
        if (
            0 <= x < self.width
            and 0 <= y < self.height
            and 0 <= value <= 15
            and self.data[y, x] != value
        ):
            self.data[y, x] = value
            self.modified = True
            return True
        return False

    def fill(self, x: int, y: int, new_value: int) -> list[tuple[int, int]]:
        """
        Flood fill from coordinates
        Returns list of changed pixels
        """
        if not (0 <= x < self.width and 0 <= y < self.height and 0 <= new_value <= 15):
            return []

        target_value = self.data[y, x]
        if target_value == new_value:
            return []

        changed_pixels = []
        stack = [(x, y)]

        while stack:
            cx, cy = stack.pop()
            if (
                0 <= cx < self.width
                and 0 <= cy < self.height
                and self.data[cy, cx] == target_value
            ):
                self.data[cy, cx] = new_value
                changed_pixels.append((cx, cy))
                self.modified = True

                # Add neighbors
                stack.extend([(cx + 1, cy), (cx - 1, cy), (cx, cy + 1), (cx, cy - 1)])

        return changed_pixels

    def get_color_at(self, x: int, y: int) -> int:
        """Color picker - get color at coordinates"""
        return self.get_pixel(x, y)


@dataclass
class PaletteModel:
    """
    Model for managing palette data
    Handles multiple palettes and conversions
    """

    colors: list[tuple[int, int, int]] = field(
        default_factory=lambda: [(i * 17, i * 17, i * 17) for i in range(16)]
    )
    name: str = "Default"
    index: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)

    def from_rgb_list(self, rgb_list: list[tuple[int, int, int]]) -> None:
        """Load palette from RGB tuples"""
        if len(rgb_list) < 16:
            # Pad with black if needed
            rgb_list = rgb_list + [(0, 0, 0)] * (16 - len(rgb_list))
        elif len(rgb_list) > 16:
            # Truncate if too many
            rgb_list = rgb_list[:16]

        self.colors = rgb_list

    def from_flat_list(self, flat_list: list[int]) -> None:
        """Load palette from flat list [r,g,b,r,g,b,...]"""
        if len(flat_list) < 48:  # 16 colors * 3 components
            flat_list = flat_list + [0] * (48 - len(flat_list))

        self.colors = []
        for i in range(0, 48, 3):
            self.colors.append((flat_list[i], flat_list[i + 1], flat_list[i + 2]))

    def to_flat_list(self) -> list[int]:
        """Convert to flat list for PIL"""
        flat = []
        for r, g, b in self.colors:
            flat.extend([r, g, b])
        # PIL expects 256 colors for mode P
        flat.extend([0] * (768 - len(flat)))  # Pad to 256 colors
        return flat

    def from_json_file(self, file_path: str) -> bool:
        """
        Load palette from JSON file
        Returns True on success
        """
        try:
            with open(file_path) as f:
                data = json.load(f)

            if "palette" in data and "colors" in data["palette"]:
                colors_data = data["palette"]["colors"]
                self.colors = [tuple(c) for c in colors_data]
                self.name = data["palette"].get("name", Path(file_path).stem)
                self.metadata = data
                return True

        except (OSError, json.JSONDecodeError, KeyError, ValueError):
            return False

        return False

    def to_json_file(self, file_path: str) -> bool:
        """Save palette to JSON file"""
        try:
            data = {
                "palette": {
                    "name": self.name,
                    "colors": [list(c) for c in self.colors],
                    "format": "RGB888",
                }
            }
            # Add any additional metadata
            if self.metadata:
                data.update(self.metadata)

            with open(file_path, "w") as f:
                json.dump(data, f, indent=2)

            return True

        except OSError:
            return False


@dataclass
class ProjectModel:
    """
    Model for managing project state and file associations
    """

    image_path: Optional[str] = None
    palette_path: Optional[str] = None
    associations: dict[str, str] = field(
        default_factory=dict
    )  # image -> palette mapping
    metadata_path: Optional[str] = None

    def associate_files(self, image_path: str, palette_path: str) -> None:
        """Associate an image with a palette file"""
        self.associations[image_path] = palette_path

    def get_associated_palette(self, image_path: str) -> Optional[str]:
        """Get palette associated with an image"""
        return self.associations.get(image_path)

    def get_metadata_path(self, image_path: str) -> str:
        """Get the metadata file path for an image"""
        path = Path(image_path)
        return str(path.with_suffix(".metadata.json"))

    def clear(self) -> None:
        """Clear project state"""
        self.image_path = None
        self.palette_path = None
        self.metadata_path = None
