# Sprite Offset Slider Feature

## Overview
Added a dynamic sprite offset slider to SpritePal's ROM extraction panel, allowing users to explore ROM offsets in real-time and discover sprites without predefined locations.

## Features Implemented

### 1. Mode Selector
- **Preset Sprites** (default): Uses configured sprite locations from dropdown
- **Manual Offset Exploration**: Enables slider for dynamic offset browsing

### 2. Offset Slider Controls
- **Slider**: Visual control for scrolling through ROM offsets (0x0 to ROM size)
- **Spinbox**: Precise numeric input with configurable step size
- **Hex Display**: Shows current offset in hexadecimal format
- **Step Size**: Dropdown to select increment (256 bytes, 4KB, or 64KB)

### 3. Smart Navigation
- **Next Valid Sprite**: Searches forward for next decompressible sprite
- **Previous Valid Sprite**: Searches backward for previous sprite
- **Jump To**: Quick navigation to common sprite locations
- **Search Range**: Up to 1MB in each direction

### 4. Real-time Preview
- **Debounced Updates**: 16ms delay prevents excessive decompression attempts
- **Background Processing**: Uses QThread to keep UI responsive
- **Status Display**: Shows decompression success/failure messages
- **Quality Assessment**: Validates sprite data before display

## Usage

1. **Load ROM** in the ROM Extraction tab
2. **Switch Mode** to "Manual Offset Exploration"
3. **Use Slider** to browse through ROM offsets
4. **Preview Updates** automatically as you move the slider
5. **Extract** when you find a sprite you want

## Technical Implementation

### UI Changes (`ui/rom_extraction_panel.py`)
- Added QSlider, QSpinBox, and navigation controls
- Implemented mode switching logic
- Added debouncing timer for smooth updates
- Created SpriteSearchWorker for navigation

### Key Methods
- `_on_mode_changed()`: Switches between preset and manual modes
- `_on_offset_slider_changed()`: Handles slider movement with debouncing
- `_preview_manual_offset()`: Attempts sprite decompression at current offset
- `_find_next_sprite()/_find_prev_sprite()`: Smart navigation to valid sprites

### Integration
- Works with existing ROM extraction workflow
- Uses same preview widget as preset mode
- Compatible with all extraction features

## Benefits

1. **Sprite Discovery**: Find sprites in unknown ROM versions
2. **Visual Exploration**: See sprites as you browse
3. **No Configuration Needed**: Works without sprite_locations.json
4. **Efficient Navigation**: Jump to likely sprite locations
5. **Real-time Feedback**: Instant visual confirmation

## Performance

- Debouncing prevents UI freezing during rapid slider movement
- Background decompression keeps interface responsive
- Quality checks avoid displaying invalid data
- Reasonable size limits prevent memory issues

## Future Enhancements

1. Cache recently decompressed sprites
2. Add bookmark functionality for discovered offsets  
3. Export discovered locations to configuration
4. Heatmap visualization of sprite density
5. Pattern recognition for automatic sprite detection
