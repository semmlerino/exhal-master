# SNES Graphics Memory Guide

## Overview

This project is a **Kirby Super Star sprite extraction and editing tool** that works with SNES memory dumps. It extracts and edits sprites by understanding and utilizing the SNES graphics memory architecture through three key memory types: CGRAM, VRAM, and OAM.

## SNES Graphics Memory Types

### 1. **CGRAM (Color Generator RAM) - Palette Memory**

**Purpose**: Contains color palettes for sprites and backgrounds.

**Key Usage**:
- **Palette Storage**: 16 palettes with 16 colors each (256 total colors)
- **File Format**: `.dmp` files like `Cave.SnesCgRam.dmp`, `CGRAM.dmp`
- **Conversion**: Uses BGR555 format (5 bits per color component)
- **Sprite Mapping**: OAM palettes 0-7 map to CGRAM palettes 8-15 (formula: `CGRAM_palette = OAM_palette + 8`)

**Code Examples**:
```python
# From sprite_edit_helpers.py
def parse_cgram(cgram_file: str) -> list[list[tuple[int, int, int]]]:
    """Parse CGRAM file and return all palettes as RGB tuples"""
    
# From constants.py
CGRAM_SIZE = 512  # Color RAM size in bytes
CGRAM_PALETTE_SIZE = 32  # Bytes per palette in CGRAM
```

**Files Generated**: 
- `Cave.SnesCgRam_palette_8.pal.json` (and similar)
- Palette extraction and conversion tools

### 2. **VRAM (Video RAM) - Tile Graphics Data**

**Purpose**: Contains sprite graphics data (tiles) in 4bpp format.

**Key Usage**:
- **Tile Storage**: 8x8 pixel tiles, 32 bytes per tile
- **Offset**: Default sprite location at `0xC000` (corresponding to SNES word address `$6000`)
- **Size**: Default sprite area is 16KB (`0x4000` bytes)
- **Format**: 4 bits per pixel (16 colors per tile)

**Code Examples**:
```python
# From constants.py
VRAM_SPRITE_OFFSET = 0xC000  # Default sprite offset in VRAM
VRAM_SPRITE_SIZE = 0x4000    # Default sprite data size (16KB)
BYTES_PER_TILE = 32          # 4bpp format
```

**Files Used**:
- `VRAM_edited.dmp`
- `VRAM_kirby_correct_palette.dmp`
- Multiple extracted VRAM regions and modified versions

### 3. **OAM (Object Attribute Memory) - Sprite Properties**

**Purpose**: Contains sprite-to-palette mappings and positioning data.

**Key Usage**:
- **Sprite Mapping**: 128 sprite entries, 4 bytes each
- **Palette Assignment**: Bits 0-2 of byte 3 specify which palette (0-7) each sprite uses
- **Critical for Accuracy**: Determines which tiles use which specific palettes
- **Structure**: X/Y position, tile number, attributes (including palette selection)

**Code Examples**:
```python
# From oam_palette_mapper.py
class OAMPaletteMapper:
    """Parse OAM data to map sprites to their assigned palettes"""
    
# OAM entry structure (from documentation)
# Byte 0: X position (low 8 bits)
# Byte 1: Y position  
# Byte 2: Tile number (low 8 bits)
# Byte 3: Attributes
#     Bit 0-2: Palette number (0-7)  ← CRITICAL
```

**Files Generated**:
- `oam_palette_mapping.txt`
- `oam_based_palette_mapping.json`

## Project Architecture & Workflow

### **Tool Components**

1. **SpritePal** (`spritepal/`):
   - Modern PyQt6 GUI application
   - **Primary Focus**: Palette extraction and management from CGRAM
   - **Workflow**: Load CGRAM dumps → Extract palettes → Preview/edit colors → Generate palette files
   - **User-Friendly**: Visual interface for palette manipulation

2. **Sprite Editor** (`sprite_editor/`):
   - Command-line tools for sprite editing
   - **Primary Focus**: VRAM injection and OAM mapping
   - **Workflow**: Parse VRAM/OAM dumps → Map sprites to palettes → Edit graphics → Inject back to VRAM
   - **Technical**: Developer-focused with precise control

3. **Pixel Editor** (`pixel_editor/`):
   - Built-in pixel art editor with MVC architecture
   - **Primary Focus**: Direct sprite graphics editing
   - **Workflow**: Edit individual tiles → Apply palette changes → Export modified graphics
   - **Integration**: Works with both SpritePal and Sprite Editor outputs

### **Typical Workflow**

1. **Memory Extraction**: 
   - Dump CGRAM, VRAM, and OAM from the same game frame using emulator tools
   - Ensure synchronization between all three memory types

2. **Palette Processing** (SpritePal):
   - Load CGRAM dump
   - Extract and preview all 16 palettes
   - Identify which palettes are active for current game area
   - Generate palette JSON files for each active palette

3. **Sprite Mapping** (Sprite Editor):
   - Parse OAM data to determine sprite-to-palette assignments
   - Map each 8x8 tile to its correct palette (0-7)
   - Generate mapping files for accurate rendering

4. **Graphics Editing** (Pixel Editor):
   - Load extracted sprites with correct palette assignments
   - Edit individual tiles or complete sprites
   - Maintain palette consistency across edits

5. **Injection** (Sprite Editor):
   - Inject modified graphics back into VRAM dumps
   - Maintain OAM mappings for consistent palette usage
   - Test in emulator to verify results

### **Key Technical Insights**

1. **Critical Mapping**: Each 8x8 tile needs individual palette assignment based on OAM data, not bulk palette application.

2. **Synchronization**: All three memory types (VRAM, CGRAM, OAM) must be dumped from the same exact game frame for accurate sprite extraction.

3. **Palette Offset**: Consistent across all SNES games - OAM palette N maps to CGRAM palette (N + 8).

4. **Game-Specific**: Different game areas (like Cave vs other levels) use different active palette combinations.

### **Error Handling**

The project includes specialized exception classes:
```python
class VRAMError(SpritePalError):
    """Raised for VRAM-related errors."""
    
class CGRAMError(SpritePalError):
    """Raised for CGRAM/palette-related errors."""
    
class OAMError(SpritePalError):
    """Raised for OAM-related errors."""
```

## Conclusion

This project represents a sophisticated reverse-engineering effort to accurately extract and edit sprites from Kirby Super Star by properly understanding and utilizing the SNES graphics memory architecture. The combination of automated tools (SpritePal, Sprite Editor) and manual editing capabilities (Pixel Editor) provides a complete workflow for SNES sprite modification while maintaining technical accuracy and visual fidelity.