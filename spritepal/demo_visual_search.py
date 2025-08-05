#!/usr/bin/env python3
"""
Comprehensive demonstration of visual similarity search functionality.

This script demonstrates:
1. Building a similarity index
2. Performing visual searches
3. Displaying results
4. Error handling for edge cases
"""

import sys
from pathlib import Path

from build_similarity_index import build_similarity_index
from core.visual_similarity_search import VisualSimilarityEngine
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QApplication,
    QLabel,
    QMainWindow,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)
from ui.dialogs.advanced_search_dialog import AdvancedSearchDialog
from ui.dialogs.similarity_results_dialog import show_similarity_results
from utils.logging_config import get_logger

logger = get_logger(__name__)


class VisualSearchDemo(QMainWindow):
    """Demo application for visual search functionality."""

    def __init__(self, rom_path: str):
        super().__init__()
        self.rom_path = Path(rom_path)
        self.index_path = self.rom_path.with_suffix(".similarity_index")

        self.setWindowTitle("Visual Search Demo")
        self.setMinimumSize(600, 400)

        self._setup_ui()
        self._update_status()

    def _setup_ui(self):
        """Setup the demo UI."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        layout = QVBoxLayout(central_widget)

        # Title
        title = QLabel("Visual Similarity Search Demo")
        title.setStyleSheet("font-size: 18px; font-weight: bold; margin: 10px;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        # ROM info
        self.rom_label = QLabel(f"ROM: {self.rom_path.name}")
        self.rom_label.setStyleSheet("font-family: monospace;")
        layout.addWidget(self.rom_label)

        # Index status
        self.index_label = QLabel()
        layout.addWidget(self.index_label)

        # Buttons
        self.build_button = QPushButton("Build Similarity Index")
        self.build_button.clicked.connect(self._build_index)
        layout.addWidget(self.build_button)

        self.search_button = QPushButton("Open Visual Search Dialog")
        self.search_button.clicked.connect(self._open_search_dialog)
        layout.addWidget(self.search_button)

        self.demo_button = QPushButton("Run Automated Demo")
        self.demo_button.clicked.connect(self._run_demo)
        layout.addWidget(self.demo_button)

        # Log output
        log_label = QLabel("Log Output:")
        layout.addWidget(log_label)

        self.log_text = QTextEdit()
        self.log_text.setMaximumHeight(200)
        self.log_text.setStyleSheet("font-family: monospace; font-size: 10px;")
        layout.addWidget(self.log_text)

        # Setup log handler
        self._setup_log_handler()

    def _setup_log_handler(self):
        """Setup log handler to show logs in the text widget."""
        import logging

        class TextHandler(logging.Handler):
            def __init__(self, text_widget):
                super().__init__()
                self.text_widget = text_widget

            def emit(self, record):
                msg = self.format(record)
                self.text_widget.append(msg)

        handler = TextHandler(self.log_text)
        handler.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))

        # Add to root logger
        root_logger = logging.getLogger()
        root_logger.addHandler(handler)
        root_logger.setLevel(logging.INFO)

    def _update_status(self):
        """Update the index status display."""
        if self.index_path.exists():
            try:
                # Try to load index to get sprite count
                engine = VisualSimilarityEngine()
                engine.import_index(self.index_path)
                count = len(engine.sprite_database)

                self.index_label.setText(f"✓ Index exists: {count} sprites indexed")
                self.index_label.setStyleSheet("color: green;")
                self.search_button.setEnabled(True)
                self.demo_button.setEnabled(True)

            except Exception as e:
                self.index_label.setText(f"⚠ Index corrupted: {e}")
                self.index_label.setStyleSheet("color: orange;")
                self.search_button.setEnabled(False)
                self.demo_button.setEnabled(False)

        else:
            self.index_label.setText("✗ No similarity index found")
            self.index_label.setStyleSheet("color: red;")
            self.search_button.setEnabled(False)
            self.demo_button.setEnabled(False)

    def _build_index(self):
        """Build the similarity index."""
        logger.info("Building similarity index...")
        self.build_button.setEnabled(False)
        self.build_button.setText("Building...")

        # Use smaller range for demo to speed up building
        success = build_similarity_index(
            rom_path=str(self.rom_path),
            start_offset=0x80000,  # Start from a typical sprite region
            end_offset=0x100000,   # Limit range for demo
            step_size=0x200        # Larger steps for demo
        )

        self.build_button.setEnabled(True)
        self.build_button.setText("Build Similarity Index")

        if success:
            logger.info("Index built successfully!")
            self._update_status()
        else:
            logger.error("Failed to build index")

    def _open_search_dialog(self):
        """Open the visual search dialog."""
        logger.info("Opening visual search dialog...")

        dialog = AdvancedSearchDialog(str(self.rom_path), self)

        # Switch to visual search tab
        dialog.tabs.setCurrentIndex(1)

        # Connect signals
        dialog.sprite_selected.connect(
            lambda offset: logger.info(f"User selected sprite at 0x{offset:X}")
        )

        dialog.exec()

    def _run_demo(self):
        """Run an automated demo of the visual search."""
        logger.info("Running automated visual search demo...")

        try:
            # Load the similarity engine
            engine = VisualSimilarityEngine()
            engine.import_index(self.index_path)

            if not engine.sprite_database:
                logger.warning("No sprites in index")
                return

            # Get a sprite to use as reference
            ref_offset = next(iter(engine.sprite_database.keys()))
            logger.info(f"Using sprite at 0x{ref_offset:X} as reference")

            # Find similar sprites
            matches = engine.find_similar(
                ref_offset,
                max_results=10,
                similarity_threshold=0.7
            )

            logger.info(f"Found {len(matches)} similar sprites")

            if matches:
                # Show results dialog
                dialog = show_similarity_results(matches, ref_offset, self)
                dialog.sprite_selected.connect(
                    lambda offset: logger.info(f"Demo: Selected sprite at 0x{offset:X}")
                )
                dialog.exec()
            else:
                logger.info("No similar sprites found (try lowering the threshold)")

        except Exception as e:
            logger.exception(f"Demo failed: {e}")


def main():
    """Main entry point."""
    if len(sys.argv) != 2:
        print("Usage: python demo_visual_search.py <rom_path>")
        print("\nThis demo will help you:")
        print("1. Build a similarity index for your ROM")
        print("2. Test visual similarity search")
        print("3. See results in the similarity dialog")
        sys.exit(1)

    rom_path = sys.argv[1]

    if not Path(rom_path).exists():
        print(f"ROM file not found: {rom_path}")
        sys.exit(1)

    app = QApplication(sys.argv)

    demo = VisualSearchDemo(rom_path)
    demo.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
