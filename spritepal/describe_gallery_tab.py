#!/usr/bin/env python3
from __future__ import annotations

"""
Script to describe the Gallery tab layout and functionality.
"""

import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication, QMainWindow, QTextEdit

# Add parent directory to path to import SpritePal modules
sys.path.insert(0, str(Path(__file__).parent))

from ui.dialogs.manual_offset_unified_integrated import UnifiedManualOffsetDialog
from utils.logging_config import get_logger

logger = get_logger(__name__)

def describe_gallery_tab():
    """Create and describe the Gallery tab widget."""
    app = QApplication.instance() or QApplication(sys.argv)

    # Create the manual offset dialog to see Gallery tab in context
    dialog = UnifiedManualOffsetDialog()

    # Switch to Gallery tab
    if dialog.tab_widget:
        for i in range(dialog.tab_widget.count()):
            if dialog.tab_widget.tabText(i) == "Gallery":
                dialog.tab_widget.setCurrentIndex(i)
                break

    # Get the gallery tab
    gallery_tab = dialog.gallery_tab

    # Collect information about the gallery tab
    description = []
    description.append("=== GALLERY TAB DESCRIPTION ===\n")
    description.append("The Gallery tab provides a visual overview of all sprites in the ROM.\n\n")

    description.append("LAYOUT:\n")
    description.append("┌─────────────────────────────────────┐\n")
    description.append("│  TOOLBAR                            │\n")
    description.append("│  [🔍 Scan ROM] [💾 Export] [🔄 Refresh] │\n")
    description.append("├─────────────────────────────────────┤\n")
    description.append("│                                     │\n")
    description.append("│     SPRITE GALLERY WIDGET          │\n")
    description.append("│                                     │\n")
    description.append("│   ┌────┐ ┌────┐ ┌────┐ ┌────┐    │\n")
    description.append("│   │    │ │    │ │    │ │    │    │\n")
    description.append("│   └────┘ └────┘ └────┘ └────┘    │\n")
    description.append("│   Sprite Sprite Sprite Sprite     │\n")
    description.append("│   @0x100 @0x200 @0x300 @0x400     │\n")
    description.append("│                                     │\n")
    description.append("│   (Grid of sprite thumbnails)      │\n")
    description.append("│                                     │\n")
    description.append("├─────────────────────────────────────┤\n")
    description.append("│  ACTION BAR                         │\n")
    description.append("│  [Compare] [Delete] Status: Ready  │\n")
    description.append("└─────────────────────────────────────┘\n\n")

    description.append("FEATURES:\n")
    description.append("• Scan ROM: Automatically finds and displays all sprites\n")
    description.append("• Grid View: Shows sprite thumbnails in a scrollable grid\n")
    description.append("• Export: Save selected sprites as PNG files\n")
    description.append("• Export Sheet: Create sprite sheets from multiple sprites\n")
    description.append("• Refresh: Update thumbnails after changes\n")
    description.append("• Selection: Click to select, Ctrl+Click for multiple\n")
    description.append("• Double-click: Navigate to sprite in Browse tab\n\n")

    description.append("CURRENT STATE:\n")
    if gallery_tab:
        description.append(f"• Tab is visible: {gallery_tab.isVisible()}\n")
        description.append(f"• Size: {gallery_tab.width()}x{gallery_tab.height()} pixels\n")

        if gallery_tab.gallery_widget:
            description.append("• Gallery widget present: Yes\n")
            description.append("• Gallery widget type: SpriteGalleryWidget\n")
        else:
            description.append("• Gallery widget present: No (not initialized)\n")

        if gallery_tab.toolbar:
            action_count = len(gallery_tab.toolbar.actions())
            description.append(f"• Toolbar actions: {action_count} actions available\n")

        description.append(f"• ROM loaded: {'Yes' if gallery_tab.rom_path else 'No'}\n")
        description.append(f"• Sprites found: {len(gallery_tab.sprites_data)}\n")
    else:
        description.append("• Gallery tab not available\n")

    description.append("\nWORKFLOW:\n")
    description.append("1. Load a ROM file in the main window\n")
    description.append("2. Open Manual Offset dialog\n")
    description.append("3. Click on Gallery tab\n")
    description.append("4. Click 'Scan ROM' to find all sprites\n")
    description.append("5. Browse thumbnails in the grid\n")
    description.append("6. Select sprites and export as needed\n")

    # Print the description
    full_description = "".join(description)
    print(full_description)

    # Also show the dialog
    dialog.resize(1000, 700)
    dialog.show()

    # Create a separate info window
    info_window = QMainWindow()
    info_window.setWindowTitle("Gallery Tab Description")
    info_window.resize(600, 800)

    text_widget = QTextEdit()
    text_widget.setReadOnly(True)
    text_widget.setPlainText(full_description)
    text_widget.setStyleSheet("font-family: monospace; font-size: 10pt;")

    info_window.setCentralWidget(text_widget)
    info_window.show()

    sys.exit(app.exec())

if __name__ == "__main__":
    describe_gallery_tab()
