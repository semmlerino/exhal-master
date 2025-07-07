#!/usr/bin/env python3
"""
Constants for SNES sprite editor
All magic numbers and specifications in one place
"""

# SNES Tile specifications
TILE_WIDTH = 8  # pixels
TILE_HEIGHT = 8  # pixels
BYTES_PER_TILE_4BPP = 32  # 4 bits per pixel, 8x8 pixels
PIXELS_PER_TILE = 64  # 8x8

# SNES Memory limits
VRAM_SIZE_STANDARD = 65536  # 64KB
VRAM_SIZE_MAX = 131072  # 128KB max
CGRAM_SIZE = 512  # Color RAM size in bytes
OAM_SIZE = 544  # Object Attribute Memory size (512 + 32 bytes)

# Palette specifications
COLORS_PER_PALETTE = 16
BYTES_PER_COLOR = 2  # BGR555 format
BYTES_PER_PALETTE = 32  # 16 colors * 2 bytes
MAX_PALETTES = 16  # Maximum number of palettes

# OAM specifications
OAM_ENTRIES = 128  # Number of sprite entries
BYTES_PER_OAM_ENTRY = 4
OAM_HIGH_TABLE_OFFSET = 512  # Offset to high table
OAM_HIGH_TABLE_SIZE = 32

# File size limits for security
MAX_VRAM_FILE_SIZE = 128 * 1024  # 128KB
MAX_PNG_FILE_SIZE = 5 * 1024 * 1024  # 5MB
MAX_CGRAM_FILE_SIZE = 2048  # 2KB
MAX_OAM_FILE_SIZE = 2048  # 2KB

# Default values
DEFAULT_TILES_PER_ROW = 16
DEFAULT_VRAM_OFFSET = 0xC000  # Common offset for sprite data

# Sprite size modes
SPRITE_SIZE_SMALL = '8x8'
SPRITE_SIZE_LARGE = '16x16'  # Can also be 32x32 or 64x64 depending on register

# Color conversion
BGR555_MAX_VALUE = 31  # 5 bits per color component
RGB888_MAX_VALUE = 255  # 8 bits per color component

# BGR555 color masks
BGR555_BLUE_MASK = 0x7C00   # Bits 14-10 for blue
BGR555_GREEN_MASK = 0x03E0  # Bits 9-5 for green  
BGR555_RED_MASK = 0x001F    # Bits 4-0 for red

# Bit shifts for BGR555
BGR555_BLUE_SHIFT = 10
BGR555_GREEN_SHIFT = 5
BGR555_RED_SHIFT = 0

# Pixel masks
PIXEL_4BPP_MASK = 0x0F  # Mask for 4-bit pixel values

# Additional memory limits
VRAM_SIZE_ABSOLUTE_MAX = 0x20000  # 128KB absolute maximum
TILE_DATA_MAX_SIZE = 0x10000      # 64KB max for tile data

# Palette sizes
PALETTE_SIZE_BYTES = 768  # 256 colors * 3 bytes (RGB)
PALETTE_ENTRIES = 256     # Total palette entries

# Tile encoding offsets
TILE_BITPLANE_OFFSET = 16  # Offset between bitplane pairs in 4bpp tiles

# Tile ranges for Kirby sprites
KIRBY_TILE_START = 0x180  # Tile 384
KIRBY_TILE_END = 0x200    # Tile 512
KIRBY_VRAM_BASE = 0x6000  # VRAM word address