# Sprite Editor Settings Guide

The Sprite Editor now remembers your settings and file selections between sessions!

## Features

### Automatic File Restoration
- The last used VRAM, CGRAM, and OAM files are automatically loaded when you start the application
- Extraction parameters (offset, size, palette) are preserved
- Window position and size are remembered

### Recent Files Menu
Access recently used files from the **File → Recent Files** menu:
- Shows the 5 most recent files of each type (VRAM, CGRAM, OAM)
- Click any file to instantly load it
- Files that no longer exist are automatically filtered out

### Settings Menu
The **Settings** menu provides control over the application behavior:

#### Reset All Settings
- Restores all settings to their defaults
- Useful if you want a fresh start or encounter issues

#### Clear Recent Files
- Removes all recent file history
- Your current settings and preferences are preserved

#### Auto-load Last Files
- When enabled (default), automatically populates file fields with last used files
- Disable if you prefer to start with empty fields each time

#### Remember Window Position
- When enabled (default), the window opens at its last position and size
- Disable if you prefer the default window placement

## Settings Storage

Settings are stored in a platform-specific location:
- **Windows**: `%APPDATA%\sprite_editor\settings.json`
- **Linux/Mac**: `~/.sprite_editor/settings.json`

## What Gets Saved

The following information is automatically saved:
- Last used file paths (VRAM, CGRAM, OAM)
- Recent files history (up to 10 per type)
- Extraction parameters (offset, tile count, palette)
- Tiles per row setting
- Window position and size
- User preferences (auto-load, remember position)

## Tips

1. **Quick Workflow**: With auto-load enabled, you can close the app and reopen it to continue exactly where you left off
2. **Project Switching**: Use the Recent Files menu to quickly switch between different ROM projects
3. **Portable Settings**: Copy the settings.json file to transfer your preferences to another machine