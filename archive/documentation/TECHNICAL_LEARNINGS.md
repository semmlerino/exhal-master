# Technical Learnings - SNES Sprite Palette System

## Core Discoveries

### 1. The OAM-to-CGRAM Palette Offset

**Critical Discovery**: OAM palette indices don't directly correspond to CGRAM palette indices.

```
OAM Palette Index → CGRAM Palette Index
        0        →        8
        1        →        9
        2        →        10
        3        →        11
        4        →        12
        5        →        13
        6        →        14
        7        →        15
```

**Why this happens**:
- CGRAM contains 256 colors (16 palettes × 16 colors)
- Palettes 0-7: Background (BG) palettes
- Palettes 8-15: Object (OBJ/sprite) palettes
- OAM only references the 8 sprite palettes (0-7)

**Implementation**:
```python
def get_sprite_palette_from_cgram(oam_palette_index):
    return oam_palette_index + 8
```

### 2. Memory Synchronization is Critical

**Problem**: Memory dumps from different frames create impossible mappings.

**Example from our debugging**:
- VRAM showed Beam Kirby (yellow ability)
- OAM showed Pink Kirby's palette mappings
- These were from different game moments!

**Solution**: Always capture VRAM, CGRAM, and OAM from the exact same frame.

### 3. OAM Only Shows Active Sprites

**The 3% Problem**:
- OAM has 128 sprite slots
- Only sprites currently on-screen have OAM entries
- A typical frame shows ~10-20 sprites
- Sprite sheet contains 512+ tile slots
- Result: Single dump captures only ~3% of all sprites

**Implications**:
- Can't determine palettes for off-screen sprites
- Different areas use different sprite combinations
- Need multiple dumps or real-time tracking

### 4. Sprite Palette Assignment is Dynamic

**Key Observations**:
1. Same sprite can use different palettes in different contexts
2. Palette usage depends on:
   - Current game area
   - Active power-ups
   - Enemy combinations
   - Special effects

**Example**: 
- Kirby normally uses palette 0
- With certain abilities, might use palette 1
- UI elements consistently use palette 2

### 5. SNES Sprite Organization

**VRAM Layout** (typical for Kirby Super Star):
```
0x0000-0xBFFF: Background tiles
0xC000-0xFFFF: Sprite tiles (16KB)
```

**Sprite Regions** (discovered through analysis):
- Tiles 0-31: Player sprites (Kirby)
- Tiles 32-63: UI/HUD elements
- Tiles 64-127: Common enemies
- Tiles 128-191: Special enemies
- Tiles 192-255: Effects/projectiles
- Tiles 256-511: Extended sprites

### 6. Large Sprite Handling

**16×16 Sprites** use 4 tiles in a 2×2 pattern:
```
[tile]    [tile+1]
[tile+16] [tile+17]
```

All 4 tiles use the same palette (from OAM entry).

### 7. Color Format (BGR555)

**SNES Color Encoding**:
```
Bit:  15 14 13 12 11 10 09 08 07 06 05 04 03 02 01 00
      [0][B4][B3][B2][B1][B0][G4][G3][G2][G1][G0][R4][R3][R2][R1][R0]
```

**Conversion to RGB888**:
```python
def bgr555_to_rgb888(bgr555):
    r = (bgr555 & 0x1F) * 8
    g = ((bgr555 >> 5) & 0x1F) * 8
    b = ((bgr555 >> 10) & 0x1F) * 8
    return (r, g, b)
```

### 8. Mesen-S Savestate Format (MSS)

**Structure**:
```
0x00-0x02: "MSS" signature
0x03-0x22: Header data
0x23-EOF:  Zlib compressed data

Decompressed layout:
0x00000-0x0FFFF: VRAM (64KB)
0x10000-0x101FF: CGRAM (512 bytes)
0x10200-0x1041F: OAM (544 bytes)
0x10420+: Additional state
```

### 9. Real-time Tracking Insights

**Confidence Scoring**:
- Track how many times each tile-palette pair appears
- Higher frequency = higher confidence
- Threshold of 3+ appearances for "confident" mapping

**Scene Detection**:
- Monitor for sudden influx of new tile-palette pairs
- 20+ new mappings likely indicates scene change
- Useful for automatic dumping

### 10. Coverage Patterns

**From 32 dumps analysis**:
- First 10 dumps: ~20% coverage (most common sprites)
- Next 10 dumps: +15% coverage (area-specific sprites)
- Next 10 dumps: +8% coverage (rare sprites)
- Diminishing returns after ~30 dumps

**Optimal Collection Strategy**:
1. Play through each major area once
2. Trigger all power-ups/abilities
3. Fight each boss type
4. Access bonus areas
5. View cutscenes

## Implementation Best Practices

### 1. Always Validate Palette Indices
```python
def validate_palette_index(palette_num):
    if not isinstance(palette_num, int):
        return 0
    return max(0, min(palette_num, 7))
```

### 2. Handle Missing Mappings Gracefully
```python
def get_palette_for_tile(tile, mappings, default=0):
    return mappings.get(tile, default)
```

### 3. Use Confidence Thresholds
```python
def is_mapping_confident(tile, min_observations=3):
    return observation_count[tile] >= min_observations
```

### 4. Preserve Synchronization
When capturing dumps, always capture in this order within the same frame:
1. VRAM
2. CGRAM  
3. OAM

### 5. Document Palette Usage
Track not just mappings, but context:
- Which game area
- What sprites were active
- Special conditions (power-ups, etc.)

## Debugging Techniques

### 1. Visual Palette Verification
Always create visual previews showing:
- Each palette's colors
- Sample sprites with each palette
- Side-by-side comparisons

### 2. Hash-based Change Detection
```python
def hash_oam_state(oam_data):
    # Simple hash for detecting major changes
    return sum(sprite.tile * 1000 + sprite.palette * 100 
               for sprite in oam_data[:32])
```

### 3. Coverage Visualization
Create tile grids colored by:
- Mapping confidence
- Palette assignment
- Last seen timestamp

## Conclusions

The SNES sprite system is more complex than it initially appears. The key insight is that palette assignment is dynamic and context-dependent, making static analysis insufficient. Real-time tracking during gameplay, combined with statistical analysis, provides the most accurate and comprehensive solution for sprite palette mapping.

The offset between OAM and CGRAM indices is a critical detail that's easy to miss but essential for correct color display. This project demonstrates the importance of understanding the hardware architecture when working with retro game assets.