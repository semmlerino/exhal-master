# Granular VRAM Offset Slider Implementation

## Overview
The VRAM offset slider has been significantly enhanced to provide fine-grained control for sprite discovery. Previously, the slider only allowed 4KB (0x1000) increments, potentially missing 99.2% of possible sprite locations. The new implementation allows tile-aligned navigation with multiple step sizes.

## Key Improvements

### 1. **Tile-Aligned Step Sizes**
- **0x20 (32 bytes)** - Single tile precision (default)
- **0x100 (256 bytes)** - 8 tiles
- **0x1000 (4KB)** - 128 tiles  
- **0x4000 (16KB)** - 512 tiles

Users can now navigate to ANY possible sprite location since sprites are aligned to 32-byte tile boundaries.

### 2. **Enhanced Visual Feedback**
- **Hex Display**: Styled monospace display (e.g., `0xC000`)
- **Tile Information**: Shows current tile number (e.g., `(Tile #1536)`)
- **Position Percentage**: Shows position in VRAM (e.g., `75.0%`)
- **Improved Styling**: Blue highlighted hex display with dark background

### 3. **Quick Jump Locations**
Added dropdown with common VRAM sprite locations:
- `0x0000` - Start of VRAM
- `0x4000` - Lower sprites region
- `0x8000` - Alternate sprites region
- `0xC000` - Default Kirby sprites
- `0x10000` - End of VRAM

### 4. **Keyboard Shortcuts**
- **Ctrl + Left/Right**: Step by current step size
- **Page Up/Down**: Jump by 0x1000 (4KB)
- **Number Keys 1-9**: Jump to 10%-90% of VRAM range

### 5. **Hex Input Support**
The spinbox now accepts hex input with `0x` prefix, making it easy to jump to specific offsets.

## Technical Details

### Files Modified
- `/ui/extraction_panel.py` - Main implementation

### Key Changes
1. Enhanced offset controls UI with multiple new widgets
2. Added `_update_offset_display()` method for unified display updates
3. Added `_on_step_changed()` handler for step size selection
4. Added `_on_jump_selected()` handler for quick jumps
5. Implemented `keyPressEvent()` for keyboard shortcuts
6. Updated slider configuration for fine-grained control

### Slider Configuration
```python
self.offset_slider.setSingleStep(0x20)    # Single tile step
self.offset_slider.setPageStep(0x100)     # Page step
self.offset_slider.setTickInterval(0x1000) # Visual ticks at 4KB
```

## Usage Guide

1. **Switch to Custom Range Mode**: Select "Custom Range" from the preset dropdown
2. **Choose Step Size**: Select desired granularity from the step dropdown
3. **Navigate**: 
   - Drag the slider for quick navigation
   - Use spinbox for precise hex input
   - Use keyboard shortcuts for efficient browsing
   - Use quick jump dropdown for known locations

## Benefits

- **No Missed Sprites**: Can now check every possible 32-byte aligned offset
- **Faster Discovery**: Quick jumps and keyboard shortcuts speed up exploration
- **Better Feedback**: Always know exactly where you are in VRAM
- **Consistent UX**: Similar controls to ROM extraction panel
- **Preserved Performance**: Real-time preview updates remain smooth

## Testing

Run `python3 test_granular_offset_slider.py` to test the new functionality in isolation.