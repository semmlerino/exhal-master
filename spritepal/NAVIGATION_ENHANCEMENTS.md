# SpritePal Navigation Enhancements

## Overview

This document describes the enhanced sprite navigation system implemented to address UX problems with finding sprites in large ROM files.

## Problems Solved

1. **Users get lost in vast empty ROM regions**
   - Solution: Visual ROM map with sprite density heatmap
   - Smart navigation that automatically skips empty areas

2. **Manual offset slider is imprecise (covers entire 4MB range)**
   - Solution: Region-aware navigation with intelligent stepping
   - Keyboard shortcuts for fine control (256-byte steps)
   - Go-to-offset dialog for precise navigation

3. **No visual indication of sprite locations or density**
   - Solution: Interactive ROM map showing all found sprites
   - Color-coded quality indicators (green=high, yellow=medium, red=low)
   - Mini ROM map in manual offset dialog

4. **Modal dialogs break the discovery workflow**
   - Solution: Integrated navigation widget in main panel
   - Non-modal manual offset dialog
   - Real-time preview updates

## Key Components

### 1. SpriteNavigator Widget (`ui/components/navigation/sprite_navigator.py`)

The main navigation interface providing:
- Interactive ROM map with density visualization
- Quick navigation controls (next/prev sprite)
- Thumbnail previews of nearby sprites
- Smart/Manual mode switching
- Navigation history with back/forward
- Keyboard shortcut support

### 2. RegionJumpWidget (`ui/components/navigation/region_jump_widget.py`)

Quick navigation to sprite-dense regions:
- Dropdown list of detected regions
- Region statistics (sprite count, quality)
- Direct offset jumping
- Smart mode highlighting

### 3. Enhanced ROMMapWidget (`ui/components/visualization/rom_map_widget.py`)

Visual ROM representation with:
- Sprite location markers
- Quality-based coloring
- Click-to-navigate functionality
- Region highlighting in smart mode
- Hover tooltips showing offset

### 4. Improved Manual Offset Dialog

Enhancements include:
- Mini ROM map showing position context
- Bookmark system for saving locations
- Region-aware next/prev navigation
- Real-time search that skips empty areas
- Keyboard shortcuts (Ctrl+G, Ctrl+D, Ctrl+B)

## Usage

### Basic Navigation

1. **Visual Navigation**: Click anywhere on the ROM map to jump to that location
2. **Smart Navigation**: Use Next/Previous buttons to find sprites automatically
3. **Keyboard Navigation**:
   - Arrow keys: Fine movement (256 bytes)
   - Shift+Arrows: Large steps (64KB)
   - PageUp/Down: Jump to next/previous sprite
   - Alt+Left/Right: Navigate history

### Smart Mode

Enable Smart Mode to navigate by regions instead of individual offsets:
- Automatically groups sprites into logical regions
- Skip large empty areas between regions
- Shows region statistics and quality

### Bookmarks

Save interesting locations for later:
- Ctrl+D: Bookmark current location
- Ctrl+B: Show bookmarks menu
- Name bookmarks for easy identification

## Technical Implementation

### Sprite Detection

The `SpriteSearchWorker` uses intelligent algorithms to:
- Quick pre-validation to skip empty data
- Check for compression headers (LZ, etc.)
- Validate sprite structure
- Calculate quality scores

### Performance Optimizations

- Thumbnail caching reduces repeated decompression
- Predictive preloading for adjacent offsets
- Throttled updates during navigation
- Background workers for non-blocking search

### Integration

The navigation system integrates seamlessly with:
- ROM extraction panel
- Preview generation system
- Cache system for fast repeated access
- Existing sprite detection algorithms

## Future Enhancements

Potential improvements include:
- Heatmap overlay showing sprite density
- Custom region naming and coloring
- Export/import bookmark sets
- Search by sprite characteristics
- Multi-ROM navigation comparison