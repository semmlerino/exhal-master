# Safe Grayscale Sprite Editing Guide

## The Golden Rule
**NEVER let your editor convert to RGB/RGBA!** Keep it indexed/grayscale throughout.

## Safe Editing Methods

### Method 1: GIMP (Free, Cross-platform)
1. **Open**: `safe_to_edit_4x.png`
2. **Check mode**: Image → Mode → should show "Indexed"
3. **Edit**: Use pencil tool (NOT brush - it anti-aliases)
4. **Important**: Set pencil to "Hard edge" mode
5. **Save**: File → Export As → PNG
   - **CRITICAL**: In export dialog, uncheck everything except "Indexed color"

### Method 2: Aseprite (Best for pixel art)
1. **Open**: `safe_to_edit_4x.png`
2. **Check**: Should show "Indexed" in title bar
3. **Edit**: All tools preserve indexed mode by default
4. **Save**: Just save normally - Aseprite preserves format

### Method 3: Paint.NET with IndexedPNG plugin
1. **Install**: IndexedPNG plugin first
2. **Open**: `safe_to_edit_4x.png`
3. **Edit**: Use pencil with aliasing OFF
4. **Save**: Use File → Save As → IndexedPNG format

### Method 4: GraphicsGale (Free, Windows)
1. **Open**: `safe_to_edit_4x.png`
2. **Edit**: Automatically preserves indexed mode
3. **Save**: File → Save - keeps format

## Grayscale Editing Rules

### Use ONLY these 16 values:
```
0  = Black (transparent in-game)
1  = Darkest gray (outlines)
2  = Very dark gray
3  = Dark gray
4  = Medium-dark gray
5  = Medium gray
6  = Medium gray
7  = Medium gray
8  = Medium-light gray
9  = Light gray
10 = Light gray
11 = Lighter gray
12 = Very light gray
13 = Near white
14 = Almost white
15 = White (brightest)
```

### What Each Value Means for Sprites:
- **0**: Background/transparent
- **1-3**: Outlines and deep shadows
- **4-7**: Main body colors (mid-tones)
- **8-11**: Highlights and lighter areas
- **12-15**: Bright highlights, shine

## Safe Editing Workflow

### 1. Before Starting
```bash
# Create backup
cp safe_to_edit_4x.png safe_to_edit_4x_backup.png
```

### 2. While Editing
- Use ONLY pencil/pixel tools (no soft brushes)
- NO blur, anti-alias, or smooth tools
- NO filters that add colors
- Zoom in to see individual pixels
- Use color picker to ensure you're using existing grays

### 3. Common Edits
- **Add sunglasses**: Use value 1 or 2 (dark)
- **Add highlights**: Use values 12-14
- **Change shapes**: Keep same value range as original
- **Add details**: Use adjacent gray values

### 4. After Editing - Verify Format
```bash
# Check your saved file
python3 -c "
from PIL import Image
img = Image.open('your_edited_file.png')
print(f'Mode: {img.mode}')
if img.mode == 'P':
    print('✓ Good! Indexed mode preserved')
    colors = img.getcolors()
    print(f'Colors used: {len(colors)}')
    if len(colors) <= 16:
        print('✓ Perfect! 16 or fewer colors')
else:
    print('✗ ERROR: Converted to RGB - need to fix!')
"
```

## Quick Test After Editing

```bash
# Resize back to original
python3 -c "
from PIL import Image
img = Image.open('safe_to_edit_4x_edited.png')
img_small = img.resize((128, 256), Image.NEAREST)
img_small.save('test_edit.png')
"

# Convert to SNES
python3 png_to_snes.py test_edit.png test_edit.bin

# Quick preview
python3 snes_tiles_to_png.py test_edit.bin preview.png 16
```

## Emergency Fix If Converted to RGB

```bash
python3 -c "
from PIL import Image
img = Image.open('accidentally_rgb.png')
# Force back to grayscale
gray = img.convert('L')
# Quantize to 16 levels
quantized = gray.point(lambda x: (x * 15) // 255)
# Save as indexed
indexed = quantized.convert('P')
indexed.save('fixed_indexed.png')
print('Fixed and saved as indexed!')
"
```

## Recommended Editors (Safest to Least Safe)

1. **Aseprite** - Built for pixel art, preserves indexed
2. **GraphicsGale** - Simple, respects formats
3. **GIMP** - Powerful but need to be careful with export
4. **Paint.NET** - Need plugin for indexed PNG
5. **Photoshop** - Often converts to RGB (be very careful!)

## Remember
- The image should ALWAYS show as "Indexed" or "Grayscale"
- You should see ONLY 16 gray levels, no smooth gradients
- Save frequently with different names to avoid losing work
- Test convert small sections first before doing big edits