# Critical Findings - Why Sprite Extraction is Failing

## The Problem
We've been unable to extract recognizable Kirby sprites from either ROM or VRAM dumps. All attempts result in garbage pixels or vertical line patterns.

## Key Discoveries

### 1. Wrong ROM Offsets
- Initial offsets like 0xC8000 were completely wrong
- Removed all incorrect data from sprite_locations.json

### 2. VRAM Contains Tilemap Data
- Offsets 0x4000-0x8000 contain 16-bit tilemap entries (tile indices + attributes)
- NOT actual tile graphics
- Example: 0x3085 = Tile #133, Palette 4

### 3. No Recognizable Graphics Found
- Searched entire VRAM (0x0000-0x10000)
- All regions show similar garbage patterns
- Different pixel format interpretations (2bpp, 4bpp planar, 4bpp linear) all fail

## Root Cause Analysis

### Possibility 1: Wrong Timing
- VRAM is dynamic - sprites load/unload during gameplay
- The MSS savestate might be from a moment when sprites aren't loaded
- Research mentioned needing to capture "when sprites are actively displayed"

### Possibility 2: MSS Format Issue
- MSS savestates might store VRAM in a processed/transformed format
- Not raw SNES VRAM format as we expect
- Emulator-specific encoding possible

### Possibility 3: Fundamental Misunderstanding
- We might be completely misunderstanding SNES graphics
- The 4bpp planar format implementation might be wrong
- Tile arrangement might be different

## What Works (According to Research)

1. **Sprite Test Mode**
   - Pro Action Replay code: 00740B01
   - Loads sprites "properly decompressed into VRAM"
   - This is the most reliable method

2. **Tile Molester**
   - Works with "4bpp linear" codec
   - Successful sprite rips exist on Spriters Resource

3. **Proper VRAM Timing**
   - Must capture when sprites are on screen
   - Dynamic loading means timing is critical

## Recommended Next Steps

### Option 1: Use Existing Tools
- Download and use Tile Molester with known working settings
- Stop trying to reinvent the wheel

### Option 2: Capture Better VRAM Dumps
- Use sprite test mode (00740B01)
- Capture VRAM when Kirby is definitely on screen
- Try different emulators (bsnes, Mesen2)

### Option 3: Analyze Successful Rips
- Download sprites from Spriters Resource
- Reverse engineer the format
- Understand what we're doing differently

### Option 4: Different Data Source
- Try extracting from save states in different formats
- Use emulator debugging features
- Work with known good sprite data

## Conclusion

We've been approaching this problem incorrectly. The combination of wrong ROM offsets, misunderstanding VRAM layout (tilemap vs graphics), and possibly using VRAM dumps at the wrong time has led to complete failure.

The most practical solution is to either:
1. Use existing tools that work (Tile Molester)
2. Implement the sprite test mode approach
3. Work backwards from successful sprite rips