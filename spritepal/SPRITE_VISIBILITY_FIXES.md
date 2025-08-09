# Sprite Visibility Fixes

## Problem
Sprites were invisible or barely visible due to:
1. Dark sprites on dark backgrounds (#1e1e1e)
2. Forced transparency on palette index 0
3. Poor contrast in checkerboard patterns
4. Inconsistent size constraints

## Solutions Implemented

### 1. SpritePreviewWidget (`ui/widgets/sprite_preview_widget.py`)

#### Checkerboard Background
- **Before**: Used `get_borderless_preview_style()` with no background
- **After**: Light checkerboard pattern (#f5f5f5 base with #e0e0e0 pattern)
- **Line 539-555**: New `_apply_content_style()` with checkerboard CSS

#### Visibility Guarantees
- **Line 998-1002**: Added explicit `show()` calls in `_guarantee_pixmap_display()`
- Ensures widgets are visible after setting pixmaps

#### Size Constraints
- **Line 663**: Changed minimum size from 200x150 to 150x150 (consistent with preview_label)
- Prevents layout conflicts

### 2. ZoomablePreviewWidget (`ui/zoomable_preview.py`)

#### Light Background
- **Line 86**: Changed background from #1e1e1e to #f0f0f0
- **Line 95**: Changed fill color from (30,30,30) to (240,240,240)
- **Line 127**: Changed zoom text from light (200,200,200) to dark (60,60,60)

#### Better Checkerboard Contrast
- **Line 168-171**: Changed checkerboard from (180,180,180)/(120,120,120) to white/(220,220,220)

#### Optional Transparency
- **Line 370**: Added `_apply_transparency` toggle
- **Line 407-410**: Added transparency checkbox UI
- **Line 463-470**: Added `_on_transparency_toggle()` handler
- **Line 501-515**: Made transparency conditional on toggle state
- Shows palette index 0 as dark gray (64,64,64) when transparency is disabled

#### Grid Visibility
- **Line 192**: Changed grid color from (60,60,60) to (100,100,100) for light background

## Testing

Run the test script to verify fixes:
```bash
python test_sprite_visibility_fix.py
```

## Results

✅ **Dark sprites are now visible** on light checkerboard backgrounds
✅ **Transparency is optional** - can be toggled on/off
✅ **Better contrast** for all UI elements
✅ **Consistent sizing** prevents layout issues
✅ **Explicit visibility** ensures sprites are shown

## Key Changes Summary

| Component | Before | After |
|-----------|--------|-------|
| Background Color | #1e1e1e (dark) | #f0f0f0 (light) |
| Checkerboard | Gray tones | White/light gray |
| Transparency | Always on index 0 | Optional toggle |
| Size Constraints | 200x150 min | 150x150 min |
| Visibility | Implicit | Explicit show() |

## Impact

These changes restore sprite visibility without redesigning the architecture. The fixes focus on:
- **Contrast**: Light backgrounds for dark sprites
- **Control**: User can toggle transparency
- **Consistency**: Matching size constraints
- **Reliability**: Explicit visibility guarantees

The feature that "USED TO WORK" now works again with better visibility controls.