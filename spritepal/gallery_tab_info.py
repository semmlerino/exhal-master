#!/usr/bin/env python3
"""
Script to print information about the Gallery tab without launching GUI.
"""

print("""
=== GALLERY TAB DESCRIPTION ===

The Gallery tab provides a visual overview of all sprites in the ROM.

LAYOUT:
┌─────────────────────────────────────┐
│  TOOLBAR                            │
│  [🔍 Scan ROM] [💾 Export] [🔄 Refresh] │
├─────────────────────────────────────┤
│                                     │
│     SPRITE GALLERY WIDGET          │
│                                     │
│   ┌────┐ ┌────┐ ┌────┐ ┌────┐    │
│   │    │ │    │ │    │ │    │    │
│   └────┘ └────┘ └────┘ └────┘    │
│   Sprite Sprite Sprite Sprite     │
│   @0x100 @0x200 @0x300 @0x400     │
│                                     │
│   (Grid of sprite thumbnails)      │
│                                     │
├─────────────────────────────────────┤
│  ACTION BAR                         │
│  [Compare] [Delete] Status: Ready  │
└─────────────────────────────────────┘

FEATURES:
• Scan ROM: Automatically finds and displays all sprites in the ROM
• Grid View: Shows sprite thumbnails in a scrollable grid layout
• Export Selected: Save selected sprites as individual PNG files
• Export Sheet: Create sprite sheets from multiple sprites
• Refresh: Update thumbnails after changes
• Selection: Click to select, Ctrl+Click for multiple selection
• Double-click: Navigate to sprite location in Browse tab
• Compare: Compare selected sprites side-by-side
• Delete: Remove sprites from the gallery view

COMPONENTS:
1. Toolbar (QToolBar):
   - 🔍 Scan ROM button
   - 💾 Export Selected button
   - 📋 Export Sheet button
   - ⚏ Grid View toggle
   - ☰ List View toggle
   - 🔄 Refresh button

2. SpriteGalleryWidget (main display area):
   - Scrollable grid of sprite thumbnails
   - Each thumbnail shows:
     * Sprite preview image
     * Offset location (hex)
     * Sprite dimensions
   - Supports drag selection
   - Context menu on right-click

3. Action Bar (bottom):
   - Compare button (enabled when 2+ sprites selected)
   - Delete button (enabled when sprites selected)
   - Status label showing selection count

WORKFLOW:
1. Load a ROM file in the main window
2. Open Manual Offset dialog
3. Click on Gallery tab
4. Click 'Scan ROM' to find all sprites
5. Browse thumbnails in the grid
6. Select sprites (click/ctrl-click/drag)
7. Export selected sprites or create sprite sheet

IMPLEMENTATION DETAILS:
- Located in: ui/tabs/sprite_gallery_tab.py
- Uses SpriteGalleryWidget for thumbnail display
- BatchThumbnailWorker for async thumbnail generation
- Integrates with SpriteFinder for sprite detection
- Supports batch operations on selected sprites

The Gallery tab is empty by default until you:
1. Load a ROM file
2. Click "Scan ROM" to populate the gallery

Once populated, it provides a visual catalog of all sprites
found in the ROM, making it easy to browse, select, and
export multiple sprites at once.
""")

# Also print code structure
print("\n=== CODE STRUCTURE ===")
print("Class: SpriteGalleryTab(QWidget)")
print("Location: ui/tabs/sprite_gallery_tab.py")
print("\nKey Methods:")
print("  _setup_ui() - Creates the UI layout")
print("  _create_toolbar() - Creates toolbar with actions")
print("  _create_action_bar() - Creates bottom action bar")
print("  _scan_for_sprites() - Scans ROM for all sprites")
print("  _export_selected() - Exports selected sprites")
print("  _export_sprite_sheet() - Creates sprite sheet")
print("  _refresh_thumbnails() - Updates thumbnail display")
print("\nSignals:")
print("  sprite_selected(int) - Emitted when navigating to sprite")
print("  sprites_exported(list) - Emitted after export")
print("\nKey Components:")
print("  self.gallery_widget - SpriteGalleryWidget instance")
print("  self.toolbar - QToolBar with actions")
print("  self.sprites_data - List of sprite metadata")
print("  self.thumbnail_worker - Async thumbnail generator")
