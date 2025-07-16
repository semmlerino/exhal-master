"""
Palette management for SpritePal
"""

import json
from pathlib import Path
from typing import Any, Optional

from spritepal.utils.constants import (
    COLORS_PER_PALETTE,
    PALETTE_INFO,
    SPRITE_PALETTE_END,
    SPRITE_PALETTE_START,
)


class PaletteManager:
    """Manages palette extraction and file generation"""

    def __init__(self) -> None:
        self.cgram_data: Optional[bytes] = None
        self.palettes: dict[int, list[list[int]]] = {}

    def load_cgram(self, cgram_path: str) -> None:
        """Load CGRAM dump file"""
        with open(cgram_path, "rb") as f:
            self.cgram_data = f.read()

        # Extract all palettes
        self._extract_palettes()

    def _extract_palettes(self) -> None:
        """Extract all palettes from CGRAM data"""
        self.palettes = {}

        if self.cgram_data is None:
            return

        for pal_idx in range(16):
            colors: list[list[int]] = []
            for color_idx in range(COLORS_PER_PALETTE):
                offset = (pal_idx * COLORS_PER_PALETTE + color_idx) * 2

                if offset + 1 < len(self.cgram_data):
                    color_low = self.cgram_data[offset]
                    color_high = self.cgram_data[offset + 1]
                    snes_color = (color_high << 8) | color_low

                    # Convert BGR555 to RGB888
                    b = ((snes_color >> 10) & 0x1F) * 8
                    g = ((snes_color >> 5) & 0x1F) * 8
                    r = (snes_color & 0x1F) * 8

                    colors.append([r, g, b])
                else:
                    colors.append([0, 0, 0])

            self.palettes[pal_idx] = colors

    def get_palette(self, palette_index: int) -> list[list[int]]:
        """Get a specific palette"""
        return self.palettes.get(palette_index, [[0, 0, 0]] * COLORS_PER_PALETTE)

    def get_sprite_palettes(self) -> dict[int, list[list[int]]]:
        """Get only the sprite palettes (8-15)"""
        return {
            idx: self.palettes[idx]
            for idx in range(SPRITE_PALETTE_START, SPRITE_PALETTE_END)
            if idx in self.palettes
        }

    def create_palette_json(self, palette_index: int, output_path: str, companion_image: Optional[str] = None) -> str:
        """Create a .pal.json file for a specific palette"""
        colors = self.get_palette(palette_index)
        palette_name, description = PALETTE_INFO.get(
            palette_index,
            (f"Palette {palette_index}", "Sprite palette")
        )

        palette_data = {
            "format_version": "1.0",
            "format_description": "Indexed Pixel Editor Palette File",
            "palette": {
                "name": palette_name,
                "colors": colors,
                "color_count": len(colors),
                "format": "RGB888"
            },
            "usage_hints": {
                "transparent_index": 0,
                "typical_use": "sprite",
                "extraction_mode": "grayscale_companion"
            },
            "editor_compatibility": {
                "indexed_pixel_editor": True,
                "supports_grayscale_mode": True,
                "auto_loadable": True
            }
        }

        # Add source info if available
        if companion_image:
            palette_data["source"] = {
                "palette_index": palette_index,
                "extraction_tool": "SpritePal",
                "companion_image": companion_image,
                "description": description
            }

        # Save file
        with open(output_path, "w") as f:
            json.dump(palette_data, f, indent=2)

        return output_path

    def create_metadata_json(self, output_base: str, palette_files: dict[int, str], 
                           extraction_params: Optional[dict[str, Any]] = None) -> str:
        """Create metadata.json for palette switching and reinsertion"""
        metadata: dict[str, Any] = {
            "format_version": "1.0",
            "description": "Sprite palettes extracted by SpritePal",
            "palettes": {},
            "default_palette": 8,
            "palette_info": {}
        }
        
        # Add extraction parameters if provided
        if extraction_params:
            from datetime import datetime
            metadata["extraction"] = {
                "vram_source": extraction_params.get("vram_source", ""),
                "vram_offset": f"0x{extraction_params.get('vram_offset', 0):04X}",
                "tile_count": extraction_params.get("tile_count", 0),
                "extraction_size": extraction_params.get("extraction_size", 0),
                "extraction_date": extraction_params.get("extraction_date", datetime.now().isoformat())
            }

        # Add palette references
        for pal_idx in range(SPRITE_PALETTE_START, SPRITE_PALETTE_END):
            if pal_idx in palette_files:
                metadata["palettes"][str(pal_idx)] = Path(palette_files[pal_idx]).name

                # Add palette info
                _, description = PALETTE_INFO.get(pal_idx, (f"Palette {pal_idx}", "Sprite palette"))
                metadata["palette_info"][str(pal_idx)] = description

        # Save metadata file
        metadata_path = f"{output_base}.metadata.json"
        with open(metadata_path, "w") as f:
            json.dump(metadata, f, indent=2)

        return metadata_path

    def analyze_oam_palettes(self, oam_path: str) -> list[int]:
        """Analyze OAM data to find active palettes"""
        active_palettes = set()

        try:
            with open(oam_path, "rb") as f:
                oam_data = f.read()

            # Parse OAM entries
            for i in range(0, min(512, len(oam_data)), 4):
                if i + 3 < len(oam_data):
                    y_pos = oam_data[i + 1]
                    attrs = oam_data[i + 3]

                    # Check if sprite is on-screen
                    if y_pos < 0xE0:  # Y < 224
                        # Extract palette (lower 3 bits)
                        oam_palette = attrs & 0x07
                        cgram_palette = oam_palette + 8
                        active_palettes.add(cgram_palette)

        except Exception:
            # If OAM analysis fails, just return all sprite palettes
            return list(range(SPRITE_PALETTE_START, SPRITE_PALETTE_END))

        return sorted(active_palettes)
