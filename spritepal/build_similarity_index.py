#!/usr/bin/env python3
"""
Utility script to build a similarity index for a ROM file.

This creates a visual similarity index that can be used by the advanced search dialog
for finding similar sprites.
"""

import argparse
import logging
import sys
from pathlib import Path

from core.rom_extractor import ROMExtractor
from core.visual_similarity_search import VisualSimilarityEngine
from PIL import Image
from utils.logging_config import get_logger

logger = get_logger(__name__)


def build_similarity_index(rom_path: str, output_path: str | None = None,
                          start_offset: int = 0, end_offset: int | None = None,
                          step_size: int = 0x100) -> bool:
    """
    Build a similarity index for a ROM file.

    Args:
        rom_path: Path to ROM file
        output_path: Output path for similarity index (defaults to rom_path.similarity_index)
        start_offset: Starting offset to scan from
        end_offset: Ending offset to scan to (None for end of file)
        step_size: Step size for scanning

    Returns:
        True if successful, False otherwise
    """
    rom_path = Path(rom_path)
    if not rom_path.exists():
        logger.error(f"ROM file not found: {rom_path}")
        return False

    if output_path is None:
        output_path = rom_path.with_suffix(".similarity_index")
    else:
        output_path = Path(output_path)

    logger.info(f"Building similarity index for: {rom_path}")
    logger.info(f"Output path: {output_path}")
    logger.info(f"Scan range: 0x{start_offset:X} - {f'0x{end_offset:X}' if end_offset else 'EOF'}")

    try:
        # Initialize components
        similarity_engine = VisualSimilarityEngine()
        rom_extractor = ROMExtractor()

        # Read ROM data
        with open(rom_path, "rb") as f:
            rom_data = f.read()

        if end_offset is None:
            end_offset = len(rom_data)
        else:
            end_offset = min(end_offset, len(rom_data))

        logger.info(f"ROM size: {len(rom_data)} bytes")
        logger.info(f"Scanning {end_offset - start_offset} bytes in steps of 0x{step_size:X}")

        indexed_count = 0
        total_offsets = (end_offset - start_offset) // step_size

        # Scan ROM for sprite data
        for i, offset in enumerate(range(start_offset, end_offset, step_size)):
            if (i + 1) % 100 == 0:
                logger.info(f"Progress: {i + 1}/{total_offsets} offsets ({indexed_count} sprites indexed)")

            try:
                # Try to extract sprite at this offset
                # This is a simplified approach - in practice, you'd want more sophisticated
                # sprite detection logic

                # Check if there's enough data
                if offset + 0x200 > len(rom_data):
                    continue

                # Try to decompress data at this offset
                try:
                    compressed_size, sprite_data = rom_extractor.rom_injector.find_compressed_sprite(
                        rom_data, offset, max_size=8192  # Reasonable max size
                    )

                    if len(sprite_data) < 32:  # Too small to be a meaningful sprite
                        continue

                    # Convert sprite data to image for indexing
                    # This is a simplified conversion - you'd want to use proper tile decoding
                    image = create_preview_image_from_sprite_data(sprite_data)

                    if image and image.width > 0 and image.height > 0:
                        # Index this sprite
                        similarity_engine.index_sprite(
                            offset=offset,
                            image=image,
                            metadata={
                                "compressed_size": compressed_size,
                                "decompressed_size": len(sprite_data)
                            }
                        )
                        indexed_count += 1

                        logger.debug(f"Indexed sprite at 0x{offset:X} ({compressed_size} -> {len(sprite_data)} bytes)")

                except Exception as e:
                    # Skip this offset if decompression fails
                    logger.debug(f"Skipping offset 0x{offset:X}: {e}")
                    continue

            except Exception as e:
                logger.exception(f"Error processing offset 0x{offset:X}: {e}")
                continue

        logger.info(f"Indexed {indexed_count} sprites from ROM")

        if indexed_count == 0:
            logger.warning("No sprites were indexed - similarity search will not work")
            return False

        # Build the similarity index
        similarity_engine.build_similarity_index()

        # Export the index
        similarity_engine.export_index(output_path)

        logger.info(f"Successfully built similarity index: {output_path}")
        logger.info(f"Index contains {indexed_count} sprites")

        return True

    except Exception as e:
        logger.exception(f"Failed to build similarity index: {e}")
        return False


def create_preview_image_from_sprite_data(sprite_data: bytes) -> Image.Image | None:
    """
    Create a preview image from sprite data.

    This is a simplified implementation that creates a grayscale image
    from the raw sprite data. In practice, you'd want proper 4bpp tile decoding.
    """
    try:
        # Simple approach: treat as grayscale data
        # Calculate square-ish dimensions
        data_len = len(sprite_data)
        width = int(data_len ** 0.5)
        height = (data_len + width - 1) // width

        # Pad data if necessary
        padded_data = sprite_data + b"\x00" * (width * height - len(sprite_data))

        # Create grayscale image
        image = Image.frombytes("L", (width, height), padded_data[:width * height])

        # Resize to reasonable size for hashing
        if image.width > 64 or image.height > 64:
            image = image.resize((64, 64), Image.Resampling.LANCZOS)

        return image

    except Exception as e:
        logger.debug(f"Failed to create preview image: {e}")
        return None


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Build visual similarity index for ROM")
    parser.add_argument("rom_path", help="Path to ROM file")
    parser.add_argument("-o", "--output", help="Output path for similarity index")
    parser.add_argument("-s", "--start", type=lambda x: int(x, 0), default=0,
                       help="Starting offset (hex or decimal)")
    parser.add_argument("-e", "--end", type=lambda x: int(x, 0), default=None,
                       help="Ending offset (hex or decimal)")
    parser.add_argument("--step", type=lambda x: int(x, 0), default=0x100,
                       help="Step size for scanning (hex or decimal)")
    parser.add_argument("-v", "--verbose", action="store_true",
                       help="Enable verbose logging")

    args = parser.parse_args()

    # Setup logging
    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    # Build the index
    success = build_similarity_index(
        rom_path=args.rom_path,
        output_path=args.output,
        start_offset=args.start,
        end_offset=args.end,
        step_size=args.step
    )

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
