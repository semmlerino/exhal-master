# Sprite Extraction Fix Summary

## Problem
Sprites were appearing as "pixely grey colours" instead of actual sprites when loading from ROM. This was caused by the HAL decompression tool (exhal) extracting far too much data because it cannot automatically detect where compressed sprite data ends in mixed data blocks.

## Root Cause Analysis
1. **exhal limitation**: The decompression tool cannot detect the end of compressed sprite data
2. **Mixed data blocks**: ROM contains level tiles + sprites in single compressed blocks
3. **Oversized extraction**: exhal was extracting 42KB instead of expected 8KB for sprites
4. **Data corruption**: Trying to display 42KB of mixed data as 8KB sprite caused visual corruption

## Solutions Implemented

### 1. Size-Limited Decompression
- Modified `find_compressed_sprite()` in `rom_injector.py` to accept `expected_size` parameter
- Truncates decompressed data to expected size from sprite configuration
- Prevents oversized data from corrupting sprite display

### 2. Sprite Data Validation
- Added `_validate_sprite_data()` method to check if data has valid 4bpp characteristics
- Added `_has_4bpp_tile_characteristics()` to validate individual tiles
- Ensures truncated data is actually valid sprite data, not mixed content

### 3. Sliding Window Search
- Implemented `_find_sprite_in_data()` for finding sprite start within larger blocks
- Tests common alignment points (0x100, 0x200, 0x400, etc.)
- Falls back to tile-by-tile scanning if needed

### 4. Multi-Size Sprite Scanner
- Updated `SpriteScanWorker` to test multiple size limits (4KB, 8KB, 16KB, 32KB)
- Helps identify correct sprite size for unknown ROM versions
- Tracks which size limit produces best quality results

### 5. Enhanced ROM Support
- Added Europe_Alt checksum (0xAE40) to sprite_locations.json
- Improved title matching for variations (e.g., SUPER STAR ↔ FUN PAK)
- Added offset_variants for different ROM versions

### 6. Size Validation in Preview
- Enhanced sprite preview to validate decompressed size against expected
- Warns if size is significantly different than expected
- Helps identify potential extraction issues early

## Testing
Use `test_sprite_extraction_fix.py` to verify the fixes:
```bash
python test_sprite_extraction_fix.py
```

The test script:
1. Reads ROM header and identifies the game
2. Tests extraction with and without size limits
3. Validates sprite data using new validation methods
4. Runs sprite scanner with multiple size limits
5. Reports on alignment and quality of extracted sprites

### 7. Default Size Fallbacks (NEW)
- Added 8KB default in `SpritePreviewWorker` when no expected_size in config
- Added 32KB default max limit in `find_compressed_sprite` when expected_size is None
- Prevents unlimited decompression even for sprites without configurations

### 8. Safety Validation (NEW)
- Added 64KB absolute maximum size check before any processing
- Validates original decompressed size to catch decompression errors early
- Raises exception if sprite data exceeds reasonable limits

## Results
With these fixes, sprites should now:
- Extract at the correct size (typically 8KB for Kirby sprites)
- Display properly instead of as "pixely grey colours"
- Validate as proper 4bpp sprite data
- Work across different ROM versions and regions
- Be protected against oversized extraction even without sprite configs
- Fail safely with clear error messages for corrupt data