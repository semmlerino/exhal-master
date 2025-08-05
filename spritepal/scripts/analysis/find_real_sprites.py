#!/usr/bin/env python3
"""
Find real character sprites in Kirby Super Star ROMs
"""

import os
import sys
from pathlib import Path

try:
    import cv2
except ImportError:
    print("ERROR: OpenCV is required for visual validation")
    print("Please install it with: pip install opencv-python")
    sys.exit(1)

# Add spritepal directory to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.sprite_finder import SpriteFinder
from utils.logging_config import get_logger

logger = get_logger(__name__)


def main():
    """Search for real sprites in ROM files"""

    # ROM files to search
    rom_files = [
        "Kirby Super Star (USA).sfc",
        "Kirby's Fun Pak (Europe).sfc"
    ]


    finder = SpriteFinder(output_dir="real_sprite_candidates")

    for rom_file in rom_files:
        if not Path(rom_file).exists():
            logger.warning(f"ROM file not found: {rom_file}")
            continue

        print(f"\n{'='*60}")
        print(f"Searching for sprites in: {rom_file}")
        print(f"{'='*60}\n")

        # First do a quick scan of common areas
        print("Phase 1: Quick scan of common sprite areas...")
        candidates = finder.quick_scan_known_areas(rom_file)

        if candidates:
            print(f"\nFound {len(candidates)} candidates in quick scan!")
            print("\nTop 5 candidates:")
            for i, candidate in enumerate(candidates[:5]):
                print(f"{i+1}. Offset: 0x{candidate.offset:06X}")
                print(f"   Confidence: {candidate.confidence:.1%}")
                print(f"   Tiles: {candidate.tile_count}")
                print(f"   Visual scores: {', '.join(f'{k}={v:.2f}' for k, v in candidate.visual_metrics.items())}")
                print()
        else:
            print("\nNo high-confidence sprites found in quick scan.")
            print("Phase 2: Deep scan with lower threshold...")

            # Do a more thorough scan with lower threshold
            candidates = finder.find_sprites_in_rom(
                rom_file,
                start_offset=0x80000,
                end_offset=0x300000,
                step=0x800,  # Check every 2KB
                min_confidence=0.5,  # Lower threshold
                save_previews=True,
                max_candidates=30
            )

            if candidates:
                print(f"\nFound {len(candidates)} candidates in deep scan!")
            else:
                print("\nNo sprites found even with lower threshold.")
                print("The sprite data may be in a different format or location.")

    print("\n" + "="*60)
    print("Scan complete! Check the 'real_sprite_candidates' folder for:")
    print("- Preview images of potential sprites")
    print("- JSON summary with all findings")
    print("- Text report with detailed analysis")
    print("\nManually review the preview images to identify actual character sprites.")


if __name__ == "__main__":
    main()
