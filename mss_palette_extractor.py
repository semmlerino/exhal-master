#!/usr/bin/env python3
"""
MSS Savestate Palette Extractor for Kirby Super Star

This tool extracts PPU state (VRAM, CGRAM, OAM) from Mesen-S savestates (.mss files)
to determine the correct sprite-to-palette mappings for accurate sprite extraction.

MSS Savestate Format (discovered through analysis):
- Header: 0x00-0x22 (MSS signature + metadata)
- Compressed data: 0x23+ (zlib compressed)
- Decompressed layout:
  - 0x00000-0x0FFFF: VRAM (64KB)
  - 0x10000-0x101FF: CGRAM (512 bytes, 16 palettes × 16 colors × 2 bytes)
  - 0x10200-0x1041F: OAM (544 bytes, 128 sprites + high table)
  - 0x10420+: Other PPU/CPU state
"""

import json
import struct
import zlib
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


class MSSPaletteExtractor:
    def __init__(self, mss_file):
        self.mss_file = Path(mss_file)
        self.vram = None
        self.cgram = None
        self.oam = None
        self.sprites = []
        self.palettes = []

    def extract(self):
        """Extract VRAM, CGRAM, and OAM from MSS savestate"""
        print(f"Extracting from: {self.mss_file}")

        with open(self.mss_file, "rb") as f:
            data = f.read()

        # Verify MSS signature
        if data[:3] != b"MSS":
            raise ValueError("Not a valid MSS savestate file")

        # Decompress data (starts at offset 0x23)
        try:
            decompressed = zlib.decompress(data[0x23:])
            print(f"Decompressed size: {len(decompressed)} bytes")
        except Exception as e:
            raise ValueError(f"Failed to decompress savestate: {e}")

        # Extract memory regions
        self.vram = decompressed[0x00000:0x10000]   # 64KB
        self.cgram = decompressed[0x10000:0x10200]  # 512 bytes
        self.oam = decompressed[0x10200:0x10420]    # 544 bytes

        # Parse the data
        self._parse_oam()
        self._parse_cgram()

        return True

    def _parse_oam(self):
        """Parse OAM data to extract sprite information"""
        self.sprites = []

        # Parse main OAM table
        for i in range(0, 512, 4):
            x = self.oam[i]
            y = self.oam[i + 1]
            tile = self.oam[i + 2]
            attr = self.oam[i + 3]

            # Skip off-screen sprites
            if y >= 240:
                continue

            # Extract attributes
            palette = (attr >> 1) & 0x07
            priority = (attr >> 4) & 0x03
            h_flip = bool(attr & 0x40)
            v_flip = bool(attr & 0x80)

            # Get high bits
            sprite_idx = i // 4
            high_byte_idx = 512 + (sprite_idx // 4)
            high_bit_shift = (sprite_idx % 4) * 2

            high_bits = self.oam[high_byte_idx]
            size_bit = (high_bits >> high_bit_shift) & 1
            x_msb = (high_bits >> (high_bit_shift + 1)) & 1

            if x_msb:
                x |= 0x100

            self.sprites.append({
                "index": sprite_idx,
                "x": x,
                "y": y,
                "tile": tile,
                "palette": palette + 8,  # Sprite palettes are 8-15
                "priority": priority,
                "h_flip": h_flip,
                "v_flip": v_flip,
                "size": "large" if size_bit else "small",
                "active": tile != 0
            })

    def _parse_cgram(self):
        """Parse CGRAM data to extract color palettes"""
        self.palettes = []

        for pal_idx in range(16):
            colors = []
            for color_idx in range(16):
                offset = (pal_idx * 16 + color_idx) * 2
                bgr555 = struct.unpack("<H", self.cgram[offset:offset+2])[0]

                # Convert BGR555 to RGB
                r = ((bgr555 >> 0) & 0x1F) * 8
                g = ((bgr555 >> 5) & 0x1F) * 8
                b = ((bgr555 >> 10) & 0x1F) * 8

                colors.append((r, g, b))

            self.palettes.append(colors)

    def get_sprite_palette_mappings(self):
        """Get active sprites grouped by palette"""
        mappings = {}

        for sprite in self.sprites:
            if not sprite["active"]:
                continue

            pal = sprite["palette"]
            if pal not in mappings:
                mappings[pal] = []
            mappings[pal].append(sprite)

        return mappings

    def find_kirby_sprites(self):
        """Find sprites that are likely Kirby based on VRAM location"""
        # Kirby sprites are typically at VRAM $6000 (tiles 0x00-0x3F in 4bpp mode)
        kirby_sprites = []

        for sprite in self.sprites:
            if sprite["active"] and 0x00 <= sprite["tile"] <= 0x3F:
                kirby_sprites.append(sprite)

        return kirby_sprites

    def save_extracted_data(self, output_dir=None):
        """Save extracted VRAM, CGRAM, and OAM data"""
        output_dir = self.mss_file.parent if output_dir is None else Path(output_dir)

        # Save raw dumps
        base_name = self.mss_file.stem

        vram_file = output_dir / f"{base_name}_VRAM.dmp"
        with open(vram_file, "wb") as f:
            f.write(self.vram)
        print(f"Saved VRAM to: {vram_file}")

        cgram_file = output_dir / f"{base_name}_CGRAM.dmp"
        with open(cgram_file, "wb") as f:
            f.write(self.cgram)
        print(f"Saved CGRAM to: {cgram_file}")

        oam_file = output_dir / f"{base_name}_OAM.dmp"
        with open(oam_file, "wb") as f:
            f.write(self.oam)
        print(f"Saved OAM to: {oam_file}")

        # Save parsed data as JSON
        data = {
            "source_file": str(self.mss_file),
            "sprites": self.sprites,
            "sprite_palette_mappings": {
                str(k): list(v)
                for k, v in self.get_sprite_palette_mappings().items()
            },
            "palettes": {
                str(i): [f"#{r:02X}{g:02X}{b:02X}" for r, g, b in colors]
                for i, colors in enumerate(self.palettes)
            },
            "kirby_sprites": self.find_kirby_sprites()
        }

        json_file = output_dir / f"{base_name}_palette_data.json"
        with open(json_file, "w") as f:
            json.dump(data, f, indent=2)
        print(f"Saved palette data to: {json_file}")

        return True

    def create_report(self, output_file=None):
        """Create a visual report of sprite-to-palette mappings"""
        if output_file is None:
            output_file = self.mss_file.parent / f"{self.mss_file.stem}_report.png"

        # Create report image
        img = Image.new("RGB", (1024, 768), (32, 32, 32))
        draw = ImageDraw.Draw(img)

        # Try to load font
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 14)
            small_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 10)
        except:
            font = ImageFont.load_default()
            small_font = font

        # Title
        draw.text((20, 20), f"MSS Palette Mapping Report: {self.mss_file.name}",
                  fill=(255, 255, 255), font=font)

        # Summary
        active_sprites = [s for s in self.sprites if s["active"]]
        kirby_sprites = self.find_kirby_sprites()
        draw.text((20, 50), f"Active Sprites: {len(active_sprites)}", fill=(200, 200, 200), font=small_font)
        draw.text((20, 70), f"Kirby Sprites (tiles 0x00-0x3F): {len(kirby_sprites)}", fill=(200, 200, 200), font=small_font)

        # Draw palettes
        y_offset = 100
        draw.text((20, y_offset), "Sprite Palettes (8-15):", fill=(255, 255, 255), font=font)
        y_offset += 30

        for pal_idx in range(8, 16):
            x_offset = 20
            draw.text((x_offset, y_offset), f"Pal {pal_idx}:", fill=(200, 200, 200), font=small_font)
            x_offset += 50

            # Draw color swatches
            for color_idx in range(16):
                color = self.palettes[pal_idx][color_idx]
                draw.rectangle([x_offset, y_offset, x_offset + 20, y_offset + 20],
                              fill=color, outline=(64, 64, 64))
                x_offset += 22

            y_offset += 30

        # Draw sprite mappings
        y_offset += 20
        draw.text((20, y_offset), "Sprite to Palette Mappings:", fill=(255, 255, 255), font=font)
        y_offset += 30

        mappings = self.get_sprite_palette_mappings()
        for pal_idx in sorted(mappings.keys()):
            if pal_idx < 8:  # Skip background palettes
                continue

            sprites = mappings[pal_idx]
            draw.text((20, y_offset), f"Palette {pal_idx}: {len(sprites)} sprites",
                      fill=(200, 200, 200), font=small_font)

            # Show tile numbers
            tiles = sorted({s["tile"] for s in sprites})[:20]  # First 20 unique tiles
            tile_str = ", ".join(f"0x{t:02X}" for t in tiles)
            if len(tiles) < len({s["tile"] for s in sprites}):
                tile_str += "..."
            draw.text((150, y_offset), f"Tiles: {tile_str}", fill=(150, 150, 150), font=small_font)

            y_offset += 20
            if y_offset > 700:
                break

        # Save report
        img.save(output_file)
        print(f"Saved report to: {output_file}")

        return True


def main():
    import sys

    if len(sys.argv) < 2:
        print("MSS Savestate Palette Extractor")
        print("Usage: python mss_palette_extractor.py <savestate.mss> [output_dir]")
        print("\nThis tool extracts palette mapping information from Mesen-S savestates.")
        sys.exit(1)

    mss_file = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else None

    extractor = MSSPaletteExtractor(mss_file)

    try:
        # Extract data
        extractor.extract()

        # Save extracted data
        extractor.save_extracted_data(output_dir)

        # Create visual report
        extractor.create_report()

        # Print summary
        print("\n=== Extraction Summary ===")
        mappings = extractor.get_sprite_palette_mappings()
        for pal_idx in sorted(mappings.keys()):
            sprites = mappings[pal_idx]
            print(f"Palette {pal_idx}: {len(sprites)} active sprites")

        kirby_sprites = extractor.find_kirby_sprites()
        if kirby_sprites:
            print(f"\nKirby sprites found: {len(kirby_sprites)}")
            kirby_pals = {s["palette"] for s in kirby_sprites}
            print(f"Kirby uses palettes: {sorted(kirby_pals)}")

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
