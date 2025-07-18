# Grid Arrangement Guide

The Grid Arrangement feature in SpritePal provides flexible sprite organization supporting rows, columns, and custom tile groups - perfect for sprites like Kirby that may be arranged in various patterns.

## Features

### Selection Modes
- **Tile Mode**: Select individual tiles
- **Row Mode**: Select entire rows at once
- **Column Mode**: Select entire columns at once
- **Rectangle Mode**: Drag to select rectangular regions

### Arrangement Types
1. **Individual Tiles**: Add/remove single tiles
2. **Rows**: Add complete horizontal rows
3. **Columns**: Add complete vertical columns
4. **Custom Groups**: Create reusable tile groups for character poses

## Usage

1. **Open Grid Arrangement**
   - Extract sprites first using SpritePal
   - Click "Grid Arrange" button
   - The Grid Arrangement dialog opens

2. **Select Tiles**
   - Choose selection mode (Tile/Row/Column/Rectangle)
   - Click or drag to select tiles
   - Selected tiles are highlighted in yellow

3. **Build Arrangement**
   - Click "Add Selection" to add selected tiles
   - Use "Create Group" for reusable tile groups
   - Drag items in the arrangement list to reorder
   - Preview updates in real-time

4. **Export**
   - Click "Export Arrangement" when done
   - Creates a new PNG with your arrangement
   - Opens automatically in the pixel editor

## Keyboard Shortcuts
- **G**: Toggle grid overlay
- **C**: Toggle palette colorization
- **P**: Cycle through palettes (when colorized)
- **Delete**: Remove selected tiles
- **Escape**: Clear selection

## Tips
- Use Column mode for vertically-arranged sprites
- Create groups for repeating patterns (e.g., animation frames)
- Rectangle selection is great for character sprite blocks
- The arrangement preserves the original tile indices for palette compatibility

## Implementation Details

### Core Classes
- `GridArrangementManager`: Manages tile arrangements and groups
- `GridImageProcessor`: Extracts individual tiles from sprite sheets
- `GridPreviewGenerator`: Creates arranged previews
- `GridArrangementDialog`: Main UI for grid arrangement

### Data Structures
- `TilePosition`: Row/column coordinate for a tile
- `TileGroup`: Collection of tiles that stay together
- `ArrangementType`: Row, Column, Tile, or Group

The grid system maintains compatibility with existing row arrangement while adding powerful new capabilities for complex sprite organizations.