# Analysis Scripts

This directory contains development scripts for analyzing VRAM dumps, ROM files, and sprite data. These scripts were used during development to understand the SNES sprite format and validate extraction algorithms.

## VRAM Analysis Scripts

### Core Analysis Tools
- `analyze_vram_dump.py` - Comprehensive VRAM dump analyzer with multiple visualization modes
- `analyze_vram_simple.py` - Simplified VRAM analyzer for quick checks
- `analyze_correct_vram_offsets.py` - Validates sprite offsets in VRAM dumps
- `visualize_vram_sprites.py` - Creates visual representations of VRAM sprite data

### Extraction Scripts
- `extract_sprites_correct_offset.py` - Extracts sprites using validated offsets
- `extract_vram_from_mss.py` - Extracts VRAM data from MSS files

## ROM Analysis Scripts

### Sprite Finding
- `find_sprites_in_rom.py` - Scans ROM files for sprite data patterns
- `find_real_sprites.py` - Advanced sprite detection with confidence scoring
- `find_pal_rom_sprites.py` - Finds palette-aware sprites in ROM data
- `find_actual_tiles.py` - Locates tile data within ROM structure

### Validation
- `check_rom_checksum.py` - Validates ROM file integrity
- `verify_config_fix.py` - Verifies configuration file fixes

## Development Utilities
- `quick_config_check.py` - Quick configuration validation tool

## Usage

These scripts are primarily for development and debugging. Most require specific ROM files or VRAM dumps to function. They were instrumental in developing the core SpritePal extraction algorithms.

**Note**: These scripts may require manual adjustment of file paths and parameters for your specific use case.