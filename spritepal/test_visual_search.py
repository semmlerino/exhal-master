#!/usr/bin/env python3
"""
Test script for visual similarity search functionality.

Tests the integration between the AdvancedSearchDialog and the visual similarity engine.
"""

import sys
from pathlib import Path

from PyQt6.QtWidgets import QApplication
from ui.dialogs.advanced_search_dialog import AdvancedSearchDialog
from utils.logging_config import get_logger

logger = get_logger(__name__)


def test_visual_search_dialog(rom_path: str):
    """Test the visual search dialog with a ROM file."""

    rom_path = Path(rom_path)
    if not rom_path.exists():
        logger.error(f"ROM file not found: {rom_path}")
        return False

    # Check if similarity index exists
    index_path = rom_path.with_suffix(".similarity_index")
    if not index_path.exists():
        logger.info(f"No similarity index found at: {index_path}")
        logger.info("Run build_similarity_index.py first to create an index")
        return False

    logger.info(f"Testing visual search with ROM: {rom_path}")
    logger.info(f"Using similarity index: {index_path}")

    QApplication(sys.argv)

    try:
        # Create and show the advanced search dialog
        dialog = AdvancedSearchDialog(str(rom_path))

        # Switch to visual search tab
        dialog.tabs.setCurrentIndex(1)  # Visual search is tab index 1

        # Connect signals for testing
        def on_search_started():
            logger.info("Visual search started")

        def on_search_completed(count):
            logger.info(f"Visual search completed: {count} results")

        def on_sprite_selected(offset):
            logger.info(f"Sprite selected: 0x{offset:X}")

        dialog.search_started.connect(on_search_started)
        dialog.search_completed.connect(on_search_completed)
        dialog.sprite_selected.connect(on_sprite_selected)

        # Show instructions
        logger.info("\n" + "="*60)
        logger.info("VISUAL SEARCH TEST")
        logger.info("="*60)
        logger.info("Instructions:")
        logger.info("1. Enter a sprite offset in the 'Reference Sprite' field (e.g., 0x80000)")
        logger.info("2. Adjust the similarity threshold slider if desired")
        logger.info("3. Click 'Search' to find similar sprites")
        logger.info("4. Results will be shown in a separate dialog")
        logger.info("5. Close the dialog when done testing")
        logger.info("="*60)

        # Show the dialog
        result = dialog.exec()

        logger.info(f"Dialog closed with result: {result}")
        return True

    except Exception as e:
        logger.exception(f"Test failed: {e}")
        return False


def main():
    """Main entry point."""
    if len(sys.argv) != 2:
        print("Usage: python test_visual_search.py <rom_path>")
        print("\nExample:")
        print("  python test_visual_search.py /path/to/rom.sfc")
        print("\nNote: Make sure to build a similarity index first:")
        print("  python build_similarity_index.py /path/to/rom.sfc")
        sys.exit(1)

    rom_path = sys.argv[1]

    # Setup logging
    import logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    success = test_visual_search_dialog(rom_path)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
